"""Paper trading do bot real: quando o portão manda executar em dry-run, simula o fill num livro local.

O livro vive em `<LOG_DIR>/paper_book.json` e começa no livro de `config/experiment.json`. O tamanho é
o mesmo do swap ao vivo (`swap.order_size_ui`), limitado pelo saldo do livro. O preço é o `px_in`
da decisão com um custo em pontos-base contra o trader (`fill_mode: "mark"`). Nada sai da máquina.

Livros A/B: `PAPER_BOOK` dá o rótulo e `LOG_DIR` a pasta. O livro A começa no instante do experimento
(`start_t`, preço de referência `ref_sol_usd`); outro livro começa no seu primeiro ciclo (`start_t` = esse
instante, `start_px` = o primeiro `px_in`), sempre com o livro inicial do experimento. Ambos ficam gravados
no `paper_book.json`, e o placar usa-os.

Posição e saídas (regras em `exits.py`): o livro guarda custo médio, pico desde a entrada, última saída e
contagem de saídas. A cada ciclo com preço, se as saídas estiverem ligadas, primeiro avalia TP/SL/trailing
sobre todo o SOL do livro e, se disparar, vende como fill de papel (`side: sell`, `reason: tp|sl|trail`);
depois executa o portão (compras bloqueadas durante `reentry_cooldown_min` após uma saída e limitadas pelo
teto de exposição). Livros antigos sem estes campos: o custo médio é reconstruído de `paper_trades.jsonl`
(SOL inicial ao `ref_sol_usd`) ou, sem histórico, fica no `px_in` do ciclo, com nota em `position_note`.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from pathlib import Path

from jev_trader.config import SOL_DECIMALS, USDT_DECIMALS, Config
from jev_trader.exits import (
    DUST_SOL,
    EXIT_MIN_USD,
    avg_cost_after_buy,
    cap_buy_usdt,
    check_exit,
    exposure,
    in_cooldown,
    peak_after_buy,
    replay_position,
)
from jev_trader.experiment import Experiment, load_experiment
from jev_trader.records import append_jsonl, read_jsonl, write_json_atomic
from jev_trader.swap import _ui_to_atoms, order_size_ui

# Abaixo disto o saldo que sobra não chega para uma ordem: sem fill, motivo `insufficient_*`.
PAPER_MIN_USDT = 0.01
PAPER_MIN_SOL = 0.0001
DEFAULT_BOOK = "A"


class PaperBookError(Exception):
    pass


@dataclass(frozen=True)
class PaperBook:
    run_id: str
    sol: float
    usdt: float
    n_trades: int = 0
    updated_t: str | None = None
    book: str = DEFAULT_BOOK
    start_t: str | None = None
    start_px: float | None = None
    avg_cost: float | None = None
    peak_px: float | None = None
    last_exit_t: str | None = None
    n_exits: int = 0
    position_note: str | None = None

    def to_json(self) -> dict:
        return {
            "run_id": self.run_id,
            "sol": round(self.sol, SOL_DECIMALS),
            "usdt": round(self.usdt, USDT_DECIMALS),
            "n_trades": self.n_trades,
            "updated_t": self.updated_t,
            "book": self.book,
            "start_t": self.start_t,
            "start_px": _r(self.start_px, 8),
            "avg_cost": _r(self.avg_cost, 8),
            "peak_px": _r(self.peak_px, 8),
            "last_exit_t": self.last_exit_t,
            "n_exits": self.n_exits,
            "position_note": self.position_note,
        }


@dataclass(frozen=True)
class PaperResult:
    fill: bool
    reason: str | None
    book: PaperBook
    trade: dict | None = None
    exit_trade: dict | None = None

    @property
    def exit_reason(self) -> str | None:
        return (self.exit_trade or {}).get("reason")


def initial_book(
    experiment: Experiment,
    *,
    label: str = DEFAULT_BOOK,
    t: str | None = None,
    px: float | None = None,
) -> PaperBook:
    """Livro inicial do experimento. Livro A: início e referência do experimento; outro: o primeiro ciclo."""
    if label == DEFAULT_BOOK:
        start_t, start_px = experiment.start_t, experiment.ref_sol_usd
    else:
        start_t, start_px = t or experiment.start_t, _valid_px(px)
    has_sol = experiment.book_sol > DUST_SOL
    return PaperBook(
        run_id=experiment.run_id,
        sol=experiment.book_sol,
        usdt=experiment.book_usdt,
        n_trades=0,
        updated_t=start_t,
        book=label,
        start_t=start_t,
        start_px=start_px,
        avg_cost=start_px if has_sol else None,
        peak_px=start_px if has_sol else None,
    )


def load_book(
    path: Path,
    experiment: Experiment,
    *,
    label: str | None = None,
    trades_path: Path | None = None,
    t: str | None = None,
    px: float | None = None,
) -> PaperBook:
    """Ficheiro ausente → livro inicial do experimento. Ficheiro de outro run, de outro livro ou partido → erro."""
    return _load(path, experiment, label=label, trades_path=trades_path, t=t, px=px)[0]


def _load(
    path: Path,
    experiment: Experiment,
    *,
    label: str | None,
    trades_path: Path | None,
    t: str | None,
    px: float | None,
) -> tuple[PaperBook, bool]:
    """(livro, precisa de ser gravado): ficheiro novo ou livro antigo sem os campos de posição."""
    if not path.is_file():
        return initial_book(experiment, label=label or DEFAULT_BOOK, t=t, px=px), True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        stored_label = str(data.get("book") or label or DEFAULT_BOOK)
        book = PaperBook(
            run_id=str(data["run_id"]),
            sol=float(data["sol"]),
            usdt=float(data["usdt"]),
            n_trades=int(data.get("n_trades") or 0),
            updated_t=data.get("updated_t"),
            book=stored_label,
            start_t=data.get("start_t") or (experiment.start_t if stored_label == DEFAULT_BOOK else None),
            start_px=_valid_px(data.get("start_px")),
            avg_cost=_valid_px(data.get("avg_cost")),
            peak_px=_valid_px(data.get("peak_px")),
            last_exit_t=data.get("last_exit_t"),
            n_exits=int(data.get("n_exits") or 0),
            position_note=data.get("position_note"),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise PaperBookError(f"paper book unreadable: {exc}") from None
    if not (math.isfinite(book.sol) and math.isfinite(book.usdt)) or book.sol < 0 or book.usdt < 0:
        raise PaperBookError("paper book has a negative or non-finite balance")
    if book.run_id != experiment.run_id:
        raise PaperBookError(
            f"paper book run_id {book.run_id} differs from experiment {experiment.run_id}; archive the old logs"
        )
    if label is not None and book.book != label:
        raise PaperBookError(f"paper book is book {book.book} but PAPER_BOOK={label}; check LOG_DIR")
    if book.start_t is None:
        book = replace(book, start_t=book.updated_t or experiment.start_t)
    if book.start_px is None and book.book == DEFAULT_BOOK:
        book = replace(book, start_px=experiment.ref_sol_usd)
    migrated = "avg_cost" not in data
    if migrated and book.sol > DUST_SOL:
        book = _derive_position(book, experiment, trades_path)
    return book, migrated


def _derive_position(book: PaperBook, experiment: Experiment, trades_path: Path | None) -> PaperBook:
    """Livro antigo sem estado de posição: reconstrói de `paper_trades.jsonl` (SOL inicial ao `start_px`)."""
    trades = [
        row for row in (read_jsonl(trades_path) if trades_path is not None else [])
        if row.get("run_id") in (None, book.run_id)
    ]
    start_cost = book.start_px or experiment.ref_sol_usd
    if not trades and start_cost is None:
        return book
    state = replay_position(trades, start_sol=experiment.book_sol, start_cost=start_cost)
    return replace(
        book,
        avg_cost=state["avg_cost"],
        peak_px=state["peak_px"],
        last_exit_t=state["last_exit_t"],
        n_exits=state["n_exits"],
        position_note=f"avg_cost reconstruído de {len(trades)} paper_trades (SOL inicial a {start_cost})",
    )


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
    """Carrega (ou cria) o livro; avalia as saídas; se o portão executa, simula o fill; grava livro e trades."""
    experiment = load_experiment(cfg.experiment_path)
    label = getattr(cfg, "paper_book_label", DEFAULT_BOOK)
    px = _valid_px(px_in)
    book, persist = _load(
        cfg.paper_book_path, experiment, label=label, trades_path=cfg.paper_trades_path, t=t, px=px
    )
    before = book
    if px is not None:
        if book.start_px is None:
            book = replace(book, start_px=px)
        if book.avg_cost is None and book.sol > DUST_SOL:
            book = replace(book, avg_cost=px, peak_px=px, position_note=f"avg_cost = px_in de {t} (sem histórico)")

    exit_trade = None
    exits = getattr(cfg, "exits", None)
    if px is not None and exits is not None and exits.active:
        book, exit_trade = _check_exits(cfg, book, px, t)

    fill, reason, trade = False, None, None
    if execute and side in {"buy", "sell"}:
        fill, reason, book, trade = _gate_fill(cfg, book, side=side, confidence=confidence, px=px, t=t)

    if persist or book != before:
        save_book(cfg.paper_book_path, book)
    return PaperResult(fill, reason, book, trade, exit_trade)


def _check_exits(cfg: Config, book: PaperBook, px: float, t: str) -> tuple[PaperBook, dict | None]:
    """Atualiza o pico e, se TP/SL/trailing disparar, vende `sell_frac` do SOL do livro como fill de papel."""
    if book.sol <= DUST_SOL or book.avg_cost is None:
        return book, None
    reason, peak, ret = check_exit(cfg.exits, book.avg_cost, book.peak_px, px)
    book = replace(book, peak_px=peak)
    if reason is None or book.sol * px < EXIT_MIN_USD:
        return book, None
    amount_in = _floor(book.sol * cfg.exits.sell_frac, SOL_DECIMALS)
    if amount_in < PAPER_MIN_SOL:
        return book, None
    avg_cost = book.avg_cost
    price, amount_out = simulate_fill("sell", amount_in, px, cfg.paper_cost_bps)
    sol = round(max(book.sol - amount_in, 0.0), SOL_DECIMALS)
    left = sol > DUST_SOL
    after = replace(
        book,
        sol=sol,
        usdt=round(book.usdt + amount_out, USDT_DECIMALS),
        n_trades=book.n_trades + 1,
        updated_t=t,
        # O que sobra (sell_frac < 1) recomeça no preço da saída; posição vazia não tem custo nem pico.
        avg_cost=px if left else None,
        peak_px=px if left else None,
        last_exit_t=t,
        n_exits=book.n_exits + 1,
    )
    trade = _trade_row(
        cfg, after, t=t, side="sell", reason=reason, confidence=None, px_in=px, price=price,
        amount_in=amount_in, amount_out=amount_out, nominal=amount_in, capped=False,
    )
    trade.update(
        {
            "avg_cost": _r(avg_cost, 8),
            "peak_px": _r(peak, 8),
            "ret_from_avg": _r(ret, 8),
            "sell_frac": cfg.exits.sell_frac,
        }
    )
    append_jsonl(cfg.paper_trades_path, trade)
    return after, trade


def _gate_fill(
    cfg: Config,
    book: PaperBook,
    *,
    side: str,
    confidence: float,
    px: float | None,
    t: str,
) -> tuple[bool, str, PaperBook, dict | None]:
    if px is None:
        return False, "no_price", book, None
    exits = getattr(cfg, "exits", None)
    if side == "buy" and exits is not None and exits.enabled and in_cooldown(book.last_exit_t, t, exits.reentry_cooldown_min):
        return False, "reentry_cooldown", book, None
    amount_in, nominal, reason = size_order(cfg, side=side, confidence=confidence, book=book)
    if amount_in is None:
        return False, reason, book, None
    exposure_capped = False
    if side == "buy":
        capped_usdt, why = cap_buy_usdt(
            amount_in,
            sol=book.sol,
            usdt=book.usdt,
            px=px,
            cap=getattr(cfg, "max_exposure_frac", None),
            min_usdt=PAPER_MIN_USDT,
        )
        if capped_usdt is None:
            return False, why or "max_exposure", book, None
        capped_usdt = _floor(capped_usdt, USDT_DECIMALS)
        if capped_usdt < PAPER_MIN_USDT:
            return False, "max_exposure", book, None
        exposure_capped = capped_usdt < amount_in
        amount_in = capped_usdt
    price, amount_out = simulate_fill(side, amount_in, px, cfg.paper_cost_bps)
    if side == "buy":
        sol, usdt = book.sol + amount_out, book.usdt - amount_in
        avg_cost = avg_cost_after_buy(book.sol, book.avg_cost, amount_in, amount_out, px)
        peak_px = peak_after_buy(book.sol, book.peak_px, px)
    else:
        sol, usdt = book.sol - amount_in, book.usdt + amount_out
        avg_cost, peak_px = book.avg_cost, book.peak_px
    sol = round(max(sol, 0.0), SOL_DECIMALS)
    if sol <= DUST_SOL:
        avg_cost = peak_px = None
    after = replace(
        book,
        sol=sol,
        usdt=round(max(usdt, 0.0), USDT_DECIMALS),
        n_trades=book.n_trades + 1,
        updated_t=t,
        avg_cost=avg_cost,
        peak_px=peak_px,
    )
    trade = _trade_row(
        cfg, after, t=t, side=side, reason="gate", confidence=confidence, px_in=px, price=price,
        amount_in=amount_in, amount_out=amount_out, nominal=nominal,
        capped=exposure_capped or amount_in < _nominal_ui(side, nominal),
    )
    if exposure_capped:
        trade["exposure_capped"] = True
    append_jsonl(cfg.paper_trades_path, trade)
    return True, "filled", after, trade


def _trade_row(
    cfg: Config,
    after: PaperBook,
    *,
    t: str,
    side: str,
    reason: str,
    confidence: float | None,
    px_in: float,
    price: float,
    amount_in: float,
    amount_out: float,
    nominal: float,
    capped: bool,
) -> dict:
    in_symbol, out_symbol = ("USDT", "SOL") if side == "buy" else ("SOL", "USDT")
    return {
        "t": t,
        "run_id": after.run_id,
        "book": after.book,
        "decision_t": t,
        "side": side,
        "reason": reason,
        "conf": None if confidence is None else round(confidence, 6),
        "px_in": round(px_in, 8),
        "fill_px": round(price, 8),
        "fill_mode": "mark",
        "cost_bps": cfg.paper_cost_bps,
        "in_symbol": in_symbol,
        "out_symbol": out_symbol,
        "in_amount_ui": amount_in,
        "out_amount_ui": amount_out,
        "nominal_in_ui": round(nominal, 9),
        "capped": capped,
        "book_after": {"sol": after.sol, "usdt": after.usdt},
        "exposure_after": _r(exposure(after.sol, after.usdt, px_in), 6),
        "n_trade": after.n_trades,
    }


def _nominal_ui(side: str, nominal: float) -> float:
    decimals = USDT_DECIMALS if side == "buy" else SOL_DECIMALS
    return _ui_to_atoms(nominal, decimals) / 10**decimals


def _floor(value: float, decimals: int) -> float:
    scale = 10**decimals
    return math.floor(value * scale + 1e-6) / scale


def _valid_px(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _r(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)
