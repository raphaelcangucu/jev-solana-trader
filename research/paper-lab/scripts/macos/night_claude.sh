#!/usr/bin/env bash
# Revisão noturna autónoma (paper only): o Claude Code lê o contexto do lab e cria forks SEM aprovação humana
# (decisão do utilizador, 2026-10-03). Lançado pelo launchd às 01:30 (com.jev.night-claude, sem KeepAlive).
#
# Segurança (além dos limites duros de scripts/night_cli.py):
#   - a única ferramenta executável é `$LAB_PYTHON $LAB/scripts/night_cli.py ...` (Bash com regra de prefixo);
#   - Read/Grep/Glob dentro do lab; escrita (Write/Edit) só em run/claude_night/<dia>/;
#   - --permission-mode dontAsk + --permission-prompts none: tudo o que não está permitido é negado, sem perguntas;
#   - --setting-sources project,local: NÃO carrega ~/.claude/settings.json (que permite Bash(*));
#   - deny explícito para .auth/.env/chaves e para comandos de leitura/rede/processos em Bash;
#   - sem --dangerously-skip-permissions; timeout de 1800 s (perl alarm).
# Log: logs/claude_night_<dia>.log com linhas de início, fim e código de saída.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
export PATH="$HOME/.local/bin:$PATH"
ROOT="$PAPER_LAB_ROOT"
DAY="$(TZ=America/Sao_Paulo date +%Y-%m-%d)"
LOG="$ROOT/logs/claude_night_${DAY}.log"
mkdir -p "$ROOT/logs"
say() { echo "$(date -Iseconds) $*" >>"$LOG"; }

if [[ "$(seconds_left)" -le 0 ]]; then
  say "RUN_UNTIL_BRT=$RUN_UNTIL_BRT já passou; não corre"
  exit 0
fi

# enabled / modelo / timeout de config.json:claude_night (sem config → valores padrão).
read -r ENABLED MODEL TIMEOUT_S <<EOF
$(/usr/bin/python3 - "$ROOT/config.json" <<'PY'
import json, sys
try:
    c = json.load(open(sys.argv[1])).get("claude_night") or {}
except Exception:
    c = {}
print("1" if c.get("enabled", True) else "0", c.get("model") or "claude-fable-5-1", int(c.get("timeout_s") or 1800))
PY
)
EOF
if [[ "$ENABLED" != "1" ]]; then
  say "claude_night.enabled=false em config.json; não corre"
  exit 0
fi

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}"
if [[ ! -x "$CLAUDE_BIN" ]]; then
  say "claude não encontrado ($CLAUDE_BIN); não corre"
  exit 1
fi

# Uma corrida de cada vez.
LOCK="$ROOT/run/claude_night.lock"
mkdir -p "$ROOT/run"
# Trinco esquecido por um processo morto (> 2 h) não bloqueia as noites seguintes.
if [[ -d "$LOCK" ]] && (( $(date +%s) - $(stat -f %m "$LOCK") > 7200 )); then
  say "trinco antigo removido ($LOCK)"
  rmdir "$LOCK" 2>/dev/null
fi
if ! mkdir "$LOCK" 2>/dev/null; then
  say "outra revisão noturna em curso ($LOCK); não corre"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

RUN_DIR="$ROOT/run/claude_night/$DAY"
mkdir -p "$RUN_DIR"
CLI="$LAB_PYTHON $LAB/scripts/night_cli.py"

PROMPT="$(cat "$LAB/scripts/macos/night_prompt.md")"
PROMPT="${PROMPT//@CLI@/$CLI}"
PROMPT="${PROMPT//@LAB@/$LAB}"
PROMPT="${PROMPT//@ROOT@/$ROOT}"
PROMPT="${PROMPT//@RUN_DIR@/$RUN_DIR}"
PROMPT="${PROMPT//@DAY@/$DAY}"

# Regras de caminho absoluto: "//caminho" (por isso "/$LAB" com $LAB a começar por "/").
ALLOW=(
  "Bash($CLI *)"
  "Read(/$LAB/**)"
  "Read(/$ROOT/**)"
  "Grep"
  "Glob"
  "Edit(/$RUN_DIR/**)"
)
DENY=(
  "Read(/$ROOT/dashboard/.auth)" "Read(/$LAB/dashboard/.auth)" "Read(**/.auth)"
  "Read(**/.env)" "Read(**/.env.*)" "Read(/$REPO/.env)" "Read(**/keypair.json)" "Read(**/secret.b58)" "Read(**/*.pem)"
  "Bash(cat *)" "Bash(head *)" "Bash(tail *)" "Bash(less *)" "Bash(more *)" "Bash(grep *)" "Bash(rg *)" "Bash(find *)"
  "Bash(ls *)" "Bash(strings *)" "Bash(xxd *)" "Bash(od *)" "Bash(base64 *)" "Bash(awk *)" "Bash(sed *)" "Bash(env *)"
  "Bash(printenv *)" "Bash(curl *)" "Bash(wget *)" "Bash(launchctl *)" "Bash(kill *)" "Bash(pkill *)" "Bash(git *)"
  "WebFetch" "WebSearch"
)
ADD_DIR=()
if [[ "$ROOT" != "$LAB" ]]; then ADD_DIR=(--add-dir "$ROOT"); fi

say "início: modelo=$MODEL timeout=${TIMEOUT_S}s lab=$LAB root=$ROOT run_dir=$RUN_DIR"
cd "$LAB" || exit 1
# alarm: ao fim de TIMEOUT_S o processo recebe SIGALRM (código 142).
/usr/bin/perl -e 'alarm shift; exec @ARGV or die "exec: $!"' "$TIMEOUT_S" \
  "$CLAUDE_BIN" -p "$PROMPT" \
  --model "$MODEL" \
  --permission-mode dontAsk \
  --permission-prompts none \
  --setting-sources project,local \
  --strict-mcp-config \
  --tools "Read,Grep,Glob,Write,Edit,Bash" \
  --allowedTools "${ALLOW[@]}" \
  --disallowedTools "${DENY[@]}" \
  ${ADD_DIR[@]+"${ADD_DIR[@]}"} \
  --output-format text \
  </dev/null >>"$LOG" 2>&1
CODE=$?
say "fim: código de saída $CODE"
# Estado final (ações desta noite e limites restantes) para auditoria no mesmo log.
"$LAB_PYTHON" "$LAB/scripts/night_cli.py" status >>"$LOG" 2>&1 || true
exit "$CODE"
