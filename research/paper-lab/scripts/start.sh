#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/box/solana-trader/paper
RUN=$ROOT/run
mkdir -p "$RUN" "$ROOT/logs"
if [[ -f $RUN/supervisor.pid ]] && kill -0 "$(cat $RUN/supervisor.pid)" 2>/dev/null; then
  echo "already running supervisor pid=$(cat $RUN/supervisor.pid)"; exit 0
fi
nohup bash "$ROOT/scripts/supervisor.sh" >>"$ROOT/logs/supervisor.log" 2>&1 &
echo $! >"$RUN/supervisor.pid"
sleep 1
echo "started supervisor pid=$(cat $RUN/supervisor.pid)"
