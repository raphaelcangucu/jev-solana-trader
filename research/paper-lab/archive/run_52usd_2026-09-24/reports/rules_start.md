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
