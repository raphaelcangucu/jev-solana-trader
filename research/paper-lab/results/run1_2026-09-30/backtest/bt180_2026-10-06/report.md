# Simulação retroativa de 180 dias — bt180_2026-10-06

**Gerado (BRT):** 2026-10-07T01:27:09-03:00 · **Janela:** 2026-04-09T09:00:00-03:00 → 2026-10-06T09:00:00-03:00 · passo de decisão 60 s · paper only (nenhuma ordem real, nenhuma chave).

## Vencedor

Em 180 dias simulados, a maior habilidade (excesso ajustado à exposição) foi de h4_hours_poorjev_relaxed (+279.96 US$, PnL +61.40%, 20 trades, todas compras: uma entrada concentrada num recuo, não seleção repetida), e o maior PnL foi de h4_hours_poorjev_relaxed (+61.40%, +595.83 US$ contra o buy & hold do mesmo ativo). Nenhum portfólio passa a regra do veredito (bater B&H e a barra USDC com p<0,05 e consistência em ≥4 de 6 meses): 112 inconclusivos e 15 perdedores. Só por falta de round trips (mínimo 30) ficam de fora: h4_hours_poorjev_relaxed (p=0.046, 0 RT, 4/6 meses). É um resultado retroativo com estados e custos aproximados; serve para ordenar hipóteses, não para provar uma vencedora.

- Por habilidade: **h4_hours_poorjev_relaxed** · por PnL: **h4_hours_poorjev_relaxed** · pelo veredito: **nenhum**

## Método

Para cada portfólio do catálogo atual do run ao vivo (originais SOL e memecoins, regras, híbridos, hipóteses H1–H4 e EXP, forks de parâmetros e de critérios, Jev, Laya, poorjev) e para os livros A e B do bot real, o backtest repete 180 dias minuto a minuto com o MESMO código dos bots ao vivo (portões, cooldown, trades/h, fração de compra, teto de exposição, saídas TP/SL/trailing e reentrada, horas, ensemble por percentil, filtro de regime, ordens limite, regras em barras de 1 h), trocando só o relógio, os ficheiros e as cotações (backtest/simenv.py). Os modelos (von, Laya, poorjev; Jev hospedado nos portfólios SOL) respondem a cada estado de 12 adjetivos reconstruído do histórico; cada par (critérios, estado) é chamado uma vez e guardado em cache.

## Pressupostos

- Janela 180 dias até 2026-10-06T09:00:00-03:00 (BRT); decisão a cada 60 s; memecoins em rotação (uma moeda por minuto, cada moeda decide a cada 7 min, como o meme_bot); bot real a cada 15 s.
- Capital: portfólios SOL com US$ 1000 na mistura do config.json (0.039188 em SOL ao preço do início da janela); memecoins com 1000.0 USDT; bot real com 0.017392206 SOL + 50.00929 USDT. Forks e hipóteses começam com o capital da família no início da janela (não com o estado do pai).
- Parâmetros: params.json + registry + overlay do run ao vivo (instantâneo em inputs/, copiado do run bt30_2026-10-06 para manter o MESMO catálogo e os mesmos pressupostos), resolvidos por bot/params.py; nenhuma pausa do dashboard é aplicada.
- Estado: palavras deep/quiet (profundidade/taxas) constantes, como em todas as decisões registadas ao vivo (as marcas Coinbase/Gate.io têm impacto 0). SOL: grelha de 10 s da Binance (ao vivo ~1 marca/10,4 s, sol_bot + rules_bot); memecoins: fecho de 1 m (ao vivo ~1 marca/60 s). Bot real: 16 fechos de 1 m da Binance; spread/profundidade/taxas e inventário (carteira) constantes em tight/deep/quiet/sold, como em >99,9% dos ciclos ao vivo.
- Preços: SOL Coinbase 1 m (fonte da marcação ao vivo); memecoins Bybit/KuCoin 1 m escolhidas pela correlação com a Gate.io (fonte ao vivo, só ~7 dias de 1 m disponíveis). Lacunas ≤ 5 min preenchidas com o último fecho.
- Fills: cotação sintética = marca × (1 ± custo por ativo), com o custo mediano dos fills reais (Jupiter/Raydium) do run ao vivo (os mesmos valores do bt30_2026-10-06) menos o extra de 5 bps que o código soma: SOL 2.4 bps, BONK 1.4 bps, WIF 8.5 bps, POPCAT 12.7 bps, FARTCOIN 5.8 bps, PNUT 32.8 bps, MEW 24.3 bps, GOAT 29.8 bps; taxa de rede 5e-6 SOL. Bot real: 10 bps (paper_cost_bps).
- Ordens limite (H3): enchem quando a mínima (compra) ou máxima (venda) do minuto cruza o limite; saídas TP/SL/trailing avaliadas no fecho de cada minuto (ao vivo: na marca de cada ciclo).
- Regras: barras de 1 h da Coinbase (SOL) e Gate.io (memes), os mesmos fetchers do rules_bot; agem no primeiro passo depois do fecho da barra. Regime de SOL dos híbridos = EMA12 > EMA26 na última barra fechada.
- Modelos: servidores próprios (portas 8865–8867, mesmos venvs/comandos do lab); cada par (critérios, estado) chamado uma vez e guardado em cache; falha → hold (fail-closed). Ensemble H2: janelas de percentil com o mesmo número de decisões que ao vivo (480 SOL / 200 memes), que a 60 s cobrem um período ~4× maior no SOL.
- Veredito: a MESMA regra do run ao vivo (≥30 round trips fechados; bate B&H com p<0,05 por block-bootstrap; PnL acima da barra de 6%/a USDC), com a consistência semanal trocada por mensal: excesso vs B&H positivo em ≥ 4 de 6 blocos de 30 dias contados do fim da janela. Escala: equity gravada e métricas (exposição, habilidade, timing com placebo, bootstrap) numa grelha de 1 h em vez de 5 min — o placebo é O(n²) e a 5 min seriam 51 840 pontos por portfólio; o bootstrap usa blocos de 12 pontos (12 h). O MDD também é medido na grelha de 1 h (pode subestimar quedas intra-hora). As 4 últimas semanas continuam no summary (weeks_*).
- Look-ahead: forks criados a partir de 2026-10-03 usaram dados de 2026-10-01 a 2026-10-06 (fim desta janela).
- Janela longa contínua: um único caminho de 180 dias com o capital inicial no início da janela (posições, cooldowns e janelas do ensemble herdados de mês para mês); chart.json com as curvas normalizadas (1000 = início).
- Jev hospedado: só portfólios SOL; teto de 14640 chamadas.

## Dados

| Ativo | Fonte | Cobertura | Início | Fim | Retorno |
|---|---|---:|---:|---:|---:|
| SOL | coinbase:SOL-USD 1m | 99.83% | 82.18 | 120.32 | +46.41% |
| BONK | bybit:BONKUSDT 1m | 100.00% | 5.755e-06 | 3.785e-06 | -34.23% |
| WIF | kucoin:WIF-USDT 1m | 100.00% | 0.1907 | 0.2532 | +32.77% |
| POPCAT | bybit:POPCATUSDT 1m | 100.00% | 0.05026 | 0.05409 | +7.62% |
| FARTCOIN | kucoin:FARTCOIN-USDT 1m | 100.00% | 0.1785 | 0.1757 | -1.57% |
| PNUT | bybit:PNUTUSDT 1m | 100.00% | 0.04173 | 0.05475 | +31.20% |
| MEW | bybit:MEWUSDT 1m | 100.00% | 0.000571 | 0.0005253 | -8.00% |
| GOAT | bybit:GOATUSDT 1m | 100.00% | 0.01716 | 0.01898 | +10.61% |

## Modelos

| Modelo | Chamadas | Cache | Cobertura | conf P50 | conf P90 |
|---|---:|---:|---:|---:|---:|
| von | 809 | 3368019 | 100.0% | 0.294 | 0.372 |
| laya | 236 | 518005 | 100.0% | 0.034 | 0.064 |
| poorjev | 682 | 592063 | 100.0% | 0.686 | 0.939 |
| jev | 178 | 258805 | 100.0% | 0.920 | 0.960 |

## Top 15 por habilidade (excesso ajustado à exposição)

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Meses > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | h4_hours_poorjev_relaxed | SOL · hipóteses (lab) | +61.40 | +595.83 | **+279.96** | +196.88 (0.21) | -15.75 | 20 (20/0) | 72.7 | 4/6 | inconclusiva |
| 2 | FARTCOIN_rule_regime_full | Meme · regras | +43.48 | +450.47 | **+267.64** | +528.00 (0.06) | -39.09 | 140 (70/70) | 52.9 | 4/6 | inconclusiva |
| 3 | BONK_rule_regime_full | Meme · regras | +3.16 | +373.92 | **+134.14** | +347.76 (0.13) | -34.25 | 140 (70/70) | 52.9 | 4/6 | inconclusiva |
| 4 | h3_limit_hybrid_von_cap2 | SOL · hipóteses (lab) | +50.73 | +489.15 | **+119.01** | +110.86 (0.17) | -23.84 | 910 (864/46) | 84.4 | 4/6 | inconclusiva |
| 5 | hybrid_von_relaxed_cap2 | SOL · híbridos | +48.32 | +465.03 | **+92.09** | +107.60 (0.17) | -24.31 | 945 (898/47) | 85.1 | 4/6 | inconclusiva |
| 6 | FARTCOIN_rule_regime | Meme · regras | +11.51 | +130.78 | **+72.06** | +116.67 (0.09) | -12.46 | 140 (70/70) | 13.6 | 3/6 | inconclusiva |
| 7 | FARTCOIN_rule_donch_regime_full | Meme · regras | +17.03 | +186.02 | **+60.93** | +278.16 (0.21) | -30.01 | 90 (45/45) | 34.6 | 2/6 | inconclusiva |
| 8 | BONK_rule_regime | Meme · regras | +2.96 | +371.95 | **+55.82** | +86.87 (0.12) | -10.79 | 140 (70/70) | 13.5 | 3/6 | inconclusiva |
| 9 | grid_sol_2pct | SOL · regras | +29.10 | +272.77 | **+36.98** | +33.05 (0.39) | -22.89 | 20 (15/5) | 55.2 | 4/6 | inconclusiva |
| 10 | FARTCOIN_laya_relaxed__fork1 ⚠ | Meme · forks | +5.21 | +67.74 | **+33.69** | +99.80 (0.18) | -12.36 | 189 (110/79) | 5.8 | 3/6 | inconclusiva |
| 11 | h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | +41.14 | +393.19 | **+33.28** | +30.14 (0.41) | -30.48 | 20 (20/0) | 82.2 | 4/6 | inconclusiva |
| 12 | FARTCOIN_rule_donch_regime | Meme · regras | +5.27 | +68.41 | **+24.59** | +57.08 (0.25) | -9.56 | 90 (45/45) | 8.9 | 3/6 | inconclusiva |
| 13 | BONK_rule_donch_regime | Meme · regras | -0.79 | +334.45 | **+8.70** | +31.00 (0.31) | -10.95 | 96 (48/48) | 8.5 | 3/6 | inconclusiva |
| 14 | poorjev_baseline | SOL · poorjev | +38.91 | +370.90 | **+7.49** | +11.23 (0.46) | -31.56 | 20 (20/0) | 83.0 | 4/6 | inconclusiva |
| 15 | meme_BONK_baseline | Meme · von | +0.00 | +342.31 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 3/6 | inconclusiva |

## Top 15 por PnL

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Meses > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | h4_hours_poorjev_relaxed | SOL · hipóteses (lab) | +61.40 | +595.83 | **+279.96** | +196.88 (0.21) | -15.75 | 20 (20/0) | 72.7 | 4/6 | inconclusiva |
| 2 | h3_limit_hybrid_von_cap2 | SOL · hipóteses (lab) | +50.73 | +489.15 | **+119.01** | +110.86 (0.17) | -23.84 | 910 (864/46) | 84.4 | 4/6 | inconclusiva |
| 3 | hybrid_von_relaxed_cap2 | SOL · híbridos | +48.32 | +465.03 | **+92.09** | +107.60 (0.17) | -24.31 | 945 (898/47) | 85.1 | 4/6 | inconclusiva |
| 4 | h4_hours_von_relaxed | SOL · hipóteses (lab) | +44.54 | +427.16 | **-7.60** | +36.11 (0.12) | -38.26 | 468 (444/24) | 98.5 | 4/6 | inconclusiva |
| 5 | FARTCOIN_rule_regime_full | Meme · regras | +43.48 | +450.47 | **+267.64** | +528.00 (0.06) | -39.09 | 140 (70/70) | 52.9 | 4/6 | inconclusiva |
| 6 | h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | +41.14 | +393.19 | **+33.28** | +30.14 (0.41) | -30.48 | 20 (20/0) | 82.2 | 4/6 | inconclusiva |
| 7 | poorjev_baseline | SOL · poorjev | +38.91 | +370.90 | **+7.49** | +11.23 (0.46) | -31.56 | 20 (20/0) | 83.0 | 4/6 | inconclusiva |
| 8 | poorjev_relaxed | SOL · poorjev | +37.74 | +359.24 | **-4.84** | +2.93 (0.48) | -32.14 | 20 (20/0) | 83.1 | 4/6 | inconclusiva |
| 9 | WIF_poorjev_baseline | Meme · poorjev | +32.32 | -4.56 | **-191.50** | -4.31 (0.73) | -46.56 | 20 (20/0) | 99.6 | 3/6 | inconclusiva |
| 10 | WIF_poorjev_relaxed | Meme · poorjev | +32.32 | -4.56 | **-191.50** | -4.31 (0.73) | -46.56 | 20 (20/0) | 99.6 | 3/6 | inconclusiva |
| 11 | PNUT_poorjev_baseline | Meme · poorjev | +30.58 | -6.18 | **-223.68** | -3.68 (0.70) | -52.82 | 20 (20/0) | 99.7 | 2/6 | inconclusiva |
| 12 | PNUT_poorjev_relaxed | Meme · poorjev | +30.58 | -6.18 | **-223.68** | -3.68 (0.70) | -52.82 | 20 (20/0) | 99.7 | 2/6 | inconclusiva |
| 13 | relaxed | SOL · von | +29.77 | +279.55 | **-157.54** | -16.35 (0.78) | -40.64 | 1488 (1413/75) | 99.0 | 4/6 | inconclusiva |
| 14 | grid_sol_2pct | SOL · regras | +29.10 | +272.77 | **+36.98** | +33.05 (0.39) | -22.89 | 20 (15/5) | 55.2 | 4/6 | inconclusiva |
| 15 | WIF_hybrid_poorjev_regime | Meme · híbridos | +27.44 | -53.34 | **-239.61** | -44.19 (0.96) | -46.55 | 20 (20/0) | 99.5 | 3/6 | inconclusiva |

⚠ = fork ou hipótese desenhada com dados do run ao vivo que se sobrepõem ao fim desta janela (ver Cuidados).

## Famílias

| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor | Pior |
|---|---:|---:|---:|---:|---|---|
| Meme · forks | 9 | -52.58 | -663.38 | 1/9 | FARTCOIN_laya_relaxed__fork1 | h1_exits_FARTCOIN_poorjev_relaxed__fork1 |
| Meme · hipóteses (lab) | 14 | -61.83 | -816.87 | 1/14 | h2_ensemble_BONK | h2_ensemble_GOAT |
| Meme · híbridos | 7 | +5.51 | -255.82 | 0/7 | WIF_hybrid_poorjev_regime | BONK_hybrid_poorjev_regime |
| Meme · laya | 14 | +0.00 | +0.00 | 6/14 | GOAT_laya_relaxed | BONK_laya_baseline |
| Meme · poorjev | 14 | +7.52 | -223.68 | 2/14 | WIF_poorjev_relaxed | BONK_poorjev_baseline |
| Meme · regras | 28 | -6.97 | -97.06 | 8/28 | FARTCOIN_rule_regime_full | MEW_rule_donch_regime_full |
| Meme · von | 14 | -10.38 | -106.36 | 4/14 | meme_GOAT_baseline | meme_PNUT_relaxed |
| SOL · forks | 6 | -40.93 | -597.14 | 0/6 | relaxed_expcap50__fork1 | laya_relaxed__fork1 |
| SOL · hipóteses (lab) | 8 | +33.67 | -33.90 | 6/8 | h4_hours_poorjev_relaxed | h1_exits_von_relaxed |
| SOL · híbridos | 1 | +48.32 | +92.09 | 1/1 | hybrid_von_relaxed_cap2 | hybrid_von_relaxed_cap2 |
| SOL · jev | 3 | +1.82 | -0.67 | 0/3 | jev_article | jev_baseline |
| SOL · laya | 2 | +1.82 | -0.67 | 0/2 | laya_relaxed | laya_baseline |
| SOL · poorjev | 2 | +38.33 | +1.32 | 2/2 | poorjev_baseline | poorjev_relaxed |
| SOL · regras | 2 | +20.47 | +17.02 | 2/2 | grid_sol_2pct | rsi_sol_1h |
| SOL · von | 3 | +1.82 | -11.70 | 1/3 | relaxed | v2 |

## Bot real: livro A × livro B

| Livro | Perfil | Valor ini. | Valor fim | PnL $ | PnL % | vs segurar $ | Acerto 15 min | MDD % | Trades | Saídas |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A | relaxed_paper | 51.4386 | 74.9600 | +23.5214 | +45.73% | +22.8579 | 49.8% | -38.09 | 602 | – |
| B | relaxed_exits_paper | 51.4386 | 29.5595 | -21.8791 | -42.53% | -22.5426 | 49.5% | -44.84 | 27786 | trail:215, sl:235, tp:75 |

## Validação contra o run ao vivo

Período comum: 2026-10-01T22:24:00-03:00 → 2026-10-06T09:00:00-03:00. Palavras de mercado do estado reconstruído × registadas ao vivo no mesmo instante (portfólio dono do estado):

| Ativo | Decisões | Estado de mercado igual | move | vol | color | rng |
|---|---:|---:|---:|---:|---:|---:|
| SOL | 26235 | 69.6% | 89.2% | 99.9% | 93.0% | 83.0% |
| BONK | 947 | 39.6% | 65.0% | 81.4% | 87.9% | 87.0% |
| WIF | 947 | 46.7% | 69.4% | 80.6% | 91.8% | 89.8% |
| POPCAT | 946 | 18.1% | 40.6% | 68.5% | 78.0% | 73.2% |
| FARTCOIN | 944 | 33.6% | 57.3% | 75.7% | 87.9% | 84.2% |
| PNUT | 946 | 14.7% | 38.5% | 74.0% | 69.2% | 68.8% |
| MEW | 946 | 42.3% | 62.1% | 84.6% | 88.6% | 83.1% |
| GOAT | 944 | 20.4% | 43.9% | 71.4% | 75.8% | 72.5% |

Respostas dos modelos do backtest × ao vivo para os mesmos estados (critérios baseline):

| Modelo | Estados ao vivo | Comparados | Mesma ação | Confiança ±0,01 |
|---|---:|---:|---:|---:|
| von | 148 | 148 | 100.0% | 100.0% |
| laya | 148 | 148 | 100.0% | 100.0% |
| poorjev | 148 | 148 | 100.0% | 100.0% |
| jev | 105 | 105 | 100.0% | 20.9% |

Trades no período comum (ao vivo × simulado; posições iniciais diferentes, só ordem de grandeza): h1_exits_FARTCOIN_poorjev_relaxed__fork1 286×254, laya_relaxed__fork1 235×275, h1_exits_von_relaxed 162×126, h1_exits_FARTCOIN_poorjev_relaxed 146×126, h1_exits_WIF_poorjev_relaxed 146×109, h1_exits_BONK_poorjev_relaxed 150×90, poorjev_relaxed__fork1 82×126, h2_ensemble_sol 144×53, h1_exits_POPCAT_poorjev_relaxed 83×90, h2_ensemble_FARTCOIN 60×97, h1_exits_GOAT_poorjev_relaxed 83×69, h1_exits_MEW_poorjev_relaxed 104×47, h1_exits_WIF_poorjev_relaxed__fork1 42×108, h1_exits_hybrid_von_cap2 75×72, h2_ensemble_BONK 77×64, h2_ensemble_WIF 68×57, h1_exits_BONK_poorjev_relaxed__fork1 38×83, h1_exits_PNUT_poorjev_relaxed 70×48, h2_ensemble_FARTCOIN__fork1 31×72, h1_exits_von_relaxed__fork1 34×65, h1_exits_WIF_poorjev_relaxed__fork2 4×92, h2_ensemble_POPCAT 45×38, h2_ensemble_WIF__fork1 30×48, meme_PNUT_relaxed 23×53, h2_ensemble_GOAT 44×29

## Vereditos

- vencedoras: 0, perdedoras: 15, inconclusivas: 112.
- Regra: a do run ao vivo (`bot/analytics.verdict`), com a janela de 180 dias a cumprir os dias mínimos; continua a exigir ≥ 30 round trips fechados. Consistência mensal em vez de semanal: excesso vs B&H positivo em ≥ 4 de 6 blocos de 30 dias; séries e bootstrap em grelha de 1 h (blocos de 12 h).

## Cuidados

- **Look-ahead / sobreajuste:** os forks (e os textos de critérios dos forks de critérios) foram desenhados pela revisão noturna com os dias 1–5 do run ao vivo (2026-10-01 → 2026-10-06), que estão dentro desta janela. O resultado deles nessa parte é dentro da amostra; compare-os sobretudo no período anterior (colunas de semanas/meses no summary.json). Portfólios afetados marcados com ⚠.
- Os parâmetros do relaxed (conf ≥ 0,35, margem ≥ 0,20) foram calibrados nas primeiras decisões do von no início de setembro de 2026 e o v2 usa critérios reescritos em 2026-09-24; janelas que incluem esses dias têm essa parte dentro da amostra.
- Estados: SOL a partir de uma grelha de 10 s da Binance (o histórico ao vivo tem ~1 marca a cada 10,4 s); memecoins a partir de fechos de 1 m; palavras de profundidade/taxas constantes (como ao vivo). Pequenas diferenças de amostragem mudam algumas palavras de movimento/volatilidade.
- Fills: cotação sintética = marca do minuto ± custo mediano por ativo medido nos fills reais do run ao vivo; as variantes `_full` (100% do saldo) podem ter mais impacto do que o estimado.
- Decisão a cada 60 s (ao vivo: SOL a cada ~15 s, memecoins a cada ~7 min por moeda, lab a cada 15 s); o bot real a cada 15 s.
