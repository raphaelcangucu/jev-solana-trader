"""Placar do livro de papel: os quatro critérios de sucesso do README, calculados a partir dos logs.

Só contas puras sobre listas de registos. A leitura dos ficheiros e a impressão ficam em `__main__.py`.

Livros A/B: `experiment_for_book` troca o início e o preço de referência pelos do `paper_book.json` quando o
livro começou depois do experimento (livro B começa no seu primeiro ciclo, com o mesmo livro inicial).
O placar leva também o rótulo do livro, o perfil e as saídas (por motivo), custo médio e exposição.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from jev_trader.exits import EXIT_REASONS, exposure, replay_position
from jev_trader.experiment import Experiment
from jev_trader.records import parse_t

HORIZON = timedelta(minutes=15)
TOLERANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class Timeline:
    """Decisões com `px_in`, ordenadas no tempo, para achar o preço ~15 min depois."""

    times: list[datetime]
    prices: list[float]
    stamps: list[str]


def build_timeline(decisions: list[dict]) -> Timeline:
    points: list[tuple[datetime, float, str]] = []
    for row in decisions:
        moment = parse_t(row.get("t"))
        price = _positive(row.get("px_in"))
        if moment is not None and price is not None:
            points.append((moment, price, str(row.get("t"))))
    points.sort(key=lambda item: item[0])
    return Timeline([p[0] for p in points], [p[1] for p in points], [p[2] for p in points])


def forward_return(
    timeline: Timeline,
    t0: datetime,
    px0: float,
    *,
    horizon: timedelta = HORIZON,
    tolerance: timedelta = TOLERANCE,
) -> tuple[float | None, float | None, str | None]:
    """(retorno, px posterior, t posterior) usando a primeira decisão com preço em [t0+15, t0+20] min.

    Sem decisão com preço nesse intervalo → (None, None, None), caso "por resolver".
    """
    target = t0 + horizon
    index = bisect.bisect_left(timeline.times, target)
    if index >= len(timeline.times):
        return None, None, None
    if timeline.times[index] > target + tolerance:
        return None, None, None
    later = timeline.prices[index]
    return later / px0 - 1.0, later, timeline.stamps[index]


def experiment_for_book(experiment: Experiment, book: dict | None) -> Experiment:
    """Experimento visto pelo livro: se o `paper_book.json` começou depois do experimento, início e referência dele."""
    if not isinstance(book, dict):
        return experiment
    start = parse_t(book.get("start_t"))
    exp_start = parse_t(experiment.start_t)
    if start is None or exp_start is None or start <= exp_start:
        return experiment
    ref = _positive(book.get("start_px"))
    return replace(
        experiment,
        start_t=str(book["start_t"]),
        ref_sol_usd=ref if ref is not None else experiment.ref_sol_usd,
        ref_source=f"px_in no início do livro {book.get('book') or '?'}" if ref is not None else experiment.ref_source,
    )


def exit_stats(trades: list[dict], book: dict | None, experiment: Experiment, last_px: float | None) -> dict:
    """Saídas por motivo, custo médio, pico e exposição. Livro sem estado de posição → reconstruído dos trades."""
    by_reason = {reason: 0 for reason in EXIT_REASONS}
    for trade in trades:
        if trade.get("side") == "sell" and trade.get("reason") in by_reason:
            by_reason[trade["reason"]] += 1
    book = book if isinstance(book, dict) else {}
    if "avg_cost" in book:
        avg, peak, last_exit = _positive(book.get("avg_cost")), _positive(book.get("peak_px")), book.get("last_exit_t")
    else:
        state = replay_position(trades, start_sol=experiment.book_sol, start_cost=experiment.ref_sol_usd)
        avg, peak, last_exit = state["avg_cost"], state["peak_px"], state["last_exit_t"]
    return {
        "total": sum(by_reason.values()),
        "by_reason": by_reason,
        "avg_cost": None if avg is None else round(avg, 8),
        "peak_px": None if peak is None else round(peak, 8),
        "ret_from_avg": round(last_px / avg - 1, 8) if avg and last_px else None,
        "last_exit_t": last_exit,
    }


def select_run(rows: list[dict], experiment: Experiment, since: datetime | None = None) -> list[dict]:
    """Registos do run: `t` >= início (ou `since`, se for mais tarde) e `run_id` igual quando existe."""
    start = parse_t(experiment.start_t)
    floor = start if since is None or (start is not None and since < start) else since
    kept: list[dict] = []
    for row in rows:
        moment = parse_t(row.get("t"))
        if moment is None or (floor is not None and moment < floor):
            continue
        run_id = row.get("run_id")
        if run_id is not None and run_id != experiment.run_id:
            continue
        kept.append(row)
    kept.sort(key=lambda item: parse_t(item.get("t")))
    return kept


def hit_rate(trades: list[dict], timeline: Timeline) -> dict:
    """Compra quer alta, venda quer queda, 15 min depois. Retorno zero conta como erro."""
    hits = misses = unresolved = 0
    rows: list[dict] = []
    for trade in trades:
        moment = parse_t(trade.get("decision_t") or trade.get("t"))
        price = _positive(trade.get("px_in"))
        side = trade.get("side")
        if moment is None or price is None or side not in {"buy", "sell"}:
            unresolved += 1
            continue
        ret, later, later_t = forward_return(timeline, moment, price)
        if ret is None:
            unresolved += 1
            rows.append({"t": trade.get("t"), "side": side, "status": "unresolved"})
            continue
        hit = ret > 0 if side == "buy" else ret < 0
        hits += int(hit)
        misses += int(not hit)
        rows.append(
            {
                "t": trade.get("t"),
                "side": side,
                "status": "hit" if hit else "miss",
                "ret": round(ret, 8),
                "px_later": later,
                "t_later": later_t,
            }
        )
    resolved = hits + misses
    return {
        "hits": hits,
        "misses": misses,
        "resolved": resolved,
        "unresolved": unresolved,
        "rate": round(hits / resolved, 6) if resolved else None,
        "horizon_min": int(HORIZON.total_seconds() // 60),
        "tolerance_min": int(TOLERANCE.total_seconds() // 60),
        "detail": rows,
    }


def equity_series(decisions: list[dict]) -> list[tuple[str, float]]:
    """Livro de papel depois de cada decisão × `px_in` da mesma decisão."""
    series: list[tuple[str, float]] = []
    for row in decisions:
        price = _positive(row.get("px_in"))
        sol = _number(row.get("paper_sol"))
        usdt = _number(row.get("paper_usdt"))
        if price is None or sol is None or usdt is None:
            continue
        series.append((str(row.get("t")), sol * price + usdt))
    return series


def max_drawdown(series: list[tuple[str, float]]) -> dict:
    """Maior queda do pico ao vale. `pct` é relativo ao pico."""
    best = {"usd": 0.0, "pct": 0.0, "peak_t": None, "trough_t": None}
    if not series:
        return {**best, "usd": None, "pct": None, "points": 0}
    peak_t, peak = series[0]
    for moment, value in series:
        if value > peak:
            peak_t, peak = moment, value
        drop = peak - value
        if drop > best["usd"]:
            best = {
                "usd": drop,
                "pct": drop / peak * 100 if peak > 0 else 0.0,
                "peak_t": peak_t,
                "trough_t": moment,
            }
    return {
        "usd": round(best["usd"], 6),
        "pct": round(best["pct"], 4),
        "peak_t": best["peak_t"],
        "trough_t": best["trough_t"],
        "points": len(series),
    }


def scoreboard(
    decisions: list[dict],
    paper_trades: list[dict],
    experiment: Experiment,
    *,
    since: datetime | None = None,
    book: dict | None = None,
) -> dict:
    """Os quatro números. PnL é sempre desde o início do run (ou do livro); `since` limita hit rate, drawdown e trades.

    `book` é o `paper_book.json` (opcional): dá o rótulo, o início de um livro B e o estado da posição.
    """
    experiment = experiment_for_book(experiment, book)
    run_decisions = select_run(decisions, experiment)
    run_trades = select_run(paper_trades, experiment)
    window_decisions = select_run(decisions, experiment, since)
    window_trades = select_run(paper_trades, experiment, since)
    timeline = build_timeline(run_decisions)

    last_px, last_t = _last_price(run_decisions, run_trades)
    sol, usdt = _paper_book_now(run_decisions, run_trades, experiment)
    start_sol, start_usdt = experiment.book_sol, experiment.book_usdt

    pnl_hold = _pnl(sol, usdt, start_sol, start_usdt, last_px, last_px)
    pnl_start = _pnl(sol, usdt, start_sol, start_usdt, last_px, experiment.ref_sol_usd)

    buys = sum(1 for trade in window_trades if trade.get("side") == "buy")
    sells = sum(1 for trade in window_trades if trade.get("side") == "sell")
    label = (book or {}).get("book") if isinstance(book, dict) else None
    profile = next((row.get("params_profile") for row in reversed(run_decisions) if row.get("params_profile")), None)
    exits = exit_stats(window_trades, book, experiment, last_px)
    exits["exposure"] = _round_or_none(exposure(sol, usdt, last_px), 6)
    return {
        "book": label or "A",
        "params_profile": profile,
        "run_id": experiment.run_id,
        "start_t": experiment.start_t,
        "since": since.isoformat() if since else None,
        "n_decisions": len(window_decisions),
        "last_t": last_t,
        "last_px": last_px,
        "start_book": {"sol": start_sol, "usdt": start_usdt},
        "paper_book": {"sol": sol, "usdt": usdt},
        "pnl_vs_hold": pnl_hold,
        "pnl_vs_start": {**pnl_start, "ref_sol_usd": experiment.ref_sol_usd, "ref_source": experiment.ref_source},
        "hit_rate": hit_rate(window_trades, timeline),
        "drawdown": max_drawdown(equity_series(window_decisions)),
        "trades": {"total": len(window_trades), "buy": buys, "sell": sells},
        "exits": exits,
    }


def render_table(board: dict) -> str:
    """Tabela legível, em português."""
    hold = board["pnl_vs_hold"]
    start = board["pnl_vs_start"]
    hits = board["hit_rate"]
    dd = board["drawdown"]
    trades = board["trades"]
    paper = board["paper_book"]
    base = board["start_book"]
    rate = "—" if hits["rate"] is None else f"{hits['rate'] * 100:.1f}%"
    ref = start.get("ref_sol_usd")
    rows = [
        ("Run", board["run_id"]),
        ("Início", board["start_t"]),
        ("Janela desde", board["since"] or board["start_t"]),
        ("Decisões na janela", str(board["n_decisions"])),
        ("Último px_in", f"{_fmt(board['last_px'], 4)} ({board['last_t'] or '—'})"),
        ("Livro de papel", f"{paper['sol']:.9f} SOL + {paper['usdt']:.6f} USDT"),
        ("Livro inicial", f"{base['sol']:.9f} SOL + {base['usdt']:.6f} USDT"),
        ("1. PnL contra segurar", f"{_signed(hold['usd'], 6)} USD ({_signed(hold['pct'], 4)}%)"),
        ("   papel / parado", f"{_fmt(hold['paper_value_usd'], 6)} / {_fmt(hold['base_value_usd'], 6)} USD"),
        (
            "   contra o início",
            f"{_signed(start['usd'], 6)} USD ({_signed(start['pct'], 4)}%), ref {_fmt(ref, 3)} USD/SOL",
        ),
        (
            "2. Hit rate 15 min",
            f"{rate} ({hits['hits']}/{hits['resolved']} resolvidos, {hits['unresolved']} por resolver)",
        ),
        ("3. Max drawdown", f"{_fmt(dd['usd'], 6)} USD ({_fmt(dd['pct'], 4)}%) em {dd['points']} pontos"),
        ("4. Trades de papel", f"{trades['total']} ({trades['buy']} compras, {trades['sell']} vendas)"),
    ]
    exits = board.get("exits")
    if exits:
        reasons = exits["by_reason"]
        expo = exits.get("exposure")
        rows += [
            ("Saídas mecânicas", f"{exits['total']} (tp {reasons['tp']}, sl {reasons['sl']}, trail {reasons['trail']})"),
            (
                "Custo médio / exposição",
                f"{_fmt(exits.get('avg_cost'), 4)} USD/SOL / "
                + ("—" if expo is None else f"{expo * 100:.1f}% em SOL"),
            ),
        ]
    width = max(len(label) for label, _ in rows)
    title = f"Placar do livro de papel {board.get('book') or 'A'}"
    if board.get("params_profile"):
        title += f" (perfil {board['params_profile']})"
    lines = [title, ""]
    lines += [f"{label.ljust(width)}  {value}" for label, value in rows]
    return "\n".join(lines)


def _pnl(
    sol: float,
    usdt: float,
    base_sol: float,
    base_usdt: float,
    px_paper: float | None,
    px_base: float | None,
) -> dict:
    if px_paper is None or px_base is None:
        return {"usd": None, "pct": None, "paper_value_usd": None, "base_value_usd": None}
    paper_value = sol * px_paper + usdt
    base_value = base_sol * px_base + base_usdt
    diff = paper_value - base_value
    return {
        "usd": round(diff, 6),
        "pct": round(diff / base_value * 100, 4) if base_value > 0 else None,
        "paper_value_usd": round(paper_value, 6),
        "base_value_usd": round(base_value, 6),
    }


def _last_price(decisions: list[dict], trades: list[dict]) -> tuple[float | None, str | None]:
    for row in reversed(decisions):
        price = _positive(row.get("px_in"))
        if price is not None:
            return price, row.get("t")
    for row in reversed(trades):
        price = _positive(row.get("px_in"))
        if price is not None:
            return price, row.get("t")
    return None, None


def _paper_book_now(decisions: list[dict], trades: list[dict], experiment: Experiment) -> tuple[float, float]:
    for row in reversed(decisions):
        sol, usdt = _number(row.get("paper_sol")), _number(row.get("paper_usdt"))
        if sol is not None and usdt is not None:
            return sol, usdt
    for row in reversed(trades):
        book = row.get("book_after") or {}
        sol, usdt = _number(book.get("sol")), _number(book.get("usdt"))
        if sol is not None and usdt is not None:
            return sol, usdt
    return experiment.book_sol, experiment.book_usdt


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _positive(value: object) -> float | None:
    number = _number(value)
    return number if number is not None and number > 0 else None


def _round_or_none(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def _fmt(value: float | None, digits: int) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _signed(value: float | None, digits: int) -> str:
    return "—" if value is None else f"{value:+.{digits}f}"
