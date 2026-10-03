#!/usr/bin/env bash
# Serviço launchd do laboratório: corre o supervisor em primeiro plano (modelos, bots, nightly, dashboard, funding).
# Se o supervisor cair, o launchd relança-o; os filhos vivos são reaproveitados pelos pidfiles.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
if [[ "$(seconds_left)" -le 0 ]]; then
  echo "$(date -Iseconds) RUN_UNTIL_BRT=$RUN_UNTIL_BRT já passou; não arranca"
  exit 0
fi
mkdir -p "$PAPER_LAB_ROOT/run" "$PAPER_LAB_ROOT/logs"
# O supervisor escreve o próprio pid; o launchd acompanha este processo.
exec bash "$LAB/scripts/supervisor.sh"
