"""Backtest: réplica dos bots sobre dados sintéticos, comparada com as funções do lab (tuner.replay, portões ao vivo).

Corre o motor completo (sol_bot, meme_bot, lab_bot, rules_bot e bot real) numa árvore temporária, com um cliente de
modelos falso e determinístico, sem rede nem ficheiros do run ao vivo."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import numpy as np
import pytest

from bot.paths import ROOT

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parents[1]
CREATED = ("config.json", "memecoins.json", "params.json", "models.json", "criteria_baseline.json", "criteria_v2.json",
           "data", "logs", "reports")
START = 1_790_000_000 // 3600 * 3600
DAYS = 2


class FakeCache:
    def commit(self):
        pass


class FakeClient:
    """Respostas determinísticas por (modelo, estado): metade compras/vendas fortes, resto hold."""

    def __init__(self):
        self.criteria = {"lab_baseline": (None, {}, "x"), "lab_v2": (None, {}, "y"), "realbot": ("von-latest", {}, "z")}
        self.cache = FakeCache()
        self.calls = 0

    def register(self, cid, crit, model_field=None):
        self.criteria[cid] = (model_field, crit, cid)
        return cid

    def get(self, model, cid, state):
        self.calls += 1
        h = int(hashlib.sha256(f"{model}|{cid}|{state}".encode()).hexdigest(), 16)
        act = ("buy", "sell", "hold", "buy")[h % 4]
        conf = 0.30 + (h >> 8) % 60 / 100.0
        top = 0.5 + (h >> 16) % 40 / 100.0
        probs = {act: top, "hold" if act != "hold" else "buy": 1 - top - 0.05, "sell" if act != "sell" else "buy": 0.05}
        return {"chosen_action": act, "probabilities": probs, "confidence": conf, "skip_noul": ((h >> 24) % 70) / 100.0,
                "fail_closed": False, "ok": True}


def _clean():
    for n in CREATED:
        p = ROOT / n
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


@pytest.fixture
def tree():
    _clean()
    for n in ("config.json", "memecoins.json", "params.json", "models.json", "criteria_baseline.json", "criteria_v2.json"):
        shutil.copy(LAB / n, ROOT / n)
    from bot import lab_registry as R
    reg = {"portfolios": {}, "lineages": {}}
    for h in R.hypothesis_defs():
        if h["name"] in ("h1_exits_von_relaxed", "h3_limit_poorjev_relaxed", "h2_ensemble_sol", "h4_hours_von_relaxed",
                         "h1_exits_BONK_poorjev_relaxed"):
            reg["portfolios"][h["name"]] = dict(h, status="active", lineage=h["name"], parent=None, strategy=f"hyp:{h['name']}")
    (ROOT / "data" / "lab").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "lab" / "registry.json").write_text(json.dumps(reg))
    from bot import params as P
    P.STORE.refresh(force=True)
    yield
    _clean()


def _synthetic(seed=11):
    from backtest import data as D
    rng = np.random.default_rng(seed)
    syms = ["SOL", "BONK", "WIF", "POPCAT", "FARTCOIN", "PNUT", "MEW", "GOAT"]
    m0 = START - 86400
    end = START + DAYS * 86400
    n = (end - m0) // 60
    out = {"minute": {}, "hourly": {}, "coverage": {}, "sources": {}}
    for k, s in enumerate(syms):
        base = 100.0 if s == "SOL" else 0.5 + k
        vol = 0.0012 if s == "SOL" else 0.004
        c = base * np.exp(np.cumsum(rng.normal(0, vol, n)))
        o = np.r_[c[0], c[:-1]]
        hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 2, n)))
        lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 2, n)))
        rows = [(m0 + 60 * i, o[i], hi[i], lo[i], c[i], 1.0) for i in range(n)]
        out["minute"][s] = D.MinuteSeries(rows, m0, end)
        hc = base * np.exp(np.cumsum(rng.normal(0, vol * 8, 40 * 24)))
        h0 = START - 40 * 24 * 3600
        bars = [{"ts": h0 + 3600 * i, "open": hc[i], "high": hc[i] * 1.004, "low": hc[i] * 0.996, "close": hc[i], "volume": 1}
                for i in range(40 * 24)]
        # junta as barras de 1 h dentro da janela, agregadas dos minutos (as do fim continuam a série)
        ms = out["minute"][s]
        for hstart in range(START - 86400, end, 3600):
            i0 = (hstart - m0) // 60
            sl = slice(i0, i0 + 60)
            bars = [b for b in bars if b["ts"] != hstart] + [{"ts": hstart, "open": float(ms.o[sl][0]), "high": float(ms.h[sl].max()),
                                                              "low": float(ms.l[sl].min()), "close": float(ms.c[sl][-1]), "volume": 1}]
        out["hourly"][s] = sorted([b for b in bars if b["ts"] < end], key=lambda b: b["ts"])
    g = np.arange(m0, end + 1, 5)
    sol = out["minute"]["SOL"]
    idx = np.clip((g - m0) // 60 - 1, 0, len(sol.c) - 1)
    out["sol_grid"] = (g, sol.c[idx] * (1 + 0.0002 * np.sin(g / 7.0)))
    return out, end


def _engine(data, end, items_filter=None):
    from backtest import catalog as CAT, engine as EN
    from bot.backends import load_models_cfg
    cfg = json.loads((ROOT / "config.json").read_text())
    mem = json.loads((ROOT / "memecoins.json").read_text())
    items = CAT.build(load_models_cfg(), jev_ready=False)
    if items_filter:
        items = [it for it in items if items_filter(it)]
    from jev_trader.config import load_params
    rb = {p: load_params(REPO / "config" / "params.json", p)[0] for p in ("relaxed_paper", "relaxed_exits_paper")}
    slip = {s: 5.0 for s in ["SOL"] + [t["symbol"] for t in mem["tokens"]]}
    client = FakeClient()
    eng = EN.Engine(data=data, start=START, end=end, step=60, items=items, client=client, cfg=cfg, memecoins=mem,
                    slip_bps=slip, crit_files={}, realbot_params=rb).setup()
    return eng, client, items


def test_engine_runs_all_bots_and_restores_modules(tree):
    import bot.lib as L
    data, end = _synthetic()
    eng, client, items = _engine(data, end)
    eng.run()
    rb = eng.run_realbot({"A": "relaxed_paper", "B": "relaxed_exits_paper"})
    eng.env.uninstall()
    assert abs(L.time.time() - time.time()) < 5          # relógio real reposto
    names = {it["name"] for it in items}
    assert {"relaxed", "meme_BONK_relaxed", "grid_sol_2pct", "BONK_rule_regime", "h1_exits_von_relaxed",
            "h3_limit_poorjev_relaxed", "h2_ensemble_sol"} <= names
    by = {}
    for t in eng.env.trades:
        by.setdefault(t["portfolio"], []).append(t)
    assert by.get("relaxed") and by.get("meme_BONK_relaxed")
    # contabilidade: equity final = usdt + quantidade × preço; saldos nunca negativos
    for n, p in eng.ports.items():
        assert p["usdt"] >= -1e-9 and (p.get("sol") or 0) >= 0 and (p.get("token") or 0) >= 0, n
        r = eng.rec.rows[n][-1]
        assert abs(r["equity"] - (p["usdt"] + r["q"] * r["price"])) < 1e-6
    # teto de trades/h e cooldown do portão (relaxed: 8/h, 120 s)
    ts = sorted(t["ts"] for t in by["relaxed"])
    assert all(b - a >= 120 for a, b in zip(ts, ts[1:]))
    assert all(sum(1 for x in ts if t - 3600 < x <= t) <= 8 for t in ts)
    # memecoins decidem em rotação: cada moeda a cada 8 min (8 ativos na rotação? não: 7 moedas → 7 min)
    bt = sorted({int(t["ts"]) for t in by["meme_BONK_relaxed"]})
    assert all((x - START) // 60 % 7 == 0 for x in bt)
    # regras só agem no fecho de uma barra de 1 h
    for n in ("grid_sol_2pct", "rsi_sol_1h", "BONK_rule_regime_full", "BONK_rule_donch_regime"):
        assert all(int(t["ts"]) % 3600 == 0 for t in by.get(n, [])), n
    # ordens limite: compra só quando a mínima do minuto cruza o limite, fill ao preço limite
    lim = [t for t in by.get("h3_limit_poorjev_relaxed", []) if t["fill"].get("fill_mode") == "limit_sim"]
    for t in lim:
        f = t["fill"]
        assert (f["mark_price"] < f["limit_price"]) if t["side"] == "buy" else (f["mark_price"] > f["limit_price"])
    # H4: só nas horas permitidas
    from bot import params as P
    hours = P.effective("h4_hours_von_relaxed").get("hours")
    if hours:
        from datetime import datetime
        from backtest.simenv import BRT
        assert all(datetime.fromtimestamp(t["ts"], tz=BRT).hour in hours for t in by.get("h4_hours_von_relaxed", []))
    # bot real: compras do tamanho do bot (min(buy_usdt, max_buy_usdt) × confiança) e livro B com teto de exposição
    assert rb["A"]["trades"] and rb["B"]["decisions"] == rb["A"]["decisions"]
    for t in rb["A"]["trades"]:
        if t["side"] == "buy" and not t["capped"]:
            assert abs(t["in_amount_ui"] - round(1.0 * t["conf"], 6)) < 1e-5
    assert all((t.get("exposure_after") or 0) <= 0.5 + 1e-6 for t in rb["B"]["trades"] if t["side"] == "buy")


def test_relaxed_matches_tuner_replay_trade_timing(tree):
    """As compras/vendas do `relaxed` no motor (sol_bot ao vivo) = as do tuner.replay (réplica do lab) sobre as mesmas
    decisões: mesmos portões (confiança, margem, skip, cooldown, trades/h, mínimos)."""
    from bot import tuner as TU
    from bot import params as P
    import bot.sol_bot as SB
    data, end = _synthetic(seed=5)
    eng, client, _ = _engine(data, end, items_filter=lambda it: it["name"] in ("baseline", "relaxed"))
    rows = []
    orig = SB.apply_and_maybe_trade

    def spy(name, *a, **k):
        r = orig(name, *a, **k)
        if name == "relaxed":
            rows.append(dict(r))
        return r
    SB.apply_and_maybe_trade = spy
    try:
        eng.run()
    finally:
        SB.apply_and_maybe_trade = orig
        eng.env.uninstall()
    sim_ts = [int(t["ts"]) for t in eng.env.trades if t["portfolio"] == "relaxed"]
    eff = P.effective("relaxed")
    px = [(r["ts"], r["price_usd"]) for r in rows]
    dec = [{"ts": r["ts"], "chosen_action": r["chosen_action"], "confidence": r["confidence"], "probabilities": r["probabilities"],
            "skip_noul": r["skip_noul"], "price_usd": r["price_usd"]} for r in rows]
    stamps = []
    orig_done = TU.Sim._done
    TU.Sim._done = lambda self, ts: (stamps.append(int(ts)), orig_done(self, ts))[1]
    try:
        out = TU.replay({"kind": "gated", "asset": "SOL", "profile": "relaxed"}, eff, START, end,
                        (eng.sol0, eng.usdt0), 7.0, data={"dec": dec, "px": px})
    finally:
        TU.Sim._done = orig_done
    assert out["trades"] == len(sim_ts) > 5
    assert stamps == sim_ts
