"""bot/gates.py (portões fail-closed) e o portão relaxed de bot/lib.py."""
from bot.gates import apply_gates
from bot import lib

NOW = 1_790_000_000.0
G = {"min_confidence": 0.6, "max_skip_noul": 0.5, "cooldown_seconds": 120, "max_trades_per_hour": 8,
     "buy_fraction_usdt": 0.25, "min_usdt_trade": 1.0, "min_sol_trade": 0.001}


def pf(**kw):
    d = {"sol": 1.0, "usdt": 100.0, "last_trade_ts": None, "trade_timestamps": [], "asset_mode": "sol"}
    d.update(kw)
    return d


def test_confident_buy_passes():
    g = apply_gates("buy", 0.7, 0.1, pf(), G, NOW)
    assert g["final_action"] == "buy" and g["gate_reasons"] == [] and not g["blocked_trade"]


def test_low_confidence_fails_closed_to_hold():
    g = apply_gates("buy", 0.38, 0.1, pf(), G, NOW)
    assert g["final_action"] == "hold" and "low_confidence" in g["gate_reasons"] and g["blocked_trade"]


def test_high_skip_holds():
    g = apply_gates("sell", 0.9, 0.5, pf(), G, NOW)
    assert g["final_action"] == "hold" and g["gate_reasons"] == ["skip_noul_high"]


def test_invalid_action_is_hold():
    g = apply_gates("moon", 0.9, 0.0, pf(), G, NOW)
    assert g["final_action"] == "hold" and "invalid_action" in g["gate_reasons"] and not g["blocked_trade"]


def test_cooldown_and_rate_limit():
    assert apply_gates("buy", 0.9, 0.0, pf(last_trade_ts=NOW - 60), G, NOW)["gate_reasons"] == ["cooldown"]
    assert apply_gates("buy", 0.9, 0.0, pf(last_trade_ts=NOW - 121), G, NOW)["final_action"] == "buy"
    stamps = [NOW - 3000 + i for i in range(8)]
    g = apply_gates("buy", 0.9, 0.0, pf(trade_timestamps=stamps), G, NOW)
    assert g["final_action"] == "hold" and g["gate_reasons"] == ["max_trades_hour"]
    old = [NOW - 3700 + i for i in range(8)]  # fora da janela de 1 h
    assert apply_gates("buy", 0.9, 0.0, pf(trade_timestamps=old), G, NOW)["final_action"] == "buy"


def test_balance_gates():
    assert apply_gates("buy", 0.9, 0.0, pf(usdt=3.0), G, NOW)["gate_reasons"] == ["insufficient_usdt"]
    assert apply_gates("sell", 0.9, 0.0, pf(sol=0.0005), G, NOW)["gate_reasons"] == ["insufficient_sol"]
    tok = pf(asset_mode="token", token=10.0)
    assert apply_gates("sell", 0.9, 0.0, tok, G, NOW, price_mark=0.01)["gate_reasons"] == ["insufficient_token"]
    assert apply_gates("sell", 0.9, 0.0, tok, G, NOW, price_mark=1.0)["final_action"] == "sell"


def test_hold_is_never_blocked():
    g = apply_gates("hold", 0.1, 0.9, pf(usdt=0, sol=0), G, NOW)
    assert g["final_action"] == "hold" and not g["blocked_trade"]


def test_live_relaxed_gate_requires_probability_margin():
    rel = dict(G, min_confidence=0.35, min_prob_margin=0.20)
    ok = lib.apply_gates("buy", 0.38, 0.1, pf(), rel, probabilities={"buy": 0.6, "sell": 0.1, "hold": 0.3}, profile="relaxed")
    assert ok["final_action"] == "buy"
    thin = lib.apply_gates("buy", 0.38, 0.1, pf(), rel, probabilities={"buy": 0.45, "sell": 0.1, "hold": 0.45}, profile="relaxed")
    assert thin["final_action"] == "hold" and "low_prob_margin" in thin["gate_reasons"]
    base = lib.apply_gates("buy", 0.38, 0.1, pf(), G, probabilities={"buy": 0.6, "sell": 0.1, "hold": 0.3}, profile="baseline")
    assert base["final_action"] == "hold" and base["gate_reasons"] == ["low_confidence"]
