"""dashboard/backtest_view.py: leitura da simulação retroativa (data/backtest), segurança de caminho e estado vazio."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "dashboard"))
import backtest_view as BT  # noqa: E402

FIXTURE = LAB / "dashboard" / "fixtures" / "backtest"
RUN = "20261006-0300"


@pytest.fixture()
def base(tmp_path: Path) -> Path:
    b = tmp_path / "backtest"
    shutil.copytree(FIXTURE, b)
    return b


def view(base: Path, **kw) -> BT.BacktestView:
    return BT.BacktestView(lambda: base, **kw)


def test_fixture_matches_contract():
    s = json.loads((FIXTURE / RUN / "summary.json").read_text())
    for k in ("run_id", "generated_brt", "window", "assets", "assumptions", "models", "winner", "families", "portfolios", "realbot"):
        assert k in s
    assert len(s["portfolios"]) == 30
    p = s["portfolios"][0]
    for k in ("name", "family", "asset", "start_value", "end_value", "pnl", "pnl_pct", "vs_bh", "skill", "timing_p", "max_dd_pct",
              "trades", "weeks", "weeks_beat_bh", "verdict", "verdict_reason", "p_bh", "p_usdc"):
        assert k in p
    assert len(p["weeks"]) == 4
    eq = json.loads((FIXTURE / RUN / "equity" / f"{p['name']}.json").read_text())
    assert len(eq["t"]) == len(eq["equity"]) == len(eq["bh"]) <= 1500


def test_empty_state_when_no_backtest(tmp_path: Path):
    v = view(tmp_path / "nada")
    out = v.payload()
    assert out["available"] is False and out["runs"] == [] and "backtest_30d.py" in out["hint"]
    assert v.equity(RUN, "relaxed") is None and v.sparks(RUN) is None and v.report(RUN) is None


def test_payload_latest_with_enrichment_and_derived_fields(base: Path):
    seen = []

    def factory():
        seen.append(1)
        return lambda p: {"catalog": f"cat_{p['name']}", "profile": "IGNORADO", "params_brief": {"min_confidence": 0.35}}

    v = view(base, meta_factory=factory, live_index_fn=lambda: {"relaxed": "relaxed", "WIF_relaxed": "WIF_relaxed"})
    out = v.payload()
    assert out["available"] and out["run_id"] == RUN and out["latest"] == RUN and out["has_report"]
    assert RUN in [r["run_id"] for r in out["runs"]]
    ports = {p["name"]: p for p in out["summary"]["portfolios"]}
    r = ports["relaxed"]
    # metadados acrescentados sem sobrescrever o que o summary já tem
    assert r["catalog"] == "cat_relaxed" and r["profile"] == "relaxed" and r["params_brief"] == {"min_confidence": 0.35}
    assert r["live_name"] == "relaxed"
    assert ports["meme_WIF_relaxed"]["live_name"] == "WIF_relaxed"  # catálogo meme_X ↔ linha X ao vivo
    assert ports["baseline"]["live_name"] is None
    # vs. segurar em %: só segurar valeria end − vs_bh
    bh = r["end_value"] - r["vs_bh"]
    assert r["vs_bh_pct"] == pytest.approx((r["end_value"] / bh - 1) * 100)
    assert r["skill_pct"] == pytest.approx(r["skill"] / r["start_value"] * 100)
    assert {p["verdict"] for p in ports.values()} <= {"vencedora", "perdedora", "inconclusiva"}
    # cache: a segunda leitura não reconstrói
    v.payload()
    assert len(seen) == 1


def test_meta_factory_errors_do_not_break_payload(base: Path):
    def boom():
        raise RuntimeError("x")
    out = view(base, meta_factory=boom, live_index_fn=boom).payload()
    assert out["available"] and len(out["summary"]["portfolios"]) == 30


def test_verdict_normalization():
    assert BT.norm_verdict("inconclusivo") == "inconclusiva"
    assert BT.norm_verdict("Vencedora") == "vencedora"
    assert BT.norm_verdict("loser") == "perdedora"
    assert BT.norm_verdict(None) == "inconclusiva"


def test_latest_falls_back_to_newest_run_and_unknown_run_is_refused(base: Path):
    (base / "latest").write_text("../../etc\n")
    assert BT.latest_run_id(base) == RUN
    old = base / "20260901-0300"
    shutil.copytree(base / RUN, old)
    s = json.loads((old / "summary.json").read_text())
    s["generated_brt"] = "2026-09-01T03:00:00-03:00"
    (old / "summary.json").write_text(json.dumps(s))
    ids = [r["run_id"] for r in BT.list_runs(base)]
    assert ids.index(RUN) < ids.index("20260901-0300")
    v = view(base)
    assert v.payload("20260901-0300")["run_id"] == "20260901-0300"
    bad = v.payload("nao-existe")
    assert bad["available"] is False and bad["latest"] == RUN


@pytest.mark.parametrize("rid", ["..", "../backtest", "a/b", "", ".hidden", "x" * 200, "%2e%2e"])
def test_run_id_validation(base: Path, rid: str):
    assert BT.run_dir(base, rid) is None
    assert view(base).equity(rid, "relaxed") is None
    assert view(base).report(rid) is None


@pytest.mark.parametrize("name", ["../summary", "../../latest", "nao_existe", "relaxed/../baseline", ""])
def test_equity_name_must_be_in_summary(base: Path, name: str):
    assert view(base).equity(RUN, name) is None


def test_equity_name_in_summary_but_file_outside_is_refused(base: Path, tmp_path: Path):
    s = json.loads((base / RUN / "summary.json").read_text())
    s["portfolios"].append(dict(s["portfolios"][0], name="../../segredo"))
    (base / RUN / "summary.json").write_text(json.dumps(s))
    (tmp_path / "segredo.json").write_text(json.dumps({"t": [1, 2], "equity": [1, 2], "bh": [1, 2]}))
    assert BT.equity_file(base, RUN, "../../segredo") is None


def test_equity_and_downsample(base: Path):
    v = view(base)
    full = v.equity(RUN, "relaxed")
    assert full and len(full["t"]) == 120 and full["t"] == sorted(full["t"])
    small = v.equity(RUN, "relaxed", points=50)
    assert len(small["t"]) == 50 and small["t"][0] == full["t"][0] and small["t"][-1] == full["t"][-1]


def test_sparks_are_percent_since_start(base: Path):
    sp = view(base).sparks(RUN, 30)
    assert len(sp) == 30
    s = sp["relaxed"]
    assert len(s["v"]) == 30 and s["v"][0] == 0 and s["h"][0] == 0
    summ = json.loads((base / RUN / "summary.json").read_text())
    r = next(p for p in summ["portfolios"] if p["name"] == "relaxed")
    assert s["v"][-1] == pytest.approx(r["pnl_pct"], abs=0.01)


def test_report_markdown(base: Path):
    txt = view(base).report(RUN)
    assert txt and txt.startswith("# Simulação retroativa")
    (base / RUN / "report.md").unlink()
    assert view(base).report(RUN) is None
    assert view(base).payload()["has_report"] is False


def test_live_meta_fn_uses_universe_then_registry():
    items = [{"name": "WIF_relaxed", "meta": {"catalog": "meme_WIF_relaxed", "profile": "relaxed"}, "parent": None},
             {"name": "relaxed__fork1", "meta": {"catalog": "relaxed__fork1", "params_diff": {"gates": {"min_confidence": 0.3}}},
              "parent": "relaxed", "hyp": None}]
    calls = []
    fn = BT.live_meta_fn(items, {"portfolios": {"h9_novo": {"hyp": "H9", "parent": None}}}, {},
                         row_meta=lambda name, group, e, orig: calls.append((name, group)) or {"catalog": name, "profile": None},
                         params_brief=lambda c: {"c": c})
    m = fn({"name": "meme_WIF_relaxed", "asset": "WIF"})
    assert m["catalog"] == "meme_WIF_relaxed" and m["params_brief"] == {"c": "meme_WIF_relaxed"}
    f = fn({"name": "relaxed__fork1"})
    assert f["parent"] == "relaxed" and f["params_diff"] == {"gates": {"min_confidence": 0.3}}
    n = fn({"name": "h9_novo", "asset": "SOL"})
    assert calls == [("h9_novo", "lab")] and n["hyp"] == "H9" and "profile" not in n
    assert BT.live_index(items) == {"WIF_relaxed": "WIF_relaxed", "meme_WIF_relaxed": "WIF_relaxed", "relaxed__fork1": "relaxed__fork1"}


def test_backtest_dir_env_override(monkeypatch, tmp_path: Path):
    assert BT.backtest_dir(tmp_path) == tmp_path / "data" / "backtest"
    monkeypatch.setenv("PAPER_LAB_BACKTEST_DIR", str(FIXTURE))
    assert BT.backtest_dir(tmp_path) == FIXTURE
