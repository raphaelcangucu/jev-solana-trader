#!/usr/bin/env bash
# Bring the paper stack up after a host reboot (idempotent).
# Called from @reboot cron (best-effort) and from the health-check routine.
set -uo pipefail
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # código do lab (research/paper-lab)
ROOT="${PAPER_LAB_ROOT:-$LAB}"                           # dados/estado (logs, data, run, status.json)
JEV_ALTS="${JEV_ALTS_ROOT:-/workspace/jev-alts}"         # venvs + hf-cache dos modelos
export PAPER_LAB_ROOT="$ROOT" JEV_ALTS_ROOT="$JEV_ALTS"
LOG=$ROOT/logs/boot_autostart.log
RUN=$ROOT/run
mkdir -p "$RUN" "$ROOT/logs"
QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

ts() { date -Iseconds; }
log() { echo "$(ts) $*" >>"$LOG"; [[ $QUIET -eq 1 ]] || echo "$*"; }

# Serialize concurrent boot/health calls
exec 9>"$RUN/boot_autostart.lock"
if ! flock -n 9; then
  log "another boot_autostart already running; exit"
  exit 0
fi

BOOT_ID=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || uptime -s 2>/dev/null || echo unknown)
log "boot_autostart begin boot_id=$BOOT_ID"

# Wait for network/DNS (box can take a minute after reboot)
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if getent hosts api.github.com >/dev/null 2>&1 || curl -fsS --max-time 3 https://www.google.com/generate_204 >/dev/null 2>&1; then
    log "network ready after ${i} try(ies)"
    break
  fi
  sleep 5
done

# Best-effort: keep cron alive so @reboot can fire on future boots
if command -v cron >/dev/null 2>&1 || [[ -x /usr/sbin/cron ]]; then
  if ! pgrep -x cron >/dev/null 2>&1; then
    if sudo -n /usr/sbin/service cron start >/dev/null 2>&1 || sudo -n /usr/sbin/cron >/dev/null 2>&1; then
      log "started cron daemon"
    else
      log "could not start cron (non-fatal)"
    fi
  fi
fi

# Main paper stack (supervisor brings models, bots, dashboard, tunnel, funding watchdog)
if [[ -x $LAB/scripts/start.sh ]]; then
  out=$(bash "$LAB/scripts/start.sh" 2>&1) || true
  log "start.sh: $out"
else
  log "ERROR: missing $LAB/scripts/start.sh"
fi

# Funding has its own watchdog; nudge once at boot
if [[ -x $LAB/funding/watchdog.sh ]]; then
  out=$(bash "$LAB/funding/watchdog.sh" 2>&1) || true
  log "funding watchdog: $out"
fi

echo "$BOOT_ID" >"$RUN/last_boot_id"
log "boot_autostart done"
