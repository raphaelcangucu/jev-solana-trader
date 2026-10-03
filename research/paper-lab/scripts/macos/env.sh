#!/usr/bin/env bash
# Ambiente comum aos serviços launchd do laboratório em macOS (paper only).
# Lido por lab_service.sh, trader_service.sh e caffeinate_service.sh; valores já exportados ganham.
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # research/paper-lab
REPO="$(cd "$LAB/../.." && pwd)"                            # raiz do repositório (bot real)
export PAPER_LAB_ROOT="${PAPER_LAB_ROOT:-$LAB}"
export JEV_ALTS_ROOT="${JEV_ALTS_ROOT:-$HOME/jev-alts}"
export LAB_PYTHON="${LAB_PYTHON:-$JEV_ALTS_ROOT/venvs/von/bin/python}"   # bots do lab usam o venv do von
export TRADER_PYTHON="${TRADER_PYTHON:-$REPO/.venv/bin/python}"
# Fim do run local: 30 dias a partir de 2026-09-30 (BRT). Depois disso os serviços saem com código 0 e o launchd não os relança.
export RUN_UNTIL_BRT="${RUN_UNTIL_BRT:-2026-10-30T23:59:59-03:00}"
# Sem túnel público: o dashboard fica só em 127.0.0.1.
export DISABLE_TUNNEL="${DISABLE_TUNNEL:-1}"
export PYTHONUNBUFFERED=1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Segundos até RUN_UNTIL_BRT (0 se já passou).
seconds_left() {
  /usr/bin/python3 - "$RUN_UNTIL_BRT" <<'PY'
import sys, time
from datetime import datetime
print(max(0, int(datetime.fromisoformat(sys.argv[1]).timestamp() - time.time())))
PY
}
