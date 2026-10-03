"""Perfis de parâmetros do bot real (config/params.json) e o portão de margem de probabilidade."""

import json
from pathlib import Path

import pytest

from jev_trader import config as C
from jev_trader.decide import ModelAnswer, apply_thresholds, prob_margin, resolve_action

ROOT = Path(__file__).resolve().parents[1]
ENV_KEYS = ["PARAMS_PATH", "PARAMS_PROFILE", "LIVE_TRADING", *C.PARAM_ENV.values()]


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PARAMS_PATH", str(ROOT / "config" / "params.json"))
    return tmp_path / "no.env"  # .env inexistente: nada é carregado


def test_default_profile_is_relaxed_paper(clean_env):
    cfg = C.load_config(clean_env)
    assert cfg.params_profile == "relaxed_paper" and cfg.params_errors == ()
    assert (cfg.confidence_min, cfg.skip_min, cfg.prob_margin_min) == (0.35, 0.5, 0.2)
    assert (cfg.buy_usdt, cfg.sell_sol, cfg.max_buy_usdt, cfg.max_sell_sol) == (1.0, 0.005, 5.0, 0.01)
    assert (cfg.loop_seconds, cfg.paper_cost_bps) == (15.0, 10.0)


def test_article_profile(clean_env, monkeypatch):
    monkeypatch.setenv("PARAMS_PROFILE", "article")
    cfg = C.load_config(clean_env)
    assert cfg.params_profile == "article"
    assert (cfg.confidence_min, cfg.skip_min, cfg.prob_margin_min) == (0.55, 0.55, 0.0)


def test_env_vars_still_override(clean_env, monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.42")
    monkeypatch.setenv("PROB_MARGIN_MIN", "0")
    monkeypatch.setenv("BUY_USDT", "2")
    cfg = C.load_config(clean_env)
    assert cfg.params_profile == "relaxed_paper"
    assert cfg.confidence_min == 0.42 and cfg.prob_margin_min == 0.0 and cfg.buy_usdt == 2.0
    assert cfg.skip_min == 0.5  # o resto continua do perfil


def test_paper_only_profile_never_goes_live(clean_env, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "1")
    cfg = C.load_config(clean_env)
    assert cfg.live_trading and cfg.params_profile == "article"
    assert cfg.confidence_min == 0.55 and cfg.prob_margin_min == 0.0
    assert any("só paper" in e for e in cfg.params_errors)


def test_bad_file_or_profile_fails_safe_to_article(clean_env, monkeypatch, tmp_path):
    monkeypatch.setenv("PARAMS_PROFILE", "nope")
    cfg = C.load_config(clean_env)
    assert cfg.params_profile == "article" and cfg.confidence_min == 0.55
    bad = tmp_path / "params.json"
    bad.write_text(json.dumps({"defaults": {"gates": {"confidence_min": 7}}, "profiles": {"relaxed_paper": {}}}))
    monkeypatch.setenv("PARAMS_PATH", str(bad))
    monkeypatch.delenv("PARAMS_PROFILE")
    cfg = C.load_config(clean_env)
    assert cfg.params_profile == "article" and cfg.confidence_min == 0.55 and cfg.params_errors
    bad.write_text("{not json")
    assert C.load_config(clean_env).confidence_min == 0.55
    monkeypatch.setenv("PARAMS_PATH", str(tmp_path / "missing.json"))
    assert C.load_config(clean_env).params_profile == "article"


def test_unknown_keys_are_errors(tmp_path):
    p = tmp_path / "params.json"
    p.write_text(json.dumps({"defaults": {"gates": {"confidense_min": 0.3}}, "profiles": {"x": {}}}))
    values, used, errors = C.load_params(p, "x")
    assert used == "article" and values == C.ARTICLE_PARAMS and any("confidense_min" in e for e in errors)


def test_margin_gate_only_when_configured():
    probs = {"buy": 0.5, "sell": 0.35, "hold": 0.15}  # margem 0.15
    assert prob_margin(probs) == pytest.approx(0.15) and prob_margin({}) is None
    g = apply_thresholds("buy", 0.4, 0.1, confidence_min=0.35, skip_min=0.5, probabilities=probs)
    assert g.execute  # sem margem configurada, comportamento antigo
    g = apply_thresholds("buy", 0.4, 0.1, confidence_min=0.35, skip_min=0.5, prob_margin_min=0.2, probabilities=probs)
    assert (g.action, g.reason, g.execute) == ("hold", "low_prob_margin", False)
    wide = {"buy": 0.6, "sell": 0.3, "hold": 0.1}
    g = apply_thresholds("buy", 0.4, 0.1, confidence_min=0.35, skip_min=0.5, prob_margin_min=0.2, probabilities=wide)
    assert g.execute and g.action == "buy"
    # margem exigida sem probabilidades: fail-closed
    g = apply_thresholds("sell", 0.9, 0.1, confidence_min=0.35, skip_min=0.5, prob_margin_min=0.2, probabilities=None)
    assert g.reason == "low_prob_margin"
    # skip e confiança continuam a vir antes
    assert apply_thresholds("buy", 0.3, 0.1, confidence_min=0.35, skip_min=0.5, prob_margin_min=0.2,
                            probabilities=wide).reason == "low_confidence"
    assert apply_thresholds("buy", 0.9, 0.5, confidence_min=0.35, skip_min=0.5, prob_margin_min=0.2,
                            probabilities=wide).reason == "skip"


def test_resolve_action_relaxed_paper_gate():
    m = ModelAnswer(ok=True, choice="buy", confidence=0.38, skip_noul=0.2,
                    probabilities={"buy": 0.38, "hold": 0.33, "sell": 0.29}, source="t")
    assert resolve_action(m, market_ok=True, confidence_min=0.55, skip_min=0.55).reason == "low_confidence"
    assert resolve_action(m, market_ok=True, confidence_min=0.35, skip_min=0.5, prob_margin_min=0.2).reason == "low_prob_margin"
    m2 = ModelAnswer(ok=True, choice="buy", confidence=0.38, skip_noul=0.2,
                     probabilities={"buy": 0.62, "hold": 0.2, "sell": 0.18}, source="t")
    assert resolve_action(m2, market_ok=True, confidence_min=0.35, skip_min=0.5, prob_margin_min=0.2).execute


def test_repo_params_file_is_valid():
    doc = json.loads((ROOT / "config" / "params.json").read_text())
    for name in doc["profiles"]:
        values, used, errors = C.load_params(ROOT / "config" / "params.json", name)
        assert used == name and errors == []
