"""Dashboard v2 API (read-mostly JSON + SSE). SIMULATION ONLY — no swaps, no keys.

Mounted by dashboard/app.py via make_router(). All routes sit behind the same HTTP Basic auth.
Never touches keypair.json / secret.b58. Writes only happen through the legacy control endpoints
(/api/params/*, /api/bots/*, /api/models/*) that app.py already exposes.
"""
from __future__ import annotations

import asyncio, glob, json, math, os, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

import sys as _sys_paths
_LAB = str(Path(__file__).resolve().parents[1])  # código do lab (research/paper-lab)
if _LAB not in _sys_paths.path:
    _sys_paths.path.insert(0, _LAB)
from bot.paths import ROOT, LAB_DIR  # noqa: E402  (ROOT = PAPER_LAB_ROOT ou a pasta do lab)
_DASH = str(Path(__file__).resolve().parent)
if _DASH not in _sys_paths.path:
    _sys_paths.path.insert(0, _DASH)
import insights as INS  # noqa: E402  (habilidade sem beta, sparklines, experimento, bot real — sem FastAPI)
import backtest_view as BT  # noqa: E402  (simulação retroativa de 30 dias, data/backtest — sem FastAPI)
SKILL = INS.SkillCache()
FUND = ROOT / "funding"
BRT = timezone(timedelta(hours=-3))
FUNDING_SHOWN = ("p1000", "p1000_pons")  # user: show only the $1000 funding portfolios
FUNDING_USDC_BAR = 0.06  # 6% USDC bar (strategy rule) — Kamino measured APY shown separately

# ---------------------------------------------------------------- helpers

def now() -> float:
    return time.time()


def brt_iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or now(), tz=BRT).isoformat(timespec="seconds")


def read_json(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def fnum(x, default=None):
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def stat_key(p: Path):
    try:
        st = p.stat()
        return (st.st_ino, st.st_size, st.st_mtime_ns)
    except FileNotFoundError:
        return None


_parse_cache: dict[str, tuple[Any, list]] = {}


def jsonl_rows(p: Path) -> list[dict]:
    """Whole live JSONL file, parsed and cached by (inode,size,mtime)."""
    p = Path(p)
    k = stat_key(p)
    if k is None:
        return []
    c = _parse_cache.get(str(p))
    if c and c[0] == k:
        return c[1]
    rows = []
    with open(p, "rb") as f:
        for line in f:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    _parse_cache[str(p)] = (k, rows)
    return rows


def tail_rows(p: Path, n: int) -> list[dict]:
    p = Path(p)
    if not p.exists():
        return []
    with open(p, "rb") as f:
        f.seek(0, 2); size = f.tell(); block = min(size, max(8192, n * 1600)); f.seek(size - block)
        data = f.read()
    lines = data.split(b"\n")
    if block < size:
        lines = lines[1:]
    out = []
    for l in lines[-n:]:
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def row_ts(r: dict) -> float | None:
    t = r.get("ts")
    if isinstance(t, (int, float)):
        return float(t)
    if r.get("ts_ms"):
        return float(r["ts_ms"]) / 1000.0
    if isinstance(t, str):
        try:
            return datetime.fromisoformat(t).timestamp()
        except Exception:
            return None
    return None


def downsample(rows: list, n: int) -> list:
    if len(rows) <= n:
        return rows
    step = len(rows) / n
    out = [rows[int(i * step)] for i in range(n)]
    if out[-1] is not rows[-1]:
        out.append(rows[-1])
    return out


def _pid_running(pid: int) -> bool:
    """Portável (Linux e macOS): sinal 0 só testa a existência do processo."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def pid_info(pidfile: Path, name: str) -> dict:
    try:
        pid = int(pidfile.read_text().strip())
        return {"name": name, "pid": pid, "running": _pid_running(pid)}
    except Exception:
        return {"name": name, "pid": None, "running": False}


def today_start_ts() -> float:
    d = datetime.now(tz=BRT)
    return d.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


# ------------------------------------------------ incremental equity stats (max DD over full history)

class EqStats:
    __slots__ = ("ino", "offset", "first", "last", "peak", "max_dd", "n")

    def __init__(self):
        self.ino = None; self.offset = 0; self.first = None; self.last = None
        self.peak = None; self.max_dd = 0.0; self.n = 0

    def feed(self, r: dict):
        e = fnum(r.get("equity"))
        if e is None:
            return
        if self.first is None:
            self.first = r
        self.last = r; self.n += 1
        if self.peak is None or e > self.peak:
            self.peak = e
        if self.peak and self.peak > 0:
            dd = (self.peak - e) / self.peak * 100.0
            if dd > self.max_dd:
                self.max_dd = dd


_eq_stats: dict[str, EqStats] = {}


def eq_stats(p: Path) -> EqStats | None:
    p = Path(p)
    try:
        st = p.stat()
    except FileNotFoundError:
        _eq_stats.pop(str(p), None)
        return None
    s = _eq_stats.get(str(p))
    if s is None or s.ino != st.st_ino or st.st_size < s.offset:
        # new file or rotated: rebuild from archives + live (logio merges without dupes)
        s = EqStats()
        try:
            import sys
            if str(LAB_DIR) not in sys.path:
                sys.path.insert(0, str(LAB_DIR))
            from bot import logio  # type: ignore
            for r in logio.iter_rows(p):
                s.feed(r)
        except Exception:
            pass
        s.ino = st.st_ino; s.offset = st.st_size
        if s.n == 0:  # fallback: plain read
            for r in jsonl_rows(p):
                s.feed(r)
        _eq_stats[str(p)] = s
        return s
    if st.st_size > s.offset:
        with open(p, "rb") as f:
            f.seek(s.offset)
            data = f.read()
        cut = data.rfind(b"\n")
        if cut >= 0:
            for line in data[:cut].split(b"\n"):
                if line.strip():
                    try:
                        s.feed(json.loads(line))
                    except Exception:
                        pass
            s.offset += cut + 1
    return s


# ------------------------------------------------ portfolio universe

MEME_STRATS = ["baseline", "relaxed", "laya_baseline", "laya_relaxed", "poorjev_baseline", "poorjev_relaxed",
               "hybrid_poorjev_regime", "rule_regime", "rule_donch_regime", "rule_regime_full", "rule_donch_regime_full"]

STRAT_LABELS = {
    "baseline": "von baseline", "relaxed": "von relaxed", "laya_baseline": "laya baseline", "laya_relaxed": "laya relaxed",
    "poorjev_baseline": "poorjev baseline", "poorjev_relaxed": "poorjev relaxed", "hybrid_poorjev_regime": "híbrido poorjev+regime",
    "rule_regime": "regra regime", "rule_donch_regime": "regra Donchian+regime", "rule_regime_full": "regime (full)",
    "rule_donch_regime_full": "Donchian+regime (full)", "h1_exits": "H1 saídas", "h2_ensemble": "H2 ensemble",
}


def sol_model_of(name: str, st: dict) -> str:
    if name in ("baseline", "relaxed", "v2"):
        return "von"
    if name.startswith("hybrid_"):
        return "von+rules"
    if name.startswith(("grid_", "rsi_")):
        return "rule"
    return (st.get("model") or name.split("_")[0])


def meme_syms() -> list[str]:
    m = read_json(ROOT / "memecoins.json", {}) or {}
    return [t["symbol"] for t in (m.get("tokens") or []) if t.get("symbol")]


def universe() -> list[dict]:
    items: list[dict] = []
    status = read_json(ROOT / "status.json", {}) or {}
    orig = INS.originals_meta()
    for f in sorted(glob.glob(str(ROOT / "data" / "portfolio_*.json"))):
        name = Path(f).stem[len("portfolio_"):]
        items.append({"name": name, "group": "sol", "asset": "SOL", "file": f,
                      "equity_file": str(ROOT / "data" / f"equity_{name}.jsonl"),
                      "model": sol_model_of(name, status.get(name) or {}),
                      "kind": "rule" if name.startswith(("grid_", "rsi_")) else ("hybrid" if name.startswith("hybrid_") else "model"),
                      "strategy": name, "meta": INS.row_meta(name, "sol", None, orig)})
    syms = meme_syms()
    for f in sorted(glob.glob(str(ROOT / "data" / "meme" / "portfolios" / "*.json"))):
        stem = Path(f).stem
        sym = next((s for s in syms if stem.startswith(s + "_")), stem.split("_")[0])
        strat = stem[len(sym) + 1:]
        model = "von" if strat in ("baseline", "relaxed") else ("rule" if strat.startswith("rule_") else
                ("poorjev+regime" if strat.startswith("hybrid_") else strat.split("_")[0]))
        items.append({"name": stem, "group": "meme", "asset": sym, "file": f,
                      "equity_file": str(ROOT / "data" / "meme" / "equity" / f"{stem}.jsonl"),
                      "model": model, "kind": "rule" if strat.startswith("rule_") else ("hybrid" if strat.startswith("hybrid_") else "model"),
                      "strategy": strat, "meta": INS.row_meta(stem, "meme", None, orig)})
    reg = read_json(ROOT / "data" / "lab" / "registry.json", {}) or {}
    for name, e in (reg.get("portfolios") or {}).items():
        asset = e.get("asset") or "SOL"
        strat = e.get("hyp") or "fork"
        items.append({"name": name, "group": "lab", "asset": asset, "file": str(ROOT / "data" / "lab" / "portfolios" / f"{name}.json"),
                      "equity_file": str(ROOT / "data" / "lab" / "equity" / f"{name}.jsonl"),
                      "model": e.get("model") or e.get("kind"), "kind": e.get("kind"), "strategy": strat, "hyp": e.get("hyp"),
                      "label": e.get("label"), "parent": e.get("parent"), "lineage": e.get("lineage"),
                      "report_label": e.get("report_label"), "status": e.get("status"),
                      "meta": INS.row_meta(name, "lab", e, orig)})
    return items


def verdict_for(verdicts: dict, it: dict, pname: str | None):
    for k in (it["name"], pname, f"meme_{it['name']}"):
        if k and k in verdicts:
            return verdicts[k]
    return None


def portfolio_row(it: dict, verdicts: dict, overlay_ports: dict, control_names: set, skill: dict | None = None) -> dict:
    pdata = read_json(Path(it["file"]), {}) or {}
    s = eq_stats(Path(it["equity_file"]))
    last = (s.last if s else None) or {}
    first = (s.first if s else None) or {}
    eq = fnum(last.get("equity"))
    price = fnum(last.get("price"))
    qty = fnum(last.get("sol")) if it["asset"] == "SOL" else fnum(last.get("token"))
    if qty is None:
        qty = fnum(pdata.get("sol") if it["asset"] == "SOL" else pdata.get("token"), 0.0)
    if eq is None:
        eq = fnum(pdata.get("usdt"), 0.0) + (qty or 0.0) * (price or fnum(pdata.get("start_price"), 0.0) or 0.0)
    start_value = fnum((pdata.get("benchmark_all_usdt") or {}).get("usdt")) or fnum(first.get("all_usdt_equity")) or fnum(first.get("equity"))
    bh = fnum(last.get("bh_equity"))
    usdt_bench = fnum(last.get("all_usdt_equity")) or start_value
    started_ts = fnum(pdata.get("created_ts")) or row_ts(first) if first else fnum(pdata.get("created_ts"))
    started_brt = pdata.get("started_brt") or (brt_iso(started_ts) if started_ts else None)
    v = verdict_for(verdicts, it, pdata.get("name")) or {}
    prog = v.get("progress") or {}
    ctrl = it["name"] if it["name"] in control_names else None
    paused = bool((overlay_ports.get(ctrl) or {}).get("paused")) if ctrl else None
    row = {
        "name": it["name"], "group": it["group"], "asset": it["asset"], "model": it.get("model"), "kind": it.get("kind"),
        "strategy": it.get("strategy"), "hyp": it.get("hyp"), "label": it.get("label"), "parent": it.get("parent"),
        "lineage": it.get("lineage"), "report_label": it.get("report_label"),
        "equity": eq, "start_value": start_value,
        "pnl": (eq - start_value) if (eq is not None and start_value) else None,
        "pnl_pct": ((eq / start_value - 1) * 100) if (eq is not None and start_value) else None,
        "vs_bh": (eq - bh) if (eq is not None and bh is not None) else None,
        "vs_bh_pct": ((eq / bh - 1) * 100) if (eq is not None and bh) else None,
        "vs_usdt": (eq - usdt_bench) if (eq is not None and usdt_bench) else None,
        "bh_equity": bh, "trades": last.get("trade_count", pdata.get("trade_count", 0)),
        "exposure_pct": ((qty or 0) * (price or 0) / eq * 100) if (eq and price) else None,
        "max_dd_pct": s.max_dd if s else None,
        "points": s.n if s else 0, "last_ts": row_ts(last) if last else None,
        "started_brt": started_brt, "started_ts": started_ts,
        "verdict": v.get("verdict") or "inconclusivo", "verdict_reason": v.get("reason"),
        "progress_text": prog.get("text"),
        "progress": {"closed_rt": prog.get("closed_rt"), "min_closed_rt": prog.get("min_closed_rt"),
                     "days": prog.get("days"), "min_days": prog.get("min_days")} if prog else None,
        "control": ctrl, "paused": paused,
    }
    meta = it.get("meta") or {}
    row.update({k: meta.get(k) for k in ("catalog", "profile", "test_type", "variant", "rule", "source", "params_diff", "created_brt",
                                         "fork_who", "fork_summary", "fork_reason", "criteria_summary")})
    row["skill"] = (skill or {}).get(meta.get("catalog") or it["name"])
    row["params_brief"] = INS.params_brief(meta.get("catalog") or it["name"])
    return row


# ------------------------------------------------ trades / markers

def trade_logs() -> list[Path]:
    return [ROOT / "logs" / "trades.jsonl", ROOT / "logs" / "meme_trades.jsonl"]


def norm_trade(r: dict) -> dict:
    fill = r.get("fill") or {}
    mark = fnum(fill.get("mark_price")) or fnum(r.get("price_mark"))
    eff = fnum(fill.get("effective_price"))
    side = r.get("side") or fill.get("side")
    if eff is None:
        usdt_in = fnum(fill.get("usdt_in")); usdt_out = fnum(fill.get("usdt_out")) or fnum(fill.get("usdt_out_net"))
        q_out = fnum(fill.get("sol_out_net")) or fnum(fill.get("token_out_net"))
        q_in = fnum(fill.get("sol_in")) or fnum(fill.get("token_in"))
        if side == "buy" and usdt_in and q_out:
            eff = usdt_in / q_out
        elif side == "sell" and usdt_out and q_in:
            eff = usdt_out / q_in
    slip = None
    if eff and mark:
        slip = (eff / mark - 1) * 1e4 * (1 if side == "buy" else -1)  # +bps = worse than mark
    return {"ts": row_ts(r), "ts_brt": r.get("ts_brt"), "portfolio": r.get("portfolio"), "side": side,
            "mark": mark, "fill_price": eff, "slippage_bps": slip,
            "fill_mode": fill.get("fill_mode") or (r.get("quote") or {}).get("fill_mode"),
            "quote_error": fill.get("quote_error"), "strategy": r.get("strategy"),
            "usdt": fnum(fill.get("usdt_in")) or fnum(fill.get("usdt_out")) or fnum(fill.get("usdt_out_net")),
            "fee_usdt": fnum(fill.get("fee_usdt")), "mint": fill.get("mint"),
            "equity_after": fnum((r.get("portfolio_after") or {}).get("equity"))}


def all_trades() -> list[dict]:
    out = []
    for p in trade_logs():
        for r in jsonl_rows(p):
            out.append(r)
    return out


def trade_matches_asset(r: dict, asset: str, mint: str | None) -> bool:
    pname = r.get("portfolio") or ""
    fill = r.get("fill") or {}
    if asset == "SOL":
        return "token_out_net" not in fill and "token_in" not in fill and not fill.get("mint")
    if mint and fill.get("mint") == mint:
        return True
    return f"_{asset}_" in f"_{pname}_"


# ------------------------------------------------ candles

def price_file(asset: str) -> Path:
    return ROOT / "data" / "prices.jsonl" if asset == "SOL" else ROOT / "data" / "meme" / "prices" / f"{asset}.jsonl"


def build_candles(asset: str, res: int, hours: float):
    since = now() - hours * 3600
    rows = [r for r in jsonl_rows(price_file(asset)) if (row_ts(r) or 0) >= since and fnum(r.get("price_usd"))]
    buckets: dict[int, list] = {}
    for r in rows:
        t = int(row_ts(r) // res * res); px = fnum(r["price_usd"])
        b = buckets.get(t)
        if b is None:
            buckets[t] = [px, px, px, px, 1]
        else:
            b[1] = max(b[1], px); b[2] = min(b[2], px); b[3] = px; b[4] += 1
    return [{"time": t, "open": b[0], "high": b[1], "low": b[2], "close": b[3], "ticks": b[4]} for t, b in sorted(buckets.items())]


# ------------------------------------------------ router factory

def make_router(require_auth: Callable, deps: dict) -> APIRouter:
    r = APIRouter(prefix="/api/v2")
    A = Depends(require_auth)

    def control_names() -> set:
        try:
            return set(deps["portfolio_names"]())
        except Exception:
            return set()

    def overlay_ports() -> dict:
        try:
            return (deps["load_overlay"]().get("portfolios") or {})
        except Exception:
            return {}

    def verdicts_all() -> dict:
        return (read_json(ROOT / "data" / "nightly" / "verdicts.json", {}) or {}).get("verdicts") or {}

    def rows_all() -> list[dict]:
        ver = verdicts_all(); ov = overlay_ports(); cn = control_names(); sk = SKILL.get()
        return [portfolio_row(it, ver, ov, cn, sk) for it in universe()]

    # ---------- health
    def health_payload() -> dict:
        t = now()
        def age_of(p: Path, key="ts"):
            d = read_json(p, {}) or {}
            ts = fnum(d.get(key))
            return (t - ts) if ts else None, d
        sol_age, sol = age_of(ROOT / "status.json")
        meme_age, meme = age_of(ROOT / "data" / "meme" / "status.json")
        rules_age, rules = age_of(ROOT / "data" / "rules" / "status.json")
        lab_age, lab = age_of(ROOT / "data" / "lab" / "status.json")
        ng_age, ng = age_of(ROOT / "data" / "nightly" / "status.json")
        fs = read_json(FUND / "data" / "status.json", {}) or {}
        f_age = (t - fnum(fs.get("heartbeat_ms"), 0) / 1000.0) if fs.get("heartbeat_ms") else None
        names = ["supervisor", "von", "laya", "poorjev", "sol", "meme", "rules", "lab", "nightly", "dashboard", "tunnel"]
        procs = [pid_info(ROOT / "run" / f"{n}.pid", n) for n in names]
        fp = FUND / "run" / "funding.pid"
        if fp.exists():
            procs.append(pid_info(fp, "funding"))
        models = read_json(ROOT / "models.json", {}) or {}
        # expected-but-down: model servers disabled in models.json are not "errors"
        disabled = {m for m, b in (models.get("backends") or {}).items() if not b.get("enabled")}
        tunnel_on = INS.tunnel_expected(ROOT)
        for p in procs:
            p["expected"] = p["name"] not in disabled and (p["name"] != "tunnel" or tunnel_on or p["running"])
        beats = [
            {"name": "sol_bot", "age_s": sol_age, "ts_brt": sol.get("ts_brt"), "cycles": sol.get("cycles"), "errors": sol.get("errors")},
            {"name": "meme_bot", "age_s": meme_age, "ts_brt": meme.get("ts_brt"), "cycles": meme.get("cycles"), "errors": meme.get("errors")},
            {"name": "rules_bot", "age_s": rules_age, "ts_brt": rules.get("ts_brt"), "cycles": rules.get("cycles"), "errors": rules.get("errors")},
            {"name": "lab_bot", "age_s": lab_age, "ts_brt": lab.get("ts_brt"), "cycles": lab.get("cycles"), "errors": lab.get("errors")},
            {"name": "nightly", "age_s": ng_age, "ts_brt": ng.get("ts_brt"), "cycles": None, "errors": None},
        ]
        if fs:
            beats.append({"name": "funding", "age_s": f_age, "ts_brt": fs.get("heartbeat"), "cycles": None,
                          "errors": 1 if fs.get("last_error") else 0})
        errors = sum(int(b["errors"] or 0) for b in beats)
        stale = [b["name"] for b in beats if b["name"] != "nightly" and (b["age_s"] is None or b["age_s"] > 180)]
        down = [p["name"] for p in procs if p["expected"] and not p["running"]]
        level = "ok" if not stale and not down and errors == 0 else ("warn" if not down else "bad")
        reviews = sorted([f for f in (ROOT / "reviews").glob("*.md") if not f.name.startswith("dryrun")], key=lambda f: f.name)
        reports = sorted((ROOT / "reports").glob("*.md"), key=lambda f: f.stat().st_mtime)
        url = ""
        try:
            url = (ROOT / "dashboard" / "url.txt").read_text().strip()
        except Exception:
            pass
        return {
            "ts": t, "ts_brt": brt_iso(t), "level": level, "errors": errors, "stale": stale, "down": down,
            "processes": procs, "heartbeats": beats,
            "nightly": {"next_run_brt": ng.get("next_run_brt"), "last_run": ng.get("last_run"),
                        "next_rotation_brt": ng.get("next_rotation_brt"), "last_rotation": ng.get("last_rotation")},
            "last_review": ({"name": reviews[-1].name, "path": f"reviews/{reviews[-1].name}"} if reviews else None),
            "reviews": [f"reviews/{f.name}" for f in reviews],
            "reports": [f"reports/{f.name}" for f in reports[-8:]],
            "criteria": [c for c in ("criteria_baseline.json", "criteria_v2.json") if (ROOT / c).exists()],
            "review_done": sol.get("review_done"),
            "price_usd": sol.get("price_usd"), "price_source": sol.get("price_source"),
            "dashboard_url": url, "paper_only": True, "live_trading": False,
            "extras": INS.health_extras(),
        }

    @r.get("/health")
    def health(_: str = A):
        return health_payload()

    # ---------- overview
    @r.get("/overview")
    def overview(_: str = A):
        rows = rows_all()
        h = health_payload()
        t0 = today_start_ts()
        trades_today = sum(1 for tr in all_trades() if (row_ts(tr) or 0) >= t0)
        lab_orders = ROOT / "logs" / "lab_orders.jsonl"
        return {
            "ts_brt": brt_iso(), "price_usd": h["price_usd"], "price_source": h["price_source"],
            "portfolios_total": len(rows), "trades_today": trades_today, "errors": h["errors"], "health": h["level"],
            "rows": rows, "experiment": INS.experiment_info([x.get("started_ts") for x in rows]),
            "skill_status": SKILL.status(),
            "verdict_rule": "inconclusivo até ≥30 RT fechados e ≥21 dias (≥28 p/ regras 1h e filtros de regime); fork líder = base de tuning, não veredito",
        }

    # ---------- charts
    @r.get("/candles")
    def candles(asset: str = "SOL", res: int = 300, hours: float = 24, _: str = A):
        if asset != "SOL" and asset not in meme_syms():
            raise HTTPException(404, "unknown asset")
        res = max(60, min(int(res), 86400)); hours = max(1.0, min(float(hours), 24 * 60))
        c = build_candles(asset, res, hours)
        since = now() - hours * 3600
        mint = None
        if asset != "SOL":
            for t in (read_json(ROOT / "memecoins.json", {}) or {}).get("tokens") or []:
                if t.get("symbol") == asset:
                    mint = t.get("mint")
        markers = []
        for tr in all_trades():
            ts = row_ts(tr)
            if not ts or ts < since or not trade_matches_asset(tr, asset, mint):
                continue
            n = norm_trade(tr)
            markers.append({"time": int(ts // res * res), "ts": ts, "portfolio": n["portfolio"], "side": n["side"],
                            "price": n["mark"], "fill_price": n["fill_price"]})
        return {"asset": asset, "res": res, "candles": c, "markers": markers}

    @r.get("/equity")
    def equity(group: str = "sol", asset: str | None = None, names: str | None = None, points: int = 600, _: str = A):
        points = max(50, min(points, 3000))
        wanted = set(names.split(",")) if names else None
        out = {}
        for it in universe():
            if wanted is not None:
                if it["name"] not in wanted:
                    continue
            else:
                if it["group"] != group:
                    continue
                if asset and it["asset"] != asset:
                    continue
            rows = downsample(jsonl_rows(Path(it["equity_file"])), points)
            out[it["name"]] = {
                "group": it["group"], "asset": it["asset"], "model": it.get("model"),
                "t": [int(row_ts(x) or 0) for x in rows],
                "equity": [fnum(x.get("equity")) for x in rows],
                "bh": [fnum(x.get("bh_equity")) for x in rows],
                "usdt": [fnum(x.get("all_usdt_equity")) for x in rows],
            }
        return out

    @r.get("/sparks")
    def sparks(points: int = 60, _: str = A):
        """Curvas reduzidas de todos os portfólios, em % desde o início (sparklines e pequenos múltiplos)."""
        points = max(12, min(int(points), 240))
        out = {}
        for it in universe():
            sp = INS.spark_series(jsonl_rows(Path(it["equity_file"])), points, ts_of=row_ts)
            if sp:
                out[it["name"]] = sp
        return out

    @r.get("/realbot")
    def realbot(points: int = 360, _: str = A):
        """Livro de papel do bot real (jev_trader score, calculado em processo; só leitura dos logs).
        Com um livro B (logs/paper_b, perfil com saídas), `books` traz A e B com os mesmos campos + `exits`."""
        return INS.real_bot_board(max(60, min(int(points), 2000)))

    # ---------- portfolio details
    def decisions_file_for(it: dict) -> Path:
        if it["group"] == "lab":
            return ROOT / "logs" / "lab_decisions.jsonl"
        if it["group"] == "meme":
            return ROOT / "logs" / "meme_decisions.jsonl"
        return ROOT / "logs" / "decisions.jsonl"

    @r.get("/portfolio/{name}")
    def portfolio(name: str, _: str = A):
        it = next((x for x in universe() if x["name"] == name), None)
        if not it:
            raise HTTPException(404, "unknown portfolio")
        row = portfolio_row(it, verdicts_all(), overlay_ports(), control_names(), SKILL.get())
        pdata = read_json(Path(it["file"]), {}) or {}
        # decision log uses meme_{SYM}_x for meme von, lab/sol names as-is
        keys = {name, pdata.get("name") or name, f"meme_{name}"}
        decs = [d for d in jsonl_rows(decisions_file_for(it)) if d.get("portfolio") in keys][-3000:]
        bins = [0] * 20
        chosen: dict[str, int] = {}; final: dict[str, int] = {}; reasons: dict[str, int] = {}
        lat = []
        for d in decs:
            c = fnum(d.get("confidence"))
            if c is not None:
                bins[min(19, max(0, int(c * 20)))] += 1
            chosen[str(d.get("chosen_action"))] = chosen.get(str(d.get("chosen_action")), 0) + 1
            final[str(d.get("final_action"))] = final.get(str(d.get("final_action")), 0) + 1
            for g in d.get("gate_reasons") or []:
                reasons[g] = reasons.get(g, 0) + 1
            if fnum(d.get("latency_ms")) is not None:
                lat.append(fnum(d["latency_ms"]))
        trades = [norm_trade(t) for t in all_trades() if t.get("portfolio") in keys]
        trades.sort(key=lambda x: x["ts"] or 0, reverse=True)
        params = None
        try:
            if row["control"]:
                params = (deps["api_params_raw"]()["portfolios"] or {}).get(row["control"])
        except Exception:
            params = None
        lat.sort()
        return {
            "row": row, "params": params,
            "portfolio_file": {k: v for k, v in pdata.items() if k not in ("trade_timestamps",)},
            "decisions": {"n": len(decs), "conf_hist": bins, "chosen": chosen, "final": final, "reasons": reasons,
                          "latency_p50": lat[len(lat) // 2] if lat else None, "latency_p95": lat[int(len(lat) * 0.95)] if lat else None,
                          "recent": [{"ts_brt": d.get("ts_brt"), "chosen": d.get("chosen_action"), "final": d.get("final_action"),
                                      "confidence": fnum(d.get("confidence")), "skip_noul": fnum(d.get("skip_noul")),
                                      "reasons": d.get("gate_reasons"), "model": d.get("model")} for d in decs[-40:]][::-1]},
            "trades": trades[:500],
        }

    # ---------- memes grid
    @r.get("/memes")
    def memes(_: str = A):
        rows = [x for x in rows_all() if x["group"] in ("meme", "lab") and x["asset"] != "SOL"]
        syms = meme_syms()
        st = read_json(ROOT / "data" / "meme" / "status.json", {}) or {}
        toks = st.get("tokens") or {}
        grid: dict[str, dict] = {s: {} for s in syms}
        strategies: list[str] = []
        for x in rows:
            if x["group"] == "meme":
                strat = x["strategy"]
            else:
                strat = (x.get("hyp") or "lab").lower() + ":" + x["name"].replace(f"_{x['asset']}", "").replace(x["asset"] + "_", "")
            if strat not in strategies:
                strategies.append(strat)
            grid.setdefault(x["asset"], {})[strat] = {k: x.get(k) for k in ("name", "equity", "vs_bh", "vs_bh_pct", "pnl_pct", "trades", "verdict", "progress_text", "max_dd_pct", "exposure_pct")}
        order = [s for s in MEME_STRATS if s in strategies] + sorted(s for s in strategies if s not in MEME_STRATS)
        return {
            "symbols": syms, "strategies": order, "labels": STRAT_LABELS, "grid": grid,
            "tokens": {s: {"price": (toks.get(s) or {}).get("price"), "price_source": (toks.get(s) or {}).get("price_source")} for s in syms},
            "meta": {"restart_brt": st.get("restart_brt"), "price_policy": st.get("price_policy"), "cycle_wall_ms": st.get("cycle_wall_ms"),
                     "meme_models_enabled": st.get("meme_models_enabled"), "rotate_seconds": st.get("rotate_seconds"),
                     "last_symbol": st.get("last_symbol")},
        }

    # ---------- models
    @r.get("/models")
    def models(_: str = A):
        mj = read_json(ROOT / "models.json", {}) or {}
        st = read_json(ROOT / "status.json", {}) or {}
        mst = read_json(ROOT / "data" / "meme" / "status.json", {}) or {}
        out = {}
        sol_dec = jsonl_rows(ROOT / "logs" / "decisions.jsonl")[-6000:]
        meme_dec = tail_rows(ROOT / "logs" / "meme_decisions.jsonl", 6000)
        def dist(rows, mid):
            bins = [0] * 20; lat = []; n = 0; chosen: dict[str, int] = {}; errors = 0
            for d in rows:
                m = d.get("model") or ("von" if not str(d.get("strategy") or "").startswith("rule") else "rule")
                if m != mid:
                    continue
                n += 1
                c = fnum(d.get("confidence"))
                if c is not None:
                    bins[min(19, max(0, int(c * 20)))] += 1
                l = fnum(d.get("latency_ms"))
                if l is not None:
                    lat.append(l)
                ca = str(d.get("chosen_action")); chosen[ca] = chosen.get(ca, 0) + 1
                if d.get("von_ok") is False or d.get("fail_closed"):
                    errors += 1
            lat.sort()
            return {"n": n, "conf_hist": bins, "chosen": chosen, "errors": errors,
                    "latency_p50": lat[len(lat) // 2] if lat else None, "latency_p95": lat[int(len(lat) * 0.95)] if lat else None}
        for mid, b in (mj.get("backends") or {}).items():
            pid = pid_info(ROOT / "run" / f"{mid}.pid", mid) if mid != "jev" else {"name": mid, "pid": None, "running": None}
            cur_lat = None
            if mid == "von":
                cur_lat = fnum((st.get("baseline") or {}).get("last_latency_ms"))
            else:
                cur_lat = fnum((st.get("extra_latencies_ms") or {}).get(mid))
            out[mid] = {
                "id": mid, "label": b.get("label"), "kind": b.get("kind"), "enabled": bool(b.get("enabled")),
                "memes_enabled": bool(b.get("memes_enabled")), "sol_portfolios": b.get("sol_portfolios") or [],
                "port": b.get("port"), "process": pid, "latency_ms": cur_lat,
                "meme_latency_ms": fnum((mst.get("extra_latencies_ms") or {}).get(mid)) if mid != "von" else fnum(mst.get("last_latency_ms")),
                "status": (st.get("jev") or {}).get("status") if mid == "jev" else ("ativo" if b.get("enabled") else "desabilitado"),
                "note": b.get("note"), "sol": dist(sol_dec, mid), "meme": dist(meme_dec, mid),
            }
        return {"models": out, "jev": st.get("jev"), "cycle_wall_ms": st.get("cycle_wall_ms"),
                "meme_cycle_wall_ms": mst.get("cycle_wall_ms"), "memes_allow_other_models": mj.get("memes_allow_other_models")}

    # ---------- lab / rules
    @r.get("/lab")
    def lab(_: str = A):
        base = deps["api_lab_raw"]()
        reg = read_json(ROOT / "data" / "lab" / "registry.json", {}) or {}
        regp = reg.get("portfolios") or {}
        ver = verdicts_all()
        rows = {x["name"]: x for x in rows_all()}
        for lin in base.get("lineages") or []:
            for m in lin.get("members") or []:
                e = regp.get(m["name"]) or {}
                m["report_label"] = e.get("report_label")
                m["parent"] = e.get("parent")
                m["params_diff"] = e.get("params_diff")
                m["is_original"] = bool(e.get("is_original")) or not e.get("parent")
                if e.get("parent"):
                    m["who"] = e.get("who") or "nightly"
                    m["reason"] = e.get("reason")
                    m["criteria_summary"] = e.get("criteria_summary")
                rr = rows.get(m["name"]) or {}
                m["max_dd_pct"] = rr.get("max_dd_pct"); m["vs_bh_pct"] = rr.get("vs_bh_pct"); m["pnl_pct"] = rr.get("pnl_pct")
                m["progress_obj"] = rr.get("progress")
        for h in base.get("hypotheses") or []:
            e = regp.get(h["name"]) or {}
            h["report_label"] = e.get("report_label")
            rr = rows.get(h["name"]) or {}
            h["max_dd_pct"] = rr.get("max_dd_pct"); h["vs_bh_pct"] = rr.get("vs_bh_pct"); h["pnl_pct"] = rr.get("pnl_pct")
            h["progress_obj"] = rr.get("progress")
        rules = read_json(ROOT / "data" / "rules" / "status.json", {}) or {}
        rule_rows = [x for x in rows.values() if x["kind"] in ("rule", "hybrid")]
        base["rules_status"] = {k: rules.get(k) for k in ("ok", "ts_brt", "cycles", "errors", "started_brt", "warm_up", "indicators", "sol_price")}
        base["rule_rows"] = rule_rows
        base["caps"] = reg.get("caps")
        try:
            from bot import lab_registry as R  # type: ignore
            base["tuning_hard_bounds"] = {k: list(v) for k, v in R.HARD.items()}
        except Exception:
            base["tuning_hard_bounds"] = None
        base["rules_paused"] = bool(((deps["load_overlay"]().get("bots") or {}).get("rules_paused")))
        return base

    # ---------- params (bounds for client-side validation)
    @r.get("/params")
    def params(_: str = A):
        p = deps["api_params_raw"]()
        bounds = {"min_confidence": [0.0, 1.0], "min_prob_margin": [0.0, 1.0], "max_skip_noul": [0.0, 1.0],
                  "buy_fraction_usdt": [0.05, 0.5], "cooldown_seconds": [15, None], "max_trades_per_hour": [1, 8]}
        p["bounds_note"] = ("Limites padrão de params.json (defaults.limits); um tipo pode subi-los em `limits` "
                            "(ex.: rule_*.variants.full compra 100%). O servidor valida com o resolver antes de gravar.")
        try:
            from bot import lab_registry as R  # type: ignore
            tuning = {k: list(v) for k, v in R.HARD.items()}
        except Exception:
            tuning = {}
        p["bounds"] = bounds
        p["tuning_bounds"] = tuning
        p["ints"] = ["cooldown_seconds", "max_trades_per_hour"]
        return p

    @r.get("/params/effective/{name}")
    def params_effective(name: str, static: bool = False, _: str = A):
        from bot import params as P  # type: ignore
        eff, prov, errs, meta = P.explain(name, use_overlay=not static)
        return {"portfolio": name, "meta": meta, "effective": eff, "provenance": prov, "errors": errs,
                "summary": P.summary(eff)}

    @r.get("/params/types")
    def params_types(_: str = A):
        from bot import params as P  # type: ignore
        doc = P.STORE.doc() or {}
        out = {}
        for t in sorted(doc.get("types") or {}):
            eff, prov, errs = P.type_view(t, doc=doc)
            out[t] = {"effective": eff, "provenance": prov, "errors": errs, "summary": P.summary(eff)}
        return {"types": out, "doc_errors": P.STORE.doc_errors}

    @r.get("/param_changes")
    def param_changes(limit: int = 200, _: str = A):
        return list(reversed(tail_rows(ROOT / "logs" / "param_changes.jsonl", max(1, min(limit, 1000)))))

    # ---------- funding (read-only; never writes to funding/)
    @r.get("/funding")
    def funding(_: str = A):
        st = read_json(FUND / "data" / "status.json")
        if not st:
            return {"available": False}
        ports = {k: v for k, v in (st.get("portfolios") or {}).items() if k in FUNDING_SHOWN}
        started = st.get("started_at")
        try:
            start_ts = datetime.fromisoformat(started).timestamp() if started else None
        except Exception:
            start_ts = None
        acc = jsonl_rows(FUND / "logs" / "funding_accruals.jsonl")
        cum: dict[str, list] = {k: [] for k in ports}
        tot = {k: 0.0 for k in ports}
        for a in acc:
            if a.get("type") != "funding" or a.get("portfolio") not in ports:
                continue
            k = a["portfolio"]; tot[k] += fnum(a.get("payment_usdc"), 0.0)
            ts = int(row_ts(a) or 0)
            if cum[k] and cum[k][-1][0] == ts:
                cum[k][-1][1] = tot[k]
            else:
                cum[k].append([ts, tot[k]])
        snaps: dict[str, list] = {k: [] for k in ports}
        for s in jsonl_rows(FUND / "logs" / "positions.jsonl"):
            if s.get("event") == "snapshot" and s.get("portfolio") in ports and fnum(s.get("nav")) is not None:
                snaps[s["portfolio"]].append([int(row_ts(s) or 0), fnum(s["nav"])])
        for k, v in ports.items():  # live point
            if st.get("heartbeat_ms") and fnum(v.get("nav")) is not None:
                snaps[k].append([int(st["heartbeat_ms"] / 1000), fnum(v["nav"])])
        trades = [t for t in jsonl_rows(FUND / "logs" / "trades.jsonl") if t.get("portfolio") in ports][-300:][::-1]
        return {
            "available": True, "service": st.get("service"), "run_mode": st.get("run_mode"), "heartbeat": st.get("heartbeat"),
            "heartbeat_age_s": (now() - st["heartbeat_ms"] / 1000) if st.get("heartbeat_ms") else None,
            "started_at": started, "start_ts": start_ts, "end_at": st.get("end_at"), "counters": st.get("counters"),
            "last_error": st.get("last_error"), "benchmarks": st.get("benchmarks"), "portfolios": ports,
            "usdc_bar_apr": FUNDING_USDC_BAR, "cum_funding": cum, "nav_series": snaps, "trades": trades,
            "shown": list(FUNDING_SHOWN), "paper_only": st.get("paper_only", True),
        }

    # ---------- simulação retroativa (data/backtest; só leitura)
    def _bt_meta():
        items = universe()
        return BT.live_meta_fn(items, read_json(ROOT / "data" / "lab" / "registry.json", {}) or {}, INS.originals_meta(),
                               INS.row_meta, INS.params_brief)

    BTV = BT.BacktestView(lambda: BT.backtest_dir(ROOT), meta_factory=_bt_meta, live_index_fn=lambda: BT.live_index(universe()))

    @r.get("/backtest")
    def backtest(run: str | None = None, _: str = A):
        """Runs disponíveis + summary do mais recente (ou de `run`), com os portfólios descritos como no placar."""
        return BTV.payload(run)

    @r.get("/backtest/index")
    def backtest_index(_: str = A):
        """Histórico de runs (index.json; sem ele, montado dos summaries), do fim mais recente para o mais antigo."""
        return BTV.index()

    @r.get("/backtest/history")
    def backtest_history(_: str = A):
        txt = BTV.history()
        if txt is None:
            raise HTTPException(404, "comparação entre meses ainda não gerada")
        return PlainTextResponse(txt, media_type="text/markdown; charset=utf-8")

    @r.get("/backtest/{run_id}/chart")
    def backtest_chart(run_id: str, points: int = 2000, _: str = A):
        """Gráfico de 6 meses (chart.json do run): benchmarks, famílias, topo e bot real, 1000 = início."""
        d = BTV.chart(run_id, points)
        if d is None:
            raise HTTPException(404, "gráfico não encontrado")
        return d

    @r.get("/backtest/{run_id}/equity/{name}")
    def backtest_equity(run_id: str, name: str, points: int = 1500, _: str = A):
        d = BTV.equity(run_id, name, points)
        if d is None:
            raise HTTPException(404, "curva não encontrada")
        return d

    @r.get("/backtest/{run_id}/sparks")
    def backtest_sparks(run_id: str, points: int = 60, _: str = A):
        d = BTV.sparks(run_id, points)
        if d is None:
            raise HTTPException(404, "run desconhecido")
        return d

    @r.get("/backtest/{run_id}/report")
    def backtest_report(run_id: str, _: str = A):
        txt = BTV.report(run_id)
        if txt is None:
            raise HTTPException(404, "relatório não encontrado")
        return PlainTextResponse(txt, media_type="text/markdown; charset=utf-8")

    # ---------- SSE stream
    TOPICS: dict[str, Callable[[], list]] = {
        "sol": lambda: [ROOT / "status.json", ROOT / "logs" / "trades.jsonl"],
        "meme": lambda: [ROOT / "data" / "meme" / "status.json", ROOT / "logs" / "meme_trades.jsonl"],
        "lab": lambda: [ROOT / "data" / "lab" / "status.json", ROOT / "data" / "lab" / "registry.json",
                        ROOT / "data" / "nightly" / "verdicts.json", ROOT / "data" / "rules" / "status.json"],
        "params": lambda: [ROOT / "data" / "params_overlay.json", ROOT / "models.json", ROOT / "logs" / "param_changes.jsonl",
                           ROOT / "params.json"],
        "funding": lambda: [FUND / "data" / "status.json"],
        "health": lambda: [ROOT / "data" / "nightly" / "status.json"] + list((ROOT / "run").glob("*.pid")),
        "realbot": lambda: [d / f for _l, d in INS.real_bot_books(INS.real_bot_root())
                            for f in ("decisions.jsonl", "paper_trades.jsonl")],
    }
    MIN_GAP = {"sol": 5, "meme": 10, "lab": 15, "params": 0, "funding": 15, "health": 10, "realbot": 30}

    def topic_version(files) -> float:
        m = 0.0
        for f in files:
            try:
                m = max(m, f.stat().st_mtime)
            except Exception:
                pass
        return m

    @r.get("/stream")
    async def stream(request: Request, _: str = A):
        async def gen():
            last_v = {k: topic_version(f()) for k, f in TOPICS.items()}
            last_sent = {k: 0.0 for k in TOPICS}
            pending: set[str] = set()
            yield "retry: 5000\n\n"
            yield f"event: hello\ndata: {json.dumps({'ts': now(), 'topics': list(TOPICS)})}\n\n"
            beat = 0
            while True:
                if await request.is_disconnected():
                    break
                t = now()
                for k, f in TOPICS.items():
                    v = topic_version(f())
                    if v > last_v[k]:
                        last_v[k] = v; pending.add(k)
                ready = [k for k in list(pending) if t - last_sent[k] >= MIN_GAP[k]]
                if ready:
                    for k in ready:
                        pending.discard(k); last_sent[k] = t
                    st = read_json(ROOT / "status.json", {}) or {}
                    payload = {"topics": ready, "ts": t, "price_usd": st.get("price_usd"), "price_source": st.get("price_source"),
                               "heartbeat_age_s": (t - fnum(st.get("ts"), t))}
                    yield f"event: update\ndata: {json.dumps(payload)}\n\n"
                beat += 1
                if beat % 15 == 0:
                    yield f": ping {int(t)}\n\n"
                await asyncio.sleep(1.0)
        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"})

    return r
