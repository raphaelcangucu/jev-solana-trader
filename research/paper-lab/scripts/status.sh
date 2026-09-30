#!/usr/bin/env bash
ROOT=/home/box/solana-trader/paper
echo "=== paper Solana bot status ==="
echo "time BRT: $(TZ=America/Sao_Paulo date -Iseconds)"
for f in supervisor von laya poorjev sol meme rules lab nightly dashboard tunnel; do
  pf=$ROOT/run/${f}.pid
  if [[ -f $pf ]] && kill -0 "$(cat $pf)" 2>/dev/null; then
    echo "$f: RUNNING pid=$(cat $pf)"
  else
    echo "$f: not running"
  fi
done
if [[ -f $ROOT/dashboard/url.txt ]]; then
  echo "dashboard_url: $(cat $ROOT/dashboard/url.txt)"
fi
python3 - <<'PY'
import json, time
from pathlib import Path
root=Path('/home/box/solana-trader/paper')
sp=root/'status.json'
if sp.exists():
  d=json.loads(sp.read_text())
  age=time.time()-float(d.get('ts') or 0)
  print('--- SOL status.json ---')
  print(f"heartbeat_age_s: {age:.1f}")
  print(f"ts_brt: {d.get('ts_brt')} ok={d.get('ok')} finished={d.get('finished')} cycles={d.get('cycles')} errors={d.get('errors')} skip_px={d.get('skipped_no_price')}")
  print(f"price: {d.get('price_usd')} source={d.get('price_source')} fabricated={d.get('fabricated')} wall_ms={d.get('cycle_wall_ms')}")
  print(f"gates: {d.get('gates')}")
  print(f"jev: {d.get('jev')}")
  print(f"extra_latencies_ms: {d.get('extra_latencies_ms')}")
  # known + dynamic portfolios
  keys = ['baseline','relaxed','v2','hybrid_von_relaxed_cap2','grid_sol_2pct','rsi_sol_1h'] + sorted(k for k in d.keys() if k.endswith('_baseline') or k.endswith('_relaxed') or k.endswith('_article') or k.startswith('hybrid_'))
  seen=set()
  for key in keys:
    if key in seen or key not in d: continue
    seen.add(key)
    b=d.get(key)
    if not b: print(f"{key}: (none)"); continue
    print(f"{key}: equity={b.get('equity_usd')} sol={b.get('sol')} usdt={b.get('usdt')} trades={b.get('trades')} "
          f"chosen={b.get('last_chosen')} final={b.get('last_final')} conf={b.get('last_conf')} "
          f"model={b.get('model')} reasons={b.get('gate_reasons')}")
  if d.get('baseline'):
    print(f"state: {d['baseline'].get('state')}")
  print(f"review_done={d.get('review_done')}")
else:
  print('no SOL status.json yet')
mp=root/'data'/'meme'/'status.json'
if mp.exists():
  d=json.loads(mp.read_text())
  age=time.time()-float(d.get('ts') or 0)
  print('--- MEME status.json ---')
  print(f"heartbeat_age_s: {age:.1f} cycles={d.get('cycles')} errors={d.get('errors')} skip_px={d.get('skipped_no_price')}")
  print(f"restart_brt={d.get('restart_brt')} price_policy={d.get('price_policy')} gates={d.get('gates')}")
  print(f"last={d.get('last_symbol')} px={d.get('last_price')} src={d.get('last_price_source')} "
        f"chosen={d.get('last_chosen')} conf={d.get('last_conf')} "
        f"base={d.get('last_final_baseline')} rel={d.get('last_final_relaxed')}")
  toks=d.get('tokens') or {}
  print(f"meme_models={d.get('meme_models_enabled')} wall_ms={d.get('cycle_wall_ms')} extra_lat={d.get('extra_latencies_ms')}")
  print(f"last_models={d.get('last_models')}")
  for s,v in toks.items():
    b=v.get('baseline') or {}; r=v.get('relaxed') or {}
    line=f"  {s}: px={v.get('price')} src={v.get('price_source')} von_base={b.get('equity_usd')}/{b.get('trades')} von_rel={r.get('equity_usd')}/{r.get('trades')}"
    models=v.get('models') or {}
    for mid, md in models.items():
      bb=md.get('baseline') or {}; rr=md.get('relaxed') or {}
      line += f" | {mid}_b={bb.get('equity_usd')}/{bb.get('trades')} {mid}_r={rr.get('equity_usd')}/{rr.get('trades')}"
    print(line)
else:
  print('no meme status yet')
PY
echo '--- recent SOL log ---'
tail -n 8 "$ROOT/logs/sol_bot.log" 2>/dev/null || true
rp=$ROOT/data/rules/status.json
if [[ -f $rp ]]; then
  python3 - <<'PY2'
import json,time
from pathlib import Path
d=json.loads(Path("/home/box/solana-trader/paper/data/rules/status.json").read_text())
age=time.time()-float(d.get("ts") or 0)
print("--- RULES status.json ---")
print(f"heartbeat_age_s: {age:.1f} cycles={d.get('cycles')} errors={d.get('errors')} ok={d.get('ok')}")
ind=(d.get("indicators") or {}).get("sol") or {}
print(f"SOL 1h: close={ind.get('close_1h')} ema12={ind.get('ema12')} ema26={ind.get('ema26')} rsi={ind.get('rsi')} bull={ind.get('regime_bull')}")
for name,p in (d.get("portfolios") or {}).items():
  print(f"  {name}: eq={p.get('equity_usd')} sig={p.get('last_signal')} trades={p.get('trades')} pos={p.get('position')}")
PY2
fi
echo '--- recent MEME log ---'
tail -n 6 "$ROOT/logs/meme_bot.log" 2>/dev/null || true
echo '--- FUNDING (Hyperliquid funding-carry paper, funding/status.sh) ---'
if [[ -x $ROOT/funding/status.sh ]]; then
  bash "$ROOT/funding/status.sh"; FST=$?
  case $FST in 0) echo "funding: healthy (exit 0)";; 1) echo "funding: STOPPED (exit 1)";; 2) echo "funding: HEARTBEAT STALE (exit 2)";; *) echo "funding: status exit $FST";; esac
else
  echo "funding: status.sh not found"
fi
