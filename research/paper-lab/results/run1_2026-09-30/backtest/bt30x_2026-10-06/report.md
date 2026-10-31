# Simulação retroativa de 30 dias — bt30x_2026-10-06

**Gerado (BRT):** 2026-10-17T20:45:41-03:00 · **Janela:** 2026-09-06T09:00:00-03:00 → 2026-10-06T09:00:00-03:00 · passo de decisão 60 s · paper only (nenhuma ordem real, nenhuma chave).

## Vencedor

Em 30 dias simulados, a maior habilidade (excesso ajustado à exposição) foi de RAY_poorjev_relaxed (+51.51 US$, PnL +83.24%, 20 trades, todas compras: uma entrada concentrada num recuo, não seleção repetida), e o maior PnL foi de RAY_poorjev_relaxed (+83.24%, -76.06 US$ contra o buy & hold do mesmo ativo). Nenhum portfólio passa a regra do veredito (bater B&H e a barra USDC com p<0,05 e consistência em ≥3 de 4 semanas): 35 inconclusivos e 5 perdedores. É um resultado retroativo com estados e custos aproximados; serve para ordenar hipóteses, não para provar uma vencedora.

- Por habilidade: **RAY_poorjev_relaxed** · por PnL: **RAY_poorjev_relaxed** · pelo veredito: **nenhum**

## Método

Para cada portfólio do catálogo atual do run ao vivo (originais SOL e memecoins, regras, híbridos, hipóteses H1–H4 e EXP, forks de parâmetros e de critérios, Jev, Laya, poorjev) e para os livros A e B do bot real, o backtest repete 30 dias minuto a minuto com o MESMO código dos bots ao vivo (portões, cooldown, trades/h, fração de compra, teto de exposição, saídas TP/SL/trailing e reentrada, horas, ensemble por percentil, filtro de regime, ordens limite, regras em barras de 1 h), trocando só o relógio, os ficheiros e as cotações (backtest/simenv.py). Os modelos (von, Laya, poorjev; Jev hospedado nos portfólios SOL) respondem a cada estado de 12 adjetivos reconstruído do histórico; cada par (critérios, estado) é chamado uma vez e guardado em cache.

**Âmbito deste run (`moedas_novas`):** só as moedas JUP, JTO, PYTH, RAY, BOME, PENGU, TRUMP, MOODENG (fora do run ao vivo; overlay só do backtest, backtest/assets_extra.json), com os portfólios listados nos Pressupostos e o "só segurar" de cada moeda. Sem portfólios SOL, sem bot real e sem validação contra o run ao vivo (estas moedas não têm decisões ao vivo).

## Pressupostos

- Janela 30 dias até 2026-10-06T09:00:00-03:00 (BRT); decisão a cada 60 s; memecoins em rotação (uma moeda por minuto, cada moeda decide a cada 7 min, como o meme_bot); bot real a cada 15 s.
- Capital: portfólios SOL com US$ 1000 na mistura do config.json (0.039188 em SOL ao preço do início da janela); memecoins com 1000.0 USDT; bot real com 0.017392206 SOL + 50.00929 USDT. Forks e hipóteses começam com o capital da família no início da janela (não com o estado do pai).
- Parâmetros: params.json + registry + overlay do run ao vivo (instantâneo em inputs/, copiado do run bt30_2026-10-06 para manter o MESMO catálogo e os mesmos pressupostos), resolvidos por bot/params.py; nenhuma pausa do dashboard é aplicada.
- Estado: palavras deep/quiet (profundidade/taxas) constantes, como em todas as decisões registadas ao vivo (as marcas Coinbase/Gate.io têm impacto 0). SOL: grelha de 10 s da Binance (ao vivo ~1 marca/10,4 s, sol_bot + rules_bot); memecoins: fecho de 1 m (ao vivo ~1 marca/60 s). Bot real: 16 fechos de 1 m da Binance; spread/profundidade/taxas e inventário (carteira) constantes em tight/deep/quiet/sold, como em >99,9% dos ciclos ao vivo.
- Preços: SOL Coinbase 1 m (fonte da marcação ao vivo); memecoins Bybit/KuCoin 1 m escolhidas pela correlação com a Gate.io (fonte ao vivo, só ~7 dias de 1 m disponíveis). Lacunas ≤ 5 min preenchidas com o último fecho.
- Fills: cotação sintética = marca × (1 ± custo por ativo), com o custo mediano dos fills reais (Jupiter/Raydium) do run ao vivo (os mesmos valores do bt30_2026-10-06) menos o extra de 5 bps que o código soma: SOL 2.4 bps, JUP 12.7 bps, JTO 12.7 bps, PYTH 32.8 bps, RAY 12.7 bps, BOME 12.7 bps, PENGU 12.7 bps, TRUMP 12.7 bps, MOODENG 32.8 bps; taxa de rede 5e-6 SOL. Bot real: 10 bps (paper_cost_bps).
- Ordens limite (H3): enchem quando a mínima (compra) ou máxima (venda) do minuto cruza o limite; saídas TP/SL/trailing avaliadas no fecho de cada minuto (ao vivo: na marca de cada ciclo).
- Regras: barras de 1 h da Coinbase (SOL) e Gate.io (memes), os mesmos fetchers do rules_bot; agem no primeiro passo depois do fecho da barra. Regime de SOL dos híbridos = EMA12 > EMA26 na última barra fechada.
- Modelos: servidores próprios (portas 8865–8867, mesmos venvs/comandos do lab); cada par (critérios, estado) chamado uma vez e guardado em cache; falha → hold (fail-closed). Ensemble H2: janelas de percentil com o mesmo número de decisões que ao vivo (480 SOL / 200 memes), que a 60 s cobrem um período ~4× maior no SOL.
- Veredito: regra do run ao vivo (≥30 round trips fechados; dias cumpridos pela janela; bate B&H com p<0,05 por block-bootstrap, PnL acima da barra de 6%/a USDC, excesso positivo em ≥3 de 4 semanas). Semanas = 4 blocos de 7 dias contados do fim da janela.
- Look-ahead: forks criados a partir de 2026-10-03 usaram dados de 2026-10-01 a 2026-10-06 (fim desta janela).
- Moedas novas (só backtest, backtest/assets_extra.json; o memecoins.json do lab não muda): JUP, JTO, PYTH, RAY, BOME, PENGU, TRUMP, MOODENG. Mesmos parâmetros das famílias meme (params.json + overlay do instantâneo, resolvidos com asset=<SYM>; nenhuma camada por moeda), mesmo capital e o mesmo estado partilhado a partir de meme_<SYM>_baseline. Rotação com cadência de 7 min por moeda (a das 7 memecoins ao vivo). Fontes de 1 m escolhidas pela cobertura e pela correlação com a Gate.io (fonte da marcação ao vivo): como a Gate.io só guarda ~7 dias de 1 m (depois do fim da janela), a correlação usada é a dos retornos de 1 h com as barras de 1 h da Gate.io dentro da janela. Custos sem fills ao vivo: Sem fills ao vivo destas moedas. Custo sobre a marca (antes do extra de 5 bps que o código soma) = mediana do custo medido nas 7 memecoins atuais (bt30_2026-10-06: BONK 1,4 · FARTCOIN 5,8 · WIF 8,5 · POPCAT 12,7 · MEW 24,3 · GOAT 29,8 · PNUT 32,8 → 12,7 bps). Moedas com liquidez on-chain (DexScreener, soma dos pares Solana; a API devolve no máximo 30 pares, por isso é um limite inferior) abaixo da da PNUT (~3,1 M US$, a mais cara das atuais) ficam com o custo da PNUT, 32,8 bps (conservador): PYTH e MOODENG.
- Portfólios por moeda: meme_{SYM}_baseline, meme_{SYM}_relaxed, {SYM}_poorjev_relaxed, h1_exits_{SYM}_poorjev_relaxed + {SYM}_buy_hold (só segurar: 100% na moeda no início da janela, sem custos; é o B&H contra o qual os outros são medidos). Sem SOL e sem bot real neste run.
- Jev hospedado desligado (sem chave ou --no-jev): portfólios jev_* fora do catálogo.

## Dados

| Ativo | Fonte | Cobertura | Início | Fim | Retorno |
|---|---|---:|---:|---:|---:|
| SOL | coinbase:SOL-USD 1m | 100.00% | 106.46 | 120.32 | +13.02% |
| JUP | bybit:JUPUSDT 1m | 100.00% | 0.2711 | 0.3492 | +28.81% |
| JTO | bybit:JTOUSDT 1m | 100.00% | 0.456 | 0.575 | +26.10% |
| PYTH | bybit:PYTHUSDT 1m | 100.00% | 0.05573 | 0.08003 | +43.60% |
| RAY | okx:RAY-USDT 1m | 100.00% | 1.1553 | 2.2048 | +90.84% |
| BOME | bybit:BOMEUSDT 1m | 100.00% | 0.0009246 | 0.0010107 | +9.31% |
| PENGU | bybit:PENGUUSDT 1m | 100.00% | 0.008826 | 0.009599 | +8.76% |
| TRUMP | bybit:TRUMPUSDT 1m | 100.00% | 2.361 | 2.026 | -14.19% |
| MOODENG | okx:MOODENG-USDT 1m | 100.00% | 0.04453 | 0.04639 | +4.18% |

## Modelos

| Modelo | Chamadas | Cache | Cobertura | conf P50 | conf P90 |
|---|---:|---:|---:|---:|---:|
| von | 8 | 49371 | 100.0% | 0.287 | 0.371 |
| poorjev | 8 | 49371 | 100.0% | 0.928 | 0.950 |

## Top 15 por habilidade (excesso ajustado à exposição)

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Semanas > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | RAY_buy_hold | Meme · só segurar | +90.84 | +0.00 | **+125.32** | +0.00 (–) | -30.85 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |
| 2 | RAY_poorjev_relaxed | Meme · poorjev | +83.24 | -76.06 | **+51.51** | -46.64 (1.00) | -30.78 | 20 (20/0) | 99.7 | 0/4 | inconclusiva |
| 3 | PYTH_buy_hold | Meme · só segurar | +43.60 | +0.00 | **+13.96** | +0.00 (–) | -16.50 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |
| 4 | PYTH_poorjev_relaxed | Meme · poorjev | +43.04 | -5.66 | **+9.73** | +1.38 (0.38) | -16.46 | 20 (20/0) | 99.7 | 0/4 | inconclusiva |
| 5 | meme_JUP_baseline | Meme · von | +0.00 | -288.09 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 1/4 | inconclusiva |
| 6 | meme_JTO_baseline | Meme · von | +0.00 | -260.96 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 0/4 | inconclusiva |
| 7 | meme_PYTH_baseline | Meme · von | +0.00 | -436.03 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 0/4 | inconclusiva |
| 8 | meme_RAY_baseline | Meme · von | +0.00 | -908.42 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 0/4 | inconclusiva |
| 9 | meme_BOME_baseline | Meme · von | +0.00 | -93.12 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/4 | inconclusiva |
| 10 | meme_PENGU_baseline | Meme · von | +0.00 | -87.58 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/4 | inconclusiva |
| 11 | meme_TRUMP_baseline | Meme · von | +0.00 | +141.89 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 3/4 | inconclusiva |
| 12 | meme_MOODENG_baseline | Meme · von | +0.00 | -41.77 | **+0.00** | +0.00 (–) | 0.00 | 0 (0/0) | 0.0 | 2/4 | inconclusiva |
| 13 | meme_RAY_relaxed | Meme · von | -0.09 | -909.29 | **-3.37** | +7.35 (0.30) | -0.94 | 27 (15/12) | 0.3 | 0/4 | inconclusiva |
| 14 | meme_JTO_relaxed | Meme · von | -2.07 | -281.62 | **-23.79** | +3.57 (0.42) | -2.54 | 69 (40/29) | 1.1 | 0/4 | inconclusiva |
| 15 | JUP_buy_hold | Meme · só segurar | +28.81 | +0.00 | **-25.37** | +0.00 (–) | -25.20 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |

## Top 15 por PnL

| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | Semanas > B&H | Veredito |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| 1 | RAY_buy_hold | Meme · só segurar | +90.84 | +0.00 | **+125.32** | +0.00 (–) | -30.85 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |
| 2 | RAY_poorjev_relaxed | Meme · poorjev | +83.24 | -76.06 | **+51.51** | -46.64 (1.00) | -30.78 | 20 (20/0) | 99.7 | 0/4 | inconclusiva |
| 3 | h1_exits_RAY_poorjev_relaxed | Meme · hipóteses (lab) | +51.75 | -390.92 | **-158.24** | +264.08 (0.05) | -31.74 | 2024 (1916/108) | 86.3 | 0/4 | inconclusiva |
| 4 | PYTH_buy_hold | Meme · só segurar | +43.60 | +0.00 | **+13.96** | +0.00 (–) | -16.50 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |
| 5 | PYTH_poorjev_relaxed | Meme · poorjev | +43.04 | -5.66 | **+9.73** | +1.38 (0.38) | -16.46 | 20 (20/0) | 99.7 | 0/4 | inconclusiva |
| 6 | JUP_buy_hold | Meme · só segurar | +28.81 | +0.00 | **-25.37** | +0.00 (–) | -25.20 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |
| 7 | JUP_poorjev_relaxed | Meme · poorjev | +28.65 | -1.57 | **-25.75** | +2.85 (0.30) | -25.12 | 20 (20/0) | 99.6 | 1/4 | inconclusiva |
| 8 | JTO_buy_hold | Meme · só segurar | +26.10 | +0.00 | **-28.10** | +0.00 (–) | -22.72 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |
| 9 | JTO_poorjev_relaxed | Meme · poorjev | +26.02 | -0.80 | **-27.88** | +2.68 (0.29) | -22.67 | 20 (20/0) | 99.6 | 0/4 | inconclusiva |
| 10 | BOME_poorjev_relaxed | Meme · poorjev | +9.34 | +0.27 | **-47.10** | +2.91 (0.25) | -23.84 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 11 | BOME_buy_hold | Meme · só segurar | +9.31 | +0.00 | **-47.89** | +0.00 (–) | -23.89 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |
| 12 | PENGU_buy_hold | Meme · só segurar | +8.76 | +0.00 | **-51.65** | +0.00 (–) | -25.28 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |
| 13 | PENGU_poorjev_relaxed | Meme · poorjev | +8.58 | -1.75 | **-52.85** | +0.08 (0.49) | -25.20 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 14 | MOODENG_poorjev_relaxed | Meme · poorjev | +4.49 | +3.09 | **-45.40** | +7.27 (0.09) | -19.96 | 20 (20/0) | 99.6 | 2/4 | inconclusiva |
| 15 | MOODENG_buy_hold | Meme · só segurar | +4.18 | +0.00 | **-48.84** | +0.00 (–) | -20.02 | 0 (0/0) | 100.0 | 0/4 | inconclusiva |

⚠ = fork ou hipótese desenhada com dados do run ao vivo que se sobrepõem ao fim desta janela (ver Cuidados).

## Famílias

| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor | Pior |
|---|---:|---:|---:|---:|---|---|
| Meme · hipóteses (lab) | 8 | -5.53 | -269.53 | 0/8 | h1_exits_RAY_poorjev_relaxed | h1_exits_MOODENG_poorjev_relaxed |
| Meme · poorjev | 8 | +17.68 | -28.16 | 3/8 | RAY_poorjev_relaxed | TRUMP_poorjev_relaxed |
| Meme · só segurar | 8 | +17.70 | -28.80 | 0/8 | RAY_buy_hold | TRUMP_buy_hold |
| Meme · von | 16 | -0.04 | -1.69 | 2/16 | meme_MOODENG_baseline | meme_MOODENG_relaxed |

## Vereditos

- vencedoras: 0, perdedoras: 5, inconclusivas: 35.
- Regra: a do run ao vivo (`bot/analytics.verdict`), com a janela de 30 dias a cumprir os dias mínimos; continua a exigir ≥ 30 round trips fechados.

## Cuidados

- **Sem look-ahead nos forks:** esta janela acaba antes de 2026-10-01; os forks desenhados pela revisão noturna com os dias 2026-10-01 → 2026-10-06 estão aqui totalmente fora da amostra.
- Os parâmetros do relaxed (conf ≥ 0,35, margem ≥ 0,20) foram calibrados nas primeiras decisões do von no início de setembro de 2026 e o v2 usa critérios reescritos em 2026-09-24; janelas que incluem esses dias têm essa parte dentro da amostra.
- Estados: SOL a partir de uma grelha de 10 s da Binance (o histórico ao vivo tem ~1 marca a cada 10,4 s); memecoins a partir de fechos de 1 m; palavras de profundidade/taxas constantes (como ao vivo). Pequenas diferenças de amostragem mudam algumas palavras de movimento/volatilidade.
- Fills: cotação sintética = marca do minuto ± custo mediano por ativo medido nos fills reais do run ao vivo; as variantes `_full` (100% do saldo) podem ter mais impacto do que o estimado.
- Decisão a cada 60 s (ao vivo: SOL a cada ~15 s, memecoins a cada ~7 min por moeda, lab a cada 15 s); o bot real a cada 15 s.
