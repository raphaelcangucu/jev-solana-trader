#!/usr/bin/env python3
"""Paper memecoin rotator. Von baseline+relaxed per token (untouched), plus optional
laya/poorjev per-coin portfolios when models.json backends.*.memes_enabled.
Live prices only. Never signs/sends."""
from __future__ import annotations
import json, os, signal, sys, time, traceback, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/box/solana-trader/paper")
sys.path.insert(0, str(ROOT))

from bot.lib import (
    brt_now, brt_iso, load_cfg, assert_no_keys, build_state, von_system_one,
    apply_gates, jupiter_quote, fetch_meme_prices, append_jsonl, write_json,
    read_jsonl, USDT,
)
from bot.backends import load_models_cfg, decide_many

STOP = False
def _sig(*_a):
    global STOP
    STOP = True

def load_criteria(path: Path) -> dict:
    return json.loads(path.read_text())

def new_portfolio(path: Path, usdt: float, price: float, name: str) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    bh_token = (usdt / price) if price > 0 else 0.0
    data = {
        "name": name, "asset_mode": "token", "sol": 0.0, "usdt": usdt, "token": 0.0,
        "start_sol": 0.0, "start_usdt": usdt, "start_token": 0.0, "start_price": price,
        "benchmark_buy_hold": {"token": bh_token, "usdt": 0.0},
        "benchmark_all_usdt": {"usdt": usdt},
        "realized_pnl_usdt": 0.0, "fees_paid_usdt": 0.0, "fees_paid_sol": 0.0,
        "trade_count": 0, "last_trade_ts": None, "trade_timestamps": [],
        "position": "flat", "recent_pnl_mood": "neutral", "created_ts": time.time(),
    }
    write_json(path, data)
    return data

def equity(d, price):
    return float(d["usdt"]) + float(d.get("token") or 0) * price

def bh_equity(d, price):
    bh = d["benchmark_buy_hold"]
    return float(bh.get("usdt") or 0) + float(bh.get("token") or 0) * price

def position_word(d):
    if float(d.get("token") or 0) > 1e-12:
        return "held"
    return "sold" if d["trade_count"] > 0 else "flat"

def sim_trade(side, data, gcfg, fees, market, price, decision_id, trades_log, mint, decimals, sol_usd, strategy=None):
    extra = float(fees.get("extra_slippage_bps", 5))
    net_sol = float(fees.get("assumed_network_fee_sol", 5e-6))
    net_usdt = net_sol * sol_usd
    slip = max(50, int(market.get("slippage_bps", 50)))
    pnl = 0.0
    data.setdefault("token", 0.0)
    q = None
    fill_meta = {}
    if side == "buy":
        usdt_in = float(data["usdt"]) * float(gcfg["buy_fraction_usdt"])
        if usdt_in < float(gcfg["min_usdt_trade"]):
            return None
        usdt_swap = max(0.0, usdt_in - net_usdt)
        try:
            q = jupiter_quote({"market": market}, USDT, mint, usdt_swap, 6, slip)
            out = float(q["outAmount"]) / (10 ** decimals)
            out_net = max(0.0, out - out * (extra / 10000.0))
            fill_meta = {"fill_mode": q.get("_fill_mode", "jupiter_quote"), "quote_source": q.get("_quote_source")}
        except Exception as e:
            # live mark fill (worse by slip+extra)
            px = price * (1.0 + (slip + extra) / 10000.0)
            out_net = usdt_swap / px if px > 0 else 0.0
            fill_meta = {"fill_mode": "mark", "mark_price": price, "effective_price": px, "quote_error": f"{type(e).__name__}:{e}"}
        fee = usdt_in * (extra / 10000.0) + net_usdt
        data["usdt"] -= usdt_in
        data["token"] = float(data["token"]) + out_net
        data["fees_paid_usdt"] += fee
        fill = {"side": "buy", "usdt_in": usdt_in, "token_out_net": out_net, "fee_usdt": fee, "mint": mint, **fill_meta}
    else:
        tok_in = float(data["token"])
        if tok_in * price < float(gcfg["min_usdt_trade"]):
            return None
        try:
            q = jupiter_quote({"market": market}, mint, USDT, tok_in, decimals, slip)
            out = float(q["outAmount"]) / 1e6
            out_net = max(0.0, out - out * (extra / 10000.0) - net_usdt)
            fill_meta = {"fill_mode": q.get("_fill_mode", "jupiter_quote"), "quote_source": q.get("_quote_source")}
        except Exception as e:
            px = price * (1.0 - (slip + extra) / 10000.0)
            out_net = max(0.0, tok_in * px - net_usdt)
            fill_meta = {"fill_mode": "mark", "mark_price": price, "effective_price": px, "quote_error": f"{type(e).__name__}:{e}"}
        fee = (tok_in * price) * (extra / 10000.0) + net_usdt
        pnl = out_net - tok_in * price
        data["token"] = 0.0
        data["usdt"] += out_net
        data["fees_paid_usdt"] += fee
        data["realized_pnl_usdt"] += pnl
        fill = {"side": "sell", "token_in": tok_in, "usdt_out_net": out_net, "fee_usdt": fee, "approx_pnl": pnl, "mint": mint, **fill_meta}
    now = time.time()
    data["trade_count"] += 1
    data["last_trade_ts"] = now
    data["trade_timestamps"] = (data.get("trade_timestamps") or [])[-99:] + [now]
    data["position"] = position_word(data)
    data["recent_pnl_mood"] = "buoyed" if pnl > 0.05 else ("stung" if pnl < -0.05 else "neutral")
    quote_info = None
    if q:
        quote_info = {
            "inAmount": q.get("inAmount"), "outAmount": q.get("outAmount"),
            "priceImpactPct": q.get("priceImpactPct"),
            "routeLabels": [r.get("swapInfo", {}).get("label") for r in (q.get("routePlan") or [])],
        }
    else:
        quote_info = {"fill_mode": fill_meta.get("fill_mode"), "mark_price": price}
    row = {
        "ts": now, "ts_brt": brt_iso(now), "portfolio": data["name"], "decision_id": decision_id,
        "side": side, "price_mark": price, "fill": fill, "quote": quote_info,
        "paper_only": True, "signed": False, "sent": False,
        "strategy": strategy,
        "portfolio_after": {"token": data["token"], "usdt": data["usdt"], "equity": equity(data, price)},
    }
    append_jsonl(trades_log, row)
    return row

def apply_and_maybe_trade(name, pdata, path, eqp, gcfg, profile, dec, st, price, price_src,
                          allow, cfg, trades_log, decisions_log, sym, mint, decimals, sol_usd,
                          model="von", strategy=None):
    gates = apply_gates(
        dec["chosen_action"], dec["confidence"], dec["skip_noul"], pdata, gcfg, price,
        probabilities=dec.get("probabilities"), profile=profile,
    )
    final = gates["final_action"] if allow else "hold"
    extra = [] if allow else ["run_ended"]
    did = str(uuid.uuid4())
    traded = False
    if allow and final in ("buy", "sell"):
        try:
            tr = sim_trade(final, pdata, gcfg, cfg["fees"], cfg["market"], price, did,
                           trades_log, mint, decimals, sol_usd, strategy=strategy)
            traded = tr is not None
            write_json(path, pdata)
        except Exception as e:
            final = "hold"
            extra.append(f"sim_err:{type(e).__name__}:{e}")
    eq = equity(pdata, price)
    append_jsonl(eqp, {
        "ts": time.time(), "price": price, "token": pdata.get("token"), "usdt": pdata["usdt"],
        "equity": eq, "bh_equity": bh_equity(pdata, price),
        "all_usdt_equity": float(pdata["benchmark_all_usdt"]["usdt"]),
        "trade_count": pdata["trade_count"], "portfolio": name,
    })
    row = {
        "ts": time.time(), "ts_brt": brt_iso(), "decision_id": did, "portfolio": name,
        "gate_profile": profile, "symbol": sym, "mint": mint,
        "state": st["state"], "features": st["features"],
        "price_usd": price, "price_source": price_src,
        "chosen_action": dec["chosen_action"], "probabilities": dec["probabilities"],
        "confidence": dec["confidence"], "skip_noul": dec["skip_noul"],
        "final_action": final, "gate_reasons": gates["gate_reasons"] + extra,
        "blocked_trade": gates["blocked_trade"] or (final == "hold" and dec["chosen_action"] in ("buy", "sell")),
        "latency_ms": dec["latency_ms"], "von_ok": dec["ok"], "von_error": dec.get("error"),
        "traded": traded, "equity_usd": eq, "token": pdata.get("token"), "usdt": pdata["usdt"],
        "bh_equity": bh_equity(pdata, price), "criteria_version": "baseline",
        "night_review": "skipped_for_memecoins",
        "model": model or dec.get("model") or "von",
        "strategy": strategy,
    }
    append_jsonl(decisions_log, row)
    return row

def main() -> int:
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)
    cfg = load_cfg()
    assert_no_keys(cfg)
    meme = json.loads((ROOT / cfg["memecoins"]["config_path"]).read_text())
    tokens = meme["tokens"]
    rotate = float(cfg["memecoins"].get("rotate_seconds", meme.get("cadence", {}).get("rotate_seconds", 60)))
    end_at = datetime.fromisoformat(cfg["end_at_brt"])
    start_usdt = float(meme.get("start_usdt_each", 1000.0))
    criteria = load_criteria(ROOT / "criteria_baseline.json")
    gates_base = cfg["gates"]
    gates_relaxed = cfg.get("gates_relaxed") or dict(gates_base)
    gates_relaxed.setdefault("min_prob_margin", 0.20)
    max_age = float(cfg["market"].get("max_price_age_seconds", 120))

    decisions_log = ROOT / "logs" / "meme_decisions.jsonl"
    trades_log = ROOT / "logs" / "meme_trades.jsonl"
    status_path = ROOT / "data" / "meme" / "status.json"
    prices_dir = ROOT / "data" / "meme" / "prices"
    port_dir = ROOT / "data" / "meme" / "portfolios"
    eq_dir = ROOT / "data" / "meme" / "equity"
    for d in (prices_dir, port_dir, eq_dir, decisions_log.parent):
        d.mkdir(parents=True, exist_ok=True)

    # Never load seed files
    seed_path = ROOT / "data" / "meme" / "seed_prices.json"
    if seed_path.exists():
        seed_path.unlink()
        print("removed seed_prices.json (no fabricated marks)", flush=True)

    marks = fetch_meme_prices(cfg, tokens, prices_dir, max_age=max_age)
    # von portfolios (unchanged names/files)
    portfolios_b = {}
    portfolios_r = {}
    # extra[model][sym][profile] -> pdata ; profiles baseline|relaxed
    extra_ports = {}  # mid -> {sym: {"baseline": pdata, "relaxed": pdata}}
    hybrid_ports = {}  # sym -> pdata for {SYM}_hybrid_poorjev_regime
    histories = {t["symbol"]: read_jsonl(prices_dir / f"{t['symbol']}.jsonl") for t in tokens}

    def meme_models_enabled():
        """Non-von backends with enabled=True and memes_enabled=True (hot-reloaded each cycle)."""
        mc = load_models_cfg()
        out = []
        for mid, b in (mc.get("backends") or {}).items():
            if mid == "von":
                continue
            if b.get("enabled") and b.get("memes_enabled"):
                out.append((mid, b))
        return out, mc

    def ensure_von_ports(sym, px):
        if sym not in portfolios_b:
            portfolios_b[sym] = new_portfolio(port_dir / f"{sym}_baseline.json", start_usdt, px, f"meme_{sym}_baseline")
            portfolios_r[sym] = new_portfolio(port_dir / f"{sym}_relaxed.json", start_usdt, px, f"meme_{sym}_relaxed")

    def ensure_extra_ports(sym, px, started_brt):
        for mid, _bcfg in meme_models_enabled()[0]:
            bucket = extra_ports.setdefault(mid, {})
            if sym in bucket:
                continue
            entry = {}
            for profile in ("baseline", "relaxed"):
                # User-requested names: BONK_poorjev_baseline (no meme_ prefix)
                pname = f"{sym}_{mid}_{profile}"
                fpath = port_dir / f"{sym}_{mid}_{profile}.json"
                pdata = new_portfolio(fpath, start_usdt, px, pname)
                if "started_brt" not in pdata:
                    pdata["started_brt"] = started_brt
                    pdata["model"] = mid
                    write_json(fpath, pdata)
                entry[profile] = pdata
            bucket[sym] = entry

    def ensure_hybrid_ports(sym, px, started_brt):
        if sym in hybrid_ports:
            return
        pname = f"{sym}_hybrid_poorjev_regime"
        fpath = port_dir / f"{pname}.json"
        pdata = new_portfolio(fpath, start_usdt, px, pname)
        if "started_brt" not in pdata:
            pdata["started_brt"] = started_brt
            pdata["strategy"] = f"rule:{pname}"
            pdata["model"] = "poorjev+rules"
            write_json(fpath, pdata)
        hybrid_ports[sym] = pdata

    meme_start_brt = brt_iso()
    for t in tokens:
        sym = t["symbol"]
        px = float((marks.get(sym) or {}).get("price_usd") or 0)
        if px <= 0:
            continue
        ensure_von_ports(sym, px)
        ensure_extra_ports(sym, px, meme_start_brt)
        ensure_hybrid_ports(sym, px, meme_start_brt)

    # Record mid-day meme multi-model start (append if file exists)
    enabled_now = [m for m, _ in meme_models_enabled()[0]]
    starts_note = ROOT / "reports" / "models_start.md"
    if enabled_now:
        block = (
            f"\n## Meme multi-model portfolios — start {meme_start_brt}\n\n"
            f"Extra meme models: {', '.join(enabled_now)}. "
            f"Per coin: `{{SYM}}_{{model}}_baseline` / `{{SYM}}_{{model}}_relaxed` at 50 USDT each. "
            f"Von meme portfolios untouched. Concurrent System One calls each meme cycle.\n\n"
        )
        for mid in enabled_now:
            for t in tokens:
                for profile in ("baseline", "relaxed"):
                    block += f"- **{t['symbol']}_{mid}_{profile}** started={meme_start_brt}\n"
        if starts_note.exists():
            prev = starts_note.read_text()
            if "Meme multi-model portfolios" not in prev:
                starts_note.write_text(prev.rstrip() + "\n" + block)
            # else: section already recorded. Restarts do NOT reset these portfolios, so never append a
            # new "start" section (2026-09-24 fix: a soft restart at 15:08 wrongly appended one).
        else:
            starts_note.write_text("# Model portfolio starts (BRT)\n" + block)

    cycles = errors = skipped_no_price = 0
    started = time.time()
    restart_brt = meme_start_brt
    idx = 0
    finished = False
    sol_usd = 115.0
    print(
        f"meme_bot restart pid={os.getpid()} at={restart_brt} "
        f"tokens={[t['symbol'] for t in tokens]} rotate={rotate}s "
        f"live_marks={list(marks.keys())} max_age={max_age}s "
        f"extra_meme_models={enabled_now}",
        flush=True,
    )

    while not STOP:
        t0 = time.time()
        now = brt_now()
        allow = now < end_at
        # Hot-reload pause from dashboard overlay
        try:
            ov = json.loads((ROOT / "data" / "params_overlay.json").read_text())
            if (ov.get("bots") or {}).get("meme_paused"):
                allow = False
        except Exception:
            pass
        if now >= end_at and not finished:
            finished = True
            print("meme end window reached", flush=True)
        try:
            try:
                sol_status = json.loads((ROOT / "status.json").read_text())
                sol_usd = float(sol_status.get("price_usd") or sol_usd)
            except Exception:
                pass

            # Refresh marks each cycle (gentle inside fetch)
            marks = fetch_meme_prices(cfg, tokens, prices_dir, max_age=max_age)
            for sym2, row in marks.items():
                histories[sym2] = (histories.get(sym2) or []) + [row]
                histories[sym2] = histories[sym2][-2000:]
                px = float(row["price_usd"])
                ensure_von_ports(sym2, px)
                ensure_extra_ports(sym2, px, restart_brt)
                ensure_hybrid_ports(sym2, px, restart_brt)

            t = tokens[idx % len(tokens)]
            idx += 1
            sym = t["symbol"]
            mark = marks.get(sym)
            if not mark or float(mark.get("price_usd") or 0) <= 0:
                skipped_no_price += 1
                print(f"skipped_no_price {sym}", flush=True)
                append_jsonl(decisions_log, {
                    "ts": time.time(), "ts_brt": brt_iso(), "portfolio": f"meme_{sym}",
                    "symbol": sym, "final_action": "skipped_no_price",
                    "gate_reasons": ["skipped_no_price"], "price_usd": None,
                    "price_source": None, "traded": False, "model": "von",
                })
                write_json(status_path, {
                    "ok": True, "ts": time.time(), "ts_brt": brt_iso(), "cycles": cycles,
                    "errors": errors, "skipped_no_price": skipped_no_price,
                    "pid": os.getpid(), "finished": finished or not allow,
                    "last_symbol": sym, "last_final": "skipped_no_price",
                    "restart_brt": restart_brt, "rotate_seconds": rotate,
                    "paper_only": True, "end_at_brt": cfg["end_at_brt"],
                    "price_policy": "live_only_no_seed",
                })
                sleep_for = max(1.0, rotate - (time.time() - t0))
                end_sleep = time.time() + sleep_for
                while time.time() < end_sleep and not STOP:
                    time.sleep(min(0.5, end_sleep - time.time()))
                continue

            price = float(mark["price_usd"])
            price_src = mark.get("source")
            pdata_b = portfolios_b[sym]
            pdata_r = portfolios_r[sym]

            hist = [{"price_usd": h.get("price_usd"), "price_impact_pct": h.get("price_impact_pct", 0)}
                    for h in histories.get(sym) or []]
            # Shared state from von baseline position; all models see same adjective state
            st = build_state(hist, position_word(pdata_b), pdata_b.get("recent_pnl_mood") or "neutral")
            timeout = float(cfg.get("von", {}).get("timeout_seconds", 30))

            # Concurrent: von + every memes_enabled backend
            enabled_extra, models_cfg = meme_models_enabled()
            jobs = [("von", (models_cfg.get("backends") or {}).get("von") or {"base_url": cfg["von"]["base_url"], "kind": "http_systemone"},
                     st["state"], criteria, timeout)]
            for mid, bcfg in enabled_extra:
                jobs.append((mid, bcfg, st["state"], criteria, timeout))
            decs = decide_many(jobs, max_workers=max(2, len(jobs)))
            # Fallback: if von HTTP path fails, try legacy helper once
            dec = decs.get("von")
            if not dec or not dec.get("ok"):
                dec = von_system_one(cfg["von"]["base_url"], st["state"], criteria, timeout)
                dec = dict(dec); dec["model"] = "von"
            else:
                dec = dict(dec); dec["model"] = "von"

            row_b = apply_and_maybe_trade(
                f"meme_{sym}_baseline", pdata_b, port_dir / f"{sym}_baseline.json",
                eq_dir / f"{sym}_baseline.jsonl", gates_base, "baseline",
                dec, st, price, price_src, allow, cfg, trades_log, decisions_log,
                sym, t["mint"], int(t["decimals"]), sol_usd, model="von",
            )
            write_json(port_dir / f"{sym}_baseline.json", pdata_b)

            row_r = apply_and_maybe_trade(
                f"meme_{sym}_relaxed", pdata_r, port_dir / f"{sym}_relaxed.json",
                eq_dir / f"{sym}_relaxed.jsonl", gates_relaxed, "relaxed",
                dec, st, price, price_src, allow, cfg, trades_log, decisions_log,
                sym, t["mint"], int(t["decimals"]), sol_usd, model="von",
            )
            write_json(port_dir / f"{sym}_relaxed.json", pdata_r)

            extra_summary = []
            for mid, _bcfg in enabled_extra:
                dec_m = decs.get(mid)
                if not dec_m:
                    continue
                dec_m = dict(dec_m); dec_m["model"] = mid
                # ensure portfolios exist
                ensure_extra_ports(sym, price, restart_brt)
                entry = extra_ports.get(mid, {}).get(sym) or {}
                for profile, gcfg in (("baseline", gates_base), ("relaxed", gates_relaxed)):
                    pdata = entry.get(profile)
                    if not pdata:
                        continue
                    pname = f"{sym}_{mid}_{profile}"
                    fpath = port_dir / f"{sym}_{mid}_{profile}.json"
                    epath = eq_dir / f"{sym}_{mid}_{profile}.jsonl"
                    row_m = apply_and_maybe_trade(
                        pname, pdata, fpath, epath, gcfg, profile,
                        dec_m, st, price, price_src, allow, cfg, trades_log, decisions_log,
                        sym, t["mint"], int(t["decimals"]), sol_usd, model=mid,
                    )
                    write_json(fpath, pdata)
                    extra_summary.append(f"{mid[0]}{profile[0]}={row_m['final_action']}/{row_m['confidence']:.2f}")

            # Hybrid: copy poorjev relaxed decision; block buys unless SOL EMA regime bull
            rules_st = {}
            rsp = ROOT / "data" / "rules" / "status.json"
            if rsp.exists():
                try:
                    rules_st = json.loads(rsp.read_text())
                except Exception:
                    rules_st = {}
            sol_bull = ((rules_st.get("indicators") or {}).get("sol") or {}).get("regime_bull")
            h_cfg = ((cfg.get("rule_strategies") or {}).get("strategies") or {}).get("hybrid_poorjev_regime") or {}
            h_enabled = bool((cfg.get("rule_strategies") or {}).get("enabled", True)) and h_cfg.get("enabled", True)
            # overlay pause
            try:
                ov = json.loads((ROOT / "data" / "params_overlay.json").read_text())
            except Exception:
                ov = {}
            if (ov.get("bots") or {}).get("rules_paused"):
                h_enabled = False
            pname_h = f"{sym}_hybrid_poorjev_regime"
            if ((ov.get("portfolios") or {}).get(pname_h) or {}).get("paused"):
                h_enabled = False
            if ((ov.get("portfolios") or {}).get("hybrid_poorjev_regime") or {}).get("paused"):
                h_enabled = False
            dec_pj = decs.get("poorjev")
            if h_enabled and dec_pj and sym in hybrid_ports:
                dec_h = dict(dec_pj); dec_h["model"] = "poorjev+rules"
                extra_r = []
                if dec_h.get("chosen_action") == "buy":
                    if sol_bull is None:
                        dec_h["chosen_action"] = "hold"; extra_r.append("sol_regime_unknown")
                    elif h_cfg.get("require_sol_regime_bull_for_buy", True) and not sol_bull:
                        dec_h["chosen_action"] = "hold"; extra_r.append("sol_regime_bear_block_buy")
                pdata_h = hybrid_ports[sym]
                fpath_h = port_dir / f"{pname_h}.json"
                epath_h = eq_dir / f"{pname_h}.jsonl"
                g_h = dict(gates_relaxed)
                ov_h = (ov.get("portfolios") or {}).get(pname_h) or {}
                for k in ("min_confidence", "min_prob_margin", "max_skip_noul",
                          "buy_fraction_usdt", "cooldown_seconds", "max_trades_per_hour"):
                    if k in ov_h and ov_h[k] is not None:
                        g_h[k] = ov_h[k]
                row_h = apply_and_maybe_trade(
                    pname_h, pdata_h, fpath_h, epath_h, g_h, "relaxed",
                    dec_h, st, price, price_src, allow, cfg, trades_log, decisions_log,
                    sym, t["mint"], int(t["decimals"]), sol_usd,
                    model="poorjev+rules", strategy=f"rule:{pname_h}",
                )
                if extra_r:
                    row_h["gate_reasons"] = list(row_h.get("gate_reasons") or []) + extra_r
                write_json(fpath_h, pdata_h)
                extra_summary.append(f"hyb={row_h['final_action']}/{row_h['confidence']:.2f}")

            cycles += 1
            wall_ms = round((time.time() - t0) * 1000, 1)
            snap = {}
            for s in portfolios_b:
                px = float((marks.get(s) or {}).get("price_usd") or 0)
                pb, pr = portfolios_b[s], portfolios_r[s]
                entry = {
                    "price": px, "price_source": (marks.get(s) or {}).get("source"),
                    "von": {
                        "baseline": {
                            "equity_usd": equity(pb, px) if px else None,
                            "usdt": pb["usdt"], "token": pb.get("token"), "trades": pb["trade_count"],
                            "bh_equity": bh_equity(pb, px) if px else None,
                        },
                        "relaxed": {
                            "equity_usd": equity(pr, px) if px else None,
                            "usdt": pr["usdt"], "token": pr.get("token"), "trades": pr["trade_count"],
                            "bh_equity": bh_equity(pr, px) if px else None,
                        },
                    },
                    # backward-compat flat keys used by older dashboard/status
                    "baseline": {
                        "equity_usd": equity(pb, px) if px else None,
                        "usdt": pb["usdt"], "token": pb.get("token"), "trades": pb["trade_count"],
                        "bh_equity": bh_equity(pb, px) if px else None,
                    },
                    "relaxed": {
                        "equity_usd": equity(pr, px) if px else None,
                        "usdt": pr["usdt"], "token": pr.get("token"), "trades": pr["trade_count"],
                        "bh_equity": bh_equity(pr, px) if px else None,
                    },
                    "models": {},
                }
                for mid, bucket in extra_ports.items():
                    if s not in bucket:
                        continue
                    md = {}
                    for profile in ("baseline", "relaxed"):
                        pdata = bucket[s][profile]
                        md[profile] = {
                            "equity_usd": equity(pdata, px) if px else None,
                            "usdt": pdata["usdt"], "token": pdata.get("token"),
                            "trades": pdata["trade_count"],
                            "bh_equity": bh_equity(pdata, px) if px else None,
                            "started_brt": pdata.get("started_brt"),
                        }
                    entry["models"][mid] = md
                # rule hybrid portfolio
                if s in hybrid_ports:
                    hp = hybrid_ports[s]
                    entry["hybrid_poorjev_regime"] = {
                        "equity_usd": equity(hp, px) if px else None,
                        "usdt": hp["usdt"], "token": hp.get("token"),
                        "trades": hp["trade_count"],
                        "bh_equity": bh_equity(hp, px) if px else None,
                        "started_brt": hp.get("started_brt"),
                        "strategy": hp.get("strategy"),
                    }
                snap[s] = entry

            latencies = {mid: (decs.get(mid) or {}).get("latency_ms") for mid in decs}
            write_json(status_path, {
                "ok": True, "ts": time.time(), "ts_brt": brt_iso(), "cycles": cycles,
                "errors": errors, "skipped_no_price": skipped_no_price,
                "pid": os.getpid(), "finished": finished or not allow,
                "last_symbol": sym, "last_final_baseline": row_b["final_action"],
                "last_final_relaxed": row_r["final_action"],
                "last_chosen": dec["chosen_action"], "last_conf": dec["confidence"],
                "last_skip": dec["skip_noul"], "last_latency_ms": dec["latency_ms"],
                "last_state": st["state"], "last_price": price, "last_price_source": price_src,
                "last_models": {
                    mid: {
                        "chosen": (decs.get(mid) or {}).get("chosen_action"),
                        "conf": (decs.get(mid) or {}).get("confidence"),
                        "ok": (decs.get(mid) or {}).get("ok"),
                        "latency_ms": (decs.get(mid) or {}).get("latency_ms"),
                    }
                    for mid in ["von"] + [m for m, _ in enabled_extra]
                },
                "extra_latencies_ms": latencies,
                "cycle_wall_ms": wall_ms,
                "meme_models_enabled": ["von"] + [m for m, _ in enabled_extra],
                "restart_brt": restart_brt, "rotate_seconds": rotate, "tokens": snap,
                "night_review": "skipped", "paper_only": True,
                "price_policy": "live_only_no_seed_max_age_120s",
                "uptime_seconds": round(time.time() - started, 1),
                "end_at_brt": cfg["end_at_brt"],
                "gates": {
                    "baseline_min_conf": gates_base["min_confidence"],
                    "relaxed_min_conf": gates_relaxed["min_confidence"],
                    "relaxed_min_prob_margin": gates_relaxed.get("min_prob_margin"),
                },
            })
            extra_part = " ".join(extra_summary) or "extra=none"
            print(
                f"meme cycle={cycles} {sym} px={price:.8g} src={price_src} "
                f"chosen={dec['chosen_action']} conf={dec['confidence']:.3f} "
                f"base={row_b['final_action']} rel={row_r['final_action']} "
                f"lat={dec['latency_ms']:.0f}ms wall={wall_ms:.0f}ms "
                f"eq_b={row_b['equity_usd']:.4f} eq_r={row_r['equity_usd']:.4f} {extra_part}",
                flush=True,
            )
        except Exception as e:
            errors += 1
            print(f"meme error: {e}\n{traceback.format_exc()}", flush=True)
            write_json(status_path, {
                "ok": False, "error": str(e), "ts_brt": brt_iso(), "cycles": cycles,
                "errors": errors, "pid": os.getpid(), "finished": finished,
            })

        if finished:
            cur = json.loads(status_path.read_text()) if status_path.exists() else {}
            cur.update({"finished": True, "finished_brt": brt_iso(), "ok": True})
            write_json(status_path, cur)
            break

        sleep_for = max(1.0, rotate - (time.time() - t0))
        end_sleep = time.time() + sleep_for
        while time.time() < end_sleep and not STOP:
            time.sleep(min(0.5, end_sleep - time.time()))

    print(f"meme_bot stopped cycles={cycles} errors={errors}", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
