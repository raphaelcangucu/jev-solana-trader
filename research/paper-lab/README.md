# Paper Solana + memecoin trading bot (von / alexsssaint pattern)

**Simulation only.** Never signs, never sends, never reads `keypair.json` / `secret.b58`.

## Execuções (histórico)

| # | Nome / arquivo | Início (BRT) | Fim (BRT) | Capital por portfólio |
| --- | --- | --- | --- | --- |
| 1 | `archive/run_52usd_2026-09-24/` | 2026-09-24 00:10 | 2026-09-24 21:07 | ~US$52 (espelho da carteira real); memes 50 USDT |
| 2 | `archive/run_1000usd_2026-09-24/` | 2026-09-24 21:07:46 | 2026-09-26 03:54 (último dado exportado) | US$1.000 (0,334150878 SOL + 960,812456 USDT); memes 1.000 USDT |
| 3 | `run_1000usd_2026-09-30` (atual) | 2026-09-30 (recomeço do zero) | — | US$1.000, paper, como a 2 |

- **2026-09-30 — execução 3.** O utilizador decidiu recomeçar do zero, tudo em paper, com US$1.000 por portfólio. O estado da execução 2
  (portfólios, `status.json`, `data/{lab,meme,rules,nightly}`, `reports/`, `reviews/`, relatórios do funding) foi movido para
  `archive/run_1000usd_2026-09-24/` com `scripts/maintenance/restart_run.py` (no repositório com `--keep-balances`, sem preço ao vivo).
  `config.json:experiment` marca a execução 3 (`run_name`, `day1_start_brt`, `previous_runs`). No host, repetir o recomeço com o
  procedimento abaixo, que grava a hora real e reescala o capital ao preço do momento.
- Revisão da regra noturna sobre os logs reais: `archive/run_1000usd_2026-09-24/reviews/percentile_vs_fixed_0.8.md`.

## Parâmetros por tipo de teste (`params.json`)

Os parâmetros deixaram de estar espalhados (`config.json:gates`/`gates_relaxed`/`rule_strategies`, `params` no registry,
valores fixos no `sol_bot`/`meme_bot`/`rules_bot`, limites do tuner no código). A fonte única é **`params.json`** (versionado),
resolvida por `bot/params.py`. Todos os bots (`sol_bot`, `meme_bot`, `rules_bot`, `lab_bot`), o tuner/`create_fork`, a revisão
noturna e o dashboard leem daqui.

### Ordem das camadas

Deep-merge, da mais fraca para a mais forte (objetos fundem-se; listas e escalares, incluindo `null`, substituem):

1. `defaults` — portão do artigo (conf ≥ 0,6, skip < 0,5), cooldown 120 s, 8 trades/h, compra 25% do USDT, execução a mercado, limites de segurança e espaço de busca do tuner.
2. `profiles.<perfil>` — `baseline`, `relaxed` (conf ≥ 0,35 e margem ≥ 0,20 com `margin_gate: true`), `v2` (`extends: relaxed`). O perfil é uma camada própria porque vale para qualquer tipo (H1 relaxed, híbrido, ...).
3. `types.<tipo>` e depois `types.<tipo>.variants.<variante>` (ex.: `rule_regime.variants.full`).
4. `models.<modelo>` — `von`, `laya`, `poorjev`, `jev`, `ensemble`, `rule` (`von+rules` conta como `von`).
5. `assets.<sol|meme>` e depois `assets.meme.symbols.<SYM>` — por exemplo os níveis de saída de SOL e das memecoins.
6. `portfolios.<nome>` — ajuste de um portfólio (ex.: `hybrid_von_relaxed_cap2.gates.max_trades_per_hour = 2`).
7. **Overlay em tempo real** `data/params_overlay.json` (escrito pelo dashboard). Aceita as chaves planas antigas
   (`min_confidence`, `min_prob_margin`, `max_skip_noul`, `buy_fraction_usdt`, `cooldown_seconds`, `max_trades_per_hour`, e `paused`)
   e grupos aninhados (`{"exits": {"enabled": true}}`); nunca mexe em `limits` nem `tuning`.

**Forks:** parâmetros efetivos do pai **sem** o overlay do pai → diff do fork (`params_diff` em `data/lab/registry.json`, só o
diff, como antes) → `portfolios.<fork>` → overlay do fork. `portfolios.<fork>` fica por cima do diff para que uma edição manual
de um fork tenha efeito.

Tipos de teste: `model_gated` (perfis baseline/relaxed/v2), `hybrid` (filtro de regime de SOL nas compras), `rule_grid`,
`rule_rsi`, `rule_regime`, `rule_donchian` (variante `full`: compra 100%, sobe `limits.buy_fraction_usdt_max` para 1,0),
`lab_h1_exits`, `lab_h2_ensemble`, `lab_h3_limit`, `lab_h4_hours`, e `funding_carry`/`real_bot` só como notas: o funding
(`funding/config.json`, com `perp_leverage: 2` na perna curta) e o bot real (`config/params.json` na raiz) não leem este ficheiro.

Grupos de parâmetros (chave desconhecida = erro de validação, para erros de digitação não passarem em silêncio):

| Grupo | Chaves | Onde vale |
| --- | --- | --- |
| `gates` | `min_confidence`, `min_prob_margin`, `margin_gate`, `max_skip_noul`, `cooldown_seconds`, `max_trades_per_hour`, `buy_fraction_usdt`, `min_usdt_trade`, `min_sol_trade`, `max_exposure_frac` | todos (regras usam cooldown, trades/h, tamanho e exposição) |
| `exec` | `mode` (`market`/`limit`), `extra_slippage_bps`, `slippage_bps`, `network_fee_sol`, `offset_bps`, `ttl_min`, `fee_bps` | todos; `limit` só no `lab_bot` |
| `exits` | `enabled`, `tp`, `sl`, `trail`, `trail_arm`, `reentry_cooldown_min` | `sol_bot`, `meme_bot`, `lab_bot` |
| `hours` | `null` ou lista de horas BRT | `sol_bot`, `meme_bot`, `lab_bot` |
| `regime_filter` | `enabled`, `require_bull_for_buy`, `block_if_unknown` | `sol_bot`, `meme_bot`, `lab_bot` |
| `ensemble` | `min_agree`, `pct_threshold`, `min_window` | H2 |
| `rule` | `grid_pct`, `levels`, `rsi_period`, `lo`, `hi`, `ema_fast`, `ema_slow`, `donchian`, `timeframe` | `rules_bot` |
| `tuning` | `enabled`, `params`, `bounds`, `max_rel_change`, `steps`, `train_frac`, `min_improvement_pct`, `trade_penalty_bps` | tuner noturno |
| `limits` | `buy_fraction_usdt_max` (0,5), `max_trades_per_hour_max` (8), `max_exposure_frac_max` (1,0), `leverage` (`never`) | validação |

O tamanho (fração da compra, mínimos, teto de exposição) vive em `gates`; não há um grupo `sizing` separado no lab.
O `rules_bot` recusa `hours` e `exec.mode=limit` (erro de validação); `exits` e `regime_filter` só valem nos **forks de
regra** (ver "Forks de regras" abaixo), nunca nos originais de regra.

### Exemplos

```jsonc
// H1 (saídas) aplicado ao relaxed do sol_bot: só params
"portfolios": { "relaxed": { "exits": { "enabled": true } } }

// Todos os híbridos com cooldown de 5 min (camada de tipo)
"types": { "hybrid": { "gates": { "cooldown_seconds": 300 } } }

// Níveis de saída próprios para o WIF
"assets": { "meme": { "symbols": { "WIF": { "exits": { "tp": 0.08 } } } } }

// O tuner só mexe na confiança dos model_gated, ±10% por noite
"types": { "model_gated": { "tuning": { "params": ["gates.min_confidence"], "max_rel_change": 0.1 } } }
```

Um fork criado pelo tuner guarda só o diff no registry; o efetivo é o do pai mais o diff:

```json
"relaxed__fork1": {"parent": "relaxed", "lineage": "relaxed", "test_type": "model_gated",
                   "params_diff": {"gates": {"min_confidence": 0.4, "cooldown_seconds": 144}}}
```

`python scripts/params_check.py --name relaxed__fork1` mostra `gates.min_confidence = 0.4 ← fork:relaxed__fork1` e
`gates.min_prob_margin = 0.2 ← profiles.relaxed`. A revisão noturna lista, por fork, cada valor que vem do diff, do
`portfolios.<fork>` ou do overlay, com o valor do pai e a camada.

### Editar, verificar, recarregar

- **Ficheiro:** edite `params.json` e corra `python scripts/params_check.py` (tabela de todos os portfólios; `--static` sem
  overlay; `--name X` com a proveniência de cada valor; `--types` vista por tipo; `--json`). Sai com código 1 se houver erros.
- **Hot reload:** os bots verificam o mtime de `params.json`, do overlay e do registry no máximo a cada segundo; não é preciso
  reiniciar nada. O estado dos portfólios não muda.
- **Fail-closed:** JSON ilegível ou estrutura inválida → fica o último documento válido. Portfólio com valores inválidos → fica
  com os últimos parâmetros válidos dele (ou os estáticos sem overlay, se o problema for o overlay); sem nada válido, portão do
  artigo com `paused: true` (hold). O bot nunca cai; o erro aparece no log do bot, em `status.json` (`params.errors`) e na revisão noturna (secção 8).
- **Limites de segurança:** `buy_fraction_usdt ≤ 0,5` e `max_trades_per_hour ≤ 8`, salvo se uma camada subir `limits`
  (tetos absolutos no código: 1,0, 60 e exposição 1,0); `leverage` só `never`; `paper_only: true` obrigatório no topo.
  O executor do lab ainda faz o clamp de `lab_registry.HARD` (cooldown ≥ 30 s etc.), com os tetos de `limits`.
- **Dashboard (API, HTTP Basic):** o separador Controles continua a gravar o overlay (agora validado pelo resolver antes de
  gravar; "restaurar" apaga os overrides em vez de copiar valores). Novos endpoints (o React ainda não os usa):

```bash
A="-u $(cat "${PAPER_LAB_ROOT:-.}/dashboard/.auth")"   # .auth = utilizador:senha (fora do git)
curl -s $A localhost:8787/api/params/effective/hybrid_von_relaxed_cap2   # efetivo + proveniência + erros (?static=true sem overlay)
curl -s $A localhost:8787/api/params/types                                # vista por tipo de teste
curl -s $A localhost:8787/api/params/doc                                  # params.json bruto
curl -s $A -X POST localhost:8787/api/params/layer/types/hybrid \
     -H 'content-type: application/json' -d '{"set": {"gates": {"cooldown_seconds": 300}}}'
curl -s $A -X POST localhost:8787/api/params/layer/portfolios/relaxed \
     -H 'content-type: application/json' -d '{"unset": ["exits.enabled"]}'
curl -s $A -X POST localhost:8787/api/params/relaxed -H 'content-type: application/json' -d '{"min_confidence": 0.4}'  # overlay
```

  A escrita em `params.json` valida **todos** os portfólios com o documento novo e recusa (400, com a lista de erros) se algum
  ficar inválido; cada mudança vai para `logs/param_changes.jsonl` (`type: params_json`). Também em `/api/v2/params/effective/{nome}` e `/api/v2/params/types`.

### Tuner por tipo

O espaço de busca do tuner noturno vem de `tuning` nos parâmetros efetivos do portfólio base: `params` (caminhos `grupo.chave`),
`bounds` (`[mín, máx]` por caminho), `max_rel_change` (±20% por noite por omissão), `steps`, `train_frac`,
`min_improvement_pct`, `trade_penalty_bps`. Um caminho só entra se a secção estiver ativa (`exits.enabled`, `exec.mode=limit`,
`gates.margin_gate`, `ensemble`). Por omissão reproduz a busca antiga: os 5 portões (+ margem no relaxed), as saídas no H1, o
limite no H3, e no H2 só cooldown/trades/h/tamanho + `ensemble.pct_threshold`; regras: `rule.*` (replay walk-forward em
barras de 1 h, `tuner.rule_search`, dentro de `tuning.bounds`; um candidato vira um fork de regra real, com os mesmos caps
7 dias/40). O diff proposto é validado pelo resolver antes de o fork nascer (`params_invalidos: ...` na revisão se não passar).

### Forks de regras (grid, RSI, regime, Donchian e variantes `_full`)

Os originais de regra (`grid_sol_2pct`, `rsi_sol_1h`, `{SYM}_rule_regime[_full]`, `{SYM}_rule_donch_regime[_full]`) podem
ter forks, como os portfólios com portões. `lab_registry.create_fork` aceita como pai um original de regra ou um fork de
regra; a entrada no registry fica com `kind: "rule"`, `runner: "rules_bot"`, `test_type`, `rule` e `variant` do pai.

- **Diff permitido** (`lab_registry.RULE_KEYS` / `RULE_FORK_GROUPS`; outro grupo → `diff_nao_suportado: ...`):
  `rule.*` do próprio tipo (grid: `grid_pct`, `levels`; RSI: `rsi_period`, `lo`, `hi`; regime: `ema_fast`, `ema_slow`;
  Donchian: `donchian`, `ema_fast`, `ema_slow`), `gates.buy_fraction_usdt`, `exits.*` e `regime_filter.*`. Sem
  cooldown/trades/h, `exec`, `hours`, `limits`, `tuning` nem critérios de texto. Os valores passam pelo resolver
  (`ema_fast < ema_slow`, `lo < hi`, fração ≤ `limits.buy_fraction_usdt_max`: 0,5, ou 1,0 nos `_full`).
- **Limites de tuning** (`types.rule_*.tuning.bounds`, usados pelo tuner e pelo `night_cli fork`): `rule.grid_pct`
  [0,005; 0,1], `rule.levels` [1; 10], `rule.rsi_period` [5; 50], `rule.lo` [10; 45], `rule.hi` [55; 90],
  `rule.ema_fast` [4; 50], `rule.ema_slow` [10; 200], `rule.donchian` [5; 120] h, `gates.buy_fraction_usdt` [0,05; 0,5]
  (`variants.full`: [0,05; 1,0]).
- **Execução** (`bot/rules_bot.py`, classe `RuleForks`): no mesmo ciclo do `rules_bot`, depois dos originais e isolada
  deles (um erro nos forks nunca afeta os originais), com o mesmo `CandleBook` e os mesmos sinais
  (`grid_signal`, `rsi_signal`, `rules_engine.meme_rule_signal` — este também usado pelos originais, sem mudança de
  comportamento) e os mesmos portões (cooldown, trades/h, mínimos, teto de exposição), mas com os parâmetros efetivos
  do fork (pai sem overlay → diff → `portfolios.<fork>` → overlay do fork). Recarrega o registry por mtime (forks novos
  entram sem reiniciar). Só age em barras de 1 h fechadas depois do arranque do `rules_bot` e da criação do fork, uma
  vez por barra.
- **Extras só dos forks:** `exits` (TP/SL/trailing verificados a cada ciclo no preço de marcação, níveis do ativo em
  `assets.<sol|meme>.exits` se o diff só ligar `enabled`; depois de uma saída a compra fica bloqueada
  `reentry_cooldown_min`; numa grade, a saída zera os níveis e recentra a referência) e `regime_filter` (compras só com
  SOL EMA 12 > 26; útil na grade e no RSI). O replay do tuner não simula estes extras (só a regra).
- **Estado e logs** (como os forks do `lab_bot`, para `analytics.catalog`, vereditos, `summary.py` e dashboard):
  `data/lab/portfolios/<fork>.json` (criado com os saldos atuais do pai; a grade herda `rule_state`),
  `data/lab/equity/<fork>.jsonl`, trades em `logs/trades.jsonl` / `logs/meme_trades.jsonl` (`strategy: fork:<nome>`),
  decisões em `logs/lab_decisions.jsonl` (`model: rule`, `params_rule`, `indicators`). Resumo em
  `data/rules/status.json` → `rule_forks`. O `lab_bot` ignora estas entradas.
- **Fail-closed:** parâmetros inválidos (qualquer erro do resolver, por exemplo um `portfolios.<fork>` mal escrito),
  estado em falta ou erro interno → hold, com motivo `params_invalidos` (ou `error`) e uma linha no log do `rules_bot`.
- **Quem cria:** o tuner noturno (secção 4: candidato do replay → `create_fork(base, {"rule": ...})`, base = original
  ou lead fork) e `scripts/night_cli.py fork --parent <regra> --diff '{"rule": {"donchian": 40}}' ...` (mesmos limites
  da noite). Exemplo de hipótese: Donchian 40 h ou `exits` nos `*_rule_donch_regime_full`, que compram rompimentos
  noturnos sincronizados e chegaram a perder 5–12% num dia.

### Equivalência com o comportamento anterior

`params.json` foi povoado para que cada portfólio resolva os mesmos valores de antes (teste
`tests/test_lab_params.py`, incluindo todas as hipóteses do registry arquivado da execução 2). Diferenças, só fora do padrão:

- O overlay do dashboard passa a valer para **qualquer** portfólio e chave editável. Antes o `lab_bot` só honrava
  cooldown/trades/h/tamanho, o `rules_bot` só esses três, e o `meme_bot` ignorava o overlay dos portfólios von/laya/poorjev por moeda
  (só a pausa global). Com o overlay atual (`relaxed.min_confidence = 0.35`, igual ao padrão) nada muda.
- O `hybrid_von_relaxed_cap2` herdava o overlay do `relaxed` (partia de `g_rel_eff`); agora só o seu próprio overlay vale.
- Overlays fora dos limites (ex.: `buy_fraction_usdt` 0,8 ou 20 trades/h, que o dashboard aceitava) são recusados e, se já
  estiverem gravados, o portfólio fica nos últimos parâmetros válidos.
- Os `_full` das regras deixam o overlay mudar a fração (antes era forçada a 1,0 depois do overlay).
- `config.json`: `gates`, `gates_relaxed`, `fees.extra_slippage_bps`, `fees.assumed_network_fee_sol`, `market.slippage_bps` e os
  parâmetros em `rule_strategies.strategies.*` (exceto `enabled`) deixam de ser lidos pelos bots (só pelos pontos de entrada
  antigos `bot/main.py`/`meme_main.py`). Os valores continuam lá, iguais, para referência.
- Logs: as razões do filtro de regime do híbrido entram agora na linha de decisão (antes só no `status.json`), com
  `model_action` = a escolha do modelo; a `chosen_action` registada continua `hold` quando o regime bloqueia (as fontes do lab dependem disso).

### Beta vs seleção (passo 3 do HANDOFF)

- Relatórios (`scripts/report.py --day/--cumulative`, `analytics.stats_table`, tabela do dia na revisão noturna): coluna
  **Excesso aj. exposição $** = PnL − exposição média × retorno do ativo, ao lado de *Exposição média %* e *Timing $ (p)*,
  com legenda. Ganho com excesso ajustado ~0 é beta (exposição num mercado em alta), não seleção.
- Novos portfólios do lab, definidos só por parâmetros e semeados por `lab_registry.hypothesis_defs()` (`ensure_hypotheses`
  no arranque do `lab_bot`; numa execução em curso entram no próximo arranque):
  - `h1_exits_hybrid_von_cap2` — H1 (saídas TP/SL/trailing de SOL) sobre as decisões do `hybrid_von_relaxed_cap2`, 2 trades/h.
  - `relaxed_expcap50` — von relaxed com `gates.max_exposure_frac = 0.5`: a compra é reduzida para a exposição a SOL nunca
    passar de 50% do valor do portfólio (motivo `max_exposure` quando não há espaço). O teto existe em todos os bots e no replay do tuner.

## Operação: caminhos (`PAPER_LAB_ROOT`)

Nenhum módulo tem caminho fixo. `bot/paths.py` resolve:

- `ROOT` (dados/estado: `config.json`, `data/`, `logs/`, `run/`, `reports/`, `reviews/`) = env **`PAPER_LAB_ROOT`**, senão a pasta do lab
  (derivada de `bot/paths.py`). `paths.root` no `config.json`, se existir, é sobreposto por `PAPER_LAB_ROOT`; caminhos relativos resolvem contra a raiz.
- `LAB_DIR` (código: `bot/`, `scripts/`, `dashboard/`, `dashboard-v2/dist`) = a pasta do lab. Scripts `.sh` usam
  `LAB=$(dirname $0)/..` e `ROOT=${PAPER_LAB_ROOT:-$LAB}` e exportam `PAPER_LAB_ROOT` para os filhos.
- `JEV_ALTS_ROOT` (venvs `venvs/{von,laya,poorjev}` e `hf-cache`) padrão `/workspace/jev-alts`; `STRATEGY_RESEARCH_ROOT` padrão `/workspace/strategy-research`.

No host antigo basta correr a partir de `/home/box/solana-trader/paper` (código e dados na mesma pasta). Para ler uma exportação sem copiar logs
para o git: `PAPER_LAB_ROOT=/caminho/para/jev-paper-export/paper python scripts/compare_review_cutoffs.py`.

## Recomeçar uma execução (`scripts/maintenance/restart_run.py`)

```bash
scripts/stop.sh && funding/stop.sh                     # o script recusa se houver pid vivo ou heartbeat < 120 s
python scripts/maintenance/restart_run.py --archive-name run_1000usd_2026-09-24 --capital 1000 --dry-run   # só o plano
python scripts/maintenance/restart_run.py --archive-name run_1000usd_2026-09-24 --capital 1000
scripts/start.sh
```

- Move (nunca apaga) para `archive/<nome>/`: `status.json`, `data/portfolio_*`, `data/equity_*`, `data/{meme,rules,lab}` (estado), `data/nightly`,
  `logs/*.jsonl`, logs dos bots, `archive/{logs,data}` (rotações), `reports/*`, `reviews/*` e, salvo `--skip-funding`, o estado/relatórios do funding.
- Copia e mantém vivos: configs, critérios, `data/params_overlay.json` (overlay do dashboard, é configuração), `data/prices.jsonl` e `data/meme/prices/`.
- `criteria_v2.json` fica vivo; o `sol_bot` considera a revisão de arranque feita se ele existir (ou o `.md` do dia de `night_review_at_brt`), por isso
  arquivar `reviews/` não relança a revisão nem sobrescreve os critérios do v2.
- Capital SOL: mesma fração SOL/USDT, escalada a `--capital` ao último preço de `data/prices.jsonl` (≤10 min) ou `--ref-price`; `--keep-balances` não reescala.
- Recusa destino com conteúdo (outro `--archive-name`), atualiza `experiment` (`run_name`, `day1_start_brt`, `previous_runs`) e `memecoins.json`.

## Revisão noturna por percentil (`bot/confidence_audit.py`)

A regra antiga (conf > 0,8 e `approx_pnl` negativo em vendas) nunca disparava com o von e ignorava compras. Agora (`config.json:review`):

- corte = **P90** (`confidence_percentile`) das confianças respondidas (sem fail-closed) do dia revisado; com muitos empates no corte usa-se `>`;
- candidatas = chamadas buy/sell do modelo (`candidates: chosen`; `acted` = só as que viraram ordem); baseline e relaxed contam como uma chamada;
- erro = retorno a `horizon_s` (900 s) contra a chamada além da banda, com o preço de `data/prices.jsonl` (memes: `data/meme/prices/`); sem preço até +5 min → não resolvida;
- banda (`band_mode`): `vol` (padrão) = banda **por ativo** = `band_k` (0,5) × mediana do |retorno a 15 min| desse ativo nos últimos `band_window_s` (3 dias) até ao fim do dia revisado, na mesma série de preços, entre `band_floor` (0,05%) e `band_cap` (1,5%); com menos de `band_min_n` (30) retornos recua para `band` (0,10%). `fixed` = `band` para todos (modo antigo; é também o padrão da função `audit`). As memecoins mexem 2–3× mais do que o SOL, e com 0,10% fixa quase todo o ruído delas contava como erro. A banda usada vai em `bands`/`band_by_asset` (e em cada resultado) e numa tabela da revisão;
- palavras das frases por **lift** (`word_lift`): % dos erros com a palavra − % dos acertos com a palavra; só entram palavras com lift ≥ `lift_min` (0,2), ≥ `lift_min_count` (3) erros, ≥ `lift_min_episodes` (2) episódios de erro e ≥ `lift_min_ref` (3) acertos de referência. Palavras de fundo (calm/deep/quiet… em quase todos os erros e acertos) ficam com lift ≈ 0. A revisão mostra a tabela (% erros / % acertos / lift / log-odds / episódios);
- a proposta só acrescenta frases quando há erros confiantes **e** palavras elegíveis (senão `changed: false`); a barra fixa (`fixed_bar` 0,8) é calculada só para comparação; o título usa o dia revisado.
- Continua **só proposta** (`reviews/criteria_v2_proposed_<data>.json` + `data/nightly/v2_review_tmp.md`); nada altera os critérios em uso.
- `bot/review.py` (variante antiga) está deprecado e delega em `sol_bot.night_review`.

## Revisão noturna autónoma (Claude Code, `scripts/night_cli.py`)

Decisão do utilizador (2026-10-03): no fim da noite o próprio Claude Code decide, **sem aprovação humana**, e cria forks
(nunca altera os originais) com parâmetros ou critérios de texto novos, que depois acompanha nos dias seguintes. **Só paper.**
É o passe lento do artigo: lê só os erros confiantes (confiança ≥ P90 da família e os 15 min seguintes contra a chamada)
mais um resumo de uma linha do resto, e reescreve critérios (reflexão ao estilo GEPA).

- **Quando:** launchd `com.jev.night-claude`, todos os dias às 01:30 locais (`config.json:claude_night.run_at`), depois do
  tuner (00:30) e da rotação de logs (01:00). `scripts/macos/night_claude.sh` corre
  `claude -p <night_prompt.md> --model claude-fable-5-1 --permission-mode dontAsk --permission-prompts none
  --setting-sources project,local` com cwd = pasta do lab, timeout de 1800 s, log em `logs/claude_night_<dia>.log`.
- **O que o Claude pode fazer:** executar só `$LAB_PYTHON scripts/night_cli.py ...` (regra de prefixo do Bash), ler com
  Read/Grep/Glob dentro do lab e escrever só em `run/claude_night/<dia>/` (critérios e diário). Deny explícito para
  `.auth`, `.env`, chaves e comandos de leitura/rede/processos; as definições do utilizador (`~/.claude/settings.json`) não
  são carregadas.
- **Subcomandos** (cada ação vai para `logs/param_changes.jsonl` com `who: "claude-night"` e `night`):

| Comando | Faz |
| --- | --- |
| `context [--hours 24]` | contexto compacto (≤ ~6k tokens): dia N/30, mercado, famílias e notáveis (PnL, ex. B&H, habilidade, timing+p, exposição, C/V, MDD), forks com margem contra o pai, erros confiantes por família (adjetivos dos erros vs dos acertos, episódios), critérios em uso, limites, parâmetros ajustáveis por tipo, placar do bot real |
| `fork --parent N --diff JSON --reason T [--dry-run]` | fork de parâmetros por `lab_registry.create_fork` (resolver valida; o pai nunca muda). Diff só em `gates`/`exec`/`exits`/`hours`/`ensemble`/`regime_filter`, dentro de `tuning.bounds` do tipo (e do clamp do lab). Pai de regra (grid/RSI/regime/Donchian e forks deles): só `rule.*` do tipo, `gates.buy_fraction_usdt`, `exits.*`, `regime_filter.*` — o fork corre no `rules_bot` (ver "Forks de regras") |
| `criteria-fork --parent N --criteria-file F --reason T [--dry-run]` | fork cuja diferença é o texto dos critérios (esquema `criteria_*.json`, sem dígitos, ≤ 300/400/1600 caracteres). Guardado em `data/lab/criteria/<fork>.json` e referenciado em `params_diff.criteria = {file, sha256}`. Pais: portfólios com portões de von/laya/poorjev (SOL e memes) |
| `realbot-criteria --criteria-file F --reason T` | proposta pela auditoria por percentil de `jev_trader.rewrite` com aprovação autónoma (`approve(..., autonomous=True)`, aprovador `claude-night`), **recusada sem escrever nada** se `LIVE_TRADING=1` (ambiente ou `.env`), `config/experiment.json` sem `"mode": "paper"` ou perfil de parâmetros ativo sem `paper_only` |
| `journal --file F` | copia o diário (markdown em `run/`) para `reviews/claude_night_<data BRT>.md` (nunca sobrescreve: `_2`, `_3`) |
| `status` | ações desta noite e limites restantes |

- **Limites** (`config.json:claude_night`): `max_forks_per_night` 6 (fork + criteria-fork), `per_lineage_days` 2 e
  `total_forks` 80 (só neste caminho; o tuner mantém `tuning.caps` 7 dias/40), `max_realbot_per_night` 1, `enabled`.
  `--reason` com 40–800 caracteres (hipótese + o que a confirma/refuta em 3–7 dias). Ficheiros de entrada só de `run/`.
- **Execução dos forks de critérios (`bot/lab_bot.py`):** para cada linha de decisão da fonte, o fork chama o backend do
  modelo (`bot/backends.decide`) com o estado registado nessa linha e os seus critérios; cache LRU limitada por
  (backend, sha256 dos critérios, estado); depois aplica os mesmos portões/saídas/execução das outras entradas. Critérios
  em falta/alterados (sha256), backend desligado ou em erro → hold (fail-closed; o backend fica 30 s em pausa após um erro).
  `logs/lab_decisions.jsonl` regista `model`, `criteria_sha256`, `confidence`, `state`, `cache`, `fail_closed`.
  Os forks de parâmetros de um fork de critérios herdam os critérios (resolver: efetivo do pai + diff).
- **Acompanhamento:** `context` e a revisão do tuner (secção 5) mostram cada fork com quem o criou, o que mudou em
  palavras, margem contra o pai (PnL pp e habilidade US$) e rótulo; `scripts/summary.py` e o dashboard também
  (`fork_who`, `fork_summary`, `fork_reason`, `criteria_summary`). Nada é apagado nem desligado.
- **Instalar** (sem reiniciar o lab): `bash scripts/macos/install_launchd.sh --install-night`; primeira corrida
  supervisionada: `--kick-night`; remover: `--uninstall-night`.

## Testes

`pytest -q` na raiz do repositório corre também `research/paper-lab/tests/` (gates, estado, analytics, auditoria de confiança, caminhos e
recomeço, parâmetros por tipo de teste em `test_lab_params.py`), offline e com `PAPER_LAB_ROOT` numa pasta temporária. `analytics` precisa de `numpy` (`pip install -e .[lab]`); sem ele esses testes fazem skip.

## 2026-09-24 meme clean restart (BRT 2026-09-24T00:33:02.275231-03:00)

- Removed `data/meme/seed_prices.json` and all seed/last_or_seed fallbacks.
- Marks are live-only: Gate.io → Coinpaprika → DexScreener → Jupiter quote (no fabrication).
- If no fresh real price within ~120s, token decision is `skipped_no_price`.
- Wiped meme portfolios, equity curves, price histories, and meme decision/trade logs (built on fake seeds).
- Added parallel **relaxed** portfolios (SOL + each meme) sharing the same von decision:
  - baseline: conf ≥ 0.6, skip_noul < 0.5 (article-faithful)
  - relaxed: conf ≥ 0.35 (~80th pct of observed von conf), prob margin ≥ 0.20, skip_noul < 0.5
- SOL feed checked: Coinbase / Coinpaprika / Jupiter only; stale cache ≤120s; no seed.


## v2 shadow — late start / gate (2026-09-24)

- Night review wrote `criteria_v2.json` + `reviews/2026-09-24.md` at **04:00:03 BRT** and created `data/portfolio_v2.json` with the same starting balances (0.017392206 SOL + 50.00929 USDT).
- **Init bug:** v2 was attached to the **baseline gate** (`conf≥0.6`) instead of the **relaxed gate**, so with von confidence ≤~0.40 it never traded; `status.json` also omitted v2 `sol`/`usdt`/`chosen`.
- **Fix applied; sol_bot restarted **2026-09-24T04:45:30 BRT**:** v2 uses **relaxed gate** (`conf≥0.35`, prob margin ≥0.20, `skip_noul<0.5`, cooldown 120s, max 8/h, buy 25% USDT, sell all SOL) + its **own** von call with `criteria_v2.json` each cycle (extra ~0.3s; alternating criteria is acceptable if latency becomes an issue).
- Restart of sol_bot only (supervisor auto-restarts); baseline/relaxed/meme state and logs preserved.
- Night review audit now includes **relaxed** trades/decisions on future runs (this morning’s review audited 0 baseline trades only; criteria_v2.json not regenerated).


## Multi-model backends (2026-09-24 ~04:49 BRT)

Pluggable System One backends in `models.json` (enable/disable flags). Interface: state + criteria → Choice probs/confidence + skip noul (`bot/backends.py`).

| Backend | Port / endpoint | SOL portfolios | Status |
| --- | --- | --- | --- |
| **von** (default) | `127.0.0.1:8765` | `baseline`, `relaxed`, `v2` | unchanged |
| **laya** | `127.0.0.1:8766` shim | `laya_baseline`, `laya_relaxed` | started mid-day |
| **poorjev** | `127.0.0.1:8767` shim | `poorjev_baseline`, `poorjev_relaxed` | started mid-day |
| **jev** (hosted) | `https://api.typesafe.ai/v1/systemone` | `jev_baseline`, `jev_relaxed`, `jev_article` | **disabled**; needs `JEV_API_KEY` |

- Same initial balances / gates / sizing as von counterparts; own von-like call per model per cycle (**concurrent**). Memes stay on von only (`memes_allow_other_models: false`).
- Decisions log includes `model` field; existing consumers keep working.
- Hosted Jev key: env **`JEV_API_KEY` only** (never logged/written). If missing → status `aguardando chave`. After setting: `export JEV_API_KEY=...` then `scripts/stop.sh` + `scripts/start.sh` (see `scripts/restart_models.sh` + `scripts/test_jev.sh`).
- Start times: `reports/models_start.md`.


## Meme multi-model (laya + poorjev) — 2026-09-24T13:55:13 BRT

- Per-backend flag `backends.*.memes_enabled` in `models.json` (dashboard toggle). Von meme portfolios **untouched**.
- New portfolios per coin: `{SYM}_laya_baseline`, `{SYM}_laya_relaxed`, `{SYM}_poorjev_baseline`, `{SYM}_poorjev_relaxed` — 50 USDT each, same gates/sizing/cooldown as von meme.
- Same adjective state each meme cycle; von/laya/poorjev called **concurrently**.
- Start recorded in `reports/models_start.md`.
- `cloudflared` binary kept at `paper/dashboard/cloudflared` so tunnel survives reboot (preferred by `scripts/start_tunnel.sh`).



## Rule strategies + hybrids — start 2026-09-24T15:09:13.282682-03:00

Paper-only rule portfolios from `$STRATEGY_RESEARCH_ROOT/REPORT.md` (padrão `/workspace/strategy-research`):

| Portfolio | Type | Params |
| --- | --- | --- |
| `grid_sol_2pct` | SOL rule | Grid 2%, 4 levels, 1h |
| `rsi_sol_1h` | SOL rule | RSI(14) 30/70, 1h |
| `hybrid_von_relaxed_cap2` | SOL hybrid | Reuses von relaxed; max 2 trades/h; buy only if SOL EMA12>EMA26 |
| `{SYM}_rule_regime` | Meme rule ×7 | Hold meme only while SOL EMA12>26 |
| `{SYM}_rule_donch_regime` | Meme rule ×7 | Donchian20 + SOL regime |
| `{SYM}_hybrid_poorjev_regime` | Meme hybrid ×7 | Reuses poorjev relaxed; block buys unless SOL regime bull |

- Process: `bot/rules_bot.py` (pid `run/rules.pid`), hybrids inside `sol_bot.py` / `meme_bot.py`.
- Warm-up: historical 1h candles at startup; **no trades on warm-up bars**.
- Logs tagged `strategy=rule:<name>`. Start note: `reports/rules_start.md`.
- Dashboard: section “Estrategias rule / hibridos” + pause toggle.
- Supervisor/status/stop include `rules`.


## Layout
- `bot/sol_bot.py` — SOL/USDT loop (~15s), night review @ 04:00 BRT → v2 shadow
- `bot/meme_bot.py` — 7 memecoins, 1 token / ~60s rotate, shared von, no night-review/v2
- `bot/lib.py` — shared price/von/gates helpers
- `config.json`, `criteria_baseline.json`, `memecoins.json`
- `logs/decisions.jsonl`, `logs/trades.jsonl`, `logs/meme_*.jsonl`
- `status.json`, `data/meme/status.json` heartbeats
- `scripts/{start,stop,status,start_von,supervisor,report}.sh|.py`

## Dashboard v2 (React)

Modern UI (Vite + React + TypeScript + Tailwind + shadcn/ui + Lightweight Charts + TanStack Query + SSE).

- **Source:** `dashboard-v2/`
- **Build output:** `dashboard-v2/dist/` (static files served by the existing FastAPI app)
- **Default URL:** same tunnel + same basic auth (`dashboard/.auth`, user `raphael`) → `/`
- **Legacy UI:** kept at `/legacy` until you remove it
- **SSE:** `/api/v2/stream` (polling fallback every ~12s if the stream drops)
- **Paper only.** No live swaps, no keypair access.

```bash
# install (once) + build
cd dashboard-v2            # a partir da pasta do lab
npm install
npm run build

# restart the Python server so it picks up dist/ (supervisor will also keep it up)
bash scripts/start_dashboard.sh
# if already running: kill the pid in run/dashboard.pid then re-run start_dashboard.sh

# force legacy temporarily
DASHBOARD_UI=legacy bash scripts/start_dashboard.sh
```

Tabs: Visão geral · Portfólios SOL · Memecoins · Regras & Lab · Modelos · Funding (Hyperliquid funding-carry paper: `p1000` + `p1000_pons`) · Controles.

Screenshots (desktop 1440 + mobile): `/workspace/dashboard-shots/`.

Inspiration (patterns only, no code copied): FreqUI (bot overview, trade markers on candles), Hummingbot Dashboard (bot cards / toggles), Jesse (equity curves), OpenBB (dense tables), Ghostfolio (performance vs benchmark), TradingView Lightweight Charts examples (crosshair legend, markers).

## Start / stop / status
```bash
scripts/start.sh      # supervisor (von + sol + meme, auto-restart); raiz = PAPER_LAB_ROOT ou a pasta do lab
scripts/status.sh
scripts/stop.sh
$JEV_ALTS_ROOT/venvs/von/bin/python scripts/report.py   # JEV_ALTS_ROOT padrão /workspace/jev-alts
# → reports/day1.md
```

## Boot autostart (2026-09-25)
After a host reboot the stack does not come up by itself (no systemd; `policy-rc.d` blocks service starts). Recovery:
- `scripts/boot_autostart.sh` — waits for network, starts supervisor + funding watchdog (idempotent). Log: `logs/boot_autostart.log`.
- `@reboot` crontab for user `box` calls that script after 45s (best-effort; cron itself may need a kick).
- Health routine **Saúde do simulador Jev** runs every 30 min at :00 and :30 BRT, calls `boot_autostart.sh`, and notifies only on real outages. Max expected downtime after a reboot: ~30 min.

## Window
- Start: now (2026-09-24 ~00:20 BRT)
- Night review (SOL only): 2026-09-24 04:00 BRT → writes `reviews/2026-09-24.md` + `criteria_v2.json`, starts v2 shadow portfolio
- End new trades: 2026-09-25 00:00 BRT

## Memecoins
BONK, WIF, POPCAT, FARTCOIN, PNUT, MEW, GOAT — see `memecoins.json` for mints/why.
Cadence: rotate 60s (each token ~every 7 min). Marks: CoinGecko with seed bootstrap (Jupiter quote fills only on simulated trades). Night review/v2 **skipped** for memes.

## Gates
Act only if confidence ≥ 0.6 and skip_noul < 0.5; else hold. Cooldown 120s, max 8 trades/hour, buy 25% USDT.
(Valores atuais por portfólio: `params.json` — ver "Parâmetros por tipo de teste".)

## Fill policy (2026-09-24)

Paper fills prefer Jupiter quote; on 429/error, fall back to **live mark ± slip** (same Coinbase/Gate mark already used for decisions). Logged as `fill_mode=mark` with `quote_error`. Not a fabricated price.

## Retention, forks and log rotation (2026-09-24 20:5x BRT)
- **No end date.** `config.json:end_at_brt` is a far-future sentinel (2099-12-31); the supervisor never stops bots.
- **Nothing is ever deactivated or retired** — originals, H1–H4 hypotheses and forks all run indefinitely.
  Forks that trail their parent are only labeled `atrás da original` in the nightly review/dashboard (`report_label` in `data/lab/registry.json`).
- **Fork creation caps** (the only resource control): max 1 new fork per lineage per 7 days, max 40 forks total
  (`config.json:tuning.caps`). When a cap blocks creation the nightly review says so; existing forks never stop.
  Forks reuse existing model decisions (lab_bot tails decision logs) — no extra model calls.
- **Log rotation** (`bot/logio.py`, run by the nightly daemon at 01:00 BRT, after the 00:30 review):
  JSONL files ≥5 MB under `logs/` and `data/` are hard-linked into `archive/<same path>/<stem>.<YYYYMMDDTHHMMSS>.jsonl`
  and the live file is atomically replaced by its last 3000 lines (so bots keep their price history). Archives
  older than 1 day are gzipped. No line is lost (late appends to the old inode land in the archive).
  Readers that need history use `logio.iter_rows(path, since_ts)` (merges archives + live, drops seeded duplicates);
  lab_bot's tail is rotation-aware. Trade logs and `param_changes.jsonl` are never rotated. Text `*.log` > 50 MB are copy-truncated to gz.
