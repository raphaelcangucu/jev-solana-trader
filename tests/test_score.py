import json
from dataclasses import replace

import pytest

from jev_trader.experiment import DEFAULT_EXPERIMENT
from jev_trader.records import parse_t
from jev_trader.score import build_timeline, forward_return, max_drawdown, render_table, scoreboard

EXP = replace(
    DEFAULT_EXPERIMENT,
    run_id="runT",
    start_t="2026-09-30T00:00:00-03:00",
    book_sol=0.02,
    book_usdt=50.0,
    ref_sol_usd=105.0,
)


def _d(clock, px, sol, usdt, **extra):
    row = {"t": f"2026-09-30T{clock}-03:00", "px_in": px, "paper_sol": sol, "paper_usdt": usdt, "run_id": "runT"}
    row.update(extra)
    return row


def _trade(clock, side, px):
    t = f"2026-09-30T{clock}-03:00"
    return {"t": t, "decision_t": t, "run_id": "runT", "side": side, "px_in": px}


# Equity (sol × px + usdt): 52, 52, 52.3, 52.15, 51.7, 51.8, 51.9.
DECISIONS = [
    {"t": "2026-09-29T23:00:00-03:00", "px_in": 50.0, "paper_sol": 9.0, "paper_usdt": 9.0},
    _d("00:00:00", 100.0, 0.02, 50.0),
    _d("00:01:00", 100.0, 0.03, 49.0),
    _d("00:10:00", 110.0, 0.03, 49.0),
    _d("00:16:00", 105.0, 0.03, 49.0),
    _d("00:20:00", 90.0, 0.02, 49.9),
    _d("00:36:00", 95.0, 0.02, 49.9),
    _d("00:40:00", 100.0, 0.03, 48.9),
    _d("00:41:00", 1.0, 5.0, 5.0, run_id="other_run"),
]
TRADES = [
    _trade("00:01:00", "buy", 100.0),
    _trade("00:20:00", "sell", 90.0),
    _trade("00:40:00", "buy", 100.0),
]


def test_scoreboard_hand_checked_numbers():
    board = scoreboard(DECISIONS, TRADES, EXP)
    assert board["n_decisions"] == 7
    assert board["last_px"] == 100.0
    assert board["paper_book"] == {"sol": 0.03, "usdt": 48.9}
    hold = board["pnl_vs_hold"]
    assert hold["paper_value_usd"] == pytest.approx(51.9)
    assert hold["base_value_usd"] == pytest.approx(52.0)
    assert hold["usd"] == pytest.approx(-0.1)
    assert hold["pct"] == pytest.approx(-0.1923, abs=1e-4)
    start = board["pnl_vs_start"]
    assert start["base_value_usd"] == pytest.approx(52.1)
    assert start["usd"] == pytest.approx(-0.2)
    assert start["pct"] == pytest.approx(-0.3839, abs=1e-4)
    hits = board["hit_rate"]
    assert (hits["hits"], hits["misses"], hits["resolved"], hits["unresolved"]) == (1, 1, 2, 1)
    assert hits["rate"] == 0.5
    assert [row["status"] for row in hits["detail"]] == ["hit", "miss", "unresolved"]
    assert hits["detail"][0]["t_later"] == "2026-09-30T00:16:00-03:00"
    assert hits["detail"][1]["t_later"] == "2026-09-30T00:36:00-03:00"
    dd = board["drawdown"]
    assert dd["usd"] == pytest.approx(0.6)
    assert dd["pct"] == pytest.approx(1.1472, abs=1e-4)
    assert dd["peak_t"] == "2026-09-30T00:10:00-03:00"
    assert dd["trough_t"] == "2026-09-30T00:20:00-03:00"
    assert board["trades"] == {"total": 3, "buy": 2, "sell": 1}


def test_since_limits_hit_rate_drawdown_and_trades_but_not_pnl():
    board = scoreboard(DECISIONS, TRADES, EXP, since=parse_t("2026-09-30T00:15:00-03:00"))
    assert board["n_decisions"] == 4
    assert board["pnl_vs_hold"]["usd"] == pytest.approx(-0.1)
    assert board["drawdown"]["usd"] == pytest.approx(0.45)
    assert board["trades"] == {"total": 2, "buy": 1, "sell": 1}
    assert board["hit_rate"]["misses"] == 1 and board["hit_rate"]["unresolved"] == 1


def test_resolution_window_is_fifteen_to_twenty_minutes():
    timeline = build_timeline(
        [
            {"t": "2026-09-30T01:14:59-03:00", "px_in": 101.0},
            {"t": "2026-09-30T01:21:00-03:00", "px_in": 102.0},
        ]
    )
    t0 = parse_t("2026-09-30T01:00:00-03:00")
    assert forward_return(timeline, t0, 100.0) == (None, None, None)
    exact = build_timeline([{"t": "2026-09-30T01:20:00-03:00", "px_in": 110.0}])
    ret, later, _ = forward_return(exact, t0, 100.0)
    assert later == 110.0 and ret == pytest.approx(0.1)


def test_drawdown_edges():
    assert max_drawdown([])["usd"] is None
    rising = max_drawdown([("a", 1.0), ("b", 2.0), ("c", 3.0)])
    assert rising["usd"] == 0.0 and rising["points"] == 3


def test_empty_logs_fall_back_to_start_book():
    board = scoreboard([], [], EXP)
    assert board["paper_book"] == {"sol": 0.02, "usdt": 50.0}
    assert board["pnl_vs_hold"]["usd"] is None
    assert board["hit_rate"]["rate"] is None
    text = render_table(board)
    assert "Placar do livro de papel" in text and "—" in text


def test_score_cli_json_and_table(monkeypatch, tmp_path, capsys):
    from jev_trader import __main__ as cli
    from test_paper import _cfg

    (tmp_path / "experiment.json").write_text(
        json.dumps(
            {
                "run_id": "runT",
                "start_t": EXP.start_t,
                "book": {"sol": 0.02, "usdt": 50.0},
                "ref_sol_usd": 105.0,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "decisions.jsonl").write_text("\n".join(json.dumps(d) for d in DECISIONS) + "\n", encoding="utf-8")
    (tmp_path / "paper_trades.jsonl").write_text("\n".join(json.dumps(t) for t in TRADES) + "\n", encoding="utf-8")
    monkeypatch.setattr(cli, "load_config", lambda: _cfg(tmp_path))
    assert cli.main(["score", "--json"]) == 0
    board = json.loads(capsys.readouterr().out)
    assert board["trades"]["total"] == 3
    assert board["hit_rate"]["rate"] == 0.5
    assert cli.main(["score"]) == 0
    out = capsys.readouterr().out
    assert "Hit rate" in out and "50.0%" in out
    assert cli.main(["score", "--since", "garbage"]) == 2
