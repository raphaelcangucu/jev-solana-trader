import json
from dataclasses import replace

from jev_trader.config import EXPERIMENT_WALLET, Config
from jev_trader.decide import ModelAnswer
from jev_trader.loop import run_cycle
from jev_trader.state import neutral_features


def _cfg(tmp_path, *, live: bool) -> Config:
    return Config(
        hot_wallet=EXPERIMENT_WALLET,
        wallet_matches_experiment=True,
        keypair_path=None,
        live_trading=live,
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


def _buy() -> ModelAnswer:
    return ModelAnswer(
        ok=True,
        choice="buy",
        confidence=0.8,
        skip_noul=0.1,
        probabilities={"buy": 0.8, "sell": 0.1, "hold": 0.1},
        source="test",
    )


def test_dry_run_logs_the_decision_and_does_not_swap(monkeypatch, tmp_path):
    features = replace(neutral_features(), slippage_1k=0.0, spread=0.0, px_in=100.0, px_15m=100.0)
    monkeypatch.setattr("jev_trader.loop.fetch_features", lambda cfg: features)
    monkeypatch.setattr("jev_trader.loop.ask_system_one", lambda state, cfg: _buy())
    monkeypatch.setattr(
        "jev_trader.loop.execute_swap",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("swap called")),
    )
    record = run_cycle(_cfg(tmp_path, live=True), dry_run=True)
    assert record["action"] == "buy"
    assert record["reason"] == "execute"
    assert record["dry_run"] is True
    assert record["submitted"] is False
    assert record["wallet"] == EXPERIMENT_WALLET
    assert not any(character.isdigit() for character in record["state"])
    assert (tmp_path / "decisions.jsonl").is_file()
    assert not (tmp_path / "trades.jsonl").exists()
    # Paper: 1 USDT × 0.8 = 0.8 USDT a 100 × (1 + 10 bps) = 100.1.
    assert record["paper"] is True
    assert record["paper_fill"] is True
    assert record["paper_reason"] == "filled"
    assert record["run_id"] == "run1_2026-09-30"
    assert record["paper_usdt"] == round(50.00929 - 0.8, 6)
    assert record["paper_sol"] == round(0.017392206 + 0.007992007, 9)
    trade = json.loads((tmp_path / "paper_trades.jsonl").read_text(encoding="utf-8"))
    assert trade["side"] == "buy"
    assert trade["fill_mode"] == "mark"
    assert trade["fill_px"] == 100.1
    assert trade["in_amount_ui"] == 0.8
    assert trade["decision_t"] == record["t"]
    book = json.loads((tmp_path / "paper_book.json").read_text(encoding="utf-8"))
    assert book["n_trades"] == 1
    assert book["usdt"] == record["paper_usdt"]


def test_live_cycle_appends_a_trade_without_touching_a_keypair(monkeypatch, tmp_path):
    features = replace(neutral_features(), slippage_1k=0.0, spread=0.0, px_in=100.0)
    monkeypatch.setattr("jev_trader.loop.fetch_features", lambda cfg: features)
    monkeypatch.setattr("jev_trader.loop.ask_system_one", lambda state, cfg: _buy())

    def fake_swap(cfg, *, side, confidence):
        assert side == "buy"
        assert confidence == 0.8
        assert cfg.keypair_path is None
        return {"ok": True, "signature": "paper-signature", "side": side, "wallet": cfg.hot_wallet}

    monkeypatch.setattr("jev_trader.loop.execute_swap", fake_swap)
    record = run_cycle(_cfg(tmp_path, live=True), dry_run=False)
    assert record["submitted"] is True
    assert record["signature"] == "paper-signature"
    trade = (tmp_path / "trades.jsonl").read_text(encoding="utf-8")
    assert "paper-signature" in trade
    assert "keypair" not in trade
    # Ao vivo não há livro de papel.
    assert record["paper"] is False
    assert record["paper_fill"] is False
    assert record["paper_sol"] is None and record["paper_usdt"] is None
    assert not (tmp_path / "paper_trades.jsonl").exists()
    assert not (tmp_path / "paper_book.json").exists()


def test_dry_run_hold_keeps_the_book_and_logs_it(monkeypatch, tmp_path):
    features = replace(neutral_features(), slippage_1k=0.0, spread=0.0, px_in=100.0)
    monkeypatch.setattr("jev_trader.loop.fetch_features", lambda cfg: features)
    low = replace(_buy(), confidence=0.3)
    monkeypatch.setattr("jev_trader.loop.ask_system_one", lambda state, cfg: low)
    record = run_cycle(_cfg(tmp_path, live=False), dry_run=True)
    assert record["reason"] == "low_confidence"
    assert record["paper"] is True and record["paper_fill"] is False
    assert record["paper_sol"] == 0.017392206 and record["paper_usdt"] == 50.00929
    assert (tmp_path / "paper_book.json").is_file()
    assert not (tmp_path / "paper_trades.jsonl").exists()


def test_broken_paper_book_does_not_break_the_cycle(monkeypatch, tmp_path):
    features = replace(neutral_features(), slippage_1k=0.0, spread=0.0, px_in=100.0)
    monkeypatch.setattr("jev_trader.loop.fetch_features", lambda cfg: features)
    monkeypatch.setattr("jev_trader.loop.ask_system_one", lambda state, cfg: _buy())
    (tmp_path / "paper_book.json").write_text("{not json", encoding="utf-8")
    record = run_cycle(_cfg(tmp_path, live=False), dry_run=True)
    assert record["action"] == "buy"
    assert record["paper_fill"] is False
    assert record["paper_reason"] == "paper_error"
    assert "paper book" in record["error"]
    assert (tmp_path / "paper_book.json").read_text(encoding="utf-8") == "{not json"


def test_cli_without_subcommand_still_runs_one_dry_cycle(monkeypatch, tmp_path):
    from jev_trader import __main__ as cli

    calls = []
    monkeypatch.setattr(cli, "load_config", lambda: _cfg(tmp_path, live=True))
    monkeypatch.setattr(cli, "run_cycle", lambda cfg, *, dry_run: calls.append(dry_run))
    assert cli.main(["--dry-run", "--once"]) == 0
    assert cli.main(["--once"]) == 0
    assert calls == [True, False]
