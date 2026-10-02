#!/usr/bin/env python3
"""
Paper-only Solana trading loop (alexsssaint / von pattern).
NEVER signs, sends, or loads wallet keypairs.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure package import when run as script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # código do lab (não PAPER_LAB_ROOT)
from bot.paths import ROOT, LAB_DIR  # noqa: E402

from bot.paths import load_config, assert_no_keypair_touch  # noqa: E402
from bot.market import MarketFeed  # noqa: E402
from bot.state import build_state  # noqa: E402
from bot.decision import VonClient, load_criteria  # noqa: E402
from bot.gates import apply_gates  # noqa: E402
from bot.portfolio import Portfolio  # noqa: E402
from bot.execute_sim import simulate_trade  # noqa: E402
from bot.review import run_night_review  # noqa: E402

BRT = timezone(timedelta(hours=-3))
STOP = False


def _handle_sig(signum, frame):
    global STOP
    STOP = True


def brt_now() -> datetime:
    return datetime.now(tz=BRT)


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


def write_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(path)


def append_decision(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")


def run_cycle_for(
    name: str,
    portfolio: Portfolio,
    criteria: dict,
    von: VonClient,
    market: MarketFeed,
    price_row: dict,
    cfg: dict,
    allow_trade: bool,
) -> dict:
    paths = cfg["_paths"]
    price = float(price_row["price_usd"])
    st = build_state(
        market.history,
        position=portfolio.position_word(),
        recent_pnl_mood=portfolio.data.get("recent_pnl_mood") or "neutral",
    )
    decision = von.system_one(st["state"], criteria)
    gates = apply_gates(
        decision["chosen_action"],
        decision["confidence"],
        decision["skip_noul"],
        portfolio.data,
        cfg["gates"],
    )
    final = gates["final_action"] if allow_trade else "hold"
    extra_reasons = [] if allow_trade else ["run_ended"]

    decision_id = str(uuid.uuid4())
    trade_row = None
    if allow_trade and final in ("buy", "sell"):
        try:
            trade_row = simulate_trade(
                side=final,
                portfolio=portfolio,
                market=market,
                gates_cfg=cfg["gates"],
                fees_cfg=cfg["fees"],
                trades_log=paths["trades_log"],
                decision_id=decision_id,
                price_mark=price,
            )
        except Exception as e:
            # Fail closed: hold, log error
            final = "hold"
            extra_reasons.append(f"sim_exec_error:{type(e).__name__}")
            trade_row = None

    eq = portfolio.append_equity(price)
    row = {
        "ts": time.time(),
        "ts_brt": brt_now().isoformat(),
        "decision_id": decision_id,
        "portfolio": name,
        "state": st["state"],
        "features": st["features"],
        "price_usd": price,
        "price_source": price_row.get("source"),
        "chosen_action": decision["chosen_action"],
        "probabilities": decision["probabilities"],
        "confidence": decision["confidence"],
        "skip_noul": decision["skip_noul"],
        "final_action": final,
        "gate_reasons": (gates.get("gate_reasons") or []) + extra_reasons,
        "blocked_trade": gates.get("blocked_trade") or (final == "hold" and decision["chosen_action"] in ("buy", "sell")),
        "latency_ms": decision["latency_ms"],
        "von_ok": decision["ok"],
        "von_error": decision.get("error"),
        "fail_closed": decision.get("fail_closed", False),
        "traded": trade_row is not None,
        "equity_usd": eq["equity"],
        "sol": portfolio.data["sol"],
        "usdt": portfolio.data["usdt"],
        "criteria_version": criteria.get("version", "unknown"),
    }
    append_decision(paths["decisions_log"], row)
    return row


def main() -> int:
    global STOP
    signal.signal(signal.SIGTERM, _handle_sig)
    signal.signal(signal.SIGINT, _handle_sig)

    cfg = load_config()
    assert_no_keypair_touch(cfg)
    # Refuse to open keypair files
    for p in cfg.get("forbid_keypair_paths", []):
        if Path(p).exists():
            # Ensure we never mmap them — just don't open.
            pass

    paths = cfg["_paths"]
    end_at = parse_iso(cfg["end_at_brt"])
    review_at = parse_iso(cfg["night_review_at_brt"])
    cycle = float(cfg["cycle_seconds"])

    # Seed market
    market = MarketFeed(cfg)
    try:
        price_row = market.fetch()
    except Exception as e:
        print(f"FATAL initial price fetch: {e}", flush=True)
        return 2
    start_price = float(price_row["price_usd"])
    bal = cfg["starting_balances"]

    baseline = Portfolio(
        "baseline",
        paths["portfolio_baseline"],
        paths["equity_baseline"],
        bal["sol"],
        bal["usdt"],
        start_price,
    )
    criteria_baseline = load_criteria(paths["criteria_baseline"])

    von = VonClient(cfg)

    # Wait for von health
    for i in range(60):
        try:
            import urllib.request

            urllib.request.urlopen(cfg["von"]["base_url"] + "/docs", timeout=2)
            break
        except Exception:
            try:
                # some servers may not have /docs — try a tiny systemone later
                urllib.request.urlopen(cfg["von"]["base_url"] + "/", timeout=2)
                break
            except Exception:
                time.sleep(1)
    else:
        print("WARNING: von HTTP not confirmed; will fail-closed until up", flush=True)

    v2_portfolio: Portfolio | None = None
    criteria_v2: dict | None = None
    review_done = paths["review_md"].exists() and paths["criteria_v2"].exists()
    if review_done:
        criteria_v2 = load_criteria(paths["criteria_v2"])
        v2_portfolio = Portfolio(
            "v2",
            paths["portfolio_v2"],
            paths["equity_v2"],
            bal["sol"],
            bal["usdt"],
            start_price,
        )

    cycles = 0
    errors = 0
    started = time.time()
    finished = False

    # Persist run meta
    run_meta = {
        "started_ts": started,
        "started_brt": brt_now().isoformat(),
        "end_at_brt": cfg["end_at_brt"],
        "pid": os.getpid(),
        "paper_only": True,
    }
    (ROOT / "run" / "run_meta.json").write_text(json.dumps(run_meta, indent=2))

    print(f"paper bot start pid={os.getpid()} price={start_price:.4f} end={cfg['end_at_brt']}", flush=True)

    while not STOP:
        loop_t0 = time.time()
        now = brt_now()
        allow_trade = now < end_at
        if now >= end_at and not finished:
            finished = True
            print(f"run window ended at {now.isoformat()}; stopping new trades", flush=True)

        try:
            price_row = market.fetch()
        except Exception as e:
            errors += 1
            write_status(
                paths["status"],
                {
                    "ok": False,
                    "error": f"price_fetch:{e}",
                    "ts_brt": now.isoformat(),
                    "cycles": cycles,
                    "errors": errors,
                    "pid": os.getpid(),
                    "finished": finished,
                },
            )
            time.sleep(cycle)
            continue

        # Night review trigger (once)
        if (not review_done) and now >= review_at:
            try:
                print("running night review...", flush=True)
                summary = run_night_review(cfg)
                print(f"night review done: {summary}", flush=True)
                criteria_v2 = load_criteria(paths["criteria_v2"])
                # Fresh shadow portfolio from SAME starting balances (not current)
                # Use original start price from baseline meta
                sp = float(baseline.data.get("start_price") or price_row["price_usd"])
                # If v2 portfolio file somehow exists from partial run, keep it; else create fresh
                if paths["portfolio_v2"].exists():
                    v2_portfolio = Portfolio(
                        "v2",
                        paths["portfolio_v2"],
                        paths["equity_v2"],
                        bal["sol"],
                        bal["usdt"],
                        sp,
                    )
                else:
                    v2_portfolio = Portfolio(
                        "v2",
                        paths["portfolio_v2"],
                        paths["equity_v2"],
                        bal["sol"],
                        bal["usdt"],
                        sp,
                    )
                review_done = True
            except Exception as e:
                errors += 1
                print(f"night review failed: {e}\n{traceback.format_exc()}", flush=True)

        try:
            row_b = run_cycle_for(
                "baseline",
                baseline,
                criteria_baseline,
                von,
                market,
                price_row,
                cfg,
                allow_trade=allow_trade,
            )
            row_v2 = None
            if v2_portfolio is not None and criteria_v2 is not None:
                row_v2 = run_cycle_for(
                    "v2",
                    v2_portfolio,
                    criteria_v2,
                    von,
                    market,
                    price_row,
                    cfg,
                    allow_trade=allow_trade,
                )
            cycles += 1
            status = {
                "ok": True,
                "ts": time.time(),
                "ts_brt": brt_now().isoformat(),
                "cycles": cycles,
                "errors": errors,
                "pid": os.getpid(),
                "finished": finished or not allow_trade,
                "price_usd": price_row["price_usd"],
                "price_source": price_row.get("source"),
                "baseline": {
                    "sol": baseline.data["sol"],
                    "usdt": baseline.data["usdt"],
                    "equity_usd": row_b["equity_usd"],
                    "last_final": row_b["final_action"],
                    "last_chosen": row_b["chosen_action"],
                    "last_conf": row_b["confidence"],
                    "last_skip": row_b["skip_noul"],
                    "last_latency_ms": row_b["latency_ms"],
                    "trades": baseline.data["trade_count"],
                    "state": row_b["state"],
                },
                "v2": None
                if row_v2 is None
                else {
                    "sol": v2_portfolio.data["sol"],
                    "usdt": v2_portfolio.data["usdt"],
                    "equity_usd": row_v2["equity_usd"],
                    "last_final": row_v2["final_action"],
                    "trades": v2_portfolio.data["trade_count"],
                    "criteria_version": "v2",
                },
                "review_done": review_done,
                "uptime_seconds": round(time.time() - started, 1),
                "paper_only": True,
                "end_at_brt": cfg["end_at_brt"],
            }
            write_status(paths["status"], status)
            print(
                f"cycle={cycles} price={price_row['price_usd']:.4f} "
                f"src={price_row.get('source')} final={row_b['final_action']} "
                f"conf={row_b['confidence']:.3f} skip={row_b['skip_noul']:.3f} "
                f"lat={row_b['latency_ms']:.0f}ms eq={row_b['equity_usd']:.4f}",
                flush=True,
            )
        except Exception as e:
            errors += 1
            print(f"cycle error: {e}\n{traceback.format_exc()}", flush=True)
            write_status(
                paths["status"],
                {
                    "ok": False,
                    "error": str(e),
                    "ts_brt": brt_now().isoformat(),
                    "cycles": cycles,
                    "errors": errors,
                    "pid": os.getpid(),
                    "finished": finished,
                },
            )

        if finished:
            # Keep heartbeating a few times then exit cleanly
            write_status(
                paths["status"],
                {
                    **(json.loads(paths["status"].read_text()) if paths["status"].exists() else {}),
                    "finished": True,
                    "finished_brt": brt_now().isoformat(),
                    "ok": True,
                },
            )
            print("finished run window; exiting main loop", flush=True)
            break

        elapsed = time.time() - loop_t0
        sleep_for = max(0.5, cycle - elapsed)
        # interruptible sleep
        end_sleep = time.time() + sleep_for
        while time.time() < end_sleep and not STOP:
            time.sleep(max(0.0, min(0.5, end_sleep - time.time())))

    print(f"stopped cycles={cycles} errors={errors}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
