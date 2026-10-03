# Day 1 paper trading report

**Generated (BRT):** 2026-09-24T21:06:04.536418-03:00

## Gate rules

- **Baseline (article-faithful):** conf ≥ 0.6, skip_noul < 0.5, cooldown 120s, max 8/h, buy 25% USDT.
- **Relaxed (calibrated to von output):** conf ≥ 0.35 (~80th pct of observed ~0.229/0.379 clusters), prob margin (chosen−runner-up) ≥ 0.2, skip_noul < 0.5, same sizing/cooldown/cap. Same von decision reused — no extra model calls.
- **v2 (shadow):** own von call with `criteria_v2.json`; **uses the relaxed gate** (conf ≥ 0.35, margin ≥ 0.2, skip < 0.5). Portfolio file created at night review 04:00:03 BRT but initially wired to the baseline 0.6 gate by an init bug; effective trading under the relaxed gate started after the fix (see README).
- Calibration note: From first ~33 baseline von decisions on this box: confidence clustered at ~0.229 and ~0.379; empirical ~80th percentile ≈0.379. Using min_confidence=0.35 to open on the high cluster. Prob margin (chosen−runner-up) observed p50≈0.32; requiring >=0.20 for a clear argmax. skip_noul < 0.5 unchanged. Same sizing/cooldown/cap as baseline.

## SOL/USDT — baseline vs relaxed vs v2

| Portfolio | Decisions | Trades | Blocked | SOL exp % | Equity start→end | vs B&H Δ | vs USDT Δ | MDD | Fees |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| baseline | 381 | 0 | 381 | 3.9% | 52.0143→52.0489 | 0.0000 | 0.0346 | 0.12% | 0.0000 |
| relaxed | 381 | 39 | 381 | 92.6% | 52.0025→51.2091 | -0.8398 | -0.7817 | 4.96% | 0.1855 |
| v2 | 381 | 3 | 381 | 0.0% | 52.0063→51.9197 | -0.1292 | -0.0786 | 0.47% | 0.0156 |

### Baseline

- chosen: {'sell': 20, 'buy': 361}
- final: {'hold': 381}
- SOL exposure: **3.9%**
- fill_mode counts: (no trades)
- blocked / gate reasons: {'low_confidence': 381}

### Relaxed

- chosen: {'sell': 20, 'buy': 361}
- final: {'hold': 381}
- SOL exposure: **92.6%**
- fill_mode counts: {'mark': 31, 'jupiter_quote': 8}
- blocked / gate reasons: {'low_confidence': 273, 'insufficient_usdt': 108, 'low_prob_margin': 24}

### v2

- chosen: {'sell': 208, 'buy': 173}
- final: {'hold': 381}
- SOL exposure: **0.0%**
- fill_mode counts: {'mark': 2, 'jupiter_quote': 1}
- blocked / gate reasons: {'low_confidence': 381, 'low_prob_margin': 381}

## Extra model SOL portfolios

# Extra model portfolios — start times (BRT)
Generated: 2026-09-24T04:48:57.833587-03:00
These portfolios started mid-day (not at day open). Same initial balances as von.
- **laya_baseline** model=`laya` gate=`baseline` started=2026-09-24T04:48:57.833587-03:00
- **laya_relaxed** model=`laya` gate=`relaxed` started=2026-09-24T04:48:57.833587-03:00
- **poorjev_baseline** model=`poorjev` gate=`baseline` started=2026-09-24T04:48:57.833587-03:00
- **poorjev_relaxed** model=`poorjev` gate=`relaxed` started=2026-09-24T04:48:57.833587-03:00

Scheduling: extra backends called **concurrently** each cycle alongside von (fits in 15s).

## Meme multi-model portfolios — start 2026-09-24T13:55:39.924587-03:00

Extra meme models: laya, poorjev. Per coin: `{SYM}_{model}_baseline` / `{SYM}_{model}_relaxed` at 50 USDT each. Von meme portfolios untouched. Concurrent System One calls each meme cycle.

- **BONK_laya_baseline** started=2026-09-24T13:55:39.924587-03:00
- **BONK_laya_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **WIF_laya_baseline** started=2026-09-24T13:55:39.924587-03:00
- **WIF_laya_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **POPCAT_laya_baseline** started=2026-09-24T13:55:39.924587-03:00
- **POPCAT_laya_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **FARTCOIN_laya_baseline** started=2026-09-24T13:55:39.924587-03:00
- **FARTCOIN_laya_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **PNUT_laya_baseline** started=2026-09-24T13:55:39.924587-03:00
- **PNUT_laya_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **MEW_laya_baseline** started=2026-09-24T13:55:39.924587-03:00
- **MEW_laya_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **GOAT_laya_baseline** started=2026-09-24T13:55:39.924587-03:00
- **GOAT_laya_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **BONK_poorjev_baseline** started=2026-09-24T13:55:39.924587-03:00
- **BONK_poorjev_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **WIF_poorjev_baseline** started=2026-09-24T13:55:39.924587-03:00
- **WIF_poorjev_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **POPCAT_poorjev_baseline** started=2026-09-24T13:55:39.924587-03:00
- **POPCAT_poorjev_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **FARTCOIN_poorjev_baseline** started=2026-09-24T13:55:39.924587-03:00
- **FARTCOIN_poorjev_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **PNUT_poorjev_baseline** started=2026-09-24T13:55:39.924587-03:00
- **PNUT_poorjev_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **MEW_poorjev_baseline** started=2026-09-24T13:55:39.924587-03:00
- **MEW_poorjev_relaxed** started=2026-09-24T13:55:39.924587-03:00
- **GOAT_poorjev_baseline** started=2026-09-24T13:55:39.924587-03:00
- **GOAT_poorjev_relaxed** started=2026-09-24T13:55:39.924587-03:00

## Correção (2026-09-24 ~20:50 BRT)

Uma seção "Meme multi-model portfolios — start 2026-09-24T15:08:36" foi anexada aqui por engano durante o soft-restart do deploy das regras (15:08). **Os portfólios laya/poorjev de memes NÃO foram resetados:** os JSONs (`started_brt`/`created_ts`), as curvas de equity e os trades são contínuos desde **2026-09-24T13:55:39.924587-03:00**. A seção errada foi removida (backup em `models_start.md.bak_pre_fix`) e o `meme_bot.py` não anexa mais seções de início ao reiniciar.

| Portfolio | Model | Decisions | Trades | SOL exp % | Equity end | vs B&H Δ | vs USDT Δ | MDD | Start BRT |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| laya_baseline | laya | 382 | 0 | 3.9% | 52.0489 | 0.0000 | 0.0273 | 0.10% | 2026-09-24T04:48:57.833587-03:00 |
| laya_relaxed | laya | 382 | 0 | 3.9% | 52.0489 | 0.0000 | 0.0273 | 0.10% | 2026-09-24T04:48:57.833587-03:00 |
| poorjev_baseline | poorjev | 382 | 2 | 46.4% | 52.4523 | 0.4034 | 0.4307 | 0.62% | 2026-09-24T04:48:57.833587-03:00 |
| poorjev_relaxed | poorjev | 382 | 2 | 46.4% | 52.4509 | 0.4020 | 0.4293 | 0.62% | 2026-09-24T04:48:57.833587-03:00 |
| jev_baseline | ? | 0 | 0 | — | n/a | — | — | — |  |
| jev_relaxed | ? | 0 | 0 | — | n/a | — | — | — |  |
| jev_article | ? | 0 | 0 | — | n/a | — | — | — |  |

### Ranked by vs B&H Δ

1. **poorjev_baseline** (poorjev) end=52.4523 vsB&H=0.4034 vsUSDT=0.4307
2. **poorjev_relaxed** (poorjev) end=52.4509 vsB&H=0.4020 vsUSDT=0.4293
3. **laya_baseline** (laya) end=52.0489 vsB&H=0.0000 vsUSDT=0.0273
4. **laya_relaxed** (laya) end=52.0489 vsB&H=0.0000 vsUSDT=0.0273

## Hosted Jev

- enabled in models.json: **False**
- api_key_env: `JEV_API_KEY` (never logged)
- endpoint: `https://api.typesafe.ai/v1/systemone`
- If key missing: status shows **aguardando chave**. After setting key: export it, then `scripts/stop.sh` + `scripts/start.sh` so supervisor inherits env (see `scripts/restart_models.sh`).
- LIVE_TRADING: always off (paper simulation only).

## Parameter changes (dashboard / hot-reload)

| BRT | Portfolio | Campo | Antigo | Novo |
| --- | --- | --- | ---: | ---: |
| 2026-09-24T04:52:12.398509-03:00 | relaxed | `min_confidence` | 0.35 | 0.4 |
| 2026-09-24T04:52:30.414085-03:00 | relaxed | `min_confidence` | 0.4 | 0.35 |
| 2026-09-24T20:43:41.743922-03:00 | relaxed | `start_price` | 115.28 | 114.605 |
| 2026-09-24T20:43:41.744212-03:00 | v2 | `start_price` | 115.28 | 114.82 |
| 2026-09-24T20:43:41.744461-03:00 | laya_baseline | `start_price` | 115.28 | 115.49 |
| 2026-09-24T20:43:41.744658-03:00 | laya_relaxed | `start_price` | 115.28 | 115.49 |
| 2026-09-24T20:43:41.744901-03:00 | poorjev_baseline | `start_price` | 115.28 | 115.49 |
| 2026-09-24T20:43:41.745119-03:00 | poorjev_relaxed | `start_price` | 115.28 | 115.49 |
| 2026-09-24T20:43:41.745401-03:00 | hybrid_von_relaxed_cap2 | `start_price` | 115.28 | 116.575 |

## Memecoin paper simulation

**Restart (clean, live prices only):** 2026-09-24T20:53:21.310024-03:00

**Price policy:** live_only_no_seed_max_age_120s — seed file removed; skip if no fresh real mark ≤120s.

**Cadence:** {'rotate_seconds': 60, 'description': '1 token/60s rotate; shared von; live marks Gate.io→Coinpaprika→DexScreener→Jupiter; Jupiter/mark fills; no seed'}

**Night review for memes:** skipped.

### Basket

- **BONK** `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` — Largest Solana meme; Jupiter verified
- **WIF** `EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm` — Top meme liquidity; Jupiter verified
- **POPCAT** `7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr` — High organic volume; Jupiter verified
- **FARTCOIN** `9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump` — High recent volume; Jupiter-routed
- **PNUT** `2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump` — High-volume meme; Jupiter-routable
- **MEW** `MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5` — Established cat meme; Jupiter verified
- **GOAT** `CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuypump` — AI-narrative meme; sustained volume

### Ranking per model vs B&H / USDT (models=['von', 'laya', 'poorjev'])

| Symbol | Model | Profile | End eq | PnL | vs B&H | vs USDT | MDD | Trades |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BONK | laya | baseline | 50.0000 | 0.0000 | -1.1895 | 0.0000 | 0.00% | 0 |
| BONK | laya | relaxed | 50.0000 | 0.0000 | -1.1895 | 0.0000 | 0.00% | 0 |
| BONK | poorjev | baseline | 51.2457 | 1.2505 | 0.0610 | 1.2505 | 1.68% | 9 |
| BONK | poorjev | relaxed | 51.2948 | 1.2984 | 0.1089 | 1.2984 | 1.68% | 9 |
| BONK | von | baseline | 50.0000 | 0.0000 | -4.0240 | 0.0000 | 0.00% | 0 |
| BONK | von | relaxed | 50.0000 | 0.0000 | -4.0240 | 0.0000 | 0.00% | 0 |
| FARTCOIN | laya | baseline | 50.0000 | 0.0000 | 1.7744 | 0.0000 | 0.00% | 0 |
| FARTCOIN | laya | relaxed | 50.0000 | 0.0000 | 1.7744 | 0.0000 | 0.00% | 0 |
| FARTCOIN | poorjev | baseline | 48.4965 | -1.4981 | 0.2763 | -1.4981 | 3.57% | 9 |
| FARTCOIN | poorjev | relaxed | 48.5113 | -1.4840 | 0.2904 | -1.4840 | 3.54% | 9 |
| FARTCOIN | von | baseline | 50.0000 | 0.0000 | 0.1992 | 0.0000 | 0.00% | 0 |
| FARTCOIN | von | relaxed | 50.0000 | 0.0000 | 0.1992 | 0.0000 | 0.00% | 0 |
| GOAT | laya | baseline | 50.0000 | 0.0000 | 1.9318 | 0.0000 | 0.00% | 0 |
| GOAT | laya | relaxed | 50.0000 | 0.0000 | 1.9318 | 0.0000 | 0.00% | 0 |
| GOAT | poorjev | baseline | 48.3277 | -1.6512 | 0.2806 | -1.6512 | 3.49% | 9 |
| GOAT | poorjev | relaxed | 48.3718 | -1.6078 | 0.3239 | -1.6078 | 3.40% | 9 |
| GOAT | von | baseline | 50.0000 | 0.0000 | 0.2599 | 0.0000 | 0.00% | 0 |
| GOAT | von | relaxed | 50.0000 | 0.0000 | 0.2599 | 0.0000 | 0.00% | 0 |
| MEW | laya | baseline | 50.0000 | 0.0000 | 0.6685 | 0.0000 | 0.00% | 0 |
| MEW | laya | relaxed | 50.0000 | 0.0000 | 0.6685 | 0.0000 | 0.00% | 0 |
| MEW | poorjev | baseline | 49.1933 | -0.7378 | -0.0693 | -0.7378 | 2.42% | 9 |
| MEW | poorjev | relaxed | 49.1933 | -0.7378 | -0.0693 | -0.7378 | 2.42% | 9 |
| MEW | von | baseline | 50.0000 | 0.0000 | -2.1671 | 0.0000 | 0.00% | 0 |
| MEW | von | relaxed | 49.9162 | -0.0838 | -2.2508 | -0.0838 | 0.20% | 2 |
| PNUT | laya | baseline | 50.0000 | 0.0000 | 0.9714 | 0.0000 | 0.00% | 0 |
| PNUT | laya | relaxed | 50.0000 | 0.0000 | 0.9714 | 0.0000 | 0.00% | 0 |
| PNUT | poorjev | baseline | 49.0488 | -0.9295 | 0.0419 | -0.9295 | 2.44% | 9 |
| PNUT | poorjev | relaxed | 49.0523 | -0.9259 | 0.0455 | -0.9259 | 2.43% | 9 |
| PNUT | von | baseline | 50.0000 | 0.0000 | -0.6979 | 0.0000 | 0.00% | 0 |
| PNUT | von | relaxed | 49.8258 | -0.1742 | -0.8721 | -0.1742 | 0.35% | 2 |
| POPCAT | laya | baseline | 50.0000 | 0.0000 | 0.7486 | 0.0000 | 0.00% | 0 |
| POPCAT | laya | relaxed | 50.0000 | 0.0000 | 0.7486 | 0.0000 | 0.00% | 0 |
| POPCAT | poorjev | baseline | 49.3097 | -0.6492 | 0.0994 | -0.6492 | 2.65% | 9 |
| POPCAT | poorjev | relaxed | 49.3108 | -0.6491 | 0.0995 | -0.6491 | 2.65% | 9 |
| POPCAT | von | baseline | 50.0000 | 0.0000 | -0.1148 | 0.0000 | 0.00% | 0 |
| POPCAT | von | relaxed | 50.0000 | 0.0000 | -0.1148 | 0.0000 | 0.00% | 0 |
| WIF | laya | baseline | 50.0000 | 0.0000 | 0.1261 | 0.0000 | 0.00% | 0 |
| WIF | laya | relaxed | 50.0000 | 0.0000 | 0.1261 | 0.0000 | 0.00% | 0 |
| WIF | poorjev | baseline | 49.9038 | -0.0845 | 0.0416 | -0.0845 | 1.55% | 9 |
| WIF | poorjev | relaxed | 49.8452 | -0.1387 | -0.0126 | -0.1387 | 1.55% | 9 |
| WIF | von | baseline | 50.0000 | 0.0000 | 1.0343 | 0.0000 | 0.00% | 0 |
| WIF | von | relaxed | 50.0000 | 0.0000 | 1.0343 | 0.0000 | 0.00% | 0 |

### Ranked by vs B&H Δ (all meme portfolios)

1. **GOAT** `laya/baseline` end=50.0000 vsB&H=1.9318 vsUSDT=0.0000 trades=0
2. **GOAT** `laya/relaxed` end=50.0000 vsB&H=1.9318 vsUSDT=0.0000 trades=0
3. **FARTCOIN** `laya/baseline` end=50.0000 vsB&H=1.7744 vsUSDT=0.0000 trades=0
4. **FARTCOIN** `laya/relaxed` end=50.0000 vsB&H=1.7744 vsUSDT=0.0000 trades=0
5. **WIF** `von/baseline` end=50.0000 vsB&H=1.0343 vsUSDT=0.0000 trades=0
6. **WIF** `von/relaxed` end=50.0000 vsB&H=1.0343 vsUSDT=0.0000 trades=0
7. **PNUT** `laya/baseline` end=50.0000 vsB&H=0.9714 vsUSDT=0.0000 trades=0
8. **PNUT** `laya/relaxed` end=50.0000 vsB&H=0.9714 vsUSDT=0.0000 trades=0
9. **POPCAT** `laya/baseline` end=50.0000 vsB&H=0.7486 vsUSDT=0.0000 trades=0
10. **POPCAT** `laya/relaxed` end=50.0000 vsB&H=0.7486 vsUSDT=0.0000 trades=0
11. **MEW** `laya/baseline` end=50.0000 vsB&H=0.6685 vsUSDT=0.0000 trades=0
12. **MEW** `laya/relaxed` end=50.0000 vsB&H=0.6685 vsUSDT=0.0000 trades=0
13. **GOAT** `poorjev/relaxed` end=48.3718 vsB&H=0.3239 vsUSDT=-1.6078 trades=9
14. **FARTCOIN** `poorjev/relaxed` end=48.5113 vsB&H=0.2904 vsUSDT=-1.4840 trades=9
15. **GOAT** `poorjev/baseline` end=48.3277 vsB&H=0.2806 vsUSDT=-1.6512 trades=9
16. **FARTCOIN** `poorjev/baseline` end=48.4965 vsB&H=0.2763 vsUSDT=-1.4981 trades=9
17. **GOAT** `von/baseline` end=50.0000 vsB&H=0.2599 vsUSDT=0.0000 trades=0
18. **GOAT** `von/relaxed` end=50.0000 vsB&H=0.2599 vsUSDT=0.0000 trades=0
19. **FARTCOIN** `von/baseline` end=50.0000 vsB&H=0.1992 vsUSDT=0.0000 trades=0
20. **FARTCOIN** `von/relaxed` end=50.0000 vsB&H=0.1992 vsUSDT=0.0000 trades=0
21. **WIF** `laya/baseline` end=50.0000 vsB&H=0.1261 vsUSDT=0.0000 trades=0
22. **WIF** `laya/relaxed` end=50.0000 vsB&H=0.1261 vsUSDT=0.0000 trades=0
23. **BONK** `poorjev/relaxed` end=51.2948 vsB&H=0.1089 vsUSDT=1.2984 trades=9
24. **POPCAT** `poorjev/relaxed` end=49.3108 vsB&H=0.0995 vsUSDT=-0.6491 trades=9
25. **POPCAT** `poorjev/baseline` end=49.3097 vsB&H=0.0994 vsUSDT=-0.6492 trades=9
26. **BONK** `poorjev/baseline` end=51.2457 vsB&H=0.0610 vsUSDT=1.2505 trades=9
27. **PNUT** `poorjev/relaxed` end=49.0523 vsB&H=0.0455 vsUSDT=-0.9259 trades=9
28. **PNUT** `poorjev/baseline` end=49.0488 vsB&H=0.0419 vsUSDT=-0.9295 trades=9
29. **WIF** `poorjev/baseline` end=49.9038 vsB&H=0.0416 vsUSDT=-0.0845 trades=9
30. **WIF** `poorjev/relaxed` end=49.8452 vsB&H=-0.0126 vsUSDT=-0.1387 trades=9

- Meme decisions by model: {'von': 2432, 'laya': 860, 'poorjev': 860, 'poorjev+rules': 357, 'rule': 10598} skipped_no_price=0
- Meme trades by model: {'von': 4, 'poorjev': 207, '?': 16}
- Sources seen: ['coinpaprika', 'gate.io']
- Meme models enabled (status): ['von', 'laya', 'poorjev']

## Rule strategies & hybrids (paper)

# Rule strategies — start times (BRT)

**Rules bot start:** `2026-09-24T15:09:13.282682-03:00`  
**Warm-up complete:** `2026-09-24T15:09:13.215920-03:00`  
**SOL hybrid (`hybrid_von_relaxed_cap2`) start:** `2026-09-24T15:08:28.370392-03:00`  
**Meme hybrids (`{SYM}_hybrid_poorjev_regime`) start:** `2026-09-24T15:08:36.995785-03:00`  

Simulation only. Existing model portfolios were **not** wiped.

## Portfolios created

### SOL
- `grid_sol_2pct` — Grid 2% / 4 níveis / 1h — start `2026-09-24T15:09:13.282682-03:00`
- `rsi_sol_1h` — RSI(14) 30/70 / 1h — start `2026-09-24T15:09:13.282682-03:00`
- `hybrid_von_relaxed_cap2` — von relaxed + max 2 trades/h + SOL EMA regime buy filter — start `2026-09-24T15:08:28.370392-03:00`

### Memes (×7: BONK WIF POPCAT FARTCOIN PNUT MEW GOAT)
- `{SYM}_rule_regime` — só carrega meme se SOL EMA12>EMA26
- `{SYM}_rule_donch_regime` — Donchian20 + filtro de regime SOL
- `{SYM}_hybrid_poorjev_regime` — copia decisão poorjev relaxed; bloqueia buy se regime SOL bear

## Indicator snapshot at start
- SOL 1h close=116.74 EMA12=115.29486081300212 EMA26=115.27442729301794 RSI=59.12874262987857 regime_bull=True
- Warm-up bars: SOL=1080 memes=1081 each
- Trade only on bars closing after warm-up (`trade_only_after_brt`=2026-09-24T15:09:13.215898-03:00)

## Grid levels vs ref
- ref=116.74 buys_open=0 price_1h=116.74
- L1: buy<=114.4052 sell_target>=119.0748
- L2: buy<=112.0704 sell_target>=121.4096
- L3: buy<=109.7356 sell_target>=123.7444
- L4: buy<=107.4008 sell_target>=126.0792

## Process
- `bot/rules_bot.py` supervised as `rules` (status: `data/rules/status.json`)
- Hybrids live inside `sol_bot.py` / `meme_bot.py` (reuse model decisions; no extra model calls)

- rules_bot started_brt (status): 2026-09-24T20:53:19.361898-03:00
- warm_up: {"warmed_at_brt": "2026-09-24T20:53:19.324937-03:00", "sol_bars": 1085, "sol_first_brt": "2026-08-10T15:00:00-03:00", "sol_last_brt": "2026-09-24T19:00:00-03:00", "meme_bars": {"BONK": 1086, "WIF": 1086, "POPCAT": 1086, "FARTCOIN": 1086, "PNUT": 1086, "MEW": 1086, "GOAT": 1086}, "trade_only_after_ts": 1790293999.324919, "trade_only_after_brt": "2026-09-24T20:53:19.324919-03:00"}
- SOL indicators now: close=117.02 ema12=116.33494537213775 ema26=115.89842399020475 rsi=58.62584612784554 bull=True

### SOL rule / hybrid portfolios

| Portfolio | Strategy | Decisions | Trades | Equity end | vs B&H Δ | MDD | Start BRT |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| grid_sol_2pct | rule:grid_sol_2pct | 190 | 0 | 52.0493 | 0.0000 | 0.05% | 2026-09-24T15:09:13.282682-03:00 |
| rsi_sol_1h | rule:rsi_sol_1h | 190 | 0 | 52.0493 | 0.0000 | 0.05% | 2026-09-24T15:09:13.282682-03:00 |
| hybrid_von_relaxed_cap2 | rule:hybrid_von_relaxed_cap2 | 381 | 9 | 52.0720 | 0.0232 | 1.06% | 2026-09-24T15:08:28.370392-03:00 |

### Meme rule / hybrid portfolios

| Portfolio | Trades | Equity end | Last signal | Start BRT |
| --- | ---: | ---: | --- | --- |
| BONK_rule_regime | 1 | 50.3958 | hold | 2026-09-24T15:09:13.282682-03:00 |
| BONK_rule_donch_regime | 1 | 50.0962 | hold | 2026-09-24T15:09:13.282682-03:00 |
| BONK_hybrid_poorjev_regime | 9 | 51.5209 | hold | 2026-09-24T15:08:36.995785-03:00 |
| WIF_rule_regime | 1 | 50.0662 | hold | 2026-09-24T15:09:13.282682-03:00 |
| WIF_rule_donch_regime | 0 | 50.0000 | hold | 2026-09-24T15:09:13.282682-03:00 |
| WIF_hybrid_poorjev_regime | 9 | 50.1997 | hold | 2026-09-24T15:08:36.995785-03:00 |
| POPCAT_rule_regime | 1 | 50.0638 | hold | 2026-09-24T15:09:13.282682-03:00 |
| POPCAT_rule_donch_regime | 0 | 50.0000 | hold | 2026-09-24T15:09:13.282682-03:00 |
| POPCAT_hybrid_poorjev_regime | 9 | 49.8190 | hold | 2026-09-24T15:08:36.995785-03:00 |
| FARTCOIN_rule_regime | 1 | 49.7569 | hold | 2026-09-24T15:09:13.282682-03:00 |
| FARTCOIN_rule_donch_regime | 0 | 50.0000 | hold | 2026-09-24T15:09:13.282682-03:00 |
| FARTCOIN_hybrid_poorjev_regime | 9 | 48.8618 | hold | 2026-09-24T15:08:36.995785-03:00 |
| PNUT_rule_regime | 1 | 49.7942 | hold | 2026-09-24T15:09:13.282682-03:00 |
| PNUT_rule_donch_regime | 0 | 50.0000 | hold | 2026-09-24T15:09:13.282682-03:00 |
| PNUT_hybrid_poorjev_regime | 9 | 49.3526 | hold | 2026-09-24T15:08:36.995785-03:00 |
| MEW_rule_regime | 1 | 49.8027 | hold | 2026-09-24T15:09:13.282682-03:00 |
| MEW_rule_donch_regime | 0 | 50.0000 | hold | 2026-09-24T15:09:13.282682-03:00 |
| MEW_hybrid_poorjev_regime | 9 | 49.1594 | hold | 2026-09-24T15:08:36.995785-03:00 |
| GOAT_rule_regime | 1 | 49.7526 | hold | 2026-09-24T15:09:13.282682-03:00 |
| GOAT_rule_donch_regime | 0 | 50.0000 | hold | 2026-09-24T15:09:13.282682-03:00 |
| GOAT_hybrid_poorjev_regime | 9 | 49.0113 | hold | 2026-09-24T15:08:36.995785-03:00 |

- Total rule-tagged trades (SOL+meme logs): 88

## Verdict

**Worth running live?** Not on this sample alone.
- Compare baseline (conf≥0.6, may trade ~0) vs relaxed (calibrated) honestly.
- Fills are Jupiter quotes minus haircuts — not identical to on-chain execution/MEV/failures.
- Marks are live-only (Gate.io / Coinpaprika / DexScreener / Jupiter); no seed/fabricated fallback.
- Keep paper-only until multi-day baseline vs relaxed vs v2 vs buy&hold shows stable edge after fees.

## Caveats

- Simulation only; wallet keys never loaded.
- Memecoin night-review/v2 shadow skipped.
- Each meme portfolio starts with 50 USDT flat (von baseline+relaxed per token; plus `{SYM}_{model}_{profile}` when memes_enabled).
- Rule portfolios: `grid_sol_2pct`, `rsi_sol_1h`, `{SYM}_rule_regime`, `{SYM}_rule_donch_regime`, `hybrid_von_relaxed_cap2`, `{SYM}_hybrid_poorjev_regime`.
- Meme clean restart noted in status: 2026-09-24T20:53:21.310024-03:00.
