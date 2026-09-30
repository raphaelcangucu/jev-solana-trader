# Portfólios de hipótese (lab) — horários de início (BRT)

Paper only. Rodam em `bot/lab_bot.py` reaproveitando as decisões já logadas (sem chamadas extras aos modelos).
SOL começa com 0.334150878 SOL + 960.812456 USDT (≈ $1000.0); memes com 1000.0 USDT.

Parâmetros iniciais:
- H1 saídas memes: TP +6%, SL −4%, trailing 3% (arma após +3%), reentrada bloqueada 30 min.
- H1 saídas SOL (von relaxed): TP +2.5%, SL −1.5%, trailing 1.0% (arma após +1.0%).
- H2 ensemble: percentil da confiança de cada modelo na janela móvel própria (SOL 480 decisões ≈ 2 h; memes 200 por modelo, todas as moedas), ≥2 modelos concordando e percentil médio ≥ 0.80; mínimo 100 amostras na janela.
- H3 limite: preço mid ∓ 10 bps, validade 15 min, preenche só se o mark cruzar o limite (estritamente); taxa assumida 10 bps + taxa de rede, sem slippage.
- H4 horários BRT permitidos: [5, 10, 11, 12, 18] (compras e vendas).

- **h1_exits_von_relaxed** iniciado 2026-09-24T21:07:46.563555-03:00
- **h1_exits_BONK_poorjev_relaxed** iniciado 2026-09-24T21:07:46.563942-03:00
- **h1_exits_WIF_poorjev_relaxed** iniciado 2026-09-24T21:07:46.564213-03:00
- **h1_exits_POPCAT_poorjev_relaxed** iniciado 2026-09-24T21:07:46.564440-03:00
- **h1_exits_FARTCOIN_poorjev_relaxed** iniciado 2026-09-24T21:07:46.564653-03:00
- **h1_exits_PNUT_poorjev_relaxed** iniciado 2026-09-24T21:07:46.564847-03:00
- **h1_exits_MEW_poorjev_relaxed** iniciado 2026-09-24T21:07:46.565071-03:00
- **h1_exits_GOAT_poorjev_relaxed** iniciado 2026-09-24T21:07:46.565258-03:00
- **h2_ensemble_sol** iniciado 2026-09-24T21:07:46.565432-03:00
- **h2_ensemble_BONK** iniciado 2026-09-24T21:07:46.565733-03:00
- **h2_ensemble_WIF** iniciado 2026-09-24T21:07:46.565961-03:00
- **h2_ensemble_POPCAT** iniciado 2026-09-24T21:07:46.566307-03:00
- **h2_ensemble_FARTCOIN** iniciado 2026-09-24T21:07:46.566672-03:00
- **h2_ensemble_PNUT** iniciado 2026-09-24T21:07:46.567012-03:00
- **h2_ensemble_MEW** iniciado 2026-09-24T21:07:46.567320-03:00
- **h2_ensemble_GOAT** iniciado 2026-09-24T21:07:46.567672-03:00
- **h3_limit_poorjev_relaxed** iniciado 2026-09-24T21:07:46.567919-03:00
- **h3_limit_hybrid_von_cap2** iniciado 2026-09-24T21:07:46.568169-03:00
- **h4_hours_poorjev_relaxed** iniciado 2026-09-24T21:07:46.568400-03:00
- **h4_hours_von_relaxed** iniciado 2026-09-24T21:07:46.568631-03:00
