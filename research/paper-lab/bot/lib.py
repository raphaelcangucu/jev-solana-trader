
"""Paper trading shared library. Simulation only — never signs or sends."""
from __future__ import annotations
import json, math, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path("/home/box/solana-trader/paper")
BRT = timezone(timedelta(hours=-3))
USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOL = "So11111111111111111111111111111111111111112"
_JUP_LOCK = 0.0
_JUP_LAST = 0.0

def brt_now():
    return datetime.now(tz=BRT)

def brt_iso(ts=None):
    return datetime.fromtimestamp(ts or time.time(), tz=BRT).isoformat()

def load_cfg():
    return json.loads((ROOT / "config.json").read_text())

def assert_no_keys(cfg):
    for p in cfg.get("forbid_keypair_paths", []):
        pass  # never open

def write_json(path: Path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp"); tmp.write_text(json.dumps(obj, indent=2)); tmp.replace(path)

def append_jsonl(path: Path, row):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f: f.write(json.dumps(row) + "\n")

def read_jsonl(path: Path):
    path = Path(path)
    if not path.exists(): return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try: out.append(json.loads(line))
            except Exception: pass
    return out

def http_get(url, timeout=15.0):
    req = urllib.request.Request(url, headers={"User-Agent":"paper-bot/0.1"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e,"read") else b""
    except Exception as e:
        return 0, str(e).encode()

def http_post_json(url, payload, timeout=30.0):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json","Accept":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e,"read") else b""
        try: return e.code, json.loads(body.decode())
        except Exception: return e.code, {"error": body.decode(errors="replace")[:300]}
    except Exception as e:
        return 0, {"error": str(e)}

def build_state(history, position, mood):
    prices = [float(h["price_usd"]) for h in history if h.get("price_usd") is not None]
    impacts = [float(h.get("price_impact_pct") or 0) for h in history]
    if len(prices) < 2:
        words = ["deep","quiet","flat","calm","early","gray","wide","soft","early","mid","quiet", position or "flat"]
        return {"state":" ".join(words), "features":{"insufficient":True}}
    def pct(a,b): return 0.0 if b==0 else (a-b)/b*100
    p0=prices[-1]; ps=prices[-min(4,len(prices))]; pm=prices[-min(20,len(prices))]; pl=prices[-min(80,len(prices))]
    rs,rm,rl = pct(p0,ps), pct(p0,pm), pct(p0,pl)
    win=prices[-min(20,len(prices)):]
    rets=[pct(win[i],win[i-1]) for i in range(1,len(win))]
    vol = 0.0
    if len(rets)>=2:
        m=sum(rets)/len(rets); vol=math.sqrt(sum((r-m)**2 for r in rets)/len(rets))
    lo,hi=min(win),max(win); pos=(p0-lo)/(hi-lo) if hi>lo else 0.5
    impact=impacts[-1] if impacts else 0.0
    iavg=sum(impacts[-min(10,len(impacts)):])/max(1,min(10,len(impacts)))
    depth="deep" if iavg<0.05 else ("okay" if iavg<0.25 else "thin")
    fees="quiet" if impact<0.05 and iavg<0.1 else ("mild" if impact<0.3 else "bot_war")
    move = ("pumping" if rm>=0.35 else "lifting" if rm>=0.12 else "dumping" if rm<=-0.35 else "fading" if rm<=-0.12 else "whipping" if abs(rs)>=0.15 and abs(rm)<0.12 else "flat")
    volw="violent" if vol>=0.25 else ("jumpy" if vol>=0.10 else "calm")
    hour=brt_now().hour
    tod="early" if 5<=hour<11 else ("mid" if 11<=hour<17 else ("late" if 17<=hour<22 else "night"))
    color="green" if rl>=0.2 else ("red" if rl<=-0.2 else "gray")
    rng="tight" if pos>=0.75 else "wide"
    tex="harsh" if abs(rs)>abs(rm)*1.5 and abs(rs)>0.08 else "soft"
    phase="early" if tod=="early" else ("late" if tod in ("late","night") else "mid")
    loud="loud" if vol>=0.2 or fees=="bot_war" else "quiet"
    posw=position if position in ("held","flat","sold","bare") else "flat"
    moodw="".join(c for c in (mood or "neutral") if c.isalpha()) or "neutral"
    if moodw not in ("neutral","flat"): tex=moodw
    words=[depth,fees,move,volw,tod,color,rng,tex,phase,"mid",loud,posw]
    state=" ".join(words)
    if any(ch.isdigit() for ch in state):
        state=" ".join("".join(c for c in state if not c.isdigit()).split())
    return {"state":state,"features":{"ret_s":round(rs,4),"ret_m":round(rm,4),"ret_l":round(rl,4),"vol":round(vol,4),"pos":round(pos,4),"impact":round(impact,6),"price":round(p0,8),"n":len(prices)}}

def _peak(probs):
    if not probs: return 0.0
    v=sorted((float(x) for x in probs.values()), reverse=True)
    return v[0] if len(v)==1 else max(0.0, v[0]-v[1])

def von_system_one(base_url, state, criteria, timeout=30.0):
    questions = {
        "action": {"type":"choice","instructions":criteria["action"]["instructions"],"criteria":criteria["action"]["criteria"]},
        "skip_this_cycle": {"type":"noul","instructions":criteria["skip_this_cycle"]["instructions"]},
    }
    t0=time.perf_counter()
    code, raw = http_post_json(base_url.rstrip("/")+"/v1/systemone", {"state":state,"questions":questions}, timeout=timeout)
    lat=(time.perf_counter()-t0)*1000
    if code!=200 or not isinstance(raw, dict):
        return {"ok":False,"error":f"http_{code}:{raw}","chosen_action":"hold","probabilities":{"buy":0,"sell":0,"hold":1},"confidence":0.0,"skip_noul":1.0,"latency_ms":round(lat,2),"fail_closed":True}
    answers = raw.get("answers") or (raw if "action" in raw else {})
    action = answers.get("action") or {}
    skip = answers.get("skip_this_cycle") or {}
    probs = {k:float(v) for k,v in (action.get("probabilities") or action.get("probs") or {}).items()}
    choice = action.get("choice") or action.get("value") or "hold"
    conf = action.get("confidence")
    try: conf=float(conf) if conf is not None else _peak(probs)
    except Exception: conf=_peak(probs)
    skip_noul=0.0
    if isinstance(skip, dict):
        for k in ("noul","prob","value"):
            if k in skip and skip[k] is not None and not isinstance(skip[k], bool):
                try: skip_noul=float(skip[k]); break
                except Exception: pass
    return {"ok":True,"error":None,"chosen_action":str(choice),"probabilities":probs,"confidence":float(conf),"skip_noul":float(skip_noul),"latency_ms":round(lat,2),"fail_closed":False,"raw":raw}


def apply_gates(chosen, conf, skip, pdata, gcfg, price_mark=None, probabilities=None, profile="baseline"):
    """Fail-closed gates. profile=baseline|relaxed."""
    now = time.time()
    reasons = []
    final = chosen
    if chosen not in ("buy", "sell", "hold"):
        final = "hold"; reasons.append("invalid")

    min_conf = float(gcfg["min_confidence"])
    if conf < min_conf:
        final = "hold"; reasons.append("low_confidence")

    if profile == "relaxed":
        margin_need = float(gcfg.get("min_prob_margin", 0.0))
        probs = probabilities or {}
        if probs and margin_need > 0:
            vals = sorted((float(v) for v in probs.values()), reverse=True)
            margin = vals[0] - (vals[1] if len(vals) > 1 else 0.0)
            if margin < margin_need:
                final = "hold"; reasons.append("low_prob_margin")

    if skip >= float(gcfg["max_skip_noul"]):
        final = "hold"; reasons.append("skip_noul_high")

    last = pdata.get("last_trade_ts")
    if final in ("buy", "sell") and last is not None and now - float(last) < float(gcfg["cooldown_seconds"]):
        final = "hold"; reasons.append("cooldown")

    if final in ("buy", "sell"):
        stamps = [float(t) for t in pdata.get("trade_timestamps") or []]
        if len([t for t in stamps if t >= now - 3600]) >= int(gcfg["max_trades_per_hour"]):
            final = "hold"; reasons.append("max_trades_hour")

    usdt = float(pdata.get("usdt", 0))
    mode = pdata.get("asset_mode", "sol")
    if final == "buy":
        need = float(gcfg["min_usdt_trade"]); frac = float(gcfg["buy_fraction_usdt"])
        if usdt * frac < need or usdt < need:
            final = "hold"; reasons.append("insufficient_usdt")
    if final == "sell":
        if mode == "token":
            tok = float(pdata.get("token") or 0)
            if tok <= 0 or tok * float(price_mark or 0) < float(gcfg["min_usdt_trade"]):
                final = "hold"; reasons.append("insufficient_token")
        else:
            if float(pdata.get("sol", 0)) < float(gcfg["min_sol_trade"]):
                final = "hold"; reasons.append("insufficient_sol")

    return {
        "final_action": final,
        "gate_reasons": reasons,
        "blocked_trade": chosen in ("buy", "sell") and final == "hold",
        "profile": profile,
    }


def jupiter_quote(cfg, input_mint, output_mint, amount_in, in_decimals, slippage_bps=50):
    """Shared cross-process quote (see bot/quotes.py): limiter + backoff + provider chain + cache.
    Returned dict carries _fill_mode (jupiter_quote | raydium_quote | *_cached). Raises on failure
    (callers fall back to live mark and log quote_error with the reason chain)."""
    from bot.quotes import get_quote
    return get_quote(cfg.get("market") or {}, input_mint, output_mint, amount_in, in_decimals, slippage_bps)


def _fresh_enough(row, max_age):
    if not row:
        return False
    return (time.time() - float(row.get("ts") or 0)) <= float(max_age)


def fetch_sol_price(cfg, history_path: Path):
    """Real SOL marks only: Coinbase primary, Coinpaprika secondary, Jupiter tertiary.
    Never fabricate. Stale reuse only if last real mark age <= max_price_age_seconds.
    """
    global _JUP_LOCK, _JUP_LAST
    max_age = float(cfg["market"].get("max_price_age_seconds", 120))
    errors = []
    result = None

    def coinbase():
        c, b = http_get("https://api.coinbase.com/v2/prices/SOL-USD/spot", timeout=10)
        if c != 200:
            raise RuntimeError(f"cb_{c}")
        return {"price_usd": float(json.loads(b.decode())["data"]["amount"]), "price_impact_pct": 0.0, "source": "coinbase"}

    def coinpaprika():
        c, b = http_get("https://api.coinpaprika.com/v1/tickers/sol-solana", timeout=10)
        if c != 200:
            raise RuntimeError(f"paprika_{c}")
        d = json.loads(b.decode())
        return {"price_usd": float(d["quotes"]["USD"]["price"]), "price_impact_pct": 0.0, "source": "coinpaprika"}

    def jupiter():
        global _JUP_LOCK, _JUP_LAST
        if time.time() < _JUP_LOCK:
            raise RuntimeError("jup_lock")
        if time.time() - _JUP_LAST < float(cfg["market"].get("jupiter_min_interval_seconds", 20)):
            raise RuntimeError("jup_interval")
        amt = int(cfg["market"]["quote_usdt_amount"])
        url = cfg["market"]["jupiter_quote_url"] + "?" + urllib.parse.urlencode({
            "inputMint": USDT, "outputMint": SOL, "amount": str(amt),
            "slippageBps": str(cfg["market"].get("slippage_bps", 50)),
        })
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
        return {"price_usd": inn / out, "price_impact_pct": float(d.get("priceImpactPct") or 0), "source": "jupiter_quote"}

    for fn in (coinbase, coinpaprika, jupiter):
        try:
            result = fn()
            break
        except Exception as e:
            errors.append(f"{fn.__name__}:{e}")

    if result is None:
        hist = read_jsonl(history_path)
        if hist and _fresh_enough(hist[-1], max_age) and not hist[-1].get("fabricated"):
            result = {
                "price_usd": float(hist[-1]["price_usd"]),
                "price_impact_pct": float(hist[-1].get("price_impact_pct") or 0),
                "source": f"cached_{hist[-1].get('source','unknown')}",
                "stale": True,
            }
        else:
            raise RuntimeError("no_fresh_sol_price:" + ";".join(errors))

    row = {
        "ts": time.time(), "ts_brt": brt_iso(),
        "price_usd": float(result["price_usd"]),
        "price_impact_pct": float(result.get("price_impact_pct") or 0),
        "source": result["source"], "stale": bool(result.get("stale")),
        "errors": errors, "fabricated": False,
    }
    append_jsonl(history_path, row)
    return row


def _gate_io_price(pair: str):
    url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
    c, b = http_get(url, timeout=10)
    if c != 200:
        raise RuntimeError(f"gate_{c}")
    data = json.loads(b.decode())
    if not isinstance(data, list) or not data:
        raise RuntimeError("gate_empty")
    return float(data[0]["last"]), "gate.io"


def _coinpaprika_price(ticker_id: str):
    url = f"https://api.coinpaprika.com/v1/tickers/{ticker_id}"
    c, b = http_get(url, timeout=10)
    if c != 200:
        raise RuntimeError(f"paprika_{c}")
    d = json.loads(b.decode())
    return float(d["quotes"]["USD"]["price"]), "coinpaprika"


def _dexscreener_price(mint: str):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
    c, b = http_get(url, timeout=10)
    if c != 200:
        raise RuntimeError(f"dex_{c}")
    pairs = [p for p in (json.loads(b.decode()).get("pairs") or []) if p.get("chainId") == "solana"]
    if not pairs:
        raise RuntimeError("dex_no_pairs")
    pairs.sort(key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0), reverse=True)
    px = float(pairs[0]["priceUsd"])
    if px <= 0:
        raise RuntimeError("dex_zero")
    return px, "dexscreener"


def _jupiter_token_price(cfg, mint: str, decimals: int):
    # 1 USDT -> token quote
    q = jupiter_quote(cfg, USDT, mint, 1.0, 6, slippage_bps=100)
    out = float(q["outAmount"]) / (10 ** int(decimals))
    if out <= 0:
        raise RuntimeError("jup_zero")
    return 1.0 / out, "jupiter_quote"


def fetch_meme_price(cfg, token: dict, history_dir: Path, max_age: float = 120.0):
    """Fetch ONE token mark from live sources only. No seeds/fabrications.
    Returns row dict or None if no fresh real price.
    """
    history_dir = Path(history_dir)
    history_dir.mkdir(parents=True, exist_ok=True)
    sym = token["symbol"]
    errors = []
    result = None
    # Prefer CEX marks (stable for liquid memes), then DexScreener, then Jupiter quote
    attempts = []
    if token.get("gate_pair"):
        attempts.append(("gate", lambda: _gate_io_price(token["gate_pair"])))
    if token.get("coinpaprika_id"):
        attempts.append(("paprika", lambda: _coinpaprika_price(token["coinpaprika_id"])))
    attempts.append(("dex", lambda: _dexscreener_price(token["mint"])))
    attempts.append(("jup", lambda: _jupiter_token_price(cfg, token["mint"], int(token["decimals"]))))

    for name, fn in attempts:
        try:
            px, src = fn()
            if px and px > 0:
                result = {"price_usd": float(px), "source": src}
                break
        except Exception as e:
            errors.append(f"{name}:{e}")

    if result is None:
        # Allow briefly-cached REAL mark only
        hist = read_jsonl(history_dir / f"{sym}.jsonl")
        if hist and _fresh_enough(hist[-1], max_age) and not hist[-1].get("fabricated") and hist[-1].get("source") not in (None, "seed", "last_or_seed"):
            result = {
                "price_usd": float(hist[-1]["price_usd"]),
                "source": f"cached_{hist[-1].get('source')}",
                "stale": True,
            }
        else:
            return None

    row = {
        "ts": time.time(), "ts_brt": brt_iso(), "symbol": sym, "mint": token["mint"],
        "price_usd": float(result["price_usd"]), "source": result["source"],
        "stale": bool(result.get("stale")), "errors": errors, "fabricated": False,
    }
    append_jsonl(history_dir / f"{sym}.jsonl", row)
    return row


def fetch_meme_prices(cfg, tokens, history_dir: Path, max_age: float = 120.0):
    """Live multi-source marks for all tokens. Missing tokens omitted (caller skips)."""
    out = {}
    for t in tokens:
        row = fetch_meme_price(cfg, t, history_dir, max_age=max_age)
        if row is not None:
            out[t["symbol"]] = row
        time.sleep(0.35)  # be gentle across CEX APIs
    return out
