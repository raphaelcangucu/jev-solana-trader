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


def test_propose_criteria_only_appends_on_mistakes():
    base = copy.deepcopy(BASE)
    clean = CA.audit([dec(0, "buy", 0.38, 100.0)], prices=series([(900, 101.0)]), percentile_p=50)
    p = CA.propose_criteria(base, clean, generated_at="t")
    assert not p["changed"] and p["action"] == BASE["action"] and p["skip_this_cycle"] == BASE["skip_this_cycle"]
    bad = CA.audit(_decisions(), prices=series([(18 * 15 + 900, 99.0), (19 * 15 + 900, 100.5)]), percentile_p=90)
    q = CA.propose_criteria(base, bad, generated_at="t")
    assert q["changed"]
    assert "deep not thin" in q["action"]["criteria"]["buy"]
    assert "never while the move is fading or dumping" in q["action"]["criteria"]["buy"]
    assert "violent" in q["skip_this_cycle"]["instructions"]
    assert base == BASE  # nunca altera o texto base
    assert q["audit"]["n_mistakes"] == 2 and "mistakes" not in q["audit"]
    assert CA.propose_criteria(base, bad, min_mistakes=5, generated_at="t")["changed"] is False


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
    prices.write_text("".join(json.dumps({"ts": T0 + t, "price_usd": 99.0}) + "\n" for t in range(900, 2000, 15)))
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
    assert p["changed"] and saved["changed"]
    # todos os confiantes erraram no mesmo estado: sem palavra "distintiva", usa as palavras de mercado dos erros
    assert saved["phrases_added"] == {"buy": ["be wary when the tape reads calm, deep, flat"]}
