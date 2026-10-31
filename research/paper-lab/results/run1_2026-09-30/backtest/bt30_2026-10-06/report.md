# Simulação retroativa de 30 dias — bt30_2026-10-06

**Gerado (BRT):** 2026-10-06T15:54:06-03:00 · **Janela:** 2026-09-06T09:00:00-03:00 → 2026-10-06T09:00:00-03:00 · passo de decisão 60 s · paper only (nenhuma ordem real, nenhuma chave).

## Vencedor

Em 30 dias simulados, a maior habilidade (excesso ajustado à exposição) foi de poorjev_baseline (+83.96 US$, PnL +19.21%, 20 trades, todas compras: uma entrada concentrada num recuo, não seleção repetida), e o maior PnL foi de MEW_poorjev_baseline (+20.01%, -3.90 US$ contra o buy & hold do mesmo ativo). Nenhum portfólio passa a regra do veredito (bater B&H e a barra USDC com p<0,05 e consistência em ≥3 de 4 semanas): 117 inconclusivos e 10 perdedores. Só por falta de round trips (mínimo 30) ficam de fora: rsi_sol_1h (p=0.042, 6 RT, 4/4 semanas). É um resultado retroativo com estados e custos aproximados; serve para ordenar hipóteses, não para provar uma vencedora.

- Por habilidade: **poorjev_baseline** · por PnL: **MEW_poorjev_baseline** · pelo veredito: **nenhum**

## Método

Para cada portfólio do catálogo atual do run ao vivo (originais SOL e memecoins, regras, híbridos, hipóteses H1–H4 e EXP, forks de parâmetros e de critérios, Jev, Laya, poorjev) e para os livros A e B do bot real, o backtest repete os últimos 30 dias minuto a minuto com o MESMO código dos bots ao vivo (portões, cooldown, trades/h, fração de compra, teto de exposição, saídas TP/SL/trailing e reentrada, horas, ensemble por percentil, filtro de regime, ordens limite, regras em barras de 1 h), trocando só o relógio, os ficheiros e as cotações (backtest/simenv.py). Os modelos (von, Laya, poorjev; Jev hospedado nos portfólios SOL) respondem a cada estado de 12 adjetivos reconstruído do histórico; cada par (critérios, estado) é chamado uma vez e guardado em cache.

## Pressupostos

- Janela 30 dias até 2026-10-06T09:00:00-03:00 (BRT); decisão a cada 60 s; memecoins em rotação (uma moeda por minuto, cada moeda decide a cada 7 min, como o meme_bot); bot real a cada 15 s.
- Capital: portfólios SOL com US$ 1000 na mistura do config.json (0.039188 em SOL ao preço do início da janela); memecoins com 1000.0 USDT; bot real com 0.017392206 SOL + 50.00929 USDT. Forks e hipóteses começam com o capital da família no início da janela (não com o estado do pai).
- Parâmetros: params.json + registry + overlay do run ao vivo (instantâneo em inputs/), resolvidos por bot/params.py; nenhuma pausa do dashboard é aplicada.
- Estado: palavras deep/quiet (profundidade/taxas) constantes, como em todas as decisões registadas ao vivo (as marcas Coinbase/Gate.io têm impacto 0). SOL: grelha de 10 s da Binance (ao vivo ~1 marca/10,4 s, sol_bot + rules_bot); memecoins: fecho de 1 m (ao vivo ~1 marca/60 s). Bot real: 16 fechos de 1 m da Binance; spread/profundidade/taxas e inventário (carteira) constantes em tight/deep/quiet/sold, como em >99,9% dos ciclos ao vivo.
- Preços: SOL Coinbase 1 m (fonte da marcação ao vivo); memecoins Bybit/KuCoin 1 m escolhidas pela correlação com a Gate.io (fonte ao vivo, só ~7 dias de 1 m disponíveis). Lacunas ≤ 5 min preenchidas com o último fecho.
- Fills: cotação sintética = marca × (1 ± custo por ativo), com o custo mediano dos fills reais (Jupiter/Raydium) do run ao vivo menos o extra de 5 bps que o código soma: SOL 2.4 bps, BONK 1.4 bps, WIF 8.5 bps, POPCAT 12.7 bps, FARTCOIN 5.8 bps, PNUT 32.8 bps, MEW 24.3 bps, GOAT 29.8 bps; taxa de rede 5e-6 SOL. Bot real: 10 bps (paper_cost_bps).
- Ordens limite (H3): enchem quando a mínima (compra) ou máxima (venda) do minuto cruza o limite; saídas TP/SL/trailing avaliadas no fecho de cada minuto (ao vivo: na marca de cada ciclo).
- Regras: barras de 1 h da Coinbase (SOL) e Gate.io (memes), os mesmos fetchers do rules_bot; agem no primeiro passo depois do fecho da barra. Regime de SOL dos híbridos = EMA12 > EMA26 na última barra fechada.
- Modelos: servidores próprios (portas 8865–8867, mesmos venvs/comandos do lab); cada par (critérios, estado) chamado uma vez e guardado em cache; falha → hold (fail-closed). Ensemble H2: janelas de percentil com o mesmo número de decisões que ao vivo (480 SOL / 200 memes), que a 60 s cobrem um período ~4× maior no SOL.
- Veredito: regra do run ao vivo (≥30 round trips fechados; dias cumpridos pela janela; bate B&H com p<0,05 por block-bootstrap, PnL acima da barra de 6%/a USDC, excesso positivo em ≥3 de 4 semanas). Semanas = 4 blocos de 7 dias contados do fim da janela.
- Look-ahead: forks criados a partir de 2026-10-03 usaram dados de 2026-10-01 a 2026-10-06 (fim desta janela).
- Jev hospedado: só portfólios SOL; teto de 20000 chamadas.

## Dados

| Ativo | Fonte | Cobertura | Início | Fim | Retorno |
|---|---|---:|---:|---:|---:|
| SOL | coinbase:SOL-USD 1m | 100.00% | 106.46 | 120.32 | +13.02% |
| BONK | bybit:BONKUSDT 1m | 100.00% | 3.308e-06 | 3.785e-06 | +14.42% |
| WIF | kucoin:WIF-USDT 1m | 100.00% | 0.2163 | 0.2532 | +17.06% |
| POPCAT | bybit:POPCATUSDT 1m | 100.00% | 0.05335 | 0.05409 | +1.39% |
| FARTCOIN | kucoin:FARTCOIN-USDT 1m | 100.00% | 0.1848 | 0.1757 | -4.92% |
| PNUT | bybit:PNUTUSDT 1m | 100.00% | 0.05101 | 0.05475 | +7.33% |
| MEW | bybit:MEWUSDT 1m | 100.00% | 0.0004363 | 0.0005253 | +20.40% |
| GOAT | bybit:GOATUSDT 1m | 100.00% | 0.01621 | 0.01898 | +17.09% |

## Modelos

| Modelo | Chamadas | Cache | Cobertura | conf P50 | conf P90 |
|---|---:|---:|---:|---:|---:|
| von | 18 | 561582 | 100.0% | 0.294 | 0.372 |
| laya | 0 | 86400 | 100.0% | 0.035 | 0.065 |
| poorjev | 0 | 98744 | 100.0% | 0.692 | 0.940 |
| jev | 0 | 43200 | 100.0% | 0.900 | 0.960 |

## Top 15 por habilidade (excesso ajustado à exposição)

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Semanas > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | poorjev_baseline | SOL · poorjev | +19.21 | +186.99 | **+83.96** | +75.03 (0.02) | -7.09 | 20 (20/0) | 79.2 | 4/4 | inconclusiva |
| 2 | poorjev_relaxed | SOL · poorjev | +19.21 | +186.99 | **+83.96** | +75.03 (0.02) | -7.09 | 20 (20/0) | 79.2 | 4/4 | inconclusiva |
| 3 | h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | +18.59 | +180.77 | **+81.46** | +71.13 (0.06) | -6.49 | 18 (18/0) | 76.4 | 4/4 | inconclusiva |
| 4 | GOAT_rule_donch_regime_full | Meme · regras | +14.04 | -30.50 | **+78.67** | +129.79 (0.13) | -18.37 | 12 (6/6) | 30.6 | 2/4 | inconclusiva |
| 5 | rsi_sol_1h | SOL · regras | +7.69 | +71.84 | **+56.33** | +57.55 (0.04) | -2.12 | 15 (9/6) | 15.1 | 4/4 | inconclusiva |
| 6 | grid_sol_2pct | SOL · regras | +10.58 | +100.71 | **+51.07** | +50.71 (0.08) | -5.43 | 9 (7/2) | 40.1 | 3/4 | inconclusiva |
| 7 | FARTCOIN_rule_regime_full | Meme · regras | +4.35 | +92.73 | **+30.58** | +96.17 (0.26) | -20.34 | 24 (12/12) | 53.7 | 2/4 | inconclusiva |
| 8 | h4_hours_poorjev_relaxed | SOL · hipóteses (lab) | +10.69 | +101.79 | **+21.50** | +23.20 (0.44) | -6.23 | 10 (10/0) | 62.5 | 3/4 | inconclusiva |
| 9 | GOAT_rule_donch_regime | Meme · regras | +3.64 | -134.45 | **+20.64** | +31.79 (0.14) | -5.09 | 12 (6/6) | 7.8 | 2/4 | inconclusiva |
| 10 | FARTCOIN_rule_regime | Meme · regras | +1.64 | +65.64 | **+13.06** | +22.26 (0.29) | -5.89 | 24 (12/12) | 13.9 | 3/4 | inconclusiva |
| 11 | GOAT_rule_regime | Meme · regras | +3.12 | -139.65 | **+3.59** | +25.86 (0.17) | -6.24 | 24 (12/12) | 13.7 | 1/4 | inconclusiva |
| 12 | GOAT_rule_regime_full | Meme · regras | +11.13 | -59.62 | **+2.70** | +106.80 (0.16) | -22.12 | 24 (12/12) | 53.7 | 2/4 | inconclusiva |
| 13 | POPCAT_rule_donch_regime | Meme · regras | +0.74 | -6.43 | **+2.03** | +11.21 (0.30) | -5.70 | 18 (9/9) | 9.8 | 2/4 | inconclusiva |
| 14 | BONK_rule_regime | Meme · regras | +2.79 | -116.33 | **+1.30** | +7.37 (0.42) | -7.32 | 24 (12/12) | 13.8 | 1/4 | inconclusiva |
| 15 | meme_BONK_baseline | Meme · von | +0.00 | -144.20 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 1/4 | inconclusiva |

## Top 15 por PnL

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Semanas > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | MEW_poorjev_baseline | Meme · poorjev | +20.01 | -3.90 | **-22.73** | -0.22 (0.54) | -17.62 | 20 (20/0) | 99.6 | 1/4 | inconclusiva |
| 2 | MEW_poorjev_relaxed | Meme · poorjev | +20.01 | -3.90 | **-22.73** | -0.22 (0.54) | -17.62 | 20 (20/0) | 99.6 | 1/4 | inconclusiva |
| 3 | MEW_hybrid_poorjev_regime | Meme · híbridos | +20.01 | -3.90 | **-22.73** | -0.22 (0.54) | -17.62 | 20 (20/0) | 99.6 | 1/4 | inconclusiva |
| 4 | poorjev_baseline | SOL · poorjev | +19.21 | +186.99 | **+83.96** | +75.03 (0.02) | -7.09 | 20 (20/0) | 79.2 | 4/4 | inconclusiva |
| 5 | poorjev_relaxed | SOL · poorjev | +19.21 | +186.99 | **+83.96** | +75.03 (0.02) | -7.09 | 20 (20/0) | 79.2 | 4/4 | inconclusiva |
| 6 | h3_limit_poorjev_relaxed | SOL · hipóteses (lab) | +18.59 | +180.77 | **+81.46** | +71.13 (0.06) | -6.49 | 18 (18/0) | 76.4 | 4/4 | inconclusiva |
| 7 | WIF_poorjev_baseline | Meme · poorjev | +17.47 | +4.10 | **-36.65** | +6.28 (0.09) | -22.82 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 8 | WIF_poorjev_relaxed | Meme · poorjev | +17.47 | +4.10 | **-36.65** | +6.28 (0.09) | -22.82 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 9 | WIF_hybrid_poorjev_regime | Meme · híbridos | +17.47 | +4.10 | **-36.65** | +6.28 (0.09) | -22.82 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 10 | GOAT_poorjev_baseline | Meme · poorjev | +17.01 | -0.79 | **-31.15** | +3.75 (0.20) | -16.97 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 11 | GOAT_poorjev_relaxed | Meme · poorjev | +17.01 | -0.79 | **-31.15** | +3.75 (0.20) | -16.97 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 12 | GOAT_hybrid_poorjev_regime | Meme · híbridos | +17.01 | -0.79 | **-31.15** | +3.75 (0.20) | -16.97 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 13 | BONK_poorjev_baseline | Meme · poorjev | +14.50 | +0.84 | **-46.54** | +1.26 (0.40) | -32.42 | 20 (20/0) | 99.6 | 1/4 | inconclusiva |
| 14 | BONK_poorjev_relaxed | Meme · poorjev | +14.50 | +0.84 | **-46.54** | +1.26 (0.40) | -32.42 | 20 (20/0) | 99.6 | 1/4 | inconclusiva |
| 15 | BONK_hybrid_poorjev_regime | Meme · híbridos | +14.50 | +0.84 | **-46.54** | +1.26 (0.40) | -32.42 | 20 (20/0) | 99.6 | 1/4 | inconclusiva |

⚠ = fork ou hipótese desenhada com dados do run ao vivo que se sobrepõem ao fim desta janela (ver Cuidados).

## Famílias

| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor | Pior |
|---|---:|---:|---:|---:|---|---|
| Meme · forks | 9 | -13.15 | -159.76 | 1/9 | h1_exits_WIF_poorjev_relaxed__fork2 | h1_exits_FARTCOIN_poorjev_relaxed__fork1 |
| Meme · hipóteses (lab) | 14 | -15.51 | -267.30 | 0/14 | h1_exits_BONK_poorjev_relaxed | h2_ensemble_GOAT |
| Meme · híbridos | 7 | +14.50 | -36.65 | 3/7 | MEW_hybrid_poorjev_regime | FARTCOIN_hybrid_poorjev_regime |
| Meme · laya | 14 | +0.00 | +0.00 | 2/14 | GOAT_laya_relaxed | BONK_laya_baseline |
| Meme · poorjev | 14 | +14.50 | -36.65 | 6/14 | MEW_poorjev_relaxed | FARTCOIN_poorjev_baseline |
| Meme · regras | 28 | +0.89 | -15.68 | 5/28 | GOAT_rule_donch_regime_full | PNUT_rule_donch_regime_full |
| Meme · von | 14 | -0.53 | -6.49 | 2/14 | meme_GOAT_baseline | meme_PNUT_relaxed |
| SOL · forks | 6 | -9.16 | -158.64 | 0/6 | relaxed_expcap50__fork1 | laya_relaxed__fork1 |
| SOL · hipóteses (lab) | 8 | +8.13 | -18.40 | 6/8 | h3_limit_poorjev_relaxed | h1_exits_von_relaxed |
| SOL · híbridos | 1 | +3.46 | -87.50 | 1/1 | hybrid_von_relaxed_cap2 | hybrid_von_relaxed_cap2 |
| SOL · jev | 3 | +0.51 | -0.49 | 0/3 | jev_article | jev_baseline |
| SOL · laya | 2 | +0.51 | -0.49 | 0/2 | laya_relaxed | laya_baseline |
| SOL · poorjev | 2 | +19.21 | +83.96 | 2/2 | poorjev_relaxed | poorjev_baseline |
| SOL · regras | 2 | +9.14 | +53.70 | 2/2 | grid_sol_2pct | rsi_sol_1h |
| SOL · von | 3 | +0.51 | -7.35 | 1/3 | relaxed | v2 |

## Bot real: livro A × livro B

| Livro | Perfil | Valor ini. | Valor fim | PnL $ | PnL % | vs segurar $ | Acerto 15 min | MDD % | Trades | Saídas |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A | relaxed_paper | 51.8607 | 58.3407 | +6.4800 | +12.49% | +6.2389 | 48.0% | -10.36 | 223 | – |
| B | relaxed_exits_paper | 51.8607 | 49.6443 | -2.2164 | -4.27% | -2.4574 | 51.8% | -7.69 | 5483 | sl:34, trail:32, tp:14 |

## Validação contra o run ao vivo

Período comum: 2026-10-01T22:24:00-03:00 → 2026-10-06T09:00:00-03:00. Palavras de mercado do estado reconstruído × registadas ao vivo no mesmo instante (portfólio dono do estado):

| Ativo | Decisões | Estado de mercado igual | move | vol | color | rng |
|---|---:|---:|---:|---:|---:|---:|
| SOL | 25983 | 69.7% | 89.2% | 99.9% | 93.1% | 83.0% |
| BONK | 939 | 39.3% | 65.0% | 81.4% | 87.8% | 87.0% |
| WIF | 940 | 46.6% | 69.4% | 80.6% | 91.7% | 89.9% |
| POPCAT | 939 | 18.1% | 40.5% | 68.6% | 77.8% | 73.1% |
| FARTCOIN | 937 | 33.3% | 57.0% | 75.7% | 87.8% | 84.1% |
| PNUT | 939 | 14.7% | 38.5% | 74.0% | 69.0% | 68.6% |
| MEW | 938 | 42.0% | 61.9% | 84.4% | 88.6% | 82.9% |
| GOAT | 936 | 20.3% | 43.8% | 71.4% | 75.8% | 72.4% |

Respostas dos modelos do backtest × ao vivo para os mesmos estados (critérios baseline):

| Modelo | Estados ao vivo | Comparados | Mesma ação | Confiança ±0,01 |
|---|---:|---:|---:|---:|
| von | 148 | 147 | 100.0% | 100.0% |
| laya | 148 | 147 | 100.0% | 100.0% |
| poorjev | 148 | 147 | 100.0% | 100.0% |
| jev | 105 | 105 | 100.0% | 20.9% |

Trades no período comum (ao vivo × simulado; posições iniciais diferentes, só ordem de grandeza): h1_exits_FARTCOIN_poorjev_relaxed__fork1 286×362, laya_relaxed__fork1 235×294, h1_exits_von_relaxed 162×139, h1_exits_FARTCOIN_poorjev_relaxed 146×138, h1_exits_BONK_poorjev_relaxed 150×104, h1_exits_WIF_poorjev_relaxed 146×101, poorjev_relaxed__fork1 82×140, h2_ensemble_sol 144×51, h1_exits_POPCAT_poorjev_relaxed 83×100, h1_exits_GOAT_poorjev_relaxed 83×89, h1_exits_MEW_poorjev_relaxed 104×60, h1_exits_hybrid_von_cap2 75×72, h1_exits_WIF_poorjev_relaxed__fork1 42×101, h2_ensemble_FARTCOIN 60×79, h2_ensemble_BONK 77×58, h1_exits_BONK_poorjev_relaxed__fork1 38×95, h2_ensemble_WIF 68×64, h1_exits_PNUT_poorjev_relaxed 70×60, h1_exits_WIF_poorjev_relaxed__fork2 4×106, h1_exits_von_relaxed__fork1 34×66, h2_ensemble_FARTCOIN__fork1 31×62, h2_ensemble_POPCAT 45×46, h2_ensemble_WIF__fork1 30×52, h2_ensemble_GOAT 44×34, h2_ensemble_MEW 38×38

## Vereditos

- vencedoras: 0, perdedoras: 10, inconclusivas: 117.
- Regra: a do run ao vivo (`bot/analytics.verdict`), com a janela de 30 dias a cumprir os dias mínimos; continua a exigir ≥ 30 round trips fechados.

## Cuidados

- **Look-ahead / sobreajuste:** os forks (e os textos de critérios dos forks de critérios) foram desenhados pela revisão noturna com os dias 1–5 do run ao vivo (2026-10-01 → 2026-10-06), que são os últimos dias desta janela. O resultado deles nessa parte é dentro da amostra; compare-os sobretudo nas semanas 1–3 (coluna de semanas no summary.json). Portfólios afetados marcados com ⚠.
- Os parâmetros do relaxed (conf ≥ 0,35, margem ≥ 0,20) foram calibrados nas primeiras decisões do von em setembro, antes da janela; o v2 usa critérios reescritos em 2026-09-24 (antes da janela).
- Estados: SOL a partir de uma grelha de 10 s da Binance (o histórico ao vivo tem ~1 marca a cada 10,4 s); memecoins a partir de fechos de 1 m; palavras de profundidade/taxas constantes (como ao vivo). Pequenas diferenças de amostragem mudam algumas palavras de movimento/volatilidade.
- Fills: cotação sintética = marca do minuto ± custo mediano por ativo medido nos fills reais do run ao vivo; as variantes `_full` (100% do saldo) podem ter mais impacto do que o estimado.
- Decisão a cada 60 s (ao vivo: SOL a cada ~15 s, memecoins a cada ~7 min por moeda, lab a cada 15 s); o bot real a cada 15 s.
