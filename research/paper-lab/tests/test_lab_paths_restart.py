"""bot/paths.py (PAPER_LAB_ROOT) e scripts/maintenance/restart_run.py sobre uma árvore temporária."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

from bot import paths

LAB = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(os.environ["PAPER_LAB_ROOT"])


def test_root_follows_env_set_before_import():
    assert paths.ROOT == TEST_ROOT
    assert paths.LAB_DIR == LAB
    from bot import lib, logio
    assert lib.ROOT == TEST_ROOT and logio.ARCH == TEST_ROOT / "archive"


def test_load_config_resolves_relative_paths(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"paths": {"root": "/home/box/solana-trader/paper", "decisions_log": "logs/d.jsonl",
                                         "trades_log": "/abs/t.jsonl"}}))
    monkeypatch.setenv("PAPER_LAB_ROOT", str(tmp_path))
    c = paths.load_config(cfg)
    assert c["_paths"]["root"] == tmp_path.resolve()
    assert c["_paths"]["decisions_log"] == tmp_path.resolve() / "logs" / "d.jsonl"
    assert c["_paths"]["trades_log"] == Path("/abs/t.jsonl")
    assert c["_paths"]["prices_log"] == tmp_path.resolve() / "data" / "prices.jsonl"  # padrão
    monkeypatch.delenv("PAPER_LAB_ROOT")
    assert paths.load_config(cfg)["_paths"]["root"] == Path("/home/box/solana-trader/paper")
    cfg.write_text(json.dumps({"paths": {"root": "."}}))
    assert paths.load_config(cfg)["_paths"]["root"] == LAB


def test_lib_load_cfg_rewrites_paths_root(monkeypatch):
    from bot import lib
    (TEST_ROOT / "config.json").write_text(json.dumps({"paths": {"root": "/elsewhere", "x": "logs/x.jsonl"}, "cycle_seconds": 15}))
    try:
        c = lib.load_cfg()
        assert c["paths"]["root"] == str(TEST_ROOT) and c["paths"]["x"] == str(TEST_ROOT / "logs" / "x.jsonl")
        json.dumps(c)  # continua serializável
    finally:
        (TEST_ROOT / "config.json").unlink()


def _restart_module():
    spec = importlib.util.spec_from_file_location("restart_run", LAB / "scripts" / "maintenance" / "restart_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tree(root: Path):
    cfg = {"paper_only": True, "live_trading_enabled": False,
           "starting_balances": {"sol": 0.334150878, "usdt": 960.812456, "total_usd": 1000.0, "ref_price": 117.275, "sol_frac": 0.039188},
           "experiment": {"day1_start_brt": "2026-09-24T21:07:46-03:00", "capital_usd_each": 1000.0,
                          "previous_runs": [{"name": "run_52usd_2026-09-24"}]}}
    files = {"config.json": json.dumps(cfg), "memecoins.json": json.dumps({"start_usdt_each": 1000.0, "tokens": []}),
             "criteria_baseline.json": "{}", "criteria_v2.json": "{}", "status.json": "{}",
             "data/portfolio_relaxed.json": "{}", "data/equity_relaxed.jsonl": "{}\n", "data/params_overlay.json": "{}",
             "data/meme/portfolios/BONK_relaxed.json": "{}", "data/lab/registry.json": "{}", "data/nightly/verdicts.json": "{}",
             "logs/decisions.jsonl": "{}\n", "logs/sol_bot.log": "x", "logs/supervisor.log": "x",
             "reports/cumulative.md": "r", "reviews/2026-09-24.md": "v", "funding/data/state.json": "{}",
             "funding/data/funding_cache.json": "{}", "funding/reports/cumulative.md": "f"}
    for rel, txt in files.items():
        p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt)


def test_restart_run_archives_and_marks_new_run(tmp_path, capsys):
    rr = _restart_module()
    _tree(tmp_path)
    args = ["--root", str(tmp_path), "--archive-name", "run_test", "--capital", "1000",
            "--start-brt", "2026-09-30T09:00:00-03:00", "--end-brt", "2026-09-30T08:59:00-03:00"]
    assert rr.main(args + ["--dry-run", "--ref-price", "150"]) == 0
    assert (tmp_path / "data" / "portfolio_relaxed.json").exists() and not (tmp_path / "archive").exists()
    assert rr.main(args + ["--ref-price", "150"]) == 0
    dest = tmp_path / "archive" / "run_test"
    for rel in ("data/portfolio_relaxed.json", "data/meme/portfolios/BONK_relaxed.json", "logs/decisions.jsonl",
                "reviews/2026-09-24.md", "reports/cumulative.md", "status.json", "funding/data/state.json", "data/nightly/verdicts.json"):
        assert (dest / rel).exists() and not (tmp_path / rel).exists(), rel
    for rel in ("config.json", "criteria_v2.json", "data/params_overlay.json", "logs/supervisor.log"):
        assert (dest / rel).exists() and (tmp_path / rel).exists(), rel
    assert (tmp_path / "funding" / "data" / "funding_cache.json").exists()
    assert (tmp_path / "reviews" / ".gitkeep").exists() and (tmp_path / "reports" / ".gitkeep").exists()
    cfg = json.loads((tmp_path / "config.json").read_text())
    e = cfg["experiment"]
    assert e["day1_start_brt"] == "2026-09-30T09:00:00-03:00" and e["run_name"] == "run_1000usd_2026-09-30"
    assert [r["name"] for r in e["previous_runs"]] == ["run_52usd_2026-09-24", "run_test"]
    assert e["previous_runs"][-1]["start_brt"] == "2026-09-24T21:07:46-03:00"
    sb = cfg["starting_balances"]
    assert sb["total_usd"] == 1000.0 and sb["sol"] * 150 + sb["usdt"] == pytest.approx(1000.0, abs=1e-3)
    assert cfg["live_trading_enabled"] is False
    assert "Início (BRT): 2026-09-24T21:07:46-03:00" in (dest / "README.md").read_text()
    with pytest.raises(SystemExit):  # nunca sobrescreve um arquivo existente
        rr.main(args + ["--ref-price", "150"])


def test_restart_run_refuses_while_bots_run(tmp_path):
    rr = _restart_module()
    _tree(tmp_path)
    (tmp_path / "run").mkdir()
    (tmp_path / "run" / "sol.pid").write_text(str(os.getpid()))
    with pytest.raises(SystemExit):
        rr.main(["--root", str(tmp_path), "--archive-name", "x", "--keep-balances"])
    assert (tmp_path / "data" / "portfolio_relaxed.json").exists()
