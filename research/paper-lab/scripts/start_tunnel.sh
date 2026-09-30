#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/box/solana-trader/paper
RUN=$ROOT/run
mkdir -p "$RUN" "$ROOT/logs" "$ROOT/dashboard"
PIDFILE=$RUN/tunnel.pid
LOG=$ROOT/logs/tunnel.log
URLFILE=$ROOT/dashboard/url.txt
# Prefer paper-local binary (survives reboot); then PATH
if [[ -x $ROOT/dashboard/cloudflared ]]; then
  CF=$ROOT/dashboard/cloudflared
elif command -v cloudflared >/dev/null 2>&1; then
  CF=$(command -v cloudflared)
else
  echo "cloudflared missing (expected $ROOT/dashboard/cloudflared)" >&2
  exit 1
fi
if [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
  echo "tunnel already running pid=$(cat $PIDFILE) url=$(cat $URLFILE 2>/dev/null || true)"; exit 0
fi
bash "$ROOT/scripts/start_dashboard.sh" >/dev/null 2>&1 || true
# Keep previous URL until new one arrives (avoid empty url.txt on brief restart)
nohup "$CF" tunnel --url http://127.0.0.1:8787 --no-autoupdate >"$LOG" 2>&1 &
echo $! >"$PIDFILE"
echo "started tunnel pid=$(cat $PIDFILE) cf=$CF"
for i in $(seq 1 60); do
  u=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$LOG" | head -1 || true)
  if [[ -n "$u" ]]; then
    echo "$u" >"$URLFILE"
    echo "tunnel url=$u"
    exit 0
  fi
  sleep 1
done
echo "WARNING: no tunnel URL yet; see $LOG" >&2
exit 0
