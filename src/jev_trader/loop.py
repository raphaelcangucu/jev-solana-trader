"""Um ciclo: estado, System One, portões, log e swap (ao vivo) ou fill no livro de papel (dry-run).

Em dry-run o livro de papel também avalia as saídas mecânicas (TP/SL/trailing) e o teto de exposição do perfil
(ver `paper.py`/`exits.py`); o registo leva `exit_reason`. Ao vivo não há saídas automáticas nem teto: se o perfil
os tiver, o registo leva `exits_warning` e o ciclo segue só com os portões de entrada.
"""

from __future__ import annotations

import json
import math

from jev_trader.config import Config
from jev_trader.exits import exposure
from jev_trader.decide import ask_system_one, resolve_action
from jev_trader.paper import paper_cycle
from jev_trader.records import append_jsonl, now_iso
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
        prob_margin_min=getattr(cfg, "prob_margin_min", 0.0),
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
    decision_t = _now_iso()
    paper = _paper_fields(cfg, gate, model.confidence, features.px_in, decision_t) if dry_run else _NO_PAPER
    exits_warning = None if dry_run else _live_exits_warning(cfg)
    reason = "swap_failed" if swap_error else gate.reason
    record = {
        "t": decision_t,
        "state": state,
        "action": gate.action,
        "conf": _round(model.confidence, 6),
        "skip": _round(model.skip_noul, 6),
        "px_in": _round(features.px_in, 8),
        "px_15m": _round(features.px_15m, 8),
        "model_action": model.choice if model.ok else None,
        "probabilities": {key: _round(value, 6) for key, value in model.probabilities.items()},
        "reason": reason,
        "params_profile": getattr(cfg, "params_profile", None),
        "book": getattr(cfg, "paper_book_label", "A"),
        "source": model.source,
        "dry_run": dry_run,
        "live_trading": cfg.live_trading,
        "submitted": submitted,
        "market_ok": market_ok,
        "sources": list(features.sources),
        "sol_ui": _round(features.sol_ui, 9),
        "usdt_ui": _round(features.usdt_ui, 6),
        "signature": signature,
        "paper": paper["paper"],
        "paper_fill": paper["paper_fill"],
        "paper_reason": paper["paper_reason"],
        "paper_sol": paper["paper_sol"],
        "paper_usdt": paper["paper_usdt"],
        "run_id": paper["run_id"],
        "exit_reason": paper["exit_reason"],
        "paper_avg_cost": paper["paper_avg_cost"],
        "paper_exposure": paper["paper_exposure"],
        "exits_warning": exits_warning,
        "error": model.error or fetch_error or swap_error or paper["paper_error"],
        "wallet": cfg.hot_wallet,
    }
    append_jsonl(cfg.decisions_path, record)
    print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return record


_NO_PAPER = {
    "paper": False,
    "paper_fill": False,
    "paper_reason": None,
    "paper_sol": None,
    "paper_usdt": None,
    "run_id": None,
    "paper_error": None,
    "exit_reason": None,
    "paper_avg_cost": None,
    "paper_exposure": None,
}


def _live_exits_warning(cfg: Config) -> str | None:
    """Saídas e teto de exposição são só paper por agora: ao vivo ficam desligados e o registo avisa."""
    exits = getattr(cfg, "exits", None)
    parts = []
    if exits is not None and exits.active:
        parts.append("exits")
    if getattr(cfg, "max_exposure_frac", None) is not None:
        parts.append("max_exposure_frac")
    if not parts:
        return None
    return f"{' e '.join(parts)} só em paper: ignorados ao vivo"


def _paper_fields(cfg: Config, gate, confidence: float, px_in: float | None, t: str) -> dict:
    """Só em dry-run. Um erro do livro de papel fica no registo e não derruba o ciclo."""
    try:
        result = paper_cycle(
            cfg,
            execute=gate.execute,
            side=gate.action,
            confidence=confidence,
            px_in=px_in,
            t=t,
        )
    except Exception as exc:
        return {**_NO_PAPER, "paper": True, "paper_reason": "paper_error", "paper_error": _clip(exc)}
    return {
        "paper": True,
        "paper_fill": result.fill,
        "paper_reason": result.reason,
        "paper_sol": _round(result.book.sol, 9),
        "paper_usdt": _round(result.book.usdt, 6),
        "run_id": result.book.run_id,
        "paper_error": None,
        "exit_reason": result.exit_reason,
        "paper_avg_cost": _round(result.book.avg_cost, 8),
        "paper_exposure": _round(exposure(result.book.sol, result.book.usdt, px_in), 6),
    }


def _now_iso() -> str:
    return now_iso()


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
