# Day 1 paper trading report

**Generated (BRT):** 2026-09-26T01:06:03.871384-03:00

## Gate rules

- **Baseline (article-faithful):** conf ≥ 0.6, skip_noul < 0.5, cooldown 120s, max 8/h, buy 25% USDT.
- **Relaxed (calibrated to von output):** conf ≥ 0.35 (~80th pct of observed ~0.229/0.379 clusters), prob margin (chosen−runner-up) ≥ 0.2, skip_noul < 0.5, same sizing/cooldown/cap. Same von decision reused — no extra model calls.
- **v2 (shadow):** own von call with `criteria_v2.json`; **uses the relaxed gate** (conf ≥ 0.35, margin ≥ 0.2, skip < 0.5). Portfolio file created at night review 04:00:03 BRT but initially wired to the baseline 0.6 gate by an init bug; effective trading under the relaxed gate started after the fix (see README).
- Calibration note: From first ~33 baseline von decisions on this box: confidence clustered at ~0.229 and ~0.379; empirical ~80th percentile ≈0.379. Using min_confidence=0.35 to open on the high cluster. Prob margin (chosen−runner-up) observed p50≈0.32; requiring >=0.20 for a clear argmax. skip_noul < 0.5 unchanged. Same sizing/cooldown/cap as baseline.

## SOL/USDT — baseline vs relaxed vs v2

| Portfolio | Decisions | Trades | Blocked | SOL exp % | Equity start→end | vs B&H Δ | vs USDT Δ | MDD | Fees |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| baseline | 354 | 0 | 354 | 4.0% | 1000.0084→1001.1729 | 0.0000 | 1.1645 | 0.11% | 0.0000 |
| relaxed | 354 | 41 | 354 | 99.7% | 1000.0084→1026.6314 | 25.4585 | 26.6230 | 2.63% | 1.5281 |
| v2 | 354 | 1 | 354 | 0.0% | 1000.0084→1001.2334 | 0.0605 | 1.2251 | 0.09% | 0.0208 |

### Baseline

- chosen: {'buy': 323, 'sell': 31}
- final: {'hold': 354}
- SOL exposure: **4.0%**
- fill_mode counts: (no trades)
- blocked / gate reasons: {'low_confidence': 354}

### Relaxed

- chosen: {'buy': 323, 'sell': 31}
- final: {'hold': 354}
- SOL exposure: **99.7%**
- fill_mode counts: {'jupiter_quote': 31, 'raydium_quote': 10}
- blocked / gate reasons: {'insufficient_usdt': 271, 'low_confidence': 83, 'low_prob_margin': 35}

### v2

- chosen: {'buy': 311, 'sell': 43}
- final: {'hold': 354}
- SOL exposure: **0.0%**
- fill_mode counts: {'jupiter_quote': 1}
- blocked / gate reasons: {'low_confidence': 354, 'low_prob_margin': 330}

## Extra model SOL portfolios

# Extra model portfolios — start times (BRT)
Generated: 2026-09-24T21:07:46.591554-03:00
These portfolios started mid-day (not at day open). Same initial balances as von.
- **laya_baseline** model=`laya` gate=`baseline` started=2026-09-24T21:07:46.591554-03:00
- **laya_relaxed** model=`laya` gate=`relaxed` started=2026-09-24T21:07:46.591554-03:00
- **poorjev_baseline** model=`poorjev` gate=`baseline` started=2026-09-24T21:07:46.591554-03:00
- **poorjev_relaxed** model=`poorjev` gate=`relaxed` started=2026-09-24T21:07:46.591554-03:00

Scheduling: extra backends called **concurrently** each cycle alongside von (fits in 15s).

## Meme multi-model portfolios — start 2026-09-24T21:07:55.970939-03:00

Extra meme models: laya, poorjev. Per coin: `{SYM}_{model}_baseline` / `{SYM}_{model}_relaxed` at 50 USDT each. Von meme portfolios untouched. Concurrent System One calls each meme cycle.

- **BONK_laya_baseline** started=2026-09-24T21:07:55.970939-03:00
- **BONK_laya_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **WIF_laya_baseline** started=2026-09-24T21:07:55.970939-03:00
- **WIF_laya_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **POPCAT_laya_baseline** started=2026-09-24T21:07:55.970939-03:00
- **POPCAT_laya_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **FARTCOIN_laya_baseline** started=2026-09-24T21:07:55.970939-03:00
- **FARTCOIN_laya_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **PNUT_laya_baseline** started=2026-09-24T21:07:55.970939-03:00
- **PNUT_laya_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **MEW_laya_baseline** started=2026-09-24T21:07:55.970939-03:00
- **MEW_laya_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **GOAT_laya_baseline** started=2026-09-24T21:07:55.970939-03:00
- **GOAT_laya_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **BONK_poorjev_baseline** started=2026-09-24T21:07:55.970939-03:00
- **BONK_poorjev_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **WIF_poorjev_baseline** started=2026-09-24T21:07:55.970939-03:00
- **WIF_poorjev_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **POPCAT_poorjev_baseline** started=2026-09-24T21:07:55.970939-03:00
- **POPCAT_poorjev_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **FARTCOIN_poorjev_baseline** started=2026-09-24T21:07:55.970939-03:00
- **FARTCOIN_poorjev_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **PNUT_poorjev_baseline** started=2026-09-24T21:07:55.970939-03:00
- **PNUT_poorjev_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **MEW_poorjev_baseline** started=2026-09-24T21:07:55.970939-03:00
- **MEW_poorjev_relaxed** started=2026-09-24T21:07:55.970939-03:00
- **GOAT_poorjev_baseline** started=2026-09-24T21:07:55.970939-03:00
- **GOAT_poorjev_relaxed** started=2026-09-24T21:07:55.970939-03:00

| Portfolio | Model | Decisions | Trades | SOL exp % | Equity end | vs B&H Δ | vs USDT Δ | MDD | Start BRT |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| laya_baseline | laya | 354 | 0 | 4.0% | 1001.1729 | 0.0000 | 1.1645 | 0.11% | 2026-09-24T21:07:46.591554-03:00 |
| laya_relaxed | laya | 354 | 0 | 4.0% | 1001.1729 | 0.0000 | 1.1645 | 0.11% | 2026-09-24T21:07:46.591554-03:00 |
| poorjev_baseline | poorjev | 355 | 2 | 45.9% | 998.6199 | -2.5529 | -1.3884 | 1.14% | 2026-09-24T21:07:46.591554-03:00 |
| poorjev_relaxed | poorjev | 355 | 2 | 45.9% | 998.5172 | -2.6556 | -1.4911 | 1.14% | 2026-09-24T21:07:46.591554-03:00 |
| jev_baseline | ? | 0 | 0 | — | n/a | — | — | — |  |
| jev_relaxed | ? | 0 | 0 | — | n/a | — | — | — |  |
| jev_article | ? | 0 | 0 | — | n/a | — | — | — |  |

### Ranked by vs B&H Δ

1. **laya_baseline** (laya) end=1001.1729 vsB&H=0.0000 vsUSDT=1.1645
2. **laya_relaxed** (laya) end=1001.1729 vsB&H=0.0000 vsUSDT=1.1645
3. **poorjev_baseline** (poorjev) end=998.6199 vsB&H=-2.5529 vsUSDT=-1.3884
4. **poorjev_relaxed** (poorjev) end=998.5172 vsB&H=-2.6556 vsUSDT=-1.4911

## Hosted Jev

- enabled in models.json: **False**
- api_key_env: `JEV_API_KEY` (never logged)
- endpoint: `https://api.typesafe.ai/v1/systemone`
- If key missing: status shows **aguardando chave**. After setting key: export it, then `scripts/stop.sh` + `scripts/start.sh` so supervisor inherits env (see `scripts/restart_models.sh`).
- LIVE_TRADING: always off (paper simulation only).

## Parameter changes (dashboard / hot-reload)

_Nenhuma alteração de parâmetros registrada ainda._

## Memecoin paper simulation

**Restart (clean, live prices only):** 2026-09-25T11:37:41.048116-03:00

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
| BONK | laya | baseline | 1000.0000 | 0.0000 | 39.4322 | 0.0000 | 0.00% | 0 |
| BONK | laya | relaxed | 1000.0000 | 0.0000 | 39.4322 | 0.0000 | 0.00% | 0 |
| BONK | poorjev | baseline | 959.4845 | -39.8392 | -0.4070 | -39.8392 | 5.51% | 20 |
| BONK | poorjev | relaxed | 959.4767 | -39.8470 | -0.4148 | -39.8470 | 5.51% | 20 |
| BONK | von | baseline | 1000.0000 | 0.0000 | 39.4322 | 0.0000 | 0.00% | 0 |
| BONK | von | relaxed | 999.4321 | -0.5679 | 38.8643 | -0.5679 | 0.06% | 2 |
| FARTCOIN | laya | baseline | 1000.0000 | 0.0000 | -51.2266 | 0.0000 | 0.00% | 0 |
| FARTCOIN | laya | relaxed | 1000.0000 | 0.0000 | -51.2266 | 0.0000 | 0.00% | 0 |
| FARTCOIN | poorjev | baseline | 1050.4964 | 50.5618 | -0.6648 | 50.5618 | 6.83% | 20 |
| FARTCOIN | poorjev | relaxed | 1050.5247 | 50.3425 | -0.8841 | 50.3425 | 6.83% | 20 |
| FARTCOIN | von | baseline | 1000.0000 | 0.0000 | -51.2266 | 0.0000 | 0.00% | 0 |
| FARTCOIN | von | relaxed | 997.9473 | -2.0527 | -53.2794 | -2.0527 | 0.21% | 2 |
| GOAT | laya | baseline | 1000.0000 | 0.0000 | -1.5609 | 0.0000 | 0.00% | 0 |
| GOAT | laya | relaxed | 1000.0000 | 0.0000 | -1.5609 | 0.0000 | 0.00% | 0 |
| GOAT | poorjev | baseline | 1003.0121 | 3.6760 | 2.1151 | 3.6760 | 2.68% | 20 |
| GOAT | poorjev | relaxed | 1003.0038 | 3.6700 | 2.1091 | 3.6700 | 2.69% | 20 |
| GOAT | von | baseline | 1000.0000 | 0.0000 | -1.5609 | 0.0000 | 0.00% | 0 |
| GOAT | von | relaxed | 984.2109 | -15.7891 | -17.3500 | -15.7891 | 1.71% | 11 |
| MEW | laya | baseline | 1000.0000 | 0.0000 | -20.4984 | 0.0000 | 0.00% | 0 |
| MEW | laya | relaxed | 1000.0000 | 0.0000 | -20.4984 | 0.0000 | 0.00% | 0 |
| MEW | poorjev | baseline | 1011.5748 | 12.8479 | -7.6505 | 12.8479 | 3.42% | 20 |
| MEW | poorjev | relaxed | 1011.5390 | 12.8521 | -7.6463 | 12.8521 | 3.42% | 20 |
| MEW | von | baseline | 1000.0000 | 0.0000 | -20.4984 | 0.0000 | 0.00% | 0 |
| MEW | von | relaxed | 1000.0000 | 0.0000 | -20.4984 | 0.0000 | 0.00% | 0 |
| PNUT | laya | baseline | 1000.0000 | 0.0000 | -41.6667 | 0.0000 | 0.00% | 0 |
| PNUT | laya | relaxed | 1000.0000 | 0.0000 | -41.6667 | 0.0000 | 0.00% | 0 |
| PNUT | poorjev | baseline | 1037.2949 | 38.9693 | -2.6973 | 38.9693 | 2.06% | 20 |
| PNUT | poorjev | relaxed | 1037.1890 | 38.9478 | -2.7189 | 38.9478 | 2.07% | 20 |
| PNUT | von | baseline | 1000.0000 | 0.0000 | -41.6667 | 0.0000 | 0.00% | 0 |
| PNUT | von | relaxed | 998.0918 | -1.9082 | -43.5748 | -1.9082 | 0.25% | 2 |
| POPCAT | laya | baseline | 1000.0000 | 0.0000 | -34.3491 | 0.0000 | 0.00% | 0 |
| POPCAT | laya | relaxed | 1000.0000 | 0.0000 | -34.3491 | 0.0000 | 0.00% | 0 |
| POPCAT | poorjev | baseline | 1027.8434 | 29.4237 | -4.9255 | 29.4237 | 3.33% | 20 |
| POPCAT | poorjev | relaxed | 1027.8615 | 29.4417 | -4.9074 | 29.4417 | 3.33% | 20 |
| POPCAT | von | baseline | 1000.0000 | 0.0000 | -34.3491 | 0.0000 | 0.00% | 0 |
| POPCAT | von | relaxed | 998.3004 | -1.6996 | -36.0488 | -1.6996 | 0.18% | 2 |
| WIF | laya | baseline | 1000.0000 | 0.0000 | -40.7221 | 0.0000 | 0.00% | 0 |
| WIF | laya | relaxed | 1000.0000 | 0.0000 | -40.7221 | 0.0000 | 0.00% | 0 |
| WIF | poorjev | baseline | 1039.0059 | 39.9902 | -0.7319 | 39.9902 | 4.00% | 20 |
| WIF | poorjev | relaxed | 1038.4046 | 39.3475 | -1.3746 | 39.3475 | 4.00% | 20 |
| WIF | von | baseline | 1000.0000 | 0.0000 | -40.7221 | 0.0000 | 0.00% | 0 |
| WIF | von | relaxed | 999.2249 | -0.7751 | -41.4971 | -0.7751 | 0.08% | 2 |

### Ranked by vs B&H Δ (all meme portfolios)

1. **BONK** `laya/baseline` end=1000.0000 vsB&H=39.4322 vsUSDT=0.0000 trades=0
2. **BONK** `laya/relaxed` end=1000.0000 vsB&H=39.4322 vsUSDT=0.0000 trades=0
3. **BONK** `von/baseline` end=1000.0000 vsB&H=39.4322 vsUSDT=0.0000 trades=0
4. **BONK** `von/relaxed` end=999.4321 vsB&H=38.8643 vsUSDT=-0.5679 trades=2
5. **GOAT** `poorjev/baseline` end=1003.0121 vsB&H=2.1151 vsUSDT=3.6760 trades=20
6. **GOAT** `poorjev/relaxed` end=1003.0038 vsB&H=2.1091 vsUSDT=3.6700 trades=20
7. **BONK** `poorjev/baseline` end=959.4845 vsB&H=-0.4070 vsUSDT=-39.8392 trades=20
8. **BONK** `poorjev/relaxed` end=959.4767 vsB&H=-0.4148 vsUSDT=-39.8470 trades=20
9. **FARTCOIN** `poorjev/baseline` end=1050.4964 vsB&H=-0.6648 vsUSDT=50.5618 trades=20
10. **WIF** `poorjev/baseline` end=1039.0059 vsB&H=-0.7319 vsUSDT=39.9902 trades=20
11. **FARTCOIN** `poorjev/relaxed` end=1050.5247 vsB&H=-0.8841 vsUSDT=50.3425 trades=20
12. **WIF** `poorjev/relaxed` end=1038.4046 vsB&H=-1.3746 vsUSDT=39.3475 trades=20
13. **GOAT** `laya/baseline` end=1000.0000 vsB&H=-1.5609 vsUSDT=0.0000 trades=0
14. **GOAT** `laya/relaxed` end=1000.0000 vsB&H=-1.5609 vsUSDT=0.0000 trades=0
15. **GOAT** `von/baseline` end=1000.0000 vsB&H=-1.5609 vsUSDT=0.0000 trades=0
16. **PNUT** `poorjev/baseline` end=1037.2949 vsB&H=-2.6973 vsUSDT=38.9693 trades=20
17. **PNUT** `poorjev/relaxed` end=1037.1890 vsB&H=-2.7189 vsUSDT=38.9478 trades=20
18. **POPCAT** `poorjev/relaxed` end=1027.8615 vsB&H=-4.9074 vsUSDT=29.4417 trades=20
19. **POPCAT** `poorjev/baseline` end=1027.8434 vsB&H=-4.9255 vsUSDT=29.4237 trades=20
20. **MEW** `poorjev/relaxed` end=1011.5390 vsB&H=-7.6463 vsUSDT=12.8521 trades=20
21. **MEW** `poorjev/baseline` end=1011.5748 vsB&H=-7.6505 vsUSDT=12.8479 trades=20
22. **GOAT** `von/relaxed` end=984.2109 vsB&H=-17.3500 vsUSDT=-15.7891 trades=11
23. **MEW** `laya/baseline` end=1000.0000 vsB&H=-20.4984 vsUSDT=0.0000 trades=0
24. **MEW** `laya/relaxed` end=1000.0000 vsB&H=-20.4984 vsUSDT=0.0000 trades=0
25. **MEW** `von/baseline` end=1000.0000 vsB&H=-20.4984 vsUSDT=0.0000 trades=0
26. **MEW** `von/relaxed` end=1000.0000 vsB&H=-20.4984 vsUSDT=0.0000 trades=0
27. **POPCAT** `laya/baseline` end=1000.0000 vsB&H=-34.3491 vsUSDT=0.0000 trades=0
28. **POPCAT** `laya/relaxed` end=1000.0000 vsB&H=-34.3491 vsUSDT=0.0000 trades=0
29. **POPCAT** `von/baseline` end=1000.0000 vsB&H=-34.3491 vsUSDT=0.0000 trades=0
30. **POPCAT** `von/relaxed` end=998.3004 vsB&H=-36.0488 vsUSDT=-1.6996 trades=2

- Meme decisions by model: {'rule': 2944, 'von': 106, 'laya': 106, 'poorjev': 106, 'poorjev+rules': 53} skipped_no_price=0
- Meme trades by model: {'poorjev': 594, '?': 80, 'von': 21}
- Sources seen: ['gate.io']
- Meme models enabled (status): ['von', 'laya', 'poorjev']

## Rule strategies & hybrids (paper)

- rules_bot started_brt (status): 2026-09-25T11:37:39.646285-03:00
- warm_up: {"warmed_at_brt": "2026-09-25T11:37:39.605851-03:00", "sol_bars": 1080, "sol_first_brt": "2026-08-10T15:00:00-03:00", "sol_last_brt": "2026-09-24T14:00:00-03:00", "meme_bars": {"BONK": 1101, "WIF": 1101, "POPCAT": 1101, "FARTCOIN": 1101, "PNUT": 1101, "MEW": 1101, "GOAT": 1101}, "trade_only_after_ts": 1790347059.6054003, "trade_only_after_brt": "2026-09-25T11:37:39.605400-03:00"}
- SOL indicators now: close=120.63 ema12=121.04674225665515 ema26=119.67737042661824 rsi=56.02084257355781 bull=True

### SOL rule / hybrid portfolios

| Portfolio | Strategy | Decisions | Trades | Equity end | vs B&H Δ | MDD | Start BRT |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| grid_sol_2pct | rule:grid_sol_2pct | 177 | 0 | 1001.1729 | 0.0000 | 0.11% | 2026-09-24T21:07:54.411779-03:00 |
| rsi_sol_1h | rule:rsi_sol_1h | 177 | 1 | 1001.4299 | 0.2570 | 0.11% | 2026-09-24T21:07:54.411779-03:00 |
| hybrid_von_relaxed_cap2 | rule:hybrid_von_relaxed_cap2 | 354 | 41 | 1030.9598 | 29.7869 | 1.94% | 2026-09-24T21:07:46.591554-03:00 |

### Meme rule / hybrid portfolios

| Portfolio | Trades | Equity end | Last signal | Start BRT |
| --- | ---: | ---: | --- | --- |
| BONK_rule_regime | 1 | 990.6134 | hold | 2026-09-24T21:07:54.411779-03:00 |
| BONK_rule_donch_regime | 0 | 1000.0000 | hold | 2026-09-24T21:07:54.411779-03:00 |
| BONK_hybrid_poorjev_regime | 20 | 959.7628 | hold | 2026-09-24T21:07:55.970939-03:00 |
| WIF_rule_regime | 1 | 1010.1984 | hold | 2026-09-24T21:07:54.411779-03:00 |
| WIF_rule_donch_regime | 1 | 1004.8403 | hold | 2026-09-24T21:07:54.411779-03:00 |
| WIF_hybrid_poorjev_regime | 20 | 1037.5442 | hold | 2026-09-24T21:07:55.970939-03:00 |
| POPCAT_rule_regime | 1 | 1007.3036 | hold | 2026-09-24T21:07:54.411779-03:00 |
| POPCAT_rule_donch_regime | 1 | 1000.2366 | hold | 2026-09-24T21:07:54.411779-03:00 |
| POPCAT_hybrid_poorjev_regime | 20 | 1027.8717 | hold | 2026-09-24T21:07:55.970939-03:00 |
| FARTCOIN_rule_regime | 1 | 1012.1761 | hold | 2026-09-24T21:07:54.411779-03:00 |
| FARTCOIN_rule_donch_regime | 1 | 998.2071 | hold | 2026-09-24T21:07:54.411779-03:00 |
| FARTCOIN_hybrid_poorjev_regime | 20 | 1050.3332 | hold | 2026-09-24T21:07:55.970939-03:00 |
| PNUT_rule_regime | 1 | 1009.9981 | hold | 2026-09-24T21:07:54.411779-03:00 |
| PNUT_rule_donch_regime | 1 | 1003.0531 | hold | 2026-09-24T21:07:54.411779-03:00 |
| PNUT_hybrid_poorjev_regime | 20 | 1037.1311 | hold | 2026-09-24T21:07:55.970939-03:00 |
| MEW_rule_regime | 1 | 1003.0524 | hold | 2026-09-24T21:07:54.411779-03:00 |
| MEW_rule_donch_regime | 0 | 1000.0000 | hold | 2026-09-24T21:07:54.411779-03:00 |
| MEW_hybrid_poorjev_regime | 20 | 1011.4594 | hold | 2026-09-24T21:07:55.970939-03:00 |
| GOAT_rule_regime | 1 | 1003.1291 | hold | 2026-09-24T21:07:54.411779-03:00 |
| GOAT_rule_donch_regime | 0 | 1000.0000 | hold | 2026-09-24T21:07:54.411779-03:00 |
| GOAT_hybrid_poorjev_regime | 20 | 1003.2257 | hold | 2026-09-24T21:07:55.970939-03:00 |

- Total rule-tagged trades (SOL+meme logs): 204

## Verdict

**Worth running live?** Not on this sample alone.
- Compare baseline (conf≥0.6, may trade ~0) vs relaxed (calibrated) honestly.
- Fills are Jupiter quotes minus haircuts — not identical to on-chain execution/MEV/failures.
- Marks are live-only (Gate.io / Coinpaprika / DexScreener / Jupiter); no seed/fabricated fallback.
- Keep paper-only until multi-day baseline vs relaxed vs v2 vs buy&hold shows stable edge after fees.

## Caveats

- Simulation only; wallet keys never loaded.
- Memecoin night-review/v2 shadow skipped.
- Each meme portfolio starts with 1000.0 USDT flat (von baseline+relaxed per token; plus `{SYM}_{model}_{profile}` when memes_enabled).
- Rule portfolios: `grid_sol_2pct`, `rsi_sol_1h`, `{SYM}_rule_regime`, `{SYM}_rule_donch_regime`, `hybrid_von_relaxed_cap2`, `{SYM}_hybrid_poorjev_regime`.
- Meme clean restart noted in status: 2026-09-25T11:37:41.048116-03:00.
