#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/box/solana-trader/paper
RUN=$ROOT/run
mkdir -p "$RUN" "$ROOT/logs"
export LAYA_PORT=8766
export HF_HOME=/workspace/jev-alts/hf-cache
export TRANSFORMERS_CACHE=/workspace/jev-alts/hf-cache
export HF_HUB_CACHE=/workspace/jev-alts/hf-cache/hub
export TOKENIZERS_PARALLELISM=false
PIDFILE=$RUN/laya.pid
LOG=$ROOT/logs/laya_serve.log
PY=/workspace/jev-alts/venvs/laya/bin/python
if [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
  echo "laya already running pid=$(cat $PIDFILE)"; exit 0
fi
nohup "$PY" "$ROOT/bot/serve_laya.py" >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"
echo "started laya pid=$(cat $PIDFILE)"
for i in $(seq 1 240); do
  if curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:${LAYA_PORT}/health"; then
    echo "laya HTTP ready after ${i}s"; exit 0
  fi
  if ! kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "laya died; see $LOG" >&2; tail -n 40 "$LOG" >&2; exit 1
  fi
  sleep 1
done
echo "WARNING: laya still loading after 240s" >&2
exit 0
