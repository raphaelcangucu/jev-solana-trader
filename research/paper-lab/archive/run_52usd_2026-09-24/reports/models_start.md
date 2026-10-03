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
