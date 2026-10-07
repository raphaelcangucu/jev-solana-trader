"""dashboard/backtest_view.py: histórico de runs (index.json), gráfico de 6 meses (chart.json) e history.md."""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "dashboard"))
import backtest_view as BT  # noqa: E402

FIXTURE = LAB / "dashboard" / "fixtures" / "backtest"
SIX = "bt180_2026-10-06"
MONTHS = ["20261006-0300", "bt30_2026-09-06", "bt30_2026-08-06"]


@pytest.fixture()
def base(tmp_path: Path) -> Path:
    b = tmp_path / "backtest"
    shutil.copytree(FIXTURE, b)
    return b


def view(base: Path) -> BT.BacktestView:
    return BT.BacktestView(lambda: base)


def test_fixture_index_matches_contract():
    idx = json.loads((FIXTURE / "index.json").read_text())
    kinds = {r["run_id"]: r["kind"] for r in idx["runs"]}
    assert kinds == {SIX: "180d", **{m: "30d" for m in MONTHS}}
    for r in idx["runs"]:
        for k in ("run_id", "kind", "start_brt", "end_brt", "days", "generated_brt", "n_portfolios", "n_winners", "n_losers",
                  "n_inconclusive", "winner", "top_skill", "top_pnl", "realbot", "assets", "look_ahead_forks"):
            assert k in r, k
        assert set(r["winner"]) >= {"by_skill", "by_pnl", "by_verdict"}
        assert r["n_winners"] + r["n_losers"] + r["n_inconclusive"] == r["n_portfolios"]
        assert all({"name", "skill", "pnl_pct"} <= set(t) for t in r["top_skill"] + r["top_pnl"])
    ch = json.loads((FIXTURE / SIX / "chart.json").read_text())
    n = len(ch["t"])
    assert set(ch["benchmarks"]) == {"sol_bh", "memes_bh", "memes_in_basket", "usdc"}
    for g in ("benchmarks", "families", "top", "realbot"):
        series = [v for k, v in ch[g].items() if k != "memes_in_basket"]
        assert series and all(len(v) == n and v[0] == pytest.approx(1000, abs=1) for v in series)
    assert any(k.startswith("SOL · ") for k in ch["families"]) and any(k.startswith("Meme · ") for k in ch["families"])
    assert set(ch["realbot"]) == {"A", "B"} and len(ch["monthly"]) == 6
    assert {"month", "start_brt", "end_brt", "top_by_pnl", "top_by_skill", "sol_ret", "memes_ret"} <= set(ch["monthly"][0])


def test_index_reads_index_json_marks_available_and_sorts_by_end(base: Path):
    out = view(base).index()
    assert out["source"] == "index" and out["latest"] == "20261006-0300" and out["has_history"]
    ids = [r["run_id"] for r in out["runs"]]
    assert set(ids) == {SIX, *MONTHS}
    ends = [r["end_brt"] for r in out["runs"]]
    assert ends == sorted(ends, reverse=True)
    assert ids.index("bt30_2026-09-06") < ids.index("bt30_2026-08-06")
    assert all(r["available"] for r in out["runs"])


def test_index_drops_unsafe_ids_and_flags_missing_dirs(base: Path):
    idx = json.loads((base / "index.json").read_text())
    idx["runs"] += [{"run_id": "bt183_x", "kind": "183d", "days": 183, "end_brt": "2026-01-01"}, {"run_id": "../../etc", "kind": "30d"}, {"run_id": "bt30_2026-05-06", "kind": "xx", "days": 30, "end_brt": "2026-05-06"},
                    "lixo", {"run_id": SIX, "kind": "180d"}]
    (base / "index.json").write_text(json.dumps(idx))
    runs = {r["run_id"]: r for r in view(base).index()["runs"]}
    assert "../../etc" not in runs
    assert runs["bt183_x"]["kind"] == "180d"  # o gerador escreve "<N>d" para janelas longas
    assert runs["bt30_2026-05-06"]["available"] is False and runs["bt30_2026-05-06"]["kind"] == "30d"
    assert len([r for r in view(base).index()["runs"] if r["run_id"] == SIX]) == 1


def test_index_built_from_summaries_when_missing(base: Path):
    want = {r["run_id"]: r for r in json.loads((base / "index.json").read_text())["runs"]}
    (base / "index.json").unlink()
    out = view(base).index()
    assert out["source"] == "runs"
    got = {r["run_id"]: r for r in out["runs"]}
    assert set(got) == set(want)
    for rid, w in want.items():
        g = got[rid]
        for k in ("kind", "n_portfolios", "n_winners", "n_losers", "n_inconclusive", "winner", "top_skill", "top_pnl", "realbot", "assets"):
            assert g[k] == w[k], (rid, k)
    assert got["20261006-0300"]["look_ahead_forks"] == []  # o summary da fixture não marca look_ahead
    assert len(got[SIX]["top_skill"]) == BT.TOP_N


def test_index_also_lists_runs_missing_from_index(base: Path):
    shutil.copytree(base / "bt30_2026-08-06", base / "bt30_2026-07-06")
    out = view(base).index()
    r = next(r for r in out["runs"] if r["run_id"] == "bt30_2026-07-06")
    assert r["available"] and r["kind"] == "30d" and r["n_portfolios"] == 10


def test_index_empty_dir(tmp_path: Path):
    out = view(tmp_path / "nada").index()
    assert out["runs"] == [] and out["latest"] is None and out["has_history"] is False


def test_index_cache_follows_file_changes(base: Path):
    v = view(base)
    assert len(v.index()["runs"]) == 4
    idx = json.loads((base / "index.json").read_text())
    idx["runs"] = idx["runs"][:1]
    (base / "index.json").write_text(json.dumps(idx))
    import os
    st = (base / "index.json").stat()
    os.utime(base / "index.json", ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
    # os runs em disco que não estão no índice continuam aparecendo (montados dos summaries)
    assert len(v.index()["runs"]) == 4
    assert v.index()["source"] == "index"


def test_run_kind():
    assert BT.run_kind("bt180_x", 30) == "180d"
    assert BT.run_kind("x", 183) == "180d"
    assert BT.run_kind("x", 30) == "30d" and BT.run_kind("x", 31) == "30d" and BT.run_kind("x", None) == "30d"


def test_chart_payload_and_downsample(base: Path):
    v = view(base)
    full = v.chart(SIX)
    assert full and full["run_id"] == SIX and len(full["t"]) == 184
    assert full["benchmarks"]["usdc"][-1] == pytest.approx(1000 * 1.06 ** (183 / 365), abs=0.5)
    small = v.chart(SIX, points=50)
    assert len(small["t"]) == 50 and small["t"][0] == full["t"][0] and small["t"][-1] == full["t"][-1]
    for g in ("benchmarks", "families", "top", "realbot"):
        assert all(len(s) == 50 for k, s in small[g].items() if k != "memes_in_basket")
    assert small["monthly"] == full["monthly"]
    # metadados que não são séries passam intactos
    assert small["benchmarks"]["memes_in_basket"] == ["BONK", "FARTCOIN", "GOAT", "MEW", "POPCAT", "WIF"]
    assert small["normalized_to"] == 1000 and small["start_brt"].startswith("2026-04-06")


def test_chart_sanitizes_nan_and_short_series(base: Path):
    ch = json.loads((base / SIX / "chart.json").read_text())
    ch["top"]["curta"] = [1000, float("nan"), 1001]
    ch["families"]["ruim"] = "não é lista"
    ch["nota"] = "extra"
    (base / SIX / "chart.json").write_text(json.dumps(ch))
    out = view(base).chart(SIX)
    assert out["top"]["curta"][:3] == [1000, None, 1001] and out["top"]["curta"][3] is None
    assert "ruim" not in out["families"] and out["nota"] == "extra"
    json.dumps(out, allow_nan=False)  # a API serializa sem NaN


def test_chart_missing_or_unsafe(base: Path):
    v = view(base)
    assert v.chart("bt30_2026-09-06") is None  # run mensal não tem chart.json
    assert v.chart("nao-existe") is None
    for rid in ["..", "../backtest", "a/b", "", ".x"]:
        assert v.chart(rid) is None
    (base / SIX / "chart.json").write_text("{quebrado")
    assert v.chart(SIX) is None
    (base / SIX / "chart.json").write_text(json.dumps({"sem_t": 1}))
    assert v.chart(SIX) is None


def test_history_markdown(base: Path):
    txt = view(base).history()
    assert txt and txt.startswith("# Histórico")
    (base / "history.md").unlink()
    assert view(base).history() is None
    assert view(base).index()["has_history"] is False


def test_six_month_run_works_with_existing_endpoints(base: Path):
    v = view(base)
    out = v.payload(SIX)
    assert out["available"] and out["summary"]["window"]["days"] == 183
    assert len(out["summary"]["portfolios"]) == 12
    sp = v.sparks(SIX, 30)
    assert len(sp) == 12 and all(math.isfinite(x) for x in sp["poorjev_relaxed"]["v"])
    assert v.equity(SIX, "poorjev_relaxed", 100)
