#!/usr/bin/env python3
"""Writes reports/YYYY-MM-DD.md (one per local date seen in logs) and reports/cumulative.md.
Reads only funding/data and funding/logs. Paper only."""
import json, gzip
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS, DATA, REP = ROOT / "logs", ROOT / "data", ROOT / "reports"
REP.mkdir(exist_ok=True)
CFG = json.load(open(ROOT / "config.json"))
BAR = CFG["rules"]["usdc_bar_ann"]


def _parse(lines):
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def rd(name):
    """Live (today's) log only. Past days are in logs/archive/YYYY-MM/<name>.jsonl.<date>.gz
    and their daily reports were already written before rotation."""
    p = LOGS / f"{name}.jsonl"
    return _parse(open(p)) if p.exists() else []


def rd_latest_archive(name):
    files = sorted((LOGS / "archive").glob(f"*/{name}.jsonl.*.gz"))
    return _parse(gzip.open(files[-1], "rt")) if files else []


def ldate(ms):
    return datetime.fromtimestamp(ms / 1000).astimezone().date().isoformat()


def f(x, n=4):
    return "—" if x is None else f"{x:,.{n}f}"


def main():
    st = json.load(open(DATA / "state.json"))
    status = json.load(open(DATA / "status.json")) if (DATA / "status.json").exists() else {}
    pos_log = rd("positions")
    acc = rd("funding_accruals")
    trades = rd("trades")
    snaps = [x for x in pos_log if x.get("event") == "snapshot"]
    have = {x["portfolio"] for x in snaps}
    if any(pid not in have for pid in st["portfolios"]):  # right after rotation: use last archived snapshot
        snaps = [x for x in rd_latest_archive("positions") if x.get("event") == "snapshot"] + snaps
    now = datetime.now().astimezone()
    started_ms = st.get("started_ms") or st["created_ms"]
    days = max(1e-9, (now.timestamp() * 1000 - started_ms) / 86400_000)

    # flips observed in settled funding while held (from cache, per coin, during run)
    cache = json.load(open(DATA / "funding_cache.json")) if (DATA / "funding_cache.json").exists() else {}
    flips_run = {}
    for coin, arr in cache.items():
        r = [a[1] for a in arr if a[0] >= started_ms]
        flips_run[coin] = sum(1 for a, b in zip(r, r[1:]) if (a > 0) != (b > 0) and a != 0 and b != 0)

    L = []
    L.append(f"# Funding-carry PAPER — relatório cumulativo\n")
    L.append(f"Gerado: {now.isoformat(timespec='seconds')} (BRT) · início: {st.get('started_at')} · modo: indefinido (sem data de fim) · "
             f"dias decorridos: {days:.2f}\n")
    L.append("**Somente paper.** Preços/funding reais da API pública Hyperliquid (+ Gate spot para hedge onde HL não tem spot). "
             "Fills simulados como *taker* andando o book real; maker só como contrafactual.\n")
    L.append("\n## Resumo por portfólio\n")
    L.append("| Portfólio | Capital | NAV (mark) | Ret % | APR simples % | vs barra 6% (US$) | Kamino USDC (US$) | JitoSOL yield (US$) | Max DD % |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for pid, p in st["portfolios"].items():
        sp = status.get("portfolios", {}).get(pid, {})
        nav = sp.get("nav", p.get("nav_last"))
        cap = p["capital"]
        ret = nav / cap - 1
        apr = ret * 365 / days if days > 0.04 else None
        bar_val = cap * (1 + BAR) ** (days / 365)
        L.append(f"| {pid} | {cap:g} | {f(nav)} | {f(ret*100,3)} | {f(apr*100 if apr is not None else None,2)} | "
                 f"{f(nav-bar_val)} | {f(p['bench']['kamino_usdc']['value'])} | {f(p['bench']['jitosol_yield']['value'])} | "
                 f"{f(p['max_dd']*100,3)} |")
    L.append("\n> APR simples em janelas curtas (< 7 dias) é muito ruidoso: custos de entrada (bridge, taxa de conta, taxas de trade) pesam primeiro; funding acumula depois.\n")

    L.append("\n## Decomposição de PnL (US$)\n")
    L.append("| Portfólio | Funding recebido | Taxas trade (taker) | Taxas se maker (contrafactual) | Custos únicos (bridge+conta) | Basis realizado (spot+perp) | Basis não-realizado | Saída estimada (withdraw $1 + bridge volta + taxas close) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for pid, p in st["portfolios"].items():
        t = p["totals"]
        last = next((s for s in reversed(snaps) if s["portfolio"] == pid), None)
        unreal = sum(x["spot_upnl"] + x["perp_upnl"] for x in (last or {}).get("positions", []))
        close_fees = 0.0
        for x in (last or {}).get("positions", []):
            spot_fee = CFG["fees"]["hl_spot_taker"] if x["hedge_venue"] == "hl_spot" else CFG["fees"]["gate_spot_taker"]
            close_fees += x["size"] * x["spot_mid"] * spot_fee + x["size"] * x["perp_mark"] * CFG["fees"]["hl_perp_taker"]
        q = st["oneoff_quotes"].get(f"{p['capital']:g}", {})
        bout = q.get("bridge_out_est", {}).get("cost_usd")
        exit_cost = CFG["oneoff_costs"]["hl_withdraw_fee_usdc"] + (bout or 0) + close_fees
        oneoff = p["oneoff"]["bridge_in"] + p["oneoff"]["hl_account_fee"]
        L.append(f"| {pid} | {f(t['funding'])} | {f(-t['fees'])} | {f(-t['fees_maker_cf'])} | {f(-oneoff)} | "
                 f"{f(t['realized_spot']+t['realized_perp'])} | {f(unreal)} | {f(-exit_cost)} |")
    L.append("\nNAV se sacar agora = NAV − saída estimada. O bridge de volta usa cotação LI.FI do início (`state.oneoff_quotes`).\n")

    L.append("\n## Posições abertas\n")
    L.append("| Portfólio | Ativo | Hedge | Tamanho | Spot mid | Perp mark | Funding acumulado | Funding atual (ann %) | uPnL spot | uPnL perp |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for pid in st["portfolios"]:
        last = next((s for s in reversed(snaps) if s["portfolio"] == pid), None)
        for x in (last or {}).get("positions", []):
            L.append(f"| {pid} | {x['coin']} | {x['hedge_venue']} | {x['size']} | {f(x['spot_mid'],6)} | {f(x['perp_mark'],6)} | "
                     f"{f(x['funding_accrued'],5)} | {f(x['current_funding_ann']*100,2)} | {f(x['spot_upnl'])} | {f(x['perp_upnl'])} |")

    L.append("\n## Saídas / flips / risco\n")
    L.append("| Portfólio | Trades | Accruals | Saídas por flip/negativo | Saídas abaixo da barra | Margin top-ups | Liquidações (proxy) |")
    L.append("|---|---|---|---|---|---|---|")
    for pid, p in st["portfolios"].items():
        t = p["totals"]
        L.append(f"| {pid} | {t['n_trades']} | {t['n_accruals']} | {t['exits_flip']} | {t['exits_bar']} | {t['margin_topups']} | {t['liquidations']} |")
    L.append("\nFlips de sinal no funding liquidado desde o início (por ativo): " +
             ", ".join(f"{k}={v}" for k, v in sorted(flips_run.items())) + "\n")

    b = st.get("benchmarks", {})
    L.append("\n## Benchmarks (APY usado)\n")
    for k, v in b.items():
        L.append(f"- **{k}**: APY {f(v.get('apy',0)*100,3)}% · fonte {v.get('source')} · polled {v.get('polled_at')} · "
                 f"{'**STALE** (último valor mantido)' if v.get('stale') else 'ok'}")
    L.append("\n## Caveats\n")
    L.append("- p52 limitado a BTC/ETH/ZEC (existe spot na HL → venue único). Mínimo de $10 por ordem na HL limita a ~2 posições.")
    L.append("- p1000*: GRASS/ONDO/UNI/TAO/PONS usam spot da **Gate** (preço USDT convertido por USDC_USDT da Gate). Custo de mover fundos para a Gate **não modelado**.")
    L.append("- Funding: `size × oracle × fundingRate` (docs HL), taxa liquidada de `fundingHistory`; oracle do poll de hh:00:15 (se não houver poll em ±5 min, proxy = candle 1m do perp, marcado no log).")
    L.append("- JitoSOL: só o yield sobre valor em US$ (sem beta de preço do SOL).")
    L.append("- Logs: rotação diária → `logs/archive/YYYY-MM/<nome>.<data>.gz` (verificado antes de truncar). Relatórios diários antigos ficam em `reports/`.")
    L.append(f"- Contadores HTTP (429 etc.): {st.get('counters')}")
    (REP / "cumulative.md").write_text("\n".join(L) + "\n")

    # ---- daily files
    days_set = set()
    for coll in (acc, trades, [x for x in pos_log if x.get("event") == "snapshot"]):
        for x in coll:
            days_set.add(ldate(x["ts_ms"]))
    for d in sorted(days_set):
        D = [f"# Funding-carry PAPER — {d}\n", f"Gerado: {now.isoformat(timespec='seconds')}\n"]
        D.append("| Portfólio | NAV início do dia | NAV fim/último | Δ US$ | Funding do dia | Taxas do dia | Trades |")
        D.append("|---|---|---|---|---|---|---|")
        for pid in st["portfolios"]:
            ds = [s for s in snaps if s["portfolio"] == pid and ldate(s["ts_ms"]) == d]
            fund = sum(x["payment_usdc"] for x in acc if x.get("type") == "funding" and x["portfolio"] == pid and ldate(x["ts_ms"]) == d)
            tr = [x for x in trades if x["portfolio"] == pid and ldate(x["ts_ms"]) == d]
            fees = sum(x["fee"] for x in tr)
            n0 = ds[0]["nav"] if ds else None
            n1 = ds[-1]["nav"] if ds else None
            D.append(f"| {pid} | {f(n0)} | {f(n1)} | {f(n1-n0 if ds else None)} | {f(fund,5)} | {f(-fees)} | {len(tr)} |")
        D.append("\n## Accruals de funding do dia (por portfólio/ativo)\n")
        agg = defaultdict(lambda: [0, 0.0])
        for x in acc:
            if x.get("type") == "funding" and ldate(x["ts_ms"]) == d:
                a = agg[(x["portfolio"], x["coin"])]; a[0] += 1; a[1] += x["payment_usdc"]
        D.append("| Portfólio | Ativo | Horas | Funding US$ |")
        D.append("|---|---|---|---|")
        for (pid, c), (n, v) in sorted(agg.items()):
            D.append(f"| {pid} | {c} | {n} | {f(v,5)} |")
        D.append("\n## Trades do dia\n")
        D.append("| Hora | Portfólio | Ativo | Perna | Venue | Lado | Tamanho | Preço | Taxa | Motivo |")
        D.append("|---|---|---|---|---|---|---|---|---|---|")
        for x in trades:
            if ldate(x["ts_ms"]) == d:
                D.append(f"| {x['ts'][11:19]} | {x['portfolio']} | {x['coin']} | {x['leg']} | {x['venue']} | {x['side']} | {x['size']} | "
                         f"{f(x['vwap_px_usdc'],6)} | {f(x['fee'],5)} | {x['reason']} |")
        (REP / f"{d}.md").write_text("\n".join(D) + "\n")
    print(f"reports written: cumulative.md + {len(days_set)} daily")


if __name__ == "__main__":
    main()
