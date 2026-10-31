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
# O supervisor escreve o próprio pid. Ao chegar a RUN_UNTIL_BRT pára o supervisor e todos os filhos (bots, modelos,
# painel, túnel) com stop.sh; o launchd relança, este script vê o fim e sai com 0.
left="$(seconds_left)"
bash "$LAB/scripts/supervisor.sh" &
sup=$!
( sleep "$left"; echo "$(date -Iseconds) fim do run ($RUN_UNTIL_BRT): a parar o laboratório"; bash "$LAB/scripts/stop.sh" ) &
wait "$sup"
