# Simulação retroativa de 31 dias — bt30_2026-09-06

**Gerado (BRT):** 2026-10-07T00:42:21-03:00 · **Janela:** 2026-08-06T09:00:00-03:00 → 2026-09-06T09:00:00-03:00 · passo de decisão 60 s · paper only (nenhuma ordem real, nenhuma chave).

## Vencedor

Em 31 dias simulados, a maior habilidade (excesso ajustado à exposição) foi de h3_limit_hybrid_von_cap2 (+155.88 US$, PnL +49.68%, 230 trades), e o maior PnL foi de h1_exits_FARTCOIN_poorjev_relaxed (+55.94%, +137.83 US$ contra o buy & hold do mesmo ativo). Nenhum portfólio passa a regra do veredito (bater B&H e a barra USDC com p<0,05 e consistência em ≥3 de 4 semanas): 120 inconclusivos e 7 perdedores. Só por falta de round trips (mínimo 30) ficam de fora: relaxed (p=0.023, 14 RT, 3/4 semanas), hybrid_von_relaxed_cap2 (p=0.013, 10 RT, 3/4 semanas), grid_sol_2pct (p=0.035, 5 RT, 4/4 semanas), h2_ensemble_sol (p=0.011, 15 RT, 3/4 semanas). É um resultado retroativo com estados e custos aproximados; serve para ordenar hipóteses, não para provar uma vencedora.

- Por habilidade: **h3_limit_hybrid_von_cap2** · por PnL: **h1_exits_FARTCOIN_poorjev_relaxed** · pelo veredito: **nenhum**

## Método

Para cada portfólio do catálogo atual do run ao vivo (originais SOL e memecoins, regras, híbridos, hipóteses H1–H4 e EXP, forks de parâmetros e de critérios, Jev, Laya, poorjev) e para os livros A e B do bot real, o backtest repete 31 dias minuto a minuto com o MESMO código dos bots ao vivo (portões, cooldown, trades/h, fração de compra, teto de exposição, saídas TP/SL/trailing e reentrada, horas, ensemble por percentil, filtro de regime, ordens limite, regras em barras de 1 h), trocando só o relógio, os ficheiros e as cotações (backtest/simenv.py). Os modelos (von, Laya, poorjev; Jev hospedado nos portfólios SOL) respondem a cada estado de 12 adjetivos reconstruído do histórico; cada par (critérios, estado) é chamado uma vez e guardado em cache.

## Pressupostos

- Janela 31 dias até 2026-09-06T09:00:00-03:00 (BRT); decisão a cada 60 s; memecoins em rotação (uma moeda por minuto, cada moeda decide a cada 7 min, como o meme_bot); bot real a cada 15 s.
- Capital: portfólios SOL com US$ 1000 na mistura do config.json (0.039188 em SOL ao preço do início da janela); memecoins com 1000.0 USDT; bot real com 0.017392206 SOL + 50.00929 USDT. Forks e hipóteses começam com o capital da família no início da janela (não com o estado do pai).
- Parâmetros: params.json + registry + overlay do run ao vivo (instantâneo em inputs/, copiado do run bt30_2026-10-06 para manter o MESMO catálogo e os mesmos pressupostos), resolvidos por bot/params.py; nenhuma pausa do dashboard é aplicada.
- Estado: palavras deep/quiet (profundidade/taxas) constantes, como em todas as decisões registadas ao vivo (as marcas Coinbase/Gate.io têm impacto 0). SOL: grelha de 10 s da Binance (ao vivo ~1 marca/10,4 s, sol_bot + rules_bot); memecoins: fecho de 1 m (ao vivo ~1 marca/60 s). Bot real: 16 fechos de 1 m da Binance; spread/profundidade/taxas e inventário (carteira) constantes em tight/deep/quiet/sold, como em >99,9% dos ciclos ao vivo.
- Preços: SOL Coinbase 1 m (fonte da marcação ao vivo); memecoins Bybit/KuCoin 1 m escolhidas pela correlação com a Gate.io (fonte ao vivo, só ~7 dias de 1 m disponíveis). Lacunas ≤ 5 min preenchidas com o último fecho.
- Fills: cotação sintética = marca × (1 ± custo por ativo), com o custo mediano dos fills reais (Jupiter/Raydium) do run ao vivo (os mesmos valores do bt30_2026-10-06) menos o extra de 5 bps que o código soma: SOL 2.4 bps, BONK 1.4 bps, WIF 8.5 bps, POPCAT 12.7 bps, FARTCOIN 5.8 bps, PNUT 32.8 bps, MEW 24.3 bps, GOAT 29.8 bps; taxa de rede 5e-6 SOL. Bot real: 10 bps (paper_cost_bps).
- Ordens limite (H3): enchem quando a mínima (compra) ou máxima (venda) do minuto cruza o limite; saídas TP/SL/trailing avaliadas no fecho de cada minuto (ao vivo: na marca de cada ciclo).
- Regras: barras de 1 h da Coinbase (SOL) e Gate.io (memes), os mesmos fetchers do rules_bot; agem no primeiro passo depois do fecho da barra. Regime de SOL dos híbridos = EMA12 > EMA26 na última barra fechada.
- Modelos: servidores próprios (portas 8865–8867, mesmos venvs/comandos do lab); cada par (critérios, estado) chamado uma vez e guardado em cache; falha → hold (fail-closed). Ensemble H2: janelas de percentil com o mesmo número de decisões que ao vivo (480 SOL / 200 memes), que a 60 s cobrem um período ~4× maior no SOL.
- Veredito: regra do run ao vivo (≥30 round trips fechados; dias cumpridos pela janela; bate B&H com p<0,05 por block-bootstrap, PnL acima da barra de 6%/a USDC, excesso positivo em ≥3 de 4 semanas). Semanas = 4 blocos de 7 dias contados do fim da janela.
- Sem look-ahead: a janela acaba antes de 2026-10-01; os forks (desenhados com 2026-10-01 → 2026-10-06) estão fora da amostra.
- Jev hospedado: só portfólios SOL; teto de 14996 chamadas.

## Dados

| Ativo | Fonte | Cobertura | Início | Fim | Retorno |
|---|---|---:|---:|---:|---:|
| SOL | coinbase:SOL-USD 1m | 100.00% | 73.38 | 106.46 | +45.08% |
| BONK | bybit:BONKUSDT 1m | 100.00% | 2.78e-06 | 3.308e-06 | +18.99% |
| WIF | kucoin:WIF-USDT 1m | 100.00% | 0.1393 | 0.2163 | +55.28% |
| POPCAT | bybit:POPCATUSDT 1m | 100.00% | 0.04351 | 0.05335 | +22.62% |
| FARTCOIN | kucoin:FARTCOIN-USDT 1m | 100.00% | 0.13 | 0.1848 | +42.15% |
| PNUT | bybit:PNUTUSDT 1m | 100.00% | 0.03892 | 0.05101 | +31.06% |
| MEW | bybit:MEWUSDT 1m | 100.00% | 0.0003291 | 0.0004363 | +32.57% |
| GOAT | bybit:GOATUSDT 1m | 100.00% | 0.01315 | 0.01621 | +23.27% |

## Modelos

| Modelo | Chamadas | Cache | Cobertura | conf P50 | conf P90 |
|---|---:|---:|---:|---:|---:|
| von | 1076 | 580302 | 100.0% | 0.294 | 0.372 |
| laya | 52 | 89280 | 100.0% | 0.034 | 0.065 |
| poorjev | 52 | 102036 | 100.0% | 0.683 | 0.939 |
| jev | 356 | 44640 | 100.0% | 0.920 | 0.960 |

## Top 15 por habilidade (excesso ajustado à exposição)

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Semanas > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | h3_limit_hybrid_von_cap2 | SOL · hipóteses (lab) | +49.68 | +479.15 | **+155.88** | +89.73 (0.04) | -10.36 | 230 (220/10) | 87.5 | 3/4 | inconclusiva |
| 2 | h1_exits_FARTCOIN_poorjev_relaxed | Meme · hipóteses (lab) | +55.94 | +137.83 | **+153.37** | +215.72 (0.01) | -36.00 | 1278 (1217/61) | 92.3 | 1/4 | inconclusiva |
| 3 | hybrid_von_relaxed_cap2 | SOL · híbridos | +49.58 | +478.10 | **+151.33** | +86.14 (0.04) | -10.36 | 231 (221/10) | 88.4 | 3/4 | inconclusiva |
| 4 | h2_ensemble_sol | SOL · hipóteses (lab) | +50.90 | +491.33 | **+138.86** | +79.08 (0.01) | -10.36 | 291 (276/15) | 95.0 | 3/4 | inconclusiva |
| 5 | BONK_hybrid_poorjev_regime | Meme · híbridos | +34.01 | +150.18 | **+121.90** | +124.39 (0.01) | -24.32 | 20 (20/0) | 96.3 | 2/4 | inconclusiva |
| 6 | h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | +33.46 | +316.90 | **+92.54** | +61.68 (0.34) | -11.33 | 20 (20/0) | 62.1 | 3/4 | inconclusiva |
| 7 | poorjev_baseline | SOL · poorjev | +33.36 | +315.98 | **+91.56** | +61.17 (0.35) | -11.33 | 20 (20/0) | 62.1 | 3/4 | inconclusiva |
| 8 | poorjev_relaxed | SOL · poorjev | +33.36 | +315.98 | **+91.56** | +61.17 (0.35) | -11.33 | 20 (20/0) | 62.1 | 3/4 | inconclusiva |
| 9 | WIF_hybrid_poorjev_regime | Meme · híbridos | +55.42 | +1.44 | **+87.46** | +19.54 (0.37) | -20.30 | 20 (20/0) | 96.3 | 1/4 | inconclusiva |
| 10 | h4_hours_poorjev_relaxed | SOL · hipóteses (lab) | +32.36 | +305.95 | **+85.29** | +56.63 (0.37) | -11.31 | 20 (20/0) | 61.2 | 3/4 | inconclusiva |
| 11 | FARTCOIN_rule_donch_regime_full | Meme · regras | +20.78 | -213.69 | **+71.81** | +114.42 (0.22) | -29.17 | 15 (8/7) | 30.9 | 1/4 | inconclusiva |
| 12 | h4_hours_von_relaxed | SOL · hipóteses (lab) | +45.34 | +435.77 | **+66.28** | +5.53 (0.19) | -11.33 | 42 (41/1) | 99.4 | 3/4 | inconclusiva |
| 13 | WIF_poorjev_baseline | Meme · poorjev | +54.91 | -3.63 | **+66.11** | +0.01 (0.52) | -20.30 | 20 (20/0) | 99.7 | 1/4 | inconclusiva |
| 14 | WIF_poorjev_relaxed | Meme · poorjev | +54.91 | -3.63 | **+66.11** | +0.01 (0.52) | -20.30 | 20 (20/0) | 99.7 | 1/4 | inconclusiva |
| 15 | relaxed | SOL · von | +44.69 | +429.23 | **+61.77** | +30.90 (0.01) | -10.96 | 318 (304/14) | 98.9 | 3/4 | inconclusiva |

## Top 15 por PnL

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Semanas > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | h1_exits_FARTCOIN_poorjev_relaxed | Meme · hipóteses (lab) | +55.94 | +137.83 | **+153.37** | +215.72 (0.01) | -36.00 | 1278 (1217/61) | 92.3 | 1/4 | inconclusiva |
| 2 | WIF_hybrid_poorjev_regime | Meme · híbridos | +55.42 | +1.44 | **+87.46** | +19.54 (0.37) | -20.30 | 20 (20/0) | 96.3 | 1/4 | inconclusiva |
| 3 | WIF_poorjev_baseline | Meme · poorjev | +54.91 | -3.63 | **+66.11** | +0.01 (0.52) | -20.30 | 20 (20/0) | 99.7 | 1/4 | inconclusiva |
| 4 | WIF_poorjev_relaxed | Meme · poorjev | +54.91 | -3.63 | **+66.11** | +0.01 (0.52) | -20.30 | 20 (20/0) | 99.7 | 1/4 | inconclusiva |
| 5 | h2_ensemble_sol | SOL · hipóteses (lab) | +50.90 | +491.33 | **+138.86** | +79.08 (0.01) | -10.36 | 291 (276/15) | 95.0 | 3/4 | inconclusiva |
| 6 | h3_limit_hybrid_von_cap2 | SOL · hipóteses (lab) | +49.68 | +479.15 | **+155.88** | +89.73 (0.04) | -10.36 | 230 (220/10) | 87.5 | 3/4 | inconclusiva |
| 7 | hybrid_von_relaxed_cap2 | SOL · híbridos | +49.58 | +478.10 | **+151.33** | +86.14 (0.04) | -10.36 | 231 (221/10) | 88.4 | 3/4 | inconclusiva |
| 8 | h4_hours_von_relaxed | SOL · hipóteses (lab) | +45.34 | +435.77 | **+66.28** | +5.53 (0.19) | -11.33 | 42 (41/1) | 99.4 | 3/4 | inconclusiva |
| 9 | relaxed | SOL · von | +44.69 | +429.23 | **+61.77** | +30.90 (0.01) | -10.96 | 318 (304/14) | 98.9 | 3/4 | inconclusiva |
| 10 | FARTCOIN_hybrid_poorjev_regime | Meme · híbridos | +43.92 | +17.65 | **+15.26** | +27.98 (0.29) | -30.04 | 20 (20/0) | 96.3 | 3/4 | inconclusiva |
| 11 | FARTCOIN_poorjev_baseline | Meme · poorjev | +41.92 | -2.32 | **-19.42** | +0.31 (0.47) | -30.04 | 20 (20/0) | 99.7 | 1/4 | inconclusiva |
| 12 | FARTCOIN_poorjev_relaxed | Meme · poorjev | +41.92 | -2.32 | **-19.42** | +0.31 (0.47) | -30.04 | 20 (20/0) | 99.7 | 1/4 | inconclusiva |
| 13 | BONK_hybrid_poorjev_regime | Meme · híbridos | +34.01 | +150.18 | **+121.90** | +124.39 (0.01) | -24.32 | 20 (20/0) | 96.3 | 2/4 | inconclusiva |
| 14 | h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | +33.46 | +316.90 | **+92.54** | +61.68 (0.34) | -11.33 | 20 (20/0) | 62.1 | 3/4 | inconclusiva |
| 15 | poorjev_baseline | SOL · poorjev | +33.36 | +315.98 | **+91.56** | +61.17 (0.35) | -11.33 | 20 (20/0) | 62.1 | 3/4 | inconclusiva |

⚠ = fork ou hipótese desenhada com dados do run ao vivo que se sobrepõem ao fim desta janela (ver Cuidados).

## Famílias

| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor | Pior |
|---|---:|---:|---:|---:|---|---|
| Meme · forks | 9 | +6.25 | -133.30 | 0/9 | h1_exits_WIF_poorjev_relaxed__fork1 | h1_exits_FARTCOIN_poorjev_relaxed__fork1 |
| Meme · hipóteses (lab) | 14 | +0.01 | -206.62 | 1/14 | h1_exits_FARTCOIN_poorjev_relaxed | h2_ensemble_PNUT |
| Meme · híbridos | 7 | +33.36 | +15.26 | 5/7 | WIF_hybrid_poorjev_regime | GOAT_hybrid_poorjev_regime |
| Meme · laya | 14 | +0.00 | +0.00 | 0/14 | GOAT_laya_relaxed | BONK_laya_baseline |
| Meme · poorjev | 14 | +30.51 | -19.42 | 2/14 | WIF_poorjev_relaxed | BONK_poorjev_baseline |
| Meme · regras | 28 | +3.08 | -30.80 | 0/28 | WIF_rule_donch_regime_full | PNUT_rule_donch_regime_full |
| Meme · von | 14 | -1.23 | -16.28 | 0/14 | meme_GOAT_baseline | meme_GOAT_relaxed |
| SOL · forks | 6 | +4.25 | -140.59 | 4/6 | laya_relaxed__fork2 | laya_relaxed__fork1 |
| SOL · hipóteses (lab) | 8 | +32.91 | +75.78 | 8/8 | h2_ensemble_sol | h1_exits_hybrid_von_cap2 |
| SOL · híbridos | 1 | +49.58 | +151.33 | 1/1 | hybrid_von_relaxed_cap2 | hybrid_von_relaxed_cap2 |
| SOL · jev | 3 | +1.77 | -0.73 | 0/3 | jev_article | jev_baseline |
| SOL · laya | 2 | +1.77 | -0.73 | 0/2 | laya_relaxed | laya_baseline |
| SOL · poorjev | 2 | +33.36 | +91.56 | 2/2 | poorjev_relaxed | poorjev_baseline |
| SOL · regras | 2 | +7.41 | +4.42 | 2/2 | grid_sol_2pct | rsi_sol_1h |
| SOL · von | 3 | +1.77 | -0.73 | 1/3 | relaxed | v2 |

## Bot real: livro A × livro B

| Livro | Perfil | Valor ini. | Valor fim | PnL $ | PnL % | vs segurar $ | Acerto 15 min | MDD % | Trades | Saídas |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A | relaxed_paper | 51.2869 | 74.4603 | +23.1734 | +45.18% | +22.5993 | 55.0% | -11.25 | 218 | – |
| B | relaxed_exits_paper | 51.2869 | 51.4584 | +0.1715 | +0.33% | -0.4026 | 47.6% | -9.44 | 6164 | trail:33, tp:19, sl:36 |

## Vereditos

- vencedoras: 0, perdedoras: 7, inconclusivas: 120.
- Regra: a do run ao vivo (`bot/analytics.verdict`), com a janela de 31 dias a cumprir os dias mínimos; continua a exigir ≥ 30 round trips fechados.

## Cuidados

- **Sem look-ahead nos forks:** esta janela acaba antes de 2026-10-01; os forks desenhados pela revisão noturna com os dias 2026-10-01 → 2026-10-06 estão aqui totalmente fora da amostra.
- Os parâmetros do relaxed (conf ≥ 0,35, margem ≥ 0,20) foram calibrados nas primeiras decisões do von no início de setembro de 2026 e o v2 usa critérios reescritos em 2026-09-24; janelas que incluem esses dias têm essa parte dentro da amostra.
- Estados: SOL a partir de uma grelha de 10 s da Binance (o histórico ao vivo tem ~1 marca a cada 10,4 s); memecoins a partir de fechos de 1 m; palavras de profundidade/taxas constantes (como ao vivo). Pequenas diferenças de amostragem mudam algumas palavras de movimento/volatilidade.
- Fills: cotação sintética = marca do minuto ± custo mediano por ativo medido nos fills reais do run ao vivo; as variantes `_full` (100% do saldo) podem ter mais impacto do que o estimado.
- Decisão a cada 60 s (ao vivo: SOL a cada ~15 s, memecoins a cada ~7 min por moeda, lab a cada 15 s); o bot real a cada 15 s.
