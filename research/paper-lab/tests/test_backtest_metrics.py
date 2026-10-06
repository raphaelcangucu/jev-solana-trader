"""Backtest: métricas sobre séries em memória = bot/analytics.window_stats sobre ficheiro; veredito adaptado."""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from bot import analytics as A
from backtest import metrics as MET
from backtest import report as REP

T0 = 1_790_900_000 // 300 * 300     # outubro de 2026 (fora das janelas DOWN do analytics)


def _series(n=2000, seed=3, drift=0.0):
    rng = np.random.default_rng(seed)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    q = np.where(rng.random(n) < 0.5, 3.0, 0.5)
    usdt = 600 + np.cumsum(rng.normal(drift, 0.05, n))
    rows = [{"ts": T0 + 300 * i, "equity": float(usdt[i] + q[i] * px[i]), "price": float(px[i]),
             "bh_equity": float(600 + 4 * px[i]), "q": float(q[i])} for i in range(n)]
    trades = [{"ts": T0 + 300 * i + 1, "side": "buy" if i % 2 else "sell", "price_mark": float(px[i]),
               "fill": ({"usdt_in": 10.0, "sol_out_net": 10 / px[i] * 0.999, "fee_usdt": 0.01} if i % 2 else
                        {"sol_in": 0.1, "usdt_out_net": 0.1 * px[i] * 0.999, "fee_usdt": 0.01, "approx_pnl": 0.02})}
              for i in range(10, n - 10, 37)]
    return rows, trades


def test_window_stats_rows_equals_analytics(tmp_path):
    rows, trades = _series()
    p = tmp_path / "eq.jsonl"
    with open(p, "w") as f:
        for r in rows:
            f.write(json.dumps({"ts": r["ts"], "equity": r["equity"], "price": r["price"], "bh_equity": r["bh_equity"],
                                "sol": r["q"]}) + "\n")
    meta = {"name": "x", "equity": str(p), "start_ts": T0}
    t_a, t_b = T0, rows[-1]["ts"]
    live = A.window_stats(meta, {"x": trades}, t_a, t_b)
    mine = MET.window_stats_rows(rows, trades, t_a, t_b)
    for k in ("start_value", "end_value", "pnl", "pnl_pct", "ex_bh", "mdd_pct", "exposure_pct", "static_usd",
              "timing_usd", "timing_p", "ex_exposure", "trades", "buys", "sells", "fees", "cost_vs_mark"):
        a, b = live[k], mine[k]
        assert (a is None and b is None) or math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9), (k, a, b)


def test_verdict_minimums_and_weeks():
    rows, trades = _series(n=8640)          # 30 dias em passos de 5 min
    t_a, t_b = T0, T0 + 8639 * 300
    v = MET.verdict("relaxed", {"kind": "gated"}, rows, trades[:20], t_a, t_b)
    assert v["verdict"] == "inconclusiva" and "round trips" in v["verdict_reason"]   # < 30 RT fechados
    assert len(v["weeks_pnl"]) == 4 and 0 <= v["weeks_beat_bh"] <= 4
    # muitos RT e excesso forte e constante → vencedora
    win_rows = [dict(r, equity=r["bh_equity"] + 0.05 * i) for i, r in enumerate(rows)]
    many = [{"ts": T0 + 600 * i, "side": "sell", "price_mark": 100.0, "fill": {"sol_in": 0.1, "usdt_out_net": 10.0}}
            for i in range(40)]
    v = MET.verdict("relaxed", {"kind": "gated"}, win_rows, many, t_a, t_b)
    assert v["verdict"] == "vencedora" and v["p_bh"] < 0.05 and v["weeks_beat_bh"] == 4
    lose_rows = [dict(r, equity=r["bh_equity"] - 0.05 * i) for i, r in enumerate(rows)]
    assert MET.verdict("relaxed", {"kind": "gated"}, lose_rows, many, t_a, t_b)["verdict"] == "perdedora"


def test_downsample_keeps_last_point_and_cap():
    rows = [{"ts": i, "equity": i, "bh_equity": i} for i in range(8641)]
    d = REP.downsample(rows)
    assert len(d) <= REP.MAX_EQ_POINTS and d[-1]["ts"] == 8640 and d[0]["ts"] == 0
