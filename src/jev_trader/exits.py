"""Saídas mecânicas (TP/SL/trailing) e teto de exposição do livro de papel. Só contas puras.

Espelham o laboratório (research/paper-lab/bot/lab_bot.py `check_exits`/`_track` e bot/params.py `cap_buy`):

- Posição: todo o SOL do livro de papel (piso 0), não só o SOL acima do livro inicial. O SOL com que o livro
  começa entra com custo = preço de início do livro (`start_px`: `ref_sol_usd` do experimento no livro A, o
  `px_in` do primeiro ciclo noutro livro), como o `start_price` do lab.
- Custo médio: cada compra faz `(sol_antes × custo_antes + usdt_pago) / (sol_antes + sol_recebido)`; o USDT pago
  inclui o custo do fill, como no lab. Uma venda do portão (parcial) não mexe no custo médio; quando a posição
  fica em pó (≤ `DUST_SOL`) o custo médio e o pico são apagados.
- Pico: máximo do preço desde a entrada (atualizado a cada ciclo com saídas ligadas; numa compra com posição
  vazia recomeça no preço da compra).
- Retorno `r = px / custo_médio − 1`. Ordem: TP (`r ≥ tp`), SL (`r ≤ −sl`), trailing (armado quando
  `pico / custo_médio − 1 ≥ trail_arm`, dispara quando `px ≤ pico × (1 − trail)`; `trail_arm` ausente = `trail`).
- Sem saída quando a posição vale menos de `EXIT_MIN_USD` (lab: 1 US$).
- Saída vende `sell_frac` (padrão 1 = tudo) do SOL do livro; o resto, se houver, recomeça com custo e pico no
  preço da saída. Depois de uma saída, nenhuma compra durante `reentry_cooldown_min`.
- Teto de exposição: valor em SOL / valor do livro nunca passa de `max_exposure_frac` por causa de uma compra;
  a compra encolhe até caber, e sem espaço para a ordem mínima não há fill (motivo `max_exposure`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from jev_trader.records import parse_t

EXIT_MIN_USD = 1.0
DUST_SOL = 1e-6
EXIT_REASONS = ("tp", "sl", "trail")


@dataclass(frozen=True)
class ExitParams:
    enabled: bool = False
    tp: float | None = None
    sl: float | None = None
    trail: float | None = None
    trail_arm: float | None = None
    reentry_cooldown_min: float = 30.0
    sell_frac: float = 1.0

    @property
    def active(self) -> bool:
        """Ligadas e com pelo menos uma regra (tp, sl ou trail)."""
        return bool(self.enabled) and any(x is not None for x in (self.tp, self.sl, self.trail))

    def to_json(self) -> dict:
        return {
            "enabled": self.enabled,
            "tp": self.tp,
            "sl": self.sl,
            "trail": self.trail,
            "trail_arm": self.trail_arm,
            "reentry_cooldown_min": self.reentry_cooldown_min,
            "sell_frac": self.sell_frac,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "ExitParams":
        data = data or {}
        fields = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**fields)


def check_exit(params: ExitParams, avg_cost: float, peak: float | None, px: float) -> tuple[str | None, float, float]:
    """(motivo ou None, pico atualizado, retorno desde o custo médio). Não olha para o tamanho da posição."""
    peak_now = max(peak if peak is not None else avg_cost, px)
    ret = px / avg_cost - 1.0
    if not params.active:
        return None, peak_now, ret
    if params.tp is not None and ret >= params.tp:
        return "tp", peak_now, ret
    if params.sl is not None and ret <= -params.sl:
        return "sl", peak_now, ret
    if params.trail is not None:
        arm = params.trail_arm if params.trail_arm is not None else params.trail
        if peak_now / avg_cost - 1.0 >= arm and px <= peak_now * (1.0 - params.trail):
            return "trail", peak_now, ret
    return None, peak_now, ret


def avg_cost_after_buy(sol_before: float, avg_before: float | None, usdt_in: float, sol_got: float, px: float) -> float:
    """Custo médio depois de uma compra (USDT pago inclui o custo do fill). Sem custo anterior, o SOL antigo vale `px`."""
    prev = avg_before if avg_before is not None and sol_before > DUST_SOL else px
    held = sol_before if sol_before > DUST_SOL else 0.0
    total = held + sol_got
    if total <= 0:
        return px
    return (held * prev + usdt_in) / total


def peak_after_buy(sol_before: float, peak_before: float | None, px: float) -> float:
    if sol_before > DUST_SOL and peak_before is not None:
        return max(peak_before, px)
    return px


def cap_buy_usdt(
    amount: float,
    *,
    sol: float,
    usdt: float,
    px: float,
    cap: float | None,
    min_usdt: float,
) -> tuple[float | None, str | None]:
    """(USDT a gastar ou None, motivo). `cap` None = sem teto. Espaço = cap × livro − posição."""
    if cap is None:
        return amount, None
    position = max(sol, 0.0) * px
    room = cap * (max(usdt, 0.0) + position) - position
    if usdt <= 0 or room < min_usdt:
        return None, "max_exposure"
    return min(amount, room), None


def in_cooldown(last_exit_t: str | None, t: str | None, minutes: float) -> bool:
    """True se `t` cai antes de `last_exit_t + minutes`. Instantes ilegíveis → sem bloqueio."""
    last, now = parse_t(last_exit_t), parse_t(t)
    if last is None or now is None or minutes <= 0:
        return False
    return now < last + timedelta(minutes=minutes)


def exposure(sol: float, usdt: float, px: float | None) -> float | None:
    """Fração do livro em SOL ao preço `px`."""
    if px is None or not math.isfinite(px) or px <= 0:
        return None
    position = max(sol, 0.0) * px
    total = position + max(usdt, 0.0)
    return position / total if total > 0 else None


def replay_position(trades: list[dict], *, start_sol: float, start_cost: float | None) -> dict:
    """Reconstrói custo médio, pico e última saída a partir de `paper_trades.jsonl` (livros antigos sem estes campos).

    O pico reconstruído é o maior preço de compra desde a entrada (o histórico de preços entre trades não está aqui).
    """
    sol = max(start_sol, 0.0)
    avg = start_cost if sol > DUST_SOL else None
    peak = start_cost if sol > DUST_SOL else None
    last_exit_t = None
    n_exits = 0
    for trade in sorted(trades, key=lambda row: parse_t(row.get("t")) or parse_t("1970-01-01T00:00:00+00:00")):
        side = trade.get("side")
        px = _positive(trade.get("fill_px")) or _positive(trade.get("px_in"))
        amount_in = _number(trade.get("in_amount_ui")) or 0.0
        amount_out = _number(trade.get("out_amount_ui")) or 0.0
        after = trade.get("book_after") or {}
        sol_after = _number(after.get("sol"))
        if side == "buy" and px is not None:
            avg = avg_cost_after_buy(sol, avg, amount_in, amount_out, px)
            peak = peak_after_buy(sol, peak, _positive(trade.get("px_in")) or px)
            sol = sol_after if sol_after is not None else sol + amount_out
        elif side == "sell":
            sol = sol_after if sol_after is not None else max(sol - amount_in, 0.0)
            if trade.get("reason") in EXIT_REASONS:
                last_exit_t = trade.get("t")
                n_exits += 1
                if sol > DUST_SOL and px is not None:
                    avg, peak = px, px
        if sol <= DUST_SOL:
            avg = peak = None
    return {"avg_cost": avg, "peak_px": peak, "last_exit_t": last_exit_t, "n_exits": n_exits, "sol": sol}


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive(value: object) -> float | None:
    number = _number(value)
    return number if number is not None and number > 0 else None
