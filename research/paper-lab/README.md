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
- erro = retorno a `horizon_s` (900 s) contra a chamada além de `band` (0,10%), com o preço de `data/prices.jsonl`; sem preço até +5 min → não resolvida;
- a proposta só acrescenta frases quando há erros confiantes; a barra fixa (`fixed_bar` 0,8) é calculada só para comparação; o título usa o dia revisado.
- Continua **só proposta** (`reviews/criteria_v2_proposed_<data>.json` + `data/nightly/v2_review_tmp.md`); nada altera os critérios em uso.
- `bot/review.py` (variante antiga) está deprecado e delega em `sol_bot.night_review`.

## Testes

`pytest -q` na raiz do repositório corre também `research/paper-lab/tests/` (gates, estado, analytics, auditoria de confiança, caminhos e
recomeço), offline e com `PAPER_LAB_ROOT` numa pasta temporária. `analytics` precisa de `numpy` (`pip install -e .[lab]`); sem ele esses testes fazem skip.

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
