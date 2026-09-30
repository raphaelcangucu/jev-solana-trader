#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/box/solana-trader/paper
RUN=$ROOT/run
mkdir -p "$RUN" "$ROOT/logs"
export VON_DEVICE=cpu
export HF_HOME=/workspace/jev-alts/hf-cache
export TRANSFORMERS_CACHE=/workspace/jev-alts/hf-cache
export HF_HUB_CACHE=/workspace/jev-alts/hf-cache/hub
export TOKENIZERS_PARALLELISM=false
PIDFILE=$RUN/von.pid
LOG=$ROOT/logs/von_serve.log
PORT=8765
if [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
  echo "von already running pid=$(cat $PIDFILE)"; exit 0
fi
nohup /workspace/jev-alts/venvs/von/bin/von serve --host 127.0.0.1 --port "$PORT" --device cpu >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"
echo "started von pid=$(cat $PIDFILE)"
for i in $(seq 1 180); do
  if curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:${PORT}/openapi.json" \
    || curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:${PORT}/docs"; then
    echo "von HTTP ready after ${i}s"; exit 0
  fi
  if ! kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "von died; see $LOG" >&2; tail -n 40 "$LOG" >&2; exit 1
  fi
  sleep 1
done
echo "WARNING: von still loading after 180s" >&2
exit 0
