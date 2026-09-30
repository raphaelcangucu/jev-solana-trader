"""Shared cross-process quote layer (paper only; quotes are read-only HTTP GETs, never swaps).

Provider chain: Jupiter lite-api -> Jupiter api.jup.ag (keyless public) -> Raydium compute API.
- Shared per-host rate limiter + 429 backoff across ALL bot processes (fcntl lock on data/jup/limiter.json).
- Short quote cache (same pair, similar size, <= cache_seconds) scaled linearly -> fill_mode "<src>_cached".
- Every attempt logged to logs/quote_events.jsonl (outcome, host, http code, wait) for fill-quality stats.
Callers keep their mark fallback when this raises; the raised message carries the reason chain.
"""
from __future__ import annotations
import fcntl, json, os, random, sys, time, urllib.parse, urllib.request, urllib.error
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/home/box/solana-trader/paper")
DIR = ROOT / "data" / "jup"
STATE = DIR / "limiter.json"
LOCK = DIR / "limiter.lock"
EVENTS = ROOT / "logs" / "quote_events.jsonl"
BRT = timezone(timedelta(hours=-3))

DEFAULTS = {
    "quote_providers": ["jup_lite", "jup_public", "raydium"],
    "quote_min_interval_seconds": 1.2,     # shared per-host spacing across processes
    "quote_backoff_base_seconds": 30,       # 429 -> lock host for base*2^fails (capped)
    "quote_backoff_base_by_provider": {"jup_lite": 60, "jup_public": 2, "raydium": 5},
    "quote_rounds": 2,
    "quote_backoff_max_seconds": 600,
    "quote_cache_seconds": 20,
    "quote_cache_size_band": [0.5, 2.0],
    "quote_max_wait_seconds": 8,
}
URLS = {
    "jup_lite": "https://lite-api.jup.ag/swap/v1/quote",
    "jup_public": "https://api.jup.ag/swap/v1/quote",
    "raydium": "https://transaction-v1.raydium.io/compute/swap-base-in",
}

def _proc():
    return Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "proc"

@contextmanager
def _locked():
    DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "a+") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            st = json.loads(STATE.read_text()) if STATE.exists() else {}
        except Exception:
            st = {}
        st.setdefault("hosts", {}); st.setdefault("cache", {})
        box = {"st": st}
        try:
            yield box
        finally:
            tmp = STATE.with_suffix(".tmp"); tmp.write_text(json.dumps(box["st"])); tmp.replace(STATE)
            fcntl.flock(lf, fcntl.LOCK_UN)

def _log(row):
    try:
        row = {"ts": time.time(), "ts_brt": datetime.now(tz=BRT).isoformat(), "pid": os.getpid(), "proc": _proc(), **row}
        EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS, "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass

def _get(url, timeout=10.0):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-bot/0.2", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.read() if hasattr(e, "read") else b"")
    except Exception as e:
        return 0, str(e).encode()

def _reserve(host, m):
    """Reserve a slot for host. Returns (ok, wait_s, reason)."""
    now = time.time()
    with _locked() as box:
        h = box["st"]["hosts"].setdefault(host, {"last": 0, "lock_until": 0, "fails": 0})
        if now < h["lock_until"]:
            return False, h["lock_until"] - now, "host_backoff"
        nxt = h["last"] + float(m["quote_min_interval_seconds"])
        if now < nxt:
            return False, nxt - now, "spacing"
        h["last"] = now
        return True, 0.0, "ok"

def _mark(host, m, code):
    with _locked() as box:
        h = box["st"]["hosts"].setdefault(host, {"last": 0, "lock_until": 0, "fails": 0})
        if code == 200:
            h["fails"] = 0; h["lock_until"] = 0
        elif code == 429:
            h["fails"] = int(h.get("fails", 0)) + 1
            base = float((m.get("quote_backoff_base_by_provider") or {}).get(host, m["quote_backoff_base_seconds"]))
            back = min(float(m["quote_backoff_max_seconds"]), base * 2 ** (h["fails"] - 1))
            h["lock_until"] = time.time() + back * (0.9 + 0.2 * random.random())

def _cache_put(key, q, src):
    with _locked() as box:
        box["st"]["cache"][key] = {"ts": time.time(), "in": q["inAmount"], "out": q["outAmount"], "src": src,
                                   "impact": q.get("priceImpactPct")}

def _cache_get(key, raw, m):
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    c = (st.get("cache") or {}).get(key)
    if not c:
        return None
    age = time.time() - float(c["ts"])
    lo, hi = m["quote_cache_size_band"]
    ratio = raw / max(1.0, float(c["in"]))
    if age > float(m["quote_cache_seconds"]) or not (lo <= ratio <= hi):
        return None
    out = int(float(c["out"]) * ratio)
    return {"inAmount": str(raw), "outAmount": str(out), "priceImpactPct": c.get("impact"),
            "routePlan": [{"swapInfo": {"label": f"cache:{c['src']}"}}], "_fill_mode": f"{c['src']}_cached",
            "_quote_source": c["src"], "_cache_age_s": round(age, 2)}

def _call(provider, in_mint, out_mint, raw, slip):
    qs = {"inputMint": in_mint, "outputMint": out_mint, "amount": str(raw), "slippageBps": str(slip)}
    if provider == "raydium":
        qs["txVersion"] = "V0"
    url = URLS[provider] + "?" + urllib.parse.urlencode(qs)
    t = time.time(); code, body = _get(url)
    lat = (time.time() - t) * 1000
    if code != 200:
        return code, None, lat, body[:120].decode(errors="replace")
    d = json.loads(body.decode())
    if provider == "raydium":
        if not d.get("success"):
            return 422, None, lat, str(d.get("msg"))[:120]
        x = d["data"]
        q = {"inAmount": x["inputAmount"], "outAmount": x["outputAmount"], "priceImpactPct": x.get("priceImpactPct"),
             "routePlan": [{"swapInfo": {"label": "Raydium"}} for _ in (x.get("routePlan") or [1])]}
    else:
        if "outAmount" not in d:
            return 422, None, lat, str(d)[:120]
        q = d
    return 200, q, lat, None

def get_quote(market: dict, in_mint, out_mint, amount_in, in_decimals, slippage_bps=50):
    m = dict(DEFAULTS); m.update({k: v for k, v in (market or {}).items() if k.startswith("quote_")})
    raw = int(round(amount_in * (10 ** in_decimals)))
    if raw <= 0:
        raise ValueError("amount_too_small")
    key = f"{in_mint}>{out_mint}"
    reasons = []
    deadline = time.time() + float(m["quote_max_wait_seconds"])
    order = [p for _ in range(int(m.get("quote_rounds", 1))) for p in m["quote_providers"]]
    for i, provider in enumerate(order):
        host = provider
        if i >= len(m["quote_providers"]):
            if time.time() >= deadline:
                break
            with _locked() as box:
                h = box["st"]["hosts"].get(host) or {}
            wait_lock = float(h.get("lock_until", 0)) - time.time()
            if 0 < wait_lock and time.time() + wait_lock <= deadline:
                time.sleep(wait_lock + 0.05)
        while True:
            ok, wait, why = _reserve(host, m)
            if ok:
                break
            if why == "spacing" and time.time() + wait <= deadline:
                time.sleep(wait + 0.05); continue
            break
        if not ok:
            reasons.append(f"{provider}:{why}")
            _log({"provider": provider, "pair": key, "outcome": why, "http": None})
            continue
        code, q, lat, err = _call(provider, in_mint, out_mint, raw, slippage_bps)
        _mark(host, m, code)
        _log({"provider": provider, "pair": key, "outcome": "ok" if code == 200 else "fail", "http": code,
              "latency_ms": round(lat, 1), "err": err})
        if code == 200 and q:
            src = "jupiter_quote" if provider.startswith("jup") else f"{provider}_quote"
            q = dict(q); q["_fill_mode"] = src; q["_quote_source"] = provider
            try:
                _cache_put(key, q, src)
            except Exception:
                pass
            return q
        reasons.append(f"{provider}:http_{code}")
    c = _cache_get(key, raw, m)
    if c:
        _log({"provider": "cache", "pair": key, "outcome": "cached", "http": None, "age_s": c["_cache_age_s"]})
        return c
    _log({"provider": "all", "pair": key, "outcome": "fallback_mark", "http": None, "reasons": reasons})
    raise RuntimeError("quote_failed:" + ",".join(reasons))
