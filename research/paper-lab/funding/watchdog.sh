#!/usr/bin/env bash
# One-shot: restart if not running or heartbeat stale (>10 min). Safe to call from any supervisor/cron/@reboot.
# `watchdog.sh --loop` keeps checking every 5 min (foreground).
cd "$(dirname "$0")"
check() {

  PIDF=run/funding.pid
  ALIVE=0; [ -f "$PIDF" ] && kill -0 "$(cat $PIDF)" 2>/dev/null && ALIVE=1
  STALE=0
  if [ -f data/status.json ]; then
    AGE=$(python3 -c "import json,time;print(int(time.time()-json.load(open('data/status.json'))['heartbeat_ms']/1000))" 2>/dev/null || echo 99999)
    [ "$AGE" -gt 600 ] && STALE=1
  fi
  if [ $ALIVE -eq 0 ]; then
    echo "[$(date -Iseconds)] watchdog: not running -> start" >> logs/watchdog.log; ./start.sh >> logs/watchdog.log 2>&1
  elif [ $STALE -eq 1 ]; then
    echo "[$(date -Iseconds)] watchdog: heartbeat stale ${AGE}s -> restart" >> logs/watchdog.log; ./stop.sh >> logs/watchdog.log 2>&1; ./start.sh >> logs/watchdog.log 2>&1
  fi
}
if [ "$1" = "--loop" ]; then while true; do check; sleep 300; done; else check; fi
