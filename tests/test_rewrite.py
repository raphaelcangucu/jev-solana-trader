import hashlib
import json
from dataclasses import replace
from datetime import date

import pytest

from jev_trader.criteria import DEFAULT_CRITERIA, load_criteria
from jev_trader.decide import ARTICLE_QUESTIONS, current_questions
from jev_trader.experiment import DEFAULT_EXPERIMENT
from jev_trader.rewrite import (
    RewriteError,
    approve,
    build_proposal,
    percentile_cutoff,
    reject,
    write_proposal,
)
from test_paper import _cfg

EXP = replace(DEFAULT_EXPERIMENT, run_id="runR", start_t="2026-09-30T00:00:00-03:00")
BUY_STATE = "thin quiet flat violent flat gray wide calm late late loud held"
SELL_STATE = "deep quiet pumping calm pumping green tight calm early early quiet held"
HOLD_STATE = "deep quiet flat calm flat gray tight calm mid mid quiet held"


def _row(minute, *, conf, action="hold", model_action="hold", px=100.0, state=HOLD_STATE, source="von-http"):
    return {
        "t": f"2026-09-30T01:{minute:02d}:00-03:00",
        "state": state,
        "action": action,
        "model_action": model_action,
        "conf": conf,
        "px_in": px,
        "source": source,
    }


def von_like_log(*, with_mistakes: bool = True) -> list[dict]:
    """41 ciclos com confiança de von (~0.2 a 0.45), portão de confiança baixado para deixar passar ~0.3+."""
    special = {0, 5, 10, 12}
    rows = []
    for minute in range(41):
        if minute in special:
            continue
        rows.append(_row(minute, conf=round(0.20 + (minute % 10) * 0.02, 2)))
    rows += [
        _row(0, conf=0.45, action="buy", model_action="buy", state=BUY_STATE),
        _row(5, conf=0.44, action="buy", model_action="buy", state=BUY_STATE),
        _row(10, conf=0.43, action="sell", model_action="sell", state=SELL_STATE),
        # Compra de confiança baixa que também erra: fica abaixo do percentil e não conta.
        _row(12, conf=0.30, action="buy", model_action="buy", state=BUY_STATE),
    ]
    if with_mistakes:
        prices = {15: 99.0, 20: 98.0, 25: 101.0, 27: 97.0}
        rows = [dict(row, px_in=prices.get(int(row["t"][14:16]), row["px_in"])) for row in rows]
    # Ciclos sem resposta do von não entram no percentil.
    rows.append(_row(41, conf=0.0, model_action=None, source="fail-closed"))
    rows.sort(key=lambda row: row["t"])
    return rows


def _proposal(rows, current=None, **kwargs):
    current = dict(current or DEFAULT_CRITERIA)
    return build_proposal(
        rows,
        EXP,
        current,
        "default",
        review_date=kwargs.pop("review_date", None),
        today=date(2026, 10, 1),
        now_t="2026-10-01T03:30:00-03:00",
        **kwargs,
    )


def test_nearest_rank_percentile():
    assert percentile_cutoff([], 90) is None
    assert percentile_cutoff([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], 90) == 0.9
    assert percentile_cutoff([0.3], 90) == 0.3
    assert percentile_cutoff([0.5, 0.1, 0.4], 50) == 0.4
    with pytest.raises(RewriteError):
        percentile_cutoff([0.1], 0)


def test_percentile_catches_confident_mistakes_the_fixed_bar_never_sees():
    proposal = _proposal(von_like_log())
    fixed = proposal["audit"]["fixed"]
    pct = proposal["audit"]["percentile"]
    assert fixed["bar"] == 0.8 and fixed["n_confident"] == 0 and fixed["n_mistakes"] == 0
    assert pct["n_answered"] == 41
    assert pct["cutoff"] == 0.38
    assert pct["n_confident"] == 3
    assert pct["n_resolved"] == 3
    assert pct["n_mistakes"] == 3
    assert [m["t"][11:16] for m in pct["mistakes"]] == ["01:00", "01:05", "01:10"]
    assert pct["word_counts"]["thin"] == 2
    assert proposal["audit"]["driver"] == "percentile"
    assert proposal["changed"] is True
    assert proposal["status"] == "pending"
    proposed = proposal["proposed_criteria"]
    assert proposed["buy"].startswith(DEFAULT_CRITERIA["buy"] + "; ")
    assert "only when depth is deep not thin" in proposed["buy"]
    assert "not late in the range" in proposed["buy"]
    assert "not while the move is pumping green" in proposed["sell"]
    assert "when the tape is violent or loud" in proposed["hold"]
    assert proposed["skip"] == DEFAULT_CRITERIA["skip"]
    assert not any(ch.isdigit() for text in proposed.values() for ch in text)


def test_no_mistakes_means_no_change():
    proposal = _proposal(von_like_log(with_mistakes=False))
    assert proposal["audit"]["percentile"]["n_mistakes"] == 0
    assert proposal["changed"] is False
    assert proposal["proposed_criteria"] == proposal["current_criteria"] == DEFAULT_CRITERIA
    assert proposal["additions"] == {}


def test_rewrite_is_idempotent_on_already_added_phrases():
    first = _proposal(von_like_log())
    second = _proposal(von_like_log(), current=first["proposed_criteria"])
    assert second["changed"] is False


def test_review_date_filters_the_brt_day_and_labels_the_file(tmp_path):
    rows = von_like_log()
    same_day = _proposal(rows, review_date=date(2026, 9, 30))
    assert same_day["date"] == "2026-09-30"
    assert same_day["title"].endswith("2026-09-30")
    assert same_day["audit"]["percentile"]["n_mistakes"] == 3
    other_day = _proposal(rows, review_date=date(2026, 10, 2))
    assert other_day["window"]["n_decisions"] == 0
    assert other_day["changed"] is False
    whole = _proposal(rows)
    assert whole["date"] == "2026-10-01"
    path = write_proposal(tmp_path, same_day)
    assert path.name == "2026-09-30.json"


def _written(tmp_path, proposal):
    return write_proposal(tmp_path / "rewrite_proposals", proposal)


def test_approve_writes_criteria_and_logs(tmp_path):
    path = _written(tmp_path, _proposal(von_like_log()))
    criteria_path = tmp_path / "config" / "criteria.json"
    approvals = tmp_path / "rewrite_approvals.jsonl"
    record = approve(path, criteria_path=criteria_path, approvals_path=approvals, approver="tester", now_t="T")
    loaded, source = load_criteria(criteria_path)
    assert source == "file"
    assert loaded == json.loads(path.read_text(encoding="utf-8"))["proposed_criteria"]
    assert record["criteria_sha256"] == hashlib.sha256(criteria_path.read_bytes()).hexdigest()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["status"] == "approved" and saved["approved_by"] == "tester"
    line = json.loads(approvals.read_text(encoding="utf-8").strip())
    assert line["approver"] == "tester" and line["proposal"] == str(path)
    with pytest.raises(RewriteError):
        approve(path, criteria_path=criteria_path, approvals_path=approvals, approver="tester", now_t="T")
    with pytest.raises(RewriteError):
        write_proposal(tmp_path / "rewrite_proposals", _proposal(von_like_log()))


@pytest.mark.parametrize(
    "bad",
    [
        {"buy": "buy when up", "sell": "sell", "hold": "hold"},
        {"buy": "buy after 3 green candles", "sell": "s", "hold": "h", "skip": "k"},
        {"buy": "   ", "sell": "s", "hold": "h", "skip": "k"},
        {"buy": "x" * 500, "sell": "s", "hold": "h", "skip": "k"},
        {"buy": ["list"], "sell": "s", "hold": "h", "skip": "k"},
    ],
)
def test_invalid_proposal_changes_nothing(tmp_path, bad):
    proposal = dict(_proposal(von_like_log()), proposed_criteria=bad)
    path = _written(tmp_path, proposal)
    before = path.read_text(encoding="utf-8")
    criteria_path = tmp_path / "criteria.json"
    approvals = tmp_path / "rewrite_approvals.jsonl"
    with pytest.raises(RewriteError):
        approve(path, criteria_path=criteria_path, approvals_path=approvals, approver="t", now_t="T")
    assert not criteria_path.exists()
    assert not approvals.exists()
    assert path.read_text(encoding="utf-8") == before


def test_stale_proposal_is_refused(tmp_path):
    path = _written(tmp_path, _proposal(von_like_log()))
    criteria_path = tmp_path / "criteria.json"
    criteria_path.write_text(json.dumps(dict(DEFAULT_CRITERIA, hold="stay out")), encoding="utf-8")
    with pytest.raises(RewriteError):
        approve(path, criteria_path=criteria_path, approvals_path=tmp_path / "a.jsonl", approver="t", now_t="T")


def test_reject_marks_the_proposal(tmp_path):
    path = _written(tmp_path, _proposal(von_like_log()))
    approvals = tmp_path / "rewrite_approvals.jsonl"
    reject(path, approvals_path=approvals, approver="tester", now_t="T")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["status"] == "rejected" and saved["rejected_by"] == "tester"
    assert json.loads(approvals.read_text(encoding="utf-8"))["decision"] == "rejected"
    with pytest.raises(RewriteError):
        reject(path, approvals_path=approvals, approver="tester", now_t="T")


def test_rewrite_cli_propose_approve_and_invalid(monkeypatch, tmp_path, capsys):
    from jev_trader import __main__ as cli

    cfg = _cfg(tmp_path, experiment_path=tmp_path / "experiment.json")
    (tmp_path / "experiment.json").write_text(
        json.dumps({"run_id": "runR", "start_t": EXP.start_t, "book": {"sol": 0.01, "usdt": 50}}),
        encoding="utf-8",
    )
    cfg.decisions_path.write_text("\n".join(json.dumps(r) for r in von_like_log()) + "\n", encoding="utf-8")
    monkeypatch.setattr(cli, "load_config", lambda: cfg)
    assert cli.main(["rewrite", "--propose", "--date", "2026-09-30"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["changed"] is True and summary["percentile_mistakes"] == 3 and summary["fixed_mistakes"] == 0
    path = tmp_path / "rewrite_proposals" / "2026-09-30.json"
    assert json.loads(path.read_text(encoding="utf-8"))["title"] == "Reescrita noturna — 2026-09-30"
    assert cli.main(["rewrite", "--approve", str(path), "--by", "tester"]) == 0
    assert load_criteria(cfg.criteria_path)[1] == "file"
    assert cli.main(["rewrite", "--approve", str(path)]) == 2
    assert cli.main(["rewrite", "--reject", str(tmp_path / "missing.json")]) == 2
    assert cli.main(["rewrite", "--propose", "--date", "not-a-date"]) == 2


def test_decide_loads_approved_criteria_and_falls_back(tmp_path):
    cfg = _cfg(tmp_path)
    assert current_questions(cfg) == ARTICLE_QUESTIONS
    custom = dict(DEFAULT_CRITERIA, buy="the move is strong and the book is deep")
    cfg.criteria_path.write_text(json.dumps(custom), encoding="utf-8")
    questions = current_questions(cfg)
    assert questions["action"]["criteria"]["buy"] == "the move is strong and the book is deep"
    assert questions["skip_this_cycle"]["instructions"] == DEFAULT_CRITERIA["skip"]
    cfg.criteria_path.write_text(json.dumps(dict(custom, sell="sell below 100")), encoding="utf-8")
    assert current_questions(cfg) == ARTICLE_QUESTIONS
    cfg.criteria_path.write_text("{broken", encoding="utf-8")
    assert current_questions(cfg) == ARTICLE_QUESTIONS
    cfg.criteria_path.write_text(json.dumps({"buy": "only buy"}), encoding="utf-8")
    assert current_questions(cfg) == ARTICLE_QUESTIONS


# ------------------------------------------------------------------ caminho autónomo (revisão noturna, só paper)

from jev_trader.rewrite import build_autonomous_proposal, paper_guard  # noqa: E402

NEW = {"buy": "the move is lifting with calm tape and a deep book", "sell": "the move is fading or dumping",
       "hold": "flat gray chop or anything unclear", "skip": "a thin book or a bot war"}


def _paper_root(tmp_path, *, mode="paper", paper_only=True, dotenv=None, experiment=True):
    root = tmp_path / "bot"
    (root / "config").mkdir(parents=True)
    if experiment:
        (root / "config" / "experiment.json").write_text(json.dumps(
            {"run_id": "runR", "start_t": "2026-09-30T00:00:00-03:00", "book": {"sol": 0.01, "usdt": 50}, "mode": mode}))
    prof = {"gates": {"confidence_min": 0.35}}
    if paper_only:
        prof["paper_only"] = True
    (root / "config" / "params.json").write_text(json.dumps({"defaults": {}, "profiles": {"article": {}, "relaxed_paper": prof}}))
    if dotenv is not None:
        (root / ".env").write_text(dotenv)
    return root


def test_paper_guard_accepts_only_a_paper_bot(tmp_path):
    assert paper_guard(_paper_root(tmp_path), env={}) == []


@pytest.mark.parametrize(
    "kw, env, why",
    [
        ({}, {"LIVE_TRADING": "1"}, "LIVE_TRADING=1 no ambiente"),
        ({"dotenv": "SOLANA_KEYPAIR_PATH=/k\nexport LIVE_TRADING=1\n"}, {}, "LIVE_TRADING=1 no .env"),
        ({"mode": "live"}, {}, "mode='live'"),
        ({"experiment": False}, {}, "experiment.json"),
        ({"paper_only": False}, {}, "não é paper_only"),
        ({}, {"PARAMS_PROFILE": "article"}, "não é paper_only"),
        ({"dotenv": "PARAMS_PROFILE=article\n"}, {}, "não é paper_only"),
        ({}, {"PARAMS_PROFILE": "nope"}, "não resolve"),
    ],
)
def test_paper_guard_refuses(tmp_path, kw, env, why):
    reasons = paper_guard(_paper_root(tmp_path, **kw), env=env)
    assert any(why in r for r in reasons), reasons
    assert not any("/k" in r for r in reasons)  # nunca ecoa outras chaves do .env


def _auto(tmp_path, proposed=NEW):
    return build_autonomous_proposal(
        von_like_log(), EXP, dict(DEFAULT_CRITERIA), "default", proposed, author="claude-night", reason="hipótese",
        review_date=None, today=date(2026, 9, 30), now_t="T")


def test_autonomous_approve_writes_only_in_paper(tmp_path):
    root = _paper_root(tmp_path)
    prop = _auto(tmp_path)
    assert prop["proposed_criteria"] == NEW and prop["author"] == "claude-night" and prop["status"] == "pending"
    assert prop["audit"]["percentile"]["n_mistakes"] == 3  # a mesma auditoria por percentil do caminho humano
    path = write_proposal(tmp_path / "p", prop, filename="2026-09-30_claude-night.json")
    criteria_path = root / "config" / "criteria.json"
    approvals = tmp_path / "a.jsonl"
    before = path.read_text(encoding="utf-8")
    with pytest.raises(RewriteError, match="autonomous approval refused"):
        approve(path, criteria_path=criteria_path, approvals_path=approvals, approver="claude-night", now_t="T",
                autonomous=True, guard_root=root, env={"LIVE_TRADING": "1"})
    assert not criteria_path.exists() and not approvals.exists() and path.read_text(encoding="utf-8") == before
    with pytest.raises(RewriteError, match="guard_root"):
        approve(path, criteria_path=criteria_path, approvals_path=approvals, approver="claude-night", now_t="T",
                autonomous=True)
    rec = approve(path, criteria_path=criteria_path, approvals_path=approvals, approver="claude-night", now_t="T",
                  autonomous=True, guard_root=root, env={})
    assert rec["autonomous"] is True and rec["approver"] == "claude-night" and rec["reason"] == "hipótese"
    assert load_criteria(criteria_path) == (NEW, "file")
    assert json.loads(path.read_text(encoding="utf-8"))["autonomous"] is True


def test_human_approve_record_is_unchanged(tmp_path):
    path = _written(tmp_path, _proposal(von_like_log()))
    rec = approve(path, criteria_path=tmp_path / "c.json", approvals_path=tmp_path / "a.jsonl", approver="h", now_t="T")
    assert set(rec) == {"t", "decision", "proposal", "criteria_path", "criteria_sha256", "approver"}


@pytest.mark.parametrize("bad", [dict(DEFAULT_CRITERIA), dict(NEW, buy="buy after 3 candles"), {"buy": "x"}])
def test_autonomous_proposal_refuses_invalid_or_unchanged(tmp_path, bad):
    with pytest.raises(RewriteError):
        _auto(tmp_path, bad)
