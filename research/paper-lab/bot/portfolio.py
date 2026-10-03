"""Simulated portfolio + benchmarks. Paper only."""
from __future__ import annotations
import json, time
from pathlib import Path

class Portfolio:
    def __init__(self, name: str, path: Path, equity_path: Path,
                 start_sol: float, start_usdt: float, start_price: float,
                 *, asset_mode: str = "sol", start_token: float = 0.0):
        self.name = name
        self.path = path
        self.equity_path = equity_path
        self.asset_mode = asset_mode
        if path.exists():
            self.data = json.loads(path.read_text())
            self.asset_mode = self.data.get("asset_mode", asset_mode)
        else:
            if asset_mode == "token":
                bh_token = (start_usdt / start_price) if start_price > 0 else 0.0
                self.data = {
                    "name": name, "asset_mode": "token", "token": start_token, "sol": 0.0,
                    "usdt": start_usdt, "start_token": start_token, "start_sol": 0.0,
                    "start_usdt": start_usdt, "start_price": start_price,
                    "benchmark_buy_hold": {"token": bh_token, "usdt": 0.0},
                    "benchmark_all_usdt": {"usdt": start_usdt},
                    "realized_pnl_usdt": 0.0, "fees_paid_usdt": 0.0, "fees_paid_sol": 0.0,
                    "trade_count": 0, "last_trade_ts": None, "trade_timestamps": [],
                    "position": "held" if start_token > 0 else "flat",
                    "recent_pnl_mood": "neutral", "created_ts": time.time(),
                }
            else:
                self.data = {
                    "name": name, "asset_mode": "sol", "sol": start_sol, "token": 0.0,
                    "usdt": start_usdt, "start_sol": start_sol, "start_usdt": start_usdt,
                    "start_price": start_price,
                    "benchmark_buy_hold": {"sol": start_sol, "usdt": start_usdt},
                    "benchmark_all_usdt": {"usdt": start_usdt + start_sol * start_price},
                    "realized_pnl_usdt": 0.0, "fees_paid_usdt": 0.0, "fees_paid_sol": 0.0,
                    "trade_count": 0, "last_trade_ts": None, "trade_timestamps": [],
                    "position": "held" if start_sol > 1e-9 else "flat",
                    "recent_pnl_mood": "neutral", "created_ts": time.time(),
                }
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.path)

    def equity_usd(self, price: float) -> float:
        if self.data.get("asset_mode") == "token":
            return float(self.data["usdt"]) + float(self.data.get("token") or 0) * price
        return float(self.data["usdt"]) + float(self.data["sol"]) * price

    def bh_equity(self, price: float) -> float:
        bh = self.data["benchmark_buy_hold"]
        if self.data.get("asset_mode") == "token":
            return float(bh.get("usdt") or 0) + float(bh.get("token") or 0) * price
        return float(bh["usdt"]) + float(bh["sol"]) * price

    def all_usdt_equity(self, price: float) -> float:
        return float(self.data["benchmark_all_usdt"]["usdt"])

    def append_equity(self, price: float, ts: float | None = None) -> dict:
        ts = ts or time.time()
        row = {
            "ts": ts, "price": price, "sol": self.data.get("sol"), "token": self.data.get("token"),
            "usdt": self.data["usdt"], "equity": self.equity_usd(price),
            "bh_equity": self.bh_equity(price), "all_usdt_equity": self.all_usdt_equity(price),
            "trade_count": self.data["trade_count"],
        }
        self.equity_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.equity_path, "a") as f:
            f.write(json.dumps(row) + "\n")
        return row

    def position_word(self) -> str:
        if self.data.get("asset_mode") == "token":
            tok = float(self.data.get("token") or 0)
            if tok > 1e-12: return "held"
            return "sold" if self.data.get("trade_count", 0) > 0 else "flat"
        sol = float(self.data["sol"])
        if sol > 1e-6: return "held"
        return "sold" if self.data.get("trade_count", 0) > 0 else "flat"

    def update_mood(self, trade_pnl_usdt: float):
        if trade_pnl_usdt > 0.05: self.data["recent_pnl_mood"] = "buoyed"
        elif trade_pnl_usdt < -0.05: self.data["recent_pnl_mood"] = "stung"
        else: self.data["recent_pnl_mood"] = "neutral"
