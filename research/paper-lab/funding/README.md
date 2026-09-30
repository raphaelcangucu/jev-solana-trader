# funding/ — paper funding-carry (Hyperliquid) — serviço standalone

Delta-neutro: **long spot** (HL spot UBTC/UETH/UZEC; Gate spot para GRASS/ONDO/UNI/TAO/PONS) + **short perp HL** de mesmo tamanho em moedas.
PAPER ONLY. Não toca nada fora de `paper/funding/`. Python 3 stdlib (sem venv).

## Comandos
```
./start.sh            # inicia em background (pid em run/funding.pid)
./stop.sh             # SIGTERM (até 40s), depois KILL
./status.sh           # resumo humano; exit 0=ok, 1=parado, 2=heartbeat >10min
./status.sh --json    # imprime data/status.json
./watchdog.sh         # one-shot: (re)inicia se parado/travado — chamar do supervisor, cron ou @reboot
./watchdog.sh --loop  # loop a cada 5 min (foreground)
python3 report.py     # regenera reports/cumulative.md + reports/<hoje>.md (o serviço já roda de hora em hora)
```

## Portfólios
- `p52` — US$52, universo BTC/ETH/ZEC (só ativos com spot na HL; venue único). Mínimo $10/ordem → ~2 posições.
- `p1000` — US$1.000, universo v1: GRASS, ONDO, UNI, ZEC, TAO, ETH, BTC.
- `p1000_pons` — variante: v1 + PONS com cap de 10% do nocional.

## Regras (config.json → rules)
Entrada: média 7d funding ≥ 8% a.a., funding atual > 0, OI ≥ $10M, ≤1 flip em 24h, fora de cooldown.
Saída: ≥2 flips em 24h, ou média 3d < 0, ou média 3d < 6% (barra USDC) após ≥24h de holding. Cooldown de reentrada 24h.
Perp 2x isolado; top-up de margem se equity < 2× manutenção; fecha (proxy de liquidação) se ≤ manutenção.
Fills: sempre **taker** andando o book real (HL l2Book / Gate order_book); `fee_maker_cf` = contrafactual maker.
Funding: a cada hora, taxa liquidada de `fundingHistory` × tamanho × oracle (poll hh:00:15). `payment = size*oracle*fundingRate`.
Benchmarks: Kamino USDC (média 24h do supplyInterestAPY horário) e JitoSOL (kobe apy) — poll 24h; se falhar, mantém último e marca `stale`.

## Arquivos
- `data/state.json` (estado completo), `data/funding_cache.json` (funding horário 10d), `data/status.json` (heartbeat p/ supervisor/dashboard)
- `logs/positions.jsonl` (open/close/snapshot horário/evaluation/rotation), `logs/funding_accruals.jsonl` (funding + benchmark), `logs/trades.jsonl`, `logs/marks.jsonl`, `logs/service.log`
- Rotação diária (meia-noite BRT): `logs/archive/YYYY-MM/<nome>.<YYYY-MM-DD>.gz`, verificado byte a byte antes de truncar.
- `reports/cumulative.md`, `reports/YYYY-MM-DD.md`, `START.md`

## Integração com o simulador principal (sem editar nada dele)
- Supervisor: chamar `paper/funding/watchdog.sh` a cada ~5 min e no boot. Health: `status.sh` exit code.
- Dashboard: ler `paper/funding/data/status.json` (NAV, ret, APR, funding, taxas, DD, posições, benchmarks, contadores 429).
