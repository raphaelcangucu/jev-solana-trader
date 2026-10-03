# Resumo dos testes em paper — noite de 2026-09-24

**Snapshot:** 2026-09-24 **20:33:31 BRT** (último mark de SOL em `data/prices.jsonl`; os marks das memes são de 20:33:28–20:33:35 BRT). Todos os horários estão em BRT (UTC-3).
**Modo:** somente leitura. Nada foi reiniciado nem alterado no simulador e nenhum swap foi feito. Os números saem dos arquivos de estado e dos logs, via `/workspace/strategy-research/scripts/evening_summary.py`, `evening_render.py` e `evening_extra2.py`. Os resultados brutos estão em `/workspace/strategy-research/out/evening_summary.json`.

## 0. Método (resumo)
- **Início** de cada portfólio: `started_brt` do JSON. Quando o JSON não tem esse campo, uso `created_ts` (von baseline 00:10:27, von relaxed 00:33:09, v2 04:00:03, memes von 00:33:18).
- **Horas líquidas** = decorrido até o snapshot menos a parte das paradas 00:11–00:21 e 08:56–09:14 que cai depois do início. As lacunas nos marks confirmam as paradas: 9,9 min a partir de 00:10:57 e cerca de 18,4 min a partir de 08:56:10.
- **Valor inicial** = saldo inicial × o preço do primeiro mark de equity do próprio portfólio. Para as memes, uso o `start_price` do JSON, que é o mesmo preço usado no benchmark. **Valor atual** = saldo atual (JSON) × o mark mais recente. A reconstrução a partir dos trades (`portfolio_after`) mais os preços bate com o último mark de equity em todos os portfólios.
- **B&H SOL:** (a) o mix inicial 0,017392206 SOL + 50,00929 USDT mantido; (b) 100% do valor inicial em SOL no início do portfólio. **B&H meme:** 50 USDT inteiros na moeda no início. **vs 100% USDT** = PnL.
- **Custo total vs mark** = diferença entre o que foi pago/recebido e o valor ao mark de referência. Inclui a `fee_usdt` registrada (5 bps + rede) e a slippage embutida no preço efetivo. O custo medido por modo de fill foi: **fill "mark"** (fallback quando a cotação Jupiter falha, por exemplo com HTTP 429) ≈ **55,6 bps** em SOL e em memes; **fill "jupiter_quote"** ≈ **0,9 bps em SOL** e **10,8 bps em memes**.
- **Round trip** = cada venda. Custo médio proporcional, com a posição inicial em SOL contada a P0. Vitória quando o realizado for > 0. **Turnover** = notional negociado ÷ valor inicial. **Exposição média** = % do equity no ativo, média em grade de 1 min (sem os minutos de parada), com a posição reconstruída dos trades.
- **MDD:** calculado (a) sobre os marks de equity gravados (SOL a cada ~15 s; memes von/laya/poorjev/hybrid a cada ~7 min por moeda, na rotação; regras a cada 30 s) e (b) sobre a série reconstruída em 1 min (posição dos trades × preços em `data/prices.jsonl` e `data/meme/prices/*.jsonl`). **Vol** = desvio-padrão dos log-retornos de 5 min da série reconstruída, excluindo a parada, em %/h (×√12).
- **Decomposição:** retorno ≈ Σ w(t-1)·r(t) em 5 min. **Estático** = w̄·Σr (beta/exposição). **Timing** = Σ(w−w̄)·r. O que sobra (custos, cortes da parada) é residual. **Placebo de timing:** desloco circularmente o vetor de exposição contra os retornos, preservando a distribuição e a autocorrelação da exposição, e p = fração dos deslocamentos com resultado ≥ ao real. Nas memes o placebo é agrupado nas 7 moedas com o mesmo deslocamento.
- **Testes de excesso:** sinal (binomial bilateral) nas 7 moedas; bootstrap simples do excesso somado nas 7 moedas (10 mil reamostragens). As moedas são muito correlacionadas, então o IC fica otimista. Para SOL, block-bootstrap (blocos de 1 h) do excesso de 5 min vs o mix.
- **Decisões:** "% passou no gate" = decisões com `final_action` buy/sell. "% ≥ limiar" usa 0,60 no baseline/v2 e 0,35 no relaxed/hybrid. Nas regras, `confidence` é sempre 1,0 e não significa nada.

## 1. Contexto de mercado

- **SOL** (marks Coinbase, `data/prices.jsonl`, sem stale/fabricated): primeiro mark do dia 115.545 às 00:06:27; agora 117.000 às 20:33:31 (+1.26%). Máxima do dia 117.720 às 13:41:46, mínima 112.505 às 06:35:34 (amplitude 4.64%).
- SOL nos marcos: 00:33 114.610 · 00:41 114.690 · 04:49 115.540 · 13:55 117.005 · 15:09 116.700.

| Moeda | Agora | Δ desde 00:41 | Δ desde 13:55 | Δ desde 15:09 | Máx/mín do log (desde 00:33) |
|---|---|---|---|---|---|
| BONK | 3.774e-06 (20:33:28) | +8.11% (ref 3.491e-06 @ 00:41:18) | +2.06% (ref 3.698e-06) | +3.34% (ref 3.652e-06) | 3.792e-06 / 3.39e-06 |
| WIF | 0.2364 (20:33:29) | -1.99% (ref 0.2412 @ 00:41:20) | -0.46% (ref 0.2375) | +0.55% (ref 0.2351) | 0.2483 / 0.2297 |
| POPCAT | 0.05605 (20:33:30) | -0.59% (ref 0.05638 @ 00:41:21) | -2.37% (ref 0.05741) | -0.99% (ref 0.05661) | 0.05836 / 0.05311 |
| FARTCOIN | 0.18464 (20:33:32) | -0.50% (ref 0.18557 @ 00:41:22) | -3.43% (ref 0.19119) | -2.26% (ref 0.1889) | 0.1934 / 0.1806 |
| PNUT | 0.05457 (20:33:33) | +1.56% (ref 0.05373 @ 00:41:23) | -1.83% (ref 0.05559) | -0.76% (ref 0.05499) | 0.05586 / 0.05228 |
| MEW | 0.0004929 (20:33:34) | +3.66% (ref 0.0004755 @ 00:41:25) | -1.73% (ref 0.0005016) | -1.34% (ref 0.0004996) | 0.0005075 / 0.000462 |
| GOAT | 0.01915 (20:33:35) | -0.57% (ref 0.01926 @ 00:41:26) | -3.91% (ref 0.01993) | -2.40% (ref 0.01962) | 0.01994 / 0.01864 |

## 2. Portfólios SOL

Base: 0,017392206 SOL + 50,00929 USDT. B&H mix = manter esse mix desde o início de CADA portfólio; B&H 100% SOL = todo o valor inicial em SOL no início dele; vs USDT = PnL (USDT parado = valor inicial).

| Portfólio | Início (BRT) | Horas líq. | Valor ini. | Valor atual | PnL $ | PnL % | Excesso vs B&H mix | Excesso vs 100% SOL | vs 100% USDT |
|---|---|---|---|---|---|---|---|---|---|
| von baseline | 00:10:27 | 19.92 | 52.014 | 52.044 | +0.030 | +0.06% | +0.000 (+0.00%) | -0.746 (-1.41%) | +0.030 |
| von relaxed | 00:33:09 | 19.71 | 52.003 | 51.100 | -0.903 | -1.74% | -0.944 (-1.81%) | -1.989 (-3.75%) | -0.903 |
| von v2 | 04:00:03 | 16.26 | 52.006 | 51.920 | -0.087 | -0.17% | -0.124 (-0.24%) | -1.074 (-2.03%) | -0.087 |
| laya baseline | 04:48:57 | 15.44 | 52.018 | 52.044 | +0.026 | +0.05% | +0.000 (+0.00%) | -0.654 (-1.24%) | +0.026 |
| laya relaxed | 04:48:57 | 15.44 | 52.018 | 52.044 | +0.026 | +0.05% | +0.000 (+0.00%) | -0.654 (-1.24%) | +0.026 |
| poorjev baseline | 04:48:57 | 15.44 | 52.018 | 52.396 | +0.378 | +0.73% | +0.352 (+0.68%) | -0.302 (-0.57%) | +0.378 |
| poorjev relaxed | 04:48:57 | 15.44 | 52.018 | 52.395 | +0.377 | +0.72% | +0.351 (+0.67%) | -0.303 (-0.58%) | +0.377 |
| grid_sol_2pct (regra) | 15:09:13 | 5.41 | 52.040 | 52.044 | +0.004 | +0.01% | +0.000 (+0.00%) | -0.107 (-0.21%) | +0.004 |
| rsi_sol_1h (regra) | 15:09:13 | 5.41 | 52.040 | 52.044 | +0.004 | +0.01% | +0.000 (+0.00%) | -0.107 (-0.21%) | +0.004 |
| hybrid_von_relaxed_cap2 | 15:08:28 | 5.42 | 52.037 | 51.961 | -0.076 | -0.15% | -0.083 (-0.16%) | -0.266 (-0.51%) | -0.076 |
| jev | – | – | – | – | – | – | – | – | – |

**jev:** desativado, sem portfólio, trades nem decisões. Não entra em nenhuma estatística.

| Portfólio | Compras/Vendas | Round trips (ganhos/total) | PnL realizado RT $ | Taxas registradas $ | Custo total vs mark $ | Turnover (x valor ini.) | Exposição média % | Posição atual |
|---|---|---|---|---|---|---|---|---|
| von baseline | 0/0 | – | – | 0.0000 | 0.0000 | 0.00 | 3.9 | 0.0174 SOL + 50.01 USDT (4% no ativo) |
| von relaxed | 36/3 | 1/3 | -1.611 | 0.1855 | 1.3690 | 6.27 | 88.0 | 0.4044 SOL + 3.78 USDT (93% no ativo) |
| von v2 | 1/2 | 0/2 | -0.085 | 0.0156 | 0.0221 | 0.54 | 2.1 | 0.0000 SOL + 51.92 USDT (0% no ativo) |
| laya baseline | 0/0 | – | – | 0.0000 | 0.0000 | 0.00 | 3.9 | 0.0174 SOL + 50.01 USDT (4% no ativo) |
| laya relaxed | 0/0 | – | – | 0.0000 | 0.0000 | 0.00 | 3.9 | 0.0174 SOL + 50.01 USDT (4% no ativo) |
| poorjev baseline | 2/0 | – | – | 0.0121 | 0.0857 | 0.42 | 33.7 | 0.2074 SOL + 28.13 USDT (46% no ativo) |
| poorjev relaxed | 2/0 | – | – | 0.0121 | 0.0872 | 0.42 | 33.7 | 0.2074 SOL + 28.13 USDT (46% no ativo) |
| grid_sol_2pct (regra) | 0/0 | – | – | 0.0000 | 0.0000 | 0.00 | 3.9 | 0.0174 SOL + 50.01 USDT (4% no ativo) |
| rsi_sol_1h (regra) | 0/0 | – | – | 0.0000 | 0.0000 | 0.00 | 3.9 | 0.0174 SOL + 50.01 USDT (4% no ativo) |
| hybrid_von_relaxed_cap2 | 9/0 | – | – | 0.0284 | 0.0553 | 0.89 | 76.1 | 0.4120 SOL + 3.75 USDT (93% no ativo) |

| Portfólio | MDD marks % | MDD reconstr. 1 min % | Vol equity %/h | Vol SOL %/h (mesma janela) | Beta | PnL estático (exposição) $ | PnL timing $ | p placebo timing | Fills Jupiter/mark |
|---|---|---|---|---|---|---|---|---|---|
| von baseline | -0.12 | -0.11 | 0.025 | 0.655 | 0.04 | +0.031 | -0.001 | – | 0/0 |
| von relaxed | -4.96 | -4.83 | 0.611 | 0.648 | 0.87 | +0.763 | -0.140 | 0.70 | 8/31 |
| von v2 | -0.47 | -0.40 | 0.094 | 0.674 | 0.06 | +0.017 | -0.079 | 0.87 | 1/2 |
| laya baseline | -0.10 | -0.10 | 0.028 | 0.725 | 0.04 | +0.021 | -0.001 | – | 0/0 |
| laya relaxed | -0.10 | -0.10 | 0.028 | 0.725 | 0.04 | +0.021 | -0.001 | – | 0/0 |
| poorjev baseline | -0.62 | -0.62 | 0.227 | 0.725 | 0.28 | +0.180 | +0.215 | 0.24 | 1/1 |
| poorjev relaxed | -0.62 | -0.62 | 0.227 | 0.725 | 0.28 | +0.180 | +0.215 | 0.24 | 1/1 |
| grid_sol_2pct (regra) | -0.05 | -0.05 | 0.016 | 0.408 | 0.04 | +0.005 | -0.000 | – | 0/0 |
| rsi_sol_1h (regra) | -0.05 | -0.05 | 0.016 | 0.408 | 0.04 | +0.005 | -0.000 | – | 0/0 |
| hybrid_von_relaxed_cap2 | -1.06 | -1.03 | 0.291 | 0.425 | 0.63 | +0.144 | -0.157 | 0.83 | 7/2 |

| Portfólio | Decisões | Confiança mín/mediana/máx | Limiar | % ≥ limiar | % escolheu buy/sell | % passou no gate (final buy/sell) | Principais motivos de bloqueio |
|---|---|---|---|---|---|---|---|
| von baseline | 4731 | 0.000 / 0.334 / 0.402 | 0.60 | 0.0 | 99.9 | 0.00 | low_confidence 4731, skip_noul_high 6 |
| von relaxed | 4678 | 0.000 / 0.334 / 0.402 | 0.35 | 38.2 | 99.9 | 0.83 | low_confidence 2891, low_prob_margin 1499, insufficient_usdt 1214, max_trades_hour 306, cooldown 211 |
| von v2 | 3860 | 0.000 / 0.233 / 0.352 | 0.60 | 0.0 | 99.8 | 0.08 | low_confidence 3857, low_prob_margin 3535, skip_noul_high 6, (none) 3 |
| laya baseline | 3664 | 0.000 / 0.028 / 0.096 | 0.60 | 0.0 | 98.4 | 0.00 | low_confidence 3664, skip_noul_high 178 |
| laya relaxed | 3664 | 0.000 / 0.028 / 0.096 | 0.35 | 0.0 | 98.4 | 0.00 | low_confidence 3664, low_prob_margin 3528, skip_noul_high 178 |
| poorjev baseline | 3664 | 0.513 / 0.520 / 0.649 | 0.60 | 0.1 | 100.0 | 0.05 | low_confidence 3661, (none) 2, cooldown 1 |
| poorjev relaxed | 3664 | 0.513 / 0.520 / 0.649 | 0.35 | 100.0 | 100.0 | 0.05 | low_prob_margin 3661, (none) 2, cooldown 1 |
| grid_sol_2pct (regra) | 649 | 1,0 fixo (regra; não é confiança) | – | – | 0.0 | 0.00 | waiting_new_bar_after_start 644, (none) 5 |
| rsi_sol_1h (regra) | 649 | 1,0 fixo (regra; não é confiança) | – | – | 0.0 | 0.00 | waiting_new_bar_after_start 644, (none) 5 |
| hybrid_von_relaxed_cap2 | 1265 | 0.000 / 0.324 / 0.400 | 0.35 | 17.1 | 99.1 | 0.71 | low_confidence 1049, low_prob_margin 384, max_trades_hour 91, insufficient_usdt 75, cooldown 36 |

## 3. Memes: agregado por estratégia (7 moedas × 50 USDT = 350 USDT)

| Rank (PnL) | Estratégia | Início | Horas líq. | Soma PnL $ | PnL % (s/ 350) | B&H mesmo período $ | Soma excesso vs B&H $ | Bate B&H | Sinal p (bilat.) | IC95% bootstrap excesso $ | Trades (C/V) | Custo vs mark $ | Exposição média % | Estático $ | Timing $ | p placebo timing (pool) | Fills Jup/mark | Pior MDD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | von_baseline | 00:33:18 | 19.70 | +0.000 | +0.00% | +4.374 | -4.374 | 4/7 | 1.000 | [-13.41; +2.91] | 0 (0/0) | 0.000 | 0.0 | +0.000 | +0.000 | – | 0/0 | 0.00 |
| 2 | laya_baseline | 13:55:39 | 6.63 | +0.000 | +0.00% | -5.881 | +5.881 | 6/7 | 0.125 | [+0.95; +10.17] | 0 (0/0) | 0.000 | 0.0 | +0.000 | +0.000 | – | 0/0 | 0.00 |
| 3 | laya_relaxed | 13:55:39 | 6.63 | +0.000 | +0.00% | -5.881 | +5.881 | 6/7 | 0.125 | [+0.82; +10.20] | 0 (0/0) | 0.000 | 0.0 | +0.000 | +0.000 | – | 0/0 | 0.00 |
| 4 | rule_donch_regime | 15:09:13 | 5.40 | +0.000 | +0.00% | -1.926 | +1.926 | 5/7 | 0.453 | [-3.28; +6.09] | 0 (0/0) | 0.000 | 0.0 | +0.000 | +0.000 | – | 0/0 | 0.00 |
| 5 | von_relaxed | 00:33:18 | 19.70 | -0.258 | -0.07% | +4.374 | -4.632 | 4/7 | 1.000 | [-13.73; +2.81] | 4 (2/2) | 0.276 | 0.4 | +0.023 | -0.075 | 0.63 | 0/4 | -0.35 |
| 6 | rule_regime | 15:09:13 | 5.40 | -1.072 | -0.31% | -1.926 | +0.854 | 5/7 | 0.453 | [-3.32; +4.32] | 7 (7/0) | 0.054 | 20.9 | -0.343 | -0.217 | 0.59 | 6/1 | -0.96 |
| 7 | hybrid_poorjev_regime | 15:08:36 | 5.41 | -2.954 | -0.84% | -1.279 | -1.675 | 1/7 | 0.125 | [-2.64; -0.46] | 63 (63/0) | 0.597 | 86.5 | -1.070 | -1.200 | 0.88 | 50/13 | -3.10 |
| 8 | poorjev_relaxed | 13:55:39 | 6.63 | -5.293 | -1.51% | -5.881 | +0.589 | 6/7 | 0.125 | [-0.13; +1.28] | 63 (63/0) | 0.849 | 87.7 | -4.885 | +0.761 | 0.22 | 48/15 | -3.54 |
| 9 | poorjev_baseline | 13:55:39 | 6.63 | -5.347 | -1.53% | -5.881 | +0.534 | 6/7 | 0.125 | [-0.12; +1.15] | 63 (63/0) | 0.904 | 87.8 | -4.885 | +0.761 | 0.22 | 45/18 | -3.57 |

Ranking por excesso vs B&H: laya_baseline (+5.88) > laya_relaxed (+5.88) > rule_donch_regime (+1.93) > rule_regime (+0.85) > poorjev_relaxed (+0.59) > poorjev_baseline (+0.53) > hybrid_poorjev_regime (-1.68) > von_baseline (-4.37) > von_relaxed (-4.63)

Estatísticas de decisão agregadas (memes):

| Estratégia | Decisões | Confiança mín/mediana/máx | % ≥ limiar | % passou no gate | Principais motivos |
|---|---|---|---|---|---|
| von_baseline | 1183 | 0.000 / 0.295 (mediana das medianas) / 0.395 | 0.0 | 0.00 | low_confidence 1183, skip_noul_high 7 |
| von_relaxed | 1183 | 0.000 / 0.295 (mediana das medianas) / 0.395 | 21.9 | 0.34 | low_confidence 924, low_prob_margin 700, insufficient_token 254, skip_noul_high 7, (none) 4 |
| laya_baseline | 397 | 0.009 / 0.047 (mediana das medianas) / 0.176 | 0.0 | 0.00 | low_confidence 397, skip_noul_high 259 |
| laya_relaxed | 397 | 0.009 / 0.047 (mediana das medianas) / 0.176 | 0.0 | 0.00 | low_confidence 397, low_prob_margin 349, skip_noul_high 259 |
| poorjev_baseline | 397 | 0.885 / 0.932 (mediana das medianas) / 0.968 | 100.0 | 15.87 | insufficient_usdt 327, (none) 63, max_trades_hour 7 |
| poorjev_relaxed | 397 | 0.885 / 0.932 (mediana das medianas) / 0.968 | 100.0 | 15.87 | insufficient_usdt 327, (none) 63, max_trades_hour 7 |
| rule_regime | 4543 | 1,0 fixo (regra) | – | 0.15 | waiting_new_bar_after_start 4508, (none) 35 |
| rule_donch_regime | 4543 | 1,0 fixo (regra) | – | 0.00 | waiting_new_bar_after_start 4508, (none) 35 |
| hybrid_poorjev_regime | 324 | 0.885 / 0.930 (mediana das medianas) / 0.968 | 100.0 | 19.44 | insufficient_usdt 253, (none) 64, max_trades_hour 7 |

## 4. Memes: tabela por moeda

B&H = 50 USDT inteiramente na moeda no início do portfólio (preço `start_price` do JSON).

| Moeda | Estratégia | Início | Horas | Valor atual | PnL $ | PnL % | B&H $ | Excesso vs B&H $ | vs USDT $ | C/V | RT (gan/tot) | Custo vs mark $ | Taxas $ | Turnover | Exp. média % | Posição | MDD marks % (n marks) | MDD 1 min % | Vol %/h | Timing $ | p placebo | Jup/mark | Decisões | Conf. mín/med/máx | % gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BONK | von_baseline | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | +3.853 | -3.853 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (172) | 0.00 | 0.000 | +0.000 | – | 0/0 | 172 | 0.000/0.295/0.392 | 0.00 |
| BONK | von_relaxed | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | +3.853 | -3.853 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (172) | 0.00 | 0.000 | +0.000 | – | 0/0 | 172 | 0.000/0.295/0.392 | 0.00 |
| BONK | laya_baseline | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | +1.014 | -1.014 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (58) | 0.00 | 0.000 | +0.000 | – | 0/0 | 58 | 0.032/0.048/0.121 | 0.00 |
| BONK | laya_relaxed | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | +1.014 | -1.014 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (58) | 0.00 | 0.000 | +0.000 | – | 0/0 | 58 | 0.032/0.048/0.121 | 0.00 |
| BONK | poorjev_baseline | 13:55:39 | 6.63 | 51.083 | +1.083 | +2.17% | +1.014 | +0.069 | +1.083 | 9/0 | – | 0.0745 | 0.0284 | 0.92 | 88.5 | 93% no ativo | -1.68 (58) | -1.99 | 1.283 | +0.339 | 0.05 | 8/1 | 58 | 0.913/0.938/0.965 | 15.52 |
| BONK | poorjev_relaxed | 13:55:39 | 6.63 | 51.132 | +1.132 | +2.26% | +1.014 | +0.118 | +1.132 | 9/0 | – | 0.0266 | 0.0284 | 0.92 | 88.6 | 93% no ativo | -1.68 (58) | -1.99 | 1.280 | +0.339 | 0.05 | 9/0 | 58 | 0.913/0.938/0.965 | 15.52 |
| BONK | rule_regime | 15:09:13 | 5.40 | 50.231 | +0.231 | +0.46% | +1.670 | -1.440 | +0.231 | 1/0 | – | -0.0146 | 0.0068 | 0.25 | 21.1 | 25% no ativo | -0.60 (649) | -0.60 | 0.282 | -0.060 | 0.55 | 1/0 | 649 | regra | 0.15 |
| BONK | rule_donch_regime | 15:09:13 | 5.40 | 50.000 | +0.000 | +0.00% | +1.670 | -1.670 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (649) | 0.00 | 0.000 | +0.000 | – | 0/0 | 649 | regra | 0.00 |
| BONK | hybrid_poorjev_regime | 15:08:36 | 5.41 | 51.357 | +1.357 | +2.71% | +1.798 | -0.441 | +1.357 | 9/0 | – | 0.0669 | 0.0284 | 0.92 | 85.7 | 93% no ativo | -1.68 (47) | -1.99 | 1.129 | -0.200 | 0.77 | 9/0 | 47 | 0.913/0.935/0.965 | 19.15 |
| WIF | von_baseline | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | -1.096 | +1.096 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (172) | 0.00 | 0.000 | +0.000 | – | 0/0 | 172 | 0.000/0.297/0.387 | 0.00 |
| WIF | von_relaxed | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | -1.096 | +1.096 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (172) | 0.00 | 0.000 | +0.000 | – | 0/0 | 172 | 0.000/0.297/0.387 | 0.00 |
| WIF | laya_baseline | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -0.315 | +0.315 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (58) | 0.00 | 0.000 | +0.000 | – | 0/0 | 58 | 0.015/0.047/0.176 | 0.00 |
| WIF | laya_relaxed | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -0.315 | +0.315 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (58) | 0.00 | 0.000 | +0.000 | – | 0/0 | 58 | 0.015/0.047/0.176 | 0.00 |
| WIF | poorjev_baseline | 13:55:39 | 6.63 | 49.748 | -0.252 | -0.50% | -0.315 | +0.063 | -0.252 | 9/0 | – | 0.0355 | 0.0284 | 0.92 | 88.3 | 92% no ativo | -1.55 (58) | -2.00 | 0.911 | +0.105 | 0.26 | 9/0 | 58 | 0.889/0.936/0.963 | 15.52 |
| WIF | poorjev_relaxed | 13:55:39 | 6.63 | 49.690 | -0.310 | -0.62% | -0.315 | +0.005 | -0.310 | 9/0 | – | 0.0944 | 0.0284 | 0.92 | 88.3 | 92% no ativo | -1.55 (58) | -2.00 | 0.914 | +0.105 | 0.26 | 8/1 | 58 | 0.889/0.936/0.963 | 15.52 |
| WIF | rule_regime | 15:09:13 | 5.40 | 49.924 | -0.076 | -0.15% | +0.276 | -0.352 | -0.076 | 1/0 | – | 0.0074 | 0.0068 | 0.25 | 21.0 | 25% no ativo | -0.56 (649) | -0.55 | 0.207 | -0.040 | 0.77 | 1/0 | 649 | regra | 0.15 |
| WIF | rule_donch_regime | 15:09:13 | 5.40 | 50.000 | +0.000 | +0.00% | +0.276 | -0.276 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (649) | 0.00 | 0.000 | +0.000 | – | 0/0 | 649 | regra | 0.00 |
| WIF | hybrid_poorjev_regime | 15:08:36 | 5.41 | 50.043 | +0.043 | +0.09% | +0.276 | -0.233 | +0.043 | 9/0 | – | 0.0911 | 0.0284 | 0.92 | 87.4 | 92% no ativo | -1.55 (47) | -2.00 | 0.972 | -0.100 | 0.75 | 7/2 | 47 | 0.889/0.933/0.954 | 19.15 |
| POPCAT | von_baseline | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | -0.486 | +0.486 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (169) | 0.00 | 0.000 | +0.000 | – | 0/0 | 169 | 0.000/0.299/0.392 | 0.00 |
| POPCAT | von_relaxed | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | -0.486 | +0.486 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (169) | 0.00 | 0.000 | +0.000 | – | 0/0 | 169 | 0.000/0.299/0.392 | 0.00 |
| POPCAT | laya_baseline | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -1.210 | +1.210 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (57) | 0.00 | 0.000 | +0.000 | – | 0/0 | 57 | 0.011/0.047/0.133 | 0.00 |
| POPCAT | laya_relaxed | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -1.210 | +1.210 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (57) | 0.00 | 0.000 | +0.000 | – | 0/0 | 57 | 0.011/0.047/0.133 | 0.00 |
| POPCAT | poorjev_baseline | 13:55:39 | 6.63 | 48.907 | -1.093 | -2.19% | -1.210 | +0.117 | -1.093 | 9/0 | – | 0.1656 | 0.0284 | 0.92 | 87.9 | 92% no ativo | -2.65 (57) | -2.73 | 1.079 | +0.076 | 0.31 | 8/1 | 57 | 0.885/0.939/0.966 | 15.79 |
| POPCAT | poorjev_relaxed | 13:55:39 | 6.63 | 48.908 | -1.092 | -2.18% | -1.210 | +0.118 | -1.092 | 9/0 | – | 0.1645 | 0.0284 | 0.92 | 87.9 | 92% no ativo | -2.65 (57) | -2.73 | 1.079 | +0.076 | 0.31 | 8/1 | 57 | 0.885/0.939/0.966 | 15.79 |
| POPCAT | rule_regime | 15:09:13 | 5.40 | 49.859 | -0.141 | -0.28% | -0.495 | +0.353 | -0.141 | 1/0 | – | -0.0175 | 0.0068 | 0.25 | 20.9 | 25% no ativo | -0.71 (649) | -0.71 | 0.224 | +0.027 | 0.33 | 1/0 | 649 | regra | 0.15 |
| POPCAT | rule_donch_regime | 15:09:13 | 5.40 | 50.000 | +0.000 | +0.00% | -0.495 | +0.495 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (649) | 0.00 | 0.000 | +0.000 | – | 0/0 | 649 | regra | 0.00 |
| POPCAT | hybrid_poorjev_regime | 15:08:36 | 5.41 | 49.412 | -0.588 | -1.18% | -0.345 | -0.243 | -0.588 | 9/0 | – | 0.1101 | 0.0284 | 0.92 | 87.0 | 92% no ativo | -2.62 (46) | -2.62 | 0.990 | -0.214 | 0.80 | 8/1 | 46 | 0.885/0.931/0.966 | 19.57 |
| FARTCOIN | von_baseline | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | -0.296 | +0.296 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (168) | 0.00 | 0.000 | +0.000 | – | 0/0 | 168 | 0.000/0.290/0.377 | 0.00 |
| FARTCOIN | von_relaxed | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | -0.296 | +0.296 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (168) | 0.00 | 0.000 | +0.000 | – | 0/0 | 168 | 0.000/0.290/0.377 | 0.00 |
| FARTCOIN | laya_baseline | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -1.678 | +1.678 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (56) | 0.00 | 0.000 | +0.000 | – | 0/0 | 56 | 0.009/0.050/0.133 | 0.00 |
| FARTCOIN | laya_relaxed | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -1.678 | +1.678 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (56) | 0.00 | 0.000 | +0.000 | – | 0/0 | 56 | 0.009/0.050/0.133 | 0.00 |
| FARTCOIN | poorjev_baseline | 13:55:39 | 6.63 | 48.436 | -1.564 | -3.13% | -1.678 | +0.114 | -1.564 | 9/0 | – | 0.0936 | 0.0284 | 0.92 | 87.7 | 92% no ativo | -3.57 (56) | -3.80 | 1.009 | +0.018 | 0.49 | 7/2 | 56 | 0.910/0.932/0.963 | 16.07 |
| FARTCOIN | poorjev_relaxed | 13:55:39 | 6.63 | 48.451 | -1.549 | -3.10% | -1.678 | +0.128 | -1.549 | 9/0 | – | 0.0783 | 0.0284 | 0.92 | 87.7 | 92% no ativo | -3.54 (56) | -3.77 | 1.009 | +0.018 | 0.49 | 7/2 | 56 | 0.910/0.932/0.963 | 16.07 |
| FARTCOIN | rule_regime | 15:09:13 | 5.41 | 49.690 | -0.310 | -0.62% | -1.128 | +0.817 | -0.310 | 1/0 | – | 0.0048 | 0.0068 | 0.25 | 20.8 | 25% no ativo | -0.96 (649) | -0.96 | 0.255 | -0.019 | 0.45 | 1/0 | 649 | regra | 0.15 |
| FARTCOIN | rule_donch_regime | 15:09:13 | 5.41 | 50.000 | +0.000 | +0.00% | -1.128 | +1.128 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (649) | 0.00 | 0.000 | +0.000 | – | 0/0 | 649 | regra | 0.00 |
| FARTCOIN | hybrid_poorjev_regime | 15:08:36 | 5.42 | 48.801 | -1.199 | -2.40% | -1.058 | -0.142 | -1.199 | 9/0 | – | -0.0329 | 0.0284 | 0.92 | 86.7 | 92% no ativo | -3.10 (46) | -3.54 | 0.847 | -0.236 | 0.94 | 9/0 | 46 | 0.910/0.930/0.961 | 19.57 |
| PNUT | von_baseline | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | +0.782 | -0.782 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (168) | 0.00 | 0.000 | +0.000 | – | 0/0 | 168 | 0.000/0.281/0.395 | 0.00 |
| PNUT | von_relaxed | 00:33:18 | 19.70 | 49.826 | -0.174 | -0.35% | +0.782 | -0.956 | -0.174 | 1/1 | 0/1 | 0.1377 | 0.0136 | 0.50 | 2.1 | 0% no ativo | -0.35 (168) | -0.35 | 0.062 | -0.108 | 0.75 | 0/2 | 168 | 0.000/0.281/0.395 | 1.19 |
| PNUT | laya_baseline | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -0.917 | +0.917 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (56) | 0.00 | 0.000 | +0.000 | – | 0/0 | 56 | 0.015/0.046/0.133 | 0.00 |
| PNUT | laya_relaxed | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -0.917 | +0.917 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (56) | 0.00 | 0.000 | +0.000 | – | 0/0 | 56 | 0.015/0.046/0.133 | 0.00 |
| PNUT | poorjev_baseline | 13:55:39 | 6.63 | 49.124 | -0.876 | -1.75% | -0.917 | +0.041 | -0.876 | 9/0 | – | 0.1612 | 0.0284 | 0.92 | 87.5 | 92% no ativo | -2.44 (56) | -2.48 | 0.894 | +0.160 | 0.19 | 6/3 | 56 | 0.885/0.930/0.957 | 16.07 |
| PNUT | poorjev_relaxed | 13:55:39 | 6.63 | 49.127 | -0.873 | -1.75% | -0.917 | +0.045 | -0.873 | 9/0 | – | 0.1576 | 0.0284 | 0.92 | 87.5 | 92% no ativo | -2.43 (56) | -2.48 | 0.895 | +0.160 | 0.19 | 7/2 | 56 | 0.885/0.930/0.957 | 16.07 |
| PNUT | rule_regime | 15:09:13 | 5.41 | 49.814 | -0.186 | -0.37% | -0.382 | +0.196 | -0.186 | 1/0 | – | 0.0073 | 0.0068 | 0.25 | 20.8 | 25% no ativo | -0.60 (649) | -0.60 | 0.192 | -0.053 | 0.78 | 1/0 | 649 | regra | 0.15 |
| PNUT | rule_donch_regime | 15:09:13 | 5.41 | 50.000 | +0.000 | +0.00% | -0.382 | +0.382 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (649) | 0.00 | 0.000 | +0.000 | – | 0/0 | 649 | regra | 0.00 |
| PNUT | hybrid_poorjev_regime | 15:08:36 | 5.42 | 49.428 | -0.572 | -1.14% | -0.201 | -0.371 | -0.572 | 9/0 | – | 0.1324 | 0.0284 | 0.92 | 86.5 | 92% no ativo | -2.20 (46) | -2.20 | 0.736 | -0.229 | 0.89 | 8/1 | 46 | 0.885/0.930/0.955 | 19.57 |
| MEW | von_baseline | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | +1.851 | -1.851 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (168) | 0.00 | 0.000 | +0.000 | – | 0/0 | 168 | 0.000/0.290/0.394 | 0.00 |
| MEW | von_relaxed | 00:33:18 | 19.70 | 49.916 | -0.084 | -0.17% | +1.851 | -1.935 | -0.084 | 1/1 | 0/1 | 0.1382 | 0.0136 | 0.50 | 0.7 | 0% no ativo | -0.20 (168) | -0.20 | 0.051 | +0.033 | 0.30 | 0/2 | 168 | 0.000/0.290/0.394 | 1.19 |
| MEW | laya_baseline | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -0.818 | +0.818 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (56) | 0.00 | 0.000 | +0.000 | – | 0/0 | 56 | 0.015/0.040/0.133 | 0.00 |
| MEW | laya_relaxed | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -0.818 | +0.818 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (56) | 0.00 | 0.000 | +0.000 | – | 0/0 | 56 | 0.015/0.040/0.133 | 0.00 |
| MEW | poorjev_baseline | 13:55:39 | 6.63 | 49.028 | -0.972 | -1.94% | -0.818 | -0.154 | -0.972 | 9/0 | – | 0.2582 | 0.0284 | 0.92 | 87.3 | 92% no ativo | -2.42 (56) | -3.08 | 0.674 | -0.038 | 0.59 | 0/9 | 56 | 0.885/0.930/0.968 | 16.07 |
| MEW | poorjev_relaxed | 13:55:39 | 6.63 | 49.028 | -0.972 | -1.94% | -0.818 | -0.154 | -0.972 | 9/0 | – | 0.2582 | 0.0284 | 0.92 | 87.2 | 92% no ativo | -2.42 (56) | -3.08 | 0.674 | -0.038 | 0.59 | 0/9 | 56 | 0.885/0.930/0.968 | 16.07 |
| MEW | rule_regime | 15:09:13 | 5.41 | 49.665 | -0.335 | -0.67% | -0.671 | +0.335 | -0.335 | 1/0 | – | 0.0690 | 0.0068 | 0.25 | 20.7 | 24% no ativo | -0.78 (649) | -0.78 | 0.154 | -0.115 | 0.92 | 0/1 | 649 | regra | 0.15 |
| MEW | rule_donch_regime | 15:09:13 | 5.41 | 50.000 | +0.000 | +0.00% | -0.671 | +0.671 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (649) | 0.00 | 0.000 | +0.000 | – | 0/0 | 649 | regra | 0.00 |
| MEW | hybrid_poorjev_regime | 15:08:36 | 5.42 | 48.994 | -1.006 | -2.01% | -0.552 | -0.454 | -1.006 | 9/0 | – | 0.2582 | 0.0284 | 0.92 | 86.1 | 92% no ativo | -2.44 (46) | -3.07 | 0.754 | -0.301 | 0.95 | 0/9 | 46 | 0.885/0.926/0.968 | 19.57 |
| GOAT | von_baseline | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | -0.234 | +0.234 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (166) | 0.00 | 0.000 | +0.000 | – | 0/0 | 166 | 0.000/0.295/0.387 | 0.00 |
| GOAT | von_relaxed | 00:33:18 | 19.70 | 50.000 | +0.000 | +0.00% | -0.234 | +0.234 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (166) | 0.00 | 0.000 | +0.000 | – | 0/0 | 166 | 0.000/0.295/0.387 | 0.00 |
| GOAT | laya_baseline | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -1.957 | +1.957 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (56) | 0.00 | 0.000 | +0.000 | – | 0/0 | 56 | 0.009/0.046/0.131 | 0.00 |
| GOAT | laya_relaxed | 13:55:39 | 6.63 | 50.000 | +0.000 | +0.00% | -1.957 | +1.957 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (56) | 0.00 | 0.000 | +0.000 | – | 0/0 | 56 | 0.009/0.046/0.131 | 0.00 |
| GOAT | poorjev_baseline | 13:55:39 | 6.63 | 48.328 | -1.672 | -3.34% | -1.957 | +0.285 | -1.672 | 9/0 | – | 0.1155 | 0.0284 | 0.92 | 87.0 | 92% no ativo | -3.49 (56) | -3.67 | 0.837 | +0.100 | 0.24 | 7/2 | 56 | 0.889/0.930/0.955 | 16.07 |
| GOAT | poorjev_relaxed | 13:55:39 | 6.63 | 48.372 | -1.628 | -3.26% | -1.957 | +0.329 | -1.628 | 9/0 | – | 0.0698 | 0.0284 | 0.92 | 87.0 | 92% no ativo | -3.40 (56) | -3.58 | 0.836 | +0.100 | 0.24 | 9/0 | 56 | 0.889/0.930/0.955 | 16.07 |
| GOAT | rule_regime | 15:09:13 | 5.41 | 49.746 | -0.254 | -0.51% | -1.198 | +0.944 | -0.254 | 1/0 | – | -0.0020 | 0.0068 | 0.25 | 20.8 | 25% no ativo | -0.60 (649) | -0.56 | 0.183 | +0.042 | 0.28 | 1/0 | 649 | regra | 0.15 |
| GOAT | rule_donch_regime | 15:09:13 | 5.41 | 50.000 | +0.000 | +0.00% | -1.198 | +1.198 | +0.000 | 0/0 | – | 0.0000 | 0.0000 | 0.00 | 0.0 | 0% no ativo | 0.00 (649) | 0.00 | 0.000 | +0.000 | – | 0/0 | 649 | regra | 0.00 |
| GOAT | hybrid_poorjev_regime | 15:08:36 | 5.42 | 49.011 | -0.989 | -1.98% | -1.198 | +0.209 | -0.989 | 9/0 | – | -0.0288 | 0.0284 | 0.92 | 85.9 | 92% no ativo | -2.18 (46) | -2.32 | 0.722 | +0.081 | 0.27 | 9/0 | 46 | 0.889/0.923/0.955 | 19.57 |

## 5. Interpretação quantitativa

### 5.1 SOL
- **No geral, nenhum teste de SOL mostra edge que se separe do ruído.** O dia foi de alta moderada: +1,26% desde o primeiro mark e +2,1% desde 00:33, com amplitude de 4,6% (mínima 112,505 às 06:35, máxima 117,72 às 13:41). Todos os portfólios ficaram **abaixo do B&H 100% SOL**. Os que não negociaram ficam exatamente iguais ao B&H mix.
- **von relaxed** é o único com amostra razoável (39 trades: 36 compras e 3 vendas; 1 de 3 round trips vencedor). Está −0,90 $ (−1,74%), −0,94 $ vs o mix e −1,99 $ vs 100% SOL.
  - **Motor do resultado:** exposição média de 88% (beta 0,87) rendeu +0,76 $ estático. O timing foi −0,14 $, com placebo p = 0,70, ou seja, sem habilidade de timing.
  - **Custos:** o custo total vs mark foi **1,37 $**, maior que todo o déficit vs o mix. Turnover de 6,3×. **31 dos 39 fills foram "mark"** (fallback de ~55 bps por falha/429 na cotação Jupiter). As 8 cotações Jupiter custaram ~1 bp.
  - **Antes de custos,** o excesso vs o mix seria ≈ +0,4 $, o que é basicamente a exposição extra a SOL num dia de alta, e ainda assim pior que o 100% SOL.
  - O block-bootstrap do excesso de 5 min dá IC95% [−3,86; +2,06] $ e P(>0) = 0,30. É indistinguível de zero.
- **poorjev baseline/relaxed:** +0,35 $ vs o mix com só 2 compras (06:37, perto da mínima do dia, e 13:22). Timing +0,215 $ com placebo p = 0,24; block-bootstrap IC95% [−0,32; +0,97], P(>0) = 0,83. **Com n = 2 não há teste que valha.** Parece sorte ou beta (exposição média de 34%, hoje 46%).
  - Os dois portfólios são praticamente idênticos. A confiança do poorjev fica sempre em 0,513–0,649, então o relaxed barra quase tudo por `low_prob_margin` (3661/3664) e o baseline por `low_confidence`. Os gates não diferenciam nada na prática.
- **von baseline e laya b/r:** 0 trades. A confiança máxima do von é 0,402 (limiar 0,60) e a do laya é 0,096, então o laya nunca passa em nenhum gate. Resultado = B&H mix por construção.
- **v2:** 3 trades (1 compra, 2 vendas), −0,12 $ vs o mix. Está **100% em USDT** desde 12:01, então fica short de beta relativo ao mix enquanto SOL sobe. Block-bootstrap IC [−0,33; +0,06], P(>0) = 0,10.
- **grid_sol_2pct / rsi_sol_1h:** 0 trades, e isso é esperado. Desde 15:09 o SOL oscilou entre 116,16 e 117,645 (1,3%), abaixo do passo de 2% do grid. O RSI 1h está em 55,9, sem cruzar 30/70. Só houve 5 avaliações de barra nova; as outras 644 decisões são `waiting_new_bar_after_start`. **Com barras de 1 h, 5,4 h não dizem nada.** Essas estratégias precisam de dias.
- **hybrid_von_relaxed_cap2:** 9 compras e 0 vendas, já 93% em SOL. −0,08 $ vs o mix e −0,27 $ vs 100% SOL. Timing −0,16 $ (placebo p = 0,83); block-bootstrap IC [−0,80; +0,60].
  - O cap de 2/h segurou o turnover: 0,89× em 5,4 h, contra 6,3× em 19,7 h no von relaxed (~0,16×/h vs ~0,32×/h). 7 dos 9 fills foram Jupiter, com custo de 0,055 $.
  - O filtro de regime **nunca bloqueou**: SOL EMA12 116,21 > EMA26 115,81 a tarde toda. Até agora é "von relaxed com freio de frequência".
  - Observação: o campo `start_price` do JSON está em 115,28, herdado. Qualquer "vs início" que use esse campo superestima o PnL deste portfólio. Aqui usei 116,575, o mark de 15:08:28.
- **jev:** desativado. Nada a medir.

### 5.2 Memes
- **O mercado dominou tudo.** Desde 13:55, 6 das 7 moedas caíram (−0,5% a −3,9%); só o BONK subiu (+2,1%). Desde 15:09 caíram 5 de 7. Desde 00:41 o BONK subiu +8,1% e puxa quase sozinho o B&H das von (+4,37 $ nas 7, sendo +3,85 $ do BONK).
- **laya b/r (+5,88 $ de excesso, 6/7):** zero trades. A confiança fica em 0,009–0,176, então não passa nunca. O "excesso" é só ter ficado em caixa numa janela de queda: beta zero, não habilidade. Teste do sinal p = 0,125.
- **rule_donch_regime (+1,93 $ de excesso, 0 trades):** mesma lógica. Não houve rompimento Donchian-20 com regime bull.
- **rule_regime (−1,07 $; +0,85 $ de excesso; 5/7; p = 0,45; IC [−3,3; +4,3]):** uma compra por moeda às 16:00 (primeira barra fechada após o início), com **25% do caixa**. Na implementação atual o `buy_fraction_usdt` = 0,25 vale por entrada, e com posição aberta ela não compra mais. Isso dá exposição de ~21%, e não os 100% do backtest. **Ou seja, o teste ao vivo é uma versão diluída da estratégia pesquisada.** O excesso vem de estar 79% em caixa numa queda. Timing −0,22 $ (placebo p = 0,59).
- **poorjev b/r (−5,35 / −5,29 $; +0,53 / +0,59 $ de excesso; 6/7; p = 0,125; IC [−0,12; +1,2] a [−0,13; +1,3]):**
  - A confiança é sempre 0,885–0,968 e o gate sempre passa. O que limita é o caixa: 9 compras de 25% do saldo por moeda até `insufficient_usdt` (327 bloqueios) e nenhuma venda.
  - Na prática é **DCA de entrada seguido de hold**, com exposição média de 88%. O estático (beta) foi −4,89 $ e o timing +0,76 $, porque escalonar as compras pegou preço médio melhor na queda. Placebo agrupado p = 0,22, não significativo. Custo vs mark 0,85–0,90 $.
- **hybrid_poorjev_regime (−2,95 $; −1,68 $ de excesso; 1/7; IC [−2,64; −0,46]):** o mesmo DCA do poorjev, só que começando às 15:08. O regime ficou bull o tempo todo e não bloqueou nenhuma compra. Comprou enquanto as moedas caíam: timing −1,20 $, placebo p = 0,88.
  - O IC exclui zero, mas as 7 moedas são altamente correlacionadas e a janela é uma só, então **não trate isso como significativo**.
  - A diferença de resultado entre poorjev e hybrid é quase só o **horário de início** (13:55 vs 15:08). O resultado depende do caminho e do beta, não do modelo.
- **von b/r (memes):** baseline com 0 trades. O relaxed fez 4 trades (PNUT e MEW, 1 round trip cada, os 2 perdedores, −0,26 $). O excesso de −4,4 a −4,6 $ vs B&H é quase só o BONK ter subido 8% com o von em caixa.
- **Ranking por PnL:** empate em 0 (von_baseline, laya_b, laya_r, donch) > von_relaxed −0,26 > rule_regime −1,07 > hybrid_poorjev_regime −2,95 > poorjev_relaxed −5,29 > poorjev_baseline −5,35. **Por excesso vs B&H:** laya b/r +5,88 > donch +1,93 > rule_regime +0,85 > poorjev_r +0,59 > poorjev_b +0,53 > hybrid −1,68 > von_b −4,37 > von_r −4,63. Os dois rankings são basicamente o ranking de **exposição média, com sinal invertido**, numa janela de queda.

### 5.3 O que observar
1. **Qualidade dos fills.** Os fills "mark" custam ~55 bps contra ~1 bp (SOL) e ~11 bps (memes) nos Jupiter. No von relaxed eles explicam todo o déficit. Vale acompanhar a taxa de 429 e comparar resultados só com fills Jupiter.
2. **Separar beta de habilidade.** Compare cada portfólio com um benchmark de **mesma exposição média**, não só com o B&H. As colunas estático/timing e o p do placebo já fazem isso. Só leve a sério um timing positivo que se repita com p < 0,05 em vários dias.
3. **poorjev** nunca vende: é DCA + hold, e os gates baseline/relaxed não o diferenciam. **laya** nunca negocia. Os dois precisam de recalibração (confiança fora da escala dos limiares) antes de dizer algo sobre o modelo.
4. **Regras 1h** (grid, RSI, donch, regime): precisam de dias. O `rule_regime` está com sizing de 25% (diluído em relação ao backtest). É uma decisão de desenho a revisar, não mudei nada.
5. **Híbridos:** até agora o filtro de regime não foi testado, porque o regime ficou bull a tarde toda. O teste real vem quando EMA12 cruzar abaixo da EMA26 no 1h.
6. **Tamanho da amostra:** a maioria dos portfólios tem 0 a 9 trades e no máximo 1 round trip. Win rate e teste do sinal por trade ainda não são informativos.

### 5.4 Notas de dados
- O `reports/models_start.md` tem uma segunda seção "Meme multi-model — start 15:08:36". Os JSONs e o equity de laya/poorjev meme continuam com início em **13:55:39** e mantêm os trades de antes das 15:08, então aquela seção é só um log repetido do soft-restart e não um reset. Aqui uso 13:55:39.
- As tabelas usam ponto decimal (saída do script). As decisões com `confidence` 0,000 do von são ciclos fail-closed/erro e entram no mínimo.
