# Simulação retroativa de 30 dias — bt30_2026-08-06

**Gerado (BRT):** 2026-10-07T01:28:58-03:00 · **Janela:** 2026-07-07T09:00:00-03:00 → 2026-08-06T09:00:00-03:00 · passo de decisão 60 s · paper only (nenhuma ordem real, nenhuma chave).

## Vencedor

Em 30 dias simulados, a maior habilidade (excesso ajustado à exposição) foi de FARTCOIN_rule_donch_regime_full (+69.12 US$, PnL +1.17%, 10 trades), e o maior PnL foi de FARTCOIN_rule_donch_regime_full (+1.17%, +212.67 US$ contra o buy & hold do mesmo ativo). Nenhum portfólio passa a regra do veredito (bater B&H e a barra USDC com p<0,05 e consistência em ≥3 de 4 semanas): 122 inconclusivos e 5 perdedores. Só por falta de round trips (mínimo 30) ficam de fora: meme_BONK_baseline (p=0.024, 0 RT, 4/4 semanas), BONK_laya_baseline (p=0.024, 0 RT, 4/4 semanas), BONK_laya_relaxed (p=0.024, 0 RT, 4/4 semanas), BONK_rule_regime (p=0.025, 13 RT, 3/4 semanas). É um resultado retroativo com estados e custos aproximados; serve para ordenar hipóteses, não para provar uma vencedora.

- Por habilidade: **FARTCOIN_rule_donch_regime_full** · por PnL: **FARTCOIN_rule_donch_regime_full** · pelo veredito: **nenhum**

## Método

Para cada portfólio do catálogo atual do run ao vivo (originais SOL e memecoins, regras, híbridos, hipóteses H1–H4 e EXP, forks de parâmetros e de critérios, Jev, Laya, poorjev) e para os livros A e B do bot real, o backtest repete 30 dias minuto a minuto com o MESMO código dos bots ao vivo (portões, cooldown, trades/h, fração de compra, teto de exposição, saídas TP/SL/trailing e reentrada, horas, ensemble por percentil, filtro de regime, ordens limite, regras em barras de 1 h), trocando só o relógio, os ficheiros e as cotações (backtest/simenv.py). Os modelos (von, Laya, poorjev; Jev hospedado nos portfólios SOL) respondem a cada estado de 12 adjetivos reconstruído do histórico; cada par (critérios, estado) é chamado uma vez e guardado em cache.

## Pressupostos

- Janela 30 dias até 2026-08-06T09:00:00-03:00 (BRT); decisão a cada 60 s; memecoins em rotação (uma moeda por minuto, cada moeda decide a cada 7 min, como o meme_bot); bot real a cada 15 s.
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
- Jev hospedado: só portfólios SOL; teto de 14462 chamadas.

## Dados

| Ativo | Fonte | Cobertura | Início | Fim | Retorno |
|---|---|---:|---:|---:|---:|
| SOL | coinbase:SOL-USD 1m | 99.99% | 81.25 | 73.38 | -9.69% |
| BONK | bybit:BONKUSDT 1m | 100.00% | 4.274e-06 | 2.78e-06 | -34.96% |
| WIF | kucoin:WIF-USDT 1m | 100.00% | 0.1687 | 0.1393 | -17.43% |
| POPCAT | bybit:POPCATUSDT 1m | 100.00% | 0.04925 | 0.04351 | -11.65% |
| FARTCOIN | kucoin:FARTCOIN-USDT 1m | 100.00% | 0.1627 | 0.13 | -20.10% |
| PNUT | bybit:PNUTUSDT 1m | 100.00% | 0.04472 | 0.03892 | -12.97% |
| MEW | bybit:MEWUSDT 1m | 100.00% | 0.0003829 | 0.0003291 | -14.05% |
| GOAT | bybit:GOATUSDT 1m | 100.00% | 0.01494 | 0.01315 | -11.98% |

## Modelos

| Modelo | Chamadas | Cache | Cobertura | conf P50 | conf P90 |
|---|---:|---:|---:|---:|---:|
| von | 15 | 561600 | 100.0% | 0.294 | 0.372 |
| laya | 15 | 86400 | 100.0% | 0.032 | 0.061 |
| poorjev | 31 | 98744 | 100.0% | 0.672 | 0.936 |
| jev | 0 | 43200 | 100.0% | 0.930 | 0.960 |

## Top 15 por habilidade (excesso ajustado à exposição)

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Semanas > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | FARTCOIN_rule_donch_regime_full | Meme · regras | +1.17 | +212.67 | **+69.12** | +91.04 (0.24) | -10.42 | 10 (5/5) | 30.3 | 3/4 | inconclusiva |
| 2 | h1_exits_BONK_poorjev_relaxed | Meme · hipóteses (lab) | -32.42 | +25.35 | **+57.03** | +70.87 (0.05) | -35.09 | 662 (629/33) | 95.4 | 2/4 | inconclusiva |
| 3 | BONK_hybrid_poorjev_regime | Meme · híbridos | -34.82 | +1.32 | **+48.91** | +0.67 (0.46) | -36.24 | 20 (20/0) | 99.4 | 4/4 | inconclusiva |
| 4 | BONK_poorjev_baseline | Meme · poorjev | -35.22 | -2.63 | **+45.56** | -6.22 (0.93) | -36.52 | 20 (20/0) | 99.5 | 4/4 | inconclusiva |
| 5 | BONK_poorjev_relaxed | Meme · poorjev | -35.22 | -2.63 | **+45.56** | -6.22 (0.93) | -36.52 | 20 (20/0) | 99.5 | 4/4 | inconclusiva |
| 6 | rsi_sol_1h | SOL · regras | +0.83 | +12.10 | **+35.08** | +37.91 (0.03) | -2.71 | 11 (8/3) | 28.2 | 3/4 | inconclusiva |
| 7 | FARTCOIN_rule_regime_full | Meme · regras | -5.89 | +142.08 | **+24.62** | +66.34 (0.27) | -12.49 | 26 (13/13) | 44.0 | 2/4 | inconclusiva |
| 8 | grid_sol_2pct | SOL · regras | -3.66 | -32.79 | **+23.99** | +26.59 (0.01) | -7.36 | 4 (4/0) | 63.9 | 1/4 | inconclusiva |
| 9 | FARTCOIN_rule_donch_regime | Meme · regras | +0.32 | +204.20 | **+17.75** | +21.16 (0.26) | -2.73 | 10 (5/5) | 7.7 | 3/4 | inconclusiva |
| 10 | GOAT_rule_donch_regime_full | Meme · regras | -0.50 | +114.84 | **+15.95** | +54.76 (0.20) | -8.37 | 10 (5/5) | 19.6 | 3/4 | inconclusiva |
| 11 | FARTCOIN_rule_regime | Meme · regras | -1.41 | +186.86 | **+7.15** | +15.06 (0.28) | -3.27 | 26 (13/13) | 11.2 | 2/4 | inconclusiva |
| 12 | GOAT_rule_donch_regime | Meme · regras | -0.08 | +119.00 | **+4.41** | +13.36 (0.20) | -2.15 | 10 (5/5) | 4.9 | 3/4 | inconclusiva |
| 13 | relaxed_expcap50__fork1 | SOL · forks | +0.02 | +4.02 | **+0.23** | +0.27 (0.02) | -0.01 | 1 (0/1) | 0.0 | 3/4 | inconclusiva |
| 14 | meme_BONK_baseline | Meme · von | +0.00 | +349.56 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 4/4 | inconclusiva |
| 15 | BONK_laya_baseline | Meme · laya | +0.00 | +349.56 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 4/4 | inconclusiva |

## Top 15 por PnL

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Semanas > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | FARTCOIN_rule_donch_regime_full | Meme · regras | +1.17 | +212.67 | **+69.12** | +91.04 (0.24) | -10.42 | 10 (5/5) | 30.3 | 3/4 | inconclusiva |
| 2 | rsi_sol_1h | SOL · regras | +0.83 | +12.10 | **+35.08** | +37.91 (0.03) | -2.71 | 11 (8/3) | 28.2 | 3/4 | inconclusiva |
| 3 | FARTCOIN_rule_donch_regime | Meme · regras | +0.32 | +204.20 | **+17.75** | +21.16 (0.26) | -2.73 | 10 (5/5) | 7.7 | 3/4 | inconclusiva |
| 4 | relaxed_expcap50__fork1 | SOL · forks | +0.02 | +4.02 | **+0.23** | +0.27 (0.02) | -0.01 | 1 (0/1) | 0.0 | 3/4 | inconclusiva |
| 5 | meme_BONK_baseline | Meme · von | +0.00 | +349.56 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 4/4 | inconclusiva |
| 6 | BONK_laya_baseline | Meme · laya | +0.00 | +349.56 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 4/4 | inconclusiva |
| 7 | BONK_laya_relaxed | Meme · laya | +0.00 | +349.56 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 4/4 | inconclusiva |
| 8 | meme_WIF_baseline | Meme · von | +0.00 | +174.27 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 3/4 | inconclusiva |
| 9 | WIF_laya_baseline | Meme · laya | +0.00 | +174.27 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 3/4 | inconclusiva |
| 10 | WIF_laya_relaxed | Meme · laya | +0.00 | +174.27 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 3/4 | inconclusiva |
| 11 | meme_POPCAT_baseline | Meme · von | +0.00 | +116.55 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/4 | inconclusiva |
| 12 | POPCAT_laya_baseline | Meme · laya | +0.00 | +116.55 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/4 | inconclusiva |
| 13 | POPCAT_laya_relaxed | Meme · laya | +0.00 | +116.55 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/4 | inconclusiva |
| 14 | meme_FARTCOIN_baseline | Meme · von | +0.00 | +200.98 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/4 | inconclusiva |
| 15 | FARTCOIN_laya_baseline | Meme · laya | +0.00 | +200.98 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/4 | inconclusiva |

⚠ = fork ou hipótese desenhada com dados do run ao vivo que se sobrepõem ao fim desta janela (ver Cuidados).

## Famílias

| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor | Pior |
|---|---:|---:|---:|---:|---|---|
| Meme · forks | 9 | -21.10 | -67.36 | 4/9 | FARTCOIN_laya_relaxed__fork1 | h1_exits_BONK_poorjev_relaxed__fork1 |
| Meme · hipóteses (lab) | 14 | -19.84 | -78.06 | 4/14 | h2_ensemble_WIF | h1_exits_BONK_poorjev_relaxed |
| Meme · híbridos | 7 | -14.25 | -6.78 | 4/7 | POPCAT_hybrid_poorjev_regime | BONK_hybrid_poorjev_regime |
| Meme · laya | 14 | +0.00 | +0.00 | 14/14 | GOAT_laya_relaxed | BONK_laya_baseline |
| Meme · poorjev | 14 | -14.25 | -11.62 | 0/14 | POPCAT_poorjev_relaxed | BONK_poorjev_baseline |
| Meme · regras | 28 | -5.15 | -29.26 | 23/28 | FARTCOIN_rule_donch_regime_full | BONK_rule_regime_full |
| Meme · von | 14 | -2.76 | -23.28 | 11/14 | meme_GOAT_baseline | meme_PNUT_relaxed |
| SOL · forks | 6 | -14.29 | -70.27 | 1/6 | relaxed_expcap50__fork1 | laya_relaxed__fork1 |
| SOL · hipóteses (lab) | 8 | -9.26 | -3.45 | 0/8 | h4_hours_poorjev_relaxed | h1_exits_von_relaxed |
| SOL · híbridos | 1 | -10.17 | -7.71 | 0/1 | hybrid_von_relaxed_cap2 | hybrid_von_relaxed_cap2 |
| SOL · jev | 3 | -0.38 | -0.33 | 0/3 | jev_article | jev_baseline |
| SOL · laya | 2 | -0.38 | -0.33 | 0/2 | laya_relaxed | laya_baseline |
| SOL · poorjev | 2 | -0.38 | -0.33 | 0/2 | poorjev_relaxed | poorjev_baseline |
| SOL · regras | 2 | -1.41 | +29.53 | 1/2 | rsi_sol_1h | grid_sol_2pct |
| SOL · von | 3 | -0.38 | -0.33 | 0/3 | v2 | relaxed |

## Bot real: livro A × livro B

| Livro | Perfil | Valor ini. | Valor fim | PnL $ | PnL % | vs segurar $ | Acerto 15 min | MDD % | Trades | Saídas |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A | relaxed_paper | 51.4236 | 46.4836 | -4.9400 | -9.61% | -4.8033 | 44.4% | -14.69 | 135 | – |
| B | relaxed_exits_paper | 51.4236 | 45.6661 | -5.7575 | -11.20% | -5.6208 | 46.0% | -12.64 | 3899 | trail:27, sl:26, tp:3 |

## Vereditos

- vencedoras: 0, perdedoras: 5, inconclusivas: 122.
- Regra: a do run ao vivo (`bot/analytics.verdict`), com a janela de 30 dias a cumprir os dias mínimos; continua a exigir ≥ 30 round trips fechados.

## Cuidados

- **Sem look-ahead nos forks:** esta janela acaba antes de 2026-10-01; os forks desenhados pela revisão noturna com os dias 2026-10-01 → 2026-10-06 estão aqui totalmente fora da amostra.
- Os parâmetros do relaxed (conf ≥ 0,35, margem ≥ 0,20) foram calibrados nas primeiras decisões do von no início de setembro de 2026 e o v2 usa critérios reescritos em 2026-09-24: nesta janela (que acaba antes de setembro) estão fora da amostra.
- Estados: SOL a partir de uma grelha de 10 s da Binance (o histórico ao vivo tem ~1 marca a cada 10,4 s); memecoins a partir de fechos de 1 m; palavras de profundidade/taxas constantes (como ao vivo). Pequenas diferenças de amostragem mudam algumas palavras de movimento/volatilidade.
- Fills: cotação sintética = marca do minuto ± custo mediano por ativo medido nos fills reais do run ao vivo; as variantes `_full` (100% do saldo) podem ter mais impacto do que o estimado.
- Decisão a cada 60 s (ao vivo: SOL a cada ~15 s, memecoins a cada ~7 min por moeda, lab a cada 15 s); o bot real a cada 15 s.
