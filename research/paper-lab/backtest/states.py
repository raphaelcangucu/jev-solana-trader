"""Estados de 12 adjetivos por passo, reconstruídos a partir das séries históricas.

Lab (bot/lib.build_state, a função usada pelo sol_bot e pelo meme_bot): as janelas são em AMOSTRAS do histórico de
preços (curta 4, média 20, longa 80). Ao vivo:

- SOL: `data/prices.jsonl` recebe marcas do sol_bot (15 s) e do rules_bot (30 s) — ~1 marca a cada 10,4 s (medido no
  run ao vivo). Aqui: grelha de 10 s de último preço (Binance 1 s), ou seja janelas de 30 s / 190 s / 790 s.
- Memecoins: o histórico em memória do meme_bot recebe uma marca por ciclo (~60 s) para todas as moedas. Aqui: fecho
  de cada minuto.
- `depth`/`fees` vêm do impacto de preço das marcas; ao vivo as marcas (Coinbase, Gate.io) têm impacto 0, e todos os
  estados registados no run ao vivo começam por "deep quiet". Mantém-se esse valor constante (é o comportamento ao vivo,
  não uma aproximação). A hora (palavras early/mid/late/night) usa o instante simulado em BRT.

As palavras 8 (textura, substituída pelo humor `buoyed`/`stung` depois de uma venda) e 12 (posição) dependem do
portfólio dono do estado; `compose()` junta-as à parte de mercado.

Bot real (jev_trader.state): 16 fechos de 1 m da Binance (15 completos + a vela em formação), via
`assemble_features`/`build_state` do próprio bot. Profundidade, spread, taxas e inventário vêm de fontes ao vivo sem
histórico público; no run ao vivo ficaram em `deep`, `tight`, `quiet` e `sold` em > 99,9% dos ciclos — mantêm-se
constantes.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np

BRT = timezone(timedelta(hours=-3))
SOL_SAMPLE_S = 10


def ffill(a: np.ndarray) -> np.ndarray:
    a = a.astype(float).copy()
    idx = np.where(~np.isnan(a), np.arange(len(a)), 0)
    np.maximum.accumulate(idx, out=idx)
    out = a[idx]
    return out


def _tod(hour: int) -> str:
    return "early" if 5 <= hour < 11 else ("mid" if 11 <= hour < 17 else ("late" if 17 <= hour < 22 else "night"))


def market_words(prices: list[float], now_ts: float) -> tuple:
    """Parte de mercado do estado (sem humor/posição), a mesma conta de bot/lib.build_state, com hora simulada.
    Devolve (depth, fees, move, volw, tod, color, rng, texture, phase, "mid", loud)."""
    if len(prices) < 2:
        return ("deep", "quiet", "flat", "calm", "early", "gray", "wide", "soft", "early", "mid", "quiet")

    def pct(a, b):
        return 0.0 if b == 0 else (a - b) / b * 100

    p0 = prices[-1]; ps = prices[-min(4, len(prices))]; pm = prices[-min(20, len(prices))]; pl = prices[-min(80, len(prices))]
    rs, rm, rl = pct(p0, ps), pct(p0, pm), pct(p0, pl)
    win = prices[-min(20, len(prices)):]
    rets = [pct(win[i], win[i - 1]) for i in range(1, len(win))]
    vol = 0.0
    if len(rets) >= 2:
        m = sum(rets) / len(rets)
        vol = math.sqrt(sum((r - m) ** 2 for r in rets) / len(rets))
    lo, hi = min(win), max(win)
    pos = (p0 - lo) / (hi - lo) if hi > lo else 0.5
    depth, fees = "deep", "quiet"
    move = ("pumping" if rm >= 0.35 else "lifting" if rm >= 0.12 else "dumping" if rm <= -0.35 else "fading" if rm <= -0.12
            else "whipping" if abs(rs) >= 0.15 and abs(rm) < 0.12 else "flat")
    volw = "violent" if vol >= 0.25 else ("jumpy" if vol >= 0.10 else "calm")
    tod = _tod(datetime.fromtimestamp(now_ts, tz=BRT).hour)
    color = "green" if rl >= 0.2 else ("red" if rl <= -0.2 else "gray")
    rng = "tight" if pos >= 0.75 else "wide"
    tex = "harsh" if abs(rs) > abs(rm) * 1.5 and abs(rs) > 0.08 else "soft"
    phase = "early" if tod == "early" else ("late" if tod in ("late", "night") else "mid")
    loud = "loud" if vol >= 0.2 or fees == "bot_war" else "quiet"
    return (depth, fees, move, volw, tod, color, rng, tex, phase, "mid", loud)


def compose(mk: tuple, position: str, mood: str) -> str:
    """Estado final igual ao de bot/lib.build_state: humor (se não neutro) substitui a textura; posição no fim."""
    posw = position if position in ("held", "flat", "sold", "bare") else "flat"
    moodw = "".join(c for c in (mood or "neutral") if c.isalpha()) or "neutral"
    words = list(mk)
    if moodw not in ("neutral", "flat"):
        words[7] = moodw
    return " ".join(words + [posw])


class MarketStates:
    """Parte de mercado por instante de decisão, com cache. `series(t, n)` devolve as últimas n amostras até t."""

    def __init__(self, sample_fn):
        self.sample_fn = sample_fn
        self.cache: dict = {}

    def at(self, t: int) -> tuple | None:
        hit = self.cache.get(t)
        if hit is not None:
            return hit
        pr = self.sample_fn(t, 80)
        if pr is None or len(pr) == 0 or np.isnan(pr[-1]):
            return None
        pr = [float(x) for x in pr if not np.isnan(x)]
        mk = market_words(pr, t)
        self.cache[t] = mk
        return mk


def sol_sampler(grid_t: np.ndarray, grid_px: np.ndarray, sample_s: int = SOL_SAMPLE_S):
    """Amostras de `sample_s` em `sample_s` segundos (último preço da grelha) terminando em t."""
    px = ffill(grid_px)
    g0 = int(grid_t[0]); gs = int(grid_t[1] - grid_t[0])
    stride = max(1, sample_s // gs)

    def f(t, n):
        i = (int(t) - g0) // gs
        if i < 0 or i >= len(px):
            return None
        lo = i - stride * (n - 1)
        idx = np.arange(max(lo, i % stride), i + 1, stride)
        return px[idx]
    return f


def minute_sampler(ms):
    """Fechos de minuto (MinuteSeries) terminando no instante t (vela que começa em t − 60)."""
    def f(t, n):
        i = ms.idx_at(t)
        if i < 0 or i >= len(ms.c):
            return None
        return ms.c[max(0, i - n + 1): i + 1]
    return f


# ------------------------------------------------------------------ bot real

REAL_SOL_UI = 0.017392206
REAL_USDT_UI = 50.00929


def realbot_state(grid_t: np.ndarray, grid_px_ff: np.ndarray, t: int):
    """(estado, px_in) do bot real no instante t: 15 velas de 1 m completas + a vela em formação (Binance)."""
    from jev_trader.state import assemble_features, build_state
    g0 = int(grid_t[0]); gs = int(grid_t[1] - grid_t[0])
    m = int(t) // 60 * 60
    pts = [m - 60 * k for k in range(14, -1, -1)]          # fim das 15 velas completas (= início da seguinte)
    idx = [(p - g0) // gs for p in pts] + [(int(t) - g0) // gs]
    if min(idx) < 0 or max(idx) >= len(grid_px_ff):
        return None, None
    prices = [float(grid_px_ff[i]) for i in idx]
    if any(np.isnan(prices)):
        return None, None
    f = assemble_features(slippage_1k=0.0001, fee_ratio=1.0, prices_1m=prices, spread=0.0001,
                          sol_ui=REAL_SOL_UI, usdt_ui=REAL_USDT_UI, px_fallback=None, sources=("backtest",))
    return build_state(f), f.px_in
