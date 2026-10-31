# Portfólios de hipótese (lab) — horários de início (BRT)

Paper only. Rodam em `bot/lab_bot.py` reaproveitando as decisões já logadas (sem chamadas extras aos modelos).
SOL começa com 0.334150878 SOL + 960.812456 USDT (≈ $1000.0); memes com 1000.0 USDT.

Parâmetros iniciais:
- H1 saídas memes: TP +6%, SL −4%, trailing 3% (arma após +3%), reentrada bloqueada 30 min.
- H1 saídas SOL (von relaxed): TP +2.5%, SL −1.5%, trailing 1.0% (arma após +1.0%).
- H2 ensemble: percentil da confiança de cada modelo na janela móvel própria (SOL 480 decisões ≈ 2 h; memes 200 por modelo, todas as moedas), ≥2 modelos concordando e percentil médio ≥ 0.80; mínimo 100 amostras na janela.
- H3 limite: preço mid ∓ 10 bps, validade 15 min, preenche só se o mark cruzar o limite (estritamente); taxa assumida 10 bps + taxa de rede, sem slippage.
- H4 horários BRT permitidos: [5, 10, 11, 12, 18] (compras e vendas).

- **h1_exits_GOAT_poorjev_relaxed** iniciado 2026-10-01T22:24:24.178492-03:00
- **h2_ensemble_sol** iniciado 2026-10-01T22:24:24.178940-03:00
- **h2_ensemble_BONK** iniciado 2026-10-01T22:24:24.179192-03:00
- **h2_ensemble_WIF** iniciado 2026-10-01T22:24:24.179403-03:00
- **h2_ensemble_POPCAT** iniciado 2026-10-01T22:24:24.179735-03:00
- **h2_ensemble_FARTCOIN** iniciado 2026-10-01T22:24:24.179958-03:00
- **h2_ensemble_PNUT** iniciado 2026-10-01T22:24:24.180134-03:00
- **h2_ensemble_MEW** iniciado 2026-10-01T22:24:24.180328-03:00
- **h2_ensemble_GOAT** iniciado 2026-10-01T22:24:24.180501-03:00
- **h3_limit_poorjev_relaxed** iniciado 2026-10-01T22:24:24.180698-03:00
- **h3_limit_hybrid_von_cap2** iniciado 2026-10-01T22:24:24.180911-03:00
- **h4_hours_poorjev_relaxed** iniciado 2026-10-01T22:24:24.181086-03:00
- **h4_hours_von_relaxed** iniciado 2026-10-01T22:24:24.181257-03:00
- **h1_exits_hybrid_von_cap2** iniciado 2026-10-01T22:49:49.862682-03:00 · conf≥0.35 margem≥0.2 skip<0.5 · cooldown 120s · ≤2/h · compra 25% USDT · saídas TP 2.5% / SL 1.5% / trailing 1% (arma +1%), reentrada 30 min
- **relaxed_expcap50** iniciado 2026-10-01T22:49:49.863280-03:00 · conf≥0.35 margem≥0.2 skip<0.5 · cooldown 120s · ≤8/h · compra 25% USDT · exposição ≤50%
