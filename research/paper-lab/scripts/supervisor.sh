#!/usr/bin/env bash
set -uo pipefail
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # código do lab (research/paper-lab)
ROOT="${PAPER_LAB_ROOT:-$LAB}"                           # dados/estado (logs, data, run, status.json)
JEV_ALTS="${JEV_ALTS_ROOT:-/workspace/jev-alts}"         # venvs + hf-cache dos modelos
export PAPER_LAB_ROOT="$ROOT" JEV_ALTS_ROOT="$JEV_ALTS"
RUN=$ROOT/run
LOG=$ROOT/logs/supervisor.log
PY="${LAB_PYTHON:-$JEV_ALTS/venvs/von/bin/python}"   # bots do lab: fastapi/uvicorn/numpy já vêm no venv do von
mkdir -p "$RUN" "$ROOT/logs"
export PYTHONUNBUFFERED=1
export VON_DEVICE=cpu
export HF_HOME=$JEV_ALTS/hf-cache
export TRANSFORMERS_CACHE=$JEV_ALTS/hf-cache
export HF_HUB_CACHE=$JEV_ALTS/hf-cache/hub
export TOKENIZERS_PARALLELISM=false
# JEV_API_KEY inherited from parent if set (never write to disk)
echo $$ >"$RUN/supervisor.pid"
echo "$(date -Iseconds) supervisor start pid=$$" >>"$LOG"
# End = config.json end_at_brt + 5 min (far-future sentinel 2099: runs indefinitely)
END_EPOCH=$(python3 -c "import json;from datetime import datetime;print(int(datetime.fromisoformat(json.load(open('$ROOT/config.json'))['end_at_brt']).timestamp())+300)")

ensure_von() {
  if [[ -f $RUN/von.pid ]] && kill -0 "$(cat $RUN/von.pid)" 2>/dev/null; then return 0; fi
  echo "$(date -Iseconds) starting von" >>"$LOG"
  bash "$LAB/scripts/start_von.sh" >>"$LOG" 2>&1 || true
}
ensure_laya() {
  # only if enabled in models.json
  if ! python3 -c "import json;d=json.load(open('$ROOT/models.json'));raise SystemExit(0 if d.get('backends',{}).get('laya',{}).get('enabled') else 1)"; then
    return 0
  fi
  if [[ -f $RUN/laya.pid ]] && kill -0 "$(cat $RUN/laya.pid)" 2>/dev/null; then return 0; fi
  echo "$(date -Iseconds) starting laya" >>"$LOG"
  bash "$LAB/scripts/start_laya.sh" >>"$LOG" 2>&1 || true
}
ensure_poorjev() {
  if ! python3 -c "import json;d=json.load(open('$ROOT/models.json'));raise SystemExit(0 if d.get('backends',{}).get('poorjev',{}).get('enabled') else 1)"; then
    return 0
  fi
  if [[ -f $RUN/poorjev.pid ]] && kill -0 "$(cat $RUN/poorjev.pid)" 2>/dev/null; then return 0; fi
  echo "$(date -Iseconds) starting poorjev" >>"$LOG"
  bash "$LAB/scripts/start_poorjev.sh" >>"$LOG" 2>&1 || true
}
ensure() {
  local name=$1 script=$2 pidfile=$3 logfile=$4 statusfile=$5
  if [[ -f $pidfile ]] && kill -0 "$(cat $pidfile)" 2>/dev/null; then return 0; fi
  if [[ -f $statusfile ]] && grep -q '"finished": true' "$statusfile" 2>/dev/null; then
    echo "$(date -Iseconds) $name finished; not restarting" >>"$LOG"; return 0
  fi
  echo "$(date -Iseconds) starting $name" >>"$LOG"
  nohup "$PY" "$script" >>"$logfile" 2>&1 &
  echo $! >"$pidfile"
  echo "$(date -Iseconds) $name pid=$(cat $pidfile)" >>"$LOG"
}
ensure_dashboard() {
  if [[ -f $RUN/dashboard.pid ]] && kill -0 "$(cat $RUN/dashboard.pid)" 2>/dev/null; then return 0; fi
  if [[ -x $LAB/scripts/start_dashboard.sh ]]; then
    echo "$(date -Iseconds) starting dashboard" >>"$LOG"
    bash "$LAB/scripts/start_dashboard.sh" >>"$LOG" 2>&1 || true
  fi
}
ensure_tunnel() {
  [[ "${DISABLE_TUNNEL:-0}" == "1" ]] && return 0   # macOS local: sem túnel público
  if [[ -f $RUN/tunnel.pid ]] && kill -0 "$(cat $RUN/tunnel.pid)" 2>/dev/null; then return 0; fi
  if [[ -x $LAB/scripts/start_tunnel.sh ]]; then
    echo "$(date -Iseconds) starting tunnel" >>"$LOG"
    bash "$LAB/scripts/start_tunnel.sh" >>"$LOG" 2>&1 || true
  fi
}
# Hyperliquid funding-carry paper service (standalone in funding/; we never edit that folder).
# Its own one-shot watchdog restarts it if stopped or heartbeat-stale; called at boot and every ~5 min.
LAST_FUNDING=0
ensure_funding() {
  local now; now=$(date +%s)
  (( now - LAST_FUNDING < 300 )) && return 0
  LAST_FUNDING=$now
  if [[ -x $LAB/funding/watchdog.sh ]]; then
    bash "$LAB/funding/watchdog.sh" >>"$LOG" 2>&1 || echo "$(date -Iseconds) funding watchdog exit=$?" >>"$LOG"
  fi
}

while true; do
  NOW=$(date +%s)
  if (( NOW > END_EPOCH )); then
    echo "$(date -Iseconds) past end; supervisor exit" >>"$LOG"; break
  fi
  ensure_von
  ensure_laya
  ensure_poorjev
  ensure sol "$LAB/bot/sol_bot.py" "$RUN/sol.pid" "$ROOT/logs/sol_bot.log" "$ROOT/status.json"
  ensure meme "$LAB/bot/meme_bot.py" "$RUN/meme.pid" "$ROOT/logs/meme_bot.log" "$ROOT/data/meme/status.json"
  ensure rules "$LAB/bot/rules_bot.py" "$RUN/rules.pid" "$ROOT/logs/rules_bot.log" "$ROOT/data/rules/status.json"
  [[ -f $LAB/bot/lab_bot.py ]] && ensure lab "$LAB/bot/lab_bot.py" "$RUN/lab.pid" "$ROOT/logs/lab_bot.log" "$ROOT/data/lab/status.json"
  [[ -f $LAB/bot/nightly.py ]] && ensure nightly "$LAB/bot/nightly.py" "$RUN/nightly.pid" "$ROOT/logs/nightly.log" "$ROOT/data/nightly/status.json"
  ensure_dashboard
  ensure_tunnel
  ensure_funding
  sleep 10
done
