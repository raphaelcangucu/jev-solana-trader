#!/usr/bin/env bash
# Human status; `status.sh --json` prints data/status.json. Exit 0 healthy, 1 not running, 2 stale heartbeat.
cd "$(dirname "$0")"
PIDF=run/funding.pid
if [ "$1" = "--json" ]; then cat data/status.json 2>/dev/null; echo; fi
RUN=0; [ -f "$PIDF" ] && kill -0 "$(cat $PIDF)" 2>/dev/null && RUN=1
python3 - "$RUN" << 'PY'
import json, sys, time
run = sys.argv[1] == "1"
try:
    s = json.load(open("data/status.json"))
except Exception:
    print("running" if run else "NOT running", "- no status.json yet"); sys.exit(0 if run else 1)
age = time.time() - s["heartbeat_ms"] / 1000
print(f"{'RUNNING' if run else 'NOT RUNNING'} | heartbeat {age:.0f}s ago | started {s.get('started_at')} | mode {s.get('run_mode','?')}")
for k, v in s["benchmarks"].items():
    print(f"  bench {k}: apy={v.get('apy',0)*100:.3f}% stale={v.get('stale')} polled={v.get('polled_at')}")
for pid, p in s["portfolios"].items():
    print(f"  {pid}: nav={p['nav']:.4f} (cap {p['capital']:g}, ret {p['ret_pct']:+.3f}%) funding={p['funding']:+.5f} fees={p['fees']:.4f} "
          f"maxDD={p['max_dd_pct']:.3f}% bench={ {k: round(v,4) for k,v in p['bench'].items()} }")
    for c, x in p["positions"].items():
        print(f"      {c}: size={x['size']} funding_acc={x['funding_accrued']:+.5f} cur_ann={x['current_funding_ann']*100:.2f}%")
print(f"  counters={s.get('counters')} last_error={s.get('last_error')}")
sys.exit(0 if (run and age < 600) else (1 if not run else 2))
PY
