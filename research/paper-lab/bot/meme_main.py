#!/usr/bin/env python3
"""Memecoin paper-trading rotator. Separate process/portfolios from SOL bot.
NEVER signs/sends/reads wallet keys. Shares von HTTP server.
Cadence: one token per ~60s rotation.
Night review / v2 shadow: SKIPPED for memecoins (documented) to keep cost/rate-limits down.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # código do lab (não PAPER_LAB_ROOT)
from bot.paths import ROOT, LAB_DIR  # noqa: E402

from bot.paths import load_config, assert_no_keypair_touch  # noqa: E402
from bot.market import MarketFeed, MemePriceFeed  # noqa: E402
from bot.state import build_state  # noqa: E402
from bot.decision import VonClient, load_criteria  # noqa: E402
from bot.gates import apply_gates  # noqa: E402
from bot.portfolio import Portfolio  # noqa: E402
from bot.execute_sim import simulate_trade  # noqa: E402

BRT = timezone(timedelta(hours=-3))
STOP = False


def _sig(signum, frame):
    global STOP
    STOP = True


def brt_now():
    return datetime.now(tz=BRT)


def write_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(path)


def main() -> int:
    global STOP
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)

    cfg = load_config()
    assert_no_keypair_touch(cfg)
    meme_cfg_path = ROOT / cfg.get("memecoins", {}).get("config_path", "memecoins.json")
    meme = json.loads(meme_cfg_path.read_text())
    tokens = meme["tokens"]
    rotate = float(cfg.get("memecoins", {}).get("rotate_seconds", meme.get("cadence", {}).get("rotate_seconds", 60)))
    end_at = datetime.fromisoformat(cfg["end_at_brt"])
    start_usdt = float(meme.get("start_usdt_each", 50.0))

    decisions_log = ROOT / cfg["memecoins"]["decisions_log"]
    trades_log = ROOT / cfg["memecoins"]["trades_log"]
    status_path = ROOT / cfg["memecoins"]["status"]

    criteria = load_criteria(cfg["_paths"]["criteria_baseline"])
    von = VonClient(cfg)
    # Shared MarketFeed instance only for Jupiter quote_swap
    jup = MarketFeed(cfg, prices_log=ROOT / "data" / "meme" / "prices" / "_jup_meta.jsonl")
    prices = MemePriceFeed(cfg, tokens)

    # Bootstrap prices
    for attempt in range(10):
        marks = prices.fetch_all()
        if len(marks) >= len(tokens) // 2:
            break
        time.sleep(5)
    else:
        marks = prices.fetch_all()

    portfolios: dict[str, Portfolio] = {}
    for t in tokens:
        sym = t["symbol"]
        px = float((marks.get(sym) or {}).get("price_usd") or prices.last.get(sym) or 0)
        if px <= 0:
            px = 1e-6  # placeholder until first good mark
        pdir = ROOT / "data" / "meme" / "portfolios"
        edir = ROOT / "data" / "meme" / "equity"
        portfolios[sym] = Portfolio(
            f"meme_{sym}",
            pdir / f"{sym}.json",
            edir / f"{sym}.jsonl",
            start_sol=0.0,
            start_usdt=start_usdt,
            start_price=px,
            asset_mode="token",
            start_token=0.0,
        )

    cycles = 0
    errors = 0
    started = time.time()
    idx = 0
    finished = False
    print(f"meme bot start pid={os.getpid()} tokens={[t['symbol'] for t in tokens]} rotate={rotate}s", flush=True)

    while not STOP:
        loop_t0 = time.time()
        now = brt_now()
        allow_trade = now < end_at
        if now >= end_at and not finished:
            finished = True
            print("meme run window ended", flush=True)

        try:
            # Refresh marks every cycle (CoinGecko batch; cheap)
            marks = prices.fetch_all()
            # Pick one token this cycle
            t = tokens[idx % len(tokens)]
            idx += 1
            sym = t["symbol"]
            port = portfolios[sym]
            mark_row = marks.get(sym) or {}
            price = float(mark_row.get("price_usd") or prices.last.get(sym) or 0)
            if price <= 0:
                raise RuntimeError(f"no_price_{sym}")

            st = build_state(
                prices.history.get(sym) or [],
                position=port.position_word(),
                recent_pnl_mood=port.data.get("recent_pnl_mood") or "neutral",
            )
            decision = von.system_one(st["state"], criteria)
            gates = apply_gates(
                decision["chosen_action"],
                decision["confidence"],
                decision["skip_noul"],
                port.data,
                cfg["gates"],
                price_mark=price,
            )
            final = gates["final_action"] if allow_trade else "hold"
            extra = [] if allow_trade else ["run_ended"]
            decision_id = str(uuid.uuid4())
            traded = False
            if allow_trade and final in ("buy", "sell"):
                try:
                    fees = dict(cfg["fees"])
                    # SOL USD for fee estimate: try coinbase via last SOL history if any
                    fees["sol_usd"] = float(fees.get("sol_usd", 115.0))
                    tr = simulate_trade(
                        side=final,
                        portfolio=port,
                        market=jup,
                        gates_cfg=cfg["gates"],
                        fees_cfg=fees,
                        trades_log=trades_log,
                        decision_id=decision_id,
                        price_mark=price,
                        token_mint=t["mint"],
                        token_decimals=int(t["decimals"]),
                        asset_key="token",
                    )
                    traded = tr is not None
                except Exception as e:
                    final = "hold"
                    extra.append(f"sim_exec_error:{type(e).__name__}:{e}")

            eq = port.append_equity(price)
            row = {
                "ts": time.time(),
                "ts_brt": brt_now().isoformat(),
                "decision_id": decision_id,
                "portfolio": f"meme_{sym}",
                "symbol": sym,
                "mint": t["mint"],
                "state": st["state"],
                "features": st["features"],
                "price_usd": price,
                "price_source": mark_row.get("source"),
                "chosen_action": decision["chosen_action"],
                "probabilities": decision["probabilities"],
                "confidence": decision["confidence"],
                "skip_noul": decision["skip_noul"],
                "final_action": final,
                "gate_reasons": (gates.get("gate_reasons") or []) + extra,
                "blocked_trade": gates.get("blocked_trade") or (
                    final == "hold" and decision["chosen_action"] in ("buy", "sell")
                ),
                "latency_ms": decision["latency_ms"],
                "von_ok": decision["ok"],
                "von_error": decision.get("error"),
                "traded": traded,
                "equity_usd": eq["equity"],
                "token": port.data.get("token"),
                "usdt": port.data["usdt"],
                "bh_equity": eq["bh_equity"],
                "all_usdt_equity": eq["all_usdt_equity"],
                "criteria_version": "baseline",
            }
            decisions_log.parent.mkdir(parents=True, exist_ok=True)
            with open(decisions_log, "a") as f:
                f.write(json.dumps(row) + "\n")

            cycles += 1
            snap = {}
            for s, p in portfolios.items():
                px = float(prices.last.get(s) or 0)
                snap[s] = {
                    "equity_usd": p.equity_usd(px) if px else None,
                    "usdt": p.data["usdt"],
                    "token": p.data.get("token"),
                    "trades": p.data["trade_count"],
                    "price": px,
                    "bh_equity": p.bh_equity(px) if px else None,
                }
            write_status(
                status_path,
                {
                    "ok": True,
                    "ts": time.time(),
                    "ts_brt": brt_now().isoformat(),
                    "cycles": cycles,
                    "errors": errors,
                    "pid": os.getpid(),
                    "finished": finished or not allow_trade,
                    "last_symbol": sym,
                    "last_final": final,
                    "last_chosen": decision["chosen_action"],
                    "last_conf": decision["confidence"],
                    "last_skip": decision["skip_noul"],
                    "last_latency_ms": decision["latency_ms"],
                    "last_state": st["state"],
                    "rotate_seconds": rotate,
                    "tokens": snap,
                    "night_review": "skipped",
                    "paper_only": True,
                    "uptime_seconds": round(time.time() - started, 1),
                    "end_at_brt": cfg["end_at_brt"],
                },
            )
            print(
                f"meme cycle={cycles} {sym} px={price:.8g} final={final} "
                f"conf={decision['confidence']:.3f} lat={decision['latency_ms']:.0f}ms "
                f"eq={eq['equity']:.4f}",
                flush=True,
            )
        except Exception as e:
            errors += 1
            print(f"meme error: {e}\n{traceback.format_exc()}", flush=True)
            write_status(
                status_path,
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
            write_status(
                status_path,
                {
                    **(json.loads(status_path.read_text()) if status_path.exists() else {}),
                    "finished": True,
                    "finished_brt": brt_now().isoformat(),
                    "ok": True,
                },
            )
            break

        elapsed = time.time() - loop_t0
        sleep_for = max(1.0, rotate - elapsed)
        end_sleep = time.time() + sleep_for
        while time.time() < end_sleep and not STOP:
            time.sleep(min(0.5, end_sleep - time.time()))

    print(f"meme stopped cycles={cycles} errors={errors}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
