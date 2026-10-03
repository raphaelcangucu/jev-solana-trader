"""Nightly tuner: bounded walk-forward replay of recorded decisions/prices with the live cost model.
Candidates only become FORKS (originals are never modified). Paper only.

Espaço de busca por tipo de teste: params.json `tuning` (params, bounds, max_rel_change, steps, ...) dos parâmetros
efetivos do portfólio base (bot/params.py). Um caminho só entra se a secção estiver ativa (exits.enabled,
exec.mode=limit, gates.margin_gate, ensemble presente)."""
from __future__ import annotations
import copy, json, math
from collections import deque
from datetime import datetime
from pathlib import Path
import numpy as np
from bot import analytics as A
from bot import lab_registry as R
from bot import logio

from bot.paths import ROOT
TUNE_DEFAULTS = {"train_frac": 0.7, "steps": [0.8, 0.9, 1.1, 1.2], "max_rel_change": 0.2,
                 "min_improvement_pct": 0.25, "trade_penalty_bps": 2.0, "net_fee_usd": 0.0006}


def cost_bps(cls, now_ts, days=7):
    vals = []
    f = "trades.jsonl" if cls == "sol" else "meme_trades.jsonl"
    for t in A.jl(ROOT / "logs" / f):
        if t["ts"] < now_ts - days * 86400:
            continue
        fl = t.get("fill") or {}
        if fl.get("fill_mode") in ("mark", "limit_sim", None):
            continue
        pm = float(t.get("price_mark") or 0)
        if t["side"] == "buy":
            q = float(fl.get("sol_out_net") or fl.get("token_out_net") or 0); n = float(fl["usdt_in"]); c = n - q * pm
        else:
            q = float(fl.get("sol_in") or fl.get("token_in") or 0); n = q * pm; c = n - float(fl["usdt_out_net"])
        if n > 0:
            vals.append(c / n * 1e4)
    return (float(np.median(vals)), len(vals)) if len(vals) >= 5 else ((15.0 if cls == "sol" else 30.0), len(vals))


def _prices(asset, t0, t1):
    p = ROOT / "data" / "prices.jsonl" if asset == "SOL" else ROOT / "data" / "meme" / "prices" / f"{asset}.jsonl"
    return [(r["ts"], float(r["price_usd"])) for r in logio.iter_rows(p, since_ts=t0)
            if t0 <= r["ts"] <= t1 and r.get("price_usd") and not r.get("stale") and not r.get("fabricated")]


_DEC_CACHE = {}


def _decisions(cls, sources, t0, t1):
    f = ROOT / "logs" / ("decisions.jsonl" if cls == "sol" else "meme_decisions.jsonl")
    keys = set(sources)
    ck = (cls, int(t1 // 3600))
    if ck not in _DEC_CACHE:
        by = {}
        lo = t1 - 15 * 86400
        for d in logio.iter_rows(f, since_ts=lo):
            if d.get("ts", 0) >= lo and d.get("confidence") is not None:
                by.setdefault(d.get("portfolio"), []).append(
                    {k: d.get(k) for k in ("ts", "portfolio", "chosen_action", "confidence", "probabilities", "skip_noul", "price_usd", "fail_closed", "decision_id")})
        _DEC_CACHE.clear(); _DEC_CACHE[ck] = by
    by = _DEC_CACHE[ck]
    out = [d for k in keys for d in by.get(k, []) if t0 <= d["ts"] <= t1]
    out.sort(key=lambda d: d["ts"])
    return out


class Sim:
    def __init__(self, sol_mode, q, usdt, px0, c_bps, net_fee):
        self.q, self.usdt = q, usdt; self.c = c_bps / 1e4; self.net = net_fee
        self.entry = px0 if q > 0 else None; self.peak = self.entry
        self.last = None; self.stamps = []; self.reentry = 0; self.order = None; self.trades = 0
    def eq(self, px): return self.usdt + self.q * px
    def buy(self, px, frac, ts, eff=None, fee_bps=None, cap=None):
        n = self.usdt * frac
        if cap is not None:  # gates.max_exposure_frac: a compra não passa o teto de exposição
            pos = self.q * px
            n = min(n, float(cap) * (self.usdt + pos) - pos)
        if n < 1.0: return False
        price = eff if eff else px * (1 + self.c)
        fee = n * (fee_bps / 1e4) if fee_bps else 0.0
        got = (n - fee) / price - self.net / px
        tot = self.q + got
        self.entry = ((self.q * (self.entry or px)) + n) / tot if tot > 0 else px
        self.peak = max(self.peak or px, px) if self.q > 0 else px
        self.q = tot; self.usdt -= n; self._done(ts); return True
    def sell(self, px, ts, eff=None, fee_bps=None):
        if self.q * px < 1.0: return False
        price = eff if eff else px * (1 - self.c)
        out = self.q * price
        out -= out * (fee_bps / 1e4) if fee_bps else 0.0
        self.usdt += out - self.net; self.q = 0.0; self.entry = None; self.peak = None; self._done(ts); return True
    def _done(self, ts):
        self.last = ts; self.stamps.append(ts); self.trades += 1


def _gate(sim, chosen, conf, probs, skip, g, profile, ts, px):
    if chosen not in ("buy", "sell"): return "hold"
    if conf < g["min_confidence"]: return "hold"
    if g.get("margin_gate", profile == "relaxed") and probs and g.get("min_prob_margin", 0) > 0:
        v = sorted((float(x) for x in probs.values()), reverse=True)
        if v[0] - (v[1] if len(v) > 1 else 0) < g["min_prob_margin"]: return "hold"
    if skip >= g["max_skip_noul"]: return "hold"
    if sim.last is not None and ts - sim.last < g["cooldown_seconds"]: return "hold"
    if len([t for t in sim.stamps if t >= ts - 3600]) >= g["max_trades_per_hour"]: return "hold"
    if chosen == "buy" and sim.usdt * g["buy_fraction_usdt"] < 1.0: return "hold"
    if chosen == "sell" and sim.q * px < 1.0: return "hold"
    return chosen


def _step_price(sim, ts, px, params):
    ex = params.get("exits"); lim = params.get("exec") or {}
    if sim.order:
        o = sim.order
        if (o["side"] == "buy" and px < o["limit"]) or (o["side"] == "sell" and px > o["limit"]):
            if o["side"] == "buy":
                sim.buy(px, o["frac"], ts, eff=o["limit"], fee_bps=lim.get("fee_bps", 10), cap=o.get("cap"))
            else:
                sim.sell(px, ts, eff=o["limit"], fee_bps=lim.get("fee_bps", 10))
            sim.order = None
        elif ts >= o["exp"]:
            sim.order = None
    if ex and ex.get("enabled", True) and sim.q * px >= 1.0 and sim.entry:
        sim.peak = max(sim.peak or px, px); r = px / sim.entry - 1
        if r >= ex["tp"] or r <= -ex["sl"] or (sim.peak / sim.entry - 1 >= ex.get("trail_arm", ex["trail"]) and px <= sim.peak * (1 - ex["trail"])):
            sim.sell(px, ts); sim.reentry = ts + 60 * ex.get("reentry_cooldown_min", 30)


def _exec(sim, side, px, ts, g, params):
    lim = params.get("exec") or {}
    if (params.get("hours") is not None) and datetime.fromtimestamp(ts, A.BRT).hour not in params["hours"]:
        return
    if side == "buy" and ts < sim.reentry:
        return
    if lim.get("mode") == "limit":
        if sim.order: return
        off = lim.get("offset_bps", 10) / 1e4
        sim.order = {"side": side, "limit": px * (1 - off) if side == "buy" else px * (1 + off),
                     "frac": g["buy_fraction_usdt"], "exp": ts + 60 * lim.get("ttl_min", 15),
                     "cap": g.get("max_exposure_frac")}
    elif side == "buy":
        sim.buy(px, g["buy_fraction_usdt"], ts, cap=g.get("max_exposure_frac"))
    else:
        sim.sell(px, ts)


def replay(entry, params, t0, t1, start, c_bps, cfg_gates=None, data=None):
    """entry: kind gated|ensemble. params: parâmetros efetivos (bot/params.py). start: (q, usdt).
    data: dict with 'dec' rows and 'px' list. `cfg_gates` (antigo) só preenche portões em falta."""
    g = dict(cfg_gates or {}); g.update(params.get("gates") or {}); g = R.clamp_gates(g, params.get("limits"))
    px_list = [x for x in data["px"] if t0 <= x[0] <= t1]
    if len(px_list) < 10:
        return None
    sim = Sim(entry["asset"] == "SOL", start[0], start[1], px_list[0][1], c_bps, TUNE_DEFAULTS["net_fee_usd"])
    dec = [d for d in data["dec"] if t0 <= d["ts"] <= t1]
    ev = [(t, 0, p) for t, p in px_list] + [(d["ts"], 1, d) for d in dec]
    ev.sort(key=lambda x: (x[0], x[1]))
    last_px = px_list[0][1]
    ens = params.get("ensemble"); win = {}; latest = {}
    for ts, typ, obj in ev:
        if typ == 0:
            last_px = obj; _step_price(sim, ts, obj, params); continue
        d = obj; px = float(d.get("price_usd") or last_px)
        if entry["kind"] == "gated":
            side = _gate(sim, d.get("chosen_action"), float(d["confidence"]), d.get("probabilities"),
                         float(d.get("skip_noul") or 0), g, entry.get("profile"), ts, px)
            if side != "hold": _exec(sim, side, px, ts, g, params)
        else:
            m = data["model_of"](d.get("portfolio")); latest[m] = d
            w = win.setdefault(m, deque(maxlen=data["window"]))
            if m == "von":
                peers = {k: r for k, r in latest.items() if abs(r["ts"] - ts) <= data["span"]}
                pc = {}
                for k, r in peers.items():
                    ww = win.get(k) or []
                    if len(ww) >= ens.get("min_window", 100):
                        c = float(r["confidence"]); pc[k] = (sum(1 for x in ww if x < c) + 0.5 * sum(1 for x in ww if x == c)) / len(ww)
                votes = {"buy": [k for k, r in peers.items() if r.get("chosen_action") == "buy" and k in pc],
                         "sell": [k for k, r in peers.items() if r.get("chosen_action") == "sell" and k in pc]}
                sd = max(votes, key=lambda s: (len(votes[s]), sum(pc[k] for k in votes[s])))
                if len(votes[sd]) >= ens.get("min_agree", 2):
                    comb = sum(pc[k] for k in votes[sd]) / len(votes[sd])
                    gg = dict(g); gg["min_confidence"] = ens.get("pct_threshold", 0.8); gg["max_skip_noul"] = 1.01
                    gg["margin_gate"] = False
                    side = _gate(sim, sd, comb, None, 0.0, gg, "baseline", ts, px)
                    if side != "hold": _exec(sim, side, px, ts, g, params)
            w.append(float(d["confidence"]))
    end = sim.eq(last_px); start_eq = start[1] + start[0] * px_list[0][1]
    return {"start": start_eq, "end": end, "pnl": end - start_eq, "trades": sim.trades}


def _active(eff, sect, k):
    if sect == "exits":
        return bool((eff.get("exits") or {}).get("enabled"))
    if sect == "exec" and k in ("offset_bps", "ttl_min", "fee_bps"):
        return (eff.get("exec") or {}).get("mode") == "limit"
    if sect == "gates" and k == "min_prob_margin":
        return bool((eff.get("gates") or {}).get("margin_gate"))
    if sect == "ensemble":
        return bool(eff.get("ensemble"))
    return True


def search_space(eff):
    """[(secção, chave)] que o tuner pode mexer neste portfólio: params.json tuning.params filtrado por secções
    ativas e valores numéricos."""
    tu = eff.get("tuning") or {}
    if not tu.get("enabled", True):
        return []
    out = []
    for path in tu.get("params") or []:
        sect, _, k = str(path).partition(".")
        v = (eff.get(sect) or {}).get(k) if isinstance(eff.get(sect), dict) else None
        if not k or isinstance(v, bool) or not isinstance(v, (int, float)) or not _active(eff, sect, k):
            continue
        out.append((sect, k))
    return out


def _bound(v, b, integer):
    if b:
        v = min(b[1], max(b[0], v))
    return int(round(v)) if integer else v


def search(entry, eff, t0, t1, start, c_bps, data, conf=None):
    """Walk-forward 70/30 de um parâmetro de cada vez (± max_rel_change), combinando os que melhoram nos dois
    lados. `eff` = parâmetros efetivos do portfólio base (sem overlay). best_diff = diff do fork."""
    tu = eff.get("tuning") or {}
    c = dict(TUNE_DEFAULTS)
    c.update({k: tu[k] for k in ("steps", "max_rel_change", "train_frac", "min_improvement_pct", "trade_penalty_bps") if k in tu})
    c.update(conf or {})
    if not tu.get("enabled", True):
        return {"status": "tuning_desligado"}
    base = copy.deepcopy(eff)
    space = search_space(base)
    if not space:
        return {"status": "sem_espaco_de_busca"}
    bounds = tu.get("bounds") or {}
    split = t0 + c["train_frac"] * (t1 - t0)
    pen = c["trade_penalty_bps"] / 1e4
    def score(params):
        tr = replay(entry, params, t0, split, start, c_bps, None, data)
        va = replay(entry, params, split, t1, start, c_bps, None, data)
        if not tr or not va:
            return None
        f = lambda r: r["pnl"] - pen * r["start"] * r["trades"]
        return {"train": f(tr), "val": f(va), "train_raw": tr, "val_raw": va}
    cur = score(base)
    if cur is None:
        return {"status": "no_data"}
    results = []
    for sect, k in space:
        v = base[sect][k]
        integer = isinstance(v, int) and not isinstance(v, bool)
        for s in c["steps"]:
            nv = v * s
            if abs(nv / v - 1) > c["max_rel_change"] + 1e-9 if v else True:
                continue
            nv = _bound(nv, bounds.get(f"{sect}.{k}"), integer)
            if nv == v: continue
            cand = copy.deepcopy(base); cand[sect][k] = nv
            if sect == "gates": cand["gates"] = R.clamp_gates(cand["gates"], cand.get("limits"))
            if cand[sect][k] == v: continue
            sc = score(cand)
            if sc: results.append(({sect: {k: cand[sect][k]}}, sc))
    min_imp = c["min_improvement_pct"] / 100 * cur["train_raw"]["start"]
    good = [(d, s) for d, s in results if s["val"] - cur["val"] >= min_imp and s["train"] >= cur["train"]]
    best = None
    if good:
        # combine improving one-parameter changes (best per param), keep if still better on both splits
        good.sort(key=lambda x: -(x[1]["val"] + x[1]["train"]))
        combo = {}; seen = set()
        for d, s in good:
            (sect, kv), = d.items(); (k, v), = kv.items()
            if (sect, k) in seen: continue
            seen.add((sect, k)); combo.setdefault(sect, {})[k] = v
        cp = copy.deepcopy(base)
        for sect, kv in combo.items(): cp[sect].update(kv)
        sc = score(cp)
        best = (combo, sc) if sc and sc["val"] >= good[0][1]["val"] and sc["train"] >= cur["train"] else good[0]
    return {"status": "candidate" if best else "no_improvement", "current": cur, "n_candidates": len(results),
            "best_diff": best[0] if best else None, "best": best[1] if best else None, "min_improvement": min_imp,
            "c_bps": c_bps, "split_ts": split, "space": [f"{a}.{b}" for a, b in space]}


def _start_capital(asset):
    """Starting capital per portfolio from config (SOL: starting_balances mix at its reference price; memes: start_usdt_each)."""
    cfg = json.loads((ROOT / "config.json").read_text())
    if asset == "SOL":
        b = cfg["starting_balances"]
        return float(b.get("total_usd") or (b["usdt"] + b["sol"] * float(b.get("ref_price") or 0)) or 1000.0)
    return float(json.loads((ROOT / "memecoins.json").read_text()).get("start_usdt_each", 1000.0))


# ---------- rule strategies (1h bars) ----------
def rule_search(meta, bars_sol, bars_meme, conf=None, eff=None):
    """Replay rule params on the last 30 days of 1h bars (walk-forward 70/30). Report-only (no rule fork executor).
    Com `eff` (params efetivos): parâmetros iniciais de rule.*, espaço de busca de tuning.params e fração de compra."""
    from bot.rules_engine import ema_series, rsi_series
    c = dict(TUNE_DEFAULTS)
    tu = (eff or {}).get("tuning") or {}
    c.update({k: tu[k] for k in ("steps", "max_rel_change", "min_improvement_pct", "trade_penalty_bps") if k in tu})
    c.update(conf or {})
    rule = meta.get("rule")
    C = float(c.get("capital") or _start_capital(meta.get("asset")))
    closes_s = [b["close"] for b in bars_sol]; ts_s = [b["ts"] for b in bars_sol]
    def run(prm, i0, i1):
        usdt, q, trades = C, 0.0, 0; cst = 0.003 if meta.get("asset") != "SOL" else 0.0015
        ef = ema_series(closes_s, prm.get("ema_fast", 12)); es = ema_series(closes_s, prm.get("ema_slow", 26))
        closes = closes_s if meta.get("asset") == "SOL" else [b["close"] for b in bars_meme]
        rs = rsi_series(closes, prm.get("rsi_period", 14)) if rule == "rsi" else None
        ref = closes[i0]; buys = 0
        for i in range(max(i0, 30), i1):
            px = closes[i]; bull = ef[i] is not None and es[i] is not None and ef[i] > es[i]
            sig = "hold"
            if rule and rule.startswith("rule_regime"):
                sig = "buy" if bull and q == 0 else ("sell" if not bull and q > 0 else "hold")
            elif rule and rule.startswith("rule_donch"):
                n = prm.get("donchian", 20); hi = max(b["high"] for b in bars_meme[i - n:i]); lo = min(b["low"] for b in bars_meme[i - n:i])
                sig = "sell" if (q > 0 and (not bull or px < lo)) else ("buy" if bull and q == 0 and px > hi else "hold")
            elif rule == "rsi":
                if rs[i] is not None and rs[i - 1] is not None:
                    sig = "buy" if rs[i - 1] < prm.get("lo", 30) <= rs[i] and q == 0 else ("sell" if rs[i - 1] > prm.get("hi", 70) >= rs[i] and q > 0 else "hold")
            elif rule == "grid":
                gp = prm.get("grid_pct", 0.02)
                if buys < prm.get("levels", 4) and px <= ref * (1 - gp * (buys + 1)): sig = "buy"
                elif buys > 0 and px >= ref * (1 + gp * buys): sig = "sell"
                elif buys == 0 and abs(px / ref - 1) > 2 * gp: ref = px
            frac = buy_frac
            if sig == "buy" and usdt > 1:
                n = usdt * frac; q += n * (1 - cst) / px; usdt -= n; trades += 1; buys += 1
            elif sig == "sell" and q > 0:
                usdt += q * px * (1 - cst); q = 0; trades += 1; buys = 0
        return usdt + q * closes[i1 - 1] - C, trades
    base = {"ema_fast": 12, "ema_slow": 26}
    if rule == "rsi": base = {"rsi_period": 14, "lo": 30, "hi": 70}
    if rule == "grid": base = {"grid_pct": 0.02, "levels": 4}
    if rule and rule.startswith("rule_donch"): base["donchian"] = 20
    buy_frac = 1.0 if (rule or "").endswith("_full") else 0.25
    if eff:
        ru = eff.get("rule") or {}
        keys = [p.split(".", 1)[1] for p in (tu.get("params") or []) if str(p).startswith("rule.")] if tu.get("enabled", True) else []
        base = {k: ru[k] for k in keys if isinstance(ru.get(k), (int, float)) and not isinstance(ru.get(k), bool)}
        buy_frac = float((eff.get("gates") or {}).get("buy_fraction_usdt", buy_frac))
    n = min(len(bars_sol), len(bars_meme) if bars_meme else len(bars_sol)); n0 = max(0, n - 720); split = n0 + int(0.7 * (n - n0))
    pen = c["trade_penalty_bps"] / 1e4 * C
    sc = lambda p: tuple(r[0] - pen * r[1] for r in (run(p, n0, split), run(p, split, n)))
    cur = sc(base); best = None
    for k, v in base.items():
        for s in c["steps"]:
            nv = v * s; nv = int(round(nv)) if isinstance(v, int) else nv
            if nv == v: continue
            p = dict(base); p[k] = nv
            if p.get("ema_fast", 0) >= p.get("ema_slow", 1e9): continue
            t, va = sc(p)
            if va - cur[1] >= c["min_improvement_pct"] / 100 * C and t >= cur[0] and (best is None or va > best[1][1]):
                best = ({k: nv}, (t, va))
    return {"status": "candidate" if best else "no_improvement", "current": cur, "best_diff": best[0] if best else None,
            "best": best[1] if best else None, "bars": n - n0}
