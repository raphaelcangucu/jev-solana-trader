#!/usr/bin/env bash
# Impede o sono do sistema até RUN_UNTIL_BRT (-s só vale ligado à corrente; -i evita o sono por inatividade).
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
left="$(seconds_left)"
[[ "$left" -le 0 ]] && exit 0
exec /usr/bin/caffeinate -s -i -t "$left"
