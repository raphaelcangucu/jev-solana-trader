#!/usr/bin/env bash
cd "$(dirname "$0")"
PIDF=run/funding.pid
[ -f "$PIDF" ] || { echo "not running (no pid file)"; exit 0; }
PID=$(cat "$PIDF")
if kill -0 "$PID" 2>/dev/null; then
  kill -TERM "$PID"
  for i in $(seq 1 40); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
  kill -0 "$PID" 2>/dev/null && { echo "force kill"; kill -KILL "$PID"; }
fi
rm -f "$PIDF"; echo "stopped"
