"""One-off (histórico; para novos recomeços use scripts/maintenance/restart_run.py): archive the $52 paper run (never delete) and switch starting capital to $1,000 per portfolio.
Run ONLY with sol/meme/rules/lab/nightly + supervisor stopped. Paper only; touches no wallet/keys."""
import json, os, shutil, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # código do lab
from bot.paths import ROOT  # noqa: E402
BRT = timezone(timedelta(hours=-3))
DEST = ROOT / "archive" / "run_52usd_2026-09-24"
moved, copied = [], []

def mv(p):
    p = Path(p)
    if not p.exists(): return
    t = DEST / p.relative_to(ROOT); t.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(p), str(t)); moved.append(str(p.relative_to(ROOT)))

def cp(p):
    p = Path(p)
    if not p.exists(): return
    t = DEST / p.relative_to(ROOT); t.parent.mkdir(parents=True, exist_ok=True)
    (shutil.copytree if p.is_dir() else shutil.copy2)(str(p), str(t)); copied.append(str(p.relative_to(ROOT)))

if DEST.exists() and any(DEST.iterdir()):
    sys.exit(f"{DEST} already populated; refusing to overwrite")
DEST.mkdir(parents=True, exist_ok=True)
cfg = json.loads((ROOT / "config.json").read_text())
old_bal = dict(cfg["starting_balances"])
px_row = json.loads((ROOT / "data" / "prices.jsonl").read_text().strip().splitlines()[-1])
px = float(px_row["price_usd"])
# first start of the $52 run
first_start = cfg.get("experiment", {}).get("day1_start_brt")
end_brt = datetime.now(BRT).isoformat(timespec="seconds")

# --- copy configs/market data (kept live), move run state/logs/reports
for f in ["config.json", "memecoins.json", "models.json", "criteria_baseline.json", "criteria_v2.json",
          "data/params_overlay.json", "data/prices.jsonl", "data/meme/prices", "README.md", "reviews/2026-09-24.md"]:
    cp(ROOT / f)
for f in sorted((ROOT / "data").glob("portfolio_*.json")) + sorted((ROOT / "data").glob("equity_*.jsonl")):
    mv(f)
for f in ["status.json", "data/meme/portfolios", "data/meme/equity", "data/meme/status.json", "data/rules/equity",
          "data/rules/status.json", "data/lab/equity", "data/lab/portfolios", "data/lab/registry.json", "data/lab/status.json",
          "data/nightly", "archive/logs", "archive/data"]:
    mv(ROOT / f)
for f in sorted((ROOT / "logs").glob("*.jsonl")):
    mv(f)
for n in ["sol_bot", "meme_bot", "rules_bot", "lab_bot", "nightly"]:
    mv(ROOT / "logs" / f"{n}.log")
for n in ["supervisor", "dashboard", "tunnel", "von_serve", "laya_serve", "poorjev_serve", "start_laya_boot", "start_poorjev_boot"]:
    cp(ROOT / "logs" / f"{n}.log")
for f in sorted((ROOT / "reports").iterdir()):
    mv(f)
for f in sorted((ROOT / "reviews").iterdir()):
    if f.name == "2026-09-24.md":
        continue  # copied above; stays live because sol_bot uses it as the v2 'review done' flag (v2 criteria unchanged)
    mv(f)

# --- new capital: scale the old wallet mirror mix to $1,000 at the current price
sol_val = old_bal["sol"] * px; frac = sol_val / (sol_val + old_bal["usdt"])
new_bal = {"sol": round(1000.0 * frac / px, 9), "usdt": round(1000.0 * (1 - frac), 6), "total_usd": 1000.0, "ref_price": px,
           "sol_frac": round(frac, 6), "note": f"$52 wallet-mirror mix ({old_bal['sol']} SOL + {old_bal['usdt']} USDT) scaled to $1,000 at SOL={px} ({px_row['ts_brt']})",
           "previous_52usd": old_bal}
cfg["starting_balances"] = new_bal
exp = cfg.setdefault("experiment", {})
exp["previous_runs"] = [{"name": "run_52usd_2026-09-24", "start_brt": first_start, "end_brt": end_brt,
                         "archive": str(DEST.relative_to(ROOT))}]
exp["day1_start_brt"] = None  # set below from the actual first new portfolio start
exp["capital_usd_each"] = 1000.0
(ROOT / "config.json").write_text(json.dumps(cfg, indent=2))
mc = json.loads((ROOT / "memecoins.json").read_text())
mc["previous_start_usdt_each"] = mc.get("start_usdt_each"); mc["start_usdt_each"] = 1000.0
(ROOT / "memecoins.json").write_text(json.dumps(mc, indent=2))

(DEST / "README.md").write_text(f"""# Archived paper run: the $52 run

This is the **$52 run** of the paper simulator (starting capital ≈ $52 per SOL portfolio: {old_bal['sol']} SOL + {old_bal['usdt']} USDT, a mirror
of the real wallet; memes 50 USDT each). Archived (moved, never deleted) when the experiment was restarted with $1,000 per portfolio.

- Start (first portfolio, BRT): {first_start}
- End / archived at (BRT): {end_brt}
- Paper only: no real trades, no keys; the real wallet was never touched.
- Layout mirrors the live tree (`data/`, `logs/`, `reports/`, `reviews/`); `archive/logs`, `archive/data` = rotated log archives of this run.
- Copied (still live in the new run): configs, criteria, `data/prices.jsonl` and `data/meme/prices/` (market data only).
- Hyperliquid funding-carry `p52` portfolio: see `funding_p52/`.
- Moved: {len(moved)} paths; copied: {len(copied)} paths (full list in `manifest.json`).
""")
(DEST / "manifest.json").write_text(json.dumps({"moved": moved, "copied": copied, "old_starting_balances": old_bal,
                                                "new_starting_balances": new_bal, "end_brt": end_brt}, indent=1))
print(json.dumps({"dest": str(DEST), "moved": len(moved), "copied": len(copied), "new_bal": new_bal, "end_brt": end_brt}))
