"""bot/params.py: parâmetros por tipo de teste (camadas, proveniência, validação, fail-closed, hot reload),
equivalência com os valores usados antes de params.json, forks, tuner por tipo e ajudas dos bots."""
import copy
import json
import os
import time
from pathlib import Path

import pytest

from bot import lab_registry as R
from bot import lib
from bot import params as P

LAB = Path(__file__).resolve().parents[1]
DOC = json.loads((LAB / "params.json").read_text())
CFG = json.loads((LAB / "config.json").read_text())

BASE_G = {"min_confidence": 0.6, "min_prob_margin": 0.0, "margin_gate": False, "max_skip_noul": 0.5,
          "cooldown_seconds": 120, "max_trades_per_hour": 8, "buy_fraction_usdt": 0.25, "min_usdt_trade": 1.0,
          "min_sol_trade": 0.001, "max_exposure_frac": None}
REL_G = dict(BASE_G, min_confidence=0.35, min_prob_margin=0.2, margin_gate=True)
MARKET = {"mode": "market", "extra_slippage_bps": 5, "slippage_bps": 50, "network_fee_sol": 5e-06,
          "offset_bps": 10, "ttl_min": 15, "fee_bps": 10}
EXITS_SOL = {"enabled": True, "tp": 0.025, "sl": 0.015, "trail": 0.01, "trail_arm": 0.01, "reentry_cooldown_min": 30}
OFF = {"enabled": False, "require_bull_for_buy": True, "block_if_unknown": True}
EMPTY_REG = {"portfolios": {}, "lineages": {}}


def eff_of(name, reg=EMPTY_REG, overlay=None, meta=None, doc=DOC):
    m = P.classify(name, entry=meta, registry=reg)
    assert m is not None, name
    eff, prov, errs = P.resolve(m, doc, overlay, reg)
    errs = errs + P.validate(eff, m)
    return eff, prov, errs, m


# ------------------------------------------------------------ equivalência com o comportamento anterior

EXPECTED = {
    # nome: (tipo, gates, overrides do resto)
    "baseline": ("model_gated", BASE_G, {}),
    "relaxed": ("model_gated", REL_G, {}),
    "v2": ("model_gated", REL_G, {}),
    "hybrid_von_relaxed_cap2": ("hybrid", dict(REL_G, max_trades_per_hour=2), {"regime_filter": dict(OFF, enabled=True)}),
    "poorjev_relaxed": ("model_gated", REL_G, {}),
    "meme_WIF_relaxed": ("model_gated", REL_G, {}),
    "WIF_poorjev_baseline": ("model_gated", BASE_G, {}),
    "grid_sol_2pct": ("rule_grid", BASE_G, {"rule": {"grid_pct": 0.02, "levels": 4, "timeframe": "1h"}}),
    "rsi_sol_1h": ("rule_rsi", BASE_G, {"rule": {"rsi_period": 14, "lo": 30, "hi": 70, "timeframe": "1h"}}),
    "BONK_rule_regime_full": ("rule_regime", dict(BASE_G, buy_fraction_usdt=1.0),
                              {"rule": {"ema_fast": 12, "ema_slow": 26, "timeframe": "1h"}}),
    "h1_exits_von_relaxed": ("lab_h1_exits", REL_G, {"exits": EXITS_SOL}),
    "h2_ensemble_sol": ("lab_h2_ensemble", BASE_G, {"ensemble": {"min_agree": 2, "pct_threshold": 0.8, "min_window": 100}}),
    "h3_limit_poorjev_relaxed": ("lab_h3_limit", REL_G, {"exec": dict(MARKET, mode="limit")}),
    "h4_hours_von_relaxed": ("lab_h4_hours", REL_G, {"hours": [5, 10, 11, 12, 18]}),
}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_resolved_values_match_previous_behaviour(name):
    tt, gates, rest = EXPECTED[name]
    eff, prov, errs, m = eff_of(name)
    assert errs == [] and m["test_type"] == tt
    assert eff["gates"] == gates
    assert eff["exec"] == rest.get("exec", MARKET)
    exits = rest.get("exits")
    assert eff["exits"]["enabled"] is bool(exits)
    if exits:
        assert eff["exits"] == exits
    assert eff["hours"] == rest.get("hours")
    assert eff["regime_filter"] == rest.get("regime_filter", OFF)
    assert eff.get("ensemble") == rest.get("ensemble")
    assert eff.get("rule") == rest.get("rule")
    assert eff["paused"] is False and eff["paper_only"] is True


def test_meme_h1_exit_levels_and_lab_hypotheses_match_archived_registry():
    arch = json.loads((LAB / "archive" / "run_1000usd_2026-09-24" / "data" / "lab" / "registry.json").read_text())
    for n, e in arch["portfolios"].items():
        eff, _p, errs, _m = eff_of(n, meta=None)
        assert errs == [], (n, errs)
        old = e["params"]
        if "exits" in old:
            assert {k: eff["exits"][k] for k in old["exits"]} == old["exits"] and eff["exits"]["enabled"]
        if "exec" in old:
            assert {k: eff["exec"][k] for k in old["exec"]} == old["exec"]
        if "hours" in old:
            assert eff["hours"] == old["hours"]
        if "ensemble" in old:
            assert eff["ensemble"] == old["ensemble"]
        for k, v in (old.get("gates") or {}).items():
            assert eff["gates"][k] == v
        prof_cfg = CFG["gates_relaxed"] if e["profile"] == "relaxed" else CFG["gates"]
        for k, v in prof_cfg.items():
            if k != "calibration_note" and k not in (old.get("gates") or {}):
                assert eff["gates"][k] == v, (n, k)


def test_gate_profiles_equal_config_json_and_fees_equal_config():
    for name, block in (("baseline", "gates"), ("relaxed", "gates_relaxed")):
        g = eff_of(name)[0]["gates"]
        for k, v in CFG[block].items():
            if k != "calibration_note":
                assert g[k] == v
    fees, market = P.fees_market(eff_of("relaxed")[0], CFG)
    assert fees == CFG["fees"] and market == CFG["market"]
    rs = CFG["rule_strategies"]["strategies"]
    assert eff_of("hybrid_von_relaxed_cap2")[0]["gates"]["max_trades_per_hour"] == rs["hybrid_von_relaxed_cap2"]["max_trades_per_hour"]
    assert eff_of("grid_sol_2pct")[0]["rule"]["grid_pct"] == rs["grid_sol_2pct"]["grid_pct"]
    r = eff_of("WIF_rule_donch_regime")[0]["rule"]
    assert (r["donchian"], r["ema_fast"], r["ema_slow"]) == (20, 12, 26)
    assert eff_of("WIF_rule_donch_regime")[0]["gates"]["buy_fraction_usdt"] == 0.25


def test_every_known_portfolio_resolves_without_errors():
    assert P.check_all(DOC, EMPTY_REG, {}) == {}
    names = P.all_names(EMPTY_REG)
    assert {"h1_exits_hybrid_von_cap2", "relaxed_expcap50", "BONK_rule_donch_regime_full"} <= set(names)


def test_provenance_names_the_layer():
    _e, prov, _errs, _m = eff_of("hybrid_von_relaxed_cap2")
    assert prov["gates.max_trades_per_hour"] == "portfolios.hybrid_von_relaxed_cap2"
    assert prov["gates.min_confidence"] == "profiles.relaxed"
    assert prov["gates.cooldown_seconds"] == "defaults"
    assert prov["regime_filter.enabled"] == "types.hybrid"
    _e, prov, _errs, _m = eff_of("v2")
    assert prov["gates.min_prob_margin"] == "profiles.relaxed"  # v2 extends relaxed
    _e, prov, _errs, _m = eff_of("h1_exits_GOAT_poorjev_relaxed")
    assert prov["exits.tp"] == "assets.meme" and prov["exits.enabled"] == "types.lab_h1_exits"
    _e, prov, _errs, _m = eff_of("BONK_rule_regime_full")
    assert prov["gates.buy_fraction_usdt"] == "types.rule_regime.variants.full"


# ------------------------------------------------------------ portfólios novos (passo 3 do HANDOFF)

def test_new_lab_portfolios_defined_by_params_only():
    defs = {h["name"]: h for h in R.hypothesis_defs()}
    for n in ("h1_exits_hybrid_von_cap2", "relaxed_expcap50"):
        assert n in defs and "params" not in defs[n]
    eff, _p, errs, m = eff_of("h1_exits_hybrid_von_cap2")
    assert errs == [] and m["runner"] == "lab_bot" and defs["h1_exits_hybrid_von_cap2"]["source"] == "hybrid_von_relaxed_cap2"
    assert eff["exits"] == EXITS_SOL and eff["gates"]["max_trades_per_hour"] == 2
    eff, _p, errs, _m = eff_of("relaxed_expcap50")
    assert errs == [] and eff["gates"] == dict(REL_G, max_exposure_frac=0.5)


# ------------------------------------------------------------ forks

def test_fork_resolves_parent_plus_diff_with_provenance():
    reg = {"portfolios": {
        "relaxed__fork1": {"name": "relaxed__fork1", "asset": "SOL", "cls": "sol", "kind": "gated", "source": "relaxed",
                           "profile": "relaxed", "model": "von", "test_type": "model_gated", "parent": "relaxed",
                           "lineage": "relaxed", "params_diff": {"gates": {"min_confidence": 0.4, "cooldown_seconds": 144}}},
        "relaxed__fork2": {"name": "relaxed__fork2", "asset": "SOL", "cls": "sol", "kind": "gated", "source": "relaxed",
                           "profile": "relaxed", "model": "von", "parent": "relaxed__fork1", "lineage": "relaxed",
                           "params_diff": {"exits": {"enabled": True}}},
    }, "lineages": {}}
    eff, prov, errs, m = eff_of("relaxed__fork1", reg)
    assert errs == [] and m["runner"] == "lab_bot"
    assert eff["gates"] == dict(REL_G, min_confidence=0.4, cooldown_seconds=144)
    assert prov["gates.min_confidence"] == "fork:relaxed__fork1" and prov["gates.min_prob_margin"] == "profiles.relaxed"
    # fork de fork: herda o diff do pai e acrescenta o seu (H1 aplicado ao relaxed é só params)
    eff2, prov2, errs2, _ = eff_of("relaxed__fork2", reg)
    assert errs2 == [] and eff2["gates"]["min_confidence"] == 0.4 and eff2["exits"] == EXITS_SOL
    assert prov2["exits.enabled"] == "fork:relaxed__fork2" and prov2["exits.tp"] == "assets.sol"
    # o overlay do pai NÃO passa para o fork; o do fork sim
    ov = {"portfolios": {"relaxed": {"min_confidence": 0.5}, "relaxed__fork1": {"buy_fraction_usdt": 0.1}}}
    eff3, prov3, _e, _m = eff_of("relaxed__fork1", reg, overlay=ov)
    assert eff3["gates"]["min_confidence"] == 0.4 and eff3["gates"]["buy_fraction_usdt"] == 0.1
    assert prov3["gates.buy_fraction_usdt"] == "overlay"
    # params.json portfolios.<fork> vale por cima do diff
    doc = copy.deepcopy(DOC)
    doc["portfolios"]["relaxed__fork1"] = {"gates": {"min_confidence": 0.45}}
    assert eff_of("relaxed__fork1", reg, doc=doc)[0]["gates"]["min_confidence"] == 0.45


def test_create_fork_validates_diff(tmp_path, monkeypatch):
    lab = tmp_path / "lab"
    monkeypatch.setattr(R, "LAB", lab)
    monkeypatch.setattr(R, "REG", lab / "registry.json")
    monkeypatch.setattr(R, "LOCK", lab / "registry.lock")
    name, why = R.create_fork("relaxed", {"gates": {"min_confidence": 0.4}}, "teste", dry_run=True)
    assert (name, why) == ("relaxed__fork1", "dry_run")
    name, why = R.create_fork("relaxed", {"gates": {"buy_fraction_usdt": 0.9}}, "teste", dry_run=True)
    assert name is None and why.startswith("params_invalidos") and "buy_fraction_usdt" in why
    name, why = R.create_fork("relaxed", {"gatez": {"x": 1}}, "teste", dry_run=True)
    assert name is None and "gatez" in why
    with pytest.raises(ValueError):
        R.create_fork("grid_sol_2pct", {"rule": {"grid_pct": 0.03}}, "teste", dry_run=True)


# ------------------------------------------------------------ validação e limites

def _doc_with(**portfolios):
    d = copy.deepcopy(DOC)
    d["portfolios"].update(portfolios)
    return d


def test_safety_limits_and_raising_them():
    errs = eff_of("relaxed", doc=_doc_with(relaxed={"gates": {"buy_fraction_usdt": 0.6}}))[2]
    assert any("buy_fraction_usdt" in e for e in errs)
    errs = eff_of("relaxed", doc=_doc_with(relaxed={"gates": {"max_trades_per_hour": 9}}))[2]
    assert any("max_trades_per_hour" in e for e in errs)
    ok = _doc_with(relaxed={"gates": {"buy_fraction_usdt": 0.6, "max_trades_per_hour": 12},
                            "limits": {"buy_fraction_usdt_max": 0.6, "max_trades_per_hour_max": 12}})
    assert eff_of("relaxed", doc=ok)[2] == []
    over = _doc_with(relaxed={"gates": {"buy_fraction_usdt": 1.5}, "limits": {"buy_fraction_usdt_max": 1.5}})
    assert any("limits.buy_fraction_usdt_max" in e for e in eff_of("relaxed", doc=over)[2])
    lev = _doc_with(relaxed={"limits": {"leverage": 2}})
    assert any("leverage" in e for e in eff_of("relaxed", doc=lev)[2])
    exp = _doc_with(relaxed={"gates": {"max_exposure_frac": 1.2}})
    assert any("max_exposure_frac" in e for e in eff_of("relaxed", doc=exp)[2])


def test_typos_bad_values_and_runner_support_are_errors():
    errs = eff_of("relaxed", doc=_doc_with(relaxed={"gates": {"min_confidense": 0.3}}))[2]
    assert any("min_confidense" in e for e in errs)
    errs = eff_of("relaxed", doc=_doc_with(relaxed={"gatez": {}}))[2]
    assert any("gatez" in e for e in errs)
    errs = eff_of("relaxed", doc=_doc_with(relaxed={"hours": [25]}))[2]
    assert any("hours" in e for e in errs)
    errs = eff_of("grid_sol_2pct", doc=_doc_with(grid_sol_2pct={"exits": {"enabled": True}}))[2]
    assert any("rules_bot" in e for e in errs)
    errs = eff_of("relaxed", doc=_doc_with(relaxed={"exec": {"mode": "limit"}}))[2]
    assert any("lab_bot" in e for e in errs)
    errs = eff_of("BONK_rule_regime", doc=_doc_with(BONK_rule_regime={"rule": {"ema_fast": 30}}))[2]
    assert any("ema_fast" in e for e in errs)
    # H1 aplicado ao relaxed do sol_bot é só params (suportado: saídas a mercado no sol_bot)
    assert eff_of("relaxed", doc=_doc_with(relaxed={"exits": {"enabled": True}}))[2] == []
    bad = copy.deepcopy(DOC); bad["paper_only"] = False
    assert P.check_doc(bad) and P.check_doc(DOC) == []


# ------------------------------------------------------------ overlay do dashboard

def test_overlay_legacy_keys_pause_and_group_keys():
    ov = {"bots": {}, "portfolios": {"relaxed": {"min_confidence": 0.4, "paused": True, "is_baseline_control": False},
                                      "hybrid_poorjev_regime": {"paused": True},
                                      "meme_rule_regime_full": {"paused": True},
                                      "baseline": {"limits": {"buy_fraction_usdt_max": 1.0}}}}
    eff, prov, errs, _ = eff_of("relaxed", overlay=ov)
    assert eff["gates"]["min_confidence"] == 0.4 and eff["paused"] and prov["gates.min_confidence"] == "overlay"
    assert eff_of("WIF_hybrid_poorjev_regime", overlay=ov)[0]["paused"]
    assert eff_of("WIF_rule_regime_full", overlay=ov)[0]["paused"]
    assert not eff_of("WIF_rule_regime", overlay=ov)[0]["paused"]
    eff, _p, errs, _ = eff_of("baseline", overlay=ov)
    assert eff["limits"]["buy_fraction_usdt_max"] == 0.5 and any("limits" in e for e in errs)


# ------------------------------------------------------------ store: hot reload e fail-closed

def _store(tmp_path, doc=DOC, overlay=None):
    pp, op = tmp_path / "params.json", tmp_path / "params_overlay.json"
    pp.write_text(json.dumps(doc))
    if overlay is not None:
        op.write_text(json.dumps(overlay))
    logs = []
    st = P.Store(path=pp, overlay=op, min_interval=0, log=lambda *a, **k: logs.append(a[0]))
    return st, pp, op, logs


def _bump(path, text):
    path.write_text(text)
    t = time.time() + 5
    os.utime(path, (t, t))


def test_hot_reload_and_last_valid_doc(tmp_path):
    st, pp, _op, logs = _store(tmp_path)
    assert st.effective("relaxed")["gates"]["min_confidence"] == 0.35
    d = copy.deepcopy(DOC); d["profiles"]["relaxed"]["gates"]["min_confidence"] = 0.3
    _bump(pp, json.dumps(d))
    assert st.effective("relaxed")["gates"]["min_confidence"] == 0.3
    _bump(pp, "{broken json")
    assert st.effective("relaxed")["gates"]["min_confidence"] == 0.3  # último documento válido
    assert st.doc_errors and any("ilegível" in m for m in logs)


def test_fail_closed_per_portfolio(tmp_path):
    st, pp, op, logs = _store(tmp_path, overlay={"portfolios": {}})
    good = st.effective("relaxed")
    _bump(op, json.dumps({"portfolios": {"relaxed": {"buy_fraction_usdt": 0.9}}}))
    eff = st.effective("relaxed")
    assert eff["gates"] == good["gates"] and st.errors.get("relaxed")  # últimos válidos
    assert st.effective("baseline")["gates"] == BASE_G  # os outros portfólios seguem normais
    # sem último válido: estáticos (sem overlay) se forem válidos, mantendo a pausa do overlay
    (tmp_path / "b").mkdir()
    st2, _pp, _op, _l = _store(tmp_path / "b", overlay={"portfolios": {"relaxed": {"buy_fraction_usdt": 0.9, "paused": True}}})
    e2 = st2.effective("relaxed")
    assert e2["gates"] == REL_G and e2["paused"] is True
    # params inválidos e sem nada válido: artigo + pausado
    d = _doc_with(relaxed={"gates": {"buy_fraction_usdt": 0.9}})
    (tmp_path / "c").mkdir()
    st3, *_ = _store(tmp_path / "c", doc=d)
    e3 = st3.effective("relaxed")
    assert e3["paused"] is True and e3.get("failsafe") and e3["gates"]["min_confidence"] == 0.6
    # ficheiro em falta: fail-closed, sem exceção
    st4 = P.Store(path=tmp_path / "nope.json", overlay=tmp_path / "nope_ov.json", min_interval=0, log=lambda *a, **k: None)
    assert st4.effective("relaxed")["paused"] is True
    # cópia: alterar o resultado não mexe no cache
    e = st.effective("baseline"); e["gates"]["min_confidence"] = 0.0
    assert st.effective("baseline")["gates"]["min_confidence"] == 0.6


def test_write_layer_validates_before_saving(tmp_path):
    pp = tmp_path / "params.json"
    pp.write_text(json.dumps(DOC))
    res = P.write_layer("types", "hybrid", {"set": {"gates": {"cooldown_seconds": 300}}}, path=pp)
    assert res["changes"] == {"gates.cooldown_seconds": {"old": None, "new": 300}}
    doc = json.loads(pp.read_text())
    assert doc["types"]["hybrid"]["gates"]["cooldown_seconds"] == 300
    assert eff_of("hybrid_von_relaxed_cap2", doc=doc)[0]["gates"]["cooldown_seconds"] == 300
    before = pp.read_text()
    with pytest.raises(ValueError) as ei:
        P.write_layer("types", "hybrid", {"gates": {"buy_fraction_usdt": 0.8}}, path=pp)
    assert "buy_fraction_usdt" in str(ei.value) and pp.read_text() == before
    P.write_layer("portfolios", "relaxed", {"exits": {"enabled": True}}, path=pp)
    P.write_layer("portfolios", "relaxed", {"unset": ["exits.enabled"]}, path=pp)
    assert json.loads(pp.read_text())["portfolios"]["relaxed"] == {"exits": {}}
    with pytest.raises(ValueError):
        P.write_layer("portfolios", "nao_existe", {"gates": {"min_confidence": 0.5}}, path=pp)


# ------------------------------------------------------------ tuner: espaço de busca por tipo

def test_tuner_search_space_per_type():
    T = pytest.importorskip("bot.tuner")
    sp = lambda n: [f"{a}.{b}" for a, b in T.search_space(eff_of(n)[0])]
    gates5 = ["gates.min_confidence", "gates.max_skip_noul", "gates.cooldown_seconds", "gates.max_trades_per_hour",
              "gates.buy_fraction_usdt"]
    assert sp("baseline") == gates5
    assert sp("relaxed") == gates5 + ["gates.min_prob_margin"]
    assert sp("h1_exits_von_relaxed") == gates5 + ["gates.min_prob_margin", "exits.tp", "exits.sl", "exits.trail",
                                                   "exits.trail_arm", "exits.reentry_cooldown_min"]
    assert sp("h3_limit_poorjev_relaxed") == gates5 + ["gates.min_prob_margin", "exec.offset_bps", "exec.ttl_min", "exec.fee_bps"]
    assert sp("h2_ensemble_sol") == ["gates.cooldown_seconds", "gates.max_trades_per_hour", "gates.buy_fraction_usdt",
                                     "ensemble.pct_threshold"]
    assert sp("BONK_rule_donch_regime") == ["rule.ema_fast", "rule.ema_slow", "rule.donchian"]
    d = copy.deepcopy(DOC)
    d["types"]["model_gated"]["tuning"] = {"params": ["gates.min_confidence"], "max_rel_change": 0.1}
    assert [f"{a}.{b}" for a, b in T.search_space(eff_of("relaxed", doc=d)[0])] == ["gates.min_confidence"]
    d["types"]["model_gated"]["tuning"] = {"enabled": False}
    assert T.search_space(eff_of("relaxed", doc=d)[0]) == []


def test_tuner_search_respects_bounds_and_step():
    T = pytest.importorskip("bot.tuner")
    t0 = 1_790_000_000.0
    px = [(t0 + i * 60, 100.0 + (i % 40) * 0.25) for i in range(600)]
    dec = [{"ts": t0 + i * 60 + 1, "portfolio": "relaxed", "chosen_action": "buy" if (i // 20) % 2 == 0 else "sell",
            "confidence": 0.36 + (i % 7) * 0.01, "probabilities": {"buy": 0.7, "sell": 0.2, "hold": 0.1},
            "skip_noul": 0.1, "price_usd": 100.0 + (i % 40) * 0.25} for i in range(0, 600, 3)]
    eff = eff_of("relaxed")[0]
    entry = {"name": "relaxed", "asset": "SOL", "kind": "gated", "profile": "relaxed"}
    r = T.search(entry, eff, t0, t0 + 600 * 60, (0.3, 960.0), 15.0, {"dec": dec, "px": px})
    assert r["status"] in ("candidate", "no_improvement")
    assert r["space"] == [f"{a}.{b}" for a, b in T.search_space(eff)]
    for sect, kv in (r.get("best_diff") or {}).items():
        for k, v in kv.items():
            old = eff[sect][k]
            assert abs(v / old - 1) <= 0.2 + 1e-9
            lo, hi = eff["tuning"]["bounds"].get(f"{sect}.{k}", (-1e9, 1e9))
            assert lo <= v <= hi
    off = copy.deepcopy(eff); off["tuning"]["enabled"] = False
    assert T.search(entry, off, t0, t0 + 600 * 60, (0.3, 960.0), 15.0, {"dec": dec, "px": px})["status"] == "tuning_desligado"


# ------------------------------------------------------------ ajudas dos bots

def test_cap_buy_limits_exposure():
    g = dict(REL_G, max_exposure_frac=0.5)
    pf = {"asset_mode": "sol", "sol": 1.0, "usdt": 900.0}  # 100 em SOL a 100, valor 1000
    g2, why = P.cap_buy(g, pf, 100.0)
    assert why is None and g2["buy_fraction_usdt"] == 0.25  # 225 cabe nos 400 de espaço
    pf = {"asset_mode": "sol", "sol": 4.5, "usdt": 550.0}   # 450 em SOL, espaço 50
    g2, why = P.cap_buy(g, pf, 100.0)
    assert why is None and g2["buy_fraction_usdt"] == pytest.approx(50 / 550)
    pf = {"asset_mode": "token", "token": 6.0, "usdt": 400.0}  # 600 na moeda: acima do teto
    assert P.cap_buy(g, pf, 100.0)[1] == "max_exposure"
    assert P.cap_buy(REL_G, pf, 100.0) == (REL_G, None)  # sem teto: nada muda


def test_regime_hours_exits_helpers():
    hyb = eff_of("hybrid_von_relaxed_cap2")[0]
    assert P.regime_block(hyb, "buy", None) == ("hold", ["sol_regime_unknown"])
    assert P.regime_block(hyb, "buy", False) == ("hold", ["sol_regime_bear_block_buy"])
    assert P.regime_block(hyb, "buy", True) == ("buy", [])
    assert P.regime_block(hyb, "sell", False) == ("sell", [])
    assert P.regime_block(eff_of("relaxed")[0], "buy", False) == ("buy", [])
    h4 = eff_of("h4_hours_von_relaxed")[0]
    assert P.pre_gate(h4, "buy", {}, 3, 0.0) == ["outside_hours"] and P.pre_gate(h4, "buy", {}, 10, 0.0) == []
    h1 = eff_of("h1_exits_von_relaxed")[0]
    assert P.pre_gate(h1, "buy", {"reentry_block_until": 10.0}, 3, 5.0) == ["reentry_cooldown"]
    pf = {"asset_mode": "sol", "sol": 1.0, "usdt": 0.0}
    assert P.check_exit(pf, h1["exits"], 100.0) is None and pf["entry_price"] == 100.0  # começa a contar agora
    assert P.check_exit(pf, h1["exits"], 102.6) == "take_profit"
    pf = {"asset_mode": "sol", "sol": 1.0, "usdt": 0.0, "entry_price": 100.0, "peak_price": 100.0}
    assert P.check_exit(pf, h1["exits"], 98.4) == "stop_loss"
    pf = {"asset_mode": "sol", "sol": 1.0, "usdt": 0.0, "entry_price": 100.0, "peak_price": 102.0}
    assert P.check_exit(pf, h1["exits"], 100.9) == "trailing_stop"
    pf = {"asset_mode": "sol", "sol": 0.0, "usdt": 100.0}
    P.track_fill(pf, "buy", 0.0, {"usdt_in": 100.0, "sol_out_net": 1.0}, 100.0)
    assert pf["entry_price"] == 100.0 and pf["peak_price"] == 100.0
    P.track_fill(pf, "sell", 1.0, {}, 101.0)
    assert pf["entry_price"] is None


def test_lib_apply_gates_margin_gate_flag():
    g = dict(REL_G)
    probs = {"buy": 0.4, "sell": 0.35, "hold": 0.25}  # margem 0.05
    pf = {"sol": 1.0, "usdt": 100.0, "trade_timestamps": [], "asset_mode": "sol"}
    assert lib.apply_gates("buy", 0.5, 0.1, pf, g, 100.0, probabilities=probs, profile="relaxed")["gate_reasons"] == ["low_prob_margin"]
    assert lib.apply_gates("buy", 0.5, 0.1, pf, g, 100.0, probabilities=probs, profile="baseline")["final_action"] == "buy"
    assert lib.apply_gates("buy", 0.5, 0.1, pf, g, 100.0, probabilities=probs, profile="baseline",
                           margin_gate=True)["gate_reasons"] == ["low_prob_margin"]
    assert lib.apply_gates("buy", 0.5, 0.1, pf, g, 100.0, probabilities=probs, profile="relaxed",
                           margin_gate=False)["final_action"] == "buy"


def test_clamp_gates_uses_limits():
    g = dict(BASE_G, buy_fraction_usdt=1.0, max_trades_per_hour=12)
    assert R.clamp_gates(g)["buy_fraction_usdt"] == 0.5 and R.clamp_gates(g)["max_trades_per_hour"] == 8
    c = R.clamp_gates(g, {"buy_fraction_usdt_max": 1.0, "max_trades_per_hour_max": 12})
    assert c["buy_fraction_usdt"] == 1.0 and c["max_trades_per_hour"] == 12


# ------------------------------------------------------------ sol_bot com params (offline: sem cotação Jupiter)

def _offline(*_a, **_k):
    raise RuntimeError("offline (teste)")


def _run(SB, tmp_path, name, pdata, eff, chosen="buy", px=100.0, bull=None, conf=0.5):
    dec = {"chosen_action": chosen, "confidence": conf, "skip_noul": 0.1, "latency_ms": 1.0, "ok": True,
           "probabilities": {"buy": 0.7, "sell": 0.2, "hold": 0.1} if chosen != "sell" else {"sell": 0.7, "buy": 0.2, "hold": 0.1}}
    return SB.apply_and_maybe_trade(name, pdata, tmp_path / f"{name}.json", tmp_path / f"eq_{name}.jsonl", eff["gates"],
                                    "relaxed", dec, {"state": "s", "features": {}}, px, {"source": "t"}, True, CFG,
                                    tmp_path / "trades.jsonl", tmp_path / "decisions.jsonl", "v", eff=eff, regime_bull=bull)


def test_sol_bot_applies_exposure_cap_regime_and_exits(tmp_path, monkeypatch):
    SB = pytest.importorskip("bot.sol_bot")
    monkeypatch.setattr(SB, "jupiter_quote", _offline)
    eff = eff_of("relaxed_expcap50")[0]
    pd = SB.new_portfolio(tmp_path / "x.json", 1.0, 900.0, 100.0, "relaxed_expcap50")
    reasons = []
    for _ in range(6):
        pd["last_trade_ts"] = None; pd["trade_timestamps"] = []
        row = _run(SB, tmp_path, "relaxed_expcap50", pd, eff)
        reasons.append(row["gate_reasons"])
        assert pd["sol"] * 100.0 / (pd["usdt"] + pd["sol"] * 100.0) <= 0.5 + 1e-9
    assert ["max_exposure"] in reasons
    # híbrido: regime de baixa bloqueia a compra e a ação registada vira hold (como antes)
    hyb = eff_of("hybrid_von_relaxed_cap2")[0]
    ph = SB.new_portfolio(tmp_path / "h.json", 0.0, 1000.0, 100.0, "hybrid_von_relaxed_cap2")
    row = _run(SB, tmp_path, "hybrid_von_relaxed_cap2", ph, hyb, bull=False)
    assert row["chosen_action"] == "hold" and row["model_action"] == "buy" and "sol_regime_bear_block_buy" in row["gate_reasons"]
    assert not row["traded"]
    assert _run(SB, tmp_path, "hybrid_von_relaxed_cap2", ph, hyb, bull=True)["traded"]
    # saídas (H1) aplicadas a um portfólio do sol_bot: TP vende tudo e bloqueia a reentrada
    h1 = eff_of("h1_exits_von_relaxed")[0]
    pe = SB.new_portfolio(tmp_path / "e.json", 1.0, 0.0, 100.0, "relaxed_h1")
    pe["entry_price"] = 100.0; pe["peak_price"] = 100.0
    row = _run(SB, tmp_path, "relaxed_h1", pe, h1, chosen="buy", px=103.0)
    assert row["exit_reason"] == "take_profit" and row["exit_traded"] and pe["sol"] == 0.0
    assert "reentry_cooldown" in row["gate_reasons"] and row["final_action"] == "hold"
    # baseline sem params novos: compra normal com confiança alta; margem não se aplica ao baseline
    base = eff_of("baseline")[0]
    pb = SB.new_portfolio(tmp_path / "b.json", 0.0, 1000.0, 100.0, "baseline")
    row = _run(SB, tmp_path, "baseline", pb, base, conf=0.7)
    assert row["traded"] and row["gate_reasons"] == [] and pb["usdt"] == pytest.approx(750.0)


def test_nightly_reports_fork_params_with_provenance():
    pytest.importorskip("numpy")
    from bot import nightly as N
    e = {"name": "relaxed__fork1", "asset": "SOL", "cls": "sol", "kind": "gated", "source": "relaxed", "profile": "relaxed",
         "model": "von", "test_type": "model_gated", "parent": "relaxed", "lineage": "relaxed",
         "params_diff": {"gates": {"min_confidence": 0.4}}}
    reg = {"portfolios": {e["name"]: e}, "lineages": {}}
    lines = N.fork_params_lines(e, reg)
    assert lines == ["`gates.min_confidence` = 0.4 (pai: 0.35; camada `fork:relaxed__fork1`)"]
    assert N.params_for("hybrid_von_relaxed_cap2")[0]["gates"]["max_trades_per_hour"] == 2
