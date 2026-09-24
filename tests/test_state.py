from dataclasses import replace

from jev_trader.state import (
    MarketFeatures,
    adjective_slots,
    assemble_features,
    build_state,
    fee_ratio_from_micro_lamports,
    neutral_features,
)


def test_neutral_state_is_twelve_adjectives_without_digits():
    text = build_state(neutral_features())
    assert text == "thin quiet flat calm flat gray wide calm mid mid quiet held"
    assert len(text.split()) == 12
    assert not any(character.isdigit() for character in text)


def test_article_thresholds_flip_the_core_words():
    base = neutral_features()
    deep = replace(base, slippage_1k=0.006, spread=0.0)
    thin = replace(base, slippage_1k=0.0061, spread=0.0)
    assert adjective_slots(deep)[0] == "deep"
    assert adjective_slots(thin)[0] == "thin"

    quiet = replace(base, fee_ratio=2.5)
    war = replace(base, fee_ratio=2.5001)
    assert adjective_slots(quiet)[1] == "quiet"
    assert adjective_slots(war)[1] == "bot_war"

    flat = replace(base, return_15m=0.02)
    pumping = replace(base, return_15m=0.0201)
    fading = replace(base, return_15m=-0.05)
    dumping = replace(base, return_15m=-0.0501)
    assert adjective_slots(flat)[2] == "flat"
    assert adjective_slots(pumping)[2] == "pumping"
    assert adjective_slots(fading)[2] == "fading"
    assert adjective_slots(dumping)[2] == "dumping"

    calm = replace(base, stdev=0.008)
    violent = replace(base, stdev=0.0081)
    assert adjective_slots(calm)[3] == "calm"
    assert adjective_slots(violent)[3] == "violent"


def test_extreme_numbers_never_enter_the_model_text():
    wild = MarketFeatures(
        slippage_1k=12.345,
        fee_ratio=99.9,
        return_15m=-0.42,
        stdev=1.7,
        spread=3.14,
        position_in_range=-0.2,
        inventory_bias=-0.8,
        inventory_empty=False,
        px_in=123.456,
        px_15m=99.0,
    )
    text = build_state(wild)
    words = text.split()
    assert words[0] == "thin"
    assert words[1] == "bot_war"
    assert words[2] == "dumping"
    assert words[3] == "violent"
    assert words[-1] == "sold"
    assert len(words) == 12
    assert not any(character.isdigit() for character in text)
    assert all(token.isidentifier() or "_" in token for token in words)


def test_inventory_and_unknown_depth():
    empty = replace(neutral_features(), inventory_empty=True, inventory_bias=0.9, slippage_1k=0.0, spread=0.0)
    assert adjective_slots(empty)[-1] == "bare"
    unknown = replace(neutral_features(), slippage_1k=None, spread=None)
    slots = adjective_slots(unknown)
    assert slots[0] == "thin"
    assert slots[6] == "wide"


def test_assemble_uses_the_fifteen_minute_tape_not_the_raw_text():
    features = assemble_features(
        slippage_1k=0.0,
        fee_ratio=1.0,
        prices_1m=[100.0, 100.0, 103.0],
        spread=0.0001,
        sol_ui=0.017392206,
        usdt_ui=50.00929,
        px_fallback=None,
    )
    assert features.px_in == 103.0
    assert features.px_15m == 100.0
    assert abs(features.return_15m - 0.03) < 1e-12
    assert adjective_slots(features)[2] == "pumping"
    assert adjective_slots(features)[-1] == "sold"
    assert not any(character.isdigit() for character in build_state(features))


def test_fee_ratio_median_against_quiet_baseline():
    assert fee_ratio_from_micro_lamports([]) == 1.0
    assert fee_ratio_from_micro_lamports([0, 1000, 5000]) == 1.0
    assert fee_ratio_from_micro_lamports([3000, 3000, 9000]) == 3.0
