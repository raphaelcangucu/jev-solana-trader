#!/usr/bin/env python3
"""One-off (2026-09-24 evening): portfolios created mid-day inherited baseline's start_price (115.28)
and benchmark_all_usdt. Set them to the mark at each portfolio's OWN start (first equity mark at/after
its start), keep the old value under *_inherited, and log to logs/param_changes.jsonl.
Balances/trades/benchmark_buy_hold (same mix) are untouched. Run only while sol_bot is stopped."""
import json, time, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path("/home/box/solana-trader/paper"); BRT = timezone(timedelta(hours=-3))
dry = "--dry-run" in sys.argv
def first_mark(eqf, t0):
    with open(eqf) as f:
        for l in f:
            r = json.loads(l)
            if r["ts"] >= t0 - 5: return r["ts"], float(r["price"])
for name in ["relaxed", "v2", "laya_baseline", "laya_relaxed", "poorjev_baseline", "poorjev_relaxed", "hybrid_von_relaxed_cap2"]:
    p = ROOT / "data" / f"portfolio_{name}.json"; d = json.loads(p.read_text())
    t0 = datetime.fromisoformat(d["started_brt"]).timestamp() if d.get("started_brt") else float(d["created_ts"])
    ts, px = first_mark(ROOT / "data" / f"equity_{name}.jsonl", t0)
    old_sp = d.get("start_price"); old_all = (d.get("benchmark_all_usdt") or {}).get("usdt")
    new_all = float(d["start_usdt"]) + float(d["start_sol"]) * px
    if abs(float(old_sp) - px) < 1e-9:
        print(name, "ok", px); continue
    print(f"{name}: start_price {old_sp} -> {px} (mark {datetime.fromtimestamp(ts, BRT).isoformat()}); all_usdt {old_all} -> {new_all:.8f}")
    if dry: continue
    d["start_price_inherited"] = old_sp; d["benchmark_all_usdt_inherited"] = old_all
    d["start_price"] = px; d["benchmark_all_usdt"] = {"usdt": new_all}
    d["start_fields_fixed_brt"] = datetime.now(BRT).isoformat()
    p.write_text(json.dumps(d, indent=2))
    with open(ROOT / "logs" / "param_changes.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.time(), "ts_brt": datetime.now(BRT).isoformat(), "portfolio": name,
                            "field": "start_price", "old": old_sp, "new": px, "who": "maintenance",
                            "reason": "inherited baseline start_price; set to mark at portfolio's own start",
                            "also": {"benchmark_all_usdt": [old_all, new_all]}}) + "\n")
