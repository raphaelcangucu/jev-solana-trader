# Funding-carry PAPER — relatório cumulativo

Gerado: 2026-09-26T03:12:05-03:00 (BRT) · início: 2026-09-24T20:50:01-03:00 · modo: indefinido (sem data de fim) · dias decorridos: 1.27

**Somente paper.** Preços/funding reais da API pública Hyperliquid (+ Gate spot para hedge onde HL não tem spot). Fills simulados como *taker* andando o book real; maker só como contrafactual.


## Resumo por portfólio

| Portfólio | Capital | NAV (mark) | Ret % | APR simples % | vs barra 6% (US$) | Kamino USDC (US$) | JitoSOL yield (US$) | Max DD % |
|---|---|---|---|---|---|---|---|---|
| p1000 | 1000 | 994.9005 | -0.510 | -147.10 | -5.3015 | 1,000.0457 | 999.9993 | 0.160 |
| p1000_pons | 1000 | 994.9636 | -0.504 | -145.28 | -5.2384 | 1,000.0457 | 999.9993 | 0.148 |

> APR simples em janelas curtas (< 7 dias) é muito ruidoso: custos de entrada (bridge, taxa de conta, taxas de trade) pesam primeiro; funding acumula depois.


## Decomposição de PnL (US$)

| Portfólio | Funding recebido | Taxas trade (taker) | Taxas se maker (contrafactual) | Custos únicos (bridge+conta) | Basis realizado (spot+perp) | Basis não-realizado | Saída estimada (withdraw $1 + bridge volta + taxas close) |
|---|---|---|---|---|---|---|---|
| p1000 | 0.7005 | -1.1750 | -0.9131 | -4.5858 | 0.0000 | -0.0393 | -4.8679 |
| p1000_pons | 0.7268 | -1.1949 | -0.9406 | -4.5858 | 0.0000 | 0.0174 | -4.8843 |

NAV se sacar agora = NAV − saída estimada. O bridge de volta usa cotação LI.FI do início (`state.oneoff_quotes`).


## Posições abertas

| Portfólio | Ativo | Hedge | Tamanho | Spot mid | Perp mark | Funding acumulado | Funding atual (ann %) | uPnL spot | uPnL perp |
|---|---|---|---|---|---|---|---|---|---|
| p1000 | GRASS | gate | 205.2 | 0.524924 | 0.526250 | 0.37166 | 183.87 | 17.7566 | -17.9981 |
| p1000 | TAO | gate | 0.304 | 310.424479 | 310.702000 | 0.09169 | 10.95 | 4.5352 | -4.5758 |
| p1000 | ONDO | gate | 171.0 | 0.544223 | 0.544580 | 0.08806 | 10.95 | 3.4463 | -3.3858 |
| p1000 | UNI | gate | 9.8 | 9.799010 | 9.810900 | 0.06091 | 11.59 | 6.4317 | -6.4621 |
| p1000 | ZEC | hl_spot | 0.05 | 1,537.150000 | 1,537.000000 | 0.03318 | 10.95 | -0.4975 | 0.6350 |
| p1000 | ETH | hl_spot | 0.0334 | 2,686.950000 | 2,686.710000 | 0.03482 | 10.95 | -0.0718 | 0.0999 |
| p1000 | BTC | hl_spot | 0.00106 | 83,925.500000 | 83,894.000000 | 0.02017 | 7.04 | -0.5782 | 0.6254 |
| p1000_pons | GRASS | gate | 179.5 | 0.524924 | 0.526250 | 0.32511 | 183.87 | 15.5507 | -15.7404 |
| p1000_pons | PONS | gate | 102.0 | 0.641618 | 0.642350 | 0.10937 | 10.95 | 2.7205 | -2.6999 |
| p1000_pons | TAO | gate | 0.266 | 310.424479 | 310.702000 | 0.08023 | 10.95 | 3.9257 | -3.9719 |
| p1000_pons | ONDO | gate | 150.0 | 0.544223 | 0.544580 | 0.07724 | 10.95 | 2.9028 | -2.8305 |
| p1000_pons | UNI | gate | 8.6 | 9.799010 | 9.810900 | 0.05345 | 11.59 | 5.6183 | -5.6514 |
| p1000_pons | ZEC | hl_spot | 0.05 | 1,537.150000 | 1,537.000000 | 0.03318 | 10.95 | -0.5125 | 0.6400 |
| p1000_pons | ETH | hl_spot | 0.0293 | 2,686.950000 | 2,686.710000 | 0.03054 | 10.95 | -0.0630 | 0.0876 |
| p1000_pons | BTC | hl_spot | 0.00093 | 83,925.500000 | 83,894.000000 | 0.01770 | 7.04 | -0.5073 | 0.5487 |

## Saídas / flips / risco

| Portfólio | Trades | Accruals | Saídas por flip/negativo | Saídas abaixo da barra | Margin top-ups | Liquidações (proxy) |
|---|---|---|---|---|---|---|
| p1000 | 14 | 207 | 0 | 0 | 2 | 0 |
| p1000_pons | 16 | 238 | 0 | 0 | 2 | 0 |

Flips de sinal no funding liquidado desde o início (por ativo): BTC=0, ETH=0, GRASS=0, ONDO=0, PONS=0, TAO=0, UNI=0, ZEC=0


## Benchmarks (APY usado)

- **kamino_usdc**: APY 5.928% · fonte api.kamino.finance reserves/metrics + metrics/history · polled 2026-09-25T20:49:38-03:00 · ok
- **jitosol**: APY 4.770% · fonte kobe.mainnet.jito.network stake_pool_stats apy[-1] · polled 2026-09-25T20:49:38-03:00 · ok

## Caveats

- p52 limitado a BTC/ETH/ZEC (existe spot na HL → venue único). Mínimo de $10 por ordem na HL limita a ~2 posições.
- p1000*: GRASS/ONDO/UNI/TAO/PONS usam spot da **Gate** (preço USDT convertido por USDC_USDT da Gate). Custo de mover fundos para a Gate **não modelado**.
- Funding: `size × oracle × fundingRate` (docs HL), taxa liquidada de `fundingHistory`; oracle do poll de hh:00:15 (se não houver poll em ±5 min, proxy = candle 1m do perp, marcado no log).
- JitoSOL: só o yield sobre valor em US$ (sem beta de preço do SOL).
- Logs: rotação diária → `logs/archive/YYYY-MM/<nome>.<data>.gz` (verificado antes de truncar). Relatórios diários antigos ficam em `reports/`.
- Contadores HTTP (429 etc.): {'http_429_hl': 1054, 'http_429_jupiter': 24}
