"""Placar por livro (A/B): início do livro B, saídas por motivo, custo médio, exposição e `score --log-dir`."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from jev_trader.config import EXPERIMENT_WALLET, Config
from jev_trader.experiment import DEFAULT_EXPERIMENT
from jev_trader.score import experiment_for_book, render_table, scoreboard

BRT = timezone(timedelta(hours=-3))
B_START = datetime(2026, 10, 3, 12, 0, tzinfo=BRT)


def _t(minutes: float) -> str:
    return (B_START + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def _book_b(**extra) -> dict:
    return {"run_id": DEFAULT_EXPERIMENT.run_id, "book": "B", "start_t": _t(0), "start_px": 120.0,
            "sol": 0.0, "usdt": 52.0, "avg_cost": None, "peak_px": None, "last_exit_t": _t(10), **extra}


def test_experiment_for_book_uses_b_start_and_price():
    exp = experiment_for_book(DEFAULT_EXPERIMENT, _book_b())
    assert exp.start_t == _t(0) and exp.ref_sol_usd == 120.0 and "livro B" in exp.ref_source
    assert (exp.book_sol, exp.book_usdt, exp.run_id) == (DEFAULT_EXPERIMENT.book_sol, DEFAULT_EXPERIMENT.book_usdt,
                                                          DEFAULT_EXPERIMENT.run_id)
    # Livro A (início = experimento) ou sem livro: experimento intacto.
    a = {"book": "A", "start_t": DEFAULT_EXPERIMENT.start_t, "start_px": 119.305}
    assert experiment_for_book(DEFAULT_EXPERIMENT, a) == DEFAULT_EXPERIMENT
    assert experiment_for_book(DEFAULT_EXPERIMENT, None) == DEFAULT_EXPERIMENT


def _b_logs():
    decisions = [
        # Antes do início do B (de outro livro, se misturado): fora.
        {"t": _t(-60), "run_id": DEFAULT_EXPERIMENT.run_id, "px_in": 100.0, "paper_sol": 9.0, "paper_usdt": 0.0},
        {"t": _t(0), "run_id": DEFAULT_EXPERIMENT.run_id, "px_in": 120.0, "paper_sol": DEFAULT_EXPERIMENT.book_sol,
         "paper_usdt": DEFAULT_EXPERIMENT.book_usdt, "params_profile": "relaxed_exits_paper", "book": "B"},
        {"t": _t(10), "run_id": DEFAULT_EXPERIMENT.run_id, "px_in": 123.0, "paper_sol": 0.0, "paper_usdt": 52.0,
         "params_profile": "relaxed_exits_paper", "book": "B", "exit_reason": "tp"},
    ]
    trades = [
        {"t": _t(1), "run_id": DEFAULT_EXPERIMENT.run_id, "side": "buy", "reason": "gate", "px_in": 120.0,
         "fill_px": 120.0, "in_amount_ui": 1.0, "out_amount_ui": 0.008333333},
        {"t": _t(10), "run_id": DEFAULT_EXPERIMENT.run_id, "side": "sell", "reason": "tp", "px_in": 123.0,
         "fill_px": 123.0, "in_amount_ui": 0.025725539, "out_amount_ui": 3.16424,
         "book_after": {"sol": 0.0, "usdt": 52.0}},
    ]
    return decisions, trades


def test_scoreboard_for_book_b():
    decisions, trades = _b_logs()
    board = scoreboard(decisions, trades, DEFAULT_EXPERIMENT, book=_book_b())
    assert board["book"] == "B" and board["params_profile"] == "relaxed_exits_paper"
    assert board["start_t"] == _t(0) and board["n_decisions"] == 2
    assert board["pnl_vs_start"]["ref_sol_usd"] == 120.0
    base = DEFAULT_EXPERIMENT.book_sol * 123.0 + DEFAULT_EXPERIMENT.book_usdt
    assert board["pnl_vs_hold"]["usd"] == pytest.approx(52.0 - base, abs=1e-6)
    ex = board["exits"]
    assert ex["total"] == 1 and ex["by_reason"] == {"tp": 1, "sl": 0, "trail": 0}
    assert ex["avg_cost"] is None and ex["exposure"] == 0.0 and ex["last_exit_t"] == _t(10)
    assert board["trades"] == {"total": 2, "buy": 1, "sell": 1}
    text = render_table(board)
    assert "livro de papel B (perfil relaxed_exits_paper)" in text and "tp 1, sl 0, trail 0" in text


def test_scoreboard_book_a_without_position_fields_replays_trades():
    trades = [{"t": "2026-09-30T01:00:00-03:00", "run_id": DEFAULT_EXPERIMENT.run_id, "side": "buy", "px_in": 100.0,
               "fill_px": 100.0, "in_amount_ui": 1.0, "out_amount_ui": 0.01,
               "book_after": {"sol": 0.027392206, "usdt": 49.00929}}]
    decisions = [{"t": "2026-09-30T01:00:00-03:00", "px_in": 100.0, "paper_sol": 0.027392206, "paper_usdt": 49.00929}]
    old = {"run_id": DEFAULT_EXPERIMENT.run_id, "sol": 0.027392206, "usdt": 49.00929}
    board = scoreboard(decisions, trades, DEFAULT_EXPERIMENT, book=old)
    assert board["book"] == "A"
    assert board["exits"]["avg_cost"] == pytest.approx((0.017392206 * 119.305 + 1.0) / 0.027392206, abs=1e-6)
    assert board["exits"]["exposure"] == pytest.approx(2.7392206 / (2.7392206 + 49.00929), abs=1e-6)
    # Sem livro, o placar continua o de sempre (A).
    assert scoreboard(decisions, trades, DEFAULT_EXPERIMENT)["start_t"] == DEFAULT_EXPERIMENT.start_t


def _cfg(tmp_path) -> Config:
    return Config(
        hot_wallet=EXPERIMENT_WALLET, wallet_matches_experiment=True, keypair_path=None, live_trading=False,
        von_base_url="http://127.0.0.1:9", von_model="von-latest", von_timeout_s=1.0, confidence_min=0.35,
        skip_min=0.5, loop_seconds=15.0, buy_usdt=1.0, sell_sol=0.005, max_buy_usdt=5.0, max_sell_sol=0.01,
        jupiter_ultra_base="x", jupiter_quote_base="x", jupiter_api_key=None, rpc_url="x", log_dir=tmp_path / "logs",
        experiment_path=tmp_path / "experiment.json", criteria_path=tmp_path / "criteria.json",
    )


def test_score_cli_log_dir_scores_book_b(monkeypatch, tmp_path, capsys):
    from jev_trader import __main__ as cli

    b_dir = tmp_path / "logs" / "paper_b"
    b_dir.mkdir(parents=True)
    decisions, trades = _b_logs()
    (b_dir / "decisions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in decisions))
    (b_dir / "paper_trades.jsonl").write_text("".join(json.dumps(r) + "\n" for r in trades))
    (b_dir / "paper_book.json").write_text(json.dumps(_book_b()))
    monkeypatch.setattr(cli, "load_config", lambda: _cfg(tmp_path))
    assert cli.main(["score", "--json", "--log-dir", str(b_dir)]) == 0
    board = json.loads(capsys.readouterr().out)
    assert board["book"] == "B" and board["start_t"] == _t(0) and board["exits"]["by_reason"]["tp"] == 1
    # Sem --log-dir: a pasta da configuração (livro A vazio).
    assert cli.main(["score", "--json"]) == 0
    a = json.loads(capsys.readouterr().out)
    assert a["book"] == "A" and a["start_t"] == DEFAULT_EXPERIMENT.start_t and a["n_decisions"] == 0


def test_score_cli_uses_log_dir_env(monkeypatch, tmp_path, capsys):
    from jev_trader import __main__ as cli

    b_dir = tmp_path / "b"
    b_dir.mkdir()
    (b_dir / "paper_book.json").write_text(json.dumps(_book_b()))
    for key in ("PARAMS_PROFILE", "PAPER_BOOK", "LIVE_TRADING"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LOG_DIR", str(b_dir))
    monkeypatch.setenv("EXPERIMENT_PATH", str(tmp_path / "missing.json"))
    monkeypatch.chdir(tmp_path)
    assert cli.main(["score", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["book"] == "B"
