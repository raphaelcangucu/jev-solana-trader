"""bot/state.py: estado em ~12 adjetivos, sem dígitos, determinístico com now_ts."""
from datetime import datetime

from bot.state import build_state, BRT

T_NIGHT = datetime(2026, 9, 26, 2, 0, tzinfo=BRT).timestamp()
T_MID = datetime(2026, 9, 26, 13, 0, tzinfo=BRT).timestamp()


def hist(prices, impact=0.0):
    return [{"price_usd": p, "price_impact_pct": impact} for p in prices]


def test_short_history_is_neutral_and_flagged():
    st = build_state(hist([100.0]), "held", "neutral", now_ts=T_NIGHT)
    assert len(st["words"]) == 12 and st["features"]["insufficient_history"] is True
    assert st["words"][-1] == "held"


def test_twelve_words_no_digits():
    prices = [100 + (i % 7) * 0.13 for i in range(120)]
    st = build_state(hist(prices), "flat", "neutral", now_ts=T_MID)
    assert len(st["state"].split()) == 12
    assert not any(ch.isdigit() for ch in st["state"])
    assert st["words"][4] == "mid"  # 13h BRT


def test_pumping_green_and_dumping_red():
    up = build_state(hist([100 * (1.0005 ** i) for i in range(100)]), "held", "neutral", now_ts=T_NIGHT)
    assert up["words"][2] == "pumping" and up["words"][5] == "green" and up["words"][4] == "night"
    down = build_state(hist([100 * (0.9995 ** i) for i in range(100)]), "flat", "neutral", now_ts=T_NIGHT)
    assert down["words"][2] == "dumping" and down["words"][5] == "red"


def test_flat_calm_deep_quiet():
    st = build_state(hist([100.0] * 50), "held", "neutral", now_ts=T_NIGHT)
    w = st["words"]
    assert (w[0], w[1], w[2], w[3], w[5]) == ("deep", "quiet", "flat", "calm", "gray")


def test_thin_book_and_bot_war():
    st = build_state(hist([100.0] * 50, impact=0.5), "held", "neutral", now_ts=T_NIGHT)
    assert st["words"][0] == "thin" and st["words"][1] == "bot_war" and st["words"][10] == "loud"


def test_position_and_mood_words():
    st = build_state(hist([100.0] * 30), "levered", "stung", now_ts=T_NIGHT)
    assert st["words"][-1] == "flat"      # posição desconhecida vira flat
    assert st["words"][7] == "stung"      # humor substitui a textura
    st2 = build_state(hist([100.0] * 30), "sold", "mood_42!", now_ts=T_NIGHT)
    assert st2["words"][-1] == "sold" and not any(ch.isdigit() for ch in st2["state"])
