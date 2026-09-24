from jev_trader.decide import (
    ARTICLE_QUESTIONS,
    apply_thresholds,
    fail_closed,
    parse_system_one_payload,
    resolve_action,
)


ARTICLE_EXAMPLE = {
    "action": {
        "choice": "hold",
        "probabilities": {"buy": 0.11, "sell": 0.08, "hold": 0.81},
        "confidence": 0.81,
    },
    "skip_this_cycle": {"noul": 0.22},
}


def test_article_criteria_strings():
    action = ARTICLE_QUESTIONS["action"]
    assert action["criteria"]["buy"] == "the move is strong and depth is not thin"
    assert action["criteria"]["sell"] == "the move is fading or fees are climbing"
    assert action["criteria"]["hold"] == "anything else"
    assert ARTICLE_QUESTIONS["skip_this_cycle"]["instructions"] == (
        "conditions are too hostile to trade at all"
    )


def test_parse_article_example_flat_and_wrapped():
    flat = parse_system_one_payload(ARTICLE_EXAMPLE, source="test")
    wrapped = parse_system_one_payload({"answers": ARTICLE_EXAMPLE}, source="test")
    assert flat.ok and wrapped.ok
    assert flat.choice == "hold"
    assert flat.confidence == 0.81
    assert flat.skip_noul == 0.22
    assert wrapped.probabilities["hold"] == 0.81


def test_incomplete_or_out_of_range_payload_fails_closed():
    missing = parse_system_one_payload({"action": {"choice": "buy"}}, source="test")
    assert missing.ok is False
    assert missing.choice == "hold"
    assert missing.skip_noul == 1.0
    scaled = parse_system_one_payload(
        {
            "action": {"choice": "buy", "confidence": 81},
            "skip_this_cycle": {"noul": 0.1},
        },
        source="test",
    )
    assert scaled.ok is False


def test_skip_and_confidence_boundaries():
    skipped = apply_thresholds("buy", 0.9, 0.55, confidence_min=0.55, skip_min=0.55)
    assert skipped == skipped.__class__("hold", "skip", False)

    acted = apply_thresholds("buy", 0.55, 0.5499, confidence_min=0.55, skip_min=0.55)
    assert acted.action == "buy"
    assert acted.reason == "execute"
    assert acted.execute is True

    low = apply_thresholds("sell", 0.5499, 0.0, confidence_min=0.55, skip_min=0.55)
    assert low.reason == "low_confidence"
    assert low.execute is False

    hold = apply_thresholds("hold", 0.81, 0.22, confidence_min=0.55, skip_min=0.55)
    assert hold.reason == "model_hold"
    assert hold.execute is False

    sold = apply_thresholds("sell", 0.8, 0.1, confidence_min=0.55, skip_min=0.55)
    assert sold.action == "sell" and sold.execute is True


def test_resolve_prefers_fail_closed_then_missing_market():
    down = fail_closed("von unavailable")
    gated = resolve_action(down, market_ok=False, confidence_min=0.55, skip_min=0.55)
    assert gated.action == "hold"
    assert gated.reason == "fail_closed"
    assert gated.execute is False

    live_model = parse_system_one_payload(
        {
            "action": {"choice": "buy", "confidence": 0.9, "probabilities": {"buy": 0.9}},
            "skip_this_cycle": {"noul": 0.1},
        },
        source="test",
    )
    blinded = resolve_action(live_model, market_ok=False, confidence_min=0.55, skip_min=0.55)
    assert blinded.reason == "market_unavailable"
    assert blinded.execute is False
