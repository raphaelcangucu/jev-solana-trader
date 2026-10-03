"""Leituras derivadas para o dashboard v2 (só leitura, sem FastAPI — testável com o .venv do repo).

- `row_meta`: identidade de cada portfólio (perfil, tipo de teste, regra, fonte, pai) a partir do lab_registry.
- `SkillCache`: habilidade sem beta por portfólio (bot/analytics.window_stats desde o início): exposição média,
  excesso ajustado à exposição, timing e p do placebo. Calculado em segundo plano e guardado por `ttl` segundos.
- `spark_series`: curva de patrimônio reduzida (em % desde o início) para sparklines e pequenos múltiplos.
- `experiment_info`: dia N de 30 do experimento, marcadores dos vereditos.
- `real_bot_board`: placar do livro de papel do bot real (jev_trader.score, em processo) + série e decisões recentes.

SIMULAÇÃO: nada aqui escreve em disco, lê chaves ou envia ordens.
"""
from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

_LAB = str(Path(__file__).resolve().parents[1])
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)
from bot.paths import ROOT, LAB_DIR  # noqa: E402

EXPERIMENT_DAYS = 30
FIRST_VERDICT_DAY = 21
MIN_CLOSED_RT = 30
LAB_TYPES = {"H1": "lab_h1_exits", "H2": "lab_h2_ensemble", "H3": "lab_h3_limit", "H4": "lab_h4_hours"}  # = bot.params


def _f(x, default=None):
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


# ------------------------------------------------------------------ identidade

def originals_meta() -> dict[str, dict]:
    try:
        from bot import lab_registry as R
        return R.originals()
    except Exception:
        return {}


def row_meta(name: str, group: str, registry_entry: dict | None, originals: dict[str, dict]) -> dict:
    """Campos de identidade extra para uma linha do placar. `catalog` = nome usado por analytics/vereditos
    (os von de memecoin aparecem como `BONK_relaxed` no disco e `meme_BONK_relaxed` no catálogo)."""
    e = registry_entry
    catalog = name
    if e is None:
        if name in originals:
            e = originals[name]
        elif f"meme_{name}" in originals:
            catalog = f"meme_{name}"
            e = originals[catalog]
    e = e or {}
    fork = {}
    if e.get("parent"):
        try:
            from bot import lab_registry as R
            fork = {"fork_who": R.fork_who(e), "fork_summary": R.describe_fork(e)}
        except Exception:
            fork = {"fork_who": e.get("who") or "nightly", "fork_summary": None}
        fork["fork_reason"] = str(e.get("reason") or "").replace("[claude-night] ", "")[:400] or None
        fork["criteria_summary"] = e.get("criteria_summary") if (e.get("params_diff") or {}).get("criteria") else None
    return {
        **{k: fork.get(k) for k in ("fork_who", "fork_summary", "fork_reason", "criteria_summary")},
        "catalog": catalog,
        "profile": e.get("profile"),
        "test_type": e.get("test_type") or LAB_TYPES.get(e.get("hyp") or ""),
        "variant": e.get("variant"),
        "rule": e.get("rule"),
        "source": e.get("source"),
        "params_diff": e.get("params_diff") or None,
        "created_brt": e.get("created_brt"),
    }


def params_brief(catalog_name: str) -> dict | None:
    """Os poucos parâmetros efetivos que explicam um teste em uma frase (portões, saídas, horas, ensemble, regra)."""
    try:
        from bot import params as P
        eff, _prov, errs, _meta = P.explain(catalog_name)
    except Exception:
        return None
    g = eff.get("gates") or {}
    ex = eff.get("exits") or {}
    en = eff.get("ensemble") or None
    out = {k: g.get(k) for k in ("min_confidence", "min_prob_margin", "margin_gate", "max_skip_noul", "buy_fraction_usdt",
                                 "max_trades_per_hour", "cooldown_seconds", "max_exposure_frac")}
    out["exits"] = {k: ex.get(k) for k in ("tp", "sl", "trail")} if ex.get("enabled") else None
    out["hours"] = eff.get("hours")
    out["ensemble"] = {k: en.get(k) for k in ("min_agree", "pct_threshold")} if en else None
    out["rule"] = eff.get("rule") or None
    out["regime_filter"] = bool((eff.get("regime_filter") or {}).get("enabled"))
    out["exec_mode"] = (eff.get("exec") or {}).get("mode")
    out["paused"] = bool(eff.get("paused"))
    out["errors"] = len(errs or [])
    return out


# ------------------------------------------------------------------ habilidade sem beta

SKILL_KEYS = ("exposure_pct", "static_usd", "timing_usd", "timing_p", "ex_exposure", "ex_bh", "bh_pnl",
              "trades", "buys", "sells", "rt_wins", "fees", "cost_vs_mark", "mdd_pct", "hours")


def skill_fields(s: dict) -> dict:
    """Recorte de window_stats para a API (números finitos ou None)."""
    out = {}
    for k in SKILL_KEYS:
        v = s.get(k)
        out[k] = _f(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    for k in ("trades", "buys", "sells", "rt_wins"):
        if out.get(k) is not None:
            out[k] = int(out[k])
    sv = _f(s.get("start_value"))
    out["ex_exposure_pct"] = (out["ex_exposure"] / sv * 100) if (out.get("ex_exposure") is not None and sv) else None
    return out


def compute_skill_all(now_ts: float | None = None) -> dict[str, dict]:
    from bot import analytics as A
    now_ts = now_ts or time.time()
    cat, _reg = A.catalog()
    trades = A.load_trades()
    out: dict[str, dict] = {}
    for n, m in cat.items():
        try:
            s = A.window_stats(m, trades, 0, now_ts)
        except Exception:
            continue
        if not s.get("empty"):
            out[n] = skill_fields(s)
    return out


class SkillCache:
    """Recalcula em thread quando passa de `ttl`; os pedidos nunca esperam mais do que `first_wait` segundos."""

    def __init__(self, compute: Callable[[], dict] = compute_skill_all, ttl: float | None = None, first_wait: float = 4.0):
        self.compute = compute
        self.ttl = float(ttl if ttl is not None else os.environ.get("DASH_SKILL_TTL", 300))
        self.first_wait = first_wait
        self.data: dict[str, dict] = {}
        self.ts: float | None = None
        self.error: str | None = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def _run(self):
        try:
            d = self.compute()
            self.data, self.ts, self.error = d, time.time(), None
        except Exception as ex:  # nunca derruba o dashboard
            self.error = repr(ex)[:300]
            self.ts = time.time()

    def get(self) -> dict[str, dict]:
        with self._lock:
            stale = self.ts is None or time.time() - self.ts > self.ttl
            if stale and (self._thread is None or not self._thread.is_alive()):
                self._thread = threading.Thread(target=self._run, name="dash-skill", daemon=True)
                self._thread.start()
            th = self._thread
        if self.ts is None and th is not None:
            th.join(self.first_wait)
        return self.data

    def status(self) -> dict:
        return {"computed_ts": self.ts, "ttl_s": self.ttl, "error": self.error,
                "computing": bool(self._thread and self._thread.is_alive())}


# ------------------------------------------------------------------ séries reduzidas

def spark_series(rows: list[dict], n: int = 60, ts_of: Callable[[dict], float | None] | None = None) -> dict | None:
    """Patrimônio em % desde o primeiro ponto (e o mesmo para 'só segurar'), reduzido a ~n pontos."""
    ts_of = ts_of or (lambda r: _f(r.get("ts")))
    pts = [(ts_of(r), _f(r.get("equity")), _f(r.get("bh_equity"))) for r in rows]
    pts = [p for p in pts if p[0] is not None and p[1] is not None]
    if not pts:
        return None
    if len(pts) > n:
        step = (len(pts) - 1) / (n - 1)
        pts = [pts[round(i * step)] for i in range(n)]
    e0 = pts[0][1]
    b0 = pts[0][2] or e0
    if not e0:
        return None
    return {
        "t": [int(p[0]) for p in pts],
        "v": [round((p[1] / e0 - 1) * 100, 4) for p in pts],
        "h": [round(((p[2] or b0) / b0 - 1) * 100, 4) if b0 else None for p in pts],
    }


# ------------------------------------------------------------------ experimento

def experiment_info(start_ts_list: list[float | None], now_ts: float | None = None) -> dict:
    """Dia N de 30 a contar do primeiro portfólio a arrancar. Vereditos a partir do dia 21."""
    now_ts = now_ts or time.time()
    starts = [s for s in start_ts_list if s]
    if not starts:
        return {"start_ts": None, "day": None, "days_total": EXPERIMENT_DAYS, "first_verdict_day": FIRST_VERDICT_DAY,
                "min_closed_rt": MIN_CLOSED_RT}
    start = min(starts)
    elapsed = max(0.0, (now_ts - start) / 86400)
    return {
        "start_ts": start, "end_ts": start + EXPERIMENT_DAYS * 86400,
        "first_verdict_ts": start + FIRST_VERDICT_DAY * 86400,
        "elapsed_days": round(elapsed, 3), "day": min(EXPERIMENT_DAYS, int(elapsed) + 1),
        "days_total": EXPERIMENT_DAYS, "first_verdict_day": FIRST_VERDICT_DAY, "min_closed_rt": MIN_CLOSED_RT,
    }


# ------------------------------------------------------------------ bot real (livro de papel)

def real_bot_root() -> Path:
    """Raiz do repo do bot real (logs/ e config/experiment.json): env JEV_TRADER_ROOT, senão LAB/../.. dos dados."""
    env = os.environ.get("JEV_TRADER_ROOT", "").strip()
    return Path(env) if env else ROOT.resolve().parents[1]


def _import_score():
    for src in (LAB_DIR.resolve().parents[1] / "src", real_bot_root() / "src"):
        if (src / "jev_trader" / "score.py").exists():
            if str(src) not in sys.path:
                sys.path.insert(0, str(src))
            break
    from jev_trader import score as S  # type: ignore
    from jev_trader.experiment import load_experiment  # type: ignore
    from jev_trader.records import parse_t  # type: ignore
    return S, load_experiment, parse_t


_jl_cache: dict[str, tuple[Any, list]] = {}


def _jsonl(p: Path) -> list[dict]:
    try:
        st = p.stat()
    except FileNotFoundError:
        return []
    k = (st.st_ino, st.st_size, st.st_mtime_ns)
    c = _jl_cache.get(str(p))
    if c and c[0] == k:
        return c[1]
    rows = []
    with open(p, "rb") as fh:
        for line in fh:
            if line.strip():
                try:
                    r = json.loads(line)
                    if isinstance(r, dict):
                        rows.append(r)
                except Exception:
                    pass
    _jl_cache[str(p)] = (k, rows)
    return rows


def _downsample(xs: list, n: int) -> list:
    if len(xs) <= n:
        return xs
    step = (len(xs) - 1) / (n - 1)
    return [xs[round(i * step)] for i in range(n)]


def build_real_board(decisions: list[dict], trades: list[dict], experiment, S, parse_t, points: int = 360,
                     book: dict | None = None) -> dict:
    """Placar + série papel × segurar + decisões/trades recentes. Pura (recebe as listas).

    `book` é o paper_book.json do livro (A/B): o livro B começa no seu primeiro ciclo (S.experiment_for_book)."""
    if book is not None and hasattr(S, "experiment_for_book"):
        board = S.scoreboard(decisions, trades, experiment, book=book)
        experiment = S.experiment_for_book(experiment, book)
    else:
        board = S.scoreboard(decisions, trades, experiment)
    hr = dict(board.get("hit_rate") or {})
    detail = hr.pop("detail", None) or []
    board["hit_rate"] = hr
    board["hit_recent"] = detail[-30:][::-1]
    run_dec = S.select_run(decisions, experiment)
    run_tr = S.select_run(trades, experiment)
    sol0, usdt0 = experiment.book_sol, experiment.book_usdt
    series = []
    for d in run_dec:
        px = _f(d.get("px_in")); sol = _f(d.get("paper_sol")); usdt = _f(d.get("paper_usdt")); t = parse_t(d.get("t"))
        if px is None or px <= 0 or sol is None or usdt is None or t is None:
            continue
        series.append([int(t.timestamp()), round(sol * px + usdt, 6), round(sol0 * px + usdt0, 6), px])
    board["series"] = {"cols": ["ts", "paper_usd", "hold_usd", "px"], "rows": _downsample(series, points)}
    board["recent_decisions"] = [
        {"t": d.get("t"), "action": d.get("action"), "model_action": d.get("model_action"), "conf": _f(d.get("conf")),
         "skip": _f(d.get("skip")), "reason": d.get("reason"), "px": _f(d.get("px_in")), "paper_fill": bool(d.get("paper_fill")),
         "source": d.get("source"), "paper_reason": d.get("paper_reason"), "exit_reason": d.get("exit_reason")}
        for d in run_dec[-30:][::-1]]
    board["recent_trades"] = [
        {"t": t.get("t"), "side": t.get("side"), "conf": _f(t.get("conf")), "px": _f(t.get("px_in")),
         "fill_px": _f(t.get("fill_px")), "in_ui": _f(t.get("in_amount_ui")), "out_ui": _f(t.get("out_amount_ui")),
         "fill_mode": t.get("fill_mode"), "reason": t.get("reason")}
        for t in run_tr[-20:][::-1]]
    px = _f(board.get("last_px"))
    pb = board.get("paper_book") or {}
    if px:
        sol_usd = (_f(pb.get("sol"), 0.0) or 0.0) * px
        usdt = _f(pb.get("usdt"), 0.0) or 0.0
        tot = sol_usd + usdt
        board["composition"] = {"sol_usd": sol_usd, "usdt_usd": usdt, "sol_frac": (sol_usd / tot) if tot > 0 else None}
    board.pop("since", None)
    return board


_rb_cache: dict[str, Any] = {"key": None, "val": None}


def real_bot_books(root: Path) -> list[tuple[str, Path]]:
    """Livros de papel do bot real: A em logs/, e cada logs/paper_<x>/ com logs (B = logs/paper_b, perfil com saídas).
    O rótulo vem do paper_book.json (campo book) ou do nome da pasta."""
    books = [("A", root / "logs")]
    for d in sorted((root / "logs").glob("paper_*")):
        if not d.is_dir() or not ((d / "decisions.jsonl").exists() or (d / "paper_book.json").exists()):
            continue
        label = d.name[len("paper_"):].upper() or d.name
        try:
            label = str(json.loads((d / "paper_book.json").read_text()).get("book") or label)
        except Exception:
            pass
        books.append((label, d))
    return books


def _read_book(p: Path) -> dict | None:
    try:
        data = json.loads(p.read_text())
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def real_bot_board(points: int = 360) -> dict:
    """Livro A no topo (compatível com a página antiga) e, se houver livro B (logs/paper_b), `books` com A e B."""
    root = real_bot_root()
    exp_p = root / "config" / "experiment.json"
    books = real_bot_books(root)
    dec_p = root / "logs" / "decisions.jsonl"
    if not exp_p.exists() and not dec_p.exists():
        return {"available": False, "reason": "sem logs do bot real nesta máquina"}
    key: list = []
    for _label, d in books:
        for p in (d / "decisions.jsonl", d / "paper_trades.jsonl", d / "paper_book.json"):
            try:
                st = p.stat(); key.append((str(p), st.st_size, st.st_mtime_ns))
            except FileNotFoundError:
                key.append((str(p), None))
    try:
        st = exp_p.stat(); key.append((st.st_size, st.st_mtime_ns))
    except FileNotFoundError:
        key.append(None)
    key.append(points)
    if _rb_cache["key"] == key:
        return _rb_cache["val"]
    try:
        S, load_experiment, parse_t = _import_score()
        exp = load_experiment(exp_p)
        boards = []
        for label, d in books:
            b = build_real_board(_jsonl(d / "decisions.jsonl"), _jsonl(d / "paper_trades.jsonl"), exp, S, parse_t,
                                 points=points, book=_read_book(d / "paper_book.json") or {"book": label})
            b["book"] = label
            b["log_dir"] = str(d.relative_to(root)) if d.is_relative_to(root) else str(d)
            b["available"] = True
            boards.append(b)
        out = dict(boards[0])
        if len(boards) > 1:
            out["books"] = boards
    except Exception as ex:
        out = {"available": False, "reason": f"placar indisponível: {ex!r}"[:300]}
    _rb_cache.update(key=key, val=out)
    return out


# ------------------------------------------------------------------ saúde: disco, reinícios, qualidade de fill

def restarts_since(log_path: Path, t0: float) -> dict[str, int]:
    """Contagem de 'starting <nome>' no supervisor.log desde t0 (mesma regra de scripts/summary.py)."""
    import re
    from datetime import datetime
    out: dict[str, int] = {}
    try:
        lines = log_path.read_text(errors="replace").splitlines()[-4000:]
    except Exception:
        return out
    for line in lines:
        m = re.match(r"(\S+) starting (\w+)", line)
        if m:
            try:
                if datetime.fromisoformat(m.group(1)).timestamp() >= t0:
                    out[m.group(2)] = out.get(m.group(2), 0) + 1
            except ValueError:
                pass
    return out


_hx_cache: dict[str, Any] = {"ts": 0.0, "val": None}


def health_extras(ttl: float = 120.0) -> dict:
    now_ts = time.time()
    if _hx_cache["val"] is not None and now_ts - _hx_cache["ts"] < ttl:
        return _hx_cache["val"]
    import shutil
    out: dict[str, Any] = {}
    try:
        du = shutil.disk_usage(str(ROOT))
        out["disk"] = {"free_gb": du.free / 1e9, "total_gb": du.total / 1e9, "used_frac": du.used / du.total if du.total else None}
    except Exception:
        out["disk"] = None
    out["restarts_24h"] = restarts_since(ROOT / "logs" / "supervisor.log", now_ts - 86400)
    try:
        from bot import analytics as A
        fq = A.fill_quality(now_ts - 86400, now_ts)
        out["fills_24h"] = {k: fq.get(k) for k in ("market_fills", "mark_fallbacks", "fallback_rate")}
        out["fills_24h"]["reasons"] = dict(sorted((fq.get("reasons") or {}).items(), key=lambda kv: -kv[1])[:4])
    except Exception as ex:
        out["fills_24h"] = {"error": repr(ex)[:200]}
    _hx_cache.update(ts=now_ts, val=out)
    return out


def tunnel_expected(root: Path, env: dict | None = None, which: Callable[[str], str | None] | None = None) -> bool:
    """O túnel público só é esperado quando não foi desligado (DISABLE_TUNNEL=1, como no macOS local) e existe um
    cloudflared para o supervisor arrancar (mesma regra de scripts/supervisor.sh e start_tunnel.sh)."""
    import shutil
    env = os.environ if env is None else env
    if str(env.get("DISABLE_TUNNEL", "0")).strip() == "1":
        return False
    which = which or shutil.which
    return (root / "dashboard" / "cloudflared").exists() or bool(which("cloudflared"))

