"""Shared helpers for paper SOL + meme bots. Never touches keypairs or sends txs."""
from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path("/home/box/solana-trader/paper")
BRT = timezone(timedelta(hours=-3))
USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOL = "So11111111111111111111111111111111111111112"

_JUP_LOCK = 0.0
_JUP_LAST = 0.0


def brt_now() -> datetime:
    return datetime.now(tz=BRT)


def brt_iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or time.time(), tz=BRT).isoformat()


def load_cfg() -> dict:
    return json.loads((ROOT / "config.json").read_text())


def assert_no_keys(cfg: dict) -> None:
    for p in cfg.get("forbid_keypair_paths", []):
        # Intentionally never open these paths
        _ = p


def http_get(url: str, timeout: float = 15.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "paper-bot/0.1"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.read() if hasattr(e, "read") else b"")
    except Exception as e:
        return 0, str(e).encode()


def http_post_json(url: str, payload: dict, timeout: float = 30.0) -> tuple[int, Any]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        try:
            return e.code, json.loads(body.decode())
        except Exception:
            return e.code, {"error": body.decode(errors="replace")[:300]}
    except Exception as e:
        return 0, {"error": str(e)}


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)


def read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def build_state(history: list[dict], position: str, mood: str) -> dict:
    prices = [float(h["price_usd"]) for h in history if h.get("price_usd") is not None]
    impacts = [float(h.get("price_impact_pct") or 0) for h in history]
    if len(prices) < 2:
        words = ["deep", "quiet", "flat", "calm", "early", "gray", "wide", "soft", "early", "mid", "quiet", position or "flat"]
        return {"state": " ".join(words), "features": {"insufficient": True}}

    def pct(a, b):
        return 0.0 if b == 0 else (a - b) / b * 100

    p0 = prices[-1]
    ps = prices[-min(4, len(prices))]
    pm = prices[-min(20, len(prices))]
    pl = prices[-min(80, len(prices))]
    rs, rm, rl = pct(p0, ps), pct(p0, pm), pct(p0, pl)
    win = prices[-min(20, len(prices)) :]
    rets = [pct(win[i], win[i - 1]) for i in range(1, len(win))]
    if len(rets) >= 2:
        m = sum(rets) / len(rets)
        vol = math.sqrt(sum((r - m) ** 2 for r in rets) / len(rets))
    else:
        vol = 0.0
    lo, hi = min(win), max(win)
    pos = (p0 - lo) / (hi - lo) if hi > lo else 0.5
    impact = impacts[-1] if impacts else 0.0
    iavg = sum(impacts[-min(10, len(impacts)) :]) / max(1, min(10, len(impacts)))
    depth = "deep" if iavg < 0.05 else ("okay" if iavg < 0.25 else "thin")
    fees = "quiet" if impact < 0.05 and iavg < 0.1 else ("mild" if impact < 0.3 else "bot_war")
    if rm >= 0.35:
        move = "pumping"
    elif rm >= 0.12:
        move = "lifting"
    elif rm <= -0.35:
        move = "dumping"
    elif rm <= -0.12:
        move = "fading"
    elif abs(rs) >= 0.15 and abs(rm) < 0.12:
        move = "whipping"
    else:
        move = "flat"
    volw = "violent" if vol >= 0.25 else ("jumpy" if vol >= 0.10 else "calm")
    hour = brt_now().hour
    tod = "early" if 5 <= hour < 11 else ("mid" if 11 <= hour < 17 else ("late" if 17 <= hour < 22 else "night"))
    color = "green" if rl >= 0.2 else ("red" if rl <= -0.2 else "gray")
    rng = "tight" if pos >= 0.75 else "wide"
    tex = "harsh" if abs(rs) > abs(rm) * 1.5 and abs(rs) > 0.08 else "soft"
    phase = "early" if tod == "early" else ("late" if tod in ("late", "night") else "mid")
    loud = "loud" if vol >= 0.2 or fees == "bot_war" else "quiet"
    posw = position if position in ("held", "flat", "sold", "bare") else "flat"
    moodw = "".join(c for c in (mood or "neutral") if c.isalpha()) or "neutral"
    if moodw not in ("neutral", "flat"):
        tex = moodw
    words = [depth, fees, move, volw, tod, color, rng, tex, phase, "mid", loud, posw]
    state = " ".join(words)
    if any(ch.isdigit() for ch in state):
        state = " ".join("".join(c for c in state if not c.isdigit()).split())
    return {
        "state": state,
        "features": {
            "ret_s": round(rs, 4),
            "ret_m": round(rm, 4),
            "ret_l": round(rl, 4),
            "vol": round(vol, 4),
            "pos": round(pos, 4),
            "impact": round(impact, 6),
            "price": round(p0, 8),
            "n": len(prices),
        },
    }


def _peak(probs: dict) -> float:
    if not probs:
        return 0.0
    v = sorted((float(x) for x in probs.values()), reverse=True)
    return v[0] if len(v) == 1 else max(0.0, v[0] - v[1])


def von_system_one(base_url: str, state: str, criteria: dict, timeout: float = 30.0) -> dict:
    questions = {
        "action": {
            "type": "choice",
            "instructions": criteria["action"]["instructions"],
            "criteria": criteria["action"]["criteria"],
        },
        "skip_this_cycle": {
            "type": "noul",
            "instructions": criteria["skip_this_cycle"]["instructions"],
        },
    }
    t0 = time.perf_counter()
    code, raw = http_post_json(
        base_url.rstrip("/") + "/v1/systemone",
        {"state": state, "questions": questions},
        timeout=timeout,
    )
    lat = (time.perf_counter() - t0) * 1000
    if code != 200 or not isinstance(raw, dict):
        return {
            "ok": False,
            "error": f"http_{code}:{raw}",
            "chosen_action": "hold",
            "probabilities": {"buy": 0.0, "sell": 0.0, "hold": 1.0},
            "confidence": 0.0,
            "skip_noul": 1.0,
            "latency_ms": round(lat, 2),
            "fail_closed": True,
        }
    answers = raw.get("answers") or (raw if "action" in raw else {})
    action = answers.get("action") or {}
    skip = answers.get("skip_this_cycle") or {}
    probs = {k: float(v) for k, v in (action.get("probabilities") or action.get("probs") or {}).items()}
    choice = action.get("choice") or action.get("value") or "hold"
    conf = action.get("confidence")
    try:
        conf = float(conf) if conf is not None else _peak(probs)
    except Exception:
        conf = _peak(probs)
    skip_noul = 0.0
    if isinstance(skip, dict):
        for k in ("noul", "prob", "value"):
            if k in skip and skip[k] is not None and not isinstance(skip[k], bool):
                try:
                    skip_noul = float(skip[k])
                    break
                except Exception:
                    pass
    return {
        "ok": True,
        "error": None,
        "chosen_action": str(choice),
        "probabilities": probs,
        "confidence": float(conf),
        "skip_noul": float(skip_noul),
        "latency_ms": round(lat, 2),
        "fail_closed": False,
        "raw": raw,
    }


def apply_gates(chosen, conf, skip, pdata, gcfg, price_mark=None):
    now = time.time()
    reasons = []
    final = chosen
    if chosen not in ("buy", "sell", "hold"):
        final = "hold"
        reasons.append("invalid")
    if conf < float(gcfg["min_confidence"]):
        final = "hold"
        reasons.append("low_confidence")
    if skip >= float(gcfg["max_skip_noul"]):
        final = "hold"
        reasons.append("skip_noul_high")
    last = pdata.get("last_trade_ts")
    if final in ("buy", "sell") and last is not None and now - float(last) < float(gcfg["cooldown_seconds"]):
        final = "hold"
        reasons.append("cooldown")
    if final in ("buy", "sell"):
        stamps = [float(t) for t in pdata.get("trade_timestamps") or []]
        if len([t for t in stamps if t >= now - 3600]) >= int(gcfg["max_trades_per_hour"]):
            final = "hold"
            reasons.append("max_trades_hour")
    usdt = float(pdata.get("usdt", 0))
    mode = pdata.get("asset_mode", "sol")
    if final == "buy":
        need = float(gcfg["min_usdt_trade"])
        frac = float(gcfg["buy_fraction_usdt"])
        if usdt * frac < need or usdt < need:
            final = "hold"
            reasons.append("insufficient_usdt")
    if final == "sell":
        if mode == "token":
            tok = float(pdata.get("token") or 0)
            if tok <= 0 or tok * float(price_mark or 0) < float(gcfg["min_usdt_trade"]):
                final = "hold"
                reasons.append("insufficient_token")
        else:
            if float(pdata.get("sol", 0)) < float(gcfg["min_sol_trade"]):
                final = "hold"
                reasons.append("insufficient_sol")
    return {
        "final_action": final,
        "gate_reasons": reasons,
        "blocked_trade": chosen in ("buy", "sell") and final == "hold",
    }


def jupiter_quote(cfg, input_mint, output_mint, amount_in, in_decimals, slippage_bps=50):
    global _JUP_LOCK, _JUP_LAST
    raw = int(round(amount_in * (10 ** in_decimals)))
    if raw <= 0:
        raise ValueError("amount_too_small")
    url = cfg["market"]["jupiter_quote_url"] + "?" + urllib.parse.urlencode(
        {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(raw),
            "slippageBps": str(slippage_bps),
        }
    )
    last = None
    for attempt in range(6):
        if time.time() < _JUP_LOCK:
            time.sleep(min(30, _JUP_LOCK - time.time()))
        if time.time() - _JUP_LAST < float(cfg["market"].get("jupiter_min_interval_seconds", 20)):
            time.sleep(1)
        code, body = http_get(url)
        if code == 429:
            _JUP_LOCK = time.time() + 60 * (attempt + 1)
            last = "429"
            time.sleep(min(45, 5 * (attempt + 1)))
            continue
        if code != 200:
            last = f"http_{code}"
            time.sleep(2)
            continue
        _JUP_LAST = time.time()
        return json.loads(body.decode())
    raise RuntimeError(f"quote_failed_{last}")


def fetch_sol_price(cfg, history_path: Path) -> dict:
    global _JUP_LOCK, _JUP_LAST
    errors = []
    result = None
    prefer_cb = time.time() < _JUP_LOCK or cfg["market"].get("prefer_secondary_on_429", True)

    def coinbase():
        c, b = http_get("https://api.coinbase.com/v2/prices/SOL-USD/spot")
        if c != 200:
            raise RuntimeError(f"cb_{c}")
        return {
            "price_usd": float(json.loads(b.decode())["data"]["amount"]),
            "price_impact_pct": 0.0,
            "source": "coinbase",
        }

    def jupiter():
        global _JUP_LOCK, _JUP_LAST
        if time.time() < _JUP_LOCK:
            raise RuntimeError("jup_lock")
        if time.time() - _JUP_LAST < float(cfg["market"].get("jupiter_min_interval_seconds", 20)):
            raise RuntimeError("jup_interval")
        amt = int(cfg["market"]["quote_usdt_amount"])
        url = cfg["market"]["jupiter_quote_url"] + "?" + urllib.parse.urlencode(
            {
                "inputMint": USDT,
                "outputMint": SOL,
                "amount": str(amt),
                "slippageBps": str(cfg["market"].get("slippage_bps", 50)),
            }
        )
        c, b = http_get(url)
        if c == 429:
            _JUP_LOCK = time.time() + 90
            raise RuntimeError("jup_429")
        if c != 200:
            raise RuntimeError(f"jup_{c}")
        d = json.loads(b.decode())
        inn = float(d["inAmount"]) / 1e6
        out = float(d["outAmount"]) / 1e9
        if out <= 0:
            raise RuntimeError("jup_zero")
        _JUP_LAST = time.time()
        return {
            "price_usd": inn / out,
            "price_impact_pct": float(d.get("priceImpactPct") or 0),
            "source": "jupiter_quote",
        }

    order = [coinbase, jupiter] if prefer_cb else [jupiter, coinbase]
    for fn in order:
        try:
            result = fn()
            break
        except Exception as e:
            errors.append(str(e))
    if result is None:
        hist = read_jsonl(history_path)
        if not hist:
            raise RuntimeError(";".join(errors))
        result = {
            "price_usd": float(hist[-1]["price_usd"]),
            "price_impact_pct": float(hist[-1].get("price_impact_pct") or 0),
            "source": "stale",
            "stale": True,
        }
    row = {
        "ts": time.time(),
        "ts_brt": brt_iso(),
        "price_usd": float(result["price_usd"]),
        "price_impact_pct": float(result.get("price_impact_pct") or 0),
        "source": result["source"],
        "stale": bool(result.get("stale")),
        "errors": errors,
    }
    append_jsonl(history_path, row)
    return row


def fetch_meme_prices(tokens: list[dict], last: dict[str, float], history_dir: Path) -> dict[str, dict]:
    ids = ",".join(sorted({t["coingecko_id"] for t in tokens}))
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    c, b = http_get(url, timeout=20)
    out: dict[str, dict] = {}
    if c != 200:
        for t in tokens:
            sym = t["symbol"]
            if sym in last:
                out[sym] = {"price_usd": last[sym], "source": f"stale_{c}", "stale": True}
        return out
    data = json.loads(b.decode())
    ts = time.time()
    history_dir.mkdir(parents=True, exist_ok=True)
    for t in tokens:
        sym = t["symbol"]
        info = data.get(t["coingecko_id"]) or {}
        if "usd" not in info:
            if sym in last:
                out[sym] = {"price_usd": last[sym], "source": "stale_missing", "stale": True}
            continue
        px = float(info["usd"])
        row = {"ts": ts, "ts_brt": brt_iso(ts), "symbol": sym, "price_usd": px, "source": "coingecko"}
        append_jsonl(history_dir / f"{sym}.jsonl", row)
        last[sym] = px
        out[sym] = row
    return out
