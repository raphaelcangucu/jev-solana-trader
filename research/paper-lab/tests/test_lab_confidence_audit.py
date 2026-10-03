"""bot/confidence_audit.py (auditoria por percentil) e a sua ligação em sol_bot.night_review."""
import copy
import json
from datetime import datetime

import pytest

from bot import confidence_audit as CA

T0 = datetime.fromisoformat("2026-09-26T01:00:00-03:00").timestamp()
BASE = {"version": "baseline",
        "action": {"instructions": "buy on strength only when the book can absorb it",
                   "criteria": {"buy": "the move is strong and depth is not thin", "sell": "the move is fading or fees are climbing",
                                "hold": "anything else"}},
        "skip_this_cycle": {"instructions": "conditions are too hostile to trade at all"}}


def dec(i, chosen, conf, price, **kw):
    r = {"ts": T0 + i * 15, "decision_id": f"d{i}", "portfolio": "relaxed", "model": "von", "chosen_action": chosen,
         "final_action": "hold", "confidence": conf, "skip_noul": 0.1, "price_usd": price, "traded": False,
         "state": "deep quiet flat calm night gray wide soft late mid quiet held", "fail_closed": False, "von_ok": True}
    r.update(kw)
    return r


def series(points):
    return {"SOL": ([T0 + t for t, _ in points], [p for _, p in points])}


def test_percentile_matches_linear_interpolation():
    assert CA.percentile([], 90) is None
    assert CA.percentile([5], 90) == 5
    assert CA.percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)
    assert CA.percentile(range(1, 11), 90) == pytest.approx(9.1)


def test_is_answered_excludes_fail_closed_rules_and_zero_conf():
    assert CA.is_answered(dec(0, "buy", 0.38, 100))
    assert not CA.is_answered(dec(0, "hold", 0.0, 100))
    assert not CA.is_answered(dec(0, "buy", 0.38, 100, fail_closed=True))
    assert not CA.is_answered(dec(0, "buy", 0.38, 100, von_ok=False))
    assert not CA.is_answered(dec(0, "hold", 1.0, 100, model="rule"))
    assert not CA.is_answered(dec(0, "buy", None, 100))


def test_forward_price_window_and_classify():
    s = series([(0, 100.0), (900, 101.0), (2000, 99.0)])
    assert CA.forward_price(s["SOL"], T0, 900, 300) == (T0 + 900, 101.0)
    assert CA.forward_price(s["SOL"], T0 + 100, 900, 300) is None  # próximo ponto fora de [1000, 1300]
    assert CA.classify("buy", -0.002, 0.001) == "mistake" and CA.classify("buy", 0.002, 0.001) == "correct"
    assert CA.classify("sell", 0.002, 0.001) == "mistake" and CA.classify("sell", 0.0005, 0.001) == "flat"


def _decisions():
    # 20 respondidas: 18 a conf 0.23 (hold/buy), 2 buys confiantes 0.38 e 0.39; uma linha fail-closed
    rows = [dec(i, "buy" if i % 3 else "hold", 0.23, 100.0) for i in range(18)]
    rows.append(dec(18, "buy", 0.38, 100.0, state="thin bot_war fading violent night red wide soft late mid loud held"))
    rows.append(dec(19, "sell", 0.39, 100.0))
    rows.append(dec(20, "hold", 0.0, 100.0, fail_closed=True))
    return rows


def test_audit_percentile_vs_fixed_bar():
    prices = series([(18 * 15 + 900, 99.0), (19 * 15 + 900, 100.5)])  # buy→queda (erro), sell→subida (erro)
    a = CA.audit(_decisions(), prices=prices, percentile_p=95)
    assert a["n_answered"] == 20 and a["n_unanswered"] == 1
    assert a["cutoff"] == pytest.approx(0.3805) and a["n_confident"] == 1  # conf >= P95 → só a venda 0.39
    b = CA.audit(_decisions(), prices=prices, percentile_p=90)
    assert b["cutoff"] == pytest.approx(0.245)
    assert b["n_confident"] == 2 and b["n_resolved"] == 2 and b["n_mistakes"] == 2 and b["hit_rate"] == 0.0
    assert b["by_side"]["buy"]["mistake"] == 1 and b["by_side"]["sell"]["mistake"] == 1
    assert b["lose_words"][:2] == [("held", 2), ("late", 2)]  # nº de erros com a palavra; desempate alfabético
    assert b["word_stats"]["thin"] == [1, 1]
    fx = CA.audit(_decisions(), prices=prices, fixed_bar=0.8)
    assert fx["n_confident"] == 0 and fx["rule"].startswith("conf > 0.8")


def test_unresolved_without_forward_price():
    a = CA.audit(_decisions(), prices=series([(0, 100.0)]), percentile_p=90)
    assert a["n_confident"] == 2 and a["n_resolved"] == 0 and a["n_unresolved"] == 2 and a["hit_rate"] is None


def test_tie_rule_auto_switches_to_strict():
    rows = [dec(i, "buy", 0.356, 100.0) for i in range(80)] + [dec(80 + i, "buy", 0.39, 100.0) for i in range(5)]
    a = CA.audit(rows, prices=series([(0, 100.0)]), percentile_p=80)
    assert a["cutoff"] == pytest.approx(0.356) and a["rule"].startswith("conf > P80") and a["n_confident"] == 5
    g = CA.audit(rows, prices=series([(0, 100.0)]), percentile_p=80, tie_rule="ge")
    assert g["n_confident"] == 85


def test_dedupe_merges_shared_call_and_acted_join():
    b = dec(0, "buy", 0.38, 100.0, portfolio="baseline", decision_id="b0")
    r = dec(0, "buy", 0.38, 100.0, portfolio="relaxed", decision_id="r0", ts=T0 + 0.2)
    merged = CA.dedupe_calls([b, r], traded_ids={"r0"})
    assert len(merged) == 1 and merged[0]["_portfolios"] == ["baseline", "relaxed"] and merged[0]["_acted"]
    trades = [{"decision_id": "r0", "side": "buy", "ts": T0}]
    a = CA.audit([b, r], prices=series([(1000, 99.0)]), trades=trades, percentile_p=50, candidates="acted")
    assert a["n_confident"] == 1 and a["n_confident_acted"] == 1 and a["n_mistakes"] == 1
    with pytest.raises(ValueError):
        CA.audit([b], candidates="bogus")


BAD = "thin bot_war fading violent night red wide soft late mid loud held"   # estado dos erros
GOOD = "deep quiet flat calm night gray tight soft late mid quiet held"       # estado dos acertos (fundo em comum)


def _lift_rows(bad_state=BAD, good_state=GOOD, bad_at=(0, 40, 80, 120), good_at=(20, 60, 100, 140, 160)):
    """Compras confiantes (0.40): erros em `bad_at` (episódios separados por 10 min) e acertos em `good_at`;
    ruído de confiança baixa (0.23, hold) à volta. Preço 15 min depois: −1% nos erros, +1% nos acertos."""
    rows = [dec(i, "hold", 0.23, 100.0) for i in range(0, 200) if i not in set(bad_at) | set(good_at)]
    rows += [dec(i, "buy", 0.40, 100.0, state=bad_state) for i in bad_at]
    rows += [dec(i, "buy", 0.40, 100.0, state=good_state) for i in good_at]
    pts = [(i * 15 + 900, 99.0) for i in bad_at] + [(i * 15 + 900, 101.0) for i in good_at]
    return rows, series(sorted(pts))


def test_propose_criteria_only_appends_on_mistakes():
    base = copy.deepcopy(BASE)
    clean = CA.audit([dec(0, "buy", 0.38, 100.0)], prices=series([(900, 101.0)]), percentile_p=50)
    p = CA.propose_criteria(base, clean, generated_at="t")
    assert not p["changed"] and p["action"] == BASE["action"] and p["skip_this_cycle"] == BASE["skip_this_cycle"]
    rows, px = _lift_rows()
    bad = CA.audit(rows, prices=px, fixed_bar=0.3)
    assert bad["n_mistakes"] == 4 and bad["n_correct"] == 5 and bad["mistake_episodes"] == 4
    q = CA.propose_criteria(base, bad, generated_at="t")
    assert q["changed"]
    assert "deep not thin" in q["action"]["criteria"]["buy"]
    assert "never while the move is fading or dumping" in q["action"]["criteria"]["buy"]
    assert "violent" in q["skip_this_cycle"]["instructions"]
    # palavras empatadas em lift 1,0: ordem alfabética; as de fundo (deep/quiet/calm/night/late) não entram
    assert "be wary when the tape reads bot_war, fading, loud" in q["action"]["criteria"]["buy"]
    assert base == BASE  # nunca altera o texto base
    assert q["audit"]["n_mistakes"] == 4 and "mistakes" not in q["audit"]
    assert q["word_selection"]["eligible"]["buy"] == ["bot_war", "fading", "loud", "red", "thin", "violent", "wide"]
    assert CA.propose_criteria(base, bad, min_mistakes=5, generated_at="t")["changed"] is False


def test_word_lift_gives_baseline_words_zero_lift():
    rows, px = _lift_rows()
    a = CA.audit(rows, prices=px, fixed_bar=0.3)
    t = {r["word"]: r for r in CA.word_lift(a["outcomes"])}
    for w in ("quiet", "night", "soft", "late"):  # em 100% dos erros e dos acertos
        assert t[w]["err_share"] in (1.0, 0.0) and t[w]["lift"] <= 0 and not t[w]["eligible"]
    assert t["night"]["lift"] == 0.0 and t["late"]["lift"] == 0.0
    assert t["thin"]["lift"] == 1.0 and t["thin"]["eligible"] and t["thin"]["episodes"] == 4
    assert t["tight"]["lift"] == -1.0 and t["tight"]["log_odds"] < 0
    assert "mid" not in t and "held" not in t  # NON_MARKET_WORDS fora
    assert a["word_lift"][0]["lift"] == 1.0 and "thin" in a["lift_words"]["buy"]
    md = CA.lift_table_md(a["word_lift"], 3)
    assert md[0].startswith("| Palavra | % erros | % acertos | lift") and len(md) == 5
    # suporte: 2 erros só, ou tudo num episódio, ou sem acertos de referência → nada elegível
    few, pxf = _lift_rows(bad_at=(0, 40))
    assert CA.audit(few, prices=pxf, fixed_bar=0.3)["lift_words"]["all"] == []
    one, px1 = _lift_rows(bad_at=(0, 1, 2, 3))
    assert CA.audit(one, prices=px1, fixed_bar=0.3)["lift_words"]["all"] == []
    noref, pxn = _lift_rows(good_at=(160, 180))
    assert CA.audit(noref, prices=pxn, fixed_bar=0.3)["lift_words"]["all"] == []


def test_propose_unchanged_without_positive_lift():
    rows, px = _lift_rows(bad_state=GOOD)  # erros e acertos no mesmo estado
    a = CA.audit(rows, prices=px, fixed_bar=0.3)
    assert a["n_mistakes"] == 4 and a["n_correct"] == 5
    assert all(r["lift"] == 0 for r in CA.word_lift(a["outcomes"]))
    p = CA.propose_criteria(copy.deepcopy(BASE), a, generated_at="t")
    assert p["changed"] is False and p["phrases_added"] == {}
    assert p["action"] == BASE["action"] and p["skip_this_cycle"] == BASE["skip_this_cycle"]


def _osc(asset, amp, n=600, step=15.0, t_off=0.0):
    """Série que alterna 100 e 100×(1+amp) a cada 900 s: |retorno a 15 min| ≈ amp em todos os pontos."""
    ts = [T0 + t_off + i * step for i in range(n)]
    return {asset: (ts, [100.0 * (1 + amp) if int((t - T0) // 900) % 2 else 100.0 for t in ts])}


def test_vol_band_per_asset_floor_cap_and_fallback():
    end = T0 + 599 * 15
    sol = CA.vol_band(_osc("SOL", 0.002)["SOL"], end)
    assert sol["source"] == "vol" and sol["n"] > 100 and sol["clamped"] is None
    assert sol["median_abs_ret"] == pytest.approx(0.002, rel=0.01) and sol["band"] == pytest.approx(0.001, rel=0.01)
    meme = CA.vol_band(_osc("WIF", 0.02)["WIF"], end)
    assert meme["band"] == pytest.approx(0.01, rel=0.01)  # 0,5 × 2%
    assert CA.vol_band(_osc("X", 0.1)["X"], end)["band"] == 0.015                  # teto
    assert CA.vol_band(_osc("X", 0.0)["X"], end)["clamped"] == "floor"            # piso 0,05%
    short = CA.vol_band(_osc("X", 0.02, n=40)["X"], T0 + 39 * 15)
    assert short["source"] == "fallback_fixed" and short["band"] == 0.001
    assert CA.vol_band(None, end, fallback=0.002)["band"] == 0.002
    # janela para trás: pontos depois de t_end não contam
    assert CA.vol_band(_osc("SOL", 0.002)["SOL"], T0 + 100 * 15)["n"] < sol["n"]


def test_audit_vol_band_per_asset():
    """Uma memecoin com ruído de ±2% não conta −0,5% como erro em modo vol; o SOL (±0,2%) conta."""
    prices = {**_osc("SOL", 0.002), **_osc("WIF", 0.02)}
    t_dec = 400 * 15  # ponto em fase "100" (int(6000/900)=6, par); +900 s → fase ímpar
    rows = [dec(400, "buy", 0.4, 100.0 * 1.002 / 0.997, symbol="SOL"),       # SOL: −0,3% vs banda ~0,1% → erro
            dec(401, "buy", 0.4, 100.0 * 1.02 / 0.995, symbol="WIF", ts=T0 + t_dec + 1)]  # WIF: −0,5% vs ~1% → flat
    rows += [dec(i, "hold", 0.2, 100.0) for i in range(10)]
    kw = dict(prices=prices, fixed_bar=0.3, window=(T0, T0 + 599 * 15 + 1))
    fixed = CA.audit(rows, **kw)
    vol = CA.audit(rows, band_mode="vol", **kw)
    assert fixed["band_mode"] == "fixed" and fixed["band_by_asset"] == {"SOL": 0.001, "WIF": 0.001}
    assert fixed["n_mistakes"] == 2
    assert vol["band_by_asset"]["SOL"] == pytest.approx(0.001, rel=0.02)
    assert vol["band_by_asset"]["WIF"] == pytest.approx(0.01, rel=0.02)
    assert vol["bands"]["WIF"]["source"] == "vol" and vol["bands"]["WIF"]["n"] > 100
    assert vol["n_mistakes"] == 1 and vol["mistakes"][0]["asset"] == "SOL" and vol["n_flat"] == 1
    assert {o["asset"]: o["band"] for o in vol["outcomes"]}["WIF"] == vol["band_by_asset"]["WIF"]
    assert CA.summary(vol)["band_by_asset"] == vol["band_by_asset"]
    assert CA.audit(rows, bands={"WIF": 0.0001}, **kw)["band_by_asset"]["WIF"] == 0.0001  # banda dada
    with pytest.raises(ValueError):
        CA.audit(rows, band_mode="nope", **kw)
    rc = CA.review_cfg({})
    assert rc["band_mode"] == "vol" and CA.band_kwargs(rc)["band_k"] == 0.5 and CA.lift_kwargs(rc)["min_episodes"] == 2


def test_night_review_uses_day_and_writes_proposal_only(tmp_path):
    import bot.sol_bot as SB
    logs = tmp_path / "logs"; logs.mkdir()
    rows = []
    for i in range(40):  # baseline + relaxed com a mesma chamada
        for port in ("baseline", "relaxed"):
            rows.append(dec(i, "buy", 0.38 if i >= 36 else 0.23, 100.0, portfolio=port, decision_id=f"{port}{i}",
                            ts=T0 + i * 15 + (0.1 if port == "relaxed" else 0)))
    rows.append(dec(0, "buy", 0.9, 100.0, portfolio="baseline", ts=T0 - 86400))  # dia anterior: fora da janela
    (logs / "decisions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (logs / "trades.jsonl").write_text("")
    prices = tmp_path / "prices.jsonl"
    prices.write_text("".join(json.dumps({"ts": T0 + t, "price_usd": 99.0}) + "\n" for t in range(900, 4000, 15)))
    crit = tmp_path / "criteria_baseline.json"; crit.write_text(json.dumps(BASE))
    before = crit.read_text()
    out_md, out_json = tmp_path / "rev.md", tmp_path / "prop.json"
    p = SB.night_review(logs / "decisions.jsonl", logs / "trades.jsonl", crit, out_md, out_json,
                        day="2026-09-26", cfg={"review": {"confidence_percentile": 90}}, prices_log=prices)
    md = out_md.read_text()
    assert md.startswith("# Revisão noturna (critérios v2) — 2026-09-26") and "2026-09-24" not in md.splitlines()[0]
    assert crit.read_text() == before
    saved = json.loads(out_json.read_text())
    assert saved["audit"]["n_answered"] == 40      # 80 linhas → 40 chamadas; a de ontem fica fora
    assert saved["audit"]["n_confident"] == 4 and saved["audit"]["n_mistakes"] == 4
    assert saved["audit"]["mistake_episodes"] == 1  # 4 ciclos seguidos = 1 episódio
    assert CA.episodes([0, 15, 30, 1000, 1015]) == 2 and CA.episodes([]) == 0
    assert saved["audit"]["fixed_bar_compare"]["n_confident"] == 0
    # todos os confiantes erraram no mesmo estado, num só episódio e sem acertos de referência: nenhuma palavra
    # tem lift com suporte, por isso a proposta é o texto base (antes saía "calm, deep, flat" por frequência)
    assert not p["changed"] and not saved["changed"] and saved["phrases_added"] == {}
    assert saved["word_selection"]["method"] == "lift" and saved["word_selection"]["eligible"]["buy"] == []
    assert saved["audit"]["band_mode"] == "vol" and saved["audit"]["bands"]["SOL"]["source"] == "vol"
    assert saved["audit"]["band_by_asset"]["SOL"] == 0.0005  # série parada → piso
    assert "Banda usada por ativo" in md and "Palavras de estado por lift" in md and "| Palavra | % erros |" in md
    assert "nenhuma palavra com lift positivo" in md
