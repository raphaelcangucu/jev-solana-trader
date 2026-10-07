"""Leitura da simulação retroativa de 30 dias (data/backtest) para o dashboard v2. Sem FastAPI: testável com o .venv.

Contrato (escrito por scripts/backtest_30d.py):
  <base>/latest                      texto com o run_id mais recente
  <base>/<run_id>/summary.json       janela, ativos, vencedores, famílias, portfólios, bot real A × B
  <base>/<run_id>/equity/<nome>.json {"t": [epoch s], "equity": [...], "bh": [...]}
  <base>/<run_id>/report.md          relatório completo
  <base>/<run_id>/chart.json         (só runs de 180 dias) patrimônio normalizado (1000 = início) por benchmark, família,
                                     topo e bot real, mais o resumo por mês
  <base>/index.json                  histórico de runs (mensais de 30 dias e de 6 meses); se faltar, é montado dos summaries
  <base>/history.md                  relatório de comparação entre meses

Segurança de caminho: `run_id` só com [A-Za-z0-9_.-] e tem de ser uma pasta com summary.json dentro de <base>;
`nome` tem de estar na lista de portfólios do summary e o arquivo resolvido tem de ficar dentro de equity/.
SIMULAÇÃO: só leitura; nada aqui escreve em disco, lê chaves ou envia ordens.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
EMPTY_HINT = "Ainda não há simulação retroativa. Rode scripts/backtest_30d.py para gerar uma."


def _f(x, default=None):
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _read_json(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def backtest_dir(root: Path) -> Path:
    """<ROOT>/data/backtest, ou PAPER_LAB_BACKTEST_DIR (útil para abrir a fixture no painel local)."""
    env = os.environ.get("PAPER_LAB_BACKTEST_DIR")
    return Path(env).expanduser() if env else Path(root) / "data" / "backtest"


def valid_run_id(run_id: str | None) -> bool:
    return bool(run_id) and bool(RUN_ID_RE.match(run_id)) and ".." not in run_id  # type: ignore[arg-type]


def run_dir(base: Path, run_id: str | None) -> Path | None:
    """A pasta do run, só se o id for válido, existir dentro de base e tiver summary.json."""
    if not valid_run_id(run_id):
        return None
    base = Path(base).resolve()
    d = (base / str(run_id)).resolve()
    if d.parent != base or not (d / "summary.json").is_file():
        return None
    return d


def list_runs(base: Path) -> list[dict]:
    """Runs com summary.json, do mais novo para o mais antigo (pelo generated_brt, depois pelo nome)."""
    base = Path(base)
    if not base.is_dir():
        return []
    out = []
    for d in base.iterdir():
        if not d.is_dir() or not valid_run_id(d.name) or not (d / "summary.json").is_file():
            continue
        s = _read_json(d / "summary.json", {}) or {}
        w = s.get("window") or {}
        out.append({"run_id": d.name, "generated_brt": s.get("generated_brt"),
                    "start_brt": w.get("start_brt"), "end_brt": w.get("end_brt"), "days": w.get("days"),
                    "portfolios": len(s.get("portfolios") or [])})
    out.sort(key=lambda r: (str(r.get("generated_brt") or ""), r["run_id"]), reverse=True)
    return out


def latest_run_id(base: Path) -> str | None:
    """O id em <base>/latest se for válido; senão, o run mais novo que existir."""
    try:
        rid = (Path(base) / "latest").read_text().strip()
    except Exception:
        rid = ""
    if rid and run_dir(base, rid):
        return rid
    runs = list_runs(base)
    return runs[0]["run_id"] if runs else None


# ------------------------------------------------------------------ normalização

VERDICT = {"vencedora": "vencedora", "vencedor": "vencedora", "winner": "vencedora", "win": "vencedora",
           "perdedora": "perdedora", "perdedor": "perdedora", "loser": "perdedora", "lose": "perdedora",
           "inconclusiva": "inconclusiva", "inconclusivo": "inconclusiva", "inconclusive": "inconclusiva"}


def norm_verdict(v) -> str:
    return VERDICT.get(str(v or "").strip().lower(), "inconclusiva")


def _derive(p: dict) -> dict:
    """Campos derivados que a UI usa (sem tocar nos originais): vs. segurar em %, habilidade em %, veredito normalizado.
    `vs_bh` e `skill` são em US$ (como no placar ao vivo); só segurar valeria end_value − vs_bh."""
    q = dict(p)
    end, start, vs = _f(p.get("end_value")), _f(p.get("start_value")), _f(p.get("vs_bh"))
    if q.get("vs_bh_pct") is None:
        bh = (end - vs) if (end is not None and vs is not None) else None
        q["vs_bh_pct"] = ((end / bh - 1) * 100) if (bh and bh > 0) else None
    if q.get("skill_pct") is None:
        sk = _f(p.get("skill"))
        q["skill_pct"] = (sk / start * 100) if (sk is not None and start) else None
    q["verdict"] = norm_verdict(p.get("verdict"))
    return q


MetaFn = Callable[[dict], dict]


def enrich_summary(summary: dict, meta_fn: MetaFn | None = None, live_index: dict[str, str] | None = None) -> dict:
    """Cópia do summary com cada portfólio enriquecido: metadados de descrição (os mesmos do placar), nome ao vivo
    (`live_name`, ou None se esse teste não existe no run ao vivo) e campos derivados."""
    live_index = live_index or {}
    out = dict(summary)
    ports = []
    for p in summary.get("portfolios") or []:
        if not isinstance(p, dict) or not p.get("name"):
            continue
        q = _derive(p)
        if meta_fn:
            try:
                meta = meta_fn(p) or {}
            except Exception:
                meta = {}
            for k, v in meta.items():
                if q.get(k) in (None, "", [], {}):
                    q[k] = v
        name = str(p["name"])
        q["live_name"] = live_index.get(name) or (live_index.get(name[5:]) if name.startswith("meme_") else None)
        ports.append(q)
    out["portfolios"] = ports
    out["realbot"] = [b for b in (summary.get("realbot") or []) if isinstance(b, dict)]
    out["families"] = [f for f in (summary.get("families") or []) if isinstance(f, dict)]
    return out


# ------------------------------------------------------------------ séries

def _series(d: dict) -> tuple[list[float], list[float | None], list[float | None]]:
    t = d.get("t") or []
    e = d.get("equity") or []
    b = d.get("bh") or []
    n = min(len(t), len(e))
    ts, es, bs = [], [], []
    for i in range(n):
        tt, ee = _f(t[i]), _f(e[i])
        if tt is None or ee is None:
            continue
        ts.append(tt); es.append(ee); bs.append(_f(b[i]) if i < len(b) else None)
    return ts, es, bs


def _pick(n_in: int, n: int) -> list[int]:
    if n_in <= n:
        return list(range(n_in))
    step = (n_in - 1) / (n - 1)
    return sorted({round(i * step) for i in range(n)})


def equity_payload(d: dict, points: int = 1500) -> dict:
    ts, es, bs = _series(d)
    idx = _pick(len(ts), max(2, points))
    return {"t": [int(ts[i]) for i in idx], "equity": [round(es[i], 6) for i in idx], "bh": [bs[i] for i in idx]}


def spark_of(d: dict, n: int = 60) -> dict | None:
    """Mesmo formato das sparklines ao vivo: % desde o início para a carteira (v) e para só segurar (h)."""
    ts, es, bs = _series(d)
    if len(ts) < 2 or not es[0]:
        return None
    idx = _pick(len(ts), max(2, n))
    e0 = es[0]
    b0 = next((b for b in bs if b), None)
    return {"t": [int(ts[i]) for i in idx],
            "v": [round((es[i] / e0 - 1) * 100, 4) for i in idx],
            "h": [round(((bs[i] or b0) / b0 - 1) * 100, 4) if b0 else None for i in idx]}


def portfolio_names(summary: dict) -> set[str]:
    return {str(p.get("name")) for p in (summary.get("portfolios") or []) if isinstance(p, dict) and p.get("name")}


def equity_file(base: Path, run_id: str, name: str, summary: dict | None = None) -> Path | None:
    """Arquivo de curva de um portfólio do run, ou None (id/nome inválidos, fora da pasta, ou sem arquivo)."""
    d = run_dir(base, run_id)
    if d is None:
        return None
    summary = summary if summary is not None else (_read_json(d / "summary.json", {}) or {})
    if name not in portfolio_names(summary):
        return None
    eq_dir = (d / "equity").resolve()
    f = (eq_dir / f"{name}.json").resolve()
    if f.parent != eq_dir or not f.is_file():
        return None
    return f


def report_file(base: Path, run_id: str) -> Path | None:
    d = run_dir(base, run_id)
    if d is None:
        return None
    f = d / "report.md"
    return f if f.is_file() else None


# ------------------------------------------------------------------ histórico: índice, gráfico de 6 meses, comparação

TOP_N = 5


def run_kind(run_id: str, days) -> str:
    """'180d' para janelas longas (≥ 60 dias ou id bt180_*; o gerador escreve "<N>d"), senão '30d' (os meses)."""
    d = _f(days)
    if str(run_id).startswith("bt180") or (d is not None and d >= 60):
        return "180d"
    return "30d"


def index_entry(run_id: str, s: dict) -> dict:
    """Uma linha do index.json a partir de um summary (mesmo contrato que o gerador escreve)."""
    w = s.get("window") or {}
    ports = [p for p in (s.get("portfolios") or []) if isinstance(p, dict) and p.get("name")]
    verdicts = [norm_verdict(p.get("verdict")) for p in ports]
    win = s.get("winner") or {}

    def top(key: str) -> list[dict]:
        rows = [p for p in ports if _f(p.get(key)) is not None]
        rows.sort(key=lambda p: _f(p.get(key)), reverse=True)  # type: ignore[arg-type, return-value]
        return [{"name": p["name"], "skill": _f(p.get("skill")), "pnl_pct": _f(p.get("pnl_pct"))} for p in rows[:TOP_N]]

    return {
        "run_id": run_id, "kind": run_kind(run_id, w.get("days")),
        "start_brt": w.get("start_brt"), "end_brt": w.get("end_brt"), "days": w.get("days"),
        "generated_brt": s.get("generated_brt"), "n_portfolios": len(ports),
        "n_winners": verdicts.count("vencedora"), "n_losers": verdicts.count("perdedora"),
        "n_inconclusive": verdicts.count("inconclusiva"),
        "winner": {k: win.get(k) for k in ("by_skill", "by_pnl", "by_verdict")},
        "top_skill": top("skill"), "top_pnl": top("pnl_pct"),
        "realbot": [{"book": b.get("book"), "pnl_pct": _f(b.get("pnl_pct")), "vs_hold": _f(b.get("vs_hold"))}
                    for b in (s.get("realbot") or []) if isinstance(b, dict)],
        "assets": {str(k): _f((v or {}).get("ret_pct")) if isinstance(v, dict) else _f(v) for k, v in (s.get("assets") or {}).items()},
        "look_ahead_forks": [p["name"] for p in ports if p.get("look_ahead")],
    }


def _end_key(r: dict) -> tuple:
    return (str(r.get("end_brt") or ""), str(r.get("generated_brt") or ""), str(r.get("run_id")))


def build_index(base: Path, index: dict | None = None) -> dict:
    """index.json validado (só ids seguros; `available` diz se a pasta do run existe), completado com os runs que
    existem em disco e não estão no índice. Sem index.json, é montado inteiro dos summaries. Ordem: fim mais recente primeiro."""
    base = Path(base)
    raw = index if index is not None else _read_json(base / "index.json", None)
    source = "index" if isinstance(raw, dict) and isinstance(raw.get("runs"), list) else "runs"
    runs: list[dict] = []
    seen: set[str] = set()
    if source == "index":
        for r in raw["runs"]:  # type: ignore[index]
            if not isinstance(r, dict) or not valid_run_id(r.get("run_id")) or r["run_id"] in seen:
                continue
            q = dict(r)
            q["kind"] = q.get("kind") if q.get("kind") in ("30d", "180d") else run_kind(q["run_id"], q.get("days"))
            q["available"] = run_dir(base, q["run_id"]) is not None
            runs.append(q); seen.add(q["run_id"])
    for r in list_runs(base):
        if r["run_id"] in seen:
            continue
        s = _read_json(base / r["run_id"] / "summary.json", None)
        if isinstance(s, dict):
            q = index_entry(r["run_id"], s)
            q["available"] = True
            runs.append(q); seen.add(r["run_id"])
    runs.sort(key=_end_key, reverse=True)
    return {"runs": runs, "source": source, "latest": latest_run_id(base),
            "has_history": (base / "history.md").is_file()}


def _clean(v):
    """NaN/inf viram None (o JSON da API não aceita NaN)."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    return v


SERIES_GROUPS = ("benchmarks", "families", "top", "realbot")


def chart_payload(d: dict, points: int = 2000) -> dict:
    """chart.json com todas as séries alinhadas ao mesmo `t`, reduzidas aos mesmos índices quando passam de `points`."""
    t = [x for x in (d.get("t") or [])]
    n = len(t)
    idx = _pick(n, max(2, points))
    out: dict[str, Any] = {"t": [int(_f(t[i], 0)) for i in idx]}  # type: ignore[arg-type]
    for g in SERIES_GROUPS:
        grp = d.get(g) or {}
        out[g] = {}
        if not isinstance(grp, dict):
            continue
        for name, arr in grp.items():
            if not isinstance(arr, list):
                continue
            if arr and not any(isinstance(x, (int, float)) and not isinstance(x, bool) for x in arr):
                out[g][str(name)] = arr  # metadado, não série (ex.: benchmarks.memes_in_basket = ["WIF", …])
                continue
            out[g][str(name)] = [_f(arr[i]) if i < len(arr) else None for i in idx]
    out["monthly"] = [m for m in (d.get("monthly") or []) if isinstance(m, dict)]
    for k, v in d.items():  # campos extras (notas, unidades) passam como vieram
        if k not in out and k not in SERIES_GROUPS:
            out[k] = v
    return _clean(out)


def chart_file(base: Path, run_id: str) -> Path | None:
    d = run_dir(base, run_id)
    if d is None:
        return None
    f = d / "chart.json"
    return f if f.is_file() else None


def history_file(base: Path) -> Path | None:
    f = Path(base) / "history.md"
    return f if f.is_file() else None


# ------------------------------------------------------------------ fachada com cache

class BacktestView:
    """Lê <base> sob demanda e guarda o summary enriquecido por (run_id, mtime do summary)."""

    def __init__(self, base_fn: Callable[[], Path], meta_factory: Callable[[], MetaFn | None] | None = None,
                 live_index_fn: Callable[[], dict[str, str]] | None = None, ttl: float = 120.0):
        """`meta_factory` é chamado uma vez por reconstrução e devolve a função de metadados por portfólio."""
        self.base_fn, self.meta_factory, self.live_index_fn, self.ttl = base_fn, meta_factory, live_index_fn, ttl
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[Any, float, dict]] = {}
        self._sparks: dict[tuple, dict] = {}

    @property
    def base(self) -> Path:
        return Path(self.base_fn())

    def _summary_raw(self, run_id: str) -> dict | None:
        d = run_dir(self.base, run_id)
        if d is None:
            return None
        s = _read_json(d / "summary.json", None)
        return s if isinstance(s, dict) else None

    def summary(self, run_id: str) -> dict | None:
        d = run_dir(self.base, run_id)
        if d is None:
            return None
        try:
            key = (d / "summary.json").stat().st_mtime_ns
        except OSError:
            return None
        with self._lock:
            c = self._cache.get(run_id)
            if c and c[0] == key and time.time() - c[1] < self.ttl:
                return c[2]
        raw = self._summary_raw(run_id)
        if raw is None:
            return None
        try:
            live = self.live_index_fn() if self.live_index_fn else {}
        except Exception:
            live = {}
        try:
            meta_fn = self.meta_factory() if self.meta_factory else None
        except Exception:
            meta_fn = None
        s = enrich_summary(raw, meta_fn, live)
        with self._lock:
            self._cache[run_id] = (key, time.time(), s)
        return s

    def payload(self, run_id: str | None = None) -> dict:
        base = self.base
        runs = list_runs(base)
        if run_id is not None and not run_dir(base, run_id):
            return {"available": False, "reason": "run desconhecido", "hint": EMPTY_HINT, "runs": runs, "run_id": None, "latest": latest_run_id(base)}
        rid = run_id or latest_run_id(base)
        s = self.summary(rid) if rid else None
        if not rid or s is None:
            return {"available": False, "reason": "sem simulação retroativa", "hint": EMPTY_HINT, "runs": runs, "run_id": None, "latest": None}
        return {"available": True, "run_id": rid, "latest": latest_run_id(base), "runs": runs,
                "has_report": report_file(base, rid) is not None, "summary": s}

    def equity(self, run_id: str, name: str, points: int = 1500) -> dict | None:
        s = self._summary_raw(run_id)
        if s is None:
            return None
        f = equity_file(self.base, run_id, name, s)
        if f is None:
            return None
        d = _read_json(f, None)
        if not isinstance(d, dict):
            return None
        return equity_payload(d, max(50, min(int(points), 3000)))

    def sparks(self, run_id: str, n: int = 60) -> dict | None:
        d = run_dir(self.base, run_id)
        s = self._summary_raw(run_id) if d else None
        if s is None:
            return None
        n = max(12, min(int(n), 240))
        key = (run_id, n, (d / "summary.json").stat().st_mtime_ns)  # type: ignore[union-attr]
        with self._lock:
            if key in self._sparks:
                return self._sparks[key]
        out = {}
        for name in sorted(portfolio_names(s)):
            f = equity_file(self.base, run_id, name, s)
            sp = spark_of(_read_json(f, {}) or {}, n) if f else None
            if sp:
                out[name] = sp
        with self._lock:
            self._sparks = {k: v for k, v in self._sparks.items() if k[0] != run_id}
            self._sparks[key] = out
        return out

    def report(self, run_id: str) -> str | None:
        f = report_file(self.base, run_id)
        if f is None:
            return None
        try:
            return f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def _index_key(self, base: Path) -> tuple:
        parts: list = []
        for f in [base / "index.json", base / "latest", base / "history.md"]:
            try:
                parts.append(f.stat().st_mtime_ns)
            except OSError:
                parts.append(None)
        if base.is_dir():
            for d in sorted(base.iterdir()):
                try:
                    parts.append((d.name, (d / "summary.json").stat().st_mtime_ns))
                except OSError:
                    pass
        return tuple(parts)

    def index(self) -> dict:
        """Histórico de runs (index.json ou montado dos summaries), com cache pelo mtime dos arquivos."""
        base = self.base
        key = ("__index__", self._index_key(base))
        with self._lock:
            c = self._cache.get("__index__")
            if c and c[0] == key and time.time() - c[1] < self.ttl:
                return c[2]
        out = build_index(base)
        with self._lock:
            self._cache["__index__"] = (key, time.time(), out)
        return out

    def chart(self, run_id: str, points: int = 2000) -> dict | None:
        f = chart_file(self.base, run_id)
        if f is None:
            return None
        d = _read_json(f, None)
        if not isinstance(d, dict) or not isinstance(d.get("t"), list):
            return None
        out = chart_payload(d, max(50, min(int(points), 5000)))
        out["run_id"] = run_id
        return out

    def history(self) -> str | None:
        f = history_file(self.base)
        if f is None:
            return None
        try:
            return f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None


# ------------------------------------------------------------------ metadados do lab ao vivo (usados pelo api_v2)

def live_meta_fn(items: Iterable[dict], registry: dict, originals: dict,
                 row_meta: Callable[..., dict], params_brief: Callable[[str], dict | None]) -> MetaFn:
    """Os mesmos metadados que o placar manda para describePortfolio (perfil, hipótese, pai, diff do fork, params_brief),
    procurando o portfólio pelo nome ou pelo nome de catálogo; o que não existe ao vivo usa o registry/originais."""
    by_name = {it["name"]: it for it in items}
    by_cat = {(it.get("meta") or {}).get("catalog"): it for it in by_name.values()}
    reg = (registry or {}).get("portfolios") or {}

    def fn(p: dict) -> dict:
        name = str(p.get("name"))
        it = by_name.get(name) or by_cat.get(name) or (by_name.get(name[5:]) if name.startswith("meme_") else None)
        if it:
            meta = dict(it.get("meta") or {})
            meta.update({k: it.get(k) for k in ("hyp", "label", "parent", "model", "kind") if it.get(k) is not None})
        else:
            e = reg.get(name)
            group = "lab" if e else ("sol" if (p.get("asset") or "SOL") == "SOL" else "meme")
            meta = dict(row_meta(name, group, e, originals) or {})
            if e:
                meta.update({k: e.get(k) for k in ("hyp", "label", "parent") if e.get(k) is not None})
        meta["params_brief"] = params_brief(meta.get("catalog") or name)
        return {k: v for k, v in meta.items() if v is not None}
    return fn


def live_index(universe_items: Iterable[dict]) -> dict[str, str]:
    """nome ou nome de catálogo → nome da linha no placar ao vivo."""
    out: dict[str, str] = {}
    for it in universe_items:
        out[it["name"]] = it["name"]
        cat = (it.get("meta") or {}).get("catalog")
        if cat:
            out.setdefault(cat, it["name"])
    return out
