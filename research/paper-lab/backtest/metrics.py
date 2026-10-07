"""Métricas do run ao vivo (bot/analytics.py) sobre as séries simuladas, e o veredito adaptado a 30 dias.

`window_stats_rows` é a mesma conta de `analytics.window_stats`, mas sobre linhas em memória (o analytics lê ficheiros):
usa `_grid_series`, `placebo_p` e as mesmas fórmulas (exposição média, excesso ajustado à exposição = habilidade,
timing com p de placebo, MDD, custos vs marca). O teste `test_backtest_metrics` confirma a igualdade com
`analytics.window_stats` num caso sintético.

Veredito (regra ao vivo, `analytics.verdict`, adaptada à janela do backtest): mínimos de ≥ 30 round trips fechados e
dias ≥ 21 (≥ 28 para regras/regime/híbridos) — a janela de 30 dias cumpre os dias; vencedora = bate o B&H (excesso > 0
com p < 0,05 por block-bootstrap dos incrementos de 5 min do excesso) E o PnL passa a barra de 6%/a em USDC E o excesso
é positivo em ≥ 3 das 4 semanas; perdedora = excesso < 0 com p < 0,05; senão inconclusiva.

Janelas longas (ex.: 180 dias): a MESMA regra e os mesmos algoritmos, com duas mudanças de escala documentadas no
relatório: (1) a grelha das séries passa de 5 min para 1 h (`grid=3600`): o placebo do timing é O(n²) e a 5 min
seriam 51 840 pontos por portfólio; o bootstrap usa blocos de 12 pontos (= 12 h, em vez de 1 h); (2) a consistência
semanal passa a mensal: blocos de 30 dias contados do fim da janela e excesso positivo em ≥ 4 de 6 meses
(`block_s=30 dias`, `need_blocks=4`). As 4 últimas semanas continuam a ser calculadas (campo `weeks_*`).
"""
from __future__ import annotations

import numpy as np

from bot import analytics as A

WEEK = 7 * 86400
MONTH = 30 * 86400


def _rows_for_analytics(rows):
    return [{"ts": r["ts"], "equity": r["equity"], "price": r["price"], "bh_equity": r["bh_equity"], "sol": r["q"]} for r in rows]


def window_stats_rows(rows, trades, t_a, t_b, grid=300.0):
    """Espelho de analytics.window_stats para linhas em memória (ts, equity, price, bh_equity, q)."""
    rows = _rows_for_analytics(rows)
    out = {"from": t_a, "to": t_b}
    before = [r for r in rows if r["ts"] <= t_a]
    inwin = [r for r in rows if t_a < r["ts"] <= t_b]
    if not inwin:
        out["empty"] = True
        return out
    r0 = before[-1] if before else inwin[0]
    r1 = inwin[-1]
    E0, E1 = float(r0["equity"]), float(r1["equity"])
    BH0, BH1 = float(r0["bh_equity"]), float(r1["bh_equity"])
    pnl = E1 - E0
    series = [r0] + inwin
    em = np.array([float(r["equity"]) for r in series])
    pk = np.maximum.accumulate(em)
    out.update(start_value=E0, end_value=E1, pnl=pnl, pnl_pct=pnl / E0 * 100 if E0 else 0.0, bh_pnl=BH1 - BH0,
               ex_bh=pnl - (BH1 - BH0), ex_usdt=pnl, mdd_pct=float(((em - pk) / pk).min() * 100), hours=(r1["ts"] - t_a) / 3600)
    gs = A._grid_series(series, t_a, t_b, step=grid)
    if gs:
        g, E, P, BH, Q = gs
        W = np.where(E > 0, Q * P / E, 0)
        rp = np.diff(E) / E[:-1]
        ra = np.diff(P) / np.where(P[:-1] > 0, P[:-1], 1)
        wl = W[:-1]
        out["exposure_pct"] = float(W.mean() * 100)
        if len(ra):
            out["static_usd"] = float(wl.mean() * ra.sum() * E0)
            out["timing_usd"] = float(((wl - wl.mean()) * ra).sum() * E0)
            out["timing_p"] = A.placebo_p(wl, ra)
            out["ex_exposure"] = pnl - out["static_usd"]
    tr = [t for t in trades if t_a < t["ts"] <= t_b]
    fees = cost = 0.0
    sells = wins = 0
    for t in tr:
        f = t.get("fill") or {}
        pm = float(t.get("price_mark") or f.get("mark_price") or 0)
        fees += float(f.get("fee_usdt") or 0)
        if t["side"] == "buy":
            q = float(f.get("sol_out_net") or f.get("token_out_net") or 0)
            cost += float(f.get("usdt_in") or 0) - q * pm
        else:
            q = float(f.get("sol_in") or f.get("token_in") or 0)
            cost += q * pm - float(f.get("usdt_out_net") or 0)
            sells += 1
            wins += 1 if float(f.get("approx_pnl") or 0) > 0 else 0
    out.update(trades=len(tr), buys=len(tr) - sells, sells=sells, rt_wins=wins, fees=fees, cost_vs_mark=cost)
    if not tr:
        out["timing_p"] = None
    return out


def excess_increments(rows, t_a, t_b, usdc_apy=0.06, grid=300.0):
    """(tempos, incrementos (5 min, ou `grid` s) do excesso vs B&H, incrementos do excesso vs barra USDC)."""
    rows = _rows_for_analytics(rows)
    g = A._grid_series(rows, t_a, t_b, step=grid)
    if not g:
        return None, None, None
    gg, E, P, BH, Q = g
    dE = np.diff(E)
    x_bh = dE - np.diff(BH)
    step_bar = E[0] * usdc_apy * (gg[1] - gg[0]) / (365 * 86400)
    x_usdc = dE - step_bar
    return gg[1:], x_bh, x_usdc


def blocks(rows, ts, x, t_b, block_s, n_blocks):
    """PnL % por bloco (do mais antigo ao mais recente) e quantos blocos têm excesso vs B&H > 0. Blocos de `block_s`
    segundos contados do fim da janela."""
    pnl, pos, n = [], 0, 0
    times = np.array([r["ts"] for r in rows])
    E = np.array([r["equity"] for r in rows])
    for k in range(n_blocks - 1, -1, -1):
        b = t_b - block_s * k
        a = b - block_s
        ia = int(np.searchsorted(times, a, side="right")) - 1
        ib = int(np.searchsorted(times, b, side="right")) - 1
        if ia < 0:
            ia = 0
        pnl.append(round(float((E[ib] - E[ia]) / E[ia] * 100), 4) if E[ia] else 0.0)
        if ts is not None:
            m = (ts > a) & (ts <= b)
            if m.sum() > 10:
                n += 1
                pos += 1 if x[m].sum() > 0 else 0
    return pnl, pos, n


def verdict(name, meta, rows, trades, t_a, t_b, cfg=None, grid=300.0, block_s=WEEK, n_blocks=4, need_blocks=None):
    """Veredito do run ao vivo. Consistência: blocos de `block_s` (semanas; meses nas janelas longas), excesso
    positivo em ≥ `need_blocks` de `n_blocks` (padrão: a regra ao vivo, 3 de 4 semanas)."""
    c = dict(A.VERDICT_DEFAULTS)
    c.update(cfg or {})
    need_blocks = c["weeks_consistent"][0] if need_blocks is None else int(need_blocks)
    unit = "semanas" if block_s == WEEK else "meses"
    s = window_stats_rows(rows, trades, t_a, t_b, grid=grid)
    closed = int(s.get("sells") or 0)
    days = (t_b - t_a) / 86400
    rr = A.is_rule_or_regime(name, meta)
    need_days = c["min_days_rule_regime"] if rr else c["min_days"]
    ts, x, xu = excess_increments(rows, t_a, t_b, c["usdc_apy"], grid=grid)
    p_win, p_lose = A.block_boot_p(x, c["boot_block"], c["boot_n"])
    pu_win, _pu_lose = A.block_boot_p(xu, c["boot_block"], c["boot_n"])
    usdc_bar = s["start_value"] * c["usdc_apy"] * days / 365
    weeks_pnl, weeks_pos, weeks = blocks(rows, ts, x, t_b, WEEK, 4)
    if block_s == WEEK and n_blocks == 4:
        b_pnl, b_pos, b_n = weeks_pnl, weeks_pos, weeks
    else:
        b_pnl, b_pos, b_n = blocks(rows, ts, x, t_b, block_s, n_blocks)
    out = {"stats": s, "p_bh": p_win, "p_bh_lose": p_lose, "p_usdc": pu_win, "usdc_bar": usdc_bar, "weeks_pnl": weeks_pnl,
           "weeks_beat_bh": weeks_pos, "weeks": weeks, "closed_rt": closed, "need_days": need_days, "days": days,
           "blocks_pnl": b_pnl, "blocks_beat_bh": b_pos, "blocks": b_n, "block_unit": unit, "need_blocks": need_blocks,
           "n_blocks": n_blocks}
    minimums = closed >= c["min_closed_rt"] and days >= need_days
    if not minimums:
        why = []
        if closed < c["min_closed_rt"]:
            why.append(f"{closed}/{c['min_closed_rt']} round trips fechados")
        if days < need_days:
            why.append(f"{days:.1f}/{need_days} dias")
        out.update(verdict="inconclusiva", verdict_reason="mínimos não atingidos: " + ", ".join(why))
    elif (s["ex_bh"] > 0 and s["pnl"] > usdc_bar and p_win is not None and p_win < c["p_max"]
          and b_pos >= need_blocks):
        out.update(verdict="vencedora", verdict_reason="bate o B&H e a barra de 6%/a em USDC, p<0,05 líquido de custos, "
                                                       f"excesso positivo em {b_pos} de {n_blocks} {unit}")
    elif s["ex_bh"] < 0 and p_lose is not None and p_lose < c["p_max"]:
        out.update(verdict="perdedora", verdict_reason="pior que o B&H com p<0,05")
    else:
        bits = []
        if s["ex_bh"] <= 0:
            bits.append("não bate o B&H")
        elif p_win is None or p_win >= c["p_max"]:
            bits.append(f"bate o B&H sem significância (p={p_win if p_win is None else round(p_win, 3)})")
        if s["pnl"] <= usdc_bar:
            bits.append("abaixo da barra USDC")
        if b_pos < need_blocks:
            bits.append(f"excesso positivo só em {b_pos} de {n_blocks} {unit}")
        out.update(verdict="inconclusiva", verdict_reason="mínimos atingidos, mas " + "; ".join(bits or ["sem significância"]))
    return out


def max_dd_pct(values):
    v = np.array(values, dtype=float)
    if len(v) == 0:
        return 0.0
    pk = np.maximum.accumulate(v)
    return float(((v - pk) / pk).min() * 100)
