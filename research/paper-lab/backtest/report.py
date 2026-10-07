"""Saídas do backtest (contrato partilhado com o dashboard): summary.json, equity/<nome>.json, trades/<nome>.jsonl,
report.md e o ficheiro `latest` com o run_id."""
from __future__ import annotations

import json
import math
import statistics
from datetime import datetime
from pathlib import Path

from backtest.simenv import BRT

MAX_EQ_POINTS = 1500
MAX_TRADES = 2000


def _r(x, n=4):
    if x is None:
        return None
    try:
        x = float(x)
    except Exception:
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return round(x, n)


def brt(ts):
    return datetime.fromtimestamp(ts, tz=BRT).isoformat(timespec="seconds")


def downsample(rows, max_points=MAX_EQ_POINTS):
    if len(rows) <= max_points:
        return rows
    stride = math.ceil(len(rows) / max_points)
    out = rows[::stride]
    if out[-1] is not rows[-1]:
        out = out[:-1] + [rows[-1]] if len(out) >= max_points else out + [rows[-1]]
    return out


def write_equity(run_dir: Path, name: str, rows):
    d = run_dir / "equity"
    d.mkdir(parents=True, exist_ok=True)
    rs = downsample(rows)
    (d / f"{name}.json").write_text(json.dumps({"t": [int(r["ts"]) for r in rs], "equity": [_r(r["equity"], 4) for r in rs],
                                                "bh": [_r(r["bh_equity"], 4) for r in rs]}, separators=(",", ":")))


def write_trades(run_dir: Path, name: str, trades):
    d = run_dir / "trades"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{name}.jsonl", "w") as f:
        for t in trades[:MAX_TRADES]:
            f.write(json.dumps(t, ensure_ascii=False, separators=(",", ":")) + "\n")


def slim_trade(t):
    f = t.get("fill") or {}
    q = f.get("sol_out_net") or f.get("token_out_net") if t["side"] == "buy" else f.get("sol_in") or f.get("token_in")
    usdt = f.get("usdt_in") if t["side"] == "buy" else f.get("usdt_out_net")
    return {"ts": int(t["ts"]), "t_brt": brt(t["ts"]), "side": t["side"], "price": _r(t.get("price_mark"), 8),
            "qty": _r(q, 9), "usdt": _r(usdt, 6), "fee_usdt": _r(f.get("fee_usdt"), 6), "fill_mode": f.get("fill_mode"),
            "pnl": _r(f.get("approx_pnl"), 6), "limit": _r(f.get("limit_price"), 8),
            "equity_after": _r((t.get("portfolio_after") or {}).get("equity"), 4)}


def slim_real_trade(t):
    return {"ts": int(datetime.fromisoformat(t["t"]).timestamp()), "t_brt": t["t"], "side": t["side"], "reason": t.get("reason"),
            "price": _r(t.get("px_in"), 8), "fill_px": _r(t.get("fill_px"), 8), "in": _r(t.get("in_amount_ui"), 9),
            "out": _r(t.get("out_amount_ui"), 9), "conf": t.get("conf")}


def fmt(x, n=2, sign=False):
    if x is None:
        return "–"
    return f"{x:+.{n}f}" if sign else f"{x:.{n}f}"


def families(portfolios):
    fam = {}
    for p in portfolios:
        fam.setdefault(p["family"], []).append(p)
    out = []
    for f, ps in sorted(fam.items()):
        ps2 = sorted(ps, key=lambda p: p["pnl_pct"])
        out.append({"family": f, "n": len(ps), "median_pnl_pct": _r(statistics.median(p["pnl_pct"] for p in ps), 4),
                    "best": ps2[-1]["name"], "worst": ps2[0]["name"], "beat_bh": sum(1 for p in ps if (p["vs_bh"] or 0) > 0),
                    "median_skill": _r(statistics.median((p["skill"] or 0) for p in ps), 4)})
    return out


def winner_text(by_skill, by_pnl, by_verdict, ports, days, unit="semanas", need=3, nblk=4):
    P = {p["name"]: p for p in ports}
    s, q = P[by_skill], P[by_pnl]
    txt = (f"Em {days:g} dias simulados, a maior habilidade (excesso ajustado à exposição) foi de {by_skill} "
           f"({s['skill']:+.2f} US$, PnL {s['pnl_pct']:+.2f}%, {s['trades']} trades"
           + (", todas compras: uma entrada concentrada num recuo, não seleção repetida" if s["sells"] == 0 else "")
           + f"), e o maior PnL foi de {by_pnl} ({q['pnl_pct']:+.2f}%, {q['vs_bh']:+.2f} US$ contra o buy & hold do mesmo ativo). ")
    if by_verdict:
        txt += f"Pela regra do veredito, a vencedora é {by_verdict}. "
    else:
        n_inc = sum(1 for p in ports if p["verdict"] == "inconclusiva")
        n_lose = sum(1 for p in ports if p["verdict"] == "perdedora")
        txt += (f"Nenhum portfólio passa a regra do veredito (bater B&H e a barra USDC com p<0,05 e consistência em ≥{need} de "
                f"{nblk} {unit}): {n_inc} inconclusivos e {n_lose} perdedores. ")
    near = [p for p in ports if p["verdict"] == "inconclusiva" and "round trips" in (p.get("verdict_reason") or "")
            and p.get("p_bh") is not None and p["p_bh"] < 0.05 and (p.get("vs_bh") or 0) > 0
            and p.get("blocks_beat_bh", p["weeks_beat_bh"]) >= need]
    if near and not by_verdict:
        txt += ("Só por falta de round trips (mínimo 30) ficam de fora: " + ", ".join(
            f"{p['name']} (p={p['p_bh']:.3f}, {p['closed_rt']} RT, {p.get('blocks_beat_bh', p['weeks_beat_bh'])}/{nblk} {unit})"
            for p in near[:4]) + ". ")
    txt += "É um resultado retroativo com estados e custos aproximados; serve para ordenar hipóteses, não para provar uma vencedora."
    return txt


def report_md(summary, extra) -> str:
    S = summary
    ports = S["portfolios"]
    L = [f"# Simulação retroativa de {S['window']['days']:g} dias — {S['run_id']}", "",
         f"**Gerado (BRT):** {S['generated_brt']} · **Janela:** {S['window']['start_brt']} → {S['window']['end_brt']} · "
         f"passo de decisão {S['window']['step_s']} s · paper only (nenhuma ordem real, nenhuma chave).", "",
         "## Vencedor", "", S["winner"]["text"], "",
         f"- Por habilidade: **{S['winner']['by_skill']}** · por PnL: **{S['winner']['by_pnl']}** · "
         f"pelo veredito: **{S['winner']['by_verdict'] or 'nenhum'}**", "",
         "## Método", "",
         "Para cada portfólio do catálogo atual do run ao vivo (originais SOL e memecoins, regras, híbridos, hipóteses "
         "H1–H4 e EXP, forks de parâmetros e de critérios, Jev, Laya, poorjev) e para os livros A e B do bot real, o "
         f"backtest repete {S['window']['days']:g} dias minuto a minuto com o MESMO código dos bots ao vivo (portões, cooldown, "
         "trades/h, fração de compra, teto de exposição, saídas TP/SL/trailing e reentrada, horas, ensemble por percentil, "
         "filtro de regime, ordens limite, regras em barras de 1 h), trocando só o relógio, os ficheiros e as cotações "
         "(backtest/simenv.py). Os modelos (von, Laya, poorjev; Jev hospedado nos portfólios SOL) respondem a cada estado "
         "de 12 adjetivos reconstruído do histórico; cada par (critérios, estado) é chamado uma vez e guardado em cache.", "",
         "## Pressupostos", ""]
    L += [f"- {a}" for a in S["assumptions"]]
    L += ["", "## Dados", "", "| Ativo | Fonte | Cobertura | Início | Fim | Retorno |", "|---|---|---:|---:|---:|---:|"]
    for sym, a in S["assets"].items():
        L.append(f"| {sym} | {a['source']} | {a['coverage'] * 100:.2f}% | {a['start_px']:.6g} | {a['end_px']:.6g} | {a['ret_pct']:+.2f}% |")
    L += ["", "## Modelos", "", "| Modelo | Chamadas | Cache | Cobertura | conf P50 | conf P90 |", "|---|---:|---:|---:|---:|---:|"]
    for m, d in S["models"].items():
        L.append(f"| {m} | {d['calls']} | {d['cache_hits']} | {fmt((d['coverage'] or 0) * 100, 1)}% | {fmt(d['conf_p50'], 3)} | {fmt(d['conf_p90'], 3)} |")
    long_run = bool(S.get("consistency", {}).get("unit") == "meses")
    blk_title = "Meses > B&H" if long_run else "Semanas > B&H"
    hdr = [f"| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | Timing $ (p) | MDD % | Trades (C/V) | Exposição % | {blk_title} | Veredito |",
           "|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|"]

    def rows(ps):
        out = []
        for i, p in enumerate(ps, 1):
            tp = f"{fmt(p['timing'], 2, True)} ({fmt(p['timing_p'], 2)})" if p["timing"] is not None else "–"
            out.append(f"| {i} | {p['name']}{' ⚠' if p.get('look_ahead') else ''} | {p['family']} | {fmt(p['pnl_pct'], 2, True)} | "
                       f"{fmt(p['vs_bh'], 2, True)} | **{fmt(p['skill'], 2, True)}** | {tp} | {fmt(p['max_dd_pct'], 2)} | "
                       f"{p['trades']} ({p['buys']}/{p['sells']}) | {fmt(p['exposure_pct'], 1)} | "
                       + (f"{p.get('months_beat_bh')}/{len(p.get('months') or [])}" if long_run else f"{p['weeks_beat_bh']}/4")
                       + f" | {p['verdict']} |")
        return out
    L += ["", "## Top 15 por habilidade (excesso ajustado à exposição)", "", *hdr,
          *rows(sorted(ports, key=lambda p: -(p["skill"] if p["skill"] is not None else -1e9))[:15])]
    L += ["", "## Top 15 por PnL", "", *hdr, *rows(sorted(ports, key=lambda p: -p["pnl_pct"])[:15])]
    L += ["", "⚠ = fork ou hipótese desenhada com dados do run ao vivo que se sobrepõem ao fim desta janela (ver Cuidados).", "",
          "## Famílias", "", "| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor | Pior |",
          "|---|---:|---:|---:|---:|---|---|"]
    for f in S["families"]:
        L.append(f"| {f['family']} | {f['n']} | {fmt(f['median_pnl_pct'], 2, True)} | {fmt(f.get('median_skill'), 2, True)} | "
                 f"{f['beat_bh']}/{f['n']} | {f['best']} | {f['worst']} |")
    L += ["", "## Bot real: livro A × livro B", "",
          "| Livro | Perfil | Valor ini. | Valor fim | PnL $ | PnL % | vs segurar $ | Acerto 15 min | MDD % | Trades | Saídas |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for b in S["realbot"]:
        ex = ", ".join(f"{k}:{v}" for k, v in (b.get("exits") or {}).items()) or "–"
        L.append(f"| {b['book']} | {b['profile']} | {b['start_value']:.4f} | {b['end_value']:.4f} | {b['pnl']:+.4f} | "
                 f"{b['pnl_pct']:+.2f}% | {b['vs_hold']:+.4f} | {fmt((b['hit_15m'] or 0) * 100, 1) if b['hit_15m'] is not None else '–'}% | "
                 f"{b['max_dd_pct']:.2f} | {b['trades']} | {ex} |")
    V = S.get("validation") or {}
    if V.get("states") or V.get("models"):
        L += ["", "## Validação contra o run ao vivo", "",
              f"Período comum: {' → '.join(V.get('overlap_brt') or [])}. Palavras de mercado do estado reconstruído × registadas "
              "ao vivo no mesmo instante (portfólio dono do estado):", "",
              "| Ativo | Decisões | Estado de mercado igual | move | vol | color | rng |", "|---|---:|---:|---:|---:|---:|---:|"]
        for k, v in (V.get("states") or {}).items():
            if v.get("n"):
                L.append(f"| {k} | {v['n']} | {v['exact_market'] * 100:.1f}% | {v.get('move', 0) * 100:.1f}% | {v.get('vol', 0) * 100:.1f}% | "
                         f"{v.get('color', 0) * 100:.1f}% | {v.get('rng', 0) * 100:.1f}% |")
        L += ["", "Respostas dos modelos do backtest × ao vivo para os mesmos estados (critérios baseline):", "",
              "| Modelo | Estados ao vivo | Comparados | Mesma ação | Confiança ±0,01 |", "|---|---:|---:|---:|---:|"]
        for k, v in (V.get("models") or {}).items():
            L.append(f"| {k} | {v['states_live']} | {v['compared']} | {fmt((v['same_action'] or 0) * 100, 1)}% | "
                     f"{fmt((v['conf_within_0.01'] or 0) * 100, 1)}% |")
        tc = V.get("trades_overlap") or {}
        if tc:
            L += ["", "Trades no período comum (ao vivo × simulado; posições iniciais diferentes, só ordem de grandeza): " +
                  ", ".join(f"{k} {v['live']}×{v['sim']}" for k, v in sorted(tc.items(), key=lambda kv: -(kv[1]['live'] + kv[1]['sim']))[:25])]
    L += ["", "## Vereditos", "",
          f"- vencedoras: {sum(1 for p in ports if p['verdict'] == 'vencedora')}, perdedoras: "
          f"{sum(1 for p in ports if p['verdict'] == 'perdedora')}, inconclusivas: {sum(1 for p in ports if p['verdict'] == 'inconclusiva')}.",
          (f"- Regra: a do run ao vivo (`bot/analytics.verdict`), com a janela de {S['window']['days']:g} dias a cumprir os dias "
           "mínimos; continua a exigir ≥ 30 round trips fechados."
           + (" Consistência mensal em vez de semanal: excesso vs B&H positivo em ≥ "
              f"{S['consistency']['need']} de {S['consistency']['n']} blocos de 30 dias; séries e bootstrap em grelha de 1 h "
              "(blocos de 12 h)." if long_run else "")), "",
          "## Cuidados", ""]
    if any(p.get("look_ahead") for p in ports):
        L += ["- **Look-ahead / sobreajuste:** os forks (e os textos de critérios dos forks de critérios) foram desenhados pela "
              "revisão noturna com os dias 1–5 do run ao vivo (2026-10-01 → 2026-10-06), que estão dentro desta janela. "
              "O resultado deles nessa parte é dentro da amostra; compare-os sobretudo no período anterior (colunas de "
              "semanas/meses no summary.json). Portfólios afetados marcados com ⚠."]
    else:
        L += ["- **Sem look-ahead nos forks:** esta janela acaba antes de 2026-10-01; os forks desenhados pela revisão "
              "noturna com os dias 2026-10-01 → 2026-10-06 estão aqui totalmente fora da amostra."]
    L += [
          "- Os parâmetros do relaxed (conf ≥ 0,35, margem ≥ 0,20) foram calibrados nas primeiras decisões do von no início "
          "de setembro de 2026 e o v2 usa critérios reescritos em 2026-09-24"
          + (": nesta janela (que acaba antes de setembro) estão fora da amostra." if S["window"]["end_brt"] < "2026-09-01"
             else "; janelas que incluem esses dias têm essa parte dentro da amostra."),
          "- Estados: SOL a partir de uma grelha de 10 s da Binance (o histórico ao vivo tem ~1 marca a cada 10,4 s); "
          "memecoins a partir de fechos de 1 m; palavras de profundidade/taxas constantes (como ao vivo). Pequenas diferenças "
          "de amostragem mudam algumas palavras de movimento/volatilidade.",
          "- Fills: cotação sintética = marca do minuto ± custo mediano por ativo medido nos fills reais do run ao vivo; "
          "as variantes `_full` (100% do saldo) podem ter mais impacto do que o estimado.",
          "- Decisão a cada 60 s (ao vivo: SOL a cada ~15 s, memecoins a cada ~7 min por moeda, lab a cada 15 s); "
          "o bot real a cada 15 s.", ""]
    if extra.get("notes"):
        L += ["## Notas da execução", ""] + [f"- {n}" for n in extra["notes"]] + [""]
    return "\n".join(L)
