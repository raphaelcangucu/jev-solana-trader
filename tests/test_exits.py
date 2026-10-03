"""Saídas mecânicas (TP/SL/trailing), teto de exposição, estado da posição no livro de papel e livros A/B."""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from jev_trader import config as C
from jev_trader.config import EXPERIMENT_WALLET, Config
from jev_trader.decide import ModelAnswer
from jev_trader.exits import (
    ExitParams,
    avg_cost_after_buy,
    cap_buy_usdt,
    check_exit,
    in_cooldown,
    peak_after_buy,
    replay_position,
)
from jev_trader.experiment import DEFAULT_EXPERIMENT
from jev_trader.loop import run_cycle
from jev_trader.paper import PaperBookError, load_book, paper_cycle
from jev_trader.state import neutral_features

ROOT = Path(__file__).resolve().parents[1]
LAB_EXITS = ExitParams(enabled=True, tp=0.025, sl=0.015, trail=0.01, trail_arm=0.01, reentry_cooldown_min=30)
BRT = timezone(timedelta(hours=-3))
T0 = datetime(2026, 10, 3, 12, 0, tzinfo=BRT)


def _t(minutes: float) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def _cfg(tmp_path, **overrides) -> Config:
    base = Config(
        hot_wallet=EXPERIMENT_WALLET,
        wallet_matches_experiment=True,
        keypair_path=None,
        live_trading=False,
        von_base_url="http://127.0.0.1:9",
        von_model="von-latest",
        von_timeout_s=1.0,
        confidence_min=0.35,
        skip_min=0.5,
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
        paper_cost_bps=0.0,
        experiment_path=tmp_path / "experiment.json",
        criteria_path=tmp_path / "criteria.json",
    )
    return replace(base, **overrides)


def _exits_cfg(tmp_path, **overrides) -> Config:
    return _cfg(tmp_path, **{"exits": LAB_EXITS, "max_exposure_frac": 0.5, "paper_book_label": "B", **overrides})


def _trades(cfg: Config) -> list[dict]:
    if not cfg.paper_trades_path.exists():
        return []
    return [json.loads(x) for x in cfg.paper_trades_path.read_text(encoding="utf-8").splitlines()]


# ---------------------------------------------------------------- contas puras


def test_take_profit_stop_loss_and_priority():
    assert check_exit(LAB_EXITS, 100.0, None, 102.51)[0] == "tp"
    assert check_exit(LAB_EXITS, 100.0, None, 102.4)[0] is None
    assert check_exit(LAB_EXITS, 100.0, None, 98.5)[0] == "sl"
    assert check_exit(LAB_EXITS, 100.0, None, 98.6)[0] is None
    # TP vem antes do trailing, mesmo com o trailing armado e disparado.
    assert check_exit(LAB_EXITS, 100.0, 110.0, 103.0)[0] == "tp"
    reason, peak, ret = check_exit(LAB_EXITS, 100.0, 101.0, 100.5)
    assert peak == 101.0 and ret == pytest.approx(0.005)


def test_trailing_arms_then_triggers():
    # Pico +0,9%: não armado, uma queda de 1% do pico não dispara.
    assert check_exit(LAB_EXITS, 100.0, 100.9, 99.85)[0] is None
    # Pico +2%: armado; a 1% abaixo do pico dispara (e não é SL: r = +0,98%).
    reason, peak, _ = check_exit(LAB_EXITS, 100.0, 102.0, 100.98)
    assert (reason, peak) == ("trail", 102.0)
    assert check_exit(LAB_EXITS, 100.0, 102.0, 101.0)[0] is None
    # O pico sobe com o preço do ciclo.
    assert check_exit(LAB_EXITS, 100.0, 101.0, 102.2)[1] == 102.2
    # trail_arm ausente = trail (lab).
    p = replace(LAB_EXITS, trail_arm=None, trail=0.02, tp=None)
    assert check_exit(p, 100.0, 101.9, 99.8)[0] is None
    assert check_exit(p, 100.0, 102.0, 99.9)[0] == "trail"


def test_disabled_or_empty_exits_never_fire():
    assert not ExitParams().active
    assert not ExitParams(enabled=True).active
    assert check_exit(replace(LAB_EXITS, enabled=False), 100.0, None, 50.0)[0] is None


def test_avg_cost_with_multiple_buys():
    # 1 SOL a 100, depois 2 USDT → 0,01 SOL e 3 USDT → 0,02 SOL (a 200 e 150).
    avg = avg_cost_after_buy(0.0, None, 100.0, 1.0, 100.0)
    assert avg == 100.0
    avg = avg_cost_after_buy(1.0, avg, 2.0, 0.01, 200.0)
    assert avg == pytest.approx(102.0 / 1.01)
    avg = avg_cost_after_buy(1.01, avg, 3.0, 0.02, 150.0)
    assert avg == pytest.approx(105.0 / 1.03)
    # Posição em pó: o custo antigo é esquecido.
    assert avg_cost_after_buy(1e-9, 50.0, 1.0, 0.01, 100.0) == pytest.approx(100.0)
    assert peak_after_buy(0.0, 120.0, 100.0) == 100.0
    assert peak_after_buy(1.0, 120.0, 100.0) == 120.0


def test_exposure_cap_shrinks_or_blocks():
    # Livro 50 USDT + 0 SOL, teto 50%: cabe tudo.
    assert cap_buy_usdt(1.0, sol=0.0, usdt=50.0, px=100.0, cap=0.5, min_usdt=0.01) == (1.0, None)
    # 0,24 SOL a 100 (24) + 26 USDT: espaço = 25 − 24 = 1 → compra de 3 encolhe para 1.
    amount, why = cap_buy_usdt(3.0, sol=0.24, usdt=26.0, px=100.0, cap=0.5, min_usdt=0.01)
    assert why is None and amount == pytest.approx(1.0)
    assert cap_buy_usdt(1.0, sol=0.25, usdt=25.0, px=100.0, cap=0.5, min_usdt=0.01) == (None, "max_exposure")
    assert cap_buy_usdt(1.0, sol=0.0, usdt=0.0, px=100.0, cap=0.5, min_usdt=0.01) == (None, "max_exposure")
    assert cap_buy_usdt(7.0, sol=10.0, usdt=1.0, px=100.0, cap=None, min_usdt=0.01) == (7.0, None)


def test_reentry_cooldown_window():
    assert in_cooldown(_t(0), _t(29), 30)
    assert not in_cooldown(_t(0), _t(30), 30)
    assert not in_cooldown(None, _t(1), 30)
    assert not in_cooldown(_t(0), _t(1), 0)


# ---------------------------------------------------------------- livro de papel


def test_paper_exit_sells_whole_book_and_blocks_rebuy(tmp_path):
    cfg = _exits_cfg(tmp_path)
    start = paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=100.0, t=_t(0))
    assert start.book.book == "B" and start.book.start_t == _t(0) and start.book.start_px == 100.0
    assert start.book.avg_cost == 100.0
    bought = paper_cycle(cfg, execute=True, side="buy", confidence=1.0, px_in=100.0, t=_t(1))
    assert bought.fill and bought.book.sol == pytest.approx(0.027392206)
    assert bought.book.avg_cost == pytest.approx(100.0)
    # +1%: nada; o pico sobe e fica gravado.
    up = paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=101.0, t=_t(2))
    assert up.exit_trade is None and up.book.peak_px == 101.0
    assert json.loads(cfg.paper_book_path.read_text())["peak_px"] == 101.0
    # +3%: take profit vende todo o SOL do livro.
    out = paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=103.0, t=_t(3))
    assert out.exit_reason == "tp"
    assert out.book.sol == 0.0 and out.book.usdt == pytest.approx(49.00929 + 0.027392206 * 103, abs=1e-6)
    assert out.book.avg_cost is None and out.book.peak_px is None
    assert out.book.last_exit_t == _t(3) and out.book.n_exits == 1
    trade = _trades(cfg)[-1]
    assert (trade["side"], trade["reason"], trade["book"]) == ("sell", "tp", "B")
    assert trade["in_amount_ui"] == pytest.approx(0.027392206)
    assert trade["avg_cost"] == pytest.approx(100.0) and trade["ret_from_avg"] == pytest.approx(0.03)
    # Compra bloqueada durante 30 min; vender continua sem SOL.
    blocked = paper_cycle(cfg, execute=True, side="buy", confidence=1.0, px_in=103.0, t=_t(20))
    assert (blocked.fill, blocked.reason) == (False, "reentry_cooldown")
    again = paper_cycle(cfg, execute=True, side="buy", confidence=1.0, px_in=103.0, t=_t(34))
    assert again.fill and again.book.avg_cost == pytest.approx(103.0)
    assert [x["reason"] for x in _trades(cfg)] == ["gate", "tp", "gate"]


def test_stop_loss_and_trailing_in_the_book(tmp_path):
    cfg = _exits_cfg(tmp_path)
    paper_cycle(cfg, execute=True, side="buy", confidence=1.0, px_in=100.0, t=_t(0))
    sl = paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=98.4, t=_t(1))
    assert sl.exit_reason == "sl" and sl.book.sol == 0.0

    cfg2 = _exits_cfg(tmp_path / "trail")
    paper_cycle(cfg2, execute=True, side="buy", confidence=1.0, px_in=100.0, t=_t(0))
    for i, px in enumerate([101.0, 102.0, 101.5]):
        r = paper_cycle(cfg2, execute=False, side="hold", confidence=0.0, px_in=px, t=_t(1 + i))
        assert r.exit_trade is None
    tr = paper_cycle(cfg2, execute=False, side="hold", confidence=0.0, px_in=100.95, t=_t(5))
    assert tr.exit_reason == "trail" and tr.exit_trade["peak_px"] == 102.0


def test_partial_exit_keeps_remainder_with_fresh_reference(tmp_path):
    cfg = _exits_cfg(tmp_path, exits=replace(LAB_EXITS, sell_frac=0.5))
    paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=100.0, t=_t(0))
    out = paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=200.0, t=_t(1))
    assert out.exit_reason == "tp"
    assert out.book.sol == pytest.approx(0.017392206 - 0.008696103)
    assert out.book.avg_cost == 200.0 and out.book.peak_px == 200.0
    # O resto só sai com novo movimento a partir do preço da saída.
    assert paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=200.0, t=_t(2)).exit_trade is None


def test_small_position_does_not_exit(tmp_path):
    cfg = _exits_cfg(tmp_path)
    cfg.paper_book_path.write_text(json.dumps({
        "run_id": DEFAULT_EXPERIMENT.run_id, "sol": 0.005, "usdt": 50.0, "book": "B", "start_t": _t(0),
        "start_px": 100.0, "avg_cost": 100.0, "peak_px": 100.0,
    }))
    # 0,005 SOL × 150 = 0,75 US$ < 1 US$: sem saída (lab).
    assert paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=150.0, t=_t(1)).exit_trade is None


def test_exposure_cap_in_the_book(tmp_path):
    cfg = _exits_cfg(tmp_path, buy_usdt=5.0)
    cfg.paper_book_path.write_text(json.dumps({
        "run_id": DEFAULT_EXPERIMENT.run_id, "sol": 0.24, "usdt": 26.0, "book": "B", "start_t": _t(0),
        "start_px": 100.0, "avg_cost": 100.0, "peak_px": 100.0,
    }))
    r = paper_cycle(cfg, execute=True, side="buy", confidence=1.0, px_in=100.0, t=_t(1))
    assert r.fill and r.trade["in_amount_ui"] == pytest.approx(1.0) and r.trade["exposure_capped"] is True
    assert r.trade["capped"] is True and r.trade["exposure_after"] == pytest.approx(0.5)
    blocked = paper_cycle(cfg, execute=True, side="buy", confidence=1.0, px_in=100.0, t=_t(2))
    assert (blocked.fill, blocked.reason) == (False, "max_exposure")
    # Vender continua livre.
    assert paper_cycle(cfg, execute=True, side="sell", confidence=1.0, px_in=100.0, t=_t(3)).fill


def test_gate_sell_keeps_avg_cost_until_dust(tmp_path):
    cfg = _exits_cfg(tmp_path, exits=ExitParams(), max_exposure_frac=None, sell_sol=0.02, max_sell_sol=1.0)
    paper_cycle(cfg, execute=True, side="buy", confidence=1.0, px_in=100.0, t=_t(0))
    part = paper_cycle(cfg, execute=True, side="sell", confidence=0.5, px_in=110.0, t=_t(1))
    assert part.book.sol > 0 and part.book.avg_cost == pytest.approx(100.0)
    gone = paper_cycle(cfg, execute=True, side="sell", confidence=1.0, px_in=110.0, t=_t(2))
    assert gone.book.sol == 0.0 and gone.book.avg_cost is None


def test_old_book_without_position_fields_is_migrated_from_history(tmp_path):
    cfg = _cfg(tmp_path)  # livro A, sem saídas
    cfg.paper_book_path.write_text(json.dumps({
        "run_id": DEFAULT_EXPERIMENT.run_id, "sol": 0.027392206, "usdt": 49.00929, "n_trades": 1,
        "updated_t": "2026-09-30T01:00:00-03:00",
    }))
    cfg.paper_trades_path.write_text(json.dumps({
        "t": "2026-09-30T01:00:00-03:00", "run_id": DEFAULT_EXPERIMENT.run_id, "side": "buy", "px_in": 100.0,
        "fill_px": 100.0, "in_amount_ui": 1.0, "out_amount_ui": 0.01,
        "book_after": {"sol": 0.027392206, "usdt": 49.00929},
    }) + "\n")
    book = load_book(cfg.paper_book_path, DEFAULT_EXPERIMENT, trades_path=cfg.paper_trades_path)
    expected = (0.017392206 * 119.305 + 1.0) / 0.027392206
    assert book.book == "A" and book.start_t == DEFAULT_EXPERIMENT.start_t
    assert book.avg_cost == pytest.approx(expected) and "reconstruído" in book.position_note
    # Um ciclo grava os campos novos (sem mexer nos saldos).
    r = paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=120.0, t=_t(0))
    saved = json.loads(cfg.paper_book_path.read_text())
    assert saved["avg_cost"] == pytest.approx(expected) and saved["sol"] == 0.027392206 and saved["book"] == "A"
    assert r.book.n_trades == 1


def test_old_book_without_history_uses_reference_or_first_price(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.paper_book_path.write_text(json.dumps({"run_id": DEFAULT_EXPERIMENT.run_id, "sol": 0.4, "usdt": 0.0}))
    book = load_book(cfg.paper_book_path, DEFAULT_EXPERIMENT, trades_path=cfg.paper_trades_path)
    assert book.avg_cost == pytest.approx(119.305)  # SOL inicial ao ref_sol_usd, sem trades
    exp = replace(DEFAULT_EXPERIMENT, ref_sol_usd=None)
    cfg.experiment_path.write_text(json.dumps({
        "run_id": exp.run_id, "start_t": exp.start_t, "book": {"sol": exp.book_sol, "usdt": exp.book_usdt},
    }))
    r = paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=130.0, t=_t(0))
    assert r.book.avg_cost == 130.0 and "sem histórico" in r.book.position_note


def test_book_label_mismatch_is_refused(tmp_path):
    cfg = _exits_cfg(tmp_path)
    paper_cycle(cfg, execute=False, side="hold", confidence=0.0, px_in=100.0, t=_t(0))
    with pytest.raises(PaperBookError):
        load_book(cfg.paper_book_path, DEFAULT_EXPERIMENT, label="A")


def test_replay_matches_live_book_state(tmp_path):
    cfg = _exits_cfg(tmp_path)
    for i, (side, px) in enumerate([("buy", 100.0), ("buy", 101.0), ("hold", 104.0), ("buy", 99.0)]):
        last = paper_cycle(cfg, execute=side != "hold", side=side, confidence=1.0, px_in=px, t=_t(40 * i))
    state = replay_position(_trades(cfg), start_sol=DEFAULT_EXPERIMENT.book_sol, start_cost=100.0)
    assert state["avg_cost"] == pytest.approx(last.book.avg_cost) and state["n_exits"] == 1
    assert state["last_exit_t"] == _t(80)


# ---------------------------------------------------------------- loop (dry-run e ao vivo)


def _answer(choice: str = "buy") -> ModelAnswer:
    return ModelAnswer(ok=True, choice=choice, confidence=0.8, skip_noul=0.1,
                       probabilities={choice: 0.8, "hold": 0.1, "x": 0.1}, source="fake")


def test_loop_dry_run_with_price_sequence(monkeypatch, tmp_path):
    cfg = _exits_cfg(tmp_path)
    steps = iter([(0, 100.0), (1, 101.0), (2, 103.0), (3, 103.0), (40, 103.0)])
    current = {}

    def features(_cfg):
        minute, px = next(steps)
        current["t"] = _t(minute)
        return replace(neutral_features(), slippage_1k=0.0, spread=0.0, px_in=px, px_15m=px)

    monkeypatch.setattr("jev_trader.loop.fetch_features", features)
    monkeypatch.setattr("jev_trader.loop.ask_system_one", lambda state, c: _answer("buy"))
    monkeypatch.setattr("jev_trader.loop._now_iso", lambda: current["t"])
    monkeypatch.setattr("jev_trader.loop.execute_swap", lambda *a, **k: pytest.fail("swap called"))
    records = [run_cycle(cfg, dry_run=True) for _ in range(5)]
    # A saída vem antes do portão no mesmo ciclo: o TP vende e a compra do modelo fica bloqueada 30 min.
    assert [r["paper_reason"] for r in records] == [
        "filled", "filled", "reentry_cooldown", "reentry_cooldown", "filled"]
    assert [r["exit_reason"] for r in records] == [None, None, "tp", None, None]
    assert all(r["book"] == "B" and r["exits_warning"] is None for r in records)
    assert records[2]["paper_sol"] == 0.0 and records[2]["paper_exposure"] == 0.0
    assert records[2]["paper_avg_cost"] is None
    assert records[4]["paper_avg_cost"] == pytest.approx(103.0)
    sides = [(x["side"], x["reason"]) for x in _trades(cfg)]
    assert sides == [("buy", "gate"), ("buy", "gate"), ("sell", "tp"), ("buy", "gate")]


def test_live_path_skips_exits_with_warning(monkeypatch, tmp_path):
    cfg = _exits_cfg(tmp_path, live_trading=True)
    monkeypatch.setattr(
        "jev_trader.loop.fetch_features",
        lambda c: replace(neutral_features(), slippage_1k=0.0, spread=0.0, px_in=50.0),
    )
    monkeypatch.setattr("jev_trader.loop.ask_system_one", lambda state, c: _answer("hold"))
    monkeypatch.setattr("jev_trader.loop.execute_swap", lambda *a, **k: pytest.fail("swap called"))
    record = run_cycle(cfg, dry_run=False)
    assert record["exits_warning"] == "exits e max_exposure_frac só em paper: ignorados ao vivo"
    assert record["exit_reason"] is None and record["paper"] is False
    assert not cfg.paper_book_path.exists() and not cfg.paper_trades_path.exists()
    plain = run_cycle(_cfg(tmp_path / "plain", live_trading=True), dry_run=False)
    assert plain["exits_warning"] is None


# ---------------------------------------------------------------- perfis


ENV_KEYS = ["PARAMS_PATH", "PARAMS_PROFILE", "LIVE_TRADING", "PAPER_BOOK", *C.PARAM_ENV.values()]


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PARAMS_PATH", str(ROOT / "config" / "params.json"))
    return tmp_path / "no.env"


def test_relaxed_exits_paper_profile(clean_env, monkeypatch):
    monkeypatch.setenv("PARAMS_PROFILE", "relaxed_exits_paper")
    monkeypatch.setenv("PAPER_BOOK", "B")
    cfg = C.load_config(clean_env)
    assert cfg.params_profile == "relaxed_exits_paper" and cfg.params_errors == ()
    assert (cfg.confidence_min, cfg.skip_min, cfg.prob_margin_min) == (0.35, 0.5, 0.2)
    assert cfg.max_exposure_frac == 0.5 and cfg.paper_book_label == "B"
    assert cfg.exits == ExitParams(enabled=True, tp=0.025, sl=0.015, trail=0.01, trail_arm=0.01,
                                   reentry_cooldown_min=30.0, sell_frac=1.0)
    # Só paper: com LIVE_TRADING=1 cai no article, sem saídas nem teto.
    monkeypatch.setenv("LIVE_TRADING", "1")
    live = C.load_config(clean_env)
    assert live.params_profile == "article" and not live.exits.active and live.max_exposure_frac is None


def test_relaxed_paper_is_unchanged(clean_env):
    cfg = C.load_config(clean_env)
    assert cfg.params_profile == "relaxed_paper" and cfg.paper_book_label == "A"
    assert cfg.max_exposure_frac is None and not cfg.exits.active and cfg.exits.reentry_cooldown_min == 30.0


def test_exposure_env_and_bad_exits_values(clean_env, monkeypatch, tmp_path):
    monkeypatch.setenv("MAX_EXPOSURE_FRAC", "0.3")
    assert C.load_config(clean_env).max_exposure_frac == 0.3
    monkeypatch.setenv("MAX_EXPOSURE_FRAC", "2")
    assert C.load_config(clean_env).max_exposure_frac is None
    monkeypatch.setenv("PAPER_BOOK", " b/../x ")
    assert C.load_config(clean_env).paper_book_label == "bx"
    p = tmp_path / "params.json"
    for bad in ({"enabled": "yes"}, {"tp": 5}, {"tpp": 0.1}, {"sell_frac": 0}):
        p.write_text(json.dumps({"profiles": {"x": {"exits": bad}}}))
        values, used, errors = C.load_params(p, "x")
        assert used == "article" and errors and values["exits"] == C.ARTICLE_PARAMS["exits"]
    p.write_text(json.dumps({"defaults": {"exits": {"tp": 0.02, "reentry_cooldown_min": 10}},
                             "profiles": {"x": {"exits": {"enabled": True, "tp": None}}}}))
    values, used, errors = C.load_params(p, "x")
    assert errors == [] and values["exits"] == {"enabled": True, "tp": None, "reentry_cooldown_min": 10.0,
                                                "sell_frac": 1.0}
