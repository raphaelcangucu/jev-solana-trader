"""Build ~12 adjective words from price history. No digits in state text."""
from __future__ import annotations
import math, time
from datetime import datetime, timezone, timedelta
from typing import Any

BRT = timezone(timedelta(hours=-3))

def _pct(a: float, b: float) -> float:
    if b == 0: return 0.0
    return (a - b) / b * 100.0

def build_state(history: list[dict], position: str, recent_pnl_mood: str, now_ts: float | None = None) -> dict[str, Any]:
    now_ts = now_ts or time.time()
    prices = [float(h["price_usd"]) for h in history if h.get("price_usd") is not None]
    impacts = [float(h.get("price_impact_pct") or 0) for h in history]
    if len(prices) < 2:
        words = ["deep","quiet","flat","calm","early","gray","wide","soft","early","mid","quiet", position or "flat"]
        return {"state": " ".join(words[:12]), "features": {"insufficient_history": True}, "words": words[:12]}

    short_n, med_n, long_n = 4, 20, 80
    p0 = prices[-1]
    p_s = prices[-min(short_n, len(prices))]
    p_m = prices[-min(med_n, len(prices))]
    p_l = prices[-min(long_n, len(prices))]
    ret_s, ret_m, ret_l = _pct(p0, p_s), _pct(p0, p_m), _pct(p0, p_l)
    window = prices[-min(med_n, len(prices)):]
    rets = [_pct(window[i], window[i-1]) for i in range(1, len(window))]
    if len(rets) >= 2:
        mean = sum(rets)/len(rets)
        vol = math.sqrt(sum((r-mean)**2 for r in rets)/len(rets))
    else:
        vol = 0.0
    lo, hi = min(window), max(window)
    pos = (p0 - lo) / (hi - lo) if hi > lo else 0.5
    impact = impacts[-1] if impacts else 0.0
    impact_avg = sum(impacts[-min(10,len(impacts)):]) / max(1, min(10, len(impacts)))

    depth = "deep" if impact_avg < 0.05 else ("okay" if impact_avg < 0.25 else "thin")
    fees = "quiet" if impact < 0.05 and impact_avg < 0.1 else ("mild" if impact < 0.3 else "bot_war")
    if ret_m >= 0.35: move = "pumping"
    elif ret_m >= 0.12: move = "lifting"
    elif ret_m <= -0.35: move = "dumping"
    elif ret_m <= -0.12: move = "fading"
    elif abs(ret_s) >= 0.15 and abs(ret_m) < 0.12: move = "whipping"
    else: move = "flat"
    vol_w = "violent" if vol >= 0.25 else ("jumpy" if vol >= 0.10 else "calm")
    hour = datetime.fromtimestamp(now_ts, tz=BRT).hour
    tod = "early" if 5 <= hour < 11 else ("mid" if 11 <= hour < 17 else ("late" if 17 <= hour < 22 else "night"))
    color = "green" if ret_l >= 0.2 else ("red" if ret_l <= -0.2 else "gray")
    rng_w = "tight" if pos >= 0.75 else ("wide" if pos <= 0.25 else "wide")
    texture = "harsh" if abs(ret_s) > abs(ret_m)*1.5 and abs(ret_s) > 0.08 else "soft"
    phase = "early" if tod == "early" else ("late" if tod in ("late","night") else "mid")
    loud = "loud" if vol >= 0.2 or fees == "bot_war" else "quiet"
    pos_w = position if position in ("held","flat","sold","bare") else "flat"
    mood = "".join(c for c in (recent_pnl_mood or "neutral") if c.isalpha()) or "neutral"
    words = [depth, fees, move, vol_w, tod, color, rng_w, mood if mood not in ("neutral","flat") else texture, phase, "mid", loud, pos_w]
    state = " ".join(words)
    if any(ch.isdigit() for ch in state):
        state = " ".join("".join(ch for ch in state if not ch.isdigit()).split())
    features = {
        "ret_short_pct": round(ret_s,4), "ret_med_pct": round(ret_m,4), "ret_long_pct": round(ret_l,4),
        "vol_pct": round(vol,4), "range_pos": round(pos,4), "impact_last": round(impact,6),
        "impact_avg": round(impact_avg,6), "hour_brt": hour, "n_prices": len(prices), "price": round(p0,8),
    }
    return {"state": state, "features": features, "words": words}
