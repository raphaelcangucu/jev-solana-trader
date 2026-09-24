"""Estado de mercado em doze adjetivos. A aritmética fica neste módulo."""

from __future__ import annotations

import math
from dataclasses import dataclass

from jev_trader.config import USDT_MINT, WSOL_MINT, Config

# Baseline de "rede quieta" para a taxa de prioridade (microlamports por CU).
QUIET_MICRO_LAMPORTS = 1000.0
SLIPPAGE_THIN = 0.006
FEE_BOT_WAR = 2.5
PUMP_RETURN = 0.02
DUMP_RETURN = -0.05
FADE_RETURN = -0.02
VOL_VIOLENT = 0.008
SPREAD_WIDE = 0.002

ALLOWED_WORDS = frozenset(
    {
        "thin",
        "deep",
        "bot_war",
        "quiet",
        "pumping",
        "flat",
        "fading",
        "dumping",
        "violent",
        "calm",
        "green",
        "red",
        "gray",
        "yellow",
        "wide",
        "tight",
        "harsh",
        "early",
        "mid",
        "late",
        "loud",
        "held",
        "sold",
        "bare",
    }
)


@dataclass(frozen=True)
class MarketFeatures:
    slippage_1k: float | None
    fee_ratio: float
    return_15m: float
    stdev: float
    spread: float | None
    position_in_range: float
    inventory_bias: float
    inventory_empty: bool = False
    px_in: float | None = None
    px_15m: float | None = None
    sol_ui: float | None = None
    usdt_ui: float | None = None
    sources: tuple[str, ...] = ()


def neutral_features() -> MarketFeatures:
    return MarketFeatures(
        slippage_1k=None,
        fee_ratio=1.0,
        return_15m=0.0,
        stdev=0.0,
        spread=None,
        position_in_range=0.5,
        inventory_bias=0.0,
    )


def fee_ratio_from_micro_lamports(values: list[int]) -> float:
    if not values:
        return 1.0
    ordered = sorted(int(v) for v in values)
    median = ordered[len(ordered) // 2]
    return median / QUIET_MICRO_LAMPORTS


def stdev_of_simple_returns(prices: list[float]) -> float:
    if len(prices) < 3:
        return 0.0
    returns: list[float] = []
    for left, right in zip(prices, prices[1:]):
        if left <= 0:
            continue
        returns.append((right - left) / left)
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    return math.sqrt(variance)


def assemble_features(
    *,
    slippage_1k: float | None,
    fee_ratio: float | None,
    prices_1m: list[float] | None,
    spread: float | None,
    sol_ui: float | None,
    usdt_ui: float | None,
    px_fallback: float | None,
    sources: tuple[str, ...] = (),
) -> MarketFeatures:
    prices = [float(price) for price in (prices_1m or []) if price and price > 0]
    if prices:
        px_in = prices[-1]
        px_15m = prices[0] if len(prices) >= 2 else None
    else:
        px_in = px_fallback if px_fallback and px_fallback > 0 else None
        px_15m = None
    if px_in and px_15m:
        return_15m = (px_in - px_15m) / px_15m
    else:
        return_15m = 0.0
        px_15m = None
    stdev = stdev_of_simple_returns(prices)
    if len(prices) >= 2:
        low, high = min(prices), max(prices)
        position = 0.5 if high <= low or px_in is None else (px_in - low) / (high - low)
    else:
        position = 0.5
    if sol_ui is None or usdt_ui is None or px_in is None:
        bias = 0.0
        empty = False
    else:
        sol_value = sol_ui * px_in
        total = sol_value + usdt_ui
        if total <= 0:
            bias = 0.0
            empty = True
        else:
            bias = (sol_value - usdt_ui) / total
            empty = False
    return MarketFeatures(
        slippage_1k=slippage_1k,
        fee_ratio=1.0 if fee_ratio is None else fee_ratio,
        return_15m=return_15m,
        stdev=stdev,
        spread=spread,
        position_in_range=position,
        inventory_bias=bias,
        inventory_empty=empty,
        px_in=px_in,
        px_15m=px_15m,
        sol_ui=sol_ui,
        usdt_ui=usdt_ui,
        sources=sources,
    )


def _move_word(ret: float) -> str:
    if ret > PUMP_RETURN:
        return "pumping"
    if ret < DUMP_RETURN:
        return "dumping"
    if ret < FADE_RETURN:
        return "fading"
    return "flat"


def _color_word(ret: float, stdev: float) -> str:
    if abs(ret) <= 0.005 and stdev > VOL_VIOLENT:
        return "yellow"
    if ret > 0.005:
        return "green"
    if ret < -0.005:
        return "red"
    return "gray"


def _phase_word(position: float) -> str:
    if position < 0.33:
        return "early"
    if position > 0.66:
        return "late"
    return "mid"


def _pocket_word(position: float) -> str:
    if position < 0.15:
        return "early"
    if position > 0.85:
        return "late"
    return "mid"


def _inventory_word(bias: float, empty: bool) -> str:
    if empty:
        return "bare"
    if bias < -0.25:
        return "sold"
    return "held"


def adjective_slots(features: MarketFeatures) -> tuple[str, ...]:
    """Doze palavras, nesta ordem: depth fees move vol shape color spread tone phase pocket noise inventory."""
    depth = "thin" if features.slippage_1k is None or features.slippage_1k > SLIPPAGE_THIN else "deep"
    fees = "bot_war" if features.fee_ratio > FEE_BOT_WAR else "quiet"
    move = _move_word(features.return_15m)
    vol = "violent" if features.stdev > VOL_VIOLENT else "calm"
    shape = "flat" if abs(features.return_15m) <= PUMP_RETURN else move
    color = _color_word(features.return_15m, features.stdev)
    spread = "wide" if features.spread is None or features.spread > SPREAD_WIDE else "tight"
    tone = "harsh" if features.fee_ratio > FEE_BOT_WAR and features.stdev > VOL_VIOLENT else "calm"
    phase = _phase_word(features.position_in_range)
    pocket = _pocket_word(features.position_in_range)
    noise = "loud" if features.stdev > VOL_VIOLENT else "quiet"
    inventory = _inventory_word(features.inventory_bias, features.inventory_empty)
    return (depth, fees, move, vol, shape, color, spread, tone, phase, pocket, noise, inventory)


def build_state(features: MarketFeatures) -> str:
    words = adjective_slots(features)
    if len(words) != 12:
        raise ValueError("market state must be 12 words")
    unknown = [word for word in words if word not in ALLOWED_WORDS]
    if unknown:
        raise ValueError("market state left the adjective list")
    text = " ".join(words)
    if any(character.isdigit() for character in text):
        raise ValueError("market state leaked a number")
    return text


def fetch_features(cfg: Config) -> MarketFeatures:
    """Lê preço, book, quote, fees e saldos públicos. Falha de uma fonte não derruba o ciclo."""
    import httpx

    timeout = httpx.Timeout(4.0, connect=2.0)
    headers = {"User-Agent": "jev-solana-trader/0.1", "Accept": "application/json"}
    prices: list[float] | None = None
    spread: float | None = None
    slippage: float | None = None
    fee_ratio: float | None = None
    sol_ui: float | None = None
    usdt_ui: float | None = None
    px_fallback: float | None = None
    sources: list[str] = []

    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        try:
            response = client.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": "SOLUSDT", "interval": "1m", "limit": 16},
            )
            response.raise_for_status()
            prices = [float(row[4]) for row in response.json()]
            sources.append("tape")
        except Exception:
            prices = None
        try:
            response = client.get(
                "https://api.binance.com/api/v3/ticker/bookTicker",
                params={"symbol": "SOLUSDT"},
            )
            response.raise_for_status()
            book = response.json()
            bid = float(book["bidPrice"])
            ask = float(book["askPrice"])
            mid = (bid + ask) / 2
            if mid > 0:
                spread = (ask - bid) / mid
                sources.append("book")
        except Exception:
            spread = None
        try:
            response = client.get(
                f"{cfg.jupiter_quote_base}/swap/v1/quote",
                params={
                    "inputMint": USDT_MINT,
                    "outputMint": WSOL_MINT,
                    "amount": "1000000000",
                    "slippageBps": "50",
                },
            )
            response.raise_for_status()
            quote = response.json()
            impact = quote.get("priceImpactPct")
            slippage = abs(float(impact)) if impact is not None else None
            in_amount = int(quote["inAmount"])
            out_amount = int(quote["outAmount"])
            if out_amount > 0:
                px_fallback = (in_amount / 1_000_000) / (out_amount / 1_000_000_000)
            sources.append("quote")
        except Exception:
            slippage = None
        try:
            fee_ratio = _priority_fee_ratio(client, cfg.rpc_url)
            sources.append("fees")
        except Exception:
            fee_ratio = None
        try:
            sol_ui, usdt_ui = _balances(client, cfg.rpc_url, cfg.hot_wallet)
            sources.append("balances")
        except Exception:
            sol_ui, usdt_ui = None, None

    return assemble_features(
        slippage_1k=slippage,
        fee_ratio=fee_ratio,
        prices_1m=prices,
        spread=spread,
        sol_ui=sol_ui,
        usdt_ui=usdt_ui,
        px_fallback=px_fallback,
        sources=tuple(sources),
    )


def _rpc(client, url: str, method: str, params: list) -> dict:
    response = client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    response.raise_for_status()
    body = response.json()
    if body.get("error"):
        raise RuntimeError("rpc error")
    return body["result"]


def _priority_fee_ratio(client, rpc_url: str) -> float:
    rows = _rpc(client, rpc_url, "getRecentPrioritizationFees", [])
    values = [int(row.get("prioritizationFee") or 0) for row in rows]
    return fee_ratio_from_micro_lamports(values)


def _balances(client, rpc_url: str, wallet: str) -> tuple[float, float]:
    lamports = int(_rpc(client, rpc_url, "getBalance", [wallet])["value"])
    token_accounts = _rpc(
        client,
        rpc_url,
        "getTokenAccountsByOwner",
        [wallet, {"mint": USDT_MINT}, {"encoding": "jsonParsed"}],
    )
    usdt = 0.0
    for account in token_accounts.get("value", []):
        info = account["account"]["data"]["parsed"]["info"]["tokenAmount"]
        usdt += float(info.get("uiAmountString") or info.get("uiAmount") or 0)
    return lamports / 1_000_000_000, usdt
