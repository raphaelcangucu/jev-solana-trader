"""Início do experimento corrente (`config/experiment.json`): run, instante, livro e preço de referência."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from jev_trader.config import EXPERIMENT_WALLET
from jev_trader.records import parse_t


@dataclass(frozen=True)
class Experiment:
    run_id: str
    start_t: str
    wallet: str
    slot: int | None
    book_sol: float
    book_usdt: float
    ref_sol_usd: float | None
    ref_source: str | None
    mode: str


# Execução 1, reiniciada em 2026-09-30 como paper trading. Vale quando o ficheiro não existe.
DEFAULT_EXPERIMENT = Experiment(
    run_id="run1_2026-09-30",
    start_t="2026-09-30T00:50:19-03:00",
    wallet=EXPERIMENT_WALLET,
    slot=451848237,
    book_sol=0.017392206,
    book_usdt=50.00929,
    ref_sol_usd=119.305,
    ref_source="coinbase spot",
    mode="paper",
)


class ExperimentError(ValueError):
    pass


def load_experiment(path: Path) -> Experiment:
    """Ficheiro ausente → `DEFAULT_EXPERIMENT`. Ficheiro presente mas inválido → `ExperimentError`."""
    if not path.is_file():
        return DEFAULT_EXPERIMENT
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExperimentError(f"experiment file unreadable: {exc}") from None
    if not isinstance(data, dict):
        raise ExperimentError("experiment file must be a JSON object")
    book = data.get("book") or {}
    if not isinstance(book, dict):
        raise ExperimentError("experiment book must be an object")
    run_id = str(data.get("run_id") or "").strip()
    start_t = str(data.get("start_t") or "").strip()
    if not run_id:
        raise ExperimentError("experiment run_id missing")
    if parse_t(start_t) is None:
        raise ExperimentError("experiment start_t is not ISO 8601")
    sol = _non_negative(book.get("sol"), "book.sol")
    usdt = _non_negative(book.get("usdt"), "book.usdt")
    ref = data.get("ref_sol_usd")
    ref_f = None if ref is None else _non_negative(ref, "ref_sol_usd")
    slot = data.get("slot")
    return Experiment(
        run_id=run_id,
        start_t=start_t,
        wallet=str(data.get("wallet") or EXPERIMENT_WALLET),
        slot=int(slot) if isinstance(slot, (int, float)) else None,
        book_sol=sol,
        book_usdt=usdt,
        ref_sol_usd=ref_f,
        ref_source=data.get("ref_source"),
        mode=str(data.get("mode") or "paper"),
    )


def _non_negative(value: object, name: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ExperimentError(f"experiment {name} is not numeric") from None
    if not math.isfinite(number) or number < 0:
        raise ExperimentError(f"experiment {name} must be finite and >= 0")
    return number
