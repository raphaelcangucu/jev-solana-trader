#!/usr/bin/env python3
"""Compara a auditoria da revisão noturna com a barra fixa antiga (conf > 0,8) e com cortes por percentil
(P80/P90/P95) nos logs REAIS do laboratório. Só leitura: escreve apenas o ficheiro --out.

    PAPER_LAB_ROOT=/caminho/para/paper python scripts/compare_review_cutoffs.py \\
        --out archive/run_1000usd_2026-09-24/reviews/percentile_vs_fixed_0.8.md \\
        --extra-run archive/run_52usd_2026-09-24

Grupos: SOL por família (von baseline+relaxed = uma chamada partilhada, fundida por dedupe; v2; híbrido;
laya; poorjev), memes por moeda e modelo (+ agregado por modelo), lab por portfólio, e auditoria de TODOS os
trades (sem corte de confiança; os logs de trades não são rotacionados). Definições em bot/confidence_audit.py.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from bot.paths import ROOT as DEFAULT_ROOT  # noqa: E402
from bot import confidence_audit as CA  # noqa: E402
from bot import logio  # noqa: E402

BRT = CA.BRT
SYMS = ["BONK", "FARTCOIN", "GOAT", "MEW", "PNUT", "POPCAT", "WIF"]


def f(x, n=3, pct=False):
    if x is None:
        return "–"
    return f"{x*100:.{max(0, n-2)}f}%" if pct else f"{x:.{n}f}"


def ts_brt(ts):
    return "–" if ts is None else datetime.fromtimestamp(ts, BRT).strftime("%Y-%m-%d %H:%M")


def rows_of(run_root: Path, rel: str) -> list[dict]:
    p = run_root / rel
    return list(logio.iter_rows(p, root=run_root)) if p.exists() else []


def price_series(roots: list[Path]) -> dict:
    parts = []
    for r in roots:
        p = r / "data" / "prices.jsonl"
        if p.exists():
            parts.append(CA.build_series(logio.iter_rows(p, root=r), asset="SOL"))
        d = r / "data" / "meme" / "prices"
        if d.exists():
            for fp in sorted(d.glob("*.jsonl")):
                parts.append(CA.build_series(logio.iter_rows(fp, root=r), asset=fp.stem))
    return CA.merge_series(*parts)


def sol_group(r: dict) -> str | None:
    m = r.get("model") or "von"
    if m == "rule":
        return None
    p = r.get("portfolio") or ""
    if p == "v2":
        return "SOL · von · v2 (critérios v2)"
    if str(r.get("strategy") or "").startswith("rule:hybrid"):
        return f"SOL · {m} · {p}"
    return f"SOL · {m} · baseline+relaxed" if m == "von" else f"SOL · {m}"


def meme_model(r: dict) -> str | None:
    m = r.get("model") or "von"
    return None if m == "rule" else m


def lab_group(r: dict) -> str:
    return f"lab · {r.get('portfolio')}"


def run_audits(groups: dict, prices, trades, variants, kw, dedupe=True):
    traded_ids = {t.get("decision_id") for t in trades if t.get("decision_id")}
    out = {}
    for g, rows in groups.items():
        rs = CA.dedupe_calls(rows, traded_ids=traded_ids) if dedupe else rows
        out[g] = {name: CA.audit(rs, prices=prices, trades=trades, **v, **kw) for name, v in variants.items()}
    return out


def audit_row(g, name, a):
    ph = ", ".join(f"{w}:{n}" for w, n in (a["lose_words"] or [])[:5]) or "–"
    share = f(a["confident_share"], 3, pct=True) if a["confident_share"] is not None else "–"
    return (f"| {g} | {name} | {a['n_answered']} | {f(a['conf_p50'])} / {f(a['conf_max'])} | {a['rule']} | {f(a['cutoff'])} | "
            f"{a['n_confident']} ({share}) | {a['n_confident_acted']} | {a['n_resolved']} | {a['n_mistakes']} ({a['mistake_episodes']}) | {a['n_correct']} | "
            f"{a['n_flat']} | {f(a['hit_rate'], 3, pct=True)} | {ph} |")


HDR = ["| Grupo | Variante | Respondidas | conf p50 / máx | Regra | Corte | Confiantes (% resp.) | Viraram ordem | Resolvidas | Erros (episódios) | Acertos | Flat | Hit rate | Palavras dos erros (top 5) |",
       "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]


def trade_family(name: str) -> str:
    return re.sub(r"(?<![A-Z])(BONK|FARTCOIN|GOAT|MEW|PNUT|POPCAT|WIF)(?![A-Z])", "{SYM}", name)


def trade_rows(trades, mint2sym, asset):
    out = []
    for t in trades:
        fill = t.get("fill") or {}
        sym = asset or mint2sym.get(fill.get("mint")) or next((s for s in SYMS if s in (t.get("portfolio") or "")), None)
        if sym is None or t.get("side") not in CA.DIRECTIONAL:
            continue
        out.append({"ts": t["ts"], "ts_brt": t.get("ts_brt"), "portfolio": t.get("portfolio"), "model": "trade",
                    "symbol": sym, "price_usd": t.get("price_mark") or fill.get("mark_price"), "chosen_action": t["side"],
                    "final_action": t["side"], "confidence": 1.0, "traded": True, "decision_id": t.get("decision_id")})
    return out


def window_line(label, rows):
    ts = [float(r["ts"]) for r in rows if r.get("ts") is not None]
    if not ts:
        return f"- {label}: sem linhas"
    return f"- {label}: {len(ts)} linhas, {ts_brt(min(ts))} → {ts_brt(max(ts))} BRT ({(max(ts)-min(ts))/3600:.1f} h)"


def analyse_run(label, run_root: Path, price_roots, variants, kw, mint2sym, base_crit, cur_v2, full=True):
    L = [f"## {label}", "", f"Pasta: `{run_root.name}`", ""]
    dec = rows_of(run_root, "logs/decisions.jsonl")
    mdec = rows_of(run_root, "logs/meme_decisions.jsonl")
    ldec = rows_of(run_root, "logs/lab_decisions.jsonl")
    tr = rows_of(run_root, "logs/trades.jsonl")
    mtr = rows_of(run_root, "logs/meme_trades.jsonl")
    prices = price_series(price_roots)
    L += ["### Janela coberta", "",
          window_line("decisões SOL (`logs/decisions.jsonl`)", dec),
          window_line("decisões memes (`logs/meme_decisions.jsonl`)", mdec),
          window_line("decisões lab (`logs/lab_decisions.jsonl`)", ldec),
          window_line("trades SOL + lab SOL (`logs/trades.jsonl`, nunca rotacionado)", tr),
          window_line("trades memes (`logs/meme_trades.jsonl`, nunca rotacionado)", mtr),
          f"- séries de preço para o retorno a {int(kw['horizon_s'])} s: " + ", ".join(
              f"{a} {ts_brt(s[0][0])}→{ts_brt(s[0][-1])}" for a, s in sorted(prices.items()) if s[0]), ""]
    all_trades = tr + mtr
    sol_g = CA.group_rows(dec, sol_group)
    meme_coin = CA.group_rows(mdec, lambda r: (f"{r.get('symbol')} · {meme_model(r)}" if meme_model(r) else None))
    meme_pool = CA.group_rows(mdec, lambda r: (f"Memes (7) · {meme_model(r)}" if meme_model(r) else None))
    lab_g = CA.group_rows(ldec, lab_group)
    res_sol = run_audits(sol_g, prices, all_trades, variants, kw)
    res_pool = run_audits(meme_pool, prices, all_trades, variants, kw)
    L += ["### Grupos principais (candidatas = chamadas buy/sell do modelo, `chosen`)", "",
          "Percentil calculado sobre as confianças respondidas (sem fail-closed/sem resposta) de cada grupo na janela. "
          "Memes agregados: um único percentil para as 7 moedas de cada modelo.", ""] + HDR
    for res in (res_sol, res_pool):
        for g in sorted(res):
            for name, a in res[g].items():
                L.append(audit_row(g, name, a))
    L.append("")
    if full:
        res_coin = run_audits(meme_coin, prices, all_trades, {k: variants[k] for k in ("barra fixa 0,8", "P90")}, kw)
        L += ["### Memes por moeda e modelo (P90 vs barra fixa)", "",
              "| Moeda · modelo | Respondidas | Corte P90 | Confiantes P90 | Resolvidas | Erros | Acertos | Hit rate | Confiantes barra 0,8 | Erros barra 0,8 |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for g in sorted(res_coin):
            p, x = res_coin[g]["P90"], res_coin[g]["barra fixa 0,8"]
            L.append(f"| {g} | {p['n_answered']} | {f(p['cutoff'])} | {p['n_confident']} | {p['n_resolved']} | {p['n_mistakes']} | "
                     f"{p['n_correct']} | {f(p['hit_rate'], 3, pct=True)} | {x['n_confident']} | {x['n_mistakes']} |")
        L.append("")
        if ldec:
            res_lab = run_audits(lab_g, prices, all_trades, {k: variants[k] for k in ("barra fixa 0,8", "P90")}, kw, dedupe=False)
            L += ["### Lab por portfólio (P90 vs barra fixa)", "",
                  "Linhas do lab copiam a decisão de origem (von/poorjev) ou, no H2, trazem a confiança do ensemble (percentil combinado). "
                  "Cópias de um modelo em falha têm conf 0 e contam como não respondidas. Sem texto de estado → sem palavras.", "",
                  "| Portfólio | Respondidas | Corte P90 | Confiantes P90 | Resolvidas | Erros | Acertos | Hit rate | Confiantes barra 0,8 | Erros barra 0,8 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
            for g in sorted(res_lab):
                p, x = res_lab[g]["P90"], res_lab[g]["barra fixa 0,8"]
                if not p["n_answered"]:
                    continue
                L.append(f"| {g} | {p['n_answered']} | {f(p['cutoff'])} | {p['n_confident']} | {p['n_resolved']} | {p['n_mistakes']} | "
                         f"{p['n_correct']} | {f(p['hit_rate'], 3, pct=True)} | {x['n_confident']} | {x['n_mistakes']} |")
            skipped = [g for g in sorted(res_lab) if not res_lab[g]["P90"]["n_answered"]]
            if skipped:
                L.append(f"\nSem respostas na janela (omitidos): {', '.join(s.replace('lab · ', '') for s in skipped)}.")
            L.append("")
        acted_kw = dict(kw, candidates="acted")
        res_acted = run_audits({**sol_g, **meme_pool}, prices, all_trades, {k: variants[k] for k in ("barra fixa 0,8", "P90")}, acted_kw)
        L += ["### Só o que virou ordem paper (`acted`: traded, join por decision_id ou final_action buy/sell)", "", *HDR]
        for g in sorted(res_acted):
            for name, a in res_acted[g].items():
                L.append(audit_row(g, name, a))
        L.append("")
        # trade-level audit (no confidence)
        trs = trade_rows(tr, mint2sym, "SOL") + trade_rows(mtr, mint2sym, None)
        fam = CA.group_rows(trs, lambda r: ("SOL · " if r["symbol"] == "SOL" else "Memes · ") + trade_family(r["portfolio"] or "?"))
        L += ["### Auditoria de todos os trades (sem corte de confiança)", "",
              f"Cada trade paper conta como chamada (compra/venda) ao `price_mark`; mesmo critério de erro ({int(kw['horizon_s'])} s, ±{kw['band']*100:.2f}%). "
              "Cobre a execução inteira, porque os logs de trades não são rotacionados. Memes agregados por família (`{SYM}`).", "",
              "| Família | Trades (C/V) | Resolvidos | Erros | Acertos | Flat | Hit rate | Erros compra / venda |",
              "|---|---:|---:|---:|---:|---:|---:|---|"]
        tot = Counter(); trade_audit = {}
        for g in sorted(fam, key=lambda k: (not k.startswith("SOL"), -len(fam[k]), k)):
            a = CA.audit(fam[g], prices=prices, fixed_bar=0.0, **kw); trade_audit[g] = a
            bs = a["by_side"]
            nb = sum(1 for r in fam[g] if r["chosen_action"] == "buy")
            L.append(f"| {g} | {len(fam[g])} ({nb}/{len(fam[g]) - nb}) | {a['n_resolved']} | {a['n_mistakes']} | {a['n_correct']} | {a['n_flat']} | "
                     f"{f(a['hit_rate'], 3, pct=True)} | {bs['buy'].get('mistake', 0)} / {bs['sell'].get('mistake', 0)} |")
            for k in ("n_resolved", "n_mistakes", "n_correct", "n_flat"):
                tot[k] += a[k]
            tot["n"] += len(fam[g])
        L.append(f"| **total** | {tot['n']} | {tot['n_resolved']} | {tot['n_mistakes']} | {tot['n_correct']} | {tot['n_flat']} | "
                 f"{f(tot['n_correct'] / tot['n_resolved'] if tot['n_resolved'] else None, 3, pct=True)} | |")
        L.append("")
    # proposal vs current criteria_v2
    main_key = "SOL · von · baseline+relaxed"
    props = {}
    if main_key in res_sol:
        L += ["### Proposta resultante vs `criteria_v2.json` atual", "",
              f"Reescrita determinística (`propose_criteria`) a partir do grupo `{main_key}`; frases só entram quando há erros confiantes.", "",
              "| Variante | Erros confiantes | Frases acrescentadas | Igual ao `criteria_v2.json` atual? |", "|---|---:|---|---|"]
        for name, a in res_sol[main_key].items():
            p = CA.propose_criteria(base_crit, a, generated_at="compare")
            props[name] = p
            L.append(f"| {name} | {a['n_mistakes']} | {json.dumps(p['phrases_added'], ensure_ascii=False) if p['changed'] else '— (texto base)'} | "
                     f"{'sim' if CA.same_text(p, cur_v2) else 'não'} |")
        L += ["", "`criteria_v2.json` atual (gerado em 2026-09-24 04:00 com 0 trades auditados) tem as frases \"prefer …\" que a revisão antiga "
              "acrescentava sempre; com a regra nova, sem erros confiantes a proposta é o texto base, logo também difere dele.", ""]
    return L, {"name": run_root.name, "sol": res_sol, "pool": res_pool, "props": props, "dec": dec, "mdec": mdec, "tr": tr, "mtr": mtr,
               "prices": prices, "trade_audit": trade_audit if full else {}}


def _get(res, g, var):
    return (res.get(g) or {}).get(var)


def _fam_line(label, a):
    if not a or not a["n_answered"]:
        return f"- {label}: sem respostas do modelo na janela."
    return (f"- {label}: corte {f(a['cutoff'])} ({a['rule']}), {a['n_confident']} de {a['n_answered']} respondidas "
            f"({f(a['confident_share'], 3, pct=True)}), {a['n_resolved']} resolvidas → {a['n_mistakes']} erros em {a['mistake_episodes']} episódio(s) / {a['n_correct']} acertos / "
            f"{a['n_flat']} flat (hit rate {f(a['hit_rate'], 3, pct=True)}); palavras dos erros: "
            f"{', '.join(w for w, _ in a['lose_words'][:5]) or '–'}.")


def leitura(main, extra):
    L = ["## Leitura", ""]
    sol, pool = main["sol"], main["pool"]
    fams = [("von SOL, critérios baseline (baseline+relaxed; o híbrido é a mesma chamada)", "von SOL", sol, "SOL · von · baseline+relaxed"),
            ("von SOL, critérios v2", "von SOL v2", sol, "SOL · von · v2 (critérios v2)"),
            ("Laya SOL", "Laya SOL", sol, "SOL · laya"), ("poorjev SOL", "poorjev SOL", sol, "SOL · poorjev"),
            ("von memes (7 moedas)", "von memes", pool, "Memes (7) · von"), ("Laya memes", "Laya memes", pool, "Memes (7) · laya"),
            ("poorjev memes", "poorjev memes", pool, "Memes (7) · poorjev")]
    fx = {short: (_get(r, g, "barra fixa 0,8") or {}).get("n_confident", 0) for _, short, r, g in fams}
    L.append("- **Barra fixa 0,8 nesta execução:** " + ", ".join(f"{k} {n}" for k, n in fx.items())
             + " chamadas confiantes. Com confianças do von ≤ ~0,40 e da Laya ≤ ~0,13 a regra antiga nunca tem o que auditar "
             "(questão 3 do HANDOFF confirmada nos logs).")
    if extra:
        pj = _get(extra["pool"], "Memes (7) · poorjev", "barra fixa 0,8")
        if pj and pj["n_answered"]:
            L.append(f"- **O mesmo 0,8 no poorjev (`{extra['name']}`):** marca {pj['n_confident']} de {pj['n_answered']} chamadas "
                     f"({f(pj['confident_share'], 3, pct=True)}) como confiantes. Barra fixa = nunca (von/Laya) ou sempre (poorjev): depende da escala "
                     "de cada modelo; o percentil dá ~10% das respondidas em qualquer escala.")
    L.append("- **P90 por família (execução principal, janela de decisões disponível):**")
    L += ["  " + _fam_line(lab, _get(r, g, "P90")) for lab, _, r, g in fams]
    tr = main.get("trade_audit") or {}
    for key in ("SOL · relaxed", "SOL · hybrid_von_relaxed_cap2"):
        a = tr.get(key)
        if a:
            bs = a["by_side"]
            L.append(f"- **Compras agora auditadas ({key.split(' · ')[1]}, todos os trades):** {a['n_resolved']} resolvidos, "
                     f"{a['n_mistakes']} erros ({bs['buy'].get('mistake', 0)} em compras), {a['n_correct']} acertos → hit rate {f(a['hit_rate'], 3, pct=True)}. "
                     "A revisão antiga só olhava `approx_pnl` de vendas (1 venda).")
    props = main.get("props") or {}
    if "P90" in props:
        p = props["P90"]
        L.append(f"- **Proposta (P90):** {'acrescenta ' + json.dumps(p['phrases_added'], ensure_ascii=False) if p['changed'] else 'sem frases novas (texto base)'}; "
                 "difere do `criteria_v2.json` em uso, que tem as frases \"prefer …\" acrescentadas sem erros em 2026-09-24. Continua só proposta (portão humano).")
    if extra:
        a = _get(extra["sol"], "SOL · von · baseline+relaxed", "P90")
        b = _get(main["sol"], "SOL · von · baseline+relaxed", "P90")
        if a and b and a["n_resolved"] and b["n_resolved"]:
            def chg(res):
                _, t0, t1 = _span_h(res["dec"]); c = _px_change(res["prices"].get("SOL"), t0, t1)
                return f"{ts_brt(t0)}→{ts_brt(t1)[-5:]}, SOL {c[2]*100:+.2f}%" if c else "?"
            L.append(f"- **A janela manda mais que o corte:** o mesmo von SOL no P90 acertou {a['n_correct']}/{a['n_resolved']} na janela da execução "
                     f"arquivada ({chg(extra)}) e {b['n_correct']}/{b['n_resolved']} na janela principal ({chg(main)}). O modelo chama quase só `buy`; "
                     "com poucas horas o hit rate reflete o movimento local, não a qualidade do corte.")
    return L


def _span_h(rows):
    ts = [float(r["ts"]) for r in rows if r.get("ts") is not None]
    return ((max(ts) - min(ts)) / 3600, min(ts), max(ts)) if ts else (0.0, None, None)


def _px_change(series, t0, t1):
    if not series or t0 is None:
        return None
    tl, pl = series
    import bisect
    i = min(bisect.bisect_left(tl, t0), len(tl) - 1); j = max(0, bisect.bisect_right(tl, t1) - 1)
    return pl[i], pl[j], pl[j] / pl[i] - 1


def ressalvas(root, res, cfg):
    L = ["## Ressalvas", ""]
    hs, a, b = _span_h(res["dec"]); hm, _, _ = _span_h(res["mdec"]); ht, _, _ = _span_h(res["tr"] + res["mtr"])
    rot = (root / "archive" / "logs").exists()
    L.append(f"- Janela de decisões curta: {hs:.1f} h de decisões SOL e {hm:.1f} h de memes nesta raiz"
             + ("" if rot else " (os logs de decisão são rotacionados às 01:00 e ficam só as últimas linhas; os arquivos `archive/logs` não estão nesta raiz)")
             + f". Os trades (nunca rotacionados) cobrem {ht:.1f} h, daí a secção sem corte de confiança.")
    ch = _px_change(res["prices"].get("SOL"), a, b)
    exp = cfg.get("experiment") or {}
    if ch:
        d1 = exp.get("day1_start_brt")
        run = _px_change(res["prices"].get("SOL"), datetime.fromisoformat(d1).timestamp(), b) if d1 else None
        L.append(f"- Movimento do SOL: {ch[0]:.2f} → {ch[1]:.2f} ({ch[2]*100:+.2f}%) na janela de decisões SOL"
                 + (f"; {run[0]:.2f} → {run[1]:.2f} ({run[2]*100:+.2f}%) desde o início da execução" if run else "")
                 + ". Como o von chama quase só `buy`, o hit rate depende sobretudo do movimento local; poucas horas não separam modelo de regime.")
    d1 = exp.get("day1_start_brt")
    if d1 and b:
        days = (b - datetime.fromisoformat(d1).timestamp()) / 86400
        L.append(f"- Execução curta (≈{days:.1f} dias desde o início até ao último dado) e já arquivada; nenhum portfólio atingiu os mínimos de veredito "
                 "(≥30 RT e ≥21 dias). Serve para escolher a regra da revisão, não para avaliar modelos.")
    L.append("- Autocorrelação: decisões a cada 15 s repetem o mesmo estado; dezenas de \"erros\" podem ser um único episódio de poucos minutos "
             "(coluna/menção \"episódios\": erros separados por > 5 min). Contar episódios, não linhas, antes de tirar conclusões.")
    L.append("- Horizonte único (15 min) e banda fixa (0,10%) para SOL e memes; memes são mais voláteis, a banda devia ser por ativo.")
    pj = [r for r in res["dec"] + res["mdec"] if str(r.get("model") or "").startswith("poorjev")]
    if pj:
        fc = sum(1 for r in pj if not CA.is_answered(r))
        L.append(f"- poorjev: {fc}/{len(pj)} linhas sem resposta (fail-closed) na janela; "
                 + (f"erro mais comum: `{Counter(str(r.get('von_error'))[:60] for r in pj if r.get('von_error')).most_common(1)[0][0]}`." if any(r.get('von_error') for r in pj) else ""))
    L.append("- Empates: as confianças do von concentram-se em poucos valores; quando `>=` no percentil marcaria >1,5× a fração pedida, usa-se `>` "
             "(coluna Regra). P80 e P90 podem então coincidir.")
    return L


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="raiz do lab (padrão: PAPER_LAB_ROOT ou a pasta do lab)")
    ap.add_argument("--out", help="ficheiro markdown de saída (padrão: stdout)")
    ap.add_argument("--percentiles", default="80,90,95")
    ap.add_argument("--fixed-bar", type=float, default=0.8)
    ap.add_argument("--horizon", type=float, default=900)
    ap.add_argument("--band", type=float, default=0.001)
    ap.add_argument("--tolerance", type=float, default=300)
    ap.add_argument("--extra-run", action="append", default=[], help="pasta de execução arquivada (relativa à raiz), ex.: archive/run_52usd_2026-09-24")
    a = ap.parse_args(argv)
    root = Path(a.root).expanduser().resolve() if a.root else DEFAULT_ROOT
    cfg = json.loads((root / "config.json").read_text())
    rc = CA.review_cfg(cfg)
    variants = {"barra fixa 0,8": {"fixed_bar": a.fixed_bar}}
    for p in [float(x) for x in a.percentiles.split(",") if x.strip()]:
        variants[f"P{p:g}"] = {"percentile_p": p}
    kw = {"horizon_s": a.horizon, "band": a.band, "tolerance_s": a.tolerance, "candidates": "chosen", "tie_rule": rc["tie_rule"]}
    mint2sym = {t["mint"]: t["symbol"] for t in (json.loads((root / "memecoins.json").read_text()).get("tokens") or [])}
    base_crit = json.loads((root / "criteria_baseline.json").read_text())
    cur_v2 = json.loads((root / "criteria_v2.json").read_text())
    L = ["# Revisão noturna: corte por percentil vs barra fixa 0,8 (logs reais)", "",
         f"Gerado {datetime.now(BRT).isoformat(timespec='seconds')} por `scripts/compare_review_cutoffs.py` (só leitura) sobre a raiz "
         f"`{root.name}` ({'exportação' if root != Path(__file__).resolve().parents[1] else 'lab'}). Paper only.", "",
         "## Definições", "",
         "- **Respondida:** decisão com resposta real do modelo (sem `fail_closed`, `von_ok` ≠ false, `model` ≠ `rule`, conf > 0).",
         f"- **Corte:** barra fixa `conf > {a.fixed_bar:g}` (regra antiga) ou percentil P das confianças respondidas do grupo na janela "
         f"(`conf >= Pxx`; com muitos empates no corte, `tie_rule={rc['tie_rule']}` passa a `>` — ver coluna Regra).",
         "- **Candidatas:** chamadas direcionais do modelo (`chosen_action` buy/sell), antes dos portões de carteira. Motivo (visto nos logs): "
         "o `relaxed` ficou 100% investido e as decisões seguintes têm `final_action=hold` (`insufficient_usdt`); auditar só ordens deixaria o modelo "
         "sem auditoria. A variante `acted` (só ordens) aparece à parte.",
         f"- **Erro:** compra com retorno a {int(a.horizon)} s < −{a.band*100:.2f}%, venda com retorno > +{a.band*100:.2f}%; acerto = movimento além da banda "
         f"no sentido da chamada; flat = dentro da banda. Preço futuro: primeiro ponto da série do ativo (`data/prices.jsonl`, "
         f"`data/meme/prices/*.jsonl`, completadas pelos preços das decisões) em [t+{int(a.horizon)} s, t+{int(a.horizon + a.tolerance)} s]; sem ponto → não resolvida.",
         "- **Dedupe:** baseline e relaxed (e as variantes de cada modelo) partilham uma chamada por ciclo; as linhas iguais são fundidas "
         "(mesmo modelo, estado, confiança, escolha e preço em ≤ 5 s) para não contar a mesma chamada duas vezes.", ""]
    exp = cfg.get("experiment") or {}
    d1 = exp.get("day1_start_brt")
    cap = f"{float(exp.get('capital_usd_each') or 0):,.0f}".replace(",", ".")
    label = (f"Execução {exp['run_name']}" if exp.get("run_name") else f"Execução de US$ {cap}") + (
        f" (desde {ts_brt(datetime.fromisoformat(d1).timestamp())} BRT)" if d1 else "")
    body, main_res = analyse_run(label, root, [root], variants, kw,
                                 mint2sym, base_crit, cur_v2, full=True)
    extra_res = None
    extra_body = []
    for rel in a.extra_run:
        rr = (root / rel).resolve()
        if not rr.exists():
            extra_body += [f"_(execução extra `{rel}` não encontrada)_", ""]
            continue
        eb, extra_res = analyse_run(f"Complemento: execução arquivada `{rr.name}`", rr, [root, rr], variants, kw,
                                    mint2sym, base_crit, cur_v2, full=False)
        extra_body += eb
    L += leitura(main_res, extra_res) + [""] + ressalvas(root, main_res, cfg) + [""] + body + extra_body
    txt = "\n".join(L)
    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(txt)
        print(f"wrote {out}")
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
