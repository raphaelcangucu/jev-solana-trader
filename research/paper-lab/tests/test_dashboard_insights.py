"""dashboard/insights.py: identidade das linhas, habilidade sem beta, sparklines, dia do experimento e placar do bot real."""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "dashboard"))
import insights as INS  # noqa: E402

REPO_SRC = LAB.parents[1] / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))


def test_row_meta_maps_meme_von_to_catalog_name():
    orig = {"meme_WIF_relaxed": {"profile": "relaxed", "test_type": "model_gated", "source": "meme_WIF_relaxed"},
            "WIF_poorjev_baseline": {"profile": "baseline", "test_type": "model_gated"}}
    m = INS.row_meta("WIF_relaxed", "meme", None, orig)
    assert m["catalog"] == "meme_WIF_relaxed" and m["profile"] == "relaxed" and m["test_type"] == "model_gated"
    assert INS.row_meta("WIF_poorjev_baseline", "meme", None, orig)["catalog"] == "WIF_poorjev_baseline"


def test_row_meta_lab_entry_gets_test_type_from_hypothesis():
    e = {"hyp": "H1", "profile": "relaxed", "source": "FARTCOIN_poorjev_relaxed", "params_diff": {}}
    m = INS.row_meta("h1_exits_FARTCOIN_poorjev_relaxed", "lab", e, {})
    assert m["test_type"] == "lab_h1_exits" and m["params_diff"] is None
    fork = {"hyp": None, "test_type": "model_gated", "parent": "relaxed", "params_diff": {"gates": {"min_confidence": 0.3}}}
    assert INS.row_meta("relaxed__fork1", "lab", fork, {})["params_diff"] == {"gates": {"min_confidence": 0.3}}


def test_skill_fields_keeps_finite_numbers_and_adds_pct():
    s = {"start_value": 1000.0, "ex_exposure": 25.0, "timing_p": float("nan"), "trades": 7.0, "buys": 4, "sells": 3,
         "exposure_pct": 50.0, "static_usd": True}
    f = INS.skill_fields(s)
    assert f["ex_exposure_pct"] == pytest.approx(2.5)
    assert f["timing_p"] is None and f["static_usd"] is None
    assert f["trades"] == 7 and isinstance(f["trades"], int)


def test_skill_cache_computes_once_then_serves_cached():
    calls = []
    c = INS.SkillCache(compute=lambda: calls.append(1) or {"a": {"ex_exposure": 1.0}}, ttl=60, first_wait=2)
    assert c.get() == {"a": {"ex_exposure": 1.0}}
    assert c.get() == {"a": {"ex_exposure": 1.0}}
    assert len(calls) == 1 and c.status()["error"] is None


def test_skill_cache_survives_compute_errors():
    def boom():
        raise RuntimeError("x")
    c = INS.SkillCache(compute=boom, ttl=60, first_wait=2)
    assert c.get() == {}
    assert "RuntimeError" in c.status()["error"]


def test_spark_series_is_percent_since_start_and_downsampled():
    rows = [{"ts": 1000 + i, "equity": 1000 + i, "bh_equity": 1000 - i} for i in range(101)]
    sp = INS.spark_series(rows, n=11)
    assert len(sp["t"]) == 11 and sp["t"][0] == 1000 and sp["t"][-1] == 1100
    assert sp["v"][0] == 0 and sp["v"][-1] == pytest.approx(10.0)
    assert sp["h"][-1] == pytest.approx(-10.0)
    assert INS.spark_series([], 10) is None


def test_experiment_info_counts_days_from_first_start():
    t0 = 1_000_000.0
    e = INS.experiment_info([t0 + 3600, t0, None], now_ts=t0 + 1.5 * 86400)
    assert e["day"] == 2 and e["days_total"] == 30 and e["first_verdict_day"] == 21
    assert e["first_verdict_ts"] == t0 + 21 * 86400
    assert INS.experiment_info([], now_ts=t0)["day"] is None
    assert INS.experiment_info([t0], now_ts=t0 + 90 * 86400)["day"] == 30


def test_build_real_board_series_and_composition():
    from jev_trader import score as S
    from jev_trader.experiment import Experiment
    from jev_trader.records import parse_t
    brt = timezone(timedelta(hours=-3))
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=brt)
    exp = Experiment(run_id="r1", start_t=t0.isoformat(), wallet="w", slot=None, book_sol=0.1, book_usdt=10.0,
                     ref_sol_usd=100.0, ref_source="test", mode="paper")
    dec = [{"t": (t0 + timedelta(minutes=i)).isoformat(), "run_id": "r1", "px_in": 100.0 + i, "paper_sol": 0.1,
            "paper_usdt": 10.0, "action": "hold", "conf": 0.3, "reason": "low_confidence"} for i in range(30)]
    trades = [{"t": (t0 + timedelta(minutes=1)).isoformat(), "run_id": "r1", "side": "buy", "px_in": 101.0}]
    b = INS.build_real_board(dec, trades, exp, S, parse_t, points=10)
    assert len(b["series"]["rows"]) == 10 and b["series"]["cols"][:3] == ["ts", "paper_usd", "hold_usd"]
    assert b["series"]["rows"][-1][1] == pytest.approx(0.1 * 129 + 10)
    assert b["recent_decisions"][0]["px"] == 129.0
    assert b["composition"]["sol_frac"] == pytest.approx(12.9 / 22.9)
    assert "detail" not in b["hit_rate"] and b["trades"]["buy"] == 1


def test_real_bot_board_unavailable_without_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_TRADER_ROOT", str(tmp_path))
    INS._rb_cache.update(key=None, val=None)
    assert INS.real_bot_board()["available"] is False


def test_params_brief_for_known_and_unknown_portfolios():
    b = INS.params_brief("relaxed")
    assert b is not None and b["min_confidence"] is not None and b["exits"] is None
    h1 = INS.params_brief("h1_exits_von_relaxed")
    assert h1 is not None and h1["exits"] and h1["exits"]["tp"] > 0
    unk = INS.params_brief("nao_existe_xyz")
    assert unk is None or unk["errors"] >= 1


def test_restarts_since_counts_recent_starts(tmp_path):
    log = tmp_path / "supervisor.log"
    log.write_text("2026-10-01T10:00:00-03:00 starting sol\n2026-10-02T10:00:00-03:00 starting sol\n"
                   "2026-10-02T11:00:00-03:00 starting meme\nlixo\n")
    t0 = datetime.fromisoformat("2026-10-02T00:00:00-03:00").timestamp()
    assert INS.restarts_since(log, t0) == {"sol": 1, "meme": 1}
    assert INS.restarts_since(tmp_path / "nao_existe.log", t0) == {}


def test_health_extras_shape():
    INS._hx_cache.update(ts=0.0, val=None)
    hx = INS.health_extras()
    assert "disk" in hx and "restarts_24h" in hx and "fills_24h" in hx


def test_tunnel_expected_respects_disable_flag_and_binary(tmp_path):
    none = lambda _n: None
    assert INS.tunnel_expected(tmp_path, env={"DISABLE_TUNNEL": "1"}, which=lambda _n: "/usr/bin/cloudflared") is False
    assert INS.tunnel_expected(tmp_path, env={}, which=none) is False
    assert INS.tunnel_expected(tmp_path, env={}, which=lambda _n: "/usr/bin/cloudflared") is True
    (tmp_path / "dashboard").mkdir()
    (tmp_path / "dashboard" / "cloudflared").write_text("")
    assert INS.tunnel_expected(tmp_path, env={"DISABLE_TUNNEL": "0"}, which=none) is True
