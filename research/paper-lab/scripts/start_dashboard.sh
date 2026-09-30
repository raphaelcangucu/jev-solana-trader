#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/box/solana-trader/paper
RUN=$ROOT/run
mkdir -p "$RUN" "$ROOT/logs" "$ROOT/dashboard"
export DASHBOARD_PORT="${DASHBOARD_PORT:-8787}"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
# default to v2 UI when dist/ exists (override with DASHBOARD_UI=legacy)
export DASHBOARD_UI="${DASHBOARD_UI:-v2}"
PIDFILE=$RUN/dashboard.pid
LOG=$ROOT/logs/dashboard.log
PY=/workspace/jev-alts/venvs/von/bin/python
[[ -x $PY ]] || PY=/workspace/jev-alts/venvs/von/bin/python
[[ -x $PY ]] || PY=python3

alive() { [[ -f $1 ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

if alive "$PIDFILE"; then
  # already the listener?
  if ss -tlnp 2>/dev/null | grep -q ":${DASHBOARD_PORT}.*pid=$(cat "$PIDFILE")"; then
    echo "dashboard already running pid=$(cat $PIDFILE)"; exit 0
  fi
fi
# clear stale listener on our port (only our app.py)
if ss -tlnp 2>/dev/null | grep -q ":${DASHBOARD_PORT}"; then
  old=$(ss -tlnp 2>/dev/null | awk -v p=":${DASHBOARD_PORT}" '$0 ~ p { if (match($0,/pid=([0-9]+)/,a)) print a[1]; }' | head -1)
  if [[ -n "${old:-}" ]] && ps -p "$old" -o cmd= | grep -q "solana-trader/paper/dashboard/app.py"; then
    echo "stopping stale dashboard pid=$old"; kill "$old" 2>/dev/null || true; sleep 1; kill -9 "$old" 2>/dev/null || true
  fi
fi
nohup "$PY" "$ROOT/dashboard/app.py" >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"
# wait until THIS pid owns the port (or at least HTTP answers)
echo "started dashboard pid=$(cat $PIDFILE) on 127.0.0.1:${DASHBOARD_PORT} UI=${DASHBOARD_UI}"
for i in $(seq 1 30); do
  if ! kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    # child died (often EADDRINUSE) — adopt whoever holds the port
    live=$(ss -tlnp 2>/dev/null | awk -v p=":${DASHBOARD_PORT}" '$0 ~ p { if (match($0,/pid=([0-9]+)/,a)) print a[1]; }' | head -1 || true)
    if [[ -n "${live:-}" ]]; then echo "$live" >"$PIDFILE"; echo "adopted live dashboard pid=$live"; fi
  fi
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:${DASHBOARD_PORT}/" || true)
  if [[ "$code" == "401" || "$code" == "200" ]]; then
    echo "dashboard HTTP up code=$code after ${i}s pid=$(cat $PIDFILE)"; exit 0
  fi
  sleep 1
done
echo "WARNING: dashboard not ready" >&2
exit 0
