"""Backtest: moedas extra (overlay só do backtest), rotação com cadência fixa, runs com etiqueta no histórico e o
motor a correr as moedas novas com os MESMOS parâmetros das famílias meme (cliente de modelos falso, sem rede)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from bot.paths import ROOT
from test_backtest_replay import START, FakeClient, _synthetic, tree  # noqa: F401  (fixture)

LAB = Path(__file__).resolve().parents[1]


def _doc():
    from backtest import extra_assets as XA
    return XA.load()


def test_assets_extra_file_is_valid_and_checked():
    from backtest import extra_assets as XA
    doc = _doc()
    syms = XA.symbols(doc)
    assert syms == ["JUP", "JTO", "PYTH", "RAY", "BOME", "PENGU", "TRUMP", "MOODENG"]
    live = {t["symbol"] for t in json.loads((LAB / "memecoins.json").read_text())["tokens"]}
    assert not set(syms) & live                     # só moedas novas; o memecoins.json do lab não as tem
    assert all(t["quote_slippage_bps"] >= 12.7 for t in doc["tokens"])
    bad = json.loads(json.dumps(doc))
    bad["tokens"][0]["mint"] = "0OIl-not-base58"
    bad["tokens"][1]["sources"] = [["ftx", "JTOUSDT"]]
    bad["tokens"].append(dict(bad["tokens"][2]))
    errs = XA.check(bad)
    assert any("mint inválido" in e for e in errs) and any("fonte inválida" in e for e in errs)
    assert any("repetido" in e for e in errs)


def test_only_assets_and_merged_memecoins_do_not_touch_base():
    from backtest import extra_assets as XA
    doc = _doc()
    base = json.loads((LAB / "memecoins.json").read_text())
    base_copy = json.loads(json.dumps(base))
    base_syms = [t["symbol"] for t in base["tokens"]]
    assert XA.parse_only(None, doc, base_syms) is None
    assert XA.parse_only("extra", doc, base_syms) == XA.symbols(doc)
    assert XA.parse_only("jup, bonk", doc, base_syms) == ["JUP", "BONK"]
    with pytest.raises(ValueError):
        XA.parse_only("DOGE", doc, base_syms)
    with pytest.raises(ValueError):
        XA.parse_only("extra", None, base_syms)
    m = XA.merged_memecoins(base, doc, XA.symbols(doc))
    assert [t["symbol"] for t in m["tokens"]] == XA.symbols(doc)
    assert all(t["extra"] and t["mint"] and isinstance(t["decimals"], int) for t in m["tokens"])
    assert m["start_usdt_each"] == base["start_usdt_each"]
    allm = XA.merged_memecoins(base, doc, None)
    assert [t["symbol"] for t in allm["tokens"]] == base_syms + XA.symbols(doc)
    assert base == base_copy                         # o dicionário de base não muda
    with pytest.raises(ValueError):                  # o overlay só acrescenta moedas novas
        XA.merged_memecoins(base, {"tokens": [dict(base["tokens"][0])]}, None)


def test_rotation_period_keeps_live_cadence():
    from backtest.engine import rotation_syms
    s7 = ["A", "B", "C", "D", "E", "F", "G"]
    # período = número de moedas → exatamente a rotação ao vivo (uma moeda por minuto)
    for k in range(30):
        assert rotation_syms(s7, START + 60 * k, START) == [s7[k % 7]]
        assert rotation_syms(s7, START + 60 * k, START, 7) == [s7[k % 7]]
    s8 = s7 + ["H"]
    seen = {s: [] for s in s8}
    for k in range(70):
        for s in rotation_syms(s8, START + 60 * k, START, 7):
            seen[s].append(k)
    for s, ks in seen.items():
        assert all(b - a == 7 for a, b in zip(ks, ks[1:])), s     # cada moeda a cada 7 min
    assert seen["A"] == seen["H"]                                   # 8 moedas em 7 lugares: A e H partilham o minuto


def _summary(run_id, days, end, tag=None):
    return {"run_id": run_id, "generated_brt": "2026-10-07T00:00:00-03:00", "tag": tag,
            "window": {"start_brt": "2026-09-06T09:00:00-03:00" if days == 30 else "2026-04-09T09:00:00-03:00",
                       "end_brt": end, "days": days, "step_s": 60},
            "assets": {"SOL": {"ret_pct": 1.0}, "BONK": {"ret_pct": 2.0}}, "winner": {"by_skill": "a", "by_pnl": "a", "by_verdict": None},
            "portfolios": [{"name": "a", "family": "Meme · von", "skill": 1.0, "pnl_pct": 1.0, "vs_bh": 1.0, "verdict": "inconclusiva",
                            "max_dd_pct": -1.0, "trades": 1}], "realbot": []}


def test_tagged_runs_never_move_latest_and_stay_out_of_monthly_history(tmp_path):
    from backtest import history as H
    for rid, days, tag in (("bt30_2026-10-06", 30, None), ("bt30x_2026-10-06", 30, "moedas_novas"),
                           ("bt180x_2026-10-06", 180, "moedas_novas")):
        d = tmp_path / rid
        d.mkdir()
        (d / "summary.json").write_text(json.dumps(_summary(rid, days, "2026-10-06T09:00:00-03:00", tag)))
    (tmp_path / "latest").write_text("bt30_2026-10-06\n")
    assert H.latest_after(tmp_path, "bt30x_2026-10-06", "30d", "2026-10-06T09:00:00-03:00", tag="moedas_novas") == "bt30_2026-10-06"
    assert H.latest_after(tmp_path, "bt30x_2026-10-06", "30d", "2026-10-07T09:00:00-03:00") == "bt30x_2026-10-06"
    idx = H.write_history(tmp_path)
    by = {e["run_id"]: e for e in idx["runs"]}
    assert by["bt30x_2026-10-06"]["tag"] == "moedas_novas" and by["bt30x_2026-10-06"]["kind"] == "30d"
    assert by["bt180x_2026-10-06"]["kind"] == "180d" and by["bt30_2026-10-06"]["tag"] is None
    md = (tmp_path / "history.md").read_text()
    assert "**bt30_2026-10-06**" in md and "**bt30x_2026-10-06**" not in md   # fora da tabela mensal
    assert "## 180 dias seguidos" not in md                                   # o run longo marcado não é o resumo longo
    assert "bt30x_2026-10-06 (moedas_novas, 30d)" in md


def test_dashboard_index_keeps_tag(tmp_path):
    from dashboard import backtest_view as BV
    e = BV.index_entry("bt180x_2026-10-06", _summary("bt180x_2026-10-06", 180, "2026-10-06T09:00:00-03:00", "moedas_novas"))
    assert e["tag"] == "moedas_novas" and e["kind"] == "180d"


def test_engine_runs_extra_coins_with_meme_params(tree):
    """Moedas novas pelo mesmo caminho meme: overlay no memecoins.json do instantâneo, símbolos acrescentados ao
    registry, H1 semeada, catálogo filtrado, cadência de 7 min e o "só segurar" a partir do B&H da moeda."""
    from backtest import catalog as CAT, engine as EN, extra_assets as XA, metrics as MET
    from bot import params as P
    from bot.backends import load_models_cfg
    import bot.lab_bot  # noqa: F401  — importado ANTES do overlay: TOKENS lido do memecoins.json de base
    doc = _doc()
    xs = ["JUP", "JTO"]
    base = json.loads((ROOT / "memecoins.json").read_text())
    mem = XA.merged_memecoins(base, doc, xs)
    (ROOT / "memecoins.json").write_text(json.dumps(mem))
    saved = XA.patch_symbols(xs, tokens=mem["tokens"])
    try:
        made = XA.seed_hypotheses(ROOT / "data" / "lab" / "registry.json", xs, "2026-10-18T00:00:00-03:00")
        assert "h1_exits_JUP_poorjev_relaxed" in made and "h1_exits_JTO_poorjev_relaxed" in made
        P.STORE.refresh(force=True)
        # mesmos parâmetros efetivos da família meme (sem camada por moeda): JUP relaxed == BONK relaxed
        assert P.effective("meme_JUP_relaxed")["gates"] == P.effective("meme_BONK_relaxed")["gates"]
        assert P.effective("h1_exits_JUP_poorjev_relaxed")["exits"] == P.effective("h1_exits_BONK_poorjev_relaxed")["exits"]
        data, end = _synthetic()
        # séries sintéticas: as moedas novas reaproveitam as de duas memecoins do gerador
        for new, old in zip(xs, ("BONK", "WIF")):
            data["minute"][new] = data["minute"].pop(old)
            data["hourly"][new] = data["hourly"].pop(old)
        items = CAT.build(load_models_cfg(), jev_ready=False)
        items = XA.filter_items(items, xs, XA.wanted_names(doc, xs))
        names = {it["name"] for it in items}
        assert names == {f"meme_{s}_{p}" for s in xs for p in ("baseline", "relaxed")} | \
            {f"{s}_poorjev_relaxed" for s in xs} | {f"h1_exits_{s}_poorjev_relaxed" for s in xs}
        cfg = json.loads((ROOT / "config.json").read_text())
        slip = {"SOL": 5.0, **{s: 12.7 for s in xs}}
        eng = EN.Engine(data=data, start=START, end=end, step=60, items=items, client=FakeClient(), cfg=cfg, memecoins=mem,
                        slip_bps=slip, crit_files={}, realbot_params={}, meme_period_min=7).setup()
        assert eng.meme_extra == ["poorjev"]          # poorjev chamado sem precisar de {SYM}_poorjev_baseline
        eng.run()
        eng.env.uninstall()
        by = {}
        for t in eng.env.trades:
            by.setdefault(t["portfolio"], []).append(t)
        assert by.get("meme_JUP_relaxed") and by.get("h1_exits_JUP_poorjev_relaxed")
        for n in ("meme_JUP_relaxed", "JTO_poorjev_relaxed"):
            off = 0 if n.startswith("meme_JUP") else 1
            assert all(((int(t["ts"]) - START) // 60) % 7 == off for t in by.get(n, [])), n   # cadência de 7 min
        assert eng.counts["meme_decisions"] > 0
        bh = XA.buy_hold_rows(eng.rec.rows["meme_JUP_baseline"])
        r0, r1 = bh[0], bh[-1]
        assert abs(r1["equity"] / r0["equity"] - r1["price"] / r0["price"]) < 1e-9          # 100% na moeda
        v = MET.verdict("JUP_buy_hold", {"kind": "buy_hold"}, bh, [], START, end)
        assert abs(v["stats"]["ex_bh"]) < 1e-6 and v["stats"]["trades"] == 0
        assert XA.buy_hold_item("JUP")["family"] == XA.BH_FAMILY
    finally:
        XA.unpatch_symbols(saved)
        P.STORE.refresh(force=True)


def test_pass_rule_and_hourly_basis():
    import importlib.util
    import numpy as np
    from backtest import data as D
    spec = importlib.util.spec_from_file_location("nmr", LAB / "scripts" / "novas_moedas_report.py")
    nmr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nmr)
    ok = {"skill": 5.0, "vs_bh": 1.0, "months_pos": 3}
    assert nmr.passes(ok) == (True, "passa")
    for k, v in (("skill", -0.1), ("vs_bh", -1.0), ("months_pos", 2)):
        assert nmr.passes(dict(ok, **{k: v}))[0] is False
    assert nmr.passes(None)[0] is False
    # correlação de 1 h: a mesma série (com ruído pequeno) correlaciona ~1; série independente não
    rng = np.random.default_rng(3)
    t0, n = START, 24 * 60 * 5
    c = 1.0 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    rows = [(t0 + 60 * i, c[i], c[i], c[i], c[i], 1.0) for i in range(n)]
    ms = D.MinuteSeries(rows, t0, t0 + 60 * n)
    bars = [{"ts": t0 + 3600 * h, "close": float(c[60 * h + 59]) * (1 + rng.normal(0, 1e-4))} for h in range(n // 60)]
    b = D.basis_check_1h(ms, bars, t0, t0 + 60 * n)
    assert b["corr_ret_1h"] > 0.99 and b["n_1h"] >= 48
    other = [{"ts": x["ts"], "close": float(np.exp(rng.normal(0, 0.01)))} for x in bars]
    assert D.basis_check_1h(ms, other, t0, t0 + 60 * n)["corr_ret_1h"] < 0.5
    assert D.basis_check_1h(ms, bars[:10], t0, t0 + 60 * n) is None
