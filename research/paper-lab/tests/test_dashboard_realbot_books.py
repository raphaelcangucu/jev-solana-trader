"""dashboard/insights.py: placar do bot real com dois livros de papel (A em logs/, B em logs/paper_b)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "dashboard"))
import insights as INS  # noqa: E402

REPO_SRC = LAB.parents[1] / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

EXP = {"run_id": "r1", "start_t": "2026-10-01T12:00:00-03:00", "book": {"sol": 0.1, "usdt": 10.0},
       "ref_sol_usd": 100.0, "mode": "paper"}


def _write(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _root(tmp_path: Path, with_b: bool) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "experiment.json").write_text(json.dumps(EXP))
    _write(tmp_path / "logs" / "decisions.jsonl", [
        {"t": f"2026-10-01T12:{m:02d}:00-03:00", "run_id": "r1", "px_in": 100.0 + m, "paper_sol": 0.1,
         "paper_usdt": 10.0, "action": "hold", "reason": "low_confidence"} for m in range(5)])
    if with_b:
        b = tmp_path / "logs" / "paper_b"
        _write(b / "decisions.jsonl", [
            {"t": "2026-10-02T12:00:00-03:00", "run_id": "r1", "px_in": 120.0, "paper_sol": 0.1, "paper_usdt": 10.0,
             "action": "hold", "params_profile": "relaxed_exits_paper"},
            {"t": "2026-10-02T12:05:00-03:00", "run_id": "r1", "px_in": 124.0, "paper_sol": 0.0, "paper_usdt": 22.3,
             "action": "hold", "exit_reason": "tp", "params_profile": "relaxed_exits_paper"}])
        _write(b / "paper_trades.jsonl", [
            {"t": "2026-10-02T12:05:00-03:00", "run_id": "r1", "side": "sell", "reason": "tp", "px_in": 124.0,
             "fill_px": 124.0, "in_amount_ui": 0.1, "out_amount_ui": 12.3, "book_after": {"sol": 0.0, "usdt": 22.3}}])
        (b / "paper_book.json").write_text(json.dumps({
            "run_id": "r1", "book": "B", "sol": 0.0, "usdt": 22.3, "start_t": "2026-10-02T12:00:00-03:00",
            "start_px": 120.0, "avg_cost": None, "peak_px": None, "last_exit_t": "2026-10-02T12:05:00-03:00"}))
    return tmp_path


def test_single_book_keeps_old_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_TRADER_ROOT", str(_root(tmp_path, with_b=False)))
    INS._rb_cache.update(key=None, val=None)
    out = INS.real_bot_board()
    assert out["available"] and out["book"] == "A" and "books" not in out
    assert out["n_decisions"] == 5 and out["exits"]["total"] == 0


def test_two_books_side_by_side(tmp_path, monkeypatch):
    root = _root(tmp_path, with_b=True)
    monkeypatch.setenv("JEV_TRADER_ROOT", str(root))
    INS._rb_cache.update(key=None, val=None)
    out = INS.real_bot_board()
    assert out["book"] == "A" and [b["book"] for b in out["books"]] == ["A", "B"]
    b = out["books"][1]
    assert b["log_dir"] == "logs/paper_b" and b["start_t"] == "2026-10-02T12:00:00-03:00"
    assert b["params_profile"] == "relaxed_exits_paper" and b["n_decisions"] == 2
    assert b["exits"]["by_reason"]["tp"] == 1 and b["exits"]["exposure"] == 0.0
    assert b["pnl_vs_start"]["ref_sol_usd"] == 120.0
    assert b["recent_decisions"][0]["exit_reason"] == "tp" and b["recent_trades"][0]["reason"] == "tp"
    # A série do B usa o mesmo livro inicial (0,1 SOL + 10 USDT) como "segurar".
    assert b["series"]["rows"][-1][2] == 0.1 * 124 + 10.0
    assert [label for label, _ in INS.real_bot_books(root)] == ["A", "B"]
