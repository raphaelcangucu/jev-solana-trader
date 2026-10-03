#!/usr/bin/env python3
"""Generate reports/day1.md — baseline vs relaxed vs v2 (SOL) and baseline vs relaxed per meme."""
from __future__ import annotations
import json, statistics, sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # código do lab
from bot.paths import ROOT  # noqa: E402  (PAPER_LAB_ROOT ou a pasta do lab)
BRT = timezone(timedelta(hours=-3))

def read_jsonl(p: Path):
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out

def max_dd(eqs):
    if not eqs:
        return 0.0
    peak, mdd = eqs[0], 0.0
    for e in eqs:
        peak = max(peak, e)
        if peak > 0:
            mdd = min(mdd, (e - peak) / peak)
    return abs(mdd)

def port_summary(name, decisions, trades, equity_path, portfolio_path=None, price=None):
    dec = [d for d in decisions if d.get("portfolio") == name]
    tr = [t for t in trades if t.get("portfolio") == name]
    equity = read_jsonl(equity_path)
    eqs = [float(e["equity"]) for e in equity]
    bh = [float(e.get("bh_equity") or 0) for e in equity]
    au = [float(e.get("all_usdt_equity") or 0) for e in equity]
    blocked = sum(1 for d in dec if d.get("blocked_trade"))
    finals = Counter(d.get("final_action") for d in dec)
    chosen = Counter(d.get("chosen_action") for d in dec)
    gate_reasons = Counter()
    for d in dec:
        for r in d.get("gate_reasons") or []:
            gate_reasons[r] += 1
    fill_modes = Counter()
    for t in tr:
        fill = t.get("fill") or {}
        mode = fill.get("fill_mode") or (t.get("quote") or {}).get("fill_mode") or "unknown"
        fill_modes[mode] += 1
    fees = sum(float((t.get("fill") or {}).get("fee_usdt") or 0) for t in tr)
    # SOL exposure % from latest equity row or portfolio file
    sol_exp_pct = None
    if equity:
        last = equity[-1]
        eq = float(last.get("equity") or 0)
        sol = float(last.get("sol") or 0)
        px = float(last.get("price") or price or 0)
        if eq > 0 and px > 0:
            sol_exp_pct = 100.0 * (sol * px) / eq
    elif portfolio_path and Path(portfolio_path).exists() and price:
        pdata = json.loads(Path(portfolio_path).read_text())
        sol = float(pdata.get("sol") or 0)
        usdt = float(pdata.get("usdt") or 0)
        eq = usdt + sol * float(price)
        if eq > 0:
            sol_exp_pct = 100.0 * (sol * float(price)) / eq
    return {
        "n_dec": len(dec), "n_tr": len(tr), "blocked": blocked,
        "eqs": eqs, "bh": bh, "au": au, "finals": finals, "chosen": chosen, "fees": fees,
        "gate_reasons": gate_reasons, "fill_modes": fill_modes, "sol_exp_pct": sol_exp_pct,
    }

def main():
    out = ROOT / "reports" / "day1.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ROOT / "config.json").read_text())
    decisions = read_jsonl(ROOT / "logs" / "decisions.jsonl")
    trades = read_jsonl(ROOT / "logs" / "trades.jsonl")
    meme_dec = read_jsonl(ROOT / "logs" / "meme_decisions.jsonl")
    meme_tr = read_jsonl(ROOT / "logs" / "meme_trades.jsonl")
    memecoins = json.loads((ROOT / "memecoins.json").read_text())
    meme_status = {}
    msp = ROOT / "data" / "meme" / "status.json"
    if msp.exists():
        meme_status = json.loads(msp.read_text())

    # optional live price from status for exposure if equity empty
    status = {}
    sp = ROOT / "status.json"
    if sp.exists():
        status = json.loads(sp.read_text())
    live_px = status.get("price_usd")

    base = port_summary("baseline", decisions, trades, ROOT / "data" / "equity_baseline.jsonl",
                        ROOT / "data" / "portfolio_baseline.json", live_px)
    rel = port_summary("relaxed", decisions, trades, ROOT / "data" / "equity_relaxed.jsonl",
                       ROOT / "data" / "portfolio_relaxed.json", live_px)
    v2 = port_summary("v2", decisions, trades, ROOT / "data" / "equity_v2.jsonl",
                      ROOT / "data" / "portfolio_v2.json", live_px)

    from bot import params as P  # portões efetivos de params.json (sem overlay)
    gb = P.explain("baseline", use_overlay=False)[0]["gates"]
    g_r = dict(P.explain("relaxed", use_overlay=False)[0]["gates"])
    g_r["calibration_note"] = ((P.STORE.doc() or {}).get("profiles") or {}).get("relaxed", {}).get("note", "")
    lines = [
        "# Day 1 paper trading report",
        f"\n**Generated (BRT):** {datetime.now(tz=BRT).isoformat()}",
        "\n## Gate rules\n",
        f"- **Baseline (article-faithful):** conf ≥ {gb['min_confidence']}, skip_noul < {gb['max_skip_noul']}, "
        f"cooldown {gb['cooldown_seconds']}s, max {gb['max_trades_per_hour']}/h, buy {gb['buy_fraction_usdt']*100:.0f}% USDT.",
        f"- **Relaxed (calibrated to von output):** conf ≥ {g_r.get('min_confidence')} (~80th pct of observed ~0.229/0.379 clusters), "
        f"prob margin (chosen−runner-up) ≥ {g_r.get('min_prob_margin')}, skip_noul < {g_r.get('max_skip_noul')}, "
        f"same sizing/cooldown/cap. Same von decision reused — no extra model calls.",
        f"- **v2 (shadow):** own von call with `criteria_v2.json`; **uses the relaxed gate** "
        f"(conf ≥ {g_r.get('min_confidence')}, margin ≥ {g_r.get('min_prob_margin')}, skip < {g_r.get('max_skip_noul')}). "
        f"Portfolio file created at night review 04:00:03 BRT but initially wired to the baseline 0.6 gate by an init bug; "
        f"effective trading under the relaxed gate started after the fix (see README).",
        f"- Calibration note: {g_r.get('calibration_note', '')}",
        "\n## SOL/USDT — baseline vs relaxed vs v2\n",
        "| Portfolio | Decisions | Trades | Blocked | SOL exp % | Equity start→end | vs B&H Δ | vs USDT Δ | MDD | Fees |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]

    def row(label, s):
        eqs, bh, au = s["eqs"], s["bh"], s["au"]
        exp = f"{s['sol_exp_pct']:.1f}%" if s.get("sol_exp_pct") is not None else "—"
        if not eqs:
            return f"| {label} | {s['n_dec']} | {s['n_tr']} | {s['blocked']} | {exp} | n/a | — | — | — | {s['fees']:.4f} |"
        vs_bh = (eqs[-1]-eqs[0]) - ((bh[-1]-bh[0]) if bh else 0)
        vs_au = (eqs[-1]-eqs[0]) - ((au[-1]-au[0]) if au else 0)
        return (f"| {label} | {s['n_dec']} | {s['n_tr']} | {s['blocked']} | {exp} | "
                f"{eqs[0]:.4f}→{eqs[-1]:.4f} | {vs_bh:.4f} | {vs_au:.4f} | {max_dd(eqs)*100:.2f}% | {s['fees']:.4f} |")

    lines.append(row("baseline", base))
    lines.append(row("relaxed", rel))
    if v2["n_dec"] or v2["eqs"]:
        lines.append(row("v2", v2))
    else:
        lines.append("| v2 | — | — | — | _night review 04:00 BRT_ | — | — | — | — |")

    def detail_block(label, s):
        gr = dict(s["gate_reasons"].most_common()) if s.get("gate_reasons") else {}
        fm = dict(s["fill_modes"].most_common()) if s.get("fill_modes") else {}
        exp = f"{s['sol_exp_pct']:.1f}%" if s.get("sol_exp_pct") is not None else "n/a"
        return [
            f"\n### {label}\n",
            f"- chosen: {dict(s['chosen'])}",
            f"- final: {dict(s['finals'])}",
            f"- SOL exposure: **{exp}**",
            f"- fill_mode counts: {fm if fm else '(no trades)'}",
            f"- blocked / gate reasons: {gr if gr else '(none)'}",
        ]

    lines += detail_block("Baseline", base)
    lines += detail_block("Relaxed", rel)
    if v2["n_dec"] or v2["eqs"]:
        lines += detail_block("v2", v2)

    # Extra model portfolios (laya/poorjev/jev) — mid-day starts
    models_cfg = {}
    mp = ROOT / "models.json"
    if mp.exists():
        models_cfg = json.loads(mp.read_text())
    extra_names = []
    for mid, b in (models_cfg.get("backends") or {}).items():
        if mid == "von":
            continue
        for pname in b.get("sol_portfolios") or []:
            if pname in ("baseline", "relaxed", "v2"):
                continue
            extra_names.append(pname)
    lines += ["\n## Extra model SOL portfolios\n"]
    starts = ROOT / "reports" / "models_start.md"
    if starts.exists():
        lines.append(starts.read_text().strip())
        lines.append("")
    lines += [
        "| Portfolio | Model | Decisions | Trades | SOL exp % | Equity end | vs B&H Δ | vs USDT Δ | MDD | Start BRT |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    ranking_extra = []
    for pname in extra_names:
        s = port_summary(pname, decisions, trades, ROOT / "data" / f"equity_{pname}.jsonl",
                         ROOT / "data" / f"portfolio_{pname}.json", live_px)
        model = "?"
        started = ""
        pp = ROOT / "data" / f"portfolio_{pname}.json"
        if pp.exists():
            pdata = json.loads(pp.read_text())
            model = pdata.get("model") or "?"
            started = pdata.get("started_brt") or ""
        exp = f"{s['sol_exp_pct']:.1f}%" if s.get("sol_exp_pct") is not None else "—"
        if s["eqs"]:
            eqs, bh, au = s["eqs"], s["bh"], s["au"]
            vs_bh = (eqs[-1]-eqs[0]) - ((bh[-1]-bh[0]) if bh else 0)
            vs_au = (eqs[-1]-eqs[0]) - ((au[-1]-au[0]) if au else 0)
            end = eqs[-1]
            mdd = max_dd(eqs)*100
            ranking_extra.append((vs_bh, pname, model, end, vs_bh, vs_au))
            lines.append(
                f"| {pname} | {model} | {s['n_dec']} | {s['n_tr']} | {exp} | {end:.4f} | "
                f"{vs_bh:.4f} | {vs_au:.4f} | {mdd:.2f}% | {started} |"
            )
        else:
            lines.append(f"| {pname} | {model} | {s['n_dec']} | {s['n_tr']} | {exp} | n/a | — | — | — | {started} |")
    if ranking_extra:
        ranking_extra.sort(key=lambda x: -x[0])
        lines += ["\n### Ranked by vs B&H Δ\n"]
        for i, (vs_bh, pname, model, end, _, vs_au) in enumerate(ranking_extra, 1):
            lines.append(f"{i}. **{pname}** ({model}) end={end:.4f} vsB&H={vs_bh:.4f} vsUSDT={vs_au:.4f}")

    j = (models_cfg.get("backends") or {}).get("jev") or {}
    lines += [
        "\n## Hosted Jev\n",
        f"- enabled in models.json: **{j.get('enabled')}**",
        f"- api_key_env: `{j.get('api_key_env', 'JEV_API_KEY')}` (never logged)",
        f"- endpoint: `{(j.get('base_url') or '')}{(j.get('endpoint') or '/v1/systemone')}`",
        "- If key missing: status shows **aguardando chave**. After setting key: export it, then `scripts/stop.sh` + `scripts/start.sh` so supervisor inherits env (see `scripts/restart_models.sh`).",
        "- LIVE_TRADING: always off (paper simulation only).",
    ]

    # Param changes log (dashboard hot-reload audit trail)
    param_changes = read_jsonl(ROOT / "logs" / "param_changes.jsonl")
    lines += ["\n## Parameter changes (dashboard / hot-reload)\n"]
    if not param_changes:
        lines.append("_Nenhuma alteração de parâmetros registrada ainda._")
    else:
        lines.append("| BRT | Portfolio | Campo | Antigo | Novo |")
        lines.append("| --- | --- | --- | ---: | ---: |")
        for p in param_changes:
            lines.append(
                f"| {p.get('ts_brt','')} | {p.get('portfolio','')} | `{p.get('field','')}` | "
                f"{p.get('old')} | {p.get('new')} |"
            )


    lines += [
        "\n## Memecoin paper simulation\n",
        f"**Restart (clean, live prices only):** {meme_status.get('restart_brt', 'see status')}",
        f"\n**Price policy:** {meme_status.get('price_policy', 'live_only_no_seed')} — seed file removed; skip if no fresh real mark ≤120s.",
        f"\n**Cadence:** {memecoins.get('cadence', {})}",
        "\n**Night review for memes:** skipped.",
        "\n### Basket\n",
    ]
    for t in memecoins["tokens"]:
        lines.append(f"- **{t['symbol']}** `{t['mint']}` — {t.get('why', '')}")

    # Discover meme equity files: von {SYM}_baseline/_relaxed + {SYM}_{model}_{profile}
    eq_dir = ROOT / "data" / "meme" / "equity"
    meme_models = ["von"]
    mc = {}
    if (ROOT / "models.json").exists():
        mc = json.loads((ROOT / "models.json").read_text())
        for mid, b in (mc.get("backends") or {}).items():
            if mid != "von" and (b.get("memes_enabled") or any(eq_dir.glob(f"*_{mid}_*.jsonl"))):
                if mid not in meme_models:
                    meme_models.append(mid)
    lines += [
        f"\n### Ranking per model vs B&H / USDT (models={meme_models})\n",
        "| Symbol | Model | Profile | End eq | PnL | vs B&H | vs USDT | MDD | Trades |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    ranking = []
    for t in memecoins["tokens"]:
        sym = t["symbol"]
        for mid in meme_models:
            for profile in ("baseline", "relaxed"):
                if mid == "von":
                    rows = read_jsonl(eq_dir / f"{sym}_{profile}.jsonl")
                else:
                    rows = read_jsonl(eq_dir / f"{sym}_{mid}_{profile}.jsonl")
                if not rows:
                    continue
                s0, s1 = float(rows[0]["equity"]), float(rows[-1]["equity"])
                bh0 = float(rows[0].get("bh_equity") or s0)
                bh1 = float(rows[-1].get("bh_equity") or s1)
                au0 = float(rows[0].get("all_usdt_equity") or s0)
                au1 = float(rows[-1].get("all_usdt_equity") or s0)
                eqs_t = [float(r["equity"]) for r in rows]
                ranking.append({
                    "symbol": sym, "model": mid, "profile": profile, "end": s1, "pnl": s1 - s0,
                    "vs_bh": (s1 - s0) - (bh1 - bh0),
                    "vs_usdt": (s1 - s0) - (au1 - au0),
                    "mdd": max_dd(eqs_t),
                    "trades": int(rows[-1].get("trade_count") or 0),
                })
    ranking.sort(key=lambda x: (x["symbol"], x["model"], 0 if x["profile"]=="baseline" else 1))
    for r in ranking:
        lines.append(
            f"| {r['symbol']} | {r['model']} | {r['profile']} | {r['end']:.4f} | {r['pnl']:.4f} | "
            f"{r['vs_bh']:.4f} | {r['vs_usdt']:.4f} | {r['mdd']*100:.2f}% | {r['trades']} |"
        )
    if not ranking:
        lines.append("_No meme equity samples yet (post-wipe)._")
    else:
        by_model = {}
        for r in ranking:
            by_model.setdefault(r["model"], []).append(r)
        lines += ["\n### Ranked by vs B&H Δ (all meme portfolios)\n"]
        flat = sorted(ranking, key=lambda x: -x["vs_bh"])
        for i, r in enumerate(flat[:30], 1):
            lines.append(
                f"{i}. **{r['symbol']}** `{r['model']}/{r['profile']}` end={r['end']:.4f} "
                f"vsB&H={r['vs_bh']:.4f} vsUSDT={r['vs_usdt']:.4f} trades={r['trades']}"
            )

    m_skip = sum(1 for d in meme_dec if d.get("final_action") == "skipped_no_price")
    from collections import Counter
    m_by_model = Counter((d.get("model") or "von") for d in meme_dec if d.get("final_action") != "skipped_no_price")
    m_tr_by_model = Counter((t.get("model") or ("von" if "meme_" in str(t.get("portfolio")) else "?")) for t in meme_tr)
    # infer model from portfolio name if missing
    def _meme_model(port):
        port = str(port or "")
        for mid in ("poorjev", "laya", "jev"):
            if f"_{mid}_" in port:
                return mid
        if port.startswith("meme_") or port.endswith("_baseline") or port.endswith("_relaxed"):
            return "von"
        return "?"
    m_by_model = Counter()
    for d in meme_dec:
        if d.get("final_action") == "skipped_no_price":
            continue
        m_by_model[d.get("model") or _meme_model(d.get("portfolio"))] += 1
    m_tr_by_model = Counter()
    for t in meme_tr:
        m_tr_by_model[t.get("model") or _meme_model(t.get("portfolio"))] += 1
    lines += [
        f"\n- Meme decisions by model: {dict(m_by_model)} skipped_no_price={m_skip}",
        f"- Meme trades by model: {dict(m_tr_by_model)}",
        f"- Sources seen: {sorted({d.get('price_source') for d in meme_dec if d.get('price_source')})}",
        f"- Meme models enabled (status): {meme_status.get('meme_models_enabled')}",
    ]

    # --- Rule strategies + hybrids ---
    rules_st = {}
    rsp = ROOT / "data" / "rules" / "status.json"
    if rsp.exists():
        try:
            rules_st = json.loads(rsp.read_text())
        except Exception:
            rules_st = {}
    starts_rules = ROOT / "reports" / "rules_start.md"
    lines += ["\n## Rule strategies & hybrids (paper)\n"]
    if starts_rules.exists():
        lines.append(starts_rules.read_text().strip())
        lines.append("")
    lines.append(f"- rules_bot started_brt (status): {rules_st.get('started_brt')}")
    lines.append(f"- warm_up: {json.dumps(rules_st.get('warm_up') or {}, default=str)[:500]}")
    ind = (rules_st.get("indicators") or {}).get("sol") or {}
    lines.append(
        f"- SOL indicators now: close={ind.get('close_1h')} ema12={ind.get('ema12')} "
        f"ema26={ind.get('ema26')} rsi={ind.get('rsi')} bull={ind.get('regime_bull')}"
    )
    rule_sol = ["grid_sol_2pct", "rsi_sol_1h", "hybrid_von_relaxed_cap2"]
    lines += [
        "\n### SOL rule / hybrid portfolios\n",
        "| Portfolio | Strategy | Decisions | Trades | Equity end | vs B&H Δ | MDD | Start BRT |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for pname in rule_sol:
        s = port_summary(pname, decisions, trades, ROOT / "data" / f"equity_{pname}.jsonl",
                         ROOT / "data" / f"portfolio_{pname}.json", live_px)
        started = ""
        strat = f"rule:{pname}"
        pp = ROOT / "data" / f"portfolio_{pname}.json"
        if pp.exists():
            pdata = json.loads(pp.read_text())
            started = pdata.get("started_brt") or ""
            strat = pdata.get("strategy") or strat
        if s["eqs"]:
            eqs, bh = s["eqs"], s["bh"]
            vs_bh = (eqs[-1]-eqs[0]) - ((bh[-1]-bh[0]) if bh else 0)
            lines.append(
                f"| {pname} | {strat} | {s['n_dec']} | {s['n_tr']} | {eqs[-1]:.4f} | "
                f"{vs_bh:.4f} | {max_dd(eqs)*100:.2f}% | {started} |"
            )
        else:
            lines.append(f"| {pname} | {strat} | {s['n_dec']} | {s['n_tr']} | n/a | — | — | {started} |")

    lines += [
        "\n### Meme rule / hybrid portfolios\n",
        "| Portfolio | Trades | Equity end | Last signal | Start BRT |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    memecoins = json.loads((ROOT / "memecoins.json").read_text())
    port_dir = ROOT / "data" / "meme" / "portfolios"
    eq_dir = ROOT / "data" / "meme" / "equity"
    for tkn in memecoins.get("tokens") or []:
        sym = tkn["symbol"]
        for suf in ("_rule_regime", "_rule_donch_regime", "_hybrid_poorjev_regime"):
            pname = f"{sym}{suf}"
            s = port_summary(pname, meme_dec, meme_tr, eq_dir / f"{pname}.jsonl",
                             port_dir / f"{pname}.json", None)
            started = ""
            last_sig = ""
            pp = port_dir / f"{pname}.json"
            if pp.exists():
                pdata = json.loads(pp.read_text())
                started = pdata.get("started_brt") or ""
            # last signal from decisions
            for d in reversed(meme_dec):
                if d.get("portfolio") == pname:
                    last_sig = d.get("final_action") or ""
                    break
            if s["eqs"]:
                lines.append(f"| {pname} | {s['n_tr']} | {s['eqs'][-1]:.4f} | {last_sig} | {started} |")
            elif pp.exists():
                lines.append(f"| {pname} | {s['n_tr']} | n/a | {last_sig} | {started} |")

    rule_tr = sum(1 for t in trades if str(t.get("strategy") or "").startswith("rule:"))
    rule_tr += sum(1 for t in meme_tr if str(t.get("strategy") or "").startswith("rule:"))
    lines.append(f"\n- Total rule-tagged trades (SOL+meme logs): {rule_tr}")

    lines += [
        "\n## Verdict\n",
        "**Worth running live?** Not on this sample alone.",
        "- Compare baseline (conf≥0.6, may trade ~0) vs relaxed (calibrated) honestly.",
        "- Fills are Jupiter quotes minus haircuts — not identical to on-chain execution/MEV/failures.",
        "- Marks are live-only (Gate.io / Coinpaprika / DexScreener / Jupiter); no seed/fabricated fallback.",
        "- Keep paper-only until multi-day baseline vs relaxed vs v2 vs buy&hold shows stable edge after fees.",
        "\n## Caveats\n",
        "- Simulation only; wallet keys never loaded.",
        "- Memecoin night-review/v2 shadow skipped.",
        f"- Each meme portfolio starts with {json.loads((ROOT / 'memecoins.json').read_text()).get('start_usdt_each')} USDT flat (von baseline+relaxed per token; plus `{{SYM}}_{{model}}_{{profile}}` when memes_enabled).",
        "- Rule portfolios: `grid_sol_2pct`, `rsi_sol_1h`, `{SYM}_rule_regime`, `{SYM}_rule_donch_regime`, `hybrid_von_relaxed_cap2`, `{SYM}_hybrid_poorjev_regime`.",
        f"- Meme clean restart noted in status: {meme_status.get('restart_brt')}.",
    ]
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")

def _analytics():
    from bot import analytics as A
    return A


def verdict_table(A, cat, tb):
    L = ["| Portfólio | Status | Veredito | Progresso até os mínimos | Motivo |", "|---|---|---|---|---|"]
    for n in sorted(cat, key=lambda k: (cat[k].get("asset", "SOL") != "SOL", cat[k].get("lineage", k), k)):
        v = A.verdict(cat[n], tb)
        L.append(f"| {n} | {cat[n].get('status','active')} | **{v['verdict']}** | {v['progress'].get('text','')} | {v.get('reason','')} |")
    return "\n".join(L)


def lineage_table(A, cat, reg):
    L = ["| Linhagem | Original | Forks (status) | Lead fork (base p/ tuning, não é veredito) |", "|---|---|---|---|"]
    for lin, d in sorted((reg.get("lineages") or {}).items()):
        forks = [f"{m} ({cat[m].get('status')})" for m in d.get("members", []) if m != lin and m in cat]
        if not forks and not d.get("lead"):
            continue
        L.append(f"| {lin} | {lin} | {', '.join(forks) or '–'} | {d.get('lead') or '–'} |")
    return "\n".join(L) if len(L) > 2 else "Nenhum fork criado ainda."


def day_report(day):
    """reports/YYYY-MM-DD.md: per-day stats for every portfolio (originals + lab) + verdicts + fill quality."""
    A = _analytics()
    cat, reg = A.catalog(); tb = A.load_trades()
    a, b = A.day_bounds(day); import time as _t; b = min(b, _t.time())
    tbl, _ = A.stats_table(cat, tb, a, b)
    fq = A.fill_quality(a, b)
    d1 = ((json.loads((ROOT / "config.json").read_text()).get("experiment") or {}).get("day1_start_brt")
          or "2026-09-24T00:00:00-03:00")
    day1 = datetime.fromisoformat(d1).astimezone(BRT).date()
    n = (datetime.fromisoformat(day + "T00:00:00-03:00").date() - day1).days + 1
    txt = "\n".join([f"# Relatório do dia {day} (dia {n} do experimento)", "",
        f"Janela 00:00–24:00 BRT (portfólios que começaram no meio do dia usam o próprio início). Gerado {datetime.now(BRT).isoformat()}. Paper only.", "",
        "Excesso vs B&H = PnL − variação do benchmark buy-and-hold do próprio portfólio (SOL: mix inicial; memes: capital inicial na moeda). vs USDT = PnL.", "",
        A.STATS_LEGEND, "",
        tbl, "", "## Veredito (regra de dados mínimos)", "", verdict_table(A, cat, tb), "",
        "## Linhagens (original → forks)", "", lineage_table(A, cat, reg), "",
        "## Qualidade de fills", "", f"- {fq['mark_fallbacks']}/{fq['market_fills']} fills a mercado no fallback de mark; motivos: {fq['reasons']}",
        f"- eventos de cotação: {fq['quote_events']}", ""])
    out = ROOT / "reports" / f"{day}.md"; out.write_text(txt); print(f"wrote {out}")
    return out


def cumulative_report():
    A = _analytics()
    cat, reg = A.catalog(); tb = A.load_trades()
    import time as _t; now = _t.time()
    tbl, _ = A.stats_table(cat, tb, 0, now)
    fq = A.fill_quality(0, now)
    txt = "\n".join(["# Relatório acumulado desde o início", "",
        f"Cada portfólio desde o SEU início até {datetime.now(BRT).isoformat()} (BRT). Paper only.", "",
        A.STATS_LEGEND, "",
        tbl, "", "## Veredito (regra de dados mínimos)", "", verdict_table(A, cat, tb), "",
        "## Linhagens (original → forks)", "", lineage_table(A, cat, reg), "",
        "## Qualidade de fills (acumulado)", "", f"- {fq['mark_fallbacks']}/{fq['market_fills']} fills a mercado no fallback de mark; motivos: {fq['reasons']}", ""])
    out = ROOT / "reports" / "cumulative.md"; out.write_text(txt); print(f"wrote {out}")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Paper reports. No args = legacy day1.md.")
    ap.add_argument("--day", help="YYYY-MM-DD -> reports/YYYY-MM-DD.md")
    ap.add_argument("--all-days", action="store_true", help="one report per day since 2026-09-24")
    ap.add_argument("--cumulative", action="store_true", help="reports/cumulative.md")
    x = ap.parse_args()
    if x.day or x.all_days or x.cumulative:
        if x.day:
            day_report(x.day)
        if x.all_days:
            from datetime import timedelta as _td
            d = datetime.fromisoformat("2026-09-24T00:00:00-03:00")
            while d <= datetime.now(BRT):
                day_report(d.strftime("%Y-%m-%d")); d += _td(days=1)
        if x.cumulative:
            cumulative_report()
    else:
        main()
