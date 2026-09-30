#!/usr/bin/env bash
# Restart model servers + sol/meme bots so new env (e.g. JEV_API_KEY) is picked up.
# Does NOT wipe portfolios/logs. Simulation only.
set -uo pipefail
ROOT=/home/box/solana-trader/paper
RUN=$ROOT/run
stop_one() {
  local f=$1 n=$2
  if [[ -f $f ]]; then
    local p; p=$(cat "$f")
    if kill -0 "$p" 2>/dev/null; then
      echo "stopping $n pid=$p"; kill "$p" 2>/dev/null || true; sleep 1; kill -9 "$p" 2>/dev/null || true
    fi
    rm -f "$f"
  fi
}
# Keep supervisor running; bounce children so it respawns with fresh env from supervisor shell.
# Note: env vars added to the box after supervisor start are NOT in the supervisor process.
# Export JEV_API_KEY in the shell, stop supervisor+children, then start.sh again.
echo "To pick up a newly-set JEV_API_KEY:"
echo "  1) export JEV_API_KEY=...   # in this shell (never commit/log it)"
echo "  2) $ROOT/scripts/stop.sh"
echo "  3) $ROOT/scripts/start.sh   # supervisor inherits current env"
echo "Bouncing local model shims + sol/meme now (von/laya/poorjev)..."
stop_one "$RUN/laya.pid" laya
stop_one "$RUN/poorjev.pid" poorjev
stop_one "$RUN/sol.pid" sol
stop_one "$RUN/meme.pid" meme
# supervisor will restart them within ~10s if still running
echo "done — supervisor should respawn within 10s if running"
