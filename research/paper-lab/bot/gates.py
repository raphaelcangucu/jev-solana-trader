"""Confidence / skip / cooldown / rate gates. Fail-closed to hold."""
from __future__ import annotations
import time
from typing import Any

def apply_gates(chosen: str, confidence: float, skip_noul: float, portfolio_data: dict,
                gates_cfg: dict, now: float | None = None, *, price_mark: float | None = None) -> dict[str, Any]:
    now = now or time.time()
    reasons: list[str] = []
    final = chosen
    if chosen not in ("buy", "sell", "hold"):
        final = "hold"; reasons.append("invalid_action")
    if confidence < float(gates_cfg["min_confidence"]):
        final = "hold"; reasons.append("low_confidence")
    if skip_noul >= float(gates_cfg["max_skip_noul"]):
        final = "hold"; reasons.append("skip_noul_high")
    last_ts = portfolio_data.get("last_trade_ts")
    if final in ("buy", "sell") and last_ts is not None:
        if now - float(last_ts) < float(gates_cfg["cooldown_seconds"]):
            final = "hold"; reasons.append("cooldown")
    if final in ("buy", "sell"):
        stamps = [float(t) for t in portfolio_data.get("trade_timestamps") or []]
        recent = [t for t in stamps if t >= now - 3600]
        if len(recent) >= int(gates_cfg["max_trades_per_hour"]):
            final = "hold"; reasons.append("max_trades_hour")
    usdt = float(portfolio_data.get("usdt", 0))
    mode = portfolio_data.get("asset_mode", "sol")
    if final == "buy":
        need = float(gates_cfg["min_usdt_trade"])
        frac = float(gates_cfg["buy_fraction_usdt"])
        if usdt * frac < need or usdt < need:
            final = "hold"; reasons.append("insufficient_usdt")
    if final == "sell":
        if mode == "token":
            tok = float(portfolio_data.get("token") or 0)
            notional = tok * float(price_mark or 0)
            if tok <= 0 or notional < float(gates_cfg["min_usdt_trade"]):
                final = "hold"; reasons.append("insufficient_token")
        else:
            if float(portfolio_data.get("sol", 0)) < float(gates_cfg["min_sol_trade"]):
                final = "hold"; reasons.append("insufficient_sol")
    return {
        "final_action": final,
        "gate_reasons": reasons,
        "blocked_trade": chosen in ("buy", "sell") and final == "hold",
        "gated": final != chosen or bool(reasons),
    }
