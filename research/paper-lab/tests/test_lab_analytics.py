"""bot/analytics.py: funções puras e estatísticas de janela sobre fixtures pequenas."""
import json

import pytest

np = pytest.importorskip("numpy")
from bot import analytics as A  # noqa: E402


def write_jsonl(path, rows, junk=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        if junk:
            f.write("{not json\n\n")


def test_jl_skips_bad_lines_and_missing(tmp_path):
    p = tmp_path / "x.jsonl"
    write_jsonl(p, [{"a": 1}, {"a": 2}], junk=True)
    assert [r["a"] for r in A.jl(p)] == [1, 2]
    assert A.jl(tmp_path / "missing.jsonl") == []


def test_day_bounds_are_brt():
    a, b = A.day_bounds("2026-09-30")
    assert b - a == 86400
    assert a == 1790737200.0  # 2026-09-30T00:00:00-03:00


def test_fmt():
    assert A.fmt(None) == "–" and A.fmt(float("nan")) == "–"
    assert A.fmt(1.23456, 3) == "1.235" and A.fmt(2.0, 1, sign=True) == "+2.0"


def test_placebo_and_bootstrap():
    assert A.placebo_p(np.ones(10), np.ones(10)) is None
    rng = np.random.default_rng(1)
    w = np.concatenate([np.ones(30), np.zeros(30)]); r = np.concatenate([np.full(30, 0.01), np.full(30, -0.01)])
    p = A.placebo_p(w, r)
    assert p is not None and 0.0 <= p <= 0.1
    assert A.block_boot_p(np.ones(5)) == (None, None)
    x = rng.normal(0.5, 0.1, 200)
    p_win, p_lose = A.block_boot_p(x)
    assert p_win < 0.05 and p_lose > 0.95


def test_rule_or_regime():
    assert A.is_rule_or_regime("rsi_sol_1h", {})
    assert A.is_rule_or_regime("BONK_hybrid_poorjev_regime", {})
    assert not A.is_rule_or_regime("relaxed", {"kind": "gated"})


def _equity(tmp_path, t0):
    rows = []
    for i in range(0, 13):  # 1 h, pontos a cada 5 min; entra comprado a meio
        px = 100.0 + i
        sol = 0.0 if i < 6 else 1.0
        usdt = 1000.0 if i < 6 else 1000.0 - 106.0
        rows.append({"ts": t0 + i * 300, "price": px, "sol": sol, "usdt": usdt, "equity": usdt + sol * px,
                     "bh_equity": 1000.0})
    p = tmp_path / "equity_test.jsonl"
    write_jsonl(p, rows)
    return p


def test_window_stats_on_fixture(tmp_path):
    t0 = 1_790_000_000.0
    meta = {"name": "test", "start_ts": t0, "equity": str(_equity(tmp_path, t0))}
    trades = {"test": [{"ts": t0 + 1800, "side": "buy", "price_mark": 106.0,
                        "fill": {"usdt_in": 106.0, "sol_out_net": 0.99, "fee_usdt": 0.05, "fill_mode": "jupiter_quote"}}]}
    s = A.window_stats(meta, trades, t0, t0 + 3600)
    assert s["pnl"] == pytest.approx(6.0)          # 1 SOL comprado a 106, fecha a 112
    assert s["ex_bh"] == pytest.approx(6.0)        # B&H constante
    assert s["trades"] == 1 and s["buys"] == 1 and s["sells"] == 0
    assert s["fees"] == pytest.approx(0.05) and s["fill_modes"] == {"jupiter_quote": 1}
    assert s["cost_vs_mark"] == pytest.approx(106.0 - 0.99 * 106.0)
    assert s["mdd_pct"] == pytest.approx(0.0)
    assert 0 < s["exposure_pct"] < 100
    assert A.window_stats(meta, trades, t0 + 7200, t0 + 9000).get("empty")


def test_verdict_is_inconclusive_before_minimums(tmp_path):
    t0 = 1_790_000_000.0
    meta = {"name": "relaxed", "start_ts": t0, "equity": str(_equity(tmp_path, t0)), "kind": "gated"}
    v = A.verdict(meta, {"relaxed": [{"ts": t0 + 10, "side": "sell"}]}, now_ts=t0 + 2 * 86400)
    assert v["verdict"] == "inconclusivo" and v["reason"] == "mínimos não atingidos"
    assert v["progress"]["closed_rt"] == 1 and v["progress"]["min_days"] == 21
