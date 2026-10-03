"""Price feeds + Jupiter quote-only. Never attaches a taker / never executes."""
from __future__ import annotations
import json, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from typing import Any
from datetime import datetime, timezone, timedelta

USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOL = "So11111111111111111111111111111111111111112"
BRT = timezone(timedelta(hours=-3))
_JUP_LOCK_UNTIL = 0.0
_JUP_LAST_OK = 0.0

def _brt(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=BRT).isoformat()

def _http_get(url: str, timeout: float = 12.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "paper-solana-bot/0.1 (sim-only)"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except Exception as e:
        return 0, str(e).encode()

class MarketFeed:
    def __init__(self, cfg: dict, prices_log: Path | None = None):
        self.cfg = cfg
        self.m = cfg["market"]
        self.prices_log = prices_log or cfg["_paths"]["prices_log"]
        self._last_price: float | None = None
        self._last_impact = 0.0
        self.history: list[dict] = []
        self._load()

    def _load(self):
        p = Path(self.prices_log)
        if not p.exists(): return
        try:
            for line in p.read_text().splitlines():
                if line.strip():
                    self.history.append(json.loads(line))
            maxn = int(self.m.get("price_history_max", 2000))
            self.history = self.history[-maxn:]
            if self.history:
                self._last_price = float(self.history[-1]["price_usd"])
                self._last_impact = float(self.history[-1].get("price_impact_pct") or 0)
        except Exception:
            pass

    def _jup_ok(self) -> bool:
        return time.time() >= _JUP_LOCK_UNTIL

    def _jup_trip(self, secs: float):
        global _JUP_LOCK_UNTIL
        _JUP_LOCK_UNTIL = max(_JUP_LOCK_UNTIL, time.time() + secs)

    def _jupiter_sol_price(self) -> dict:
        global _JUP_LAST_OK
        if not self._jup_ok():
            raise RuntimeError("jupiter_cooldown")
        min_iv = float(self.m.get("jupiter_min_interval_seconds", 20))
        if time.time() - _JUP_LAST_OK < min_iv:
            raise RuntimeError("jupiter_min_interval")
        params = {
            "inputMint": USDT, "outputMint": SOL,
            "amount": str(int(self.m["quote_usdt_amount"])),
            "slippageBps": str(self.m.get("slippage_bps", 50)),
        }
        url = self.m["jupiter_quote_url"] + "?" + urllib.parse.urlencode(params)
        status, body = _http_get(url)
        if status == 429:
            self._jup_trip(90); raise RuntimeError("jupiter_429")
        if status != 200:
            raise RuntimeError(f"jupiter_http_{status}")
        data = json.loads(body.decode())
        in_amt = float(data["inAmount"]) / 1e6
        out_amt = float(data["outAmount"]) / 1e9
        if out_amt <= 0: raise RuntimeError("jupiter_zero_out")
        _JUP_LAST_OK = time.time()
        return {
            "price_usd": in_amt / out_amt,
            "price_impact_pct": float(data.get("priceImpactPct") or 0),
            "source": "jupiter_quote",
            "quote": data,
        }

    def _coinbase_sol_price(self) -> dict:
        status, body = _http_get("https://api.coinbase.com/v2/prices/SOL-USD/spot")
        if status != 200: raise RuntimeError(f"coinbase_http_{status}")
        price = float(json.loads(body.decode())["data"]["amount"])
        return {"price_usd": price, "price_impact_pct": self._last_impact, "source": "coinbase", "quote": None}

    def quote_swap(self, *, input_mint: str, output_mint: str, amount_in: float,
                   in_decimals: int, slippage_bps: int | None = None) -> dict:
        slip = slippage_bps if slippage_bps is not None else int(self.m.get("slippage_bps", 50))
        raw = int(round(amount_in * (10 ** in_decimals)))
        if raw <= 0: raise ValueError("amount_too_small")
        params = {"inputMint": input_mint, "outputMint": output_mint, "amount": str(raw), "slippageBps": str(slip)}
        url = self.m["jupiter_quote_url"] + "?" + urllib.parse.urlencode(params)
        last = None
        for attempt in range(6):
            if not self._jup_ok():
                time.sleep(min(30, max(1, _JUP_LOCK_UNTIL - time.time())))
            status, body = _http_get(url)
            if status == 429:
                self._jup_trip(60 * (attempt + 1)); last = "429"; time.sleep(min(45, 5*(attempt+1))); continue
            if status != 200:
                last = f"http_{status}"; time.sleep(2); continue
            global _JUP_LAST_OK
            _JUP_LAST_OK = time.time()
            return json.loads(body.decode())
        raise RuntimeError(f"quote_failed_{last}")

    def fetch(self) -> dict:
        errors = []
        result = None
        prefer_cb = (not self._jup_ok()) or bool(self.m.get("prefer_secondary_on_429", True))
        order = ["coinbase", "jupiter"] if prefer_cb else ["jupiter", "coinbase"]
        for src in order:
            try:
                result = self._coinbase_sol_price() if src == "coinbase" else self._jupiter_sol_price()
                break
            except Exception as e:
                errors.append(f"{src}:{e}")
        if result is None:
            if self._last_price is None:
                raise RuntimeError(";".join(errors))
            result = {"price_usd": self._last_price, "price_impact_pct": self._last_impact, "source": "stale_last", "quote": None, "stale": True}
        ts = time.time()
        row = {
            "ts": ts, "ts_brt": _brt(ts), "price_usd": float(result["price_usd"]),
            "price_impact_pct": float(result.get("price_impact_pct") or 0),
            "source": result["source"], "stale": bool(result.get("stale")), "errors": errors,
        }
        self._last_price = row["price_usd"]
        self._last_impact = row["price_impact_pct"]
        self.history.append(row)
        self.history = self.history[-int(self.m.get("price_history_max", 2000)):]
        Path(self.prices_log).parent.mkdir(parents=True, exist_ok=True)
        with open(self.prices_log, "a") as f:
            f.write(json.dumps(row) + "\n")
        return row

    @property
    def last_price(self):
        return self._last_price


class MemePriceFeed:
    """CoinGecko batch marks for memecoins."""
    def __init__(self, cfg: dict, tokens: list[dict]):
        self.cfg = cfg
        self.tokens = {t["symbol"]: t for t in tokens}
        self.cg_ids = {t["symbol"]: t["coingecko_id"] for t in tokens}
        self.history: dict[str, list] = {t["symbol"]: [] for t in tokens}
        self.last: dict[str, float] = {}
        self._lock_until = 0.0
        root = Path(cfg["paths"]["root"]) / "data" / "meme" / "prices"
        for sym in self.tokens:
            p = root / f"{sym}.jsonl"
            if not p.exists(): continue
            try:
                for line in p.read_text().splitlines():
                    if line.strip():
                        self.history[sym].append(json.loads(line))
                if self.history[sym]:
                    self.last[sym] = float(self.history[sym][-1]["price_usd"])
            except Exception:
                pass

    def fetch_all(self) -> dict[str, dict]:
        out = {}
        if time.time() < self._lock_until:
            for sym, px in self.last.items():
                out[sym] = {"price_usd": px, "source": "stale_last", "stale": True}
            return out
        ids = ",".join(sorted(set(self.cg_ids.values())))
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        status, body = _http_get(url, timeout=20)
        if status == 429:
            self._lock_until = time.time() + 90
            for sym, px in self.last.items():
                out[sym] = {"price_usd": px, "source": "stale_cg_429", "stale": True}
            return out
        if status != 200:
            for sym, px in self.last.items():
                out[sym] = {"price_usd": px, "source": f"stale_cg_{status}", "stale": True}
            return out
        data = json.loads(body.decode())
        ts = time.time()
        root = Path(self.cfg["paths"]["root"]) / "data" / "meme" / "prices"
        root.mkdir(parents=True, exist_ok=True)
        for sym, cg in self.cg_ids.items():
            info = data.get(cg) or {}
            if "usd" not in info:
                if sym in self.last:
                    out[sym] = {"price_usd": self.last[sym], "source": "stale_missing", "stale": True}
                continue
            px = float(info["usd"])
            row = {"ts": ts, "ts_brt": _brt(ts), "symbol": sym, "price_usd": px, "source": "coingecko"}
            self.history[sym].append(row)
            self.history[sym] = self.history[sym][-2000:]
            self.last[sym] = px
            with open(root / f"{sym}.jsonl", "a") as f:
                f.write(json.dumps(row) + "\n")
            out[sym] = row
        return out
