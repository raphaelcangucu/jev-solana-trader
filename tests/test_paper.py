import json
from dataclasses import replace

import pytest

from jev_trader.config import EXPERIMENT_WALLET, Config
from jev_trader.experiment import DEFAULT_EXPERIMENT, ExperimentError, load_experiment
from jev_trader.paper import (
    PaperBook,
    PaperBookError,
    fill_price,
    load_book,
    paper_cycle,
    simulate_fill,
    size_order,
)
from jev_trader.swap import _order_spec


def _cfg(tmp_path, **overrides) -> Config:
    base = Config(
        hot_wallet=EXPERIMENT_WALLET,
        wallet_matches_experiment=True,
        keypair_path=None,
        live_trading=False,
        von_base_url="http://127.0.0.1:9",
        von_model="von-latest",
        von_timeout_s=1.0,
        confidence_min=0.55,
        skip_min=0.55,
        loop_seconds=15.0,
        buy_usdt=1.0,
        sell_sol=0.005,
        max_buy_usdt=5.0,
        max_sell_sol=0.01,
        jupiter_ultra_base="https://lite-api.jup.ag",
        jupiter_quote_base="https://lite-api.jup.ag",
        jupiter_api_key=None,
        rpc_url="http://127.0.0.1:9",
        log_dir=tmp_path,
        paper_cost_bps=10.0,
        experiment_path=tmp_path / "experiment.json",
        criteria_path=tmp_path / "criteria.json",
    )
    return replace(base, **overrides)


def _book(sol=0.017392206, usdt=50.00929) -> PaperBook:
    return PaperBook(run_id=DEFAULT_EXPERIMENT.run_id, sol=sol, usdt=usdt)


def test_size_matches_the_live_order_spec(tmp_path):
    cfg = _cfg(tmp_path, buy_usdt=3.0, sell_sol=0.008)
    amount, nominal, reason = size_order(cfg, side="buy", confidence=0.7, book=_book())
    assert reason == "filled"
    assert amount == pytest.approx(2.1)
    assert int(_order_spec(cfg, side="buy", confidence=0.7)[2]) == round(amount * 1_000_000)
    amount, nominal, reason = size_order(cfg, side="sell", confidence=0.6, book=_book())
    assert amount == pytest.approx(0.0048)
    assert int(_order_spec(cfg, side="sell", confidence=0.6)[2]) == round(amount * 1_000_000_000)


def test_caps_by_max_and_by_available_balance(tmp_path):
    cfg = _cfg(tmp_path, buy_usdt=20.0, max_buy_usdt=5.0, sell_sol=1.0, max_sell_sol=0.01)
    amount, nominal, _ = size_order(cfg, side="buy", confidence=1.0, book=_book())
    assert amount == 5.0 and nominal == 5.0
    amount, _, _ = size_order(cfg, side="sell", confidence=1.0, book=_book())
    assert amount == 0.01
    amount, nominal, reason = size_order(cfg, side="buy", confidence=1.0, book=_book(usdt=2.5))
    assert (amount, nominal, reason) == (2.5, 5.0, "filled")
    amount, _, reason = size_order(cfg, side="sell", confidence=1.0, book=_book(sol=0.004))
    assert (amount, reason) == (0.004, "filled")


def test_insufficient_balance_is_no_fill(tmp_path):
    cfg = _cfg(tmp_path)
    assert size_order(cfg, side="buy", confidence=0.8, book=_book(usdt=0.0))[2] == "insufficient_usdt"
    assert size_order(cfg, side="buy", confidence=0.8, book=_book(usdt=0.005))[0] is None
    assert size_order(cfg, side="sell", confidence=0.8, book=_book(sol=0.00005))[2] == "insufficient_sol"


def test_fill_price_charges_cost_against_the_trader():
    assert fill_price("buy", 100.0, 10) == pytest.approx(100.1)
    assert fill_price("sell", 100.0, 10) == pytest.approx(99.9)
    price, sol = simulate_fill("buy", 1.0, 100.0, 0)
    assert price == 100.0 and sol == 0.01
    price, usdt = simulate_fill("sell", 0.01, 100.0, 10)
    assert usdt == pytest.approx(0.999)


def test_book_persists_across_cycles_and_trades_are_logged(tmp_path):
    cfg = _cfg(tmp_path, paper_cost_bps=0.0)
    first = paper_cycle(cfg, execute=True, side="buy", confidence=1.0, px_in=100.0, t="2026-09-30T01:00:00-03:00")
    assert first.fill and first.book.usdt == pytest.approx(49.00929)
    assert first.book.sol == pytest.approx(0.027392206)
    second = paper_cycle(cfg, execute=True, side="sell", confidence=1.0, px_in=110.0, t="2026-09-30T01:01:00-03:00")
    assert second.fill
    assert second.book.sol == pytest.approx(0.022392206)
    assert second.book.usdt == pytest.approx(49.00929 + 0.55)
    assert second.book.n_trades == 2
    saved = json.loads(cfg.paper_book_path.read_text(encoding="utf-8"))
    assert saved["sol"] == second.book.sol and saved["n_trades"] == 2
    lines = [json.loads(x) for x in cfg.paper_trades_path.read_text(encoding="utf-8").splitlines()]
    assert [x["side"] for x in lines] == ["buy", "sell"]
    assert lines[1]["book_after"] == {"sol": second.book.sol, "usdt": second.book.usdt}
    assert all(x["run_id"] == DEFAULT_EXPERIMENT.run_id for x in lines)


def test_non_executing_cycle_initialises_book_without_trade(tmp_path):
    cfg = _cfg(tmp_path)
    result = paper_cycle(cfg, execute=False, side="hold", confidence=0.2, px_in=100.0, t="t")
    assert result.fill is False and result.reason is None
    assert json.loads(cfg.paper_book_path.read_text(encoding="utf-8"))["usdt"] == 50.00929
    assert not cfg.paper_trades_path.exists()


def test_insufficient_cycle_records_reason_and_keeps_book(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.paper_book_path.write_text(
        json.dumps({"run_id": DEFAULT_EXPERIMENT.run_id, "sol": 0.0, "usdt": 3.0, "n_trades": 4}),
        encoding="utf-8",
    )
    result = paper_cycle(cfg, execute=True, side="sell", confidence=0.9, px_in=100.0, t="t")
    assert (result.fill, result.reason) == (False, "insufficient_sol")
    assert result.book.usdt == 3.0 and result.book.n_trades == 4
    assert not cfg.paper_trades_path.exists()


def test_book_from_another_run_is_refused(tmp_path):
    path = tmp_path / "paper_book.json"
    path.write_text(json.dumps({"run_id": "run0", "sol": 1.0, "usdt": 1.0}), encoding="utf-8")
    with pytest.raises(PaperBookError):
        load_book(path, DEFAULT_EXPERIMENT)


def test_experiment_loader_defaults_and_file(tmp_path):
    assert load_experiment(tmp_path / "missing.json") == DEFAULT_EXPERIMENT
    path = tmp_path / "experiment.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "run9",
                "start_t": "2026-10-01T00:00:00-03:00",
                "book": {"sol": 1, "usdt": 2},
                "ref_sol_usd": 150,
            }
        ),
        encoding="utf-8",
    )
    loaded = load_experiment(path)
    assert (loaded.run_id, loaded.book_sol, loaded.book_usdt, loaded.ref_sol_usd) == ("run9", 1.0, 2.0, 150.0)
    path.write_text(json.dumps({"run_id": "x", "start_t": "not a time", "book": {}}), encoding="utf-8")
    with pytest.raises(ExperimentError):
        load_experiment(path)


def test_repo_experiment_file_matches_the_restart():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1] / "config" / "experiment.json"
    assert load_experiment(repo) == DEFAULT_EXPERIMENT
