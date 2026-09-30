# START — funding-carry PAPER

- **Início (portfólios criados, posições abertas):** 2026-09-24T20:50:01-03:00 (BRT, America/Sao_Paulo)
- **Modo:** indefinido — sem data de fim. Portfólios nunca são desativados de forma definitiva; só há rotação entre ativos pelas regras (saída por flips/abaixo da barra 6%, reentrada após cooldown de 24h).
- **PAPER ONLY:** nenhuma conta, depósito, ordem ou chave. Só endpoints públicos de leitura (Hyperliquid info, Gate spot público, LI.FI/Jupiter quotes, Kamino, Jito kobe).

## Custos únicos simulados (cotações reais no início)
| Capital | Bridge Solana USDT → HyperCore USDC (LI.FI) | Taxa conta nova HL | Saída estimada: withdraw HL $1 + LI.FI ARB USDC→SOL USDT | Custo entrada benchmark (USDT→USDC) |
|---|---|---|---|---|
| $52 | 0.2410 (relaydepository, 2026-09-24T20:49:27-03:00) | 1.00 (docs HL) | 1.00 + 0.1750 | 0.1479 (lifi (includes LI.FI 0.25% fee; jupiter unavailable)) |
| $1000 | 3.5858 (mayan, 2026-09-24T20:49:45-03:00) | 1.00 (docs HL) | 1.00 + 2.6154 | 2.7383 (lifi (includes LI.FI 0.25% fee; jupiter unavailable)) |

## Benchmarks no início
- Kamino USDC supply: **6.260%** (mean of last 24 hourly supplyInterestAPY (metrics/history); spot agora 21.86%, faixa 24h 4.61–27.10%) — polled 2026-09-24T20:49:26-03:00
- JitoSOL: **4.770%** (kobe.mainnet.jito.network stake_pool_stats apy[-1], data 2026-09-24T23:11:44Z) — polled 2026-09-24T20:49:26-03:00

## Posições abertas no início
| Portfólio | Ativo | Hedge spot | Tamanho | Nocional perp US$ | Spot @ | Perp short @ | Funding média 7d (ann %) | Funding atual (ann %) | Aberto |
|---|---|---|---|---|---|---|---|---|---|
| p52 | ZEC | hl_spot (@272) | 0.01 | 15.49 | 1547 | 1549.4 | 16.74 | 10.95 | 2026-09-24T20:50:03-03:00 |
| p52 | ETH | hl_spot (@151) | 0.0059 | 15.87 | 2688.7 | 2689.7 | 12.38 | 10.95 | 2026-09-24T20:50:06-03:00 |
| p1000 | GRASS | gate (GRASS_USDT) | 205.2 | 89.99 | 0.43839 | 0.43854 | 41.56 | 95.72 | 2026-09-24T20:50:07-03:00 |
| p1000 | TAO | gate (TAO_USDT) | 0.304 | 89.88 | 295.506 | 295.65 | 37.04 | 10.95 | 2026-09-24T20:50:08-03:00 |
| p1000 | ONDO | gate (ONDO_USDT) | 171.0 | 89.74 | 0.524069 | 0.52478 | 34.77 | 55.20 | 2026-09-24T20:50:10-03:00 |
| p1000 | UNI | gate (UNI_USDT) | 9.8 | 89.68 | 9.14271 | 9.1515 | 27.73 | 10.95 | 2026-09-24T20:50:11-03:00 |
| p1000 | ZEC | hl_spot (@272) | 0.05 | 77.49 | 1547.1 | 1549.7 | 16.74 | 10.95 | 2026-09-24T20:50:13-03:00 |
| p1000 | ETH | hl_spot (@151) | 0.0334 | 89.84 | 2689.1 | 2689.7 | 12.38 | 10.95 | 2026-09-24T20:50:16-03:00 |
| p1000_pons | GRASS | gate (GRASS_USDT) | 179.5 | 78.72 | 0.43829 | 0.43856 | 41.56 | 95.72 | 2026-09-24T20:50:17-03:00 |
| p1000_pons | PONS | gate (PONS_USDT) | 102.0 | 62.82 | 0.614946 | 0.61588 | 40.48 | 36.31 | 2026-09-24T20:50:18-03:00 |
| p1000_pons | TAO | gate (TAO_USDT) | 0.266 | 78.67 | 295.666 | 295.77 | 37.04 | 10.95 | 2026-09-24T20:50:20-03:00 |
| p1000_pons | ONDO | gate (ONDO_USDT) | 150.0 | 78.86 | 0.524871 | 0.52571 | 34.77 | 55.20 | 2026-09-24T20:50:21-03:00 |
| p1000_pons | UNI | gate (UNI_USDT) | 8.6 | 78.72 | 9.14571 | 9.15376 | 27.73 | 10.95 | 2026-09-24T20:50:22-03:00 |
| p1000_pons | ZEC | hl_spot (@272) | 0.05 | 77.49 | 1547.4 | 1549.8 | 16.74 | 10.95 | 2026-09-24T20:50:24-03:00 |
| p1000_pons | ETH | hl_spot (@151) | 0.0293 | 78.81 | 2689.1 | 2689.7 | 12.38 | 10.95 | 2026-09-24T20:50:27-03:00 |

BTC não entrou: 4 flips de sinal nas últimas 24h (regra `entry_max_flips_24h=1`).
