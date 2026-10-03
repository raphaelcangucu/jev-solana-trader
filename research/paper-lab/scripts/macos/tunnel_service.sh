#!/usr/bin/env bash
# Serviço launchd do túnel público (cloudflared quick tunnel → http://127.0.0.1:8787), para abrir o painel no telemóvel.
# O URL *.trycloudflare.com muda a cada arranque; fica em dashboard/url.txt (fora do git) e no log.
# O painel continua atrás do login (.auth); o túnel não muda a autenticação.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
if [[ "$(seconds_left)" -le 0 ]]; then
  echo "$(date -Iseconds) RUN_UNTIL_BRT=$RUN_UNTIL_BRT já passou; não arranca"
  exit 0
fi
CF="$(command -v cloudflared || true)"
if [[ -z "$CF" ]]; then
  echo "$(date -Iseconds) cloudflared não encontrado (brew install cloudflared)" >&2
  exit 1
fi
RUN="$PAPER_LAB_ROOT/run"; LOG="$PAPER_LAB_ROOT/logs/tunnel.log"; URLFILE="$PAPER_LAB_ROOT/dashboard/url.txt"
mkdir -p "$RUN" "$PAPER_LAB_ROOT/logs" "$PAPER_LAB_ROOT/dashboard"
echo $$ >"$RUN/tunnel.pid"   # o painel mostra o túnel como ativo por este pid
# Extrai o URL novo do log em segundo plano assim que aparecer.
(
  for _ in $(seq 1 120); do
    u=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -1)
    if [[ -n "$u" ]]; then echo "$u" >"$URLFILE"; echo "$(date -Iseconds) url=$u"; exit 0; fi
    sleep 1
  done
) &
: >"$LOG"
exec "$CF" tunnel --url http://127.0.0.1:8787 --no-autoupdate >>"$LOG" 2>&1
