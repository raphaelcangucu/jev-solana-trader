#!/usr/bin/env bash
# Instala (ou remove) os agentes launchd do utilizador para o run local em paper.
#   bash scripts/macos/install_launchd.sh             # instala e arranca
#   bash scripts/macos/install_launchd.sh --status    # estado dos três agentes
#   bash scripts/macos/install_launchd.sh --uninstall # pára e remove os plists (não apaga dados)
# Agentes: com.jev.paperlab (supervisor do lab), com.jev.trader-paper (bot real, dry-run), com.jev.caffeinate.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
AGENTS="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"
LOGS="$PAPER_LAB_ROOT/logs"
LABELS=(com.jev.paperlab com.jev.trader-paper com.jev.caffeinate)
# bash 3.2 do macOS: sem arrays associativos.
script_for() {
  case "$1" in
    com.jev.paperlab) echo "$LAB/scripts/macos/lab_service.sh" ;;
    com.jev.trader-paper) echo "$LAB/scripts/macos/trader_service.sh" ;;
    com.jev.caffeinate) echo "$LAB/scripts/macos/caffeinate_service.sh" ;;
  esac
}

plist() {
  local label=$1 script=$2
  cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$script</string></array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PAPER_LAB_ROOT</key><string>$PAPER_LAB_ROOT</string>
    <key>JEV_ALTS_ROOT</key><string>$JEV_ALTS_ROOT</string>
    <key>RUN_UNTIL_BRT</key><string>$RUN_UNTIL_BRT</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>ProcessType</key><string>Standard</string>
  <key>StandardOutPath</key><string>$LOGS/launchd_${label#com.jev.}.log</string>
  <key>StandardErrorPath</key><string>$LOGS/launchd_${label#com.jev.}.log</string>
</dict>
</plist>
EOF
}

case "${1:-install}" in
  --uninstall)
    for l in "${LABELS[@]}"; do
      launchctl bootout "$DOMAIN/$l" 2>/dev/null && echo "parado $l" || echo "$l não estava carregado"
      rm -f "$AGENTS/$l.plist"
    done
    # O supervisor deixa filhos (modelos, bots) com nohup: pará-los também.
    bash "$LAB/scripts/stop.sh" || true
    ;;
  --status)
    for l in "${LABELS[@]}"; do
      if launchctl print "$DOMAIN/$l" >/dev/null 2>&1; then
        launchctl print "$DOMAIN/$l" | awk -v l="$l" '/^\tstate =|^\tpid =|last exit code/ {gsub(/^\t+/,""); printf "%s: %s\n", l, $0}'
      else
        echo "$l: não carregado"
      fi
    done
    ;;
  install|--install)
    mkdir -p "$AGENTS" "$LOGS"
    for l in "${LABELS[@]}"; do
      chmod +x "$(script_for "$l")"
      plist "$l" "$(script_for "$l")" >"$AGENTS/$l.plist"
      plutil -lint -s "$AGENTS/$l.plist"
      launchctl bootout "$DOMAIN/$l" 2>/dev/null || true
      launchctl bootstrap "$DOMAIN" "$AGENTS/$l.plist"
      echo "carregado $l -> $(script_for "$l")"
    done
    echo "fim do run: $RUN_UNTIL_BRT; logs: $LOGS/launchd_*.log"
    ;;
  *) echo "uso: $0 [--install|--status|--uninstall]" >&2; exit 2 ;;
esac
