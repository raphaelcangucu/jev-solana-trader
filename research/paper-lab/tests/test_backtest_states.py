"""Backtest: reconstrução do estado de 12 adjetivos (igual a bot/lib.build_state) e amostragem das séries."""
from __future__ import annotations

import random
from datetime import datetime

import numpy as np

import bot.lib as L
from backtest import data as D
from backtest import states as ST
from backtest.simenv import BRT


def _lib_state(prices, position, mood, ts, monkeypatch):
    monkeypatch.setattr(L, "brt_now", lambda: datetime.fromtimestamp(ts, tz=BRT))
    hist = [{"price_usd": p, "price_impact_pct": 0.0} for p in prices]
    return L.build_state(hist, position, mood)["state"]


def test_market_words_compose_equals_live_build_state(monkeypatch):
    rng = random.Random(7)
    base_ts = int(datetime.fromisoformat("2026-10-02T00:00:00-03:00").timestamp())
    for k in range(400):
        n = rng.choice([2, 3, 5, 20, 21, 79, 80, 120])
        vol = rng.choice([0.0002, 0.001, 0.004])
        p = [100.0]
        for _ in range(n - 1):
            p.append(p[-1] * (1 + rng.gauss(0, vol)))
        ts = base_ts + rng.randrange(0, 86400)
        pos = rng.choice(["held", "flat", "sold"])
        mood = rng.choice(["neutral", "buoyed", "stung"])
        mine = ST.compose(ST.market_words(p, ts), pos, mood)
        assert mine == _lib_state(p, pos, mood, ts, monkeypatch), (k, p[-3:], pos, mood)


def test_sol_sampler_every_10s_from_5s_grid():
    g = np.arange(0, 2000, 5)
    px = g.astype(float)          # preço = instante (fácil de ler)
    f = ST.sol_sampler(g, px, sample_s=10)
    s = f(1000, 80)
    assert len(s) == 80 and s[-1] == 1000 and s[-2] == 990 and s[0] == 1000 - 790
    s = f(30, 80)                 # início da série: só o que existe, mesma fase
    assert list(s) == [0.0, 10.0, 20.0, 30.0]


def test_minute_sampler_uses_last_closed_candle():
    t0 = 1_000_020 // 60 * 60
    rows = [(t0 + 60 * i, 1.0, 1.0, 1.0, float(i), 0.0) for i in range(100)]
    ms = D.MinuteSeries(rows, t0, t0 + 6000)
    f = ST.minute_sampler(ms)
    s = f(t0 + 600, 4)            # instante t0+600: vela fechada mais recente começa em t0+540 (i=9)
    assert list(s) == [6.0, 7.0, 8.0, 9.0]


def test_minute_series_ffill_short_gaps_only():
    t0 = 6_000_000
    rows = [(t0 + 60 * i, 1, 1, 1, 10.0 + i, 0) for i in range(30) if not (5 <= i < 8) and not (15 <= i < 25)]
    ms = D.MinuteSeries(rows, t0, t0 + 30 * 60)
    assert ms.c[5] == ms.c[7] == 14.0            # lacuna de 3 min preenchida com o último fecho
    assert np.isnan(ms.c[21]) and ms.c[15] == 24.0   # lacuna de 10 min: só os primeiros 5 min
    cov = D.coverage(rows, t0, t0 + 30 * 60)
    assert cov["missing"] == 13 and cov["gaps"] == 2 and cov["max_gap_min"] == 10 and cov["gaps_gt_ffill"] == 1


def test_realbot_state_reuses_bot_assembly():
    g = np.arange(0, 3600, 5)
    px = 100.0 + g / 3600.0 * 1.0      # +1% numa hora: retorno de 15 min ≈ +0,25% → gray
    st, p = ST.realbot_state(g, px, 3000)
    assert p == px[3000 // 5]
    w = st.split()
    assert len(w) == 12 and w[0] == "deep" and w[6] == "tight" and w[11] == "sold" and w[5] == "gray"
    px2 = 100.0 + (g >= 2500) * 1.0    # salto de +1% → green
    assert ST.realbot_state(g, px2, 3000)[0].split()[5] == "green"
