#!/usr/bin/env bash
# Instala (ou remove) os agentes launchd do utilizador para o run local em paper.
#   bash scripts/macos/install_launchd.sh             # instala e arranca
#   bash scripts/macos/install_launchd.sh --status    # estado dos quatro agentes
#   bash scripts/macos/install_launchd.sh --uninstall # pára e remove os plists (não apaga dados)
#   bash scripts/macos/install_launchd.sh --install-night | --uninstall-night | --kick-night   # só a revisão noturna
# Agentes: com.jev.paperlab (supervisor do lab), com.jev.trader-paper (bot real, dry-run), com.jev.caffeinate,
# com.jev.night-claude (revisão noturna autónoma com o Claude Code, todos os dias à hora de config.json
# claude_night.run_at, padrão 01:30 local; sem RunAtLoad nem KeepAlive).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
AGENTS="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"
LOGS="$PAPER_LAB_ROOT/logs"
LABELS=(com.jev.paperlab com.jev.trader-paper com.jev.caffeinate com.jev.night-claude)
# bash 3.2 do macOS: sem arrays associativos.
script_for() {
  case "$1" in
    com.jev.paperlab) echo "$LAB/scripts/macos/lab_service.sh" ;;
    com.jev.trader-paper) echo "$LAB/scripts/macos/trader_service.sh" ;;
    com.jev.caffeinate) echo "$LAB/scripts/macos/caffeinate_service.sh" ;;
    com.jev.night-claude) echo "$LAB/scripts/macos/night_claude.sh" ;;
  esac
}

# Hora e minuto de claude_night.run_at (config.json), padrão 01:30.
night_at() {
  /usr/bin/python3 - "$PAPER_LAB_ROOT/config.json" <<'PY'
import json, sys
try:
    at = (json.load(open(sys.argv[1])).get("claude_night") or {}).get("run_at") or "01:30"
    h, m = (int(x) for x in at.split(":"))
    assert 0 <= h <= 23 and 0 <= m <= 59
except Exception:
    h, m = 1, 30
print(h, m)
PY
}

# Serviços contínuos: RunAtLoad + relançar se cair. Revisão noturna: só à hora marcada, nunca relançada.
schedule() {
  if [[ "$1" == "com.jev.night-claude" ]]; then
    local h m
    read -r h m <<<"$(night_at)"
    printf '  <key>RunAtLoad</key><false/>\n'
    printf '  <key>StartCalendarInterval</key>\n'
    printf '  <dict><key>Hour</key><integer>%s</integer><key>Minute</key><integer>%s</integer></dict>\n' "$h" "$m"
  else
    printf '  <key>RunAtLoad</key><true/>\n'
    printf '  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>\n'
    printf '  <key>ThrottleInterval</key><integer>30</integer>\n'
  fi
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
    <key>LAB_PYTHON</key><string>$LAB_PYTHON</string>
  </dict>
$(schedule "$label")
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
  install|--install|--install-night)
    # --install-night: só o agente da revisão noturna (não reinicia o lab nem o bot real que já correm).
    TARGETS=("${LABELS[@]}")
    if [[ "${1:-install}" == "--install-night" ]]; then TARGETS=(com.jev.night-claude); fi
    mkdir -p "$AGENTS" "$LOGS"
    for l in "${TARGETS[@]}"; do
      chmod +x "$(script_for "$l")"
      plist "$l" "$(script_for "$l")" >"$AGENTS/$l.plist"
      plutil -lint -s "$AGENTS/$l.plist"
      launchctl bootout "$DOMAIN/$l" 2>/dev/null || true
      launchctl bootstrap "$DOMAIN" "$AGENTS/$l.plist"
      echo "carregado $l -> $(script_for "$l")"
    done
    echo "fim do run: $RUN_UNTIL_BRT; logs: $LOGS/launchd_*.log"
    ;;
  --uninstall-night)
    launchctl bootout "$DOMAIN/com.jev.night-claude" 2>/dev/null && echo "parado com.jev.night-claude" || echo "com.jev.night-claude não estava carregado"
    rm -f "$AGENTS/com.jev.night-claude.plist"
    ;;
  --kick-night)
    # Corre a revisão noturna agora (primeira corrida supervisionada); log em logs/claude_night_<dia>.log.
    launchctl kickstart "$DOMAIN/com.jev.night-claude" && echo "com.jev.night-claude lançado; log: $LOGS/claude_night_*.log"
    ;;
  *) echo "uso: $0 [--install|--install-night|--status|--uninstall|--uninstall-night|--kick-night]" >&2; exit 2 ;;
esac
