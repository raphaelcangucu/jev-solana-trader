# Passagem de contexto — sessão Cursor → nova sessão

Documento de continuidade. Resume o trabalho feito em Cursor até 2026-09-26 e o que falta. Escrito em 2026-09-29 a partir do repositório, dos anexos da sessão Cursor e da exportação do laboratório de paper trading (`jev-paper-export`).

## 0. Estado em 2026-09-30 (branch `feat/scoreboard-and-percentile-review`)

Decisões do utilizador nesta data: a experiência **recomeça do zero em 2026-09-30**, e tudo corre em **paper trading** para simular o que se pode ganhar. `LIVE_TRADING` continua desligado. Os dados até 2026-09-26 ficam arquivados e só serviram para validar o método da revisão.

Passos da secção 7:

| Passo | Estado |
| --- | --- |
| 1. Estado atual do lab | Substituído pelo reinício. Execução 2 arquivada em `research/paper-lab/archive/run_1000usd_2026-09-24/`; `config.json` marca a execução 3 (US$1.000, 2026-09-30). **Falta correr no host:** `scripts/stop.sh && funding/stop.sh`, `python scripts/maintenance/restart_run.py --archive-name run_1000usd_2026-09-24 --capital 1000 --dry-run`, depois sem `--dry-run`, e `scripts/start.sh`. |
| 2. Placar do bot real | Feito: `python -m jev_trader score [--json]`, sobre o livro de papel. |
| 3. Separar beta de seleção | Parcial: a auditoria passa a avaliar compras a 15 min (hit rate do `relaxed` 35,9%, do híbrido 33,3% na execução 2). Destaque do excesso ajustado à exposição nos relatórios e H1 aplicado ao `relaxed` continuam por fazer. |
| 4. Revisão noturna | Feito: corte por percentil (P90) em `bot/confidence_audit.py`, título com a data revisada. Comparação com a barra 0,8 em `archive/run_1000usd_2026-09-24/reviews/percentile_vs_fixed_0.8.md`. |
| 5. `rewrite --approve` | Feito: `python -m jev_trader rewrite --propose / --approve <ficheiro> / --reject <ficheiro>`, `config/criteria.json` só por aprovação. |
| 6. Lab portável | Feito: `PAPER_LAB_ROOT` (por omissão, a pasta do lab); 35 testes em `research/paper-lab/tests/`. |

Bot real em paper: o livro parte de `config/experiment.json` (0.017392206 SOL + 50.00929 USDT, lido do RPC público às 00:50 BRT, SOL = 119,305). Em dry-run cada decisão que passa os portões vira um fill simulado (`logs/paper_book.json`, `logs/paper_trades.jsonl`), com o mesmo tamanho do swap ao vivo e 10 bps de custo. Logs antigos em `logs/archive/run0_2026-09-23/`.

**Atenção:** com `CONFIDENCE_THRESHOLD=0.55` (valor do artigo) o von, cuja confiança fica em ~0,2–0,45, nunca passa o portão, e o livro de papel fica parado. Para o paper medir alguma coisa é preciso baixar o limiar (o `relaxed` do lab usa 0,35 com margem de 0,20) — decisão pendente do utilizador.

Testes: `pytest -q` na raiz → 85 passed (50 do bot, 35 do lab; o lab precisa de `numpy`, extra `pip install -e .[lab]`).

## 1. Contexto e objetivo

O projeto testa, com dinheiro pequeno e registo público, o padrão de alex saint (@alexsssaint), "System One": a cada ~15 s o mercado vira uma frase de ~12 adjetivos (nenhum número no texto do modelo), um classificador responde `buy` / `sell` / `hold` com confiança e um veto `skip_this_cycle`; confiança baixa ou skip alto viram `hold` (fail-closed). À noite, um passe relê os erros confiantes e propõe critérios novos, sempre com portão humano.

A pergunta do experimento: este loop, com estado só em adjetivos e portões de confiança, melhora o resultado de um livro pequeno em relação a deixá-lo parado?

Duas frentes existem:

1. **Bot real (este repositório, raiz):** `jev_trader`, carteira pública `GNJv4FcMb4j1A6NFiVaaHkGVTZ5p5A7ea9GsFgccS75r`, livro de partida 0.017392206 SOL + 50.00929 USDT (2026-09-23 ~23:30 BRT). Corre em dry-run por omissão; ao vivo só com `LIVE_TRADING=1`.
2. **Laboratório de paper trading (`research/paper-lab/`):** simulação sem chaves, com 107 portfólios de US$1.000 cada (SOL e sete memecoins), vários modelos, regras clássicas, híbridos e hipóteses H1–H4. Foi aqui que a maior parte do trabalho da sessão Cursor aconteceu.

## 2. O que existe no repositório

| Caminho | Conteúdo |
| --- | --- |
| `README.md` | Arquitetura, os 12 adjetivos, portões, dry-run e ao vivo, segurança da carteira, critérios de sucesso, desenho da reescrita noturna. |
| `docs/EXPERIMENT.md` | Livro inicial e as transações que o formaram. |
| `src/jev_trader/` | `config.py` (ambiente; chave só via `SOLANA_KEYPAIR_PATH` no swap), `state.py` (12 adjetivos), `decide.py` (critérios do artigo, cliente von, portões), `swap.py` (Jupiter Ultra, assinatura só do slot do taker), `loop.py` (ciclo e JSONL), `__main__.py`. |
| `tests/` | 16 testes: portões e limites, parsing fail-closed, estado sem dígitos, assinatura gasless, ciclo dry-run e ao vivo sem tocar em chave. |
| `logs/` | `trades.jsonl` (linha seed do swap gasless) e `decisions.jsonl` (primeiros ciclos, todos `fail_closed` porque o von não estava no ar). |
| `research/jev-alts/` | Comparação de alternativas abertas ao Jev (ver secção 3). |
| `research/paper-lab/` | Instantâneo do laboratório: código, configuração, relatórios, revisões, estado dos portfólios e dashboard (ver secção 4). |

### Como correr os testes

```bash
python3.10 -m venv .venv          # 3.10+ chega para o ciclo; von-sdk exige 3.12+
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
```

Resultado registado em 2026-09-29 (Python 3.10.10, solders 0.29.0, httpx 0.28.1, pytest 9.1.1, venv fora do repositório): **16 passed in 0.92s**.

Ciclo único sem chave: `cp .env.example .env && python -m jev_trader --dry-run --once`.

## 3. Conclusões da pesquisa (`research/jev-alts/`)

- `REPORT.md` classificou 16 projetos abertos que imitam o Jev hospedado da TypeSafe. Numa máquina só com CPU (8 vCPU, ~15 GiB, sem GPU) foram testados **von** (`von-sdk`, ModernBERT ~395M), **Laya** (~421M) e **poorjev** (DeBERTa NLI ~400 MB). Os três instalam e respondem; latências quentes de ~380 ms, ~300 ms e ~140 ms.
- `ARTICLE_COMPARE.md` comparou-os contra o padrão do artigo. Vencedor: **von** (6.82/10), por ter `POST /v1/systemone` nativo, probabilidades completas, skip contínuo, sanidade direcional 4/4 e determinismo. Laya (6.73) é quase uniforme em jargão curto; poorjev (6.27) é muito confiante e não tem API compatível (precisou de um shim).
- Os anexos da sessão Cursor (`ARTICLE_COMPARE`, `REPORT`, `article_citations`, `cases.json`) são idênticos aos ficheiros já presentes em `research/jev-alts/`.

## 4. Laboratório de paper trading (`research/paper-lab/`)

Conteúdo do instantâneo: `README.md` do lab (histórico de alterações e operação), `config.json`, `criteria_*.json`, `models.json`, `memecoins.json`, `status.json`; `bot/` (loops SOL, memes, regras, lab, revisão noturna, tuner, shims Laya/poorjev); `dashboard/` (FastAPI) e `dashboard-v2/` (React); `scripts/` (supervisor, arranque, relatório); `funding/` (código, configuração e relatórios); `reports/`, `reviews/`; em `data/`, estado atual de cada portfólio, `nightly/verdicts.json`, `lab/registry.json` e `params_overlay.json`; `archive/run_52usd_2026-09-24/` (configuração, relatórios e revisões da execução de $52).

### Desenho

- **Somente paper.** Nunca assina, nunca envia, recusa ler `keypair.json` / `secret.b58` (`config.json: paper_only`, `forbid_keypair_paths`, `live_trading_enabled: false`).
- Preços apenas reais (Coinbase, Gate.io, Coinpaprika, DexScreener, Jupiter); sem preço fresco em ≤120 s, o ciclo fica `skipped_no_price`. Fills simulados com cotação Jupiter/Raydium ao tamanho real da ordem; fallback para mark ± slippage registado como `fill_mode=mark`.
- **Execução 1 ($52):** 2026-09-24 00:10 → 21:07 BRT, espelho da carteira real. Arquivada em `archive/run_52usd_2026-09-24/`.
- **Execução 2 ($1.000, a atual):** início em **2026-09-24 21:07:46 BRT**, sem data de fim. Portfólios SOL começam com 0.334150878 SOL + 960.812456 USDT (a mistura de $52 escalada a SOL = 117.275); portfólios de memecoins com 1000 USDT.
- Portões: `baseline` (fiel ao artigo) conf ≥ 0.6, skip < 0.5; `relaxed` conf ≥ 0.35, margem de probabilidade ≥ 0.20, skip < 0.5 (calibrado porque a confiança do von concentra-se em ~0.23 e ~0.38). Cooldown 120 s, máximo 8 trades/h, compra de 25% do USDT.
- Nada é desativado; afinações noturnas geram *forks* (máx. 1 por linhagem a cada 7 dias, 40 no total). Veredito exige ≥30 round trips fechados **e** ≥21 dias (≥28 para regras de 1 h e filtros de regime), bater buy & hold e a barra de 6%/a em USDC com p < 0,05 por block-bootstrap.

### Famílias de portfólios (107)

| Família | SOL | Memecoins (BONK, FARTCOIN, GOAT, MEW, PNUT, POPCAT, WIF) |
| --- | --- | --- |
| Modelos | `baseline`, `relaxed`, `v2` (von); `laya_*`, `poorjev_*` | `meme_{SYM}_baseline/relaxed` (von); `{SYM}_laya_*`, `{SYM}_poorjev_*` |
| Regras | `grid_sol_2pct`, `rsi_sol_1h` | `{SYM}_rule_regime[_full]`, `{SYM}_rule_donch_regime[_full]` (só com SOL EMA12 > EMA26) |
| Híbridos | `hybrid_von_relaxed_cap2` (von relaxed, 2 trades/h, compra só em regime de alta) | `{SYM}_hybrid_poorjev_regime` |
| Hipóteses (lab) | H1 saídas TP/SL/trailing, H2 ensemble por percentil, H3 ordens limite, H4 janelas horárias | H1 e H2 por moeda |

`v2` usa os critérios reescritos pela revisão noturna (`criteria_v2.json`) com o portão relaxed. O Jev hospedado (`jev_*`) está desligado à espera de `JEV_API_KEY`.

Existe ainda um serviço independente, `funding/`: carry de funding delta-neutro em paper (spot longo + perp curto na Hyperliquid), portfólios `p1000` e `p1000_pons`.

### Resultados até 2026-09-26 01:06 BRT (~1,2 dias; `reports/cumulative.md`)

Contexto de mercado: SOL subiu ~2,6% (117,28 → ~120,3). Buy & hold das moedas: BONK −3,9%, FARTCOIN +5,1%, GOAT +0,2%, MEW +2,0%, PNUT +4,2%, POPCAT +3,4%, WIF +4,1%. O B&H dos portfólios SOL é a mistura inicial (~4% SOL); o das memecoins é segurar a moeda.

| Grupo | | Portfólio | PnL % | Excesso vs B&H (US$) | MDD % | Trades (C/V) |
| --- | --- | --- | ---: | ---: | ---: | --- |
| SOL · von | melhor | `relaxed` | +2,67 | +25,58 | −2,63 | 41 (40/1) |
| | pior | `baseline` | +0,12 | 0,00 | −0,11 | 0 |
| SOL · laya | ambos | `laya_baseline` / `laya_relaxed` | +0,12 | 0,00 | −0,11 | 0 |
| SOL · poorjev | melhor / pior | `poorjev_baseline` / `poorjev_relaxed` | −0,13 / −0,14 | −2,50 / −2,60 | −1,14 | 2 (2/0) |
| SOL · regras | melhor | `rsi_sol_1h` | +0,14 | +0,25 | −0,11 | 1 (0/1) |
| | pior | `grid_sol_2pct` | +0,12 | 0,00 | −0,11 | 0 |
| SOL · híbrido | único | `hybrid_von_relaxed_cap2` | +3,11 | +29,91 | −1,94 | 41 (40/1) |
| SOL · lab | melhor | `h4_hours_von_relaxed` | +3,23 | +31,09 | −2,39 | 20 (20/0) |
| | pior | `h3_limit_poorjev_relaxed` | −0,05 | −1,67 | −1,00 | 2 (2/0) |
| Meme · von | melhor | `meme_BONK_relaxed` | −0,06 | +38,86 | −0,06 | 2 (1/1) |
| | pior | `meme_GOAT_relaxed` | −1,58 | −17,35 | −1,71 | 11 (7/4) |
| Meme · laya | todos | 14 portfólios | 0,00 | = −B&H | 0,00 | 0 |
| Meme · poorjev | melhor | `FARTCOIN_poorjev_baseline` | +5,06 | −0,67 | −6,83 | 20 (20/0) |
| | pior | `BONK_poorjev_baseline` | −3,99 | −0,41 | −5,51 | 20 (20/0) |
| Meme · regras | melhor | `FARTCOIN_rule_regime_full` | +5,22 | −2,18 | −7,48 | 1 (1/0) |
| | pior | `BONK_rule_regime_full` | −4,24 | −2,72 | −5,78 | 1 (1/0) |
| Meme · híbrido | melhor | `FARTCOIN_hybrid_poorjev_regime` | +5,02 | −0,99 | −6,83 | 20 (20/0) |
| | pior | `BONK_hybrid_poorjev_regime` | −4,02 | −0,81 | −5,34 | 20 (20/0) |
| Meme · lab | melhor | `h1_exits_WIF_poorjev_relaxed` | +5,89 | +15,24 | −3,08 | 21 (20/1) |
| | pior | `h1_exits_BONK_poorjev_relaxed` | −3,80 | −0,63 | −5,83 | 43 (41/2) |

Leitura:

- **Todos os 107 portfólios estão `inconclusivo`** (no máximo 5/30 round trips e 1,2/21 dias). Nenhum fork foi criado. Os mínimos de dias só são atingidos por volta de **2026-10-15** (21 dias) e **2026-10-22** (28 dias).
- Os ganhos em SOL são sobretudo **exposição direcional num mercado em alta**, não seleção: `relaxed` e o híbrido fizeram 40 compras e 1 venda e ficaram com ~3 USDT (gate `insufficient_usdt`). A coluna "Timing $" (contribuição do *timing* da exposição, com p de placebo) é negativa em `relaxed` (−1,36, p 0,69).
- O von nunca atinge conf ≥ 0,6, logo `baseline` nunca opera; Laya nunca opera (confiança ~0,04); poorjev compra e fica ~98% exposto, reproduzindo o B&H.
- Sinais a acompanhar (amostra ainda muito pequena): *timing* com p ≤ 0,02 em `h1_exits_WIF` (+26,1), `h2_ensemble_FARTCOIN` (+26,1), `h2_ensemble_POPCAT` (+20,8), `h2_ensemble_PNUT` (+14,8); no dia 2026-09-25, `hybrid_von_relaxed_cap2` teve *timing* +8,7 (p 0,03).
- Funding carry: `p1000` −0,51% e `p1000_pons` −0,50% após 1,27 dias, dominados por custos de entrada (bridge e conta, ~US$4,6); ambos abaixo do Kamino USDC. 1.083 respostas 429 da Hyperliquid.
- Qualidade de fills: 0/913 fills caíram no fallback de mark.

### Última revisão noturna (`reviews/2026-09-26.md`)

- Veredito: todos `inconclusivo`, motivo "mínimos não atingidos".
- Tuning: nenhuma linhagem elegível ("dados insuficientes"); regras de 1 h sem replay; 0/40 forks.
- Critérios v2: auditoria de 10.512 decisões e 41 trades (todos do `relaxed`), `lose_words` vazio; a proposta (`criteria_v2_proposed_2026-09-26.json`) é **idêntica** aos critérios atuais. Um fork com texto novo exigiria uma chamada extra ao von por ciclo, o que ficou como **decisão do utilizador**.
- Próxima revisão agendada no host: 2026-09-27 00:30 BRT; rotação de logs às 01:00.

### Dashboard (`research/paper-lab/dashboard-v2/` + `dashboard/`)

React 19 + Vite + TypeScript + Tailwind + shadcn/ui + Lightweight Charts + TanStack Query, com SSE em `/api/v2/stream` (polling de ~12 s como alternativa). É servido pela app FastAPI em `dashboard/app.py` (porta 8787, HTTP Basic com credenciais em `dashboard/.auth`, fora do git), exposto por um túnel rápido `cloudflared` (URL `*.trycloudflare.com` efémero). Separadores: Visão geral, Portfólios SOL, Memecoins, Regras & Lab, Modelos, Funding, Controles (pausa de bots, ativação de modelos, edição de parâmetros com *hot reload* via `data/params_overlay.json`). A interface antiga fica em `/legacy`.

Construção: `cd research/paper-lab/dashboard-v2 && npm install && npm run build` (sem lockfile no repositório; o `npm install` gera um novo).

## 5. Onde correu e o que não está no repositório

- **Host do laboratório:** uma máquina Linux com utilizador `box`, código em `/home/box/solana-trader/paper` (caminho fixo na maioria dos módulos de `bot/`, em `dashboard/` e em `scripts/*.sh`). Os venvs dos modelos ficam em `/workspace/jev-alts/venvs/{von,laya,poorjev}` e os pesos em `/workspace/jev-alts/hf-cache`. Serviços locais: von `127.0.0.1:8765`, Laya `:8766`, poorjev `:8767`, dashboard `:8787`. Sem systemd; arranque por `scripts/boot_autostart.sh` via `@reboot` no cron e uma rotina de saúde "Saúde do simulador Jev" a cada 30 min. A pesquisa `research/jev-alts` foi feita na mesma família de caminhos (`/workspace/jev-alts/`, máquina de 8 vCPU sem GPU, Python 3.13). A identidade exata do host (fornecedor, IP) não aparece em nenhum artefacto.
- **Estado conhecido mais recente:** heartbeat de `status.json` em 2026-09-26 03:54 BRT, 3.908 ciclos, 0 erros. Não se sabe se continua a correr.
- **Referenciado mas ausente:** `/workspace/strategy-research/REPORT.md` (origem das regras grid/RSI/regime/Donchian) e `/workspace/dashboard-shots/` (capturas do dashboard).
- **Deixado de fora deste commit (~86 MB):** logs de decisões e trades (`logs/`, 12 MB), curvas de equity SOL (`data/equity_*.jsonl`, 13 MB), `data/prices.jsonl` (2,9 MB), equity do lab (8 MB), equity e preços das memecoins (23 MB + 11 MB), logs arquivados da execução de $52 (15 MB) e `funding_p52` (56 KB), logs e cache do funding (~0,6 MB), `package-lock.json` e `tsconfig.tsbuildinfo` do dashboard. O tarball completo continua em `~/.cursor/projects/Users-raphaelcangucu-projects-jev-solana-trader/uploads/jev-paper-export.tar_1453.gz` na máquina do utilizador.
- **Nunca no repositório:** chave da carteira, `keypair.json`, `secret.b58`, `.env`, `dashboard/.auth`, `dashboard/url.txt`, o binário `cloudflared`, `JEV_API_KEY`.

## 6. Questões em aberto

1. O laboratório continua a correr no host `box`? Sem acesso ao host, a sessão nova só vê este instantâneo.
2. A deriva só-compra do von relaxed (e do poorjev) é aceitável ou é preciso regra de saída/limite de exposição para que o PnL meça seleção e não beta?
3. A revisão noturna não aprende: o critério "conf > 0,8 e errado" nunca dispara com o von. Trocar por um corte por percentil da confiança?
4. Ligar o Jev hospedado (`JEV_API_KEY`) para comparar com o modelo original do artigo?
5. Aprovar o fork `v2` com texto novo, ao custo de uma chamada extra ao von por ciclo?
6. O laboratório deve passar a ser código versionado de primeira classe (com testes) ou continuar como instantâneo de pesquisa?

## 7. Próximos passos (por prioridade)

1. **Obter o estado atual do laboratório.** Pedir ao utilizador uma exportação nova (ou acesso ao host) e atualizar `research/paper-lab/` com os relatórios e revisões posteriores a 2026-09-26.
2. **Placar do bot real.** Implementar em `jev_trader` o cálculo dos quatro critérios do README (PnL contra segurar o livro, hit rate a 15 min, max drawdown, número de trades) a partir de `logs/*.jsonl`, com testes.
3. **Separar beta de seleção.** Nos relatórios do lab, pôr em destaque o excesso ajustado à exposição e a coluna de *timing*; avaliar H1 (saídas) aplicado ao `relaxed` e ao híbrido como remédio à deriva só-compra.
4. **Corrigir a revisão noturna.** Substituir o limiar fixo 0,8 por percentil da confiança do modelo e corrigir o título com data errada em `data/nightly/v2_review_tmp.md` ("Night review — 2026-09-24" num ficheiro gerado a 2026-09-26).
5. **Comando `rewrite --approve`** no bot real, com `config/criteria.json` e registo de aprovação (desenho já descrito no README).
6. **Tornar o lab portável.** Trocar o caminho fixo `/home/box/solana-trader/paper` por variável de ambiente e acrescentar testes mínimos a `bot/gates.py`, `bot/state.py` e `bot/analytics.py`.
7. **Manter tudo em paper** até os primeiros vereditos (≥30 RT e ≥21 dias, por volta de 2026-10-15). `LIVE_TRADING` continua desligado.

## 8. Como começar uma sessão nova

```bash
git fetch origin && git checkout handoff/cursor-session
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
pytest -q                                    # esperado: 16 passed
python -m jev_trader --dry-run --once        # sem von no ar: hold fail_closed, é o esperado
```

Leitura recomendada, por ordem: este documento, `README.md`, `research/paper-lab/README.md`, `research/paper-lab/reviews/2026-09-26.md`, `research/paper-lab/reports/cumulative.md`, `research/jev-alts/ARTICLE_COMPARE.md`.

Regras de segurança que se mantêm: nunca pedir nem escrever chave privada; dry-run por omissão; qualquer envio ao vivo exige decisão explícita do utilizador.
