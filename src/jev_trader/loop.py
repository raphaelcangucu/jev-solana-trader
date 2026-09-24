"""Um ciclo: estado, System One, portões, log e (ao vivo) swap."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jev_trader.config import Config
from jev_trader.decide import ask_system_one, resolve_action
from jev_trader.state import build_state, fetch_features, neutral_features
from jev_trader.swap import SwapError, execute_swap


def run_cycle(cfg: Config, *, dry_run: bool) -> dict:
    fetch_error = None
    try:
        features = fetch_features(cfg)
    except Exception as exc:
        features = neutral_features()
        fetch_error = _clip(exc)
    market_ok = features.px_in is not None
    state = build_state(features)
    model = ask_system_one(state, cfg)
    gate = resolve_action(
        model,
        market_ok=market_ok,
        confidence_min=cfg.confidence_min,
        skip_min=cfg.skip_min,
    )
    submitted = False
    swap_error = None
    signature = None
    if gate.execute and not dry_run:
        try:
            trade = execute_swap(cfg, side=gate.action, confidence=model.confidence)
            trade["t"] = _now_iso()
            append_jsonl(cfg.trades_path, trade)
            submitted = True
            signature = trade.get("signature")
        except (SwapError, Exception) as exc:
            swap_error = _clip(exc, cfg)
            append_jsonl(
                cfg.trades_path,
                {
                    "t": _now_iso(),
                    "ok": False,
                    "kind": "ultra",
                    "side": gate.action,
                    "wallet": cfg.hot_wallet,
                    "error": swap_error,
                },
            )
    reason = "swap_failed" if swap_error else gate.reason
    record = {
        "t": _now_iso(),
        "state": state,
        "action": gate.action,
        "conf": _round(model.confidence, 6),
        "skip": _round(model.skip_noul, 6),
        "px_in": _round(features.px_in, 8),
        "px_15m": _round(features.px_15m, 8),
        "model_action": model.choice if model.ok else None,
        "probabilities": {key: _round(value, 6) for key, value in model.probabilities.items()},
        "reason": reason,
        "source": model.source,
        "dry_run": dry_run,
        "live_trading": cfg.live_trading,
        "submitted": submitted,
        "market_ok": market_ok,
        "sources": list(features.sources),
        "sol_ui": _round(features.sol_ui, 9),
        "usdt_ui": _round(features.usdt_ui, 6),
        "signature": signature,
        "error": model.error or fetch_error or swap_error,
        "wallet": cfg.hot_wallet,
    }
    append_jsonl(cfg.decisions_path, record)
    print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return record


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _now_iso() -> str:
    try:
        from zoneinfo import ZoneInfo

        clock = ZoneInfo("America/Sao_Paulo")
    except Exception:
        clock = timezone(timedelta(hours=-3))
    return datetime.now(clock).isoformat(timespec="seconds")


def _round(value, digits: int):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, digits)


def _clip(exc: Exception, cfg: Config | None = None) -> str:
    text = " ".join(str(exc).split())
    if cfg and cfg.jupiter_api_key:
        text = text.replace(cfg.jupiter_api_key, "[redacted]")
    return text[:180]
