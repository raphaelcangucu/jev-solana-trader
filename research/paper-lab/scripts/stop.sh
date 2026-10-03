#!/usr/bin/env bash
set -uo pipefail
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # código do lab (research/paper-lab)
ROOT="${PAPER_LAB_ROOT:-$LAB}"                           # dados/estado (logs, data, run, status.json)
JEV_ALTS="${JEV_ALTS_ROOT:-/workspace/jev-alts}"         # venvs + hf-cache dos modelos
export PAPER_LAB_ROOT="$ROOT" JEV_ALTS_ROOT="$JEV_ALTS"
RUN=$ROOT/run
stop() {
  local f=$1 n=$2
  if [[ -f $f ]]; then
    local p; p=$(cat "$f")
    if kill -0 "$p" 2>/dev/null; then
      echo "stopping $n pid=$p"; kill "$p" 2>/dev/null || true; sleep 1; kill -9 "$p" 2>/dev/null || true
    fi
    rm -f "$f"
  fi
}
stop "$RUN/supervisor.pid" supervisor
stop "$RUN/sol.pid" sol
stop "$RUN/meme.pid" meme
stop "$RUN/rules.pid" rules
stop "$RUN/dashboard.pid" dashboard
stop "$RUN/tunnel.pid" tunnel
stop "$RUN/laya.pid" laya
stop "$RUN/poorjev.pid" poorjev
stop "$RUN/von.pid" von
pkill -f "$LAB/bot/sol_bot.py" 2>/dev/null || true
pkill -f "$LAB/bot/meme_bot.py" 2>/dev/null || true
pkill -f "$LAB/bot/rules_bot.py" 2>/dev/null || true
pkill -f "$LAB/dashboard/app.py" 2>/dev/null || true
pkill -f "von serve --host 127.0.0.1 --port 8765" 2>/dev/null || true
pkill -f "serve_laya.py" 2>/dev/null || true
pkill -f "serve_poorjev.py" 2>/dev/null || true
pkill -f "cloudflared tunnel --url http://127.0.0.1:8787" 2>/dev/null || true
echo stopped
