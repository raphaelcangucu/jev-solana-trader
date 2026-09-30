#!/usr/bin/env bash
cd "$(dirname "$0")"
PIDF=run/funding.pid
if [ -f "$PIDF" ] && kill -0 "$(cat $PIDF)" 2>/dev/null; then echo "already running pid $(cat $PIDF)"; exit 0; fi
setsid nohup ./run.sh > /dev/null 2>&1 < /dev/null &
echo $! > "$PIDF"
sleep 1
echo "started pid $(cat $PIDF)"
