"""Rule-based indicators + signals for paper portfolios. Simulation only."""
from __future__ import annotations
import csv, json, math, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

BRT = timezone(timedelta(hours=-3))
UA = {"User-Agent": "paper-solana-bot/rules (sim-only)"}
from bot.paths import ROOT, STRATEGY_RESEARCH_ROOT
RESEARCH = STRATEGY_RESEARCH_ROOT / "data"

MEME_GATE_PAIRS = {
    "BONK": "BONK_USDT", "WIF": "WIF_USDT", "POPCAT": "POPCAT_USDT",
    "FARTCOIN": "FARTCOIN_USDT", "PNUT": "PNUT_USDT", "MEW": "MEW_USDT",
    "GOAT": "GOAT_USDT",
}


def _http_get(url: str, timeout: float = 25.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except Exception as e:
        return 0, str(e).encode()


def load_csv_ohlc(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append({
                "ts": int(float(row["ts"])),
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
                "volume": float(row.get("volume") or 0),
            })
    rows.sort(key=lambda r: r["ts"])
    return rows


def merge_bars(existing: list[dict], new_bars: list[dict]) -> list[dict]:
    by = {r["ts"]: r for r in existing}
    for r in new_bars:
        by[r["ts"]] = r
    return [by[k] for k in sorted(by)]


def fetch_coinbase_sol_1h(start_ts: int | None = None, end_ts: int | None = None) -> list[dict]:
    end_ts = end_ts or int(time.time())
    start_ts = start_ts or (end_ts - 10 * 86400)
    rows: list[dict] = []
    cursor = start_ts
    gran = 3600
    while cursor < end_ts:
        win_end = min(end_ts, cursor + gran * 280)
        start_iso = datetime.fromtimestamp(cursor, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        end_iso = datetime.fromtimestamp(win_end, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        url = (
            f"https://api.exchange.coinbase.com/products/SOL-USD/candles"
            f"?granularity={gran}&start={start_iso}&end={end_iso}"
        )
        status, body = _http_get(url)
        if status != 200:
            break
        data = json.loads(body.decode())
        for c in data:
            t, lo, hi, o, cl, vol = c
            rows.append({"ts": int(t), "open": float(o), "high": float(hi),
                         "low": float(lo), "close": float(cl), "volume": float(vol)})
        cursor = win_end
        time.sleep(0.2)
    return merge_bars([], rows)


def fetch_gate_1h(pair: str, start_ts: int | None = None, end_ts: int | None = None) -> list[dict]:
    end_ts = end_ts or int(time.time())
    start_ts = start_ts or (end_ts - 10 * 86400)
    rows: list[dict] = []
    cursor = start_ts
    sec = 3600
    while cursor < end_ts:
        win_end = min(end_ts, cursor + sec * 900)
        url = (
            f"https://api.gateio.ws/api/v4/spot/candlesticks"
            f"?currency_pair={pair}&interval=1h&from={cursor}&to={win_end}"
        )
        status, body = _http_get(url)
        if status != 200:
            break
        data = json.loads(body.decode())
        if not isinstance(data, list):
            break
        for c in data:
            t = int(float(c[0]))
            rows.append({
                "ts": t, "open": float(c[5]), "high": float(c[3]),
                "low": float(c[4]), "close": float(c[2]), "volume": float(c[6]),
            })
        cursor = win_end
        time.sleep(0.15)
    return merge_bars([], rows)


def ema_series(closes: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) < n:
        return out
    a = 2 / (n + 1)
    out[n - 1] = sum(closes[:n]) / n
    for i in range(n, len(closes)):
        out[i] = a * closes[i] + (1 - a) * float(out[i - 1])
    return out


def rsi_series(closes: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) < n + 1:
        return out
    gains, losses = [], []
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains) / n
    avg_loss = sum(losses) / n
    rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
    out[n] = 100 - (100 / (1 + rs))
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (n - 1) + max(d, 0.0)) / n
        avg_loss = (avg_loss * (n - 1) + max(-d, 0.0)) / n
        rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
        out[i] = 100 - (100 / (1 + rs))
    return out


def donchian_break(bars: list[dict], n: int = 20) -> str:
    """Signal on last COMPLETED bar using prior n bars (no lookahead)."""
    if len(bars) < n + 1:
        return "hold"
    # evaluate at last bar index using highs/lows of bars[-n-1:-1]
    window = bars[-(n + 1):-1]
    last = bars[-1]
    hh = max(b["high"] for b in window)
    ll = min(b["low"] for b in window)
    if last["close"] > hh:
        return "buy"
    if last["close"] < ll:
        return "sell"
    return "hold"


class CandleBook:
    """In-memory 1h OHLC with warm-up from research CSVs + live refresh."""

    def __init__(self):
        self.sol: list[dict] = []
        self.memes: dict[str, list[dict]] = {s: [] for s in MEME_GATE_PAIRS}
        self.started_ts: float = time.time()  # trades only on bars closing after this
        self.last_acted_bar: dict[str, int] = {}  # key -> last bar ts acted on
        self.meta: dict[str, Any] = {}

    def warm_up(self) -> dict:
        """Load historical candles. Does NOT trade on them."""
        sol_path = RESEARCH / "SOL_USD_1h.csv"
        self.sol = load_csv_ohlc(sol_path)
        # top up with live fetch (last ~5 days) to include any gap to now
        live = fetch_coinbase_sol_1h(int(time.time()) - 5 * 86400)
        self.sol = merge_bars(self.sol, live)
        # drop forming candle (current incomplete hour)
        hour_floor = int(time.time()) // 3600 * 3600
        self.sol = [b for b in self.sol if b["ts"] < hour_floor]
        for sym, pair in MEME_GATE_PAIRS.items():
            path = RESEARCH / f"{sym}_USDT_1h.csv"
            self.memes[sym] = load_csv_ohlc(path)
            live_m = fetch_gate_1h(pair, int(time.time()) - 5 * 86400)
            self.memes[sym] = merge_bars(self.memes[sym], live_m)
            self.memes[sym] = [b for b in self.memes[sym] if b["ts"] < hour_floor]
        self.started_ts = time.time()
        self.meta = {
            "warmed_at_brt": datetime.now(tz=BRT).isoformat(),
            "sol_bars": len(self.sol),
            "sol_first_brt": datetime.fromtimestamp(self.sol[0]["ts"], tz=BRT).isoformat() if self.sol else None,
            "sol_last_brt": datetime.fromtimestamp(self.sol[-1]["ts"], tz=BRT).isoformat() if self.sol else None,
            "meme_bars": {s: len(self.memes[s]) for s in self.memes},
            "trade_only_after_ts": self.started_ts,
            "trade_only_after_brt": datetime.fromtimestamp(self.started_ts, tz=BRT).isoformat(),
        }
        return self.meta

    def refresh_closed(self) -> list[str]:
        """Fetch latest closed 1h bars; return list of keys with NEW closed bars after start."""
        hour_floor = int(time.time()) // 3600 * 3600
        new_keys = []
        live = fetch_coinbase_sol_1h(hour_floor - 3 * 3600, hour_floor + 1)
        live = [b for b in live if b["ts"] < hour_floor]
        before = self.sol[-1]["ts"] if self.sol else 0
        self.sol = merge_bars(self.sol, live)
        if self.sol and self.sol[-1]["ts"] > before and self.sol[-1]["ts"] >= int(self.started_ts) // 3600 * 3600:
            # bar closed at/after start hour
            if self.sol[-1]["ts"] + 3600 > self.started_ts:  # closed after start
                new_keys.append("SOL")
        for sym, pair in MEME_GATE_PAIRS.items():
            live_m = fetch_gate_1h(pair, hour_floor - 3 * 3600, hour_floor + 1)
            live_m = [b for b in live_m if b["ts"] < hour_floor]
            before_m = self.memes[sym][-1]["ts"] if self.memes[sym] else 0
            self.memes[sym] = merge_bars(self.memes[sym], live_m)
            if self.memes[sym] and self.memes[sym][-1]["ts"] > before_m:
                if self.memes[sym][-1]["ts"] + 3600 > self.started_ts:
                    new_keys.append(sym)
        return new_keys

    def sol_indicators(self, ema_fast: int = 12, ema_slow: int = 26, rsi_period: int = 14) -> dict:
        """Indicadores de SOL na última barra fechada. Os períodos vêm de params.json (rule.*); as chaves
        ema12/ema26 guardam a EMA rápida/lenta pedida (nomes antigos mantidos)."""
        closes = [b["close"] for b in self.sol]
        ema12 = ema_series(closes, int(ema_fast))
        ema26 = ema_series(closes, int(ema_slow))
        rsi = rsi_series(closes, int(rsi_period))
        i = len(closes) - 1
        if i < 0:
            return {"ready": False}
        e12, e26, r = ema12[i], ema26[i], rsi[i]
        r_prev = rsi[i - 1] if i >= 1 else None
        bull = (e12 is not None and e26 is not None and e12 > e26)
        return {
            "ready": e12 is not None and e26 is not None and r is not None,
            "close": closes[i],
            "bar_ts": self.sol[i]["ts"],
            "bar_brt": datetime.fromtimestamp(self.sol[i]["ts"], tz=BRT).isoformat(),
            "ema12": e12, "ema26": e26, "rsi": r, "rsi_prev": r_prev,
            "sol_regime_bull": bull,
            "n_bars": len(closes),
        }

    def meme_indicators(self, sym: str, donchian: int = 20) -> dict:
        bars = self.memes.get(sym) or []
        n = int(donchian)
        if len(bars) < n + 1:
            return {"ready": False, "symbol": sym}
        closes = [b["close"] for b in bars]
        sig = donchian_break(bars, n)
        return {
            "ready": True, "symbol": sym, "close": closes[-1],
            "bar_ts": bars[-1]["ts"],
            "bar_brt": datetime.fromtimestamp(bars[-1]["ts"], tz=BRT).isoformat(),
            "donchian20_signal": sig,
            "n_bars": len(bars),
        }


def grid_signal(state: dict, price: float, grid_pct: float = 0.02, levels: int = 4) -> tuple[str, dict]:
    """Return buy/sell/hold and updated grid state. state keys: ref, buys_open."""
    ref = float(state.get("ref") or price)
    buys_open = int(state.get("buys_open") or 0)
    action = "hold"
    if buys_open < levels and price <= ref * (1 - grid_pct * (buys_open + 1)):
        action = "buy"
    elif buys_open > 0 and price >= ref * (1 + grid_pct * buys_open):
        action = "sell"
    # recenter when flat
    new_state = dict(state)
    new_state["ref"] = ref
    new_state["buys_open"] = buys_open
    if buys_open == 0 and abs(price / ref - 1) > grid_pct * 2:
        new_state["ref"] = price
    return action, new_state


def rsi_signal(rsi: float | None, rsi_prev: float | None, lo: float = 30.0, hi: float = 70.0) -> str:
    if rsi is None or rsi_prev is None:
        return "hold"
    if rsi_prev < lo and rsi >= lo:
        return "buy"
    if rsi_prev > hi and rsi <= hi:
        return "sell"
    return "hold"


def load_rule_enabled(overlay: dict, strategy_key: str, cfg_rules: dict) -> bool:
    """Global + per-strategy enable from config and overlay paused flags."""
    if not cfg_rules.get("enabled", True):
        return False
    strat = (cfg_rules.get("strategies") or {}).get(strategy_key) or {}
    if not strat.get("enabled", True):
        return False
    ports = overlay.get("portfolios") or {}
    # map strategy key to portfolio pause name(s)
    if strategy_key in ports and ports[strategy_key].get("paused"):
        return False
    if (overlay.get("bots") or {}).get("rules_paused"):
        return False
    return True
