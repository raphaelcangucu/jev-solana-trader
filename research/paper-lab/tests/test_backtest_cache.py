"""Backtest: cache das respostas dos modelos (uma chamada por critérios+estado), fail-closed e teto do Jev."""
from __future__ import annotations

import json
from pathlib import Path

from backtest import models as M

CRIT = {"action": {"instructions": "buy on strength", "criteria": {"buy": "a", "sell": "b", "hold": "c"}},
        "skip_this_cycle": {"instructions": "skip"}}


def _fake_http(calls, fail_states=()):
    def f(base, state, criteria, timeout, model_id, extra_headers=None, model_name=None):
        calls.append((base, state, model_name))
        assert ":8765" not in base and ":8766" not in base and ":8767" not in base   # nunca as portas do run ao vivo
        if state in fail_states:
            return {"ok": False, "fail_closed": True, "chosen_action": "hold", "error": "boom"}
        return {"ok": True, "fail_closed": False, "chosen_action": "buy", "probabilities": {"buy": 0.6, "sell": 0.3, "hold": 0.1},
                "confidence": 0.4, "skip_noul": 0.1}
    return f


def test_cache_one_call_per_state_and_persists(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(M.BK, "call_http_systemone", _fake_http(calls))
    monkeypatch.setattr(M.time, "sleep", lambda s: None)
    c = M.ModelClient(M.ModelCache(tmp_path / "a.sqlite"))
    c.register("b", CRIT)
    r1 = c.get("von", "b", "deep quiet flat")
    r2 = c.get("von", "b", "deep quiet flat")
    assert r1["chosen_action"] == r2["chosen_action"] == "buy" and len(calls) == 1
    assert calls[0][0] == "http://127.0.0.1:8865"
    c.cache.commit()
    # nova instância lê do disco: zero chamadas
    c2 = M.ModelClient(M.ModelCache(tmp_path / "a.sqlite"))
    c2.register("b", CRIT)
    assert c2.get("von", "b", "deep quiet flat")["confidence"] == 0.4 and len(calls) == 1
    assert c2.stats["von"]["cache_hits"] == 1 and c2.stats["von"]["calls"] == 0
    # outro modelo ou critérios diferentes → outra chave
    c2.get("laya", "b", "deep quiet flat")
    c2.register("v2", dict(CRIT, skip_this_cycle={"instructions": "other"}))
    c2.get("von", "v2", "deep quiet flat")
    assert len(calls) == 3


def test_model_field_changes_key_and_failures_are_not_cached(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(M.BK, "call_http_systemone", _fake_http(calls, fail_states={"bad"}))
    monkeypatch.setattr(M.time, "sleep", lambda s: None)
    c = M.ModelClient(M.ModelCache(tmp_path / "b.sqlite"))
    sha_a = c.register("a", CRIT)
    sha_b = c.register("rb", CRIT, model_field="von-latest")
    assert sha_a != sha_b
    c.get("von", "rb", "s")
    assert calls[-1][2] == "von-latest"
    r = c.get("von", "a", "bad")
    assert r["fail_closed"] and r["chosen_action"] == "hold" and r["skip_noul"] == 1.0
    n = len(calls)
    c.get("von", "a", "bad")
    assert len(calls) > n            # falhas nunca entram na cache


def test_prefetch_parallel_and_jev_budget(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(M.BK, "call_http_systemone", _fake_http(calls))

    def fake_jev(cfg, state, criteria, timeout):
        calls.append(("jev", state, None))
        return {"ok": True, "chosen_action": "sell", "probabilities": {"sell": 0.9}, "confidence": 0.8, "skip_noul": 0.0}
    monkeypatch.setattr(M.BK, "call_hosted_jev", fake_jev)
    c = M.ModelClient(M.ModelCache(tmp_path / "c.sqlite"), jev_max_calls=3)
    c.register("b", CRIT)
    r = c.prefetch([("von", "b", f"s{i}") for i in range(20)] + [("von", "b", "s1")])
    assert r["todo"] == 20 and r["ok"] == 20
    r = c.prefetch([("jev", "b", f"j{i}") for i in range(10)])
    assert c.stats["jev"]["calls"] == 3 and c.jev_budget_hit
    assert c.get("jev", "b", "j9")["fail_closed"]          # acima do teto → hold
    assert c.get("jev", "b", "j0")["chosen_action"] in ("sell", "hold")


def test_load_secrets_never_returns_values(tmp_path, monkeypatch):
    p = tmp_path / "s.env"
    p.write_text("JEV_API_KEY=abc123secret\n# comment\n")
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    names = M.load_secrets(p)
    assert names == ["JEV_API_KEY"] and "abc123secret" not in json.dumps(names)
    import os
    assert os.environ["JEV_API_KEY"] == "abc123secret"
    monkeypatch.delenv("JEV_API_KEY", raising=False)
