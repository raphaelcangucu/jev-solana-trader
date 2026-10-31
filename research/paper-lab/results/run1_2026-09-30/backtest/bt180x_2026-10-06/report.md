# Simulação retroativa de 180 dias — bt180x_2026-10-06

**Gerado (BRT):** 2026-10-17T20:34:26-03:00 · **Janela:** 2026-04-09T09:00:00-03:00 → 2026-10-06T09:00:00-03:00 · passo de decisão 60 s · paper only (nenhuma ordem real, nenhuma chave).

## Vencedor

Em 180 dias simulados, a maior habilidade (excesso ajustado à exposição) foi de RAY_poorjev_relaxed (+971.35 US$, PnL +252.54%, 20 trades, todas compras: uma entrada concentrada num recuo, não seleção repetida), e o maior PnL foi de RAY_poorjev_relaxed (+252.54%, -13.60 US$ contra o buy & hold do mesmo ativo). Nenhum portfólio passa a regra do veredito (bater B&H e a barra USDC com p<0,05 e consistência em ≥4 de 6 meses): 33 inconclusivos e 7 perdedores. É um resultado retroativo com estados e custos aproximados; serve para ordenar hipóteses, não para provar uma vencedora.

- Por habilidade: **RAY_poorjev_relaxed** · por PnL: **RAY_poorjev_relaxed** · pelo veredito: **nenhum**

## Método

Para cada portfólio do catálogo atual do run ao vivo (originais SOL e memecoins, regras, híbridos, hipóteses H1–H4 e EXP, forks de parâmetros e de critérios, Jev, Laya, poorjev) e para os livros A e B do bot real, o backtest repete 180 dias minuto a minuto com o MESMO código dos bots ao vivo (portões, cooldown, trades/h, fração de compra, teto de exposição, saídas TP/SL/trailing e reentrada, horas, ensemble por percentil, filtro de regime, ordens limite, regras em barras de 1 h), trocando só o relógio, os ficheiros e as cotações (backtest/simenv.py). Os modelos (von, Laya, poorjev; Jev hospedado nos portfólios SOL) respondem a cada estado de 12 adjetivos reconstruído do histórico; cada par (critérios, estado) é chamado uma vez e guardado em cache.

**Âmbito deste run (`moedas_novas`):** só as moedas JUP, JTO, PYTH, RAY, BOME, PENGU, TRUMP, MOODENG (fora do run ao vivo; overlay só do backtest, backtest/assets_extra.json), com os portfólios listados nos Pressupostos e o "só segurar" de cada moeda. Sem portfólios SOL, sem bot real e sem validação contra o run ao vivo (estas moedas não têm decisões ao vivo).

## Pressupostos

- Janela 180 dias até 2026-10-06T09:00:00-03:00 (BRT); decisão a cada 60 s; memecoins em rotação (uma moeda por minuto, cada moeda decide a cada 7 min, como o meme_bot); bot real a cada 15 s.
- Capital: portfólios SOL com US$ 1000 na mistura do config.json (0.039188 em SOL ao preço do início da janela); memecoins com 1000.0 USDT; bot real com 0.017392206 SOL + 50.00929 USDT. Forks e hipóteses começam com o capital da família no início da janela (não com o estado do pai).
- Parâmetros: params.json + registry + overlay do run ao vivo (instantâneo em inputs/, copiado do run bt180_2026-10-06 para manter o MESMO catálogo e os mesmos pressupostos), resolvidos por bot/params.py; nenhuma pausa do dashboard é aplicada.
- Estado: palavras deep/quiet (profundidade/taxas) constantes, como em todas as decisões registadas ao vivo (as marcas Coinbase/Gate.io têm impacto 0). SOL: grelha de 10 s da Binance (ao vivo ~1 marca/10,4 s, sol_bot + rules_bot); memecoins: fecho de 1 m (ao vivo ~1 marca/60 s). Bot real: 16 fechos de 1 m da Binance; spread/profundidade/taxas e inventário (carteira) constantes em tight/deep/quiet/sold, como em >99,9% dos ciclos ao vivo.
- Preços: SOL Coinbase 1 m (fonte da marcação ao vivo); memecoins Bybit/KuCoin 1 m escolhidas pela correlação com a Gate.io (fonte ao vivo, só ~7 dias de 1 m disponíveis). Lacunas ≤ 5 min preenchidas com o último fecho.
- Fills: cotação sintética = marca × (1 ± custo por ativo), com o custo mediano dos fills reais (Jupiter/Raydium) do run ao vivo (os mesmos valores do bt180_2026-10-06) menos o extra de 5 bps que o código soma: SOL 2.4 bps, JUP 12.7 bps, JTO 12.7 bps, PYTH 32.8 bps, RAY 12.7 bps, BOME 12.7 bps, PENGU 12.7 bps, TRUMP 12.7 bps, MOODENG 32.8 bps; taxa de rede 5e-6 SOL. Bot real: 10 bps (paper_cost_bps).
- Ordens limite (H3): enchem quando a mínima (compra) ou máxima (venda) do minuto cruza o limite; saídas TP/SL/trailing avaliadas no fecho de cada minuto (ao vivo: na marca de cada ciclo).
- Regras: barras de 1 h da Coinbase (SOL) e Gate.io (memes), os mesmos fetchers do rules_bot; agem no primeiro passo depois do fecho da barra. Regime de SOL dos híbridos = EMA12 > EMA26 na última barra fechada.
- Modelos: servidores próprios (portas 8865–8867, mesmos venvs/comandos do lab); cada par (critérios, estado) chamado uma vez e guardado em cache; falha → hold (fail-closed). Ensemble H2: janelas de percentil com o mesmo número de decisões que ao vivo (480 SOL / 200 memes), que a 60 s cobrem um período ~4× maior no SOL.
- Veredito: a MESMA regra do run ao vivo (≥30 round trips fechados; bate B&H com p<0,05 por block-bootstrap; PnL acima da barra de 6%/a USDC), com a consistência semanal trocada por mensal: excesso vs B&H positivo em ≥ 4 de 6 blocos de 30 dias contados do fim da janela. Escala: equity gravada e métricas (exposição, habilidade, timing com placebo, bootstrap) numa grelha de 1 h em vez de 5 min — o placebo é O(n²) e a 5 min seriam 51 840 pontos por portfólio; o bootstrap usa blocos de 12 pontos (12 h). O MDD também é medido na grelha de 1 h (pode subestimar quedas intra-hora). As 4 últimas semanas continuam no summary (weeks_*).
- Look-ahead: forks criados a partir de 2026-10-03 usaram dados de 2026-10-01 a 2026-10-06 (fim desta janela).
- Janela longa contínua: um único caminho de 180 dias com o capital inicial no início da janela (posições, cooldowns e janelas do ensemble herdados de mês para mês); chart.json com as curvas normalizadas (1000 = início).
- Moedas novas (só backtest, backtest/assets_extra.json; o memecoins.json do lab não muda): JUP, JTO, PYTH, RAY, BOME, PENGU, TRUMP, MOODENG. Mesmos parâmetros das famílias meme (params.json + overlay do instantâneo, resolvidos com asset=<SYM>; nenhuma camada por moeda), mesmo capital e o mesmo estado partilhado a partir de meme_<SYM>_baseline. Rotação com cadência de 7 min por moeda (a das 7 memecoins ao vivo). Fontes de 1 m escolhidas pela cobertura e pela correlação com a Gate.io (fonte da marcação ao vivo): como a Gate.io só guarda ~7 dias de 1 m (depois do fim da janela), a correlação usada é a dos retornos de 1 h com as barras de 1 h da Gate.io dentro da janela. Custos sem fills ao vivo: Sem fills ao vivo destas moedas. Custo sobre a marca (antes do extra de 5 bps que o código soma) = mediana do custo medido nas 7 memecoins atuais (bt30_2026-10-06: BONK 1,4 · FARTCOIN 5,8 · WIF 8,5 · POPCAT 12,7 · MEW 24,3 · GOAT 29,8 · PNUT 32,8 → 12,7 bps). Moedas com liquidez on-chain (DexScreener, soma dos pares Solana; a API devolve no máximo 30 pares, por isso é um limite inferior) abaixo da da PNUT (~3,1 M US$, a mais cara das atuais) ficam com o custo da PNUT, 32,8 bps (conservador): PYTH e MOODENG.
- Portfólios por moeda: meme_{SYM}_baseline, meme_{SYM}_relaxed, {SYM}_poorjev_relaxed, h1_exits_{SYM}_poorjev_relaxed + {SYM}_buy_hold (só segurar: 100% na moeda no início da janela, sem custos; é o B&H contra o qual os outros são medidos). Sem SOL e sem bot real neste run.
- Jev hospedado desligado (sem chave ou --no-jev): portfólios jev_* fora do catálogo.

## Dados

| Ativo | Fonte | Cobertura | Início | Fim | Retorno |
|---|---|---:|---:|---:|---:|
| SOL | coinbase:SOL-USD 1m | 99.83% | 82.18 | 120.32 | +46.41% |
| JUP | bybit:JUPUSDT 1m | 100.00% | 0.1591 | 0.3492 | +119.48% |
| JTO | bybit:JTOUSDT 1m | 100.00% | 0.277 | 0.575 | +107.58% |
| PYTH | bybit:PYTHUSDT 1m | 100.00% | 0.04412 | 0.08003 | +81.39% |
| RAY | okx:RAY-USDT 1m | 100.00% | 0.623 | 2.2048 | +253.90% |
| BOME | bybit:BOMEUSDT 1m | 100.00% | 0.0003887 | 0.0010107 | +160.02% |
| PENGU | bybit:PENGUUSDT 1m | 100.00% | 0.006348 | 0.009599 | +51.21% |
| TRUMP | bybit:TRUMPUSDT 1m | 100.00% | 2.918 | 2.026 | -30.57% |
| MOODENG | okx:MOODENG-USDT 1m | 100.00% | 0.04794 | 0.04639 | -3.23% |

## Modelos

| Modelo | Chamadas | Cache | Cobertura | conf P50 | conf P90 |
|---|---:|---:|---:|---:|---:|
| von | 144 | 296227 | 100.0% | 0.290 | 0.373 |
| poorjev | 132 | 296228 | 100.0% | 0.926 | 0.948 |

## Top 15 por habilidade (excesso ajustado à exposição)

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Meses > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | RAY_buy_hold | Meme · só segurar | +253.90 | +0.00 | **+980.46** | +0.00 (–) | -39.32 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 2 | RAY_poorjev_relaxed | Meme · poorjev | +252.54 | -13.60 | **+971.35** | +2.35 (0.36) | -39.24 | 20 (20/0) | 99.7 | 2/6 | inconclusiva |
| 3 | JUP_buy_hold | Meme · só segurar | +119.48 | +0.00 | **+166.86** | +0.00 (–) | -46.10 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 4 | BOME_buy_hold | Meme · só segurar | +160.02 | +0.00 | **+164.86** | +0.00 (–) | -52.66 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 5 | JUP_poorjev_relaxed | Meme · poorjev | +118.97 | -5.12 | **+164.55** | +3.22 (0.33) | -46.01 | 20 (20/0) | 99.7 | 2/6 | inconclusiva |
| 6 | BOME_poorjev_relaxed | Meme · poorjev | +158.65 | -13.74 | **+154.60** | -4.62 (0.72) | -52.58 | 20 (20/0) | 99.8 | 2/6 | inconclusiva |
| 7 | meme_JUP_baseline | Meme · von | +0.00 | -1194.85 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/6 | inconclusiva |
| 8 | meme_JTO_baseline | Meme · von | +0.00 | -1075.81 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 3/6 | inconclusiva |
| 9 | meme_PYTH_baseline | Meme · von | +0.00 | -813.92 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/6 | inconclusiva |
| 10 | meme_RAY_baseline | Meme · von | +0.00 | -2539.00 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/6 | inconclusiva |
| 11 | meme_BOME_baseline | Meme · von | +0.00 | -1600.21 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/6 | inconclusiva |
| 12 | meme_PENGU_baseline | Meme · von | +0.00 | -512.13 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 3/6 | inconclusiva |
| 13 | meme_TRUMP_baseline | Meme · von | +0.00 | +305.69 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 5/6 | inconclusiva |
| 14 | meme_MOODENG_baseline | Meme · von | +0.00 | +32.33 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/6 | inconclusiva |
| 15 | PYTH_buy_hold | Meme · só segurar | +81.39 | +0.00 | **-42.49** | +0.00 (–) | -52.38 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |

## Top 15 por PnL

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Meses > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | RAY_buy_hold | Meme · só segurar | +253.90 | +0.00 | **+980.46** | +0.00 (–) | -39.32 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 2 | RAY_poorjev_relaxed | Meme · poorjev | +252.54 | -13.60 | **+971.35** | +2.35 (0.36) | -39.24 | 20 (20/0) | 99.7 | 2/6 | inconclusiva |
| 3 | BOME_buy_hold | Meme · só segurar | +160.02 | +0.00 | **+164.86** | +0.00 (–) | -52.66 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 4 | BOME_poorjev_relaxed | Meme · poorjev | +158.65 | -13.74 | **+154.60** | -4.62 (0.72) | -52.58 | 20 (20/0) | 99.8 | 2/6 | inconclusiva |
| 5 | JUP_buy_hold | Meme · só segurar | +119.48 | +0.00 | **+166.86** | +0.00 (–) | -46.10 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 6 | JUP_poorjev_relaxed | Meme · poorjev | +118.97 | -5.12 | **+164.55** | +3.22 (0.33) | -46.01 | 20 (20/0) | 99.7 | 2/6 | inconclusiva |
| 7 | h1_exits_RAY_poorjev_relaxed | Meme · hipóteses (lab) | +108.26 | -1456.44 | **-395.67** | -251.92 (0.95) | -48.45 | 4687 (4447/240) | 94.8 | 1/6 | perdedora |
| 8 | JTO_buy_hold | Meme · só segurar | +107.58 | +0.00 | **-66.23** | +0.00 (–) | -54.27 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 9 | JTO_poorjev_relaxed | Meme · poorjev | +106.55 | -10.31 | **-74.22** | -7.96 (0.79) | -54.21 | 20 (20/0) | 99.8 | 3/6 | inconclusiva |
| 10 | PYTH_buy_hold | Meme · só segurar | +81.39 | +0.00 | **-42.49** | +0.00 (–) | -52.38 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 11 | PYTH_poorjev_relaxed | Meme · poorjev | +79.05 | -23.38 | **-62.98** | -12.97 (0.91) | -52.27 | 20 (20/0) | 99.7 | 2/6 | inconclusiva |
| 12 | PENGU_buy_hold | Meme · só segurar | +51.21 | +0.00 | **-143.03** | +0.00 (–) | -52.10 | 0 (0/0) | 100.0 | 0/6 | inconclusiva |
| 13 | PENGU_poorjev_relaxed | Meme · poorjev | +50.52 | -6.96 | **-148.04** | -4.92 (0.75) | -52.01 | 20 (20/0) | 99.7 | 3/6 | inconclusiva |
| 14 | h1_exits_JUP_poorjev_relaxed | Meme · hipóteses (lab) | +0.05 | -1194.35 | **-978.33** | +122.77 (0.16) | -53.03 | 4379 (4160/219) | 95.2 | 1/6 | perdedora |
| 15 | meme_JUP_baseline | Meme · von | +0.00 | -1194.85 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/6 | inconclusiva |

⚠ = fork ou hipótese desenhada com dados do run ao vivo que se sobrepõem ao fim desta janela (ver Cuidados).

## Famílias

| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor | Pior |
|---|---:|---:|---:|---:|---|---|
| Meme · hipóteses (lab) | 8 | -56.88 | -1136.90 | 0/8 | h1_exits_RAY_poorjev_relaxed | h1_exits_MOODENG_poorjev_relaxed |
| Meme · poorjev | 8 | +92.80 | -68.60 | 0/8 | RAY_poorjev_relaxed | TRUMP_poorjev_relaxed |
| Meme · só segurar | 8 | +94.49 | -54.36 | 0/8 | RAY_buy_hold | TRUMP_buy_hold |
| Meme · von | 16 | -9.66 | -105.65 | 2/16 | meme_MOODENG_baseline | meme_MOODENG_relaxed |

## Vereditos

- vencedoras: 0, perdedoras: 7, inconclusivas: 33.
- Regra: a do run ao vivo (`bot/analytics.verdict`), com a janela de 180 dias a cumprir os dias mínimos; continua a exigir ≥ 30 round trips fechados. Consistência mensal em vez de semanal: excesso vs B&H positivo em ≥ 4 de 6 blocos de 30 dias; séries e bootstrap em grelha de 1 h (blocos de 12 h).

## Cuidados

- **Sem look-ahead nos forks:** esta janela acaba antes de 2026-10-01; os forks desenhados pela revisão noturna com os dias 2026-10-01 → 2026-10-06 estão aqui totalmente fora da amostra.
- Os parâmetros do relaxed (conf ≥ 0,35, margem ≥ 0,20) foram calibrados nas primeiras decisões do von no início de setembro de 2026 e o v2 usa critérios reescritos em 2026-09-24; janelas que incluem esses dias têm essa parte dentro da amostra.
- Estados: SOL a partir de uma grelha de 10 s da Binance (o histórico ao vivo tem ~1 marca a cada 10,4 s); memecoins a partir de fechos de 1 m; palavras de profundidade/taxas constantes (como ao vivo). Pequenas diferenças de amostragem mudam algumas palavras de movimento/volatilidade.
- Fills: cotação sintética = marca do minuto ± custo mediano por ativo medido nos fills reais do run ao vivo; as variantes `_full` (100% do saldo) podem ter mais impacto do que o estimado.
- Decisão a cada 60 s (ao vivo: SOL a cada ~15 s, memecoins a cada ~7 min por moeda, lab a cada 15 s); o bot real a cada 15 s.
