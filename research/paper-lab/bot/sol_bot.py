#!/usr/bin/env python3
"""Paper SOL/USDT bot. Simulation only — never signs or sends txs.
Baseline (article-faithful) + relaxed (calibrated gate) share one von call per cycle.
v2 shadow (after night review) uses its own criteria_v2.json von call and the RELAXED gate
(conf>=0.35, margin>=0.20, skip<0.5) — von confidence never exceeds ~0.40 so a 0.6 gate
would never trade. Extra von call per cycle is fine within 15s; alternating is acceptable.
"""
from __future__ import annotations
import json, os, signal, sys, time, traceback, uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # código do lab (não PAPER_LAB_ROOT)
from bot.paths import ROOT, LAB_DIR  # noqa: E402

from bot.lib import (
    brt_now, brt_iso, load_cfg, assert_no_keys, build_state, von_system_one,
    apply_gates, jupiter_quote, fetch_sol_price, append_jsonl, write_json,
    read_jsonl, USDT, SOL,
)
from bot.backends import load_models_cfg, decide_many, jev_key_status
from bot import params as P

STOP = False

def _sig(*_a):
    global STOP
    STOP = True

def load_criteria(path: Path) -> dict:
    return json.loads(path.read_text())

def new_portfolio(path: Path, sol: float, usdt: float, price: float, name: str) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    data = {
        "name": name, "asset_mode": "sol", "sol": sol, "usdt": usdt, "token": 0.0,
        "start_sol": sol, "start_usdt": usdt, "start_price": price,
        "benchmark_buy_hold": {"sol": sol, "usdt": usdt},
        "benchmark_all_usdt": {"usdt": usdt + sol * price},
        "realized_pnl_usdt": 0.0, "fees_paid_usdt": 0.0, "fees_paid_sol": 0.0,
        "trade_count": 0, "last_trade_ts": None, "trade_timestamps": [],
        "position": "held" if sol > 1e-9 else "flat", "recent_pnl_mood": "neutral",
        "created_ts": time.time(),
    }
    write_json(path, data)
    return data

def equity(d, price):
    return float(d["usdt"]) + float(d["sol"]) * price

def bh_equity(d, price):
    bh = d["benchmark_buy_hold"]
    return float(bh["usdt"]) + float(bh["sol"]) * price

def position_word(d):
    if float(d["sol"]) > 1e-6:
        return "held"
    return "sold" if d["trade_count"] > 0 else "flat"

def _mark_fill_buy_sol(usdt_in, price, slip_bps, extra_bps, net_sol):
    """Paper fill at live mark when Jupiter quote unavailable. Not a fabricated mark — uses current real price."""
    px = price * (1.0 + (slip_bps + extra_bps) / 10000.0)  # worse buy
    sol_out = usdt_in / px
    sol_net = max(0.0, sol_out - net_sol)
    return sol_net, {"fill_mode": "mark", "mark_price": price, "effective_price": px}

def _mark_fill_sell_sol(sol_in, price, slip_bps, extra_bps, net_usdt):
    px = price * (1.0 - (slip_bps + extra_bps) / 10000.0)  # worse sell
    usdt_out = sol_in * px
    usdt_net = max(0.0, usdt_out - net_usdt)
    return usdt_net, {"fill_mode": "mark", "mark_price": price, "effective_price": px}

def sim_trade(side, data, gcfg, fees, market, price, decision_id, trades_log: Path, strategy=None):
    extra = float(fees.get("extra_slippage_bps", 5))
    net_sol = float(fees.get("assumed_network_fee_sol", 5e-6))
    net_usdt = net_sol * price
    slip = int(market.get("slippage_bps", 50))
    pnl = 0.0
    q = None
    fill_meta = {}
    if side == "buy":
        usdt_in = float(data["usdt"]) * float(gcfg["buy_fraction_usdt"])
        if usdt_in < float(gcfg["min_usdt_trade"]):
            return None
        try:
            q = jupiter_quote({"market": market}, USDT, SOL, usdt_in, 6, slip)
            out = float(q["outAmount"]) / 1e9
            out_net = max(0.0, out - out * (extra / 10000.0) - net_sol)
            fill_meta = {"fill_mode": q.get("_fill_mode", "jupiter_quote"), "quote_source": q.get("_quote_source")}
        except Exception as e:
            out_net, fill_meta = _mark_fill_buy_sol(usdt_in, price, slip, extra, net_sol)
            fill_meta["quote_error"] = f"{type(e).__name__}:{e}"
        fee = usdt_in * (extra / 10000.0) + net_usdt
        data["usdt"] -= usdt_in
        data["sol"] = float(data["sol"]) + out_net
        data["fees_paid_usdt"] += fee
        data["fees_paid_sol"] += net_sol
        fill = {"side": "buy", "usdt_in": usdt_in, "sol_out_net": out_net, "fee_usdt": fee, **fill_meta}
    else:
        sol_in = float(data["sol"])
        if sol_in < float(gcfg["min_sol_trade"]):
            return None
        to_swap = max(0.0, sol_in - net_sol)
        if to_swap < float(gcfg["min_sol_trade"]):
            return None
        try:
            q = jupiter_quote({"market": market}, SOL, USDT, to_swap, 9, slip)
            out = float(q["outAmount"]) / 1e6
            out_net = max(0.0, out - out * (extra / 10000.0))
            fill_meta = {"fill_mode": q.get("_fill_mode", "jupiter_quote"), "quote_source": q.get("_quote_source")}
        except Exception as e:
            out_net, fill_meta = _mark_fill_sell_sol(to_swap, price, slip, extra, net_usdt)
            fill_meta["quote_error"] = f"{type(e).__name__}:{e}"
        fee = out_net * (extra / 10000.0) + net_usdt if fill_meta.get("fill_mode") == "mark" else (out * (extra / 10000.0) + net_usdt if q else net_usdt)
        # recompute fee cleanly
        fee = float(to_swap * price) * (extra / 10000.0) + net_usdt
        pnl = out_net - to_swap * price
        data["sol"] = 0.0
        data["usdt"] += out_net
        data["fees_paid_usdt"] += fee
        data["fees_paid_sol"] += net_sol
        data["realized_pnl_usdt"] += pnl
        fill = {"side": "sell", "sol_in": to_swap, "usdt_out_net": out_net, "fee_usdt": fee, "approx_pnl": pnl, **fill_meta}
    now = time.time()
    data["trade_count"] += 1
    data["last_trade_ts"] = now
    data["trade_timestamps"] = (data.get("trade_timestamps") or [])[-99:] + [now]
    data["position"] = position_word(data)
    data["recent_pnl_mood"] = "buoyed" if pnl > 0.05 else ("stung" if pnl < -0.05 else "neutral")
    quote_info = None
    if q:
        quote_info = {
            "inAmount": q.get("inAmount"), "outAmount": q.get("outAmount"),
            "priceImpactPct": q.get("priceImpactPct"),
            "routeLabels": [r.get("swapInfo", {}).get("label") for r in (q.get("routePlan") or [])],
        }
    else:
        quote_info = {"fill_mode": fill_meta.get("fill_mode"), "mark_price": price}
    row = {
        "ts": now, "ts_brt": brt_iso(now), "portfolio": data["name"], "decision_id": decision_id,
        "side": side, "price_mark": price, "fill": fill, "quote": quote_info,
        "paper_only": True, "signed": False, "sent": False,
        "strategy": strategy,
        "portfolio_after": {"sol": data["sol"], "usdt": data["usdt"], "equity": equity(data, price)},
    }
    append_jsonl(trades_log, row)
    return row

AUDIT_GROUPS = {
    # baseline e relaxed partilham UMA chamada von por ciclo (critérios baseline): fundidas por dedupe_calls.
    "von · critérios baseline (baseline+relaxed)": ("baseline", "relaxed"),
    "von · critérios v2 (v2)": ("v2",),
}
PROPOSAL_GROUP = "von · critérios baseline (baseline+relaxed)"


def _day_window(day):
    if not day:
        return None
    a = datetime.fromisoformat(f"{day}T00:00:00-03:00").timestamp()
    return a, a + 86400


def night_review(decisions_log, trades_log, criteria_path, review_path, criteria_v2_path,
                 day=None, cfg=None, prices_log=None):
    """Revisão noturna (proposta apenas; portão humano). Auditoria por PERCENTIL da confiança
    (bot/confidence_audit.py): corte = P`review.confidence_percentile` das confianças respondidas do von
    no dia revisado, candidatas = chamadas buy/sell, erro = retorno a `review.horizon_s` contra a chamada
    além de `review.band`. A barra fixa antiga (`review.fixed_bar`, 0,8) é calculada só para comparação.
    Escreve a proposta em `criteria_v2_path` e o resumo em `review_path`; nunca altera criteria_baseline.json.
    `day` (YYYY-MM-DD, BRT) limita a janela ao dia revisado; sem `day` audita tudo (arranque do v2)."""
    from bot import confidence_audit as CA
    from bot import logio
    cfg = cfg if cfg is not None else load_cfg()
    rc = CA.review_cfg(cfg)
    win = _day_window(day)
    since = (win[0] - 1) if win else None
    wanted = {p for ps in AUDIT_GROUPS.values() for p in ps}
    rows = [d for d in logio.iter_rows(Path(decisions_log), since_ts=since) if d.get("portfolio") in wanted]
    trades = [t for t in read_jsonl(Path(trades_log)) if t.get("portfolio") in wanted]
    traded_ids = {t.get("decision_id") for t in trades}
    prices_log = Path(prices_log) if prices_log else ROOT / "data" / "prices.jsonl"
    prices = CA.build_series(logio.iter_rows(prices_log, since_ts=since), asset="SOL") if prices_log.exists() else {}
    kw = dict(prices=prices, trades=trades, horizon_s=rc["horizon_s"], band=rc["band"],
              tolerance_s=rc["tolerance_s"], candidates=rc["candidates"], window=win, top_words=rc["top_words"],
              tie_rule=rc["tie_rule"])
    audits = {}
    for gname, ports in AUDIT_GROUPS.items():
        g = CA.dedupe_calls([d for d in rows if d.get("portfolio") in ports], traded_ids=traded_ids)
        audits[gname] = {
            "pct": CA.audit(g, percentile_p=rc["confidence_percentile"], **kw),
            "fixed": CA.audit(g, fixed_bar=rc["fixed_bar"], **kw),
        }
    base = load_criteria(Path(criteria_path))
    main = audits[PROPOSAL_GROUP]["pct"]
    proposed = CA.propose_criteria(base, main, min_mistakes=int(rc["min_mistakes"]), generated_at=brt_iso())
    proposed["audit"].update({
        "day": day, "group": PROPOSAL_GROUP,
        "fixed_bar_compare": CA.summary(audits[PROPOSAL_GROUP]["fixed"]),
        "groups": {g: {"percentile": CA.summary(v["pct"]), "fixed_bar": CA.summary(v["fixed"])} for g, v in audits.items()},
    })
    write_json(Path(criteria_v2_path), proposed)
    title_day = day or brt_now().strftime("%Y-%m-%d")
    f = lambda x, n=3: "–" if x is None else f"{x:.{n}f}"
    L = [f"# Revisão noturna (critérios v2) — {title_day}", "",
         f"**Gerado (BRT):** {brt_iso()} · **Dia revisado:** {day or 'todo o log disponível'} · paper only", "",
         "## Portão humano", "",
         "- `criteria_baseline.json` NÃO foi alterado; o portfólio v2 em curso mantém os seus critérios.",
         f"- Proposta escrita em `{Path(criteria_v2_path).name}` (só proposta).", "",
         "## Auditoria por percentil da confiança", "",
         f"Corte = P{rc['confidence_percentile']:g} das confianças respondidas (sem fail-closed) de cada grupo; candidatas = "
         f"`{rc['candidates']}`; erro = retorno a {int(rc['horizon_s'])} s contra a chamada além de ±{rc['band']*100:.2f}%. "
         f"A barra fixa {rc['fixed_bar']} aparece só para comparação. Com muitos empates no corte usa-se `>` (coluna Regra).", "",
         "| Grupo | Regra | Corte | Respondidas | Confiantes | Resolvidas | Erros (episódios) | Acertos | Hit rate | Palavras dos erros |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for g, v in audits.items():
        for a in (v["pct"], v["fixed"]):
            L.append(f"| {g} | {a['rule']} | {f(a['cutoff'])} | {a['n_answered']} | {a['n_confident']} | {a['n_resolved']} | "
                     f"{a['n_mistakes']} ({a['mistake_episodes']}) | {a['n_correct']} | {f(a['hit_rate'], 2)} | "
                     f"{', '.join(f'{w}:{n}' for w, n in a['lose_words']) or '–'} |")
    L += ["", "## Proposta", "",
          ("- Há erros confiantes: frases acrescentadas " + json.dumps(proposed["phrases_added"], ensure_ascii=False))
          if proposed["changed"] else "- Sem erros confiantes no grupo principal: nenhuma frase nova (proposta = texto base).",
          "", "```json",
          json.dumps({"action": proposed["action"], "skip_this_cycle": proposed["skip_this_cycle"]}, indent=2),
          "```", ""]
    if main["mistakes"]:
        L += ["## Erros confiantes (grupo principal, até 20)", ""]
        for i, m in enumerate(main["mistakes"][:20], 1):
            L.append(f"{i}. `{m['ts_brt']}` {m['side']} conf={m['confidence']:.3f} ret={m['ret']*100:+.3f}% estado=`{m['state']}`")
        L.append("")
    review_path = Path(review_path)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text("\n".join(L))
    return proposed

def apply_and_maybe_trade(name, pdata, path, eqp, gcfg, profile, dec, st, price, price_row,
                          allow, cfg, trades_log, decisions_log, criteria_version, model="von",
                          strategy=None, eff=None, regime_bull=None):
    """Portões + fill simulado. `eff` = parâmetros efetivos (bot/params.py): margem de probabilidade, filtro de regime,
    horário, saídas TP/SL/trailing, teto de exposição e custos da execução. Sem `eff`, comportamento antigo."""
    eff = eff or {}
    fees, market = P.fees_market(eff, cfg) if eff else (cfg["fees"], cfg["market"])
    chosen = dec["chosen_action"]
    extra = []
    info = {}
    if eff:
        ex = eff.get("exits") or {}
        if allow and ex.get("enabled"):
            why = P.check_exit(pdata, ex, price)
            if why:
                before = float(pdata["sol"])
                try:
                    tr_x = sim_trade("sell", pdata, gcfg, fees, market, price, str(uuid.uuid4()), trades_log, strategy=strategy)
                except Exception as e:
                    tr_x = None
                    info["exit_error"] = f"{type(e).__name__}:{e}"
                if tr_x:
                    P.track_fill(pdata, "sell", before, tr_x["fill"], price)
                    pdata["reentry_block_until"] = time.time() + 60 * float(ex.get("reentry_cooldown_min", 30))
                    write_json(path, pdata)
                info.update(exit_reason=why, exit_traded=bool(tr_x))
        chosen, rr = P.regime_block(eff, chosen, regime_bull)
        if rr:
            info["model_action"] = dec["chosen_action"]
        extra += rr + P.pre_gate(eff, chosen, pdata, brt_now().hour, time.time())
    gates = apply_gates(
        chosen, dec["confidence"], dec["skip_noul"], pdata, gcfg, price,
        probabilities=dec.get("probabilities"), profile=profile,
        margin_gate=gcfg.get("margin_gate") if eff else None,
    )
    final = gates["final_action"] if allow else "hold"
    if any(r in ("outside_hours", "reentry_cooldown") for r in extra):
        final = "hold"
    if not allow:
        extra.append("run_ended")
    g_trade = gcfg
    if final == "buy" and eff:
        g_trade, why = P.cap_buy(gcfg, pdata, price)
        if why:
            final = "hold"
            extra.append(why)
    did = str(uuid.uuid4())
    traded = False
    if allow and final in ("buy", "sell"):
        try:
            before = float(pdata["sol"])
            tr = sim_trade(final, pdata, g_trade, fees, market, price, did, trades_log, strategy=strategy)
            traded = tr is not None
            if traded and (eff.get("exits") or {}).get("enabled"):
                P.track_fill(pdata, final, before, tr["fill"], price)
            write_json(path, pdata)
        except Exception as e:
            final = "hold"
            extra.append(f"sim_err:{type(e).__name__}")
    eq = equity(pdata, price)
    append_jsonl(eqp, {
        "ts": time.time(), "price": price, "sol": pdata["sol"], "usdt": pdata["usdt"],
        "equity": eq, "bh_equity": bh_equity(pdata, price),
        "all_usdt_equity": float(pdata["benchmark_all_usdt"]["usdt"]),
        "trade_count": pdata["trade_count"], "portfolio": name,
    })
    row = {
        "ts": time.time(), "ts_brt": brt_iso(), "decision_id": did, "portfolio": name,
        "gate_profile": profile,
        "state": st["state"], "features": st["features"], "price_usd": price,
        "price_source": price_row.get("source"),
        "chosen_action": chosen, "probabilities": dec["probabilities"],
        "confidence": dec["confidence"], "skip_noul": dec["skip_noul"],
        "final_action": final, "gate_reasons": gates["gate_reasons"] + extra,
        "blocked_trade": gates["blocked_trade"] or (final == "hold" and chosen in ("buy", "sell")),
        "latency_ms": dec["latency_ms"], "von_ok": dec["ok"], "von_error": dec.get("error"),
        "fail_closed": dec.get("fail_closed", False), "traded": traded,
        "equity_usd": eq, "sol": pdata["sol"], "usdt": pdata["usdt"],
        "criteria_version": criteria_version,
        "model": model or dec.get("model") or "von",
        "strategy": strategy,
        **info,
    }
    append_jsonl(decisions_log, row)
    return row

def main() -> int:
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)
    cfg = load_cfg()
    assert_no_keys(cfg)
    end_at = datetime.fromisoformat(cfg["end_at_brt"])
    review_at = datetime.fromisoformat(cfg["night_review_at_brt"])
    cycle = float(cfg["cycle_seconds"])
    # Parâmetros por portfólio: params.json via bot/params.py (hot reload por mtime; overlay do dashboard por cima).
    eff_b, eff_r = P.effective("baseline"), P.effective("relaxed")

    prices_log = ROOT / "data" / "prices.jsonl"
    decisions_log = ROOT / "logs" / "decisions.jsonl"
    trades_log = ROOT / "logs" / "trades.jsonl"
    status_path = ROOT / "status.json"
    port_path = ROOT / "data" / "portfolio_baseline.json"
    eq_path = ROOT / "data" / "equity_baseline.jsonl"
    port_rel_path = ROOT / "data" / "portfolio_relaxed.json"
    eq_rel_path = ROOT / "data" / "equity_relaxed.jsonl"
    port_v2_path = ROOT / "data" / "portfolio_v2.json"
    eq_v2_path = ROOT / "data" / "equity_v2.jsonl"
    crit_path = ROOT / "criteria_baseline.json"
    crit_v2_path = ROOT / "criteria_v2.json"
    # Arranque do v2: revisão única no dia de night_review_at_brt. O flag "revisão feita" é criteria_v2.json
    # (critérios em uso pelo v2) OU o .md desse dia, para que arquivar reviews/ num recomeço não relance a
    # revisão nem sobrescreva criteria_v2.json.
    review_day = datetime.fromisoformat(cfg["night_review_at_brt"]).strftime("%Y-%m-%d")
    review_path = ROOT / "reviews" / f"{review_day}.md"

    for d in (ROOT / "data", ROOT / "logs", ROOT / "reviews", ROOT / "run"):
        d.mkdir(parents=True, exist_ok=True)

    price_row = fetch_sol_price(cfg, prices_log)
    price = float(price_row["price_usd"])
    bal = cfg["starting_balances"]
    base = new_portfolio(port_path, bal["sol"], bal["usdt"], price, "baseline")
    relaxed = new_portfolio(port_rel_path, bal["sol"], bal["usdt"],
                            float(base.get("start_price") or price), "relaxed")
    criteria = load_criteria(crit_path)
    criteria_v2 = load_criteria(crit_v2_path) if crit_v2_path.exists() else None
    v2 = None
    # Init bug fix: previously required port_v2_path.exists(), so if review wrote
    # criteria_v2.json but portfolio_v2.json was missing (or bot restarted before
    # new_portfolio ran), review_done stayed True and v2 never started.
    # Now: any time criteria_v2 exists, ensure portfolio_v2 is loaded/created.
    if criteria_v2 is not None:
        v2 = new_portfolio(port_v2_path, bal["sol"], bal["usdt"], float(base.get("start_price") or price), "v2")

    cycles = errors = skipped_no_price = 0
    started = time.time()
    review_done = crit_v2_path.exists() or review_path.exists()
    finished = False
    _g2 = P.effective("v2")["gates"]
    v2_gate_note = (
        f"v2_gate=relaxed conf>={_g2['min_confidence']} "
        f"margin>={_g2.get('min_prob_margin')} skip<{_g2['max_skip_noul']}"
    )
    # Extra local/hosted model portfolios (do NOT alter von baseline/relaxed/v2).
    models_cfg = load_models_cfg()
    extra_ports = {}  # name -> {pdata, path, eqp, model_id, profile, gcfg}
    start_price = float(base.get("start_price") or price)
    model_start_brt = brt_iso()
    for mid, bcfg in (models_cfg.get("backends") or {}).items():
        if mid == "von":
            continue
        if not bcfg.get("enabled"):
            continue
        if mid == "jev":
            # Hosted jev: only run portfolios when key present
            jst = jev_key_status(models_cfg)
            if jst["status"] != "ready":
                print(f"jev portfolios skipped: {jst['status']}", flush=True)
                continue
        for pname in bcfg.get("sol_portfolios") or []:
            if pname in ("baseline", "relaxed", "v2"):
                continue  # never shadow von names
            # Gate profile label from suffix (os valores vêm de params.json a cada ciclo)
            profile = "relaxed" if pname.endswith("_relaxed") else "baseline"  # _article = baseline conf>=0.6
            ppath = ROOT / "data" / f"portfolio_{pname}.json"
            epath = ROOT / "data" / f"equity_{pname}.jsonl"
            pdata = new_portfolio(ppath, bal["sol"], bal["usdt"], start_price, pname)
            # stamp start time once
            if "started_brt" not in pdata:
                pdata["started_brt"] = model_start_brt
                pdata["model"] = mid
                write_json(ppath, pdata)
            extra_ports[pname] = {
                "pdata": pdata, "path": ppath, "eqp": epath,
                "model_id": mid, "profile": profile, "bcfg": bcfg,
            }

    # Hybrid copy of von-relaxed: max 2 trades/h + SOL EMA regime buy filter (no extra model call)
    hybrid_name = "hybrid_von_relaxed_cap2"
    hybrid_path = ROOT / "data" / f"portfolio_{hybrid_name}.json"
    hybrid_eq = ROOT / "data" / f"equity_{hybrid_name}.jsonl"
    hybrid = new_portfolio(hybrid_path, bal["sol"], bal["usdt"], start_price, hybrid_name)
    if "started_brt" not in hybrid:
        hybrid["started_brt"] = model_start_brt
        hybrid["strategy"] = "rule:hybrid_von_relaxed_cap2"
        hybrid["model"] = "von+rules"
        write_json(hybrid_path, hybrid)

    print(
        f"sol_bot start pid={os.getpid()} price={price:.4f} src={price_row.get('source')} "
        f"gates_base={eff_b['gates']['min_confidence']} gates_relaxed={eff_r['gates']['min_confidence']}/"
        f"margin={eff_r['gates'].get('min_prob_margin')} params={P.params_path()} "
        f"v2={'on' if v2 is not None else 'off'} {v2_gate_note} "
        f"extra_ports={list(extra_ports)}",
        flush=True,
    )
    # Record mid-day starts
    starts_note = ROOT / "reports" / "models_start.md"
    if extra_ports and not starts_note.exists():
        lines = [
            "# Extra model portfolios — start times (BRT)\n",
            f"Generated: {model_start_brt}\n",
            "These portfolios started mid-day (not at day open). Same initial balances as von.\n",
        ]
        for n, meta in extra_ports.items():
            lines.append(f"- **{n}** model=`{meta['model_id']}` gate=`{meta['profile']}` started={meta['pdata'].get('started_brt')}\n")
        lines.append("\nScheduling: extra backends called **concurrently** each cycle alongside von (fits in 15s).\n")
        starts_note.write_text("".join(lines))

    _crit_v2_mtime = crit_v2_path.stat().st_mtime if crit_v2_path.exists() else None
    while not STOP:
        t0 = time.time()
        now = brt_now()
        allow = now < end_at
        # Hot-reload criteria_v2.json when the nightly job rewrites it (no restart needed).
        try:
            _m = crit_v2_path.stat().st_mtime if crit_v2_path.exists() else None
            if _m is not None and _m != _crit_v2_mtime:
                criteria_v2 = load_criteria(crit_v2_path)
                _crit_v2_mtime = _m
                print(f"criteria_v2 reloaded at {brt_iso()}", flush=True)
        except Exception as _e:
            print(f"criteria_v2 reload failed: {_e}", flush=True)
        row_h = None
        sol_bull = None
        if now >= end_at and not finished:
            finished = True
            print("end window reached", flush=True)
        try:
            try:
                price_row = fetch_sol_price(cfg, prices_log)
                price = float(price_row["price_usd"])
            except Exception as e:
                skipped_no_price += 1
                print(f"skipped_no_price SOL: {e}", flush=True)
                write_json(status_path, {
                    "ok": True, "ts": time.time(), "ts_brt": brt_iso(), "cycles": cycles,
                    "errors": errors, "skipped_no_price": skipped_no_price,
                    "pid": os.getpid(), "finished": finished or not allow,
                    "note": "skipped_no_price", "paper_only": True,
                })
                sleep_for = max(0.5, cycle - (time.time() - t0))
                end_sleep = time.time() + sleep_for
                while time.time() < end_sleep and not STOP:
                    time.sleep(max(0.0, min(0.5, end_sleep - time.time())))
                continue

            history = read_jsonl(prices_log)[-2000:]

            if (not review_done) and now >= review_at:
                print("night review...", flush=True)
                criteria_v2 = night_review(decisions_log, trades_log, crit_path, review_path, crit_v2_path,
                                           cfg=cfg, prices_log=prices_log)
                v2 = new_portfolio(port_v2_path, bal["sol"], bal["usdt"], float(base.get("start_price") or price), "v2")
                review_done = True

            # Hot-reload params (params.json + overlay do dashboard). Does not wipe portfolio state.
            params_overlay = P.STORE.overlay()
            pause_sol = bool((params_overlay.get("bots") or {}).get("sol_paused"))
            allow_trade = allow and not pause_sol
            eff_b, eff_r, eff_v = P.effective("baseline"), P.effective("relaxed"), P.effective("v2")
            g_base_eff, g_rel_eff, g_v2_eff = eff_b["gates"], eff_r["gates"], eff_v["gates"]
            allow_b = allow_trade and not eff_b["paused"]
            allow_r = allow_trade and not eff_r["paused"]
            allow_v = allow_trade and not eff_v["paused"]

            # Shared market state from baseline position; one von call for baseline+relaxed
            st = build_state(history, position_word(base), base.get("recent_pnl_mood") or "neutral")
            dec = von_system_one(cfg["von"]["base_url"], st["state"], criteria, cfg["von"].get("timeout_seconds", 30))

            # Tag von decisions with model field (consumers that ignore unknown fields keep working)
            if "model" not in dec:
                dec = dict(dec); dec["model"] = "von"
            row_b = apply_and_maybe_trade(
                "baseline", base, port_path, eq_path, g_base_eff, "baseline",
                dec, st, price, price_row, allow_b, cfg, trades_log, decisions_log,
                criteria.get("version", "baseline"), model="von", eff=eff_b,
            )
            write_json(port_path, base)

            row_r = apply_and_maybe_trade(
                "relaxed", relaxed, port_rel_path, eq_rel_path, g_rel_eff, "relaxed",
                dec, st, price, price_row, allow_r, cfg, trades_log, decisions_log,
                criteria.get("version", "baseline"), model="von", eff=eff_r,
            )
            write_json(port_rel_path, relaxed)

            # --- Hybrid: reuse von relaxed decision; teto de trades/h e filtro de regime vêm de params.json
            #     (types.hybrid + portfolios.hybrid_von_relaxed_cap2) ---
            row_h = None
            sol_bull = P.sol_regime_bull()
            h_cfg = ((cfg.get("rule_strategies") or {}).get("strategies") or {}).get("hybrid_von_relaxed_cap2") or {}
            h_enabled = bool((cfg.get("rule_strategies") or {}).get("enabled", True)) and h_cfg.get("enabled", True)
            eff_h = P.effective("hybrid_von_relaxed_cap2")
            allow_h = allow_trade and h_enabled and not eff_h["paused"]
            st_h = build_state(history, position_word(hybrid), hybrid.get("recent_pnl_mood") or "neutral")
            row_h = apply_and_maybe_trade(
                "hybrid_von_relaxed_cap2", hybrid, hybrid_path, hybrid_eq, eff_h["gates"], "relaxed",
                dec, st_h, price, price_row, allow_h, cfg, trades_log, decisions_log,
                criteria.get("version", "baseline"), model="von+rules",
                strategy="rule:hybrid_von_relaxed_cap2", eff=eff_h, regime_bull=sol_bull,
            )
            write_json(hybrid_path, hybrid)

            row_v = None
            # If review already done but v2 somehow missing, recover without re-running review.
            if v2 is None and criteria_v2 is None and crit_v2_path.exists():
                criteria_v2 = load_criteria(crit_v2_path)
            if v2 is None and criteria_v2 is not None:
                v2 = new_portfolio(port_v2_path, bal["sol"], bal["usdt"], float(base.get("start_price") or price), "v2")
                print(f"v2 portfolio recovered/init at {brt_iso()}", flush=True)

            if v2 is not None and criteria_v2 is not None:
                # Own von call with criteria_v2 text. Gate = RELAXED (von conf never exceeds ~0.40;
                # baseline 0.6 gate would never trade). Extra von call (~0.3s) fits in 15s cycle;
                # alternating base/v2 criteria is acceptable if latency becomes a problem.
                st_v = build_state(history, position_word(v2), v2.get("recent_pnl_mood") or "neutral")
                dec_v = von_system_one(cfg["von"]["base_url"], st_v["state"], criteria_v2, cfg["von"].get("timeout_seconds", 30))
                if "model" not in dec_v:
                    dec_v = dict(dec_v); dec_v["model"] = "von"
                row_v = apply_and_maybe_trade(
                    "v2", v2, port_v2_path, eq_v2_path, g_v2_eff, "relaxed",
                    dec_v, st_v, price, price_row, allow_v, cfg, trades_log, decisions_log,
                    criteria_v2.get("version", "v2"), model="von", eff=eff_v,
                )
                write_json(port_v2_path, v2)

            cycles += 1
            status = {
                "ok": True, "ts": time.time(), "ts_brt": brt_iso(), "cycles": cycles, "errors": errors,
                "skipped_no_price": skipped_no_price,
                "pid": os.getpid(), "finished": finished or not allow,
                "price_usd": price, "price_source": price_row.get("source"),
                "fabricated": False,
                "baseline": {
                    "sol": base["sol"], "usdt": base["usdt"], "equity_usd": row_b["equity_usd"],
                    "last_final": row_b["final_action"], "last_chosen": row_b["chosen_action"],
                    "last_conf": row_b["confidence"], "last_skip": row_b["skip_noul"],
                    "last_latency_ms": row_b["latency_ms"], "trades": base["trade_count"],
                    "state": row_b["state"], "gate_reasons": row_b["gate_reasons"],
                },
                "relaxed": {
                    "sol": relaxed["sol"], "usdt": relaxed["usdt"], "equity_usd": row_r["equity_usd"],
                    "last_final": row_r["final_action"], "last_chosen": row_r["chosen_action"],
                    "last_conf": row_r["confidence"], "trades": relaxed["trade_count"],
                    "gate_reasons": row_r["gate_reasons"],
                },
                "hybrid_von_relaxed_cap2": None if row_h is None else {
                    "sol": hybrid["sol"], "usdt": hybrid["usdt"], "equity_usd": row_h["equity_usd"],
                    "last_final": row_h["final_action"], "last_chosen": row_h["chosen_action"],
                    "last_conf": row_h["confidence"], "trades": hybrid["trade_count"],
                    "gate_reasons": row_h["gate_reasons"], "model": "von+rules",
                    "strategy": "rule:hybrid_von_relaxed_cap2",
                    "sol_regime_bull": sol_bull,
                    "started_brt": hybrid.get("started_brt"),
                },
                "v2": None if row_v is None else {
                    "sol": v2["sol"], "usdt": v2["usdt"], "equity_usd": row_v["equity_usd"],
                    "last_final": row_v["final_action"], "last_chosen": row_v["chosen_action"],
                    "last_conf": row_v["confidence"], "last_skip": row_v["skip_noul"],
                    "last_latency_ms": row_v["latency_ms"], "trades": v2["trade_count"],
                    "state": row_v["state"], "gate_reasons": row_v["gate_reasons"],
                    "gate_profile": "relaxed",
                },
                "gates": {
                    "baseline": {"min_confidence": g_base_eff["min_confidence"], "max_skip_noul": g_base_eff["max_skip_noul"]},
                    "relaxed": {
                        "min_confidence": g_rel_eff["min_confidence"],
                        "min_prob_margin": g_rel_eff.get("min_prob_margin"),
                        "max_skip_noul": g_rel_eff["max_skip_noul"],
                    },
                    "v2": {
                        "min_confidence": g_v2_eff["min_confidence"],
                        "min_prob_margin": g_v2_eff.get("min_prob_margin"),
                        "max_skip_noul": g_v2_eff["max_skip_noul"],
                        "note": "v2 uses relaxed gate + criteria_v2.json von call",
                    },
                },
                "params": {"path": str(P.params_path()), "errors": dict(P.STORE.errors), "doc_errors": list(P.STORE.doc_errors)},
                "review_done": review_done, "uptime_seconds": round(time.time() - started, 1),
                "paper_only": True, "end_at_brt": cfg["end_at_brt"],
            }

            # --- Extra model backends (concurrent). Von path above unchanged. ---
            extra_rows = {}
            models_cfg = load_models_cfg()  # hot-reload enabled flags
            # Build jobs: one decision call per enabled non-von model that still has portfolios
            jobs = []
            model_to_ports = {}
            for pname, meta in list(extra_ports.items()):
                mid = meta["model_id"]
                bcfg = (models_cfg.get("backends") or {}).get(mid) or meta["bcfg"]
                if not bcfg.get("enabled"):
                    continue
                if mid == "jev" and jev_key_status(models_cfg)["status"] != "ready":
                    continue
                # per-portfolio pause
                ppause = P.effective(pname)["paused"]
                if pause_sol or ppause:
                    continue
                model_to_ports.setdefault(mid, []).append(pname)
                if mid not in {j[0] for j in jobs}:
                    # Use shared market state text (same adjectives); own position word per first port
                    st_m = build_state(history, position_word(meta["pdata"]), meta["pdata"].get("recent_pnl_mood") or "neutral")
                    jobs.append((mid, bcfg, st_m["state"], criteria, float(cfg.get("von", {}).get("timeout_seconds", 30))))

            decs = decide_many(jobs, max_workers=4) if jobs else {}
            for mid, port_names in model_to_ports.items():
                dec_m = decs.get(mid)
                if not dec_m:
                    continue
                for pname in port_names:
                    meta = extra_ports[pname]
                    eff_m = P.effective(pname)
                    gcfg = eff_m["gates"]
                    st_m = build_state(history, position_word(meta["pdata"]), meta["pdata"].get("recent_pnl_mood") or "neutral")
                    row_m = apply_and_maybe_trade(
                        pname, meta["pdata"], meta["path"], meta["eqp"], gcfg, meta["profile"],
                        dec_m, st_m, price, price_row, allow and not pause_sol, cfg,
                        trades_log, decisions_log, criteria.get("version", "baseline"),
                        model=mid, eff=eff_m,
                    )
                    write_json(meta["path"], meta["pdata"])
                    extra_rows[pname] = row_m
                    status[pname] = {
                        "sol": meta["pdata"]["sol"], "usdt": meta["pdata"]["usdt"],
                        "equity_usd": row_m["equity_usd"],
                        "last_final": row_m["final_action"], "last_chosen": row_m["chosen_action"],
                        "last_conf": row_m["confidence"], "trades": meta["pdata"]["trade_count"],
                        "gate_reasons": row_m["gate_reasons"], "model": mid,
                        "started_brt": meta["pdata"].get("started_brt"),
                        "latency_ms": row_m["latency_ms"],
                    }

            status["models"] = {
                mid: {
                    "enabled": bool(b.get("enabled")),
                    "label": b.get("label"),
                    "kind": b.get("kind"),
                    "base_url": b.get("base_url"),
                }
                for mid, b in (models_cfg.get("backends") or {}).items()
            }
            status["jev"] = jev_key_status(models_cfg)
            status["extra_latencies_ms"] = {mid: (decs.get(mid) or {}).get("latency_ms") for mid in decs}
            status["cycle_wall_ms"] = round((time.time() - t0) * 1000, 1)

            write_json(status_path, status)
            v2_part = (
                f"v2={row_v['final_action']} conf_v={row_v['confidence']:.3f} eq_v={row_v['equity_usd']:.4f}"
                if row_v else "v2=off"
            )
            extra_part = " ".join(
                f"{n}={extra_rows[n]['final_action']}/{extra_rows[n]['confidence']:.2f}"
                for n in sorted(extra_rows)
            ) or "extra=none"
            print(
                f"cycle={cycles} px={price:.4f} src={price_row.get('source')} "
                f"chosen={row_b['chosen_action']} conf={row_b['confidence']:.3f} "
                f"base={row_b['final_action']} rel={row_r['final_action']} {v2_part} "
                f"skip={row_b['skip_noul']:.3f} lat={row_b['latency_ms']:.0f}ms "
                f"eq_b={row_b['equity_usd']:.4f} eq_r={row_r['equity_usd']:.4f} "
                f"wall={status['cycle_wall_ms']:.0f}ms {extra_part}",
                flush=True,
            )
        except Exception as e:
            errors += 1
            print(f"cycle error: {e}\n{traceback.format_exc()}", flush=True)
            write_json(status_path, {
                "ok": False, "error": str(e), "ts_brt": brt_iso(), "cycles": cycles,
                "errors": errors, "pid": os.getpid(), "finished": finished,
            })
        if finished:
            cur = json.loads(status_path.read_text()) if status_path.exists() else {}
            cur.update({"finished": True, "finished_brt": brt_iso(), "ok": True})
            write_json(status_path, cur)
            break
        sleep_for = max(0.5, cycle - (time.time() - t0))
        end_sleep = time.time() + sleep_for
        while time.time() < end_sleep and not STOP:
            time.sleep(max(0.0, min(0.5, end_sleep - time.time())))
    print(f"sol_bot stopped cycles={cycles} errors={errors}", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
