"""Paper trading do bot real: quando o portão manda executar em dry-run, simula o fill num livro local.

O livro vive em `logs/paper_book.json` e começa no livro de `config/experiment.json`. O tamanho é
o mesmo do swap ao vivo (`swap.order_size_ui`), limitado pelo saldo do livro. O preço é o `px_in`
da decisão com um custo em pontos-base contra o trader (`fill_mode: "mark"`). Nada sai da máquina.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from jev_trader.config import SOL_DECIMALS, USDT_DECIMALS, Config
from jev_trader.experiment import Experiment, load_experiment
from jev_trader.records import append_jsonl, write_json_atomic
from jev_trader.swap import _ui_to_atoms, order_size_ui

# Abaixo disto o saldo que sobra não chega para uma ordem: sem fill, motivo `insufficient_*`.
PAPER_MIN_USDT = 0.01
PAPER_MIN_SOL = 0.0001


class PaperBookError(Exception):
    pass


@dataclass(frozen=True)
class PaperBook:
    run_id: str
    sol: float
    usdt: float
    n_trades: int = 0
    updated_t: str | None = None

    def to_json(self) -> dict:
        return {
            "run_id": self.run_id,
            "sol": round(self.sol, SOL_DECIMALS),
            "usdt": round(self.usdt, USDT_DECIMALS),
            "n_trades": self.n_trades,
            "updated_t": self.updated_t,
        }


@dataclass(frozen=True)
class PaperResult:
    fill: bool
    reason: str | None
    book: PaperBook
    trade: dict | None = None


def initial_book(experiment: Experiment) -> PaperBook:
    return PaperBook(
        run_id=experiment.run_id,
        sol=experiment.book_sol,
        usdt=experiment.book_usdt,
        n_trades=0,
        updated_t=experiment.start_t,
    )


def load_book(path: Path, experiment: Experiment) -> PaperBook:
    """Ficheiro ausente → livro inicial do experimento. Ficheiro de outro run ou partido → erro, sem reescrever."""
    if not path.is_file():
        return initial_book(experiment)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        book = PaperBook(
            run_id=str(data["run_id"]),
            sol=float(data["sol"]),
            usdt=float(data["usdt"]),
            n_trades=int(data.get("n_trades") or 0),
            updated_t=data.get("updated_t"),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PaperBookError(f"paper book unreadable: {exc}") from None
    if not (math.isfinite(book.sol) and math.isfinite(book.usdt)) or book.sol < 0 or book.usdt < 0:
        raise PaperBookError("paper book has a negative or non-finite balance")
    if book.run_id != experiment.run_id:
        raise PaperBookError(
            f"paper book run_id {book.run_id} differs from experiment {experiment.run_id}; archive the old logs"
        )
    return book


def save_book(path: Path, book: PaperBook) -> None:
    write_json_atomic(path, book.to_json())


def size_order(cfg: Config, *, side: str, confidence: float, book: PaperBook) -> tuple[float | None, float, str]:
    """(quantidade de entrada ou None, nominal, motivo). Compra em USDT, venda em SOL."""
    nominal = order_size_ui(cfg, side=side, confidence=confidence)
    if side == "buy":
        decimals, available, minimum, short = USDT_DECIMALS, book.usdt, PAPER_MIN_USDT, "insufficient_usdt"
    else:
        decimals, available, minimum, short = SOL_DECIMALS, book.sol, PAPER_MIN_SOL, "insufficient_sol"
    nominal_atoms = _ui_to_atoms(nominal, decimals)
    available_atoms = max(int(math.floor(available * 10**decimals + 1e-6)), 0)
    atoms = min(nominal_atoms, available_atoms)
    amount = atoms / 10**decimals
    if amount < minimum:
        return None, nominal, short
    return amount, nominal, "filled"


def fill_price(side: str, px_in: float, cost_bps: float) -> float:
    """Compra paga mais caro, venda recebe menos: `px_in × (1 ± bps/10000)`."""
    cost = max(cost_bps, 0.0) / 10_000
    return px_in * (1 + cost) if side == "buy" else px_in * (1 - cost)


def simulate_fill(side: str, amount_in: float, px_in: float, cost_bps: float) -> tuple[float, float]:
    """(preço do fill, quantidade de saída arredondada para baixo em átomos)."""
    price = fill_price(side, px_in, cost_bps)
    if side == "buy":
        return price, _floor(amount_in / price, SOL_DECIMALS)
    return price, _floor(amount_in * price, USDT_DECIMALS)


def paper_cycle(
    cfg: Config,
    *,
    execute: bool,
    side: str,
    confidence: float,
    px_in: float | None,
    t: str,
) -> PaperResult:
    """Carrega (ou cria) o livro; se o portão executa, simula o fill, grava o livro e o trade."""
    experiment = load_experiment(cfg.experiment_path)
    book = load_book(cfg.paper_book_path, experiment)
    if not cfg.paper_book_path.is_file():
        save_book(cfg.paper_book_path, book)
    if not execute or side not in {"buy", "sell"}:
        return PaperResult(False, None, book)
    if px_in is None or not math.isfinite(px_in) or px_in <= 0:
        return PaperResult(False, "no_price", book)
    amount_in, nominal, reason = size_order(cfg, side=side, confidence=confidence, book=book)
    if amount_in is None:
        return PaperResult(False, reason, book)
    price, amount_out = simulate_fill(side, amount_in, px_in, cfg.paper_cost_bps)
    if side == "buy":
        sol, usdt = book.sol + amount_out, book.usdt - amount_in
        in_symbol, out_symbol = "USDT", "SOL"
    else:
        sol, usdt = book.sol - amount_in, book.usdt + amount_out
        in_symbol, out_symbol = "SOL", "USDT"
    after = PaperBook(
        run_id=book.run_id,
        sol=round(max(sol, 0.0), SOL_DECIMALS),
        usdt=round(max(usdt, 0.0), USDT_DECIMALS),
        n_trades=book.n_trades + 1,
        updated_t=t,
    )
    trade = {
        "t": t,
        "run_id": book.run_id,
        "decision_t": t,
        "side": side,
        "conf": round(confidence, 6),
        "px_in": round(px_in, 8),
        "fill_px": round(price, 8),
        "fill_mode": "mark",
        "cost_bps": cfg.paper_cost_bps,
        "in_symbol": in_symbol,
        "out_symbol": out_symbol,
        "in_amount_ui": amount_in,
        "out_amount_ui": amount_out,
        "nominal_in_ui": round(nominal, 9),
        "capped": amount_in < _nominal_ui(side, nominal),
        "book_after": {"sol": after.sol, "usdt": after.usdt},
        "n_trade": after.n_trades,
    }
    save_book(cfg.paper_book_path, after)
    append_jsonl(cfg.paper_trades_path, trade)
    return PaperResult(True, "filled", after, trade)


def _nominal_ui(side: str, nominal: float) -> float:
    decimals = USDT_DECIMALS if side == "buy" else SOL_DECIMALS
    return _ui_to_atoms(nominal, decimals) / 10**decimals


def _floor(value: float, decimals: int) -> float:
    scale = 10**decimals
    return math.floor(value * scale + 1e-6) / scale
