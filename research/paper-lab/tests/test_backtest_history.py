"""Backtest: histórico dos runs (index.json, latest, history.md) e chart.json das janelas longas — dados sintéticos."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import numpy as np

from backtest import history as H
from backtest import metrics as MET
from backtest.simenv import BRT

DAY = 86400


def _summary(run_id, end_iso, days, ports=None, look=()):
    end = datetime.fromisoformat(end_iso)
    ports = ports or [
        {"name": "a", "family": "SOL · von", "pnl_pct": 5.0, "skill": 10.0, "vs_bh": 3.0, "verdict": "vencedora", "trades": 40},
        {"name": "b", "family": "SOL · von", "pnl_pct": 9.0, "skill": -2.0, "vs_bh": -1.0, "verdict": "perdedora", "trades": 4},
        {"name": "c", "family": "Meme · regras", "pnl_pct": -1.0, "skill": None, "vs_bh": 0.5, "verdict": "inconclusiva", "trades": 0},
    ]
    for p in ports:
        p.setdefault("look_ahead", p["name"] in look)
        p.setdefault("max_dd_pct", -1.0)
    return {"run_id": run_id, "generated_brt": "2026-10-07T01:00:00-03:00",
            "window": {"start_brt": (end - timedelta(days=days)).isoformat(), "end_brt": end.isoformat(), "days": days},
            "portfolios": ports, "winner": {"by_skill": "a", "by_pnl": "b", "by_verdict": "a"},
            "realbot": [{"book": "A", "pnl_pct": 1.5, "vs_hold": 0.2, "trades": 3}, {"book": "B", "pnl_pct": -0.5, "vs_hold": -0.1, "trades": 9}],
            "assets": {"SOL": {"ret_pct": 13.0}, "BONK": {"ret_pct": -4.0}}, "families": [], "notes": []}


def _write(base, s):
    d = base / s["run_id"]
    d.mkdir(parents=True)
    (d / "summary.json").write_text(json.dumps(s))


def test_index_entry_fields_and_order(tmp_path):
    _write(tmp_path, _summary("bt30_2026-09-06", "2026-09-06T09:00:00-03:00", 31))
    _write(tmp_path, _summary("bt30_2026-10-06", "2026-10-06T09:00:00-03:00", 30, look=("a",)))
    _write(tmp_path, _summary("bt180_2026-10-06", "2026-10-06T09:00:00-03:00", 180))
    (tmp_path / "_cache").mkdir()                       # pastas sem summary (cache) são ignoradas
    idx = H.update_index(tmp_path)
    ids = [e["run_id"] for e in idx["runs"]]
    assert set(ids) == {"bt30_2026-09-06", "bt30_2026-10-06", "bt180_2026-10-06"}
    assert ids[-1] == "bt30_2026-09-06"                   # ordenado pelo fim da janela, mais recente primeiro
    e = next(x for x in idx["runs"] if x["run_id"] == "bt30_2026-10-06")
    assert e["kind"] == "30d" and e["n_portfolios"] == 3
    assert (e["n_winners"], e["n_losers"], e["n_inconclusive"]) == (1, 1, 1)
    assert [x["name"] for x in e["top_pnl"]] == ["b", "a", "c"] and [x["name"] for x in e["top_skill"]][:2] == ["a", "b"]
    assert set(e["top_skill"][0]) == {"name", "skill", "pnl_pct"}
    assert e["realbot"] == [{"book": "A", "pnl_pct": 1.5, "vs_hold": 0.2}, {"book": "B", "pnl_pct": -0.5, "vs_hold": -0.1}]
    assert e["assets"] == {"SOL": 13.0, "BONK": -4.0} and e["look_ahead_forks"] == ["a"]
    assert e["winner"] == {"by_skill": "a", "by_pnl": "b", "by_verdict": "a"}
    assert next(x for x in idx["runs"] if x["run_id"] == "bt180_2026-10-06")["kind"] == "180d"
    assert next(x for x in idx["runs"] if x["run_id"] == "bt30_2026-09-06")["kind"] == "30d"   # 31 dias = mensal
    assert json.loads((tmp_path / "index.json").read_text())["runs"] == idx["runs"]


def test_index_rebuilt_when_missing_or_invalid_and_drops_deleted_runs(tmp_path):
    _write(tmp_path, _summary("bt30_2026-10-06", "2026-10-06T09:00:00-03:00", 30))
    (tmp_path / "index.json").write_text("{not json")
    idx = H.update_index(tmp_path)
    assert [e["run_id"] for e in idx["runs"]] == ["bt30_2026-10-06"]
    # entrada nova pelo summary (upsert) + entrada antiga cuja pasta desapareceu sai
    idx["runs"].append({"run_id": "gone", "end_brt": "2026-01-01T00:00:00-03:00"})
    (tmp_path / "index.json").write_text(json.dumps(idx))
    s2 = _summary("bt30_2026-09-06", "2026-09-06T09:00:00-03:00", 31)
    _write(tmp_path, s2)
    idx = H.update_index(tmp_path, s2)
    assert [e["run_id"] for e in idx["runs"]] == ["bt30_2026-10-06", "bt30_2026-09-06"]


def test_latest_points_to_newest_monthly_run(tmp_path):
    _write(tmp_path, _summary("bt30_2026-10-06", "2026-10-06T09:00:00-03:00", 30))
    (tmp_path / "latest").write_text("bt30_2026-10-06\n")
    # mês anterior e janela longa não mudam o latest
    assert H.latest_after(tmp_path, "bt30_2026-09-06", "30d", "2026-09-06T09:00:00-03:00") == "bt30_2026-10-06"
    assert H.latest_after(tmp_path, "bt180_2026-10-06", "180d", "2026-10-06T09:00:00-03:00") == "bt30_2026-10-06"
    # um mês mais recente muda
    assert H.latest_after(tmp_path, "bt30_2026-11-06", "30d", "2026-11-06T09:00:00-03:00") == "bt30_2026-11-06"
    # sem latest (ou a apontar para um run não mensal) → este run mensal
    (tmp_path / "latest").unlink()
    assert H.latest_after(tmp_path, "bt30_2026-09-06", "30d", "2026-09-06T09:00:00-03:00") == "bt30_2026-09-06"


def test_history_md_compares_months_and_consistency(tmp_path):
    for rid, end, sk in (("bt30_2026-08-06", "2026-08-06T09:00:00-03:00", 4.0), ("bt30_2026-09-06", "2026-09-06T09:00:00-03:00", 2.0),
                         ("bt30_2026-10-06", "2026-10-06T09:00:00-03:00", 1.0)):
        s = _summary(rid, end, 30)
        s["portfolios"][0]["skill"] = sk
        _write(tmp_path, s)
    md = H.history_md(tmp_path)
    assert "## Meses lado a lado" in md and "bt30_2026-08-06" in md and "Top 5 por PnL" in md
    assert "Habilidade positiva em TODOS os 3 meses: a." in md
    rows = {r["name"]: r for r in H.consistency([json.loads((tmp_path / r / "summary.json").read_text())
                                                 for r in ("bt30_2026-08-06", "bt30_2026-09-06", "bt30_2026-10-06")])}
    assert rows["a"]["skill_pos"] == 3 and rows["b"]["skill_pos"] == 0 and abs(rows["b"]["pnl_comp_pct"] - (1.09 ** 3 - 1) * 100) < 1e-9


def test_month_blocks_and_chart_times():
    end = int(datetime.fromisoformat("2026-10-06T09:00:00-03:00").timestamp())
    start = end - 180 * DAY
    b = H.month_blocks(start, end)
    assert len(b) == 6 and b[0]["a"] == start and b[-1]["b"] == end
    assert [x["month"] for x in b] == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    t = H.chart_times(start, end)
    assert len(t) <= H.MAX_CHART_POINTS and t[0] == start and t[-1] == end and np.all(np.diff(t) > 0)


def test_build_chart_normalizes_and_aggregates():
    start, end = 1_780_000_000 // 3600 * 3600, 1_780_000_000 // 3600 * 3600 + 180 * DAY
    ts = np.arange(start, end + 1, 3600)
    n = len(ts)
    lin = np.linspace(0, 1, n)
    equity = {"x": (ts, 500 * (1 + lin)), "y": (ts, 2000 * (1 + 0.5 * lin)), "z": (ts, 1000 * (1 - 0.1 * lin)),
              "rsi_sol_1h": (ts, 1000 + 0 * lin)}
    ports = [{"name": "x", "family": "F1", "pnl_pct": 100.0, "skill": 1.0}, {"name": "y", "family": "F1", "pnl_pct": 50.0, "skill": 3.0},
             {"name": "z", "family": "F2", "pnl_pct": -10.0, "skill": None},
             {"name": "rsi_sol_1h", "family": "F2", "pnl_pct": 0.0, "skill": 0.5}]
    prices = {"SOL": (ts, 100 * (1 + lin))}
    for k, m in enumerate(H.MEMES):
        prices[m] = (ts, (k + 1) * (1 + (0.7 if k == 0 else 0.0) * lin))     # só a 1.ª moeda sobe 70%
    ch = H.build_chart(start=start, end=end, equity=equity, ports=ports, prices=prices,
                       realbot={"A": (ts, 50 * (1 + 0.1 * lin)), "B": (ts, 50 + 0 * lin)}, months=[{"month": "2026-04"}])
    assert len(ch["t"]) <= 1500 and ch["t"][0] == start and ch["t"][-1] == end
    L = len(ch["t"])
    for series in [*ch["benchmarks"].values(), *ch["families"].values(), *ch["top"].values(), *ch["realbot"].values()]:
        if isinstance(series, list) and series and isinstance(series[0], (int, float)):
            assert len(series) == L
    assert ch["benchmarks"]["sol_bh"][0] == 1000 and abs(ch["benchmarks"]["sol_bh"][-1] - 2000) < 1e-6
    assert abs(ch["benchmarks"]["memes_bh"][-1] - 1000 * (1 + 0.7 / 7)) < 1e-6
    assert abs(ch["benchmarks"]["usdc"][-1] - 1000 * (1 + 0.06 * 180 / 365)) < 0.01
    # mediana da família F1 = média de x (2000) e y (1500) no fim, tudo normalizado a 1000
    assert ch["families"]["F1"][0] == 1000 and abs(ch["families"]["F1"][-1] - 1750) < 1e-6
    assert list(ch["top"])[:2] == ["y", "x"] and "rsi_sol_1h" in ch["top"] and "relaxed" not in ch["top"]
    assert abs(ch["top"]["x"][-1] - 2000) < 1e-6 and abs(ch["realbot"]["A"][-1] - 1100) < 1e-6
    assert ch["monthly"] == [{"month": "2026-04"}]


def test_monthly_consistency_verdict_on_hourly_grid():
    """Janela longa: mesma regra, grelha de 1 h e consistência ≥ 4 de 6 meses."""
    t0 = 1_780_000_000 // 3600 * 3600
    n = 180 * 24 + 1
    rng = np.random.default_rng(1)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    rows = [{"ts": t0 + 3600 * i, "equity": float(500 + 5 * px[i] + 0.2 * i), "price": float(px[i]),
             "bh_equity": float(500 + 5 * px[i]), "q": 5.0} for i in range(n)]
    sells = [{"ts": t0 + 7200 * i + 1, "side": "sell", "price_mark": 100.0, "fill": {"sol_in": 0.1, "usdt_out_net": 10.0}}
             for i in range(40)]
    v = MET.verdict("relaxed", {"kind": "gated"}, rows, sells, t0, t0 + (n - 1) * 3600, grid=3600, block_s=MET.MONTH,
                    n_blocks=6, need_blocks=4)
    assert v["block_unit"] == "meses" and len(v["blocks_pnl"]) == 6 and v["blocks_beat_bh"] == 6
    assert v["verdict"] == "vencedora" and "6 de 6 meses" in v["verdict_reason"] and len(v["weeks_pnl"]) == 4
    # excesso só nos 2 primeiros meses (depois uma pequena perda) → falha a consistência mensal
    rows2 = [dict(r, equity=r["bh_equity"] + 0.6 * min(i, 60 * 24) - 0.01 * max(0, i - 60 * 24)) for i, r in enumerate(rows)]
    v2 = MET.verdict("relaxed", {"kind": "gated"}, rows2, sells, t0, t0 + (n - 1) * 3600, grid=3600, block_s=MET.MONTH,
                     n_blocks=6, need_blocks=4)
    assert v2["blocks_beat_bh"] == 2 and v2["verdict"] != "vencedora" and "2 de 6 meses" in v2["verdict_reason"]
