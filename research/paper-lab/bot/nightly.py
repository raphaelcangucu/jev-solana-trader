#!/usr/bin/env python3
"""Nightly self-improvement job (paper only).

Daemon (supervised as `nightly`): runs every night at ~00:30 BRT for the previous day, and refreshes
verdict progress (data/nightly/verdicts.json) every 30 min for the dashboard.
Manual:  python bot/nightly.py --run [--dry-run] [--date YYYY-MM-DD]

Per portfolio: day + cumulative stats, verdict (inconclusivo/vencedora/perdedora with progress),
tuning eligibility, walk-forward tuning -> FORK (never modifies an original), fork lifecycle
(lead fork = base for further tuning only, never a winner verdict; trailing forks only labeled — nothing is ever stopped), v2 criteria audit
(proposal only), fill quality. Writes reviews/<run-date>.md (dry-run: reviews/dryrun_<run-date>.md),
reports/<day>.md and reports/cumulative.md (not in dry-run) and logs every change to logs/param_changes.jsonl.
"""
from __future__ import annotations
import argparse, json, os, signal, sys, time, traceback
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # código do lab (não PAPER_LAB_ROOT)
from bot.paths import ROOT, LAB_DIR  # noqa: E402
from bot.lib import BRT, brt_iso, load_cfg, write_json, append_jsonl
from bot import analytics as A, lab_registry as R, tuner as T
from bot import params as P

STATUS = ROOT / "data" / "nightly" / "status.json"
VERDICTS = ROOT / "data" / "nightly" / "verdicts.json"
STOP = False
def _sig(*_a):
    global STOP
    STOP = True

DEFAULT_TUNING = {"run_at_brt": "00:30", "eligibility": {"min_closed_rt": 30, "min_days": 7, "min_trades": 10},
                  "lead": {"min_days": 5, "min_trades": 20, "min_margin_pct": 0.5, "consistent_frac": 0.67},
                  "caps": {"per_lineage_days": 7, "total": 40}, "history_days": 14, "rotate_at_brt": "01:00"}


def tcfg():
    c = json.loads(json.dumps(DEFAULT_TUNING)); u = (load_cfg().get("tuning") or {})
    for k, v in u.items():
        if isinstance(v, dict): c.setdefault(k, {}).update(v)
        else: c[k] = v
    return c


def compute_verdicts(cat=None, tb=None):
    cat = cat or A.catalog()[0]; tb = tb or A.load_trades()
    vc = (load_cfg().get("verdict") or {})
    out = {}
    for n, m in cat.items():
        try:
            v = A.verdict(m, tb, cfg=vc)
        except Exception as e:
            v = {"portfolio": n, "verdict": "inconclusivo", "reason": f"erro: {e}", "progress": {}}
        v["status"] = m.get("status", "active"); v["lineage"] = m.get("lineage", n); v["parent"] = m.get("parent")
        out[n] = v
    write_json(VERDICTS, {"ts": time.time(), "ts_brt": brt_iso(), "verdicts": out})
    return out


def params_for(name, m=None, reg=None):
    """Parâmetros efetivos SEM overlay (base do tuning e dos forks), proveniência e erros (bot/params.py)."""
    entry = m if (m and m.get("origin") == "lab") else None
    eff, prov, errs, _meta = P.explain(name, meta=entry, use_overlay=False, registry=reg)
    return eff, prov, errs


def gates_for_meta(m, cfg):
    """Compatibilidade: portões efetivos do portfólio (params.json, sem overlay)."""
    return params_for(m["name"], m)[0]["gates"]


def fork_params_lines(e, reg):
    """Linhas do relatório com o diff do fork, o valor efetivo e a camada de onde vem (proveniência)."""
    eff, prov, errs = params_for(e["name"], dict(e, origin="lab"), reg)
    _peff, _pprov, _ = params_for(e["parent"], None, reg) if e.get("parent") else ({}, {}, [])
    out = []
    for path, layer in sorted(prov.items()):
        if layer.startswith("fork:") or layer.startswith("portfolios.") or layer == "overlay":
            sect, _, key = path.partition(".")
            val = (eff.get(sect) or {}).get(key) if isinstance(eff.get(sect), dict) else eff.get(sect)
            pv = (_peff.get(sect) or {}).get(key) if isinstance(_peff.get(sect), dict) else _peff.get(sect)
            out.append(f"`{path}` = {json.dumps(val)} (pai: {json.dumps(pv)}; camada `{layer}`)")
    if errs:
        out.append("**params inválidos (fail-closed no bot):** " + "; ".join(errs[:5]))
    return out


def tuning_parent(lineage, reg, cat):
    lead = (reg["lineages"].get(lineage) or {}).get("lead")
    return lead if lead and lead in cat and cat[lead].get("status") == "active" else lineage


def rule_tune(lin, base, m, reg, book, run_date, dry, caps):
    """Secção 4: replay walk-forward da regra (tuner.rule_search) na base do tuning (original ou lead fork) e, se houver
    candidato, um fork de regra real (`{"rule": best_diff}`, executado pelo rules_bot) com os mesmos caps do tuner.
    -> (linha do relatório, nota de cap | None)."""
    eff, _prov, perr = params_for(base, m, reg)
    if perr:
        return f"- {lin}: params inválidos na base {base}: {'; '.join(perr[:3])}", None
    r = T.rule_search(m, book.sol, book.memes.get(m["asset"]) if m["asset"] != "SOL" else book.sol, eff=eff)
    if r["status"] != "candidate":
        return f"- {lin}: {r['status']} (base {base}; atual train/val {r['current']})", None
    diff = {"rule": r["best_diff"]}
    why_txt = (f"nightly {run_date}: replay de regra 1h val {r['best'][1]:+.3f} vs {r['current'][1]:+.3f} "
               f"(train {r['best'][0]:+.3f} vs {r['current'][0]:+.3f}), {r.get('bars')} barras")
    fname, why = R.create_fork(base, diff, why_txt, dry_run=dry, caps_override=caps)
    line = f"- {lin}: candidato {json.dumps(diff)} (base {base}; atual train/val {r['current']}) → fork `{fname}` ({why})"
    return line, (f"{lin}: {why}" if fname is None else None)


def run(day=None, dry=False):
    t_start = time.time(); cfg = load_cfg(); tc = tcfg()
    now = time.time(); run_date = datetime.now(BRT).strftime("%Y-%m-%d")
    day = day or (datetime.now(BRT) - timedelta(days=1)).strftime("%Y-%m-%d")
    a, b = A.day_bounds(day); b = min(b, now)
    cat, reg = A.catalog(); tb = A.load_trades()
    L = [f"# Revisão noturna (self-improvement) — {'DRY-RUN ' if dry else ''}{run_date}",
         "", f"**Gerado:** {brt_iso()} · **Dia revisado:** {day} (00:00–24:00 BRT) · paper only · originais NUNCA são alterados (ajustes viram forks).", ""]
    # 1) verdicts
    verd = compute_verdicts(cat, tb)
    L += ["## 1. Veredito por portfólio", "",
          "Regra: **inconclusivo** até ≥30 round trips fechados E ≥21 dias (≥28 para regras 1h e filtros de regime; idealmente com um período de regime baixista de SOL observado). "
          "Só então **vencedora** (bate B&H e a barra de 6%/a USDC, p<0,05 líquido de custos por block-bootstrap, consistente em ≥3 das últimas 4 semanas) ou **perdedora** (pior que o benchmark com p<0,05). "
          "*Lead fork* = apenas base para novos ajustes, nunca veredito de vencedora.", "",
          "| Portfólio | Status | Veredito | Progresso | Motivo |", "|---|---|---|---|---|"]
    for n in sorted(verd, key=lambda k: (cat[k].get("asset", "SOL") != "SOL", k)):
        v = verd[n]; L.append(f"| {n} | {v.get('status')} | **{v['verdict']}** | {(v.get('progress') or {}).get('text','')} | {v.get('reason','')} |")
    # 2) day + cumulative stats
    tbl_day, day_rows = A.stats_table(cat, tb, a, b)
    L += ["", f"## 2. Estatísticas do dia {day}", "", A.STATS_LEGEND, "", tbl_day]
    # 3) eligibility + tuning
    el = tc["eligibility"]; L += ["", "## 3. Elegibilidade e tuning", "",
          f"Elegível se ≥{el['min_closed_rt']} round trips fechados OU (≥{el['min_days']} dias e ≥{el['min_trades']} trades). "
          "Espaço de busca por tipo de teste em params.json (`tuning`: parâmetros, limites, passo máximo relativo; padrão ±20% por noite), "
          "limites de segurança do resolver (buy_fraction ≤0,5 e trades/h ≤8 salvo `limits`, sem alavancagem), walk-forward 70/30, penalidade por trade, melhoria mínima exigida. "
          "O diff de cada fork é validado pelo resolver antes de criar.", "",
          "| Linhagem | Base do tuning | Tipo | RT fechados | Trades | Dias | Elegível | Resultado |", "|---|---|---|---|---|---|---|---|"]
    lineages = {}
    for n, m in cat.items():
        if m.get("origin") == "original" or m.get("is_original"):
            lineages[n] = n
    tuning_log = []; cap_notes = []
    for lin in sorted(lineages, key=lambda k: (cat[k].get("asset", "SOL") != "SOL", k)):
        base = tuning_parent(lin, reg, cat); m = cat[base]
        cc = A.cumulative_counts(m, tb)
        elig = cc["closed_rt"] >= el["min_closed_rt"] or (cc["days"] >= el["min_days"] and cc["trades"] >= el["min_trades"])
        res = "dados insuficientes"
        if elig:
            try:
                if m.get("kind") == "rule":
                    res = "elegível; replay de regra na seção 4 (candidato → fork de regra no rules_bot)"
                    tuning_log.append((lin, base, "rule", None))
                else:
                    t1 = now; t0 = max(m["start_ts"], now - tc["history_days"] * 86400)
                    cls = m.get("cls", "sol" if m.get("asset") == "SOL" else "meme")
                    if m.get("kind") == "ensemble":
                        srcs = ["baseline", "poorjev_baseline", "laya_baseline"] if cls == "sol" else \
                               [f"meme_{m['asset']}_baseline", f"{m['asset']}_poorjev_baseline", f"{m['asset']}_laya_baseline"]
                        mo = lambda pn: "von" if (pn == "baseline" or (pn or "").startswith("meme_")) else ("poorjev" if "poorjev" in pn else "laya")
                        data = {"dec": T._decisions(cls, srcs, t0 - 3 * 3600, t1), "px": T._prices(m["asset"], t0, t1), "model_of": mo,
                                "window": 480 if cls == "sol" else 200, "span": 30 if cls == "sol" else 120}
                    else:
                        data = {"dec": T._decisions(cls, [m["source"]], t0, t1), "px": T._prices(m["asset"], t0, t1)}
                    st = m["state"]; start = (float(st.get("start_sol") or st.get("start_token") or 0), float(st["start_usdt"]))
                    eff, _prov, perr = params_for(base, m, reg)
                    if perr:
                        raise ValueError("params inválidos: " + "; ".join(perr[:3]))
                    c_bps, n_c = T.cost_bps(cls, now)
                    r = T.search(m, eff, t0, t1, start, c_bps, data)
                    if r["status"] == "candidate":
                        fname, why = R.create_fork(base, r["best_diff"], f"nightly {run_date}: val {r['best']['val']:+.3f} vs {r['current']['val']:+.3f} (train {r['best']['train']:+.3f} vs {r['current']['train']:+.3f}), custo {c_bps:.1f} bps", dry_run=dry, caps_override=tc["caps"])
                        if fname is None:
                            cap_notes.append(f"{lin}: {why}")
                        res = f"candidato {json.dumps(r['best_diff'])} → fork `{fname}` ({why})"
                    else:
                        res = f"{r['status']} (custo {c_bps:.1f} bps, {r.get('n_candidates',0)} candidatos; espaço {', '.join(r.get('space') or []) or '–'})"
                    tuning_log.append((lin, base, m.get("kind"), r))
            except Exception as ex:
                res = f"erro no tuning: {ex}"
        L.append(f"| {lin} | {base} | {m.get('kind')} | {cc['closed_rt']} | {cc['trades']} | {cc['days']:.1f} | {'sim' if elig else 'não'} | {res} |")
    # 4) rule replay for eligible rule lineages
    rule_lins = [x for x in tuning_log if x[2] == "rule"]
    L += ["", "## 4. Regras 1h (replay walk-forward em barras)", ""]
    if rule_lins:
        try:
            from bot.rules_engine import CandleBook
            book = CandleBook(); book.warm_up()
            for lin, base, _, _ in rule_lins:
                try:
                    line, note = rule_tune(lin, base, cat[base], reg, book, run_date, dry, tc["caps"])
                except Exception as ex:
                    line, note = f"- {lin}: erro no replay/fork de regra: {ex}", None
                L.append(line)
                if note:
                    cap_notes.append(note)
        except Exception as ex:
            L.append(f"- erro no replay de regras: {ex}")
    else:
        L.append("- nenhuma estratégia de regra elegível (dados insuficientes).")
    # 5) fork lifecycle
    L += ["", "## 5. Forks (linhagens): lead fork e rótulos", "",
          f"Nada é desativado ou aposentado: originais e forks rodam indefinidamente. Criação limitada a 1 fork por linhagem a cada {tc['caps']['per_lineage_days']} dias e {tc['caps']['total']} forks no total. "
          f"Lead fork exige ≥{tc['lead']['min_days']} dias e ≥{tc['lead']['min_trades']} trades desde a criação, margem ≥{tc['lead']['min_margin_pct']}pp sobre o pai e à frente em ≥{int(tc['lead']['consistent_frac']*100)}% dos dias. "
          "**Lead fork = só a base para novos ajustes, não é veredito de vencedora.** Forks que perdem do pai recebem o rótulo 'atrás da original'. "
          "Forks da revisão autónoma (`who=claude-night`, scripts/night_cli.py: parâmetros ou critérios de texto) seguem os limites de "
          "`config.json:claude_night` e são acompanhados aqui como os outros.", ""]
    n_forks = sum(1 for e in reg["portfolios"].values() if e.get("parent"))
    L.append(f"- Forks existentes: {n_forks}/{tc['caps']['total']}" + (" — **cap total atingido: novos forks não serão criados** (os existentes continuam)." if n_forks >= tc["caps"]["total"] else ""))
    for note in cap_notes:
        L.append(f"- criação bloqueada por cap: {note}")
    forks = [e for e in reg["portfolios"].values() if e.get("parent")]
    if not forks:
        L.append("- nenhum fork ainda.")
    for e in forks:
        m = cat[e["name"]]; par = cat.get(e["parent"])
        cc = A.cumulative_counts(m, tb)
        if not par:
            L.append(f"- {e['name']}: pai {e['parent']} não encontrado"); continue
        daily = []
        d0 = datetime.fromtimestamp(m["start_ts"], BRT).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        while d0.timestamp() + 86400 <= now:
            fa = A.window_stats(m, tb, d0.timestamp(), d0.timestamp() + 86400); pa = A.window_stats(par, tb, d0.timestamp(), d0.timestamp() + 86400)
            if not fa.get("empty") and not pa.get("empty"):
                daily.append(fa["pnl_pct"] - pa["pnl_pct"])
            d0 += timedelta(days=1)
        tot_f = A.window_stats(m, tb, m["start_ts"], now); tot_p = A.window_stats(par, tb, m["start_ts"], now)
        both = not tot_f.get("empty") and not tot_p.get("empty")
        margin = (tot_f.get("pnl_pct", 0) - tot_p.get("pnl_pct", 0)) if both else 0.0
        skill = ((tot_f.get("ex_exposure") or 0) - (tot_p.get("ex_exposure") or 0)) if both else None
        ahead = sum(1 for x in daily if x > 0) / len(daily) if daily else 0
        lab_txt = "em observação"
        if cc["days"] >= tc["lead"]["min_days"] and cc["trades"] >= tc["lead"]["min_trades"]:
            if margin >= tc["lead"]["min_margin_pct"] and ahead >= tc["lead"]["consistent_frac"]:
                lab_txt = "lead fork (base para tuning — não é veredito)"
                if not dry: R.set_lead(e["lineage"], e["name"], f"margem {margin:+.2f}pp, à frente {ahead:.0%} dos dias")
            elif margin < 0:
                lab_txt = "atrás da original"
        elif margin < 0 and daily:
            lab_txt = "atrás da original (amostra ainda pequena)"
        if not dry:
            R.label(e["name"], lab_txt, f"margem {margin:+.2f}pp, à frente {ahead:.0%} de {len(daily)} dias")
        L.append(f"- {e['name']} (pai {e['parent']}; criado por `{R.fork_who(e)}`; {R.describe_fork(e)}): {cc['days']:.1f} d, {cc['trades']} trades, "
                 f"margem {margin:+.2f}pp" + (f", habilidade {skill:+.1f} US$" if skill is not None else "")
                 + f", à frente {ahead:.0%} de {len(daily)} dias → **{lab_txt}** (continua rodando)")
        if e.get("reason"):
            L.append(f"  - motivo/hipótese: {str(e['reason'])[:300]}")
        cref = (e.get("params_diff") or {}).get("criteria")
        if cref:
            try:
                from bot import lab_criteria as LC
                L.append(f"  - critérios ({str(cref.get('sha256'))[:10]}): {LC.summary(LC.load_ref(cref)[0])}")
            except Exception as ex:
                L.append(f"  - critérios inválidos ({ex}): o lab_bot segura (hold)")
        try:
            for ln in fork_params_lines(e, reg):
                L.append(f"  - {ln}")
        except Exception as ex:
            L.append(f"  - params: erro ao resolver ({ex})")
    # 6) v2 criteria audit (proposal only; original v2 keeps its criteria)
    L += ["", "## 6. Revisão de critérios v2 (von) — só proposta", ""]
    try:
        import bot.sol_bot as SB
        prop = ROOT / "reviews" / f"criteria_v2_proposed_{run_date}.json"
        tmp = ROOT / "data" / "nightly" / "v2_review_tmp.md"
        if dry:
            prop = ROOT / "data" / "nightly" / f"criteria_v2_proposed_dryrun_{run_date}.json"
        p = SB.night_review(ROOT / "logs" / "decisions.jsonl", ROOT / "logs" / "trades.jsonl", ROOT / "criteria_baseline.json",
                            tmp, prop, day=day, cfg=cfg, prices_log=ROOT / "data" / "prices.jsonl")
        cur = json.loads((ROOT / "criteria_v2.json").read_text())
        same = cur.get("action") == p.get("action") and cur.get("skip_this_cycle") == p.get("skip_this_cycle")
        au = p["audit"]; fx = au.get("fixed_bar_compare") or {}
        hr = lambda x: "–" if x is None else f"{x:.0%}"
        L.append(f"- Auditoria por percentil ({au['rule']}, corte {A.fmt(au['cutoff'], 3)}; grupo {au.get('group')}; dia {day}): "
                 f"{au['n_answered']} respondidas, {au['n_confident']} chamadas buy/sell confiantes ({au['n_confident_acted']} viraram ordem), "
                 f"{au['n_resolved']} resolvidas a {int(au['horizon_s'])} s, **{au['n_mistakes']} erros** ({au.get('mistake_episodes')} episódios), hit rate {hr(au['hit_rate'])}; "
                 f"palavras dos erros {au['lose_words'] or '–'}.")
        L.append(f"- Comparação com a barra fixa ({fx.get('rule')}): {fx.get('n_confident')} confiantes, {fx.get('n_mistakes')} erros.")
        L.append(f"- {'Frases novas: ' + json.dumps(p.get('phrases_added'), ensure_ascii=False) if p.get('changed') else 'Sem erros confiantes: nenhuma frase nova (proposta = critérios base).'}")
        L.append(f"- Proposta salva em `{prop.relative_to(ROOT)}`; {'idêntica aos critérios atuais' if same else 'DIFERENTE dos critérios atuais'}. "
                 "O portfólio v2 original NÃO é alterado; forks com critério de texto novo existem via `scripts/night_cli.py criteria-fork` (revisão autónoma, uma chamada extra ao modelo por ciclo, com cache). "
                 f"Resumo em `{tmp.relative_to(ROOT)}`.")
    except Exception as ex:
        L.append(f"- erro na auditoria v2: {ex}")
    # 7) fill quality
    fq_day = A.fill_quality(a, b); fq_all = A.fill_quality(0, now)
    L += ["", "## 7. Qualidade de fills", "",
          f"- Dia: {fq_day['mark_fallbacks']}/{fq_day['market_fills']} fills a mercado caíram no fallback de mark ({A.fmt((fq_day['fallback_rate'] or 0)*100,1)}%); motivos {fq_day['reasons']}; eventos de cotação {fq_day['quote_events']}",
          f"- Acumulado: {fq_all['mark_fallbacks']}/{fq_all['market_fills']} ({A.fmt((fq_all['fallback_rate'] or 0)*100,1)}%)"]
    # 8) params.json: validação de todos os portfólios (fail-closed nos bots se houver erros)
    L += ["", "## 8. Parâmetros por tipo de teste (params.json)", ""]
    try:
        doc = P.STORE.doc()
        bad = P.check_all(doc, reg, P.STORE.overlay()) if doc is not None else {}
        L.append(f"- Ficheiro: `{P.params_path()}`; erros do documento: {P.STORE.doc_errors or 'nenhum'}.")
        L.append(f"- Portfólios com parâmetros inválidos (com overlay): {len(bad)}" + (":" if bad else "."))
        for n, errs in sorted(bad.items()):
            L.append(f"  - {n}: {'; '.join(errs[:3])}")
        L.append("- Tabela completa e proveniência: `python scripts/params_check.py [--name <portfólio>]`.")
    except Exception as ex:
        L.append(f"- erro ao validar params: {ex}")
    L += ["", f"_Tempo de execução: {time.time()-t_start:.1f} s._", ""]
    out = ROOT / "reviews" / (f"dryrun_{run_date}.md" if dry else f"{run_date}.md")
    if not dry and out.exists():
        out = ROOT / "reviews" / f"{run_date}_nightly.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L))
    if not dry:
        try:
            import subprocess
            subprocess.run([sys.executable, str(LAB_DIR / "scripts" / "report.py"), "--day", day], timeout=600)
            subprocess.run([sys.executable, str(LAB_DIR / "scripts" / "report.py"), "--cumulative"], timeout=600)
        except Exception as ex:
            print(f"report generation failed: {ex}", flush=True)
    return out


def next_run_ts(hhmm):
    h, m = map(int, hhmm.split(":"))
    n = datetime.now(BRT); t = n.replace(hour=h, minute=m, second=0, microsecond=0)
    if t <= n: t += timedelta(days=1)
    return t.timestamp()


def daemon():
    signal.signal(signal.SIGTERM, _sig); signal.signal(signal.SIGINT, _sig)
    tc = tcfg(); nxt = next_run_ts(tc["run_at_brt"]); nrot = next_run_ts(tc.get("rotate_at_brt", "01:00")); last_v = 0; last = None; last_rot = None
    print(f"nightly daemon pid={os.getpid()} next_run={datetime.fromtimestamp(nxt, BRT).isoformat()}", flush=True)
    while not STOP:
        try:
            if time.time() - last_v > 1800:
                compute_verdicts(); last_v = time.time()
            if time.time() >= nrot:
                from bot import logio
                last_rot = logio.rotate_all(); last_rot["ts_brt"] = brt_iso()
                print(f"log rotation: {json.dumps(last_rot)[:500]}", flush=True)
                nrot = next_run_ts(tcfg().get("rotate_at_brt", "01:00"))
            if time.time() >= nxt:
                print(f"nightly run start {brt_iso()}", flush=True)
                out = run(); last = {"ts_brt": brt_iso(), "review": str(out)}
                print(f"nightly run done -> {out}", flush=True)
                nxt = next_run_ts(tcfg()["run_at_brt"])
            write_json(STATUS, {"ok": True, "ts": time.time(), "ts_brt": brt_iso(), "pid": os.getpid(), "finished": False,
                                "next_run_brt": datetime.fromtimestamp(nxt, BRT).isoformat(), "next_rotation_brt": datetime.fromtimestamp(nrot, BRT).isoformat(),
                                "last_run": last, "last_rotation": last_rot, "paper_only": True})
        except Exception as ex:
            print(f"nightly error: {ex}\n{traceback.format_exc()}", flush=True)
            write_json(STATUS, {"ok": False, "error": str(ex), "ts_brt": brt_iso(), "pid": os.getpid(), "finished": False,
                                "next_run_brt": datetime.fromtimestamp(nxt, BRT).isoformat()})
            nxt = max(nxt, time.time() + 600) if time.time() >= nxt else nxt
        for _ in range(60):
            if STOP: break
            time.sleep(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--date")
    ap.add_argument("--verdicts", action="store_true")
    x = ap.parse_args()
    if x.verdicts:
        v = compute_verdicts(); print(json.dumps({k: (d["verdict"], d["progress"].get("text")) for k, d in v.items()}, ensure_ascii=False, indent=0))
    elif x.run or x.dry_run:
        print(run(x.date, dry=x.dry_run))
    else:
        daemon()
