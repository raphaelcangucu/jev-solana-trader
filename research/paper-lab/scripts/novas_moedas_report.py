#!/usr/bin/env python3
"""Relatório "von relaxado em moedas novas": compara os runs bt30x/bt180x (moedas fora do run ao vivo, overlay só do
backtest) com as 7 memecoins atuais nos runs de referência bt30/bt180 da mesma janela, e aplica a regra de passagem.

Só lê summary.json e equity/*.json já escritos (nada de rede, chaves ou ordens) e grava
<base>/novas_moedas.md (e novas_moedas.json com as mesmas linhas).

Uso:
    python research/paper-lab/scripts/novas_moedas_report.py [--base ~/jev-lab/code/research/paper-lab/data/backtest]
        [--new30 bt30x_2026-10-06 --new180 bt180x_2026-10-06 --ref30 bt30_2026-10-06 --ref180 bt180_2026-10-06]

Regra de passagem (só a janela de 180 dias decide): von relaxed com habilidade > 0 E a bater o "só segurar" da moeda
nos 180 dias (excesso vs B&H > 0) E PnL > 0 em ≥ 3 dos 6 blocos de 30 dias.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

BRT = timezone(timedelta(hours=-3))
CURRENT = ["BONK", "WIF", "POPCAT", "FARTCOIN", "PNUT", "MEW", "GOAT"]
STRATS = [("von_relaxed", "von relaxado", "meme_{S}_relaxed"), ("von_artigo", "von artigo", "meme_{S}_baseline"),
          ("poorjev_saidas", "poorjev + saídas (H1)", "h1_exits_{S}_poorjev_relaxed")]
NEED_MONTHS = 3


def _f(x, n=2, sign=True, pct=False):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "–"
    s = f"{x:+.{n}f}" if sign else f"{x:.{n}f}"
    return s + ("%" if pct else "")


def load_run(base: Path, rid: str) -> dict:
    s = json.loads((base / rid / "summary.json").read_text())
    s["_P"] = {p["name"]: p for p in s["portfolios"]}
    s["_dir"] = base / rid
    return s


def bh_mdd(run: dict, sym: str) -> float | None:
    """MDD % do "só segurar" pela série bh gravada com a equity do meme_<SYM>_baseline (mesmo método para todas)."""
    f = run["_dir"] / "equity" / f"meme_{sym}_baseline.json"
    try:
        bh = [x for x in json.loads(f.read_text())["bh"] if x is not None]
    except Exception:
        return None
    pk, mdd = -1e18, 0.0
    for v in bh:
        pk = max(pk, v)
        mdd = min(mdd, (v - pk) / pk * 100 if pk > 0 else 0.0)
    return mdd


def rows_for(run: dict, sym: str, long_run: bool) -> list[dict]:
    a = run["assets"].get(sym) or {}
    out = []
    for key, lab, tpl in STRATS:
        p = run["_P"].get(tpl.replace("{S}", sym))
        if p is None:
            continue
        months = p.get("months") or []
        out.append({"sym": sym, "key": key, "label": lab, "name": p["name"], "pnl_pct": p["pnl_pct"], "vs_bh": p["vs_bh"],
                    "skill": p["skill"], "trades": p["trades"], "closed_rt": p.get("closed_rt"), "max_dd_pct": p["max_dd_pct"],
                    "verdict": p["verdict"], "verdict_reason": p.get("verdict_reason"),
                    "months_pos": sum(1 for m in months if (m or 0) > 0) if long_run else None,
                    "months_beat_bh": p.get("months_beat_bh") if long_run else None, "months": months or None,
                    "weeks_beat_bh": p.get("weeks_beat_bh"), "exposure_pct": p.get("exposure_pct"),
                    "cost_vs_mark": p.get("cost_vs_mark"), "fees": p.get("fees")})
    out.append({"sym": sym, "key": "so_segurar", "label": "só segurar", "name": f"{sym}_buy_hold", "pnl_pct": a.get("ret_pct"),
                "vs_bh": 0.0, "skill": None, "trades": 0, "closed_rt": 0, "max_dd_pct": bh_mdd(run, sym), "verdict": "–",
                "months_pos": None, "months_beat_bh": None, "weeks_beat_bh": None})
    return out


def passes(r180: dict | None) -> tuple[bool, str]:
    if not r180:
        return False, "sem dados de 180 dias"
    why = []
    if not ((r180.get("skill") or 0) > 0):
        why.append(f"habilidade {_f(r180.get('skill'))} $ ≤ 0")
    if not ((r180.get("vs_bh") or 0) > 0):
        why.append(f"não bate o só segurar ({_f(r180.get('vs_bh'))} $)")
    if (r180.get("months_pos") or 0) < NEED_MONTHS:
        why.append(f"PnL > 0 só em {r180.get('months_pos') or 0}/6 meses")
    return (not why), ("; ".join(why) if why else "passa")


def gross(r: dict | None) -> float | None:
    """Habilidade antes de custos: habilidade + custo vs marca (slippage + extra de 5 bps + rede; `fees` já está dentro
    de `cost_vs_mark`, por isso não se soma)."""
    if not r or r.get("skill") is None or r.get("cost_vs_mark") is None:
        return None
    return r["skill"] + r["cost_vs_mark"]


def table(rows: list[dict], long_run: bool) -> list[str]:
    cons = "Meses PnL>0 · >B&H" if long_run else "Semanas > B&H"
    L = [f"| Moeda | Estratégia | PnL % | vs segurar $ | Habilidade $ | Trades | MDD % | {cons} | Veredito |",
         "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        if r["key"] == "so_segurar":
            c = "–"
        elif long_run:
            c = f"{r['months_pos']}/6 · {r['months_beat_bh']}/6"
        else:
            c = f"{r['weeks_beat_bh']}/4"
        bold = "**" if r["key"] == "von_relaxed" else ""
        L.append(f"| {r['sym']} | {bold}{r['label']}{bold} | {_f(r['pnl_pct'])} | {_f(r['vs_bh']) if r['key'] != 'so_segurar' else '–'} | "
                 f"{_f(r['skill'])} | {r['trades']} | {_f(r['max_dd_pct'], 1, sign=False) if r['max_dd_pct'] is not None else '–'} | "
                 f"{c} | {r['verdict']} |")
    return L


def coverage_table(n30: dict, n180: dict, syms: list[str], xdoc: dict) -> list[str]:
    tok = {t["symbol"]: t for t in xdoc.get("tokens") or []}
    L = ["| Moeda | Mint | Dec. | Fonte 1 m (30 d / 180 d) | Cobertura 30 d | Cobertura 180 d | Corr. 1 h vs Gate.io (180 d) | "
         "Retorno 30 d | Retorno 180 d | Custo assumido (bps) | Liquidez on-chain US$ |",
         "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s in syms:
        a30, a180, t = n30["assets"].get(s) or {}, n180["assets"].get(s) or {}, tok.get(s) or {}
        b = (a180.get("basis") or {})
        src30 = (a30.get("source") or "–").replace(" 1m", "")
        src180 = (a180.get("source") or "–").replace(" 1m", "")
        L.append(f"| {s} | `{t.get('mint', '?')}` | {t.get('decimals', '?')} | {src30} / {src180} | "
                 f"{(a30.get('coverage') or 0) * 100:.2f}% | {(a180.get('coverage') or 0) * 100:.2f}% | {_f(b.get('corr_ret_1h'), 4, sign=False)} | "
                 f"{_f(a30.get('ret_pct'))}% | {_f(a180.get('ret_pct'))}% | {_f(t.get('quote_slippage_bps'), 1, sign=False)} | "
                 f"{t.get('dex_liquidity_usd', 0) / 1e6:.1f} M |")
    return L


def build(base: Path, new30: str, new180: str, ref30: str, ref180: str) -> tuple[str, dict]:
    n30, n180, r30, r180 = (load_run(base, x) for x in (new30, new180, ref30, ref180))
    xdoc = json.loads((n180["_dir"] / "inputs" / "assets_extra.json").read_text())
    syms = [t["symbol"] for t in xdoc["tokens"] if t["symbol"] in n180["assets"]]
    new_rows30 = [r for s in syms for r in rows_for(n30, s, False)]
    new_rows180 = [r for s in syms for r in rows_for(n180, s, True)]
    cur_rows30 = [r for s in CURRENT for r in rows_for(r30, s, False)]
    cur_rows180 = [r for s in CURRENT for r in rows_for(r180, s, True)]

    def vr(rows, s):
        return next((r for r in rows if r["sym"] == s and r["key"] == "von_relaxed"), None)

    verdicts = []
    for grp, rows180, rows30, ss in (("nova", new_rows180, new_rows30, syms), ("atual", cur_rows180, cur_rows30, CURRENT)):
        for s in ss:
            ok, why = passes(vr(rows180, s))
            v30 = vr(rows30, s)
            verdicts.append({"sym": s, "group": grp, "passes": ok, "why": why, "skill_180": (vr(rows180, s) or {}).get("skill"),
                             "pnl_180": (vr(rows180, s) or {}).get("pnl_pct"), "vs_bh_180": (vr(rows180, s) or {}).get("vs_bh"),
                             "months_pos": (vr(rows180, s) or {}).get("months_pos"),
                             "skill_30": (v30 or {}).get("skill"), "pnl_30": (v30 or {}).get("pnl_pct"),
                             "trades_180": (vr(rows180, s) or {}).get("trades"),
                             "cost_180": (vr(rows180, s) or {}).get("cost_vs_mark"),
                             "gross_skill_180": gross(vr(rows180, s))})
    passed = [v["sym"] for v in verdicts if v["group"] == "nova" and v["passes"]]
    passed_cur = [v["sym"] for v in verdicts if v["group"] == "atual" and v["passes"]]
    nv = [v for v in verdicts if v["group"] == "nova"]
    best = max(nv, key=lambda v: v["skill_180"] if v["skill_180"] is not None else -1e18)
    pos_skill = [v["sym"] for v in nv if (v["skill_180"] or 0) > 0]
    beat = [v["sym"] for v in nv if (v["vs_bh_180"] or 0) > 0]
    pos30 = [v["sym"] for v in nv if (v["skill_30"] or 0) > 0]
    gpos = [v["sym"] for v in nv if (v["gross_skill_180"] or 0) > 0]
    gpos_cur = [v["sym"] for v in verdicts if v["group"] == "atual" and (v["gross_skill_180"] or 0) > 0]
    g_all = [v["gross_skill_180"] for v in verdicts if v["gross_skill_180"] is not None]
    c_all = [v["cost_180"] for v in verdicts if v["cost_180"] is not None]
    t_all = [v["trades_180"] for v in verdicts if v["trades_180"] is not None]
    med = sorted(v["pnl_180"] for v in nv if v["pnl_180"] is not None)
    med_cur = sorted(v["pnl_180"] for v in verdicts if v["group"] == "atual" and v["pnl_180"] is not None)

    def median(x):
        return (x[len(x) // 2] if len(x) % 2 else (x[len(x) // 2 - 1] + x[len(x) // 2]) / 2) if x else None

    calls = {m: (n30["models"].get(m) or {}).get("calls", 0) + (n180["models"].get(m) or {}).get("calls", 0)
             for m in set(n30["models"]) | set(n180["models"])}
    rt = {new30: n30["runtime"]["total_s"], new180: n180["runtime"]["total_s"]}
    now = datetime.now(tz=BRT).isoformat(timespec="seconds")
    L = ["# Von relaxado em moedas novas — o que daria?", "",
         f"Gerado (BRT): {now} · paper only (nenhuma ordem, nenhuma chave) · runs: `{new30}` e `{new180}` (moedas novas) contra "
         f"`{ref30}` e `{ref180}` (as 7 memecoins atuais, mesma janela e mesmos parâmetros).", "",
         "**Pergunta:** se aplicarmos o von relaxado (`meme_<SYM>_relaxed`: von, perfil relaxed — confiança ≥ 0,35, margem ≥ 0,20, "
         "skip < 0,5) a outras memecoins e moedas Solana negociáveis na Jupiter, qual seria o resultado, e algum fork novo se "
         "justifica?", "",
         "## Resposta curta", ""]
    if passed:
        L.append(f"Passam a regra: **{', '.join(passed)}**. Antes de um fork ao vivo, ler os Cuidados (estado aproximado, um só "
                 "regime, custos assumidos).")
    else:
        L.append("**Nenhuma das 8 moedas novas passa a regra.** O von relaxado perde também nelas: "
                 f"PnL mediano em 180 dias {_f(median(med))}% (as 7 atuais: {_f(median(med_cur))}%), habilidade positiva em "
                 f"{len(pos_skill)}/8 ({', '.join(pos_skill) or 'nenhuma'}) e a bater o só segurar em {len(beat)}/8 "
                 f"({', '.join(beat) or 'nenhuma'}). A melhor foi {best['sym']} (habilidade {_f(best['skill_180'])} $, PnL "
                 f"{_f(best['pnl_180'])}%, PnL > 0 em {best['months_pos']}/6 meses). Não recomendo nenhum fork von relaxado ao "
                 "vivo com estas moedas.")
        L += ["", f"**Porquê:** quase toda a perda é custo de execução. Em 180 dias o von relaxado faz {min(t_all)}–{max(t_all)} "
              f"trades por moeda e paga {min(c_all):.0f}–{max(c_all):.0f} US$ sobre a marca (de 1000 US$). Antes de custos a "
              f"habilidade fica perto de zero ({min(g_all):+.0f} a {max(g_all):+.0f} US$; positiva só em "
              f"{', '.join(gpos + gpos_cur) or 'nenhuma'}): o modelo não mostra vantagem de timing que pague os custos, nem "
              "nas moedas novas nem nas atuais. Trocar de moeda não muda isto."]
    L += ["", f"Nas 7 memecoins atuais a mesma regra dá: {', '.join(passed_cur) or 'nenhuma passa'} (referência).", "",
          "## Regra de passagem", "",
          f"Só a janela de 180 dias decide. Uma moeda **passa** se o von relaxado nela tem, nos 180 dias: (1) habilidade > 0 "
          f"(excesso ajustado à exposição: o PnL menos o que a exposição média ao ativo teria rendido), (2) excesso vs só segurar "
          f"> 0 (PnL acima do buy & hold da moeda), e (3) PnL > 0 em ≥ {NEED_MONTHS} dos 6 blocos de 30 dias (contados do fim "
          "da janela). A janela de 30 dias e o veredito estatístico do run (bate B&H com p < 0,05, ≥ 30 round trips, "
          "consistência) ficam como informação; com 180 dias e ~1000 trades por moeda o veredito estatístico é mais exigente "
          "que esta regra.", "",
          "## Moedas, mints e dados", "",
          "Mints conferidos em 3 fontes públicas (Jupiter tokens v2 — `isVerified`, decimais, programa SPL Token; CoinGecko "
          "`platforms.solana` e decimais; DexScreener — `baseToken.address` dos pares Solana). Velas de 1 m de CEX spot; fonte "
          "escolhida pela cobertura e pela correlação com a Gate.io (fonte da marcação ao vivo das memecoins). A Gate.io só "
          "guarda ~7 dias de 1 m (depois do fim destas janelas), por isso a correlação é a dos retornos de 1 h com as barras de "
          "1 h da Gate.io dentro da janela. Todas as moedas estavam listadas antes do início da janela de 180 dias "
          "(2026-04-09): cobertura total, sem janela parcial.", ""]
    L += coverage_table(n30, n180, syms, xdoc)
    L += ["", f"Fontes: {xdoc.get('sources_note') or ''} Correlação 1 h de cada candidata no `summary.json` "
          "(`assets.<SYM>.basis.candidates`).", "", f"Custos: {xdoc.get('slippage_policy')}", "",
          f"Chamadas novas aos modelos (servidores próprios 8865–8867, nice 15, 2 threads, 1 worker): "
          + ", ".join(f"{m} {c}" for m, c in sorted(calls.items())) + " (o resto veio da cache: os estados são só palavras, "
          "por isso muitos já tinham sido vistos nas memecoins atuais). Duração: "
          + ", ".join(f"{k} {v / 60:.1f} min" for k, v in rt.items()) + ".", ""]
    L += ["## 180 dias (2026-04-09 → 2026-10-06, 09:00 BRT) — moedas novas", ""]
    L += table(new_rows180, True)
    L += ["", "## 180 dias — as 7 memecoins atuais (referência, " + ref180 + ")", ""]
    L += table(cur_rows180, True)
    L += ["", "## 30 dias (2026-09-06 → 2026-10-06, 09:00 BRT) — moedas novas", ""]
    L += table(new_rows30, False)
    L += ["", "## 30 dias — as 7 memecoins atuais (referência, " + ref30 + ")", ""]
    L += table(cur_rows30, False)
    L += ["", "## Quem passa (von relaxado, 180 dias)", "",
          "| Moeda | Grupo | Habilidade 180 d $ | Custos 180 d $ | Hab. antes de custos $ | vs segurar 180 d $ | PnL 180 d % | "
          "Meses PnL > 0 | Habilidade 30 d $ | Passa? | Porquê |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for v in sorted(verdicts, key=lambda v: (v["group"] != "nova", -(v["skill_180"] if v["skill_180"] is not None else -1e18))):
        L.append(f"| {v['sym']} | {v['group']} | {_f(v['skill_180'])} | {_f(v['cost_180'], sign=False)} | {_f(v['gross_skill_180'])} | "
                 f"{_f(v['vs_bh_180'])} | {_f(v['pnl_180'])} | "
                 f"{v['months_pos']}/6 | {_f(v['skill_30'])} | {'**sim**' if v['passes'] else 'não'} | {v['why']} |")
    h1 = [r for r in new_rows180 if r["key"] == "poorjev_saidas"]
    L += ["", "## Leitura", "",
          "- **von artigo** (perfil baseline) não negoceia (0 trades em todas as moedas e janelas): a confiança do von fica "
          "perto de 0,29 (P50) e o portão do artigo é mais alto. Fica em USDT; o 'vs segurar' dele é só o simétrico do "
          "retorno da moeda.",
          f"- **von relaxado** negoceia {min(t_all)}–{max(t_all)} vezes em 180 dias por moeda, com exposição média de ~2% "
          "(compra uma fração do saldo e vende pouco depois). A curva desce quase sem recuperar (MDD ≈ PnL): é o custo de "
          "cada ida e volta, não um mau mês.",
          f"- **poorjev + saídas (H1)** faz {min(r['trades'] for r in h1)}–{max(r['trades'] for r in h1)} trades em 180 dias; "
          "o PnL só fica positivo quando a moeda sobe muito (RAY, JUP), sempre bem abaixo do só segurar e com habilidade "
          "negativa em todas as moedas novas.",
          "- O poorjev relaxado sem saídas (no summary, `<SYM>_poorjev_relaxed`) compra uma vez e segura (20 compras, 0 "
          "vendas): é o buy & hold menos custos. A 'habilidade' de estratégias ~100% expostas inclui um termo de composição "
          "(o 'só segurar' da RAY tem +980 $ de 'habilidade'); compare-a com a do só segurar da mesma moeda.",
          "- Habilidade positiva no mês mais recente (30 dias) do von relaxado nas moedas novas: "
          f"{', '.join(pos30) or 'nenhuma'}.", "",
          "## Cuidados", "",
          "- **Fidelidade do estado meme:** os estados são reconstruídos de fechos de 1 m de CEX (ao vivo: marcas Gate.io → "
          "Coinpaprika a ~1/min). Na validação do bt180 o estado de mercado reconstruído bateu com o ao vivo só em 15–47% das "
          "decisões das memecoins atuais (palavra 'move' 39–69%); para moedas sem histórico ao vivo não há validação nenhuma.",
          "- **Um só regime:** 180 dias seguidos (abril → outubro de 2026), um caminho contínuo; JUP, JTO, PYTH, RAY e BOME "
          "subiram 80–250% neste período, o que torna o 'só segurar' muito difícil de bater por qualquer estratégia de "
          "exposição baixa. Noutro regime o 'vs segurar' mudaria; a habilidade (perto de zero antes de custos) é a parte que "
          "não depende tanto do regime.",
          "- **Custos assumidos:** sem fills reais destas moedas; usei a mediana das memecoins atuais (12,7 bps sobre a marca, "
          "+5 bps do código) e o custo da PNUT (32,8 bps) para PYTH e MOODENG, de liquidez on-chain mais baixa. Os custos "
          "decidem o resultado: mesmo com custo zero a habilidade fica perto de zero (coluna 'Hab. antes de custos'), por isso "
          "custos reais mais baixos reduziriam a perda mas não criariam uma vantagem.",
          "- **Mesmos parâmetros:** nenhuma afinação por moeda (params.json resolvido com asset=<SYM>, sem camada por moeda); "
          "um fork afinado para uma moeda seria avaliado dentro da amostra.",
          "- **Cadência:** cada moeda decide a cada 7 min, como as memecoins ao vivo (com 8 moedas, JUP e MOODENG no mesmo "
          "minuto). Adicionar moedas à rotação ao vivo abrandaria a cadência de todas.",
          "- **FARTCOIN ao vivo:** o único von relaxado positivo ao vivo (16 dias) também perde aqui em 180 dias (−20,8%, "
          "habilidade −213 $, 0/6 meses com PnL > 0): consistente com sorte de curto prazo.",
          "- JUP, JTO, PYTH e RAY não são memecoins (tokens de protocolo); correram pelo mesmo caminho meme (mesmo bot, mesmos "
          "parâmetros) como pedido.", ""]
    data = {"generated_brt": now, "runs": {"new30": new30, "new180": new180, "ref30": ref30, "ref180": ref180},
            "rule": {"window": "180d", "skill_gt": 0, "vs_bh_gt": 0, "months_pnl_pos_min": NEED_MONTHS},
            "passed": passed, "passed_current": passed_cur, "verdicts": verdicts,
            "rows": {"new30": new_rows30, "new180": new_rows180, "cur30": cur_rows30, "cur180": cur_rows180},
            "model_calls": calls, "runtime_s": rt}
    return "\n".join(L), data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=str(Path.home() / "jev-lab/code/research/paper-lab/data/backtest"))
    ap.add_argument("--new30", default="bt30x_2026-10-06")
    ap.add_argument("--new180", default="bt180x_2026-10-06")
    ap.add_argument("--ref30", default="bt30_2026-10-06")
    ap.add_argument("--ref180", default="bt180_2026-10-06")
    a = ap.parse_args(argv)
    base = Path(a.base).expanduser()
    md, data = build(base, a.new30, a.new180, a.ref30, a.ref180)
    (base / "novas_moedas.md").write_text(md)
    (base / "novas_moedas.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"{base / 'novas_moedas.md'}: passam {data['passed'] or 'nenhuma'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
