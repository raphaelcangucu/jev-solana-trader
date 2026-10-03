#!/usr/bin/env bash
# Serviço launchd do bot real em paper: `python -m jev_trader --dry-run` em ciclo contínuo até RUN_UNTIL_BRT.
# --dry-run é obrigatório aqui: o processo nunca abre a chave nem envia swap, mesmo com LIVE_TRADING=1 no ambiente.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
left="$(seconds_left)"
if [[ "$left" -le 0 ]]; then
  echo "$(date -Iseconds) RUN_UNTIL_BRT=$RUN_UNTIL_BRT já passou; não arranca"
  exit 0
fi
cd "$REPO"
export LIVE_TRADING=0
# O von do laboratório serve o bot real também.
export VON_BASE_URL="${VON_BASE_URL:-http://127.0.0.1:8765}"
# alarm: ao chegar a RUN_UNTIL_BRT o processo recebe SIGALRM; o launchd relança, este script vê o fim e sai com 0.
exec /usr/bin/perl -e 'alarm shift; exec @ARGV or die "exec: $!"' "$left" \
  "$TRADER_PYTHON" -m jev_trader --dry-run
