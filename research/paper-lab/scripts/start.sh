#!/usr/bin/env bash
set -euo pipefail
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # código do lab (research/paper-lab)
ROOT="${PAPER_LAB_ROOT:-$LAB}"                           # dados/estado (logs, data, run, status.json)
JEV_ALTS="${JEV_ALTS_ROOT:-/workspace/jev-alts}"         # venvs + hf-cache dos modelos
export PAPER_LAB_ROOT="$ROOT" JEV_ALTS_ROOT="$JEV_ALTS"
RUN=$ROOT/run
mkdir -p "$RUN" "$ROOT/logs"
if [[ -f $RUN/supervisor.pid ]] && kill -0 "$(cat $RUN/supervisor.pid)" 2>/dev/null; then
  echo "already running supervisor pid=$(cat $RUN/supervisor.pid)"; exit 0
fi
nohup bash "$LAB/scripts/supervisor.sh" >>"$ROOT/logs/supervisor.log" 2>&1 &
echo $! >"$RUN/supervisor.pid"
sleep 1
echo "started supervisor pid=$(cat $RUN/supervisor.pid)"
