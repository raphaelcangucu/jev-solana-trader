#!/usr/bin/env bash
# Guarda do disco (launchd com.jev.disk-guard, a cada 10 min): protege o run em paper de outros projetos que enchem o
# disco com caches de build. Só age com menos de DISK_GUARD_MIN_GB livres (padrão 30).
#  1) apaga ficheiros com mais de 60 min das caches Go (~/Library/Caches/go-build e caches Go em /private/tmp,
#     reconhecidas pelo README do Go) — builds em curso não são afetados;
#  2) se continuar abaixo do limite: esvazia essas caches e corre `docker builder prune -f`.
# Nunca toca em volumes/imagens Docker, projetos, venvs, node_modules nem nos dados do run.
#   DISK_GUARD_DRY=1 bash disk_guard.sh   # só mostra o que faria
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
MIN_GB="${DISK_GUARD_MIN_GB:-30}"
DRY="${DISK_GUARD_DRY:-0}"
LOG="$PAPER_LAB_ROOT/logs/disk_guard.log"
mkdir -p "$PAPER_LAB_ROOT/logs"

free_gb() { df -g "$HOME" | awk 'NR==2 {print $4}'; }
say() { echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

# Caches Go: a do utilizador + qualquer GOCACHE em /private/tmp (o Go escreve um README a identificá-la).
go_caches() {
  [[ -d "$HOME/Library/Caches/go-build" ]] && echo "$HOME/Library/Caches/go-build"
  find /private/tmp -maxdepth 6 -name README -size -2k 2>/dev/null | while read -r f; do
    grep -q "Go build" "$f" 2>/dev/null && dirname "$f"
  done
}

before=$(free_gb)
if (( before >= MIN_GB )); then
  exit 0
fi
say "disco com ${before} GB livres (< ${MIN_GB}): a limpar caches de build$([[ "$DRY" == "1" ]] && echo " (simulação)")"

# 1) ficheiros antigos (> 60 min) das caches Go
while read -r c; do
  [[ -z "$c" ]] && continue
  sz=$(du -sh "$c" 2>/dev/null | cut -f1)
  if [[ "$DRY" == "1" ]]; then say "  [dry] apagaria ficheiros > 60 min em $c ($sz)"; continue; fi
  find "$c" -type f -mmin +60 -delete 2>/dev/null
  say "  cache Go aparada: $c (era $sz, agora $(du -sh "$c" 2>/dev/null | cut -f1))"
done < <(go_caches)

mid=$(free_gb)
if (( mid < MIN_GB )); then
  # 2) ainda abaixo: esvaziar caches Go e o build cache do Docker
  while read -r c; do
    [[ -z "$c" ]] && continue
    if [[ "$DRY" == "1" ]]; then say "  [dry] esvaziaria $c"; continue; fi
    find "$c" -mindepth 1 -delete 2>/dev/null
    say "  cache Go esvaziada: $c"
  done < <(go_caches)
  if command -v docker >/dev/null 2>&1; then
    if [[ "$DRY" == "1" ]]; then say "  [dry] correria docker builder prune -f"
    else
      out=$(/usr/bin/perl -e 'alarm 600; exec @ARGV' docker builder prune -f 2>&1 | tail -1)
      say "  docker builder prune: $out"
    fi
  fi
fi
say "fim: ${before} GB → $(free_gb) GB livres"
