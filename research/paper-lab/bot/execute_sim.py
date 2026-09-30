"""Simulated fills via Jupiter quotes. NEVER signs or sends transactions."""
from __future__ import annotations
import json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any

USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOL = "So11111111111111111111111111111111111111112"
BRT = timezone(timedelta(hours=-3))

def simulate_trade(
    side: str, portfolio, market, gates_cfg: dict, fees_cfg: dict,
    trades_log: Path, decision_id: str, price_mark: float,
    *, token_mint: str | None = None, token_decimals: int | None = None,
) -> dict[str, Any] | None:
    assert side in ("buy", "sell")
    data = portfolio.data
    extra_bps = float(fees_cfg.get("extra_slippage_bps", 5))
    net_fee_sol = float(fees_cfg.get("assumed_network_fee_sol", 5e-6))
    sol_usd = float(fees_cfg.get("sol_usd", price_mark if token_mint is None else 115.0))
    net_fee_usdt = net_fee_sol * sol_usd
    slip = 50 if token_mint is None else 100

    if token_mint is None:
        if side == "buy":
            usdt_in = float(data["usdt"]) * float(gates_cfg["buy_fraction_usdt"])
            if usdt_in < float(gates_cfg["min_usdt_trade"]): return None
            quote = market.quote_swap(input_mint=USDT, output_mint=SOL, amount_in=usdt_in, in_decimals=6, slippage_bps=slip)
            out = float(quote["outAmount"]) / 1e9
            out_net = max(0.0, out - out * (extra_bps/10000.0) - net_fee_sol)
            fee = usdt_in * (extra_bps/10000.0) + net_fee_usdt
            data["usdt"] -= usdt_in; data["sol"] = float(data["sol"]) + out_net
            data["fees_paid_usdt"] = float(data["fees_paid_usdt"]) + fee
            data["fees_paid_sol"] = float(data.get("fees_paid_sol", 0)) + net_fee_sol
            fill = {"side":"buy","usdt_in":usdt_in,"asset_out_gross":out,"asset_out_net":out_net,"fee_usdt_est":fee}
            trade_pnl = 0.0
        else:
            sol_in = float(data["sol"])
            if sol_in < float(gates_cfg["min_sol_trade"]): return None
            to_swap = max(0.0, sol_in - net_fee_sol)
            if to_swap < float(gates_cfg["min_sol_trade"]): return None
            quote = market.quote_swap(input_mint=SOL, output_mint=USDT, amount_in=to_swap, in_decimals=9, slippage_bps=slip)
            out = float(quote["outAmount"]) / 1e6
            out_net = max(0.0, out - out * (extra_bps/10000.0))
            fee = out * (extra_bps/10000.0) + net_fee_usdt
            trade_pnl = out_net - to_swap * price_mark
            data["sol"] = 0.0; data["usdt"] = float(data["usdt"]) + out_net
            data["fees_paid_usdt"] = float(data["fees_paid_usdt"]) + fee
            data["fees_paid_sol"] = float(data.get("fees_paid_sol", 0)) + net_fee_sol
            data["realized_pnl_usdt"] = float(data["realized_pnl_usdt"]) + trade_pnl
            fill = {"side":"sell","asset_in":to_swap,"usdt_out_gross":out,"usdt_out_net":out_net,"fee_usdt_est":fee,"approx_pnl_usdt":trade_pnl}
    else:
        dec = int(token_decimals or 6)
        data.setdefault("token", 0.0)
        if side == "buy":
            usdt_in = float(data["usdt"]) * float(gates_cfg["buy_fraction_usdt"])
            if usdt_in < float(gates_cfg["min_usdt_trade"]): return None
            usdt_swap = max(0.0, usdt_in - net_fee_usdt)
            quote = market.quote_swap(input_mint=USDT, output_mint=token_mint, amount_in=usdt_swap, in_decimals=6, slippage_bps=slip)
            out = float(quote["outAmount"]) / (10 ** dec)
            out_net = max(0.0, out - out * (extra_bps/10000.0))
            fee = usdt_in * (extra_bps/10000.0) + net_fee_usdt
            data["usdt"] -= usdt_in; data["token"] = float(data["token"]) + out_net
            data["fees_paid_usdt"] = float(data["fees_paid_usdt"]) + fee
            fill = {"side":"buy","usdt_in":usdt_in,"asset_out_gross":out,"asset_out_net":out_net,"fee_usdt_est":fee,"mint":token_mint}
            trade_pnl = 0.0
        else:
            tok_in = float(data["token"])
            if tok_in * price_mark < float(gates_cfg["min_usdt_trade"]): return None
            quote = market.quote_swap(input_mint=token_mint, output_mint=USDT, amount_in=tok_in, in_decimals=dec, slippage_bps=slip)
            out = float(quote["outAmount"]) / 1e6
            out_net = max(0.0, out - out * (extra_bps/10000.0) - net_fee_usdt)
            fee = out * (extra_bps/10000.0) + net_fee_usdt
            trade_pnl = out_net - tok_in * price_mark
            data["token"] = 0.0; data["usdt"] = float(data["usdt"]) + out_net
            data["fees_paid_usdt"] = float(data["fees_paid_usdt"]) + fee
            data["realized_pnl_usdt"] = float(data["realized_pnl_usdt"]) + trade_pnl
            fill = {"side":"sell","asset_in":tok_in,"usdt_out_gross":out,"usdt_out_net":out_net,"fee_usdt_est":fee,"approx_pnl_usdt":trade_pnl,"mint":token_mint}

    now = time.time()
    data["trade_count"] = int(data["trade_count"]) + 1
    data["last_trade_ts"] = now
    stamps = list(data.get("trade_timestamps") or [])
    stamps.append(now)
    data["trade_timestamps"] = stamps[-100:]
    data["position"] = portfolio.position_word()
    portfolio.update_mood(trade_pnl if side == "sell" else 0.0)
    portfolio.save()

    row = {
        "ts": now, "ts_brt": datetime.fromtimestamp(now, tz=BRT).isoformat(),
        "portfolio": portfolio.name, "decision_id": decision_id, "side": side,
        "price_mark": price_mark, "fill": fill,
        "quote": {
            "inAmount": quote.get("inAmount"), "outAmount": quote.get("outAmount"),
            "priceImpactPct": quote.get("priceImpactPct"), "slippageBps": quote.get("slippageBps"),
            "routeLabels": [r.get("swapInfo", {}).get("label") for r in (quote.get("routePlan") or [])],
            "swapUsdValue": quote.get("swapUsdValue"), "contextSlot": quote.get("contextSlot"),
        },
        "portfolio_after": {
            "sol": data.get("sol"), "token": data.get("token"), "usdt": data["usdt"],
            "equity_usd": portfolio.equity_usd(price_mark),
        },
        "paper_only": True, "signed": False, "sent": False,
    }
    trades_log.parent.mkdir(parents=True, exist_ok=True)
    with open(trades_log, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row
