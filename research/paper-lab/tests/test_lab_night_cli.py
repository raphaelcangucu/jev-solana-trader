"""scripts/night_cli.py (revisão noturna autónoma, paper only) e a execução dos forks de critérios no lab_bot.

Tudo offline, numa árvore temporária (PAPER_LAB_ROOT do conftest): limites da noite/linhagem/total, limites dos
parâmetros, validação e armazenamento dos critérios, diário sem sobrescrever, recusa do bot real fora de paper e
o fork de critérios a correr no lab_bot com um backend falso e cache.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import time
from pathlib import Path

import pytest

from bot import lab_criteria as LC
from bot import lab_registry as R
from bot import params as P
from bot.paths import ROOT

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parents[1]
REASON = ("Hipótese: exigir cautela em estados thin reduz compras erradas. Confirma se em 5 dias a habilidade do fork "
          "supera a do pai com pelo menos dez trades; refuta se ficar igual ou pior.")
STATE = "deep quiet flat calm night gray wide soft late mid quiet flat"
GOOD = {"action": {"instructions": "buy on strength only when the book can absorb it and the tape agrees",
                   "criteria": {"buy": "the move is lifting or pumping with calm tape and a deep book",
                                "sell": "the move is fading or dumping, or the tape turns harsh and loud",
                                "hold": "flat gray chop, whipping tape, or anything unclear"}},
        "skip_this_cycle": {"instructions": "conditions are too hostile to trade at all, such as a thin book"}}
CREATED = ("config.json", "memecoins.json", "models.json", "criteria_baseline.json", "criteria_v2.json",
           "data", "logs", "run", "reviews")


def _load_cli():
    spec = importlib.util.spec_from_file_location("night_cli", LAB / "scripts" / "night_cli.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CLI = _load_cli()


def _write(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))


@pytest.fixture
def lab(monkeypatch):
    """Árvore mínima do lab em ROOT; limpa no fim (os outros testes usam a mesma raiz temporária)."""
    for n in CREATED:
        assert not (ROOT / n).exists(), f"{ROOT / n} já existe: outro teste não limpou"
    cfg = json.loads((LAB / "config.json").read_text())
    cfg["claude_night"] = dict(cfg.get("claude_night") or {}, enabled=True, max_forks_per_night=3, per_lineage_days=2,
                               total_forks=80, max_realbot_per_night=1)
    _write(ROOT / "config.json", cfg)
    for n in ("memecoins.json", "models.json", "criteria_baseline.json", "criteria_v2.json"):
        shutil.copy(LAB / n, ROOT / n)
    now = time.time()
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "prices.jsonl").write_text(json.dumps({"ts": now, "price_usd": 150.0}) + "\n")
    for n in ("baseline", "relaxed", "poorjev_relaxed", "laya_relaxed", "v2"):
        _write(ROOT / "data" / f"portfolio_{n}.json", R.new_state(n, "SOL", 150.0, sol=0.3, usdt=960.0))
    (ROOT / "run" / "claude_night").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    P.STORE.refresh(force=True)
    yield ROOT
    for n in CREATED:
        p = ROOT / n
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    P.STORE.refresh(force=True)


def run(capsys, *argv):
    code = CLI.main(list(argv))
    out = capsys.readouterr().out
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, out


def crit_file(name="c.json", doc=None):
    p = ROOT / "run" / "claude_night" / name
    _write(p, doc if doc is not None else GOOD)
    return str(p)


def changes():
    p = ROOT / "logs" / "param_changes.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


# ------------------------------------------------------------------ fork de parâmetros: limites

def test_fork_creates_child_logs_who_and_never_touches_parent(lab, capsys):
    before = (ROOT / "data" / "portfolio_relaxed.json").read_text()
    code, out = run(capsys, "fork", "--parent", "relaxed", "--diff", '{"gates": {"cooldown_seconds": 600}}', "--reason", REASON)
    assert code == 0 and out["ok"] and out["fork"] == "relaxed__fork1" and out["status"] == "created"
    e = R.load()["portfolios"]["relaxed__fork1"]
    assert e["who"] == "claude-night" and e["params_diff"] == {"gates": {"cooldown_seconds": 600}} and e["fork_kind"] == "params"
    assert P.explain("relaxed__fork1", meta=e, use_overlay=False)[0]["gates"]["cooldown_seconds"] == 600
    assert P.explain("relaxed", use_overlay=False)[0]["gates"]["cooldown_seconds"] == 120  # original intacto
    assert (ROOT / "data" / "portfolio_relaxed.json").read_text() == before
    row = [c for c in changes() if c["type"] == "fork_created"][-1]
    assert row["who"] == "claude-night" and row["night"] == CLI.night_key() and row["portfolio"] == "relaxed__fork1"
    assert R.describe_fork(e) == "pausa entre trades (s) 600"


@pytest.mark.parametrize("diff, msg", [
    ('{"gates": {"cooldown_seconds": 6000}}', "fora dos limites"),
    ('{"gates": {"buy_fraction_usdt": 0.9}}', "fora dos limites"),
    ('{"gates": {"min_confidence": 1.5}}', "fora dos limites"),
    ('{"limits": {"buy_fraction_usdt_max": 1.0}}', "não permitido"),
    ('{"tuning": {"enabled": false}}', "não permitido"),
    ('{"criteria": {"file": "data/lab/criteria/x.json"}}', "não permitido"),
    ('{"gates": {"cooldown_seconds": 120}}', "sem efeito"),
    ('{"gates": {"no_such_key": 1}}', "chave desconhecida"),
    ('{"exits": {"enabled": true, "tp": 2.0, "sl": 0.01, "trail": 0.01}}', "acima do máximo"),
    ('{}', "não vazio"),
])
def test_fork_refuses_out_of_bounds_or_forbidden_diffs(lab, capsys, diff, msg):
    code, out = run(capsys, "fork", "--parent", "laya_relaxed", "--diff", diff, "--reason", REASON)
    assert code == 2 and not out["ok"] and msg in out["error"]
    assert "laya_relaxed__fork1" not in R.load()["portfolios"]
    assert changes()[-1]["type"] == "claude_night_refused" and changes()[-1]["who"] == "claude-night"


def test_fork_dry_run_and_short_reason(lab, capsys):
    code, out = run(capsys, "fork", "--parent", "laya_relaxed", "--diff", '{"gates": {"min_confidence": 0.3}}', "--reason", REASON, "--dry-run")
    assert code == 0 and out["status"] == "dry_run"
    assert "laya_relaxed__fork1" not in R.load()["portfolios"] and not changes()
    code, out = run(capsys, "fork", "--parent", "laya_relaxed", "--diff", '{"gates": {"min_confidence": 0.3}}', "--reason", "curto")
    assert code == 2 and "--reason" in out["error"]
    code, out = run(capsys, "fork", "--parent", "nao_existe", "--diff", '{"gates": {"min_confidence": 0.3}}', "--reason", REASON)
    assert code == 2 and "pai desconhecido" in out["error"]


def test_night_lineage_and_total_caps(lab, capsys):
    ok = lambda parent, diff: run(capsys, "fork", "--parent", parent, "--diff", diff, "--reason", REASON)
    assert ok("relaxed", '{"gates": {"cooldown_seconds": 300}}')[0] == 0
    code, out = ok("relaxed", '{"gates": {"cooldown_seconds": 900}}')  # mesma linhagem em < 2 dias
    assert code == 2 and "cap_1_fork_per_2" in out["error"]
    assert ok("laya_relaxed", '{"gates": {"min_confidence": 0.3}}')[0] == 0
    assert ok("poorjev_relaxed", '{"gates": {"min_confidence": 0.3}}')[0] == 0
    code, out = ok("v2", '{"gates": {"min_confidence": 0.3}}')  # 4.º fork com max_forks_per_night=3
    assert code == 2 and "cap da noite" in out["error"]
    st = CLI.caps_status()
    assert st["forks_tonight"] == 3 and st["forks_left_tonight"] == 0 and "relaxed" in st["lineages_blocked"]
    # cap total: com total_forks=3 nem uma noite nova passaria
    cfg = json.loads((ROOT / "config.json").read_text())
    cfg["claude_night"].update(max_forks_per_night=10, total_forks=3)
    _write(ROOT / "config.json", cfg)
    code, out = ok("v2", '{"gates": {"min_confidence": 0.3}}')
    assert code == 2 and "cap total" in out["error"]


def test_disabled_config_refuses_writes(lab, capsys):
    cfg = json.loads((ROOT / "config.json").read_text())
    cfg["claude_night"]["enabled"] = False
    _write(ROOT / "config.json", cfg)
    code, out = run(capsys, "fork", "--parent", "relaxed", "--diff", '{"gates": {"cooldown_seconds": 300}}', "--reason", REASON)
    assert code == 2 and "enabled=false" in out["error"]


# ------------------------------------------------------------------ critérios: validação e armazenamento

@pytest.mark.parametrize("mut, msg", [
    (lambda d: d["action"]["criteria"].__setitem__("buy", "buy when up two percent"), None),
    (lambda d: d["action"]["criteria"].__setitem__("buy", "buy when up 2 percent"), "dígitos"),
    (lambda d: d["action"]["criteria"].pop("hold"), "action.criteria.hold"),
    (lambda d: d["action"]["criteria"].__setitem__("short", "x"), "desconhecidas"),
    (lambda d: d.pop("skip_this_cycle"), "skip_this_cycle"),
    (lambda d: d["action"].__setitem__("instructions", "   "), "vazio"),
    (lambda d: d["action"]["criteria"].__setitem__("sell", "fade " * 100), "máximo"),
    (lambda d: d["action"]["criteria"].__setitem__("sell", 3), "texto"),
])
def test_criteria_validation(mut, msg):
    d = json.loads(json.dumps(GOOD))
    mut(d)
    if msg is None:
        assert LC.validate(d)["action"]["criteria"]["buy"] == "buy when up two percent"
    else:
        with pytest.raises(LC.CriteriaTextError, match=msg):
            LC.validate(d)


def test_criteria_store_never_overwrites_and_checks_hash(lab):
    clean = LC.validate(GOOD)
    ref = LC.store("x__fork1", clean, {"who": "test"})
    assert ref["file"] == "data/lab/criteria/x__fork1.json" and ref["sha256"] == LC.digest(clean)
    assert LC.load_ref(ref) == (clean, ref["sha256"])
    with pytest.raises(LC.CriteriaTextError, match="sobrescritos"):
        LC.store("x__fork1", clean)
    p = LC.abs_path(ref["file"])
    doc = json.loads(p.read_text()); doc["action"]["criteria"]["buy"] = "anything goes"
    p.write_text(json.dumps(doc))
    with pytest.raises(LC.CriteriaTextError, match="sha256"):
        LC.load_ref(ref)
    for bad in ("../x.json", "data/lab/criteria/../../x.json", "/etc/x.json", "data/lab/criteria/a/b.json"):
        with pytest.raises(LC.CriteriaTextError):
            LC.abs_path(bad)


def test_params_criteria_group_only_for_lab_forks():
    doc = json.loads((LAB / "params.json").read_text())
    reg = {"portfolios": {}, "lineages": {}}
    ref = {"file": "data/lab/criteria/relaxed__fork9.json", "sha256": "a" * 64}
    meta = {"name": "relaxed__fork9", "parent": "relaxed", "lineage": "relaxed", "kind": "gated", "source": "relaxed",
            "asset": "SOL", "model": "von", "profile": "relaxed", "test_type": "model_gated", "params_diff": {"criteria": ref}}
    m = P.classify("relaxed__fork9", entry=meta, registry=reg)
    eff, _prov, errs = P.resolve(m, doc, None, reg)
    assert P.validate(eff, m) == [] and eff["criteria"] == ref and "critérios próprios" in P.summary(eff)
    # original do sol_bot com critérios em params.json → erro (o sol_bot não os usa)
    doc2 = json.loads(json.dumps(doc)); doc2.setdefault("portfolios", {})["relaxed"] = {"criteria": ref}
    m2 = P.classify("relaxed", registry=reg)
    eff2, _p, e2 = P.resolve(m2, doc2, None, reg)
    assert any("lab_bot" in e for e in P.validate(eff2, m2))
    bad = dict(meta, params_diff={"criteria": {"file": "../../etc/passwd"}})
    m3 = P.classify("relaxed__fork9", entry=bad, registry=reg)
    assert any("criteria.file" in e for e in P.validate(P.resolve(m3, doc, None, reg)[0], m3))
    # o overlay do dashboard nunca muda critérios
    _l, _paused, warn = P.overlay_layer({"name": "x", "pause_keys": ["x"]}, {"portfolios": {"x": {"criteria": ref}}})
    assert warn and "criteria" in warn[0]


def test_criteria_fork_creates_file_and_refuses_bad_parents(lab, capsys):
    f = crit_file()
    code, out = run(capsys, "criteria-fork", "--parent", "baseline", "--criteria-file", f, "--reason", REASON)
    assert code == 0 and out["fork"] == "baseline__fork1" and out["parent_criteria"] == "criteria_baseline.json"
    e = R.load()["portfolios"]["baseline__fork1"]
    ref = e["params_diff"]["criteria"]
    assert ref["file"] == "data/lab/criteria/baseline__fork1.json" and e["fork_kind"] == "criteria" and e["who"] == "claude-night"
    assert LC.load_ref(ref)[0] == LC.validate(GOOD)
    assert R.describe_fork(e) == "critérios reescritos"
    assert P.explain("baseline__fork1", meta=e, use_overlay=False)[2] == []
    # pai com os mesmos critérios
    same = crit_file("same.json", json.loads((LAB / "criteria_baseline.json").read_text()))
    code, out = run(capsys, "criteria-fork", "--parent", "relaxed", "--criteria-file", same, "--reason", REASON)
    assert code == 2 and "iguais" in out["error"]
    # pai de regra / ensemble / fora de run/ / com dígitos
    code, out = run(capsys, "criteria-fork", "--parent", "grid_sol_2pct", "--criteria-file", f, "--reason", REASON)
    assert code == 2 and "kind=rule" in out["error"]
    code, out = run(capsys, "criteria-fork", "--parent", "relaxed", "--criteria-file", str(ROOT / "config.json"), "--reason", REASON)
    assert code == 2 and "run" in out["error"]
    d = json.loads(json.dumps(GOOD)); d["skip_this_cycle"]["instructions"] = "skip after 3 losses"
    code, out = run(capsys, "criteria-fork", "--parent", "relaxed", "--criteria-file", crit_file("d.json", d), "--reason", REASON)
    assert code == 2 and "dígitos" in out["error"]
    # backend desligado em models.json
    mj = json.loads((ROOT / "models.json").read_text()); mj["backends"]["laya"]["enabled"] = False
    _write(ROOT / "models.json", mj)
    code, out = run(capsys, "criteria-fork", "--parent", "laya_relaxed", "--criteria-file", f, "--reason", REASON)
    assert code == 2 and "desligado" in out["error"]
    # fork de parâmetros de um fork de critérios herda os critérios
    code, out = run(capsys, "fork", "--parent", "baseline__fork1", "--diff", '{"gates": {"min_confidence": 0.5}}', "--reason", REASON)
    assert code == 2 and "cap_1_fork_per_2" in out["error"]  # mesma linhagem (baseline)


def test_journal_copies_without_overwrite(lab, capsys):
    src = ROOT / "run" / "claude_night" / "diario.md"
    src.write_text("# Diário\n\nnada a declarar\n")
    code, a = run(capsys, "journal", "--file", str(src))
    code2, b = run(capsys, "journal", "--file", str(src))
    assert code == code2 == 0 and a["file"] != b["file"] and b["file"].endswith("_2.md")
    assert Path(a["file"]).read_text() == src.read_text() == Path(b["file"]).read_text()
    (ROOT / "run" / "claude_night" / "x.txt").write_text("x")
    assert run(capsys, "journal", "--file", str(ROOT / "run" / "claude_night" / "x.txt"))[0] == 2
    assert run(capsys, "journal", "--file", str(ROOT / "config.json"))[0] == 2
    code, st = run(capsys, "status")
    assert code == 0 and len(st["caps"]["journal_tonight"]) == 2


# ------------------------------------------------------------------ bot real: aprovação autónoma só em paper

def _realbot(tmp_path, mode="paper", profile_paper_only=True, dotenv=None):
    root = tmp_path / "realbot"
    _write(root / "config" / "experiment.json", {"run_id": "r", "start_t": "2026-09-30T00:00:00-03:00",
                                                 "book": {"sol": 0.01, "usdt": 50}, "mode": mode})
    _write(root / "config" / "params.json", {"defaults": {}, "profiles": {
        "article": {"gates": {"confidence_min": 0.55}},
        "relaxed_paper": dict({"gates": {"confidence_min": 0.35}}, **({"paper_only": True} if profile_paper_only else {}))}})
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "logs" / "decisions.jsonl").write_text("")
    if dotenv is not None:
        (root / ".env").write_text(dotenv)
    return root


@pytest.mark.parametrize("env, kw, why", [
    ({"LIVE_TRADING": "1"}, {}, "LIVE_TRADING=1 no ambiente"),
    ({}, {"dotenv": "SECRET=abc\nLIVE_TRADING=1\n"}, "LIVE_TRADING=1 no .env"),
    ({}, {"mode": "live"}, "mode='live'"),
    ({}, {"profile_paper_only": False}, "não é paper_only"),
    ({"PARAMS_PROFILE": "article"}, {}, "não é paper_only"),
])
def test_realbot_criteria_refuses_outside_paper_and_writes_nothing(lab, capsys, monkeypatch, tmp_path, env, kw, why):
    root = _realbot(tmp_path, **kw)
    monkeypatch.setenv("JEV_TRADER_ROOT", str(root))
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    code, out = run(capsys, "realbot-criteria", "--criteria-file", crit_file(), "--reason", REASON)
    assert code == 2 and any(why in r for r in out["refused"])
    assert "abc" not in json.dumps(out)  # o .env nunca é ecoado
    assert not (root / "config" / "criteria.json").exists() and not (root / "logs" / "rewrite_proposals").exists()
    assert not (root / "logs" / "rewrite_approvals.jsonl").exists() and not changes()


def test_realbot_criteria_auto_approves_in_paper_once_per_night(lab, capsys, monkeypatch, tmp_path):
    root = _realbot(tmp_path)
    monkeypatch.setenv("JEV_TRADER_ROOT", str(root))
    code, out = run(capsys, "realbot-criteria", "--criteria-file", crit_file(), "--reason", REASON)
    assert code == 0 and out["approved"]["approver"] == "claude-night" and out["approved"]["autonomous"] is True
    live = json.loads((root / "config" / "criteria.json").read_text())
    assert live["buy"] == GOOD["action"]["criteria"]["buy"] and live["skip"] == GOOD["skip_this_cycle"]["instructions"]
    prop = json.loads(Path(out["approved"]["proposal"]).read_text())
    assert prop["status"] == "approved" and prop["author"] == "claude-night" and prop["autonomous"] is True
    assert changes()[-1]["type"] == "realbot_criteria_approved"
    code, out = run(capsys, "realbot-criteria", "--criteria-file", crit_file("c2.json"), "--reason", REASON)
    assert code == 2 and "cap da noite" in out["error"]


# ------------------------------------------------------------------ lab_bot: execução dos forks de critérios

def _lab_with_forks(capsys):
    assert run(capsys, "fork", "--parent", "relaxed", "--diff", '{"gates": {"cooldown_seconds": 300}}', "--reason", REASON)[0] == 0
    assert run(capsys, "criteria-fork", "--parent", "baseline", "--criteria-file", crit_file(), "--reason", REASON)[0] == 0
    import bot.lab_bot as LB
    return LB


def _src_row(portfolio, chosen="hold", conf=0.2, state=STATE):
    return {"ts": time.time(), "ts_brt": "x", "decision_id": f"d-{portfolio}-{time.time()}", "portfolio": portfolio,
            "state": state, "price_usd": 150.0, "chosen_action": chosen, "confidence": conf,
            "probabilities": {"buy": 0.1, "sell": 0.1, "hold": 0.8}, "skip_noul": 0.1, "model": "von"}


def _append(rows):
    with open(ROOT / "logs" / "decisions.jsonl", "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_lab_bot_runs_criteria_fork_with_fake_backend_and_cache(lab, capsys, monkeypatch):
    LB = _lab_with_forks(capsys)
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "logs" / "decisions.jsonl").touch()
    lab_ = LB.Lab()
    calls = []

    def fake(model, bcfg, state, criteria, timeout):
        calls.append((model, state, criteria["action"]["criteria"]["buy"]))
        return {"ok": True, "chosen_action": "buy", "probabilities": {"buy": 0.9, "sell": 0.05, "hold": 0.05},
                "confidence": 0.9, "skip_noul": 0.1, "fail_closed": False, "latency_ms": 1.0, "model": model}
    lab_.crit._decide = fake
    trades = []
    monkeypatch.setattr(LB.Lab, "market_trade", lambda self, e, side, px, did, g=None: trades.append((e["name"], side)) or {"fill": {}})
    _append([_src_row("baseline"), _src_row("relaxed")])
    lab_.cycle()
    assert calls == [("von", STATE, GOOD["action"]["criteria"]["buy"])]
    assert trades == [("baseline__fork1", "buy")]  # o fork de parâmetros seguiu o hold da fonte
    rows = [json.loads(l) for l in (ROOT / "logs" / "lab_decisions.jsonl").read_text().splitlines()]
    cf = [r for r in rows if r["portfolio"] == "baseline__fork1"][-1]
    assert cf["model"] == "von" and cf["confidence"] == 0.9 and cf["final_action"] == "buy" and cf["state"] == STATE
    assert cf["criteria_sha256"] == LC.digest(LC.validate(GOOD)) and cf["cache"] == "miss" and cf["fail_closed"] is False
    pf = [r for r in rows if r["portfolio"] == "relaxed__fork1"][-1]
    assert "criteria_sha256" not in pf and pf["chosen_action"] == "hold" and pf["confidence"] == 0.2
    # mesmo estado → cache (sem nova chamada); estado novo → nova chamada
    _append([_src_row("baseline"), _src_row("baseline", state=STATE.replace("gray", "green"))])
    lab_.cycle()
    assert len(calls) == 2 and lab_.crit.stats["hits"] == 1
    # erro do backend → hold (fail-closed), não vai para a cache, pausa o backend
    lab_.crit._decide = lambda *a: {"ok": False, "fail_closed": True, "error": "http_0:boom", "chosen_action": "hold"}
    n_tr = len(trades)
    _append([_src_row("baseline", state=STATE.replace("deep", "thin"))])
    lab_.cycle()
    last = [json.loads(l) for l in (ROOT / "logs" / "lab_decisions.jsonl").read_text().splitlines()][-1]
    assert last["portfolio"] == "baseline__fork1" and last["final_action"] == "hold" and last["fail_closed"] is True
    assert "boom" in last["backend_error"] and len(trades) == n_tr
    assert not [k for k in lab_.crit.cache if k[2] == STATE.replace("deep", "thin")]
    assert lab_.crit.down_until.get("von", 0) > time.time()


def test_lab_bot_criteria_fork_fails_closed_on_tampered_file_and_lru_is_bounded(lab, capsys, monkeypatch):
    LB = _lab_with_forks(capsys)
    caller = LB.CriteriaCaller(decide=lambda m, b, s, c, t: {"ok": True, "chosen_action": "sell", "confidence": 0.7,
                                                             "probabilities": {}, "skip_noul": 0.0}, max_items=2)
    e = dict(R.load()["portfolios"]["baseline__fork1"])
    e["params"] = P.explain("baseline__fork1", meta=e, use_overlay=False)[0]
    for i, w in enumerate(("deep", "okay", "thin")):
        assert caller.decide(e, {"state": STATE.replace("deep", w), "chosen_action": "hold"})["chosen_action"] == "sell"
    assert len(caller.cache) == 2
    assert caller.decide(e, {"state": "", "chosen_action": "buy"})["fail_closed"] is True
    assert caller.decide(e, {"state": "thin 2 calm"})["error"] == "sem_estado"
    p = LC.abs_path(e["params"]["criteria"]["file"])
    doc = json.loads(p.read_text()); doc["action"]["criteria"]["buy"] = "always buy"
    p.write_text(json.dumps(doc))
    r = caller.decide(e, {"state": STATE})
    assert r["fail_closed"] is True and r["chosen_action"] == "hold" and "sha256" in r["error"]


def test_context_is_compact_and_lists_forks(lab, capsys):
    run(capsys, "fork", "--parent", "relaxed", "--diff", '{"gates": {"cooldown_seconds": 300}}', "--reason", REASON)
    run(capsys, "criteria-fork", "--parent", "baseline", "--criteria-file", crit_file(), "--reason", REASON)
    code = CLI.main(["context"])
    txt = capsys.readouterr().out
    assert code == 0 and "# Contexto da noite" in txt and len(txt) < 24000
    for s in ("## Forks existentes (2)", "relaxed__fork1", "critérios reescritos", "claude-night", "## Limites (claude_night)",
              "2/3 forks", "## Critérios em uso", "baseline__fork1 (fork de critérios"):
        assert s in txt, s
