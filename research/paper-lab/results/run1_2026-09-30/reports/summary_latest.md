# Resumo do run paper — 2026-10-30 23:39 BRT

## Saúde

- Processos: todos ativos · heartbeat/erros: sol 1s/0 erros; meme 29s/0 erros; rules 21s/0 erros; lab 2s/0 erros; nightly 38s/0 erros
- Painel no telemóvel: https://backing-efficient-explicitly-south.trycloudflare.com (login do .auth)
- Reinícios nas últimas 72 h: poorjev×13, von×1, laya×1, sol×1, meme×1, rules×1, lab×1, nightly×1, dashboard×1 · disco livre 144 GB

## Desde o início (29.1 dias, 189 portfólios)

Melhores por PnL:

| Portfólio | PnL % | PnL US$ | Exposição | Excesso aj. exposição US$ | Trades (C/V) |
|---|---:|---:|---:|---:|---|
| poorjev_relaxed__fork4 | +0.93% | +8.04 | 70% | +49.97 | 196 (180/16) |
| rsi_sol_1h__fork1 | +0.91% | +8.75 | 32% | +23.79 | 5 (4/1) |
| meme_POPCAT_relaxed__fork1 | +0.64% | +6.15 | 0% | +6.34 | 1 (0/1) |
| meme_GOAT_relaxed__fork1 | +0.56% | +5.50 | 1% | +6.52 | 1 (0/1) |
| meme_FARTCOIN_relaxed | +0.55% | +5.46 | 3% | +14.03 | 139 (89/50) |

Piores por PnL:

| Portfólio | PnL % | PnL US$ | Exposição | Excesso aj. exposição US$ | Trades (C/V) |
|---|---:|---:|---:|---:|---|
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | -47.21% | -497.99 | 79% | -220.93 | 2094 (1957/137) |
| h1_exits_GOAT_poorjev_relaxed | -40.39% | -403.88 | 96% | -196.07 | 517 (491/26) |
| GOAT_rule_regime_full | -34.26% | -342.59 | 33% | -270.82 | 26 (13/13) |
| h1_exits_WIF_poorjev_relaxed__fork1 | -32.76% | -331.58 | 96% | -17.51 | 476 (452/24) |
| h1_exits_WIF_poorjev_relaxed | -31.71% | -317.15 | 96% | -3.94 | 581 (553/28) |

Melhor seleção (excesso ajustado à exposição, o que não é só beta):

| Portfólio | PnL % | PnL US$ | Exposição | Excesso aj. exposição US$ | Trades (C/V) |
|---|---:|---:|---:|---:|---|
| h1_exits_FARTCOIN_poorjev_relaxed | -22.39% | -223.90 | 94% | +84.19 | 841 (800/41) |
| h1_exits_WIF_poorjev_relaxed__fork3 | -6.12% | -53.34 | 90% | +76.72 | 374 (355/19) |
| h1_exits_von_relaxed__fork1 | -7.21% | -73.31 | 63% | +64.35 | 649 (587/62) |
| rsi_sol_1h | -1.49% | -14.90 | 37% | +57.09 | 19 (15/4) |
| poorjev_relaxed__fork4 | +0.93% | +8.04 | 70% | +49.97 | 196 (180/16) |

## Últimas 72 h

- Trades: 5461 em 105 portfólios; mais ativos: laya_relaxed__fork1 (344), h1_exits_FARTCOIN_poorjev_relaxed__fork1 (274), poorjev_relaxed__fork1 (249), h1_exits_von_relaxed (239), h1_exits_FARTCOIN_poorjev_relaxed (140)
- Vereditos: inconclusivo 185, perdedora 4 (mínimos: ≥30 RT e ≥21 dias)

## Forks (80)

| Fork | Quem | O que mudou | Idade | PnL fork − pai (pp) | Habilidade fork − pai US$ | Trades fork/pai |
|---|---|---|---:|---:|---:|---|
| relaxed__fork1 | nightly | take-profit 0.025, stop-loss 0.015, trailing 0.01, armar trailing 0.01, reentrad | 671 h | +11.23 | +13.56 | 401/261 |
| poorjev_relaxed__fork1 | nightly | take-profit 0.025, stop-loss 0.015, trailing 0.01, armar trailing 0.01, reentrad | 671 h | -7.64 | -55.62 | 1340/19 |
| h1_exits_FARTCOIN_poorjev_relaxed__fork1 | nightly | take-profit 0.015, trailing 0.007, armar trailing 0.007 | 671 h | -20.69 | -271.75 | 2094/779 |
| h2_ensemble_FARTCOIN__fork1 | nightly | pausa entre trades (s) 600 | 671 h | +2.35 | +22.38 | 332/420 |
| h2_ensemble_WIF__fork1 | nightly | pausa entre trades (s) 600 | 671 h | +1.38 | +12.89 | 223/271 |
| relaxed_expcap50__fork1 | claude-night | critérios reescritos | 670 h | +11.40 | +14.08 | 1/118 |
| laya_relaxed__fork1 | claude-night | confiança mínima 0.04, margem mínima 0.0 | 670 h | -28.52 | -211.76 | 2581/0 |
| FARTCOIN_laya_relaxed__fork1 | claude-night | confiança mínima 0.07, margem mínima 0.0 | 670 h | -4.11 | -35.99 | 20/0 |
| h1_exits_von_relaxed__fork1 | claude-night | critérios reescritos | 646 h | +15.53 | +100.40 | 649/1343 |
| h1_exits_WIF_poorjev_relaxed__fork1 | claude-night | critérios reescritos | 646 h | -0.19 | -2.00 | 476/477 |
| h1_exits_BONK_poorjev_relaxed__fork1 | claude-night | reentrada (min) 120 | 622 h | +5.11 | +39.07 | 556/605 |
| h1_exits_MEW_poorjev_relaxed__fork1 | claude-night | reentrada (min) 120 | 622 h | -1.90 | -33.19 | 610/711 |
| laya_relaxed__fork2 | claude-night | pausa entre trades (s) 3600 | 598 h | +17.74 | +162.60 | 438/2363 |
| FARTCOIN_laya_relaxed__fork2 | claude-night | confiança mínima 0.07, margem mínima 0.0, skip máximo 0.95 | 598 h | -10.26 | -81.56 | 243/0 |
| h1_exits_WIF_poorjev_relaxed__fork2 | claude-night | confiança mínima 0.75 | 598 h | +7.35 | +57.00 | 422/451 |
| h1_exits_von_relaxed__fork2 | claude-night | pausa entre trades (s) 3600 | 574 h | +7.10 | +25.82 | 463/1240 |
| poorjev_relaxed__fork2 | claude-night | pausa entre trades (s) 3600 | 574 h | +7.78 | +33.14 | 497/1216 |
| FARTCOIN_laya_relaxed__fork3 | claude-night | pausa entre trades (s) 3600 | 550 h | +1.65 | +15.53 | 103/229 |
| laya_relaxed__fork3 | claude-night | critérios reescritos | 550 h | +7.79 | +19.76 | 3/401 |
| h1_exits_hybrid_von_cap2__fork1 | nightly | confiança mínima 0.42 | 527 h | +4.51 | +10.47 | 0/218 |
| h2_ensemble_sol__fork1 | nightly | percentil mínimo 0.96 | 527 h | +5.02 | +53.99 | 23/599 |
| h3_limit_hybrid_von_cap2__fork1 | nightly | confiança mínima 0.42 | 527 h | +12.41 | +33.47 | 0/31 |
| h4_hours_von_relaxed__fork1 | nightly | confiança mínima 0.42 | 527 h | +0.99 | +10.19 | 0/64 |
| hybrid_von_relaxed_cap2__fork1 | nightly | confiança mínima 0.42 | 527 h | +10.69 | +40.27 | 0/99 |
| h1_exits_GOAT_poorjev_relaxed__fork1 | nightly | stop-loss 0.036000000000000004, reentrada (min) 36 | 527 h | +5.62 | +54.11 | 334/352 |
| h1_exits_PNUT_poorjev_relaxed__fork1 | nightly | stop-loss 0.032, trades por hora 6 | 527 h | -0.29 | -3.24 | 387/376 |
| h1_exits_POPCAT_poorjev_relaxed__fork1 | nightly | stop-loss 0.032 | 527 h | -3.33 | -31.23 | 504/463 |
| meme_BONK_relaxed__fork1 | nightly | confiança mínima 0.385 | 527 h | +4.47 | +43.29 | 1/118 |
| meme_MEW_relaxed__fork1 | nightly | confiança mínima 0.385 | 527 h | +8.57 | +81.99 | 0/123 |
| meme_POPCAT_relaxed__fork1 | nightly | confiança mínima 0.385 | 527 h | +4.11 | +37.56 | 1/81 |
| meme_WIF_relaxed__fork1 | nightly | confiança mínima 0.385 | 527 h | +7.68 | +72.00 | 1/146 |
| h1_exits_FARTCOIN_poorjev_relaxed__fork2 | claude-night | reentrada (min) 120 | 526 h | +4.50 | +29.02 | 471/602 |
| h1_exits_WIF_poorjev_relaxed__fork3 | claude-night | reentrada (min) 120 | 526 h | +15.55 | +126.41 | 374/375 |
| relaxed__fork2 | nightly | confiança mínima 0.42, fração por compra 0.3, stop-loss 0.0135 | 503 h | +6.04 | +8.73 | 1/321 |
| meme_PNUT_relaxed__fork1 | nightly | confiança mínima 0.385 | 503 h | +3.37 | +28.41 | 0/63 |
| relaxed_expcap50__fork2 | nightly | confiança mínima 0.42 | 479 h | +1.58 | +14.62 | 0/99 |
| meme_GOAT_relaxed__fork1 | nightly | confiança mínima 0.385 | 479 h | +8.14 | +77.90 | 1/94 |
| h1_exits_BONK_poorjev_relaxed__fork2 | nightly | stop-loss 0.036000000000000004, take-profit 0.054, fração por compra 0.3 | 431 h | +2.42 | +23.90 | 356/429 |
| h1_exits_MEW_poorjev_relaxed__fork2 | nightly | stop-loss 0.032 | 431 h | -4.67 | -42.89 | 553/483 |
| h1_exits_von_relaxed__fork3 | nightly | confiança mínima 0.42, trailing 0.008, armar trailing 0.008, stop-loss 0.012 | 383 h | +6.99 | +31.99 | 1/313 |
| h3_limit_poorjev_relaxed__fork1 | nightly | margem mínima 0.24 | 383 h | +0.09 | +1.26 | 5/10 |
| poorjev_baseline__fork1 | nightly | confiança mínima 0.72 | 383 h | +0.18 | +0.34 | 0/9 |
| poorjev_relaxed__fork3 | nightly | armar trailing 0.008 | 383 h | +2.10 | +17.27 | 377/338 |
| rsi_sol_1h__fork1 | nightly | período do RSI 17 | 383 h | -1.47 | -18.85 | 5/9 |
| h2_ensemble_sol__fork2 | nightly | percentil mínimo 0.96 | 359 h | +1.41 | +17.21 | 0/448 |
| h3_limit_hybrid_von_cap2__fork2 | nightly | confiança mínima 0.42 | 359 h | +0.91 | +9.87 | 0/9 |
| h4_hours_von_relaxed__fork2 | nightly | confiança mínima 0.42 | 359 h | +0.15 | +1.53 | 0/20 |
| hybrid_von_relaxed_cap2__fork2 | nightly | confiança mínima 0.42 | 359 h | -1.59 | +12.65 | 0/64 |
| h1_exits_GOAT_poorjev_relaxed__fork2 | nightly | stop-loss 0.036000000000000004, trailing 0.024, take-profit 0.072, reentrada (mi | 359 h | +2.45 | +17.52 | 179/217 |
| h1_exits_PNUT_poorjev_relaxed__fork2 | nightly | stop-loss 0.0256 | 359 h | -7.97 | -67.36 | 340/274 |
| h1_exits_POPCAT_poorjev_relaxed__fork2 | nightly | reentrada (min) 36 | 359 h | +1.56 | +11.12 | 318/323 |
| meme_BONK_relaxed__fork2 | nightly | confiança mínima 0.385 | 359 h | +3.48 | +33.99 | 0/73 |
| meme_MEW_relaxed__fork2 | nightly | confiança mínima 0.385 | 359 h | +5.21 | +49.23 | 0/66 |
| meme_POPCAT_relaxed__fork2 | nightly | confiança mínima 0.385 | 359 h | +2.90 | +25.93 | 0/44 |
| meme_WIF_relaxed__fork2 | nightly | confiança mínima 0.385 | 359 h | +5.37 | +49.07 | 0/97 |
| BONK_rule_regime_full__fork1 | nightly | EMA lenta (regime SOL) 31 | 359 h | -7.92 | -65.65 | 13/13 |
| FARTCOIN_rule_regime_full__fork1 | nightly | EMA rápida (regime SOL) 10 | 359 h | -2.71 | -19.25 | 15/13 |
| GOAT_rule_regime_full__fork1 | nightly | EMA rápida (regime SOL) 10 | 359 h | -2.28 | -16.35 | 15/13 |
| POPCAT_rule_regime_full__fork1 | nightly | EMA rápida (regime SOL) 10 | 359 h | -2.92 | -22.30 | 15/13 |
| WIF_rule_regime_full__fork1 | nightly | EMA rápida (regime SOL) 10 | 359 h | -3.26 | -23.80 | 15/13 |
| h1_exits_hybrid_von_cap2__fork2 | nightly | confiança mínima 0.42 | 335 h | +1.50 | -5.72 | 0/173 |
| relaxed__fork3 | nightly | confiança mínima 0.42, fração por compra 0.3 | 335 h | +3.22 | -1.17 | 1/212 |
| h1_exits_FARTCOIN_poorjev_relaxed__fork3 | nightly | trades por hora 6 | 335 h | +0.55 | +6.97 | 376/381 |
| h1_exits_WIF_poorjev_relaxed__fork4 | nightly | take-profit 0.054, stop-loss 0.036000000000000004, fração por compra 0.3 | 335 h | +8.52 | +70.11 | 222/215 |
| meme_PNUT_relaxed__fork2 | nightly | confiança mínima 0.385 | 335 h | +2.28 | +19.54 | 0/47 |
| relaxed_expcap50__fork3 | nightly | confiança mínima 0.42 | 311 h | +1.19 | +11.50 | 0/62 |
| meme_GOAT_relaxed__fork2 | nightly | confiança mínima 0.385 | 311 h | +4.70 | +43.41 | 0/68 |
| h1_exits_BONK_poorjev_relaxed__fork3 | nightly | stop-loss 0.036000000000000004, fração por compra 0.3 | 263 h | -5.72 | -45.28 | 266/329 |
| h1_exits_MEW_poorjev_relaxed__fork3 | nightly | stop-loss 0.036000000000000004, fração por compra 0.3 | 263 h | -0.23 | -0.01 | 383/395 |
| meme_FARTCOIN_relaxed__fork1 | nightly | confiança mínima 0.385 | 263 h | +1.55 | +12.86 | 0/54 |
| MEW_rule_donch_regime_full__fork1 | nightly | EMA rápida (regime SOL) 13 | 239 h | -0.04 | -0.61 | 3/3 |
| h1_exits_von_relaxed__fork4 | nightly | confiança mínima 0.42, fração por compra 0.2, trailing 0.008, take-profit 0.0275 | 214 h | +1.54 | -37.84 | 1/169 |
| poorjev_relaxed__fork4 | nightly | pausa entre trades (s) 3240, fração por compra 0.2, stop-loss 0.018, trailing 0. | 213 h | +1.75 | +1.95 | 196/180 |
| h3_limit_hybrid_von_cap2__fork3 | nightly | confiança mínima 0.42 | 191 h | +0.58 | +13.21 | 0/1 |
| h3_limit_poorjev_relaxed__fork2 | nightly | margem mínima 0.22000000000000003 | 191 h | +0.09 | +0.12 | 5/6 |
| h4_hours_von_relaxed__fork3 | nightly | confiança mínima 0.42 | 191 h | +0.23 | +3.76 | 0/20 |
| hybrid_von_relaxed_cap2__fork3 | nightly | confiança mínima 0.42 | 191 h | +5.35 | +23.53 | 0/20 |
| laya_relaxed__fork4 | nightly | fração por compra 0.2 | 191 h | +0.65 | +2.66 | 153/152 |
| h1_exits_GOAT_poorjev_relaxed__fork3 | nightly | trades por hora 6 | 191 h | +0.60 | +8.47 | 112/114 |
| h1_exits_PNUT_poorjev_relaxed__fork3 | nightly | fração por compra 0.3 | 191 h | -0.60 | -4.67 | 137/154 |

## Bot real (paper, livro da carteira)

- **A** (relaxed_paper, desde 2026-09-30T00:50:19-03:00): 0.429854 SOL + 0.00 USDT = US$ 41.65; contra segurar -10.05 US$ (-19.43%)
  hit 15 min 118/272 (43%) · max DD 25.38% · trades 272 (182/90) · saídas 0 (tp 0/sl 0/trail 0) · SOL 100% do livro
- **B** (relaxed_exits_paper, desde 2026-10-03T13:20:50-03:00): 0.245542 SOL + 23.06 USDT = US$ 46.85; contra segurar -4.85 US$ (-9.38%)
  hit 15 min 2195/4397 (50%) · max DD 12.40% · trades 4407 (4335/72) · saídas 66 (tp 9/sl 35/trail 22) · SOL 51% do livro
