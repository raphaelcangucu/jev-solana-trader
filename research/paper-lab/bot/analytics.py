"""Portfolio analytics shared by the nightly job and report.py (read-only on sim state)."""
from __future__ import annotations
import json, math
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from bot.lib import BRT
from bot import lab_registry as R
from bot import logio

from bot.paths import ROOT
DOWN = []  # known downtime windows (ts pairs) excluded from return series
for a, b in (("2026-09-24T00:11:00", "2026-09-24T00:21:00"), ("2026-09-24T08:56:00", "2026-09-24T09:14:00")):
    DOWN.append((datetime.fromisoformat(a + "-03:00").timestamp(), datetime.fromisoformat(b + "-03:00").timestamp()))


def jl(path):
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p) as f:
        for l in f:
            if l.strip():
                try: out.append(json.loads(l))
                except Exception: pass
    return out


def group_of(name, meta):
    a = meta.get("asset", "SOL")
    if name in R.originals():
        m = R.originals()[name]
        if m["kind"] == "rule":
            return f"{a} rule"
        return f"{a} {m['model']}"
    return f"{a} lab"


def catalog():
    """All portfolios: originals (bot-run) + lab (hypotheses/forks)."""
    cat = {}
    for n, m in R.originals().items():
        if Path(m["file"]).exists():
            cat[n] = dict(m, name=n, origin="original", lineage=n, parent=None, status="active")
    reg = R.load()
    for n, e in reg["portfolios"].items():
        cat[n] = dict(e, file=str(R.port_path(n)), equity=str(R.eq_path(n)), origin="lab")
    for n, m in cat.items():
        st = json.loads(Path(m["file"]).read_text())
        m["state"] = st
        m["start_ts"] = datetime.fromisoformat(st["started_brt"]).timestamp() if st.get("started_brt") else float(st.get("created_ts") or 0)
        m["trades_log"] = str(ROOT / "logs" / ("trades.jsonl" if m.get("asset", "SOL") == "SOL" else "meme_trades.jsonl"))
    return cat, reg


def load_trades():
    by = {}
    for f in ("trades.jsonl", "meme_trades.jsonl"):
        for t in jl(ROOT / "logs" / f):
            by.setdefault(t.get("portfolio"), []).append(t)
    return by


def _grid_series(rows, t_a, t_b, step=300.0):
    ts = np.array([r["ts"] for r in rows]); 
    g = np.arange(max(t_a, ts[0]), t_b + 1e-6, step)
    if len(g) < 2:
        return None
    idx = np.clip(np.searchsorted(ts, g, side="right") - 1, 0, len(ts) - 1)
    pick = lambda k: np.array([float(rows[i].get(k) or 0.0) for i in idx])
    E = pick("equity"); P = pick("price"); BH = pick("bh_equity")
    Q = np.array([float(rows[i].get("sol") or rows[i].get("token") or 0.0) for i in idx])
    return g, E, P, BH, Q


def placebo_p(w, r, n_min=24):
    if len(r) < n_min or np.std(w) < 1e-9:
        return None
    act = float(((w - w.mean()) * r).sum())
    sims = np.array([((np.roll(w, k) - w.mean()) * r).sum() for k in range(1, len(w))])
    return float((sims >= act - 1e-15).mean())


def window_stats(meta, trades_by, t_a, t_b):
    """Stats for [t_a, t_b] (clipped to portfolio start). Values in USDT."""
    name = meta["name"]
    t_a = max(t_a, meta["start_ts"])
    rows = [r for r in logio.iter_rows(meta["equity"], since_ts=t_a - 86400) if r.get("equity") is not None and r["ts"] <= t_b + 1]
    out = {"name": name, "from": t_a, "to": t_b}
    if not rows or t_a >= t_b:
        out["empty"] = True; return out
    before = [r for r in rows if r["ts"] <= t_a]
    inwin = [r for r in rows if t_a < r["ts"] <= t_b]
    if not inwin:
        out["empty"] = True; return out
    r0 = before[-1] if before else inwin[0]; r1 = inwin[-1]
    E0, E1 = float(r0["equity"]), float(r1["equity"])
    BH0, BH1 = float(r0.get("bh_equity") or E0), float(r1.get("bh_equity") or E1)
    pnl = E1 - E0
    series = [r0] + inwin
    em = np.array([float(r["equity"]) for r in series]); pk = np.maximum.accumulate(em)
    out.update(start_value=E0, end_value=E1, pnl=pnl, pnl_pct=pnl / E0 * 100 if E0 else 0.0,
               bh_pnl=BH1 - BH0, ex_bh=pnl - (BH1 - BH0), ex_usdt=pnl, mdd_pct=float(((em - pk) / pk).min() * 100),
               hours=(r1["ts"] - t_a) / 3600)
    gs = _grid_series(series, t_a, t_b)
    if gs:
        g, E, P, BH, Q = gs
        W = np.where(E > 0, Q * P / E, 0)
        ok = np.array([not any(a <= x < b or a <= y < b for a, b in DOWN) for x, y in zip(g[:-1], g[1:])])
        rp = np.diff(E) / E[:-1]; ra = np.diff(P) / np.where(P[:-1] > 0, P[:-1], 1)
        rp, ra, wl = rp[ok], ra[ok], W[:-1][ok]
        out["exposure_pct"] = float(W.mean() * 100)
        out["vol_5m_pct"] = float(np.std(rp, ddof=1) * 100) if len(rp) > 2 else None
        if len(ra):
            out["static_usd"] = float(wl.mean() * ra.sum() * E0)
            out["timing_usd"] = float(((wl - wl.mean()) * ra).sum() * E0)
            out["timing_p"] = placebo_p(wl, ra)
    tr = [t for t in trades_by.get(name, []) if t_a < t["ts"] <= t_b]
    fees = cost = 0.0; modes = {}; sells = wins = 0
    for t in tr:
        f = t.get("fill") or {}; pm = float(t.get("price_mark") or f.get("mark_price") or 0)
        fees += float(f.get("fee_usdt") or 0)
        m = f.get("fill_mode") or "?"; modes[m] = modes.get(m, 0) + 1
        if t["side"] == "buy":
            q = float(f.get("sol_out_net") or f.get("token_out_net") or 0); cost += float(f.get("usdt_in") or 0) - q * pm
        else:
            q = float(f.get("sol_in") or f.get("token_in") or 0); cost += q * pm - float(f.get("usdt_out_net") or 0)
            sells += 1; wins += 1 if float(f.get("approx_pnl") or 0) > 0 else 0
    out.update(trades=len(tr), buys=len(tr) - sells, sells=sells, rt_wins=wins, fees=fees, cost_vs_mark=cost, fill_modes=modes)
    if not tr:
        out["timing_p"] = None
    return out


def cumulative_counts(meta, trades_by):
    tr = trades_by.get(meta["name"], [])
    tr = [t for t in tr if t["ts"] >= meta["start_ts"] - 5]
    return {"trades": len(tr), "closed_rt": sum(1 for t in tr if t["side"] == "sell"),
            "days": (datetime.now().timestamp() - meta["start_ts"]) / 86400}


def day_bounds(day: str):
    a = datetime.fromisoformat(day + "T00:00:00-03:00").timestamp()
    return a, a + 86400


def fmt(x, n=2, sign=False):
    if x is None: return "–"
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)): return "–"
    return f"{x:+.{n}f}" if sign else f"{x:.{n}f}"


def stats_table(cat, trades_by, t_a, t_b, names=None):
    rows = []
    for n in (names or sorted(cat, key=lambda k: (cat[k].get("asset", "SOL") != "SOL", cat[k].get("asset", ""), k))):
        s = window_stats(cat[n], trades_by, t_a, t_b)
        if s.get("empty"):
            continue
        rows.append((n, s))
    L = ["| Portfólio | Grupo | Início janela | Valor ini. | Valor fim | PnL $ | PnL % | Excesso vs B&H $ | vs USDT $ | Trades (C/V) | RT ganhos | Taxas $ | Custo vs mark $ | Exposição % | MDD % | Timing $ (p) | Fills |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, s in rows:
        fm = ", ".join(f"{k}:{v}" for k, v in sorted(s["fill_modes"].items())) or "–"
        tp = f"{fmt(s.get('timing_usd'),3,True)} ({fmt(s.get('timing_p'),2)})" if s.get("timing_usd") is not None else "–"
        L.append(f"| {n} | {group_of(n, cat[n])} | {datetime.fromtimestamp(s['from'], BRT).strftime('%m-%d %H:%M')} | {fmt(s['start_value'],3)} | {fmt(s['end_value'],3)} | "
                 f"{fmt(s['pnl'],3,True)} | {fmt(s['pnl_pct'],2,True)}% | {fmt(s['ex_bh'],3,True)} | {fmt(s['ex_usdt'],3,True)} | {s['trades']} ({s['buys']}/{s['sells']}) | "
                 f"{s['rt_wins']}/{s['sells']} | {fmt(s['fees'],4)} | {fmt(s['cost_vs_mark'],4)} | {fmt(s.get('exposure_pct'),1)} | {fmt(s['mdd_pct'],2)} | {tp} | {fm} |")
    return "\n".join(L), dict(rows)


def fill_quality(t_a, t_b):
    """Fallback-to-mark rate for trades + quote-layer outcomes in window."""
    tot = mark = 0; reasons = {}
    for f in ("trades.jsonl", "meme_trades.jsonl"):
        for t in jl(ROOT / "logs" / f):
            if t_a < t["ts"] <= t_b:
                fm = (t.get("fill") or {}).get("fill_mode")
                if fm == "limit_sim":
                    continue
                tot += 1
                if fm == "mark":
                    mark += 1; r = str((t.get("fill") or {}).get("quote_error"))[:60]; reasons[r] = reasons.get(r, 0) + 1
    q = {}
    for e in logio.iter_rows(ROOT / "logs" / "quote_events.jsonl", since_ts=t_a):
        if t_a < e["ts"] <= t_b:
            k = f"{e.get('provider')}:{e.get('outcome')}"; q[k] = q.get(k, 0) + 1
    return {"market_fills": tot, "mark_fallbacks": mark, "fallback_rate": (mark / tot if tot else None), "reasons": reasons, "quote_events": q}


# ---------------- verdicts (user rule, 2026-09-24) ----------------
VERDICT_DEFAULTS = {"min_closed_rt": 30, "min_days": 21, "min_days_rule_regime": 28, "usdc_apy": 0.06,
                    "p_max": 0.05, "weeks_consistent": [3, 4], "boot_block": 12, "boot_n": 2000,
                    "require_bear_regime_for_rule": False}


def is_rule_or_regime(name, meta):
    k = (meta.get("kind") == "rule") or any(s in name for s in ("rule_", "grid_", "rsi_", "regime", "hybrid_"))
    src = meta.get("source") or ""
    return k or "hybrid" in src


_BEAR_CACHE = {}
def bear_regime_seen_since(t0):
    """True if any rules-bot decision since t0 logged SOL regime bull == False (1h EMA12<=EMA26)."""
    if "rows" not in _BEAR_CACHE:
        rows = [(d["ts"], (d.get("indicators") or {}).get("sol_regime_bull"))
                for d in logio.iter_rows(ROOT / "logs" / "decisions.jsonl", contains='"rule:rsi_sol_1h"')]
        _BEAR_CACHE["rows"] = rows
    return any(ts >= t0 and b is False for ts, b in _BEAR_CACHE["rows"])


def _excess_series(meta, t_a, t_b):
    rows = [r for r in logio.iter_rows(meta["equity"], since_ts=t_a - 86400) if r.get("equity") is not None and t_a - 1 <= r["ts"] <= t_b]
    if len(rows) < 3:
        return None, None
    g = _grid_series(rows, t_a, t_b)
    if not g:
        return None, None
    gg, E, P, BH, Q = g
    ok = np.array([not any(a <= x < b or a <= y < b for a, b in DOWN) for x, y in zip(gg[:-1], gg[1:])])
    return gg[1:][ok], (np.diff(E) - np.diff(BH))[ok]


def block_boot_p(x, block=12, n=2000, seed=7):
    """One-sided p-values for sum(x)>0 (win) and sum(x)<0 (lose) via circular block bootstrap of centered data."""
    if x is None or len(x) < 2 * block:
        return None, None
    rng = np.random.default_rng(seed); m = len(x); xc = x - x.mean(); s = x.sum()
    sims = np.empty(n)
    for i in range(n):
        st = rng.integers(0, m, m // block + 1)
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:m] % m
        sims[i] = xc[idx].sum()
    return float((sims >= s).mean()), float((sims <= s).mean())


def verdict(meta, trades_by, now_ts=None, cfg=None):
    c = dict(VERDICT_DEFAULTS); c.update(cfg or {})
    now_ts = now_ts or datetime.now().timestamp()
    name = meta["name"]; t0 = meta["start_ts"]
    tr = [t for t in trades_by.get(name, []) if t["ts"] >= t0 - 5]
    closed = sum(1 for t in tr if t["side"] == "sell")
    days = (now_ts - t0) / 86400
    rr = is_rule_or_regime(name, meta)
    need_days = c["min_days_rule_regime"] if rr else c["min_days"]
    bear = bear_regime_seen_since(t0) if rr else None
    prog = {"closed_rt": closed, "min_closed_rt": c["min_closed_rt"], "days": round(days, 2), "min_days": need_days,
            "trades": len(tr), "bear_regime_seen": bear, "rule_or_regime": rr}
    prog["text"] = f"{closed}/{c['min_closed_rt']} RT fechados · {days:.1f}/{need_days} dias" + (
        f" · regime baixista visto: {'sim' if bear else 'não'}" if rr else "")
    out = {"portfolio": name, "verdict": "inconclusivo", "progress": prog, "reason": "mínimos não atingidos"}
    minimums = closed >= c["min_closed_rt"] and days >= need_days and (bear or not (rr and c["require_bear_regime_for_rule"]))
    if not minimums:
        return out
    s = window_stats(meta, trades_by, t0, now_ts)
    ts, x = _excess_series(meta, t0, now_ts)
    p_win, p_lose = block_boot_p(x, c["boot_block"], c["boot_n"])
    usdc_bar = s["start_value"] * c["usdc_apy"] * days / 365
    weeks_pos = weeks = 0
    if ts is not None:
        for k in range(4):
            b = now_ts - 7 * 86400 * k; a = b - 7 * 86400
            m = (ts > a) & (ts <= b)
            if m.sum() > 10:
                weeks += 1; weeks_pos += 1 if x[m].sum() > 0 else 0
    out.update({"ex_bh": s["ex_bh"], "pnl": s["pnl"], "usdc_bar": usdc_bar, "p_win": p_win, "p_lose": p_lose,
                "timing_p": s.get("timing_p"), "weeks_pos": weeks_pos, "weeks": weeks})
    if (s["ex_bh"] > 0 and s["pnl"] > usdc_bar and p_win is not None and p_win < c["p_max"]
            and weeks_pos >= c["weeks_consistent"][0]):
        out.update(verdict="vencedora", reason="bate B&H e 6%/a USDC, p<0,05 líquido de custos, ≥3 de 4 semanas")
    elif s["ex_bh"] < 0 and p_lose is not None and p_lose < c["p_max"]:
        out.update(verdict="perdedora", reason="pior que o benchmark com p<0,05")
    else:
        out.update(reason="mínimos atingidos, mas sem significância/consistência")
    return out


VERDICT_PT = {"inconclusivo": "inconclusivo", "vencedora": "vencedora", "perdedora": "perdedora"}
