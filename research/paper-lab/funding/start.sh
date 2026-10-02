#!/usr/bin/env bash
cd "$(dirname "$0")"
PIDF=run/funding.pid
if [ -f "$PIDF" ] && kill -0 "$(cat $PIDF)" 2>/dev/null; then echo "already running pid $(cat $PIDF)"; exit 0; fi
# setsid não existe em macOS; nohup chega para sobreviver ao fim da shell.
if command -v setsid >/dev/null 2>&1; then
  setsid nohup ./run.sh > /dev/null 2>&1 < /dev/null &
else
  nohup ./run.sh > /dev/null 2>&1 < /dev/null &
fi
echo $! > "$PIDF"
sleep 1
echo "started pid $(cat $PIDF)"
