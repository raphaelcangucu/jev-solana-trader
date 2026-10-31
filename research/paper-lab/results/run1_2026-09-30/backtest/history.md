# Histórico das simulações retroativas

Atualizado (BRT): 2026-10-17T20:45:41-03:00 · runs no índice: 6 (3 mensais, 1 longo(s)). Fonte: `data/backtest/index.json` e os `summary.json` de cada pasta. Paper only: nada aqui é ordem real.

Todos os runs usam o MESMO catálogo e os mesmos pressupostos (instantâneo `inputs/` do run bt30_2026-10-06: registry, params, overlay, critérios, models.json; custos de execução por ativo medidos nos fills reais do run ao vivo). Cada run começa com o capital inicial no início da sua janela (não herda posições).

Estudos à parte (etiqueta `tag`, outro catálogo; não entram nas comparações abaixo): bt180x_2026-10-06 (moedas_novas, 180d), bt30x_2026-10-06 (moedas_novas, 30d).

## Meses lado a lado

| | **bt30_2026-08-06** | **bt30_2026-09-06** | **bt30_2026-10-06** |
|---|---|---|---|
| Janela (BRT, 09:00) | 2026-07-07 → 2026-08-06 | 2026-08-06 → 2026-09-06 | 2026-09-06 → 2026-10-06 |
| Dias | 30 | 31 | 30 |
| Portfólios | 127 | 127 | 127 |
| Vencedoras / perdedoras / inconclusivas | 0 / 5 / 122 | 0 / 7 / 120 | 0 / 10 / 117 |
| Maior habilidade | FARTCOIN_rule_donch_regime_full | h3_limit_hybrid_von_cap2 | poorjev_baseline |
| Maior PnL | FARTCOIN_rule_donch_regime_full | h1_exits_FARTCOIN_poorjev_relaxed | MEW_poorjev_baseline |
| Pelo veredito | nenhum | nenhum | nenhum |
| Bot real livro A | -9.61% (vs segurar -4.803 $) | +45.18% (vs segurar +22.599 $) | +12.49% (vs segurar +6.239 $) |
| Bot real livro B | -11.20% (vs segurar -5.621 $) | +0.33% (vs segurar -0.403 $) | -4.27% (vs segurar -2.457 $) |

### Movimento do mercado (retorno do ativo na janela)

| Ativo | bt30_2026-08-06 | bt30_2026-09-06 | bt30_2026-10-06 |
|---|---:|---:|---:|
| SOL | -9.69% | +45.08% | +13.02% |
| BONK | -34.96% | +18.99% | +14.42% |
| WIF | -17.43% | +55.28% | +17.06% |
| POPCAT | -11.65% | +22.62% | +1.39% |
| FARTCOIN | -20.10% | +42.15% | -4.92% |
| PNUT | -12.97% | +31.06% | +7.33% |
| MEW | -14.05% | +32.57% | +20.40% |
| GOAT | -11.98% | +23.27% | +17.09% |
| Memes (média simples) | -17.59% | +32.28% | +10.39% |

### Top 5 por PnL

| # | bt30_2026-08-06 | bt30_2026-09-06 | bt30_2026-10-06 |
|---:|---|---|---|
| 1 | FARTCOIN_rule_donch_regime_full (+1.17%) | h1_exits_FARTCOIN_poorjev_relaxed (+55.94%) | MEW_poorjev_baseline (+20.01%) |
| 2 | rsi_sol_1h (+0.83%) | WIF_hybrid_poorjev_regime (+55.42%) | MEW_poorjev_relaxed (+20.01%) |
| 3 | FARTCOIN_rule_donch_regime (+0.32%) | WIF_poorjev_baseline (+54.91%) | MEW_hybrid_poorjev_regime (+20.01%) |
| 4 | relaxed_expcap50__fork1 (+0.02%) | WIF_poorjev_relaxed (+54.91%) | poorjev_baseline (+19.21%) |
| 5 | meme_BONK_baseline (+0.00%) | h2_ensemble_sol (+50.90%) | poorjev_relaxed (+19.21%) |

### Top 5 por habilidade (excesso ajustado à exposição, US$)

| # | bt30_2026-08-06 | bt30_2026-09-06 | bt30_2026-10-06 |
|---:|---|---|---|
| 1 | FARTCOIN_rule_donch_regime_full (+69.12 $, +1.17%) | h3_limit_hybrid_von_cap2 (+155.88 $, +49.68%) | poorjev_baseline (+83.96 $, +19.21%) |
| 2 | h1_exits_BONK_poorjev_relaxed (+57.03 $, -32.42%) | h1_exits_FARTCOIN_poorjev_relaxed (+153.37 $, +55.94%) | poorjev_relaxed (+83.96 $, +19.21%) |
| 3 | BONK_hybrid_poorjev_regime (+48.91 $, -34.82%) | hybrid_von_relaxed_cap2 (+151.33 $, +49.58%) | h3_limit_poorjev_relaxed (+81.46 $, +18.59%) |
| 4 | BONK_poorjev_baseline (+45.56 $, -35.22%) | h2_ensemble_sol (+138.86 $, +50.90%) | GOAT_rule_donch_regime_full (+78.67 $, +14.04%) |
| 5 | BONK_poorjev_relaxed (+45.56 $, -35.22%) | BONK_hybrid_poorjev_regime (+121.90 $, +34.01%) | rsi_sol_1h (+56.33 $, +7.69%) |

## Quem aparece bem em vários meses

Portfólios presentes nos 3 meses com habilidade > 0 em ≥ 2 meses, ou no top 15 (habilidade ou PnL) em ≥ 2 meses. Habilidade = excesso ajustado à exposição (o que sobra do PnL depois de descontar o efeito de estar exposto ao ativo); positivo em vários meses é o sinal que interessa, PnL alto com habilidade negativa é só beta (o ativo subiu).

| Portfólio | Família | Hab. > 0 | Bate B&H | Top 15 hab. | Top 15 PnL | PnL composto % | Hab. somada $ | PnL por mês % (antigo → recente) | Hab. por mês $ (antigo → recente) |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| GOAT_rule_donch_regime_full | Meme · regras | 3/3 | 1/3 | 2/3 | 0/3 | +24.57 | +106.47 | -0.50 · +9.78 · +14.04 | +15.95 · +11.85 · +78.67 |
| rsi_sol_1h | SOL · regras | 3/3 | 3/3 | 2/3 | 1/3 | +12.83 | +94.76 | +0.83 · +3.90 · +7.69 | +35.08 · +3.35 · +56.33 |
| grid_sol_2pct | SOL · regras | 3/3 | 2/3 | 2/3 | 0/3 | +18.18 | +80.54 | -3.66 · +10.93 · +10.58 | +23.99 · +5.48 · +51.07 |
| GOAT_rule_donch_regime | Meme · regras | 3/3 | 1/3 | 2/3 | 1/3 | +6.26 | +28.49 | -0.08 · +2.60 · +3.64 | +4.41 · +3.44 · +20.64 |
| poorjev_baseline | SOL · poorjev | 2/3 | 2/3 | 2/3 | 3/3 | +58.38 | +175.19 | -0.38 · +33.36 · +19.21 | -0.33 · +91.56 · +83.96 |
| poorjev_relaxed | SOL · poorjev | 2/3 | 2/3 | 2/3 | 2/3 | +58.38 | +175.19 | -0.38 · +33.36 · +19.21 | -0.33 · +91.56 · +83.96 |
| h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | 2/3 | 2/3 | 2/3 | 3/3 | +57.66 | +173.68 | -0.38 · +33.46 · +18.59 | -0.33 · +92.54 · +81.46 |
| BONK_hybrid_poorjev_regime | Meme · híbridos | 2/3 | 3/3 | 2/3 | 2/3 | +0.01 | +124.27 | -34.82 · +34.01 · +14.50 | +48.91 · +121.90 · -46.54 |
| FARTCOIN_rule_donch_regime_full | Meme · regras | 2/3 | 2/3 | 2/3 | 1/3 | +20.61 | +120.03 | +1.17 · +20.78 · -1.30 | +69.12 · +71.81 · -20.90 |
| h4_hours_poorjev_relaxed | SOL · hipóteses (lab) | 2/3 | 2/3 | 2/3 | 0/3 | +45.95 | +106.46 | -0.38 · +32.36 · +10.69 | -0.33 · +85.29 · +21.50 |
| FARTCOIN_rule_regime | Meme · regras | 2/3 | 2/3 | 2/3 | 0/3 | +3.63 | -15.22 | -1.41 · +3.41 · +1.64 | +7.15 · -35.44 · +13.06 |
| FARTCOIN_rule_regime_full | Meme · regras | 2/3 | 2/3 | 2/3 | 0/3 | +9.64 | -97.47 | -5.89 · +11.65 · +4.35 | +24.62 · -152.66 · +30.58 |
| FARTCOIN_rule_donch_regime | Meme · regras | 2/3 | 2/3 | 1/3 | 1/3 | +5.59 | +32.17 | +0.32 · +5.24 · +0.02 | +17.75 · +16.31 · -1.90 |
| BONK_rule_regime | Meme · regras | 2/3 | 1/3 | 1/3 | 0/3 | +1.02 | -5.37 | -5.27 · +3.75 · +2.79 | -8.40 · +1.74 · +1.30 |
| WIF_hybrid_poorjev_regime | Meme · híbridos | 1/3 | 2/3 | 1/3 | 2/3 | +50.74 | +49.49 | -17.43 · +55.42 · +17.47 | -1.32 · +87.46 · -36.65 |
| WIF_poorjev_baseline | Meme · poorjev | 1/3 | 1/3 | 1/3 | 2/3 | +49.41 | +23.82 | -17.89 · +54.91 · +17.47 | -5.64 · +66.11 · -36.65 |
| WIF_poorjev_relaxed | Meme · poorjev | 1/3 | 1/3 | 1/3 | 2/3 | +49.41 | +23.82 | -17.89 · +54.91 · +17.47 | -5.64 · +66.11 · -36.65 |
| meme_BONK_baseline | Meme · von | 0/3 | 1/3 | 2/3 | 0/3 | +0.00 | +0.00 | +0.00 · +0.00 · +0.00 | +0.00 · +0.00 · +0.00 |

Habilidade positiva em TODOS os 3 meses: GOAT_rule_donch_regime, GOAT_rule_donch_regime_full, grid_sol_2pct, rsi_sol_1h.
⚠ = fork desenhado com dados de 2026-10-01 → 2026-10-06 (só o mês mais recente tem look-ahead; nos meses anteriores estes forks estão fora da amostra).

## 180 dias seguidos — bt180_2026-10-06

Janela 2026-04-09T09:00:00-03:00 → 2026-10-06T09:00:00-03:00; capital inicial no início da janela; mesma regra de veredito com consistência mensal (excesso vs B&H positivo em ≥ 4 de 6 blocos de 30 dias) e métricas sobre a série horária (ver Pressupostos no report.md do run). Gráfico: `chart.json` na pasta do run.

| Benchmark (1000 no início) | Fim | Retorno |
|---|---:|---:|
| SOL buy & hold | 1464.1 | +46.41% |
| Cesto das 7 memecoins (peso igual) | 1054.8 | +5.48% |
| USDC a 6%/a | 1029.6 | +2.96% |

Vereditos: 0 vencedoras, 15 perdedoras, 112 inconclusivas. Maior habilidade: **h4_hours_poorjev_relaxed**; maior PnL: **h4_hours_poorjev_relaxed**; pelo veredito: **nenhum**.

### Top 15 por PnL

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | MDD % | Trades | Meses > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | h4_hours_poorjev_relaxed | SOL · hipóteses (lab) | +61.40 | +595.83 | **+279.96** | -15.75 | 20 | 4/6 | inconclusiva |
| 2 | h3_limit_hybrid_von_cap2 | SOL · hipóteses (lab) | +50.73 | +489.15 | **+119.01** | -23.84 | 910 | 4/6 | inconclusiva |
| 3 | hybrid_von_relaxed_cap2 | SOL · híbridos | +48.32 | +465.03 | **+92.09** | -24.31 | 945 | 4/6 | inconclusiva |
| 4 | h4_hours_von_relaxed | SOL · hipóteses (lab) | +44.54 | +427.16 | **-7.60** | -38.26 | 468 | 4/6 | inconclusiva |
| 5 | FARTCOIN_rule_regime_full | Meme · regras | +43.48 | +450.47 | **+267.64** | -39.09 | 140 | 4/6 | inconclusiva |
| 6 | h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | +41.14 | +393.19 | **+33.28** | -30.48 | 20 | 4/6 | inconclusiva |
| 7 | poorjev_baseline | SOL · poorjev | +38.91 | +370.90 | **+7.49** | -31.56 | 20 | 4/6 | inconclusiva |
| 8 | poorjev_relaxed | SOL · poorjev | +37.74 | +359.24 | **-4.84** | -32.14 | 20 | 4/6 | inconclusiva |
| 9 | WIF_poorjev_baseline | Meme · poorjev | +32.32 | -4.56 | **-191.50** | -46.56 | 20 | 3/6 | inconclusiva |
| 10 | WIF_poorjev_relaxed | Meme · poorjev | +32.32 | -4.56 | **-191.50** | -46.56 | 20 | 3/6 | inconclusiva |
| 11 | PNUT_poorjev_baseline | Meme · poorjev | +30.58 | -6.18 | **-223.68** | -52.82 | 20 | 2/6 | inconclusiva |
| 12 | PNUT_poorjev_relaxed | Meme · poorjev | +30.58 | -6.18 | **-223.68** | -52.82 | 20 | 2/6 | inconclusiva |
| 13 | relaxed | SOL · von | +29.77 | +279.55 | **-157.54** | -40.64 | 1488 | 4/6 | inconclusiva |
| 14 | grid_sol_2pct | SOL · regras | +29.10 | +272.77 | **+36.98** | -22.89 | 20 | 4/6 | inconclusiva |
| 15 | WIF_hybrid_poorjev_regime | Meme · híbridos | +27.44 | -53.34 | **-239.61** | -46.55 | 20 | 3/6 | inconclusiva |

### Top 15 por habilidade

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | MDD % | Trades | Meses > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | h4_hours_poorjev_relaxed | SOL · hipóteses (lab) | +61.40 | +595.83 | **+279.96** | -15.75 | 20 | 4/6 | inconclusiva |
| 2 | FARTCOIN_rule_regime_full | Meme · regras | +43.48 | +450.47 | **+267.64** | -39.09 | 140 | 4/6 | inconclusiva |
| 3 | BONK_rule_regime_full | Meme · regras | +3.16 | +373.92 | **+134.14** | -34.25 | 140 | 4/6 | inconclusiva |
| 4 | h3_limit_hybrid_von_cap2 | SOL · hipóteses (lab) | +50.73 | +489.15 | **+119.01** | -23.84 | 910 | 4/6 | inconclusiva |
| 5 | hybrid_von_relaxed_cap2 | SOL · híbridos | +48.32 | +465.03 | **+92.09** | -24.31 | 945 | 4/6 | inconclusiva |
| 6 | FARTCOIN_rule_regime | Meme · regras | +11.51 | +130.78 | **+72.06** | -12.46 | 140 | 3/6 | inconclusiva |
| 7 | FARTCOIN_rule_donch_regime_full | Meme · regras | +17.03 | +186.02 | **+60.93** | -30.01 | 90 | 2/6 | inconclusiva |
| 8 | BONK_rule_regime | Meme · regras | +2.96 | +371.95 | **+55.82** | -10.79 | 140 | 3/6 | inconclusiva |
| 9 | grid_sol_2pct | SOL · regras | +29.10 | +272.77 | **+36.98** | -22.89 | 20 | 4/6 | inconclusiva |
| 10 | FARTCOIN_laya_relaxed__fork1 | Meme · forks | +5.21 | +67.74 | **+33.69** | -12.36 | 189 | 3/6 | inconclusiva |
| 11 | h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | +41.14 | +393.19 | **+33.28** | -30.48 | 20 | 4/6 | inconclusiva |
| 12 | FARTCOIN_rule_donch_regime | Meme · regras | +5.27 | +68.41 | **+24.59** | -9.56 | 90 | 3/6 | inconclusiva |
| 13 | BONK_rule_donch_regime | Meme · regras | -0.79 | +334.45 | **+8.70** | -10.95 | 96 | 3/6 | inconclusiva |
| 14 | poorjev_baseline | SOL · poorjev | +38.91 | +370.90 | **+7.49** | -31.56 | 20 | 4/6 | inconclusiva |
| 15 | meme_BONK_baseline | Meme · von | +0.00 | +342.31 | **+0.00** | 0.00 | 0 | 3/6 | inconclusiva |

### Vencedores de cada bloco de 30 dias (dentro do run contínuo)

| Mês | Janela | Maior PnL | Maior habilidade | SOL | Memes |
|---|---|---|---|---:|---:|
| 2026-04 | 2026-04-09 → 2026-05-09 | PNUT_poorjev_baseline (+48.97%) | h4_hours_von_relaxed (+28.61 $) | +13.93% | +30.43% |
| 2026-05 | 2026-05-09 → 2026-06-08 | GOAT_rule_donch_regime_full (+1.31%) | FARTCOIN_poorjev_baseline (+241.85 $) | -28.85% | -38.85% |
| 2026-06 | 2026-06-08 → 2026-07-08 | FARTCOIN_poorjev_baseline (+25.84%) | BONK_rule_regime_full (+160.73 $) | +16.30% | +2.96% |
| 2026-07 | 2026-07-08 → 2026-08-07 | FARTCOIN_rule_donch_regime_full (+1.17%) | FARTCOIN_rule_regime_full (+68.05 $) | -5.03% | -12.74% |
| 2026-08 | 2026-08-07 → 2026-09-06 | h1_exits_FARTCOIN_poorjev_relaxed (+55.88%) | h3_limit_hybrid_von_cap2 (+150.08 $) | +44.69% | +34.51% |
| 2026-09 | 2026-09-06 → 2026-10-06 | MEW_poorjev_baseline (+20.31%) | rsi_sol_1h (+61.34 $) | +13.02% | +10.39% |

### Famílias (6 meses)

| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor |
|---|---:|---:|---:|---:|---|
| Meme · forks | 9 | -52.58 | -663.38 | 1/9 | FARTCOIN_laya_relaxed__fork1 |
| Meme · hipóteses (lab) | 14 | -61.83 | -816.87 | 1/14 | h2_ensemble_BONK |
| Meme · híbridos | 7 | +5.51 | -255.82 | 0/7 | WIF_hybrid_poorjev_regime |
| Meme · laya | 14 | +0.00 | +0.00 | 6/14 | GOAT_laya_relaxed |
| Meme · poorjev | 14 | +7.52 | -223.68 | 2/14 | WIF_poorjev_relaxed |
| Meme · regras | 28 | -6.97 | -97.06 | 8/28 | FARTCOIN_rule_regime_full |
| Meme · von | 14 | -10.38 | -106.36 | 4/14 | meme_GOAT_baseline |
| SOL · forks | 6 | -40.93 | -597.14 | 0/6 | relaxed_expcap50__fork1 |
| SOL · hipóteses (lab) | 8 | +33.67 | -33.90 | 6/8 | h4_hours_poorjev_relaxed |
| SOL · híbridos | 1 | +48.32 | +92.09 | 1/1 | hybrid_von_relaxed_cap2 |
| SOL · jev | 3 | +1.82 | -0.67 | 0/3 | jev_article |
| SOL · laya | 2 | +1.82 | -0.67 | 0/2 | laya_relaxed |
| SOL · poorjev | 2 | +38.33 | +1.32 | 2/2 | poorjev_baseline |
| SOL · regras | 2 | +20.47 | +17.02 | 2/2 | grid_sol_2pct |
| SOL · von | 3 | +1.82 | -11.70 | 1/3 | relaxed |

Bot real: livro A +45.73% (vs segurar +22.858 $, 602 trades); livro B -42.53% (vs segurar -22.543 $, 27786 trades).

Consistentes nos meses E com habilidade positiva nos 6 meses: h4_hours_poorjev_relaxed (2/3 meses; 6 meses: hab. +279.96 $, PnL +61.40%), FARTCOIN_rule_regime_full (2/3 meses; 6 meses: hab. +267.64 $, PnL +43.48%), FARTCOIN_rule_regime (2/3 meses; 6 meses: hab. +72.06 $, PnL +11.51%), FARTCOIN_rule_donch_regime_full (2/3 meses; 6 meses: hab. +60.93 $, PnL +17.03%), BONK_rule_regime (2/3 meses; 6 meses: hab. +55.82 $, PnL +2.96%), grid_sol_2pct (3/3 meses; 6 meses: hab. +36.98 $, PnL +29.10%), h3_limit_poorjev_relaxed (2/3 meses; 6 meses: hab. +33.28 $, PnL +41.14%), FARTCOIN_rule_donch_regime (2/3 meses; 6 meses: hab. +24.59 $, PnL +5.27%), poorjev_baseline (2/3 meses; 6 meses: hab. +7.49 $, PnL +38.91%).

## Como ler

- PnL alto num mês de alta das memecoins é quase sempre beta (comprar e segurar); a habilidade separa isso.
- Os runs mensais começam do zero em cada janela; o run de 6 meses é um único caminho contínuo (posições e cooldowns herdados de um mês para o outro), por isso os blocos mensais dele não coincidem com os runs mensais.
- Retroativo com estados e custos aproximados: serve para ordenar hipóteses, não para provar uma vencedora.
