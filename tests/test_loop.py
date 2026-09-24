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
