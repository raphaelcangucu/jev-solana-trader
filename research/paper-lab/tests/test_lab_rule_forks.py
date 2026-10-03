"""Forks de regras (grid/RSI/regime/Donchian, com variantes _full): criação e validação (lab_registry.create_fork),
execução no rules_bot (RuleForks) com os parâmetros do fork sobre velas sintéticas, originais intactos, hot reload do
registry, fail-closed com parâmetros inválidos, saídas/filtro de regime só nos forks, night_cli com pai de regra
(dry-run) e o tuner noturno a criar um fork de regra real.

Tudo offline numa árvore temporária (PAPER_LAB_ROOT do conftest); as cotações Jupiter são substituídas por erro
(fill a mark, como no fallback real)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import time
from pathlib import Path

import pytest

from bot import lab_registry as R
from bot import params as P
from bot import rules_bot as RB
from bot.paths import ROOT
from bot.rules_engine import CandleBook, grid_signal, meme_rule_signal

LAB = Path(__file__).resolve().parents[1]
CREATED = ("config.json", "memecoins.json", "data", "logs", "run", "reviews", "reports", "params.json")
DONCH = "BONK_rule_donch_regime_full"
REASON = ("Hipótese: a janela de Donchian de 40 h evita comprar rompimentos noturnos sincronizados. Confirma se em 5 "
          "dias o fork perde menos que o pai com pelo menos dois trades; refuta se ficar igual ou pior.")
HOUR = 3600


def _write(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))


def _jl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def _clean():
    for n in CREATED:
        p = ROOT / n
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


@pytest.fixture
def lab(monkeypatch):
    _clean()  # a raiz temporária é partilhada: começa limpa (outros testes podem deixar logs/param_changes.jsonl)
    cfg = json.loads((LAB / "config.json").read_text())
    cfg["claude_night"] = dict(cfg.get("claude_night") or {}, enabled=True, max_forks_per_night=3, per_lineage_days=2,
                               total_forks=80, max_realbot_per_night=1)
    _write(ROOT / "config.json", cfg)
    shutil.copy(LAB / "memecoins.json", ROOT / "memecoins.json")
    now = time.time()
    (ROOT / "data" / "meme" / "prices").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "prices.jsonl").write_text(json.dumps({"ts": now, "price_usd": 130.0}) + "\n")
    (ROOT / "data" / "meme" / "prices" / "BONK.jsonl").write_text(json.dumps({"ts": now, "price_usd": 1.2}) + "\n")
    # originais de regra (estado como o rules_bot cria)
    g = RB.new_sol_portfolio(ROOT / "data" / "portfolio_grid_sol_2pct.json", 0.3, 960.0, 130.0, "grid_sol_2pct")
    g["rule_state"] = {"ref": 130.0, "buys_open": 0}
    RB.write_json(ROOT / "data" / "portfolio_grid_sol_2pct.json", g)
    RB.new_sol_portfolio(ROOT / "data" / "portfolio_rsi_sol_1h.json", 0.3, 960.0, 130.0, "rsi_sol_1h")
    for n in (DONCH, "BONK_rule_donch_regime", "BONK_rule_regime"):
        RB.new_meme_portfolio(ROOT / "data" / "meme" / "portfolios" / f"{n}.json", 1000.0, 1.0, n)
    # cotações: sempre erro → fill a mark (sem rede)
    monkeypatch.setattr(RB, "jupiter_quote", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.delenv("PAPER_LAB_PARAMS", raising=False)
    P.STORE.refresh(force=True)
    yield cfg
    _clean()
    P.STORE.refresh(force=True)


def fork(parent, diff, days=0, **kw):
    return R.create_fork(parent, diff, "teste", caps_override={"per_lineage_days": days}, **kw)


def backdate(name, secs=3 * HOUR):
    """O fork só age em barras fechadas depois da sua criação: as velas sintéticas acabam agora."""
    p = R.port_path(name)
    st = json.loads(p.read_text())
    st["created_ts"] = time.time() - secs
    p.write_text(json.dumps(st))


def sol_bars(n=60, up=True, last=None):
    t_last = int(time.time()) // HOUR * HOUR - HOUR
    out = []
    for i in range(n):
        c = 100.0 + (i * 0.5 if up else -i * 0.5) + (60 if not up else 0)
        out.append({"ts": t_last - (n - 1 - i) * HOUR, "open": c, "high": c * 1.002, "low": c * 0.998, "close": c, "volume": 1.0})
    if last is not None:
        out[-1].update(close=last, low=min(out[-1]["low"], last), high=max(out[-1]["high"], last))
    return out


def bonk_bars(n=60, last=1.2):
    """Topo antigo (2,0) há ~41 h, depois lateral 0,95–1,1 e rompimento final a `last`: Donchian 20 compra, 40 não."""
    t_last = int(time.time()) // HOUR * HOUR - HOUR
    out = []
    for i in range(n):
        hi = 2.0 if i == n - 41 else 1.1
        out.append({"ts": t_last - (n - 1 - i) * HOUR, "open": 1.0, "high": hi, "low": 0.95, "close": 1.0, "volume": 1.0})
    out[-1].update(close=last, high=last)
    return out


def make_book(sol, bonk=None):
    b = CandleBook()
    b.sol = sol
    b.memes["BONK"] = bonk or []
    b.started_ts = time.time() - 10 * HOUR
    return b


def step(forks, book, cfg, sol_px=130.0, bonk_px=1.2, allow=True, overlay=None):
    ind = book.sol_indicators()
    bull = lambda f, s: bool(book.sol_indicators(ema_fast=f, ema_slow=s).get("sol_regime_bull"))
    return forks.step(book, ind=ind, sol_px=sol_px, marks={"BONK": {"price_usd": bonk_px, "source": "test"}}, allow=allow,
                      overlay=overlay or {}, rules_cfg=cfg["rule_strategies"], cfg=cfg,
                      token_by_sym={"BONK": {"symbol": "BONK", "mint": "Mint111", "decimals": 5}}, bull=bull)


# ------------------------------------------------------------------ sinais partilhados com os originais

def test_meme_rule_signal_matches_original_truth_table():
    # tabela do código inline antigo do rules_bot (regime e donch), agora partilhado com os forks
    for held in (False, True):
        for bull in (False, True):
            exp = "buy" if bull and not held else ("sell" if not bull and held else "hold")
            assert meme_rule_signal("regime", held, bull, "buy") == (exp, [])
            for d in ("buy", "sell", "hold"):
                if not bull and held:
                    exp = ("sell", ["sol_regime_exit"])
                elif bull and d == "buy" and not held:
                    exp = ("buy", [])
                elif d == "sell" and held:
                    exp = ("sell", [])
                else:
                    exp = ("hold", [])
                assert meme_rule_signal("donch", held, bull, d) == exp


# ------------------------------------------------------------------ criação e validação

def test_create_rule_fork_starts_from_parent_and_never_touches_original(lab):
    parent_file = ROOT / "data" / "meme" / "portfolios" / f"{DONCH}.json"
    st = json.loads(parent_file.read_text()); st.update(usdt=400.0, token=500.0)
    parent_file.write_text(json.dumps(st))
    before = parent_file.read_text()
    eff_parent = P.explain(DONCH, use_overlay=False)[0]
    name, why = fork(DONCH, {"rule": {"donchian": 40}})
    assert (name, why) == (f"{DONCH}__fork1", "created")
    e = R.load()["portfolios"][name]
    assert R.is_rule_fork(e) and e["kind"] == "rule" and e["runner"] == "rules_bot" and e["test_type"] == "rule_donchian"
    assert e["rule"] == "rule_donch_regime_full" and e["variant"] == "full" and e["lineage"] == DONCH
    fs = json.loads(R.port_path(name).read_text())
    assert fs["usdt"] == 400.0 and fs["token"] == 500.0 and fs["asset_mode"] == "token" and fs["strategy"] == f"fork:{name}"
    eff, _prov, errs, _m = P.explain(name, meta=e, use_overlay=False)
    assert errs == [] and eff["rule"]["donchian"] == 40 and eff["gates"]["buy_fraction_usdt"] == 1.0  # herda o _full
    assert parent_file.read_text() == before and P.explain(DONCH, use_overlay=False)[0] == eff_parent
    assert "janela de Donchian (h) 40" in R.describe_fork(e)
    # fork de um fork de regra: mesma linhagem, efetivo = fork1 + diff
    n2, why2 = fork(name, {"gates": {"buy_fraction_usdt": 0.5}})
    assert n2 == f"{DONCH}__fork2" and why2 == "created"
    e2 = R.load()["portfolios"][n2]
    eff2 = P.explain(n2, meta=e2, use_overlay=False)[0]
    assert e2["lineage"] == DONCH and e2["parent"] == name and eff2["rule"]["donchian"] == 40
    assert eff2["gates"]["buy_fraction_usdt"] == 0.5
    # grade: o estado da grade do pai segue para o fork
    n3, _ = fork("grid_sol_2pct", {"rule": {"grid_pct": 0.03, "levels": 3}})
    g3 = json.loads(R.port_path(n3).read_text())
    assert g3["rule_state"] == {"ref": 130.0, "buys_open": 0} and g3["sol"] == 0.3 and g3["usdt"] == 960.0


@pytest.mark.parametrize("parent, diff, msg", [
    (DONCH, {"gates": {"cooldown_seconds": 60}}, "diff_nao_suportado"),
    (DONCH, {"exec": {"mode": "limit"}}, "diff_nao_suportado"),
    (DONCH, {"hours": [1, 2]}, "diff_nao_suportado"),
    (DONCH, {"rule": {"grid_pct": 0.03}}, "diff_nao_suportado"),
    (DONCH, {"limits": {"buy_fraction_usdt_max": 1.0}}, "diff_nao_suportado"),
    (DONCH, {}, "diff_nao_suportado"),
    ("grid_sol_2pct", {"rule": {"donchian": 10}}, "diff_nao_suportado"),
    (DONCH, {"rule": {"ema_fast": 30}}, "params_invalidos"),
    (DONCH, {"gates": {"buy_fraction_usdt": 1.5}}, "params_invalidos"),
    ("BONK_rule_donch_regime", {"gates": {"buy_fraction_usdt": 0.9}}, "params_invalidos"),
    ("rsi_sol_1h", {"rule": {"lo": 75}}, "params_invalidos"),
    ("grid_sol_2pct", {"exits": {"enabled": True, "tp": 0.0}}, "params_invalidos"),
])
def test_rule_fork_diff_validation(lab, parent, diff, msg):
    name, why = fork(parent, diff, dry_run=True)
    assert name is None and why.startswith(msg), why


def test_rule_fork_supports_exits_and_regime_filter_but_originals_do_not(lab):
    name, why = fork("grid_sol_2pct", {"exits": {"enabled": True}, "regime_filter": {"enabled": True}}, dry_run=True)
    assert (name, why) == ("grid_sol_2pct__fork1", "dry_run")
    # criteria de texto nunca em forks de regra
    assert fork("grid_sol_2pct", {"rule": {"levels": 3}}, criteria={"x": 1}, dry_run=True)[1].startswith("criterios")
    # no original continua a ser erro de validação (os originais nunca mudam)
    doc = json.loads((LAB / "params.json").read_text())
    doc["portfolios"]["grid_sol_2pct"] = {"exits": {"enabled": True}}
    m = P.classify("grid_sol_2pct", registry={"portfolios": {}})
    eff, _p, errs = P.resolve(m, doc, None, {"portfolios": {}})
    assert any("só em forks de regra" in x for x in errs + P.validate(eff, m))


# ------------------------------------------------------------------ executor (rules_bot.RuleForks)

def test_executor_runs_rule_forks_with_their_own_params(lab):
    cfg = lab
    orig_files = {p: p.read_text() for p in (ROOT / "data" / "meme" / "portfolios").glob("*.json")}
    orig_files[ROOT / "data" / "portfolio_grid_sol_2pct.json"] = (ROOT / "data" / "portfolio_grid_sol_2pct.json").read_text()
    f40, _ = fork(DONCH, {"rule": {"donchian": 40}})
    f20, _ = fork(DONCH, {"gates": {"buy_fraction_usdt": 0.5}})
    for n in (f40, f20):
        backdate(n)
    book = make_book(sol_bars(up=True), bonk_bars())
    # o original (Donchian 20, SOL em alta) compraria nesta barra
    assert book.meme_indicators("BONK")["donchian20_signal"] == "buy" and book.sol_indicators()["sol_regime_bull"]
    forks = RB.RuleForks(log=lambda *a, **k: None)
    snap = step(forks, book, cfg)
    assert set(snap) == {f40, f20}
    assert snap[f40]["last_signal"] == "hold" and snap[f40]["trades"] == 0      # janela de 40 h: sem rompimento
    assert snap[f20]["last_signal"] == "buy" and snap[f20]["trades"] == 1
    s20 = json.loads(R.port_path(f20).read_text())
    assert s20["usdt"] == pytest.approx(500.0) and s20["token"] > 0 and s20["entry_price"]   # 50% do USDT
    trades = _jl(ROOT / "logs" / "meme_trades.jsonl")
    assert [(t["portfolio"], t["side"], t["strategy"]) for t in trades] == [(f20, "buy", f"fork:{f20}")]
    assert trades[0]["fill"]["fill_mode"] == "mark"
    decs = _jl(ROOT / "logs" / "lab_decisions.jsonl")
    assert {d["portfolio"] for d in decs} == {f40, f20} and all(d["model"] == "rule" for d in decs)
    assert [d["params_rule"]["donchian"] for d in decs if d["portfolio"] == f40] == [40]
    assert _jl(R.eq_path(f20))[-1]["equity"] > 0 and _jl(R.eq_path(f40))
    # a mesma barra não age duas vezes
    snap2 = step(forks, book, cfg)
    assert snap2[f20]["trades"] == 1 and len(_jl(ROOT / "logs" / "lab_decisions.jsonl")) == len(decs)
    # os originais nunca são tocados pelo executor dos forks
    for p, txt in orig_files.items():
        assert p.read_text() == txt, p
    assert not (ROOT / "logs" / "meme_decisions.jsonl").exists() and not (ROOT / "logs" / "trades.jsonl").exists()


def test_grid_fork_differs_from_parent_and_regime_filter_blocks_buys(lab):
    cfg = lab
    wide, _ = fork("grid_sol_2pct", {"rule": {"grid_pct": 0.05}})
    filt, _ = fork("grid_sol_2pct", {"regime_filter": {"enabled": True}})
    for n in (wide, filt):
        backdate(n)
    book = make_book(sol_bars(up=False, last=126.0))   # SOL a cair (EMA12 < EMA26) e −3,1% contra a ref 130
    ind = book.sol_indicators()
    assert not ind["sol_regime_bull"]
    assert grid_signal({"ref": 130.0, "buys_open": 0}, ind["close"], 0.02, 4)[0] == "buy"   # o pai compraria
    snap = step(RB.RuleForks(log=lambda *a, **k: None), book, cfg, sol_px=126.0)
    assert snap[wide]["last_signal"] == "hold" and snap[wide]["trades"] == 0
    assert snap[filt]["last_signal"] == "hold" and "sol_regime_bear_block_buy" in snap[filt]["gate_reasons"]
    d = [x for x in _jl(ROOT / "logs" / "lab_decisions.jsonl") if x["portfolio"] == filt][-1]
    assert d["chosen_action"] == "buy" and d["final_action"] == "hold"
    # sem filtro de regime e com a grade do pai: compra
    plain, _ = fork(filt, {"regime_filter": {"enabled": False}})
    backdate(plain)
    snap = step(RB.RuleForks(log=lambda *a, **k: None), book, cfg, sol_px=126.0)
    assert snap[plain]["last_signal"] == "buy" and json.loads(R.port_path(plain).read_text())["rule_state"]["buys_open"] == 1


def test_exits_on_rule_fork_take_profit_and_reentry_block(lab):
    cfg = lab
    pf = ROOT / "data" / "meme" / "portfolios" / "BONK_rule_regime.json"
    st = json.loads(pf.read_text()); st.update(usdt=0.0, token=1000.0)
    pf.write_text(json.dumps(st))
    name, _ = fork("BONK_rule_regime", {"exits": {"enabled": True, "tp": 0.05}})
    s = json.loads(R.port_path(name).read_text()); s["entry_price"] = 1.0; s["peak_price"] = 1.0
    R.port_path(name).write_text(json.dumps(s))
    backdate(name)
    book = make_book(sol_bars(up=True), bonk_bars())
    snap = step(RB.RuleForks(log=lambda *a, **k: None), book, cfg, bonk_px=1.1)
    assert snap[name]["last_signal"] == "sell" and snap[name]["gate_reasons"] == ["take_profit"]
    s = json.loads(R.port_path(name).read_text())
    assert s["token"] == 0.0 and s["usdt"] > 1000 and s["reentry_block_until"] > time.time()
    # na barra seguinte o regime (SOL em alta) pediria compra, mas a reentrada está bloqueada
    book.sol.append(dict(book.sol[-1], ts=book.sol[-1]["ts"] + HOUR))
    book.memes["BONK"].append(dict(book.memes["BONK"][-1], ts=book.memes["BONK"][-1]["ts"] + HOUR))
    forks = RB.RuleForks(log=lambda *a, **k: None)
    snap = step(forks, book, cfg, bonk_px=1.1)
    assert snap[name]["last_signal"] == "hold" and "reentry_cooldown" in snap[name]["gate_reasons"]


def test_registry_hot_reload_and_lab_bot_skips_rule_forks(lab):
    cfg = lab
    forks = RB.RuleForks(log=lambda *a, **k: None)
    book = make_book(sol_bars(up=True), bonk_bars())
    assert step(forks, book, cfg) == {}
    name, _ = fork(DONCH, {"rule": {"donchian": 30}})
    snap = step(forks, book, cfg)          # sem reiniciar: o registry mudou (mtime) e o fork entra
    assert list(snap) == [name] and not forks.refresh()
    reg = R.load()
    gated, _ = R.create_fork("relaxed", {"gates": {"cooldown_seconds": 600}}, "t", dry_run=True)
    assert gated == "relaxed__fork1"
    assert [n for n, e in reg["portfolios"].items() if R.is_rule_fork(e)] == [name]
    import inspect
    from bot import lab_bot
    assert "is_rule_fork" in inspect.getsource(lab_bot.Lab.active)


def test_fail_closed_on_invalid_params_holds_and_logs(lab):
    cfg = lab
    name, _ = fork(DONCH, {"gates": {"buy_fraction_usdt": 0.5}})
    backdate(name)
    doc = json.loads((LAB / "params.json").read_text())
    doc["portfolios"][name] = {"rule": {"ema_fast": 40}}            # ema_fast ≥ ema_slow: inválido
    (ROOT / "params.json").write_text(json.dumps(doc))
    P.STORE.refresh(force=True)
    logs = []
    forks = RB.RuleForks(log=lambda *a, **k: logs.append(" ".join(map(str, a))))
    snap = step(forks, make_book(sol_bars(up=True), bonk_bars()), cfg)
    assert snap[name]["last_signal"] == "hold" and snap[name]["gate_reasons"] == ["params_invalidos"]
    assert snap[name]["params_ok"] is False and snap[name]["trades"] == 0
    assert any("parâmetros inválidos" in l for l in logs)
    assert not (ROOT / "logs" / "meme_trades.jsonl").exists()
    # estado em falta → hold com erro, sem afetar os outros forks
    R.port_path(name).unlink()
    forks.refresh(force=True)
    out = step(forks, make_book(sol_bars(up=True), bonk_bars()), cfg)
    assert out[name]["last_signal"] == "hold" and "error" in out[name]


# ------------------------------------------------------------------ night_cli e tuner noturno

def _cli():
    spec = importlib.util.spec_from_file_location("night_cli_rules", LAB / "scripts" / "night_cli.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(cli, capsys, *argv):
    code = cli.main(list(argv))
    out = capsys.readouterr().out
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, out


def test_night_cli_fork_with_rule_parent(lab, capsys):
    cli = _cli()
    code, out = _run(cli, capsys, "fork", "--parent", DONCH, "--diff", '{"rule": {"donchian": 40}}', "--reason", REASON, "--dry-run")
    assert code == 0 and out["ok"] and out["fork"] == f"{DONCH}__fork1" and out["status"] == "dry_run"
    assert DONCH + "__fork1" not in R.load()["portfolios"]
    for diff, msg in (('{"gates": {"cooldown_seconds": 600}}', "não permitido"),
                      ('{"rule": {"donchian": 300}}', "fora dos limites"),
                      ('{"rule": {"grid_pct": 0.03}}', "não permitido"),
                      ('{"rule": {"donchian": 20}}', "sem efeito")):
        code, out = _run(cli, capsys, "fork", "--parent", DONCH, "--diff", diff, "--reason", REASON, "--dry-run")
        assert code == 2 and msg in out["error"], (diff, out)
    # _full aceita fração até 1; o não-full fica nos 0,5
    code, out = _run(cli, capsys, "fork", "--parent", DONCH, "--diff", '{"gates": {"buy_fraction_usdt": 0.6}}', "--reason", REASON, "--dry-run")
    assert code == 0, out
    code, out = _run(cli, capsys, "fork", "--parent", "BONK_rule_donch_regime", "--diff", '{"gates": {"buy_fraction_usdt": 0.6}}',
                     "--reason", REASON, "--dry-run")
    assert code == 2 and "fora dos limites" in out["error"]
    # criação real conta para os limites da noite e regista who=claude-night
    code, out = _run(cli, capsys, "fork", "--parent", "rsi_sol_1h", "--diff", '{"rule": {"lo": 25, "hi": 75}}', "--reason", REASON)
    assert code == 0 and out["fork"] == "rsi_sol_1h__fork1" and "regra" in (out["effective"] or "")
    e = R.load()["portfolios"]["rsi_sol_1h__fork1"]
    assert e["who"] == "claude-night" and R.is_rule_fork(e)
    txt = "\n".join(cli.sec_tunables())
    assert "rule_donchian: rule.donchian=20 [5, 120]" in txt and "rule.grid_pct=0.02 [0.005, 0.1]" in txt
    assert "gates.buy_fraction_usdt=0.25 [0.05, 0.5]" in txt


def test_nightly_rule_replay_candidate_creates_real_fork(lab, monkeypatch):
    pytest.importorskip("numpy")
    from bot import nightly as N, tuner as T
    calls = []

    def fake(meta, bars_sol, bars_meme, conf=None, eff=None):
        calls.append((meta["name"], eff["rule"]["donchian"]))
        return {"status": "candidate", "current": (-5.0, -3.0), "best_diff": {"donchian": 24}, "best": (1.0, 2.0), "bars": 720}
    monkeypatch.setattr(T, "rule_search", fake)
    book = make_book(sol_bars(), bonk_bars())
    m = dict(R.originals()[DONCH], name=DONCH, origin="original")
    reg = R.load()
    line, note = N.rule_tune(DONCH, DONCH, m, reg, book, "2026-10-03", False, {"per_lineage_days": 7, "total": 40})
    assert note is None and f"`{DONCH}__fork1`" in line and "(created)" in line
    e = R.load()["portfolios"][f"{DONCH}__fork1"]
    assert e["params_diff"] == {"rule": {"donchian": 24}} and e["who"] == "nightly" and R.is_rule_fork(e)
    assert calls == [(DONCH, 20)]
    # cap de 7 dias por linhagem: o candidato seguinte só vira nota
    line, note = N.rule_tune(DONCH, DONCH, m, R.load(), book, "2026-10-03", False, {"per_lineage_days": 7, "total": 40})
    assert "cap_1_fork_per_7d" in note and "fork `None`" in line
    # sem candidato: só relatório
    monkeypatch.setattr(T, "rule_search", lambda *a, **k: {"status": "no_improvement", "current": (0, 0)})
    line, note = N.rule_tune("rsi_sol_1h", "rsi_sol_1h", dict(R.originals()["rsi_sol_1h"], name="rsi_sol_1h"), R.load(), book,
                             "2026-10-03", False, {"per_lineage_days": 7, "total": 40})
    assert "no_improvement" in line and note is None


def test_tuner_rule_search_respects_bounds(monkeypatch):
    pytest.importorskip("numpy")
    from bot import tuner as T
    doc = json.loads((LAB / "params.json").read_text())
    m = P.classify(DONCH, registry={"portfolios": {}})
    eff, _p, _e = P.resolve(m, doc, None, {"portfolios": {}})
    eff["rule"]["donchian"] = 118          # perto do teto de tuning.bounds (120); janela maior que o início do histórico
    seen = []
    real = T._bound
    monkeypatch.setattr(T, "_bound", lambda v, b, i: seen.append((b, real(v, b, i))) or real(v, b, i))
    sol = sol_bars(200)
    meme = [dict(b, high=b["close"] * 1.01, low=b["close"] * 0.99) for b in sol]
    r = T.rule_search(dict(R.originals()[DONCH], name=DONCH), sol, meme, conf={"capital": 1000.0}, eff=eff)
    assert r["status"] in ("candidate", "no_improvement")
    don = [v for b, v in seen if b == [5, 120]]
    assert don and max(don) == 120 and all(isinstance(v, int) for v in don)
