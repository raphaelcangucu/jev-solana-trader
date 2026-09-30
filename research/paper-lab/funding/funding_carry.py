#!/usr/bin/env python3
"""
Paper funding-carry service (Hyperliquid perp short + spot long hedge).
PAPER ONLY: no accounts, no orders, no keys. Only public read endpoints.
Stdlib only. State: data/state.json. Logs: logs/*.jsonl.
"""
import json, os, sys, time, math, random, signal, traceback, gzip, shutil
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"
for d in (DATA, LOGS, REPORTS):
    d.mkdir(exist_ok=True)

CFG = json.load(open(ROOT / "config.json"))
HL = "https://api.hyperliquid.xyz/info"
GATE = "https://api.gateio.ws/api/v4"
HOUR_MS = 3600_000
YEAR_H = 24 * 365

STOP = False


def _sig(*_):
    global STOP
    STOP = True


signal.signal(signal.SIGTERM, _sig)
signal.signal(signal.SIGINT, _sig)


# ---------------------------------------------------------------- utils
def now_ms():
    return int(time.time() * 1000)


def iso(ms=None):
    ms = now_ms() if ms is None else ms
    return datetime.fromtimestamp(ms / 1000).astimezone().isoformat(timespec="seconds")


def log(msg):
    line = f"[{iso()}] {msg}"
    if sys.stdout.isatty():
        print(line, flush=True)
    with open(LOGS / "service.log", "a") as f:
        f.write(line + "\n")


def jl(name, obj):
    obj = {"ts": iso(), "ts_ms": now_ms(), **obj}
    with open(LOGS / f"{name}.jsonl", "a") as f:
        f.write(json.dumps(obj, separators=(",", ":")) + "\n")


def atomic_write(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def floor_dec(x, dec):
    q = 10 ** dec
    return math.floor(x * q + 1e-9) / q


# ---------------------------------------------------------------- http
class Http:
    def __init__(self, state):
        self.last_hl = 0.0
        self.state = state

    def _req(self, url, body=None, venue="other", timeout=30, tries=8):
        err = None
        for attempt in range(tries):
            if venue == "hl":
                wait = self.last_hl + CFG["hl_min_request_interval_s"] - time.time()
                if wait > 0:
                    time.sleep(wait)
                self.last_hl = time.time()
            try:
                data = json.dumps(body).encode() if body is not None else None
                r = urllib.request.Request(url, data=data, headers={
                    "Content-Type": "application/json",
                    "User-Agent": "funding-carry-paper/1 (research; read-only)"})
                with urllib.request.urlopen(r, timeout=timeout) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                err = e
                if e.code == 429 or e.code >= 500:
                    key = f"http_{e.code}_{venue}"
                    self.state["counters"][key] = self.state["counters"].get(key, 0) + 1
                    sl = min(180, 2 * (2 ** attempt)) + random.uniform(0, 2)
                    log(f"HTTP {e.code} {venue} {url[:80]} -> backoff {sl:.1f}s (try {attempt+1}/{tries})")
                    time.sleep(sl)
                    continue
                raise
            except Exception as e:  # network / json
                err = e
                sl = min(120, 2 * (2 ** attempt)) + random.uniform(0, 2)
                log(f"NET ERR {venue} {type(e).__name__}: {e} -> backoff {sl:.1f}s")
                time.sleep(sl)
        raise RuntimeError(f"request failed after {tries} tries: {url} ({err})")

    def hl(self, body):
        return self._req(HL, body, venue="hl")

    def get(self, url, venue="other"):
        return self._req(url, None, venue=venue)


# ---------------------------------------------------------------- service
class Service:
    def __init__(self):
        self.state_path = DATA / "state.json"
        self.cache_path = DATA / "funding_cache.json"
        if self.state_path.exists():
            self.state = json.load(open(self.state_path))
            log("state loaded (resume)")
        else:
            self.state = None
        self.http = Http(self.state if self.state else {"counters": {}})
        self.cache = json.load(open(self.cache_path)) if self.cache_path.exists() else {}
        self.markets = {}      # latest ctx per coin
        self.spot_px = {}      # coin -> {"mid","venue","symbol","bid","ask"}
        self.usdc_usdt = None
        self.perp_meta = {}    # coin -> {szDecimals,maxLeverage}
        self.spot_meta = {}    # coin -> {symbol:@N, szDecimals}
        self.gate_meta = {}    # coin -> {amount_precision, min_quote}
        self.last_poll = 0

    # ---- universe
    def all_coins(self):
        s = set()
        for p in CFG["portfolios"].values():
            s.update(p["universe"])
        return sorted(s)

    # ---- init
    def init_state(self):
        st = {
            "created_at": iso(), "created_ms": now_ms(),
            "started_at": None, "started_ms": None,
            "run_mode": "indefinite", "last_rotation_date": None,
            "counters": {}, "last_error": None,
            "oracle_snaps": {}, "last_snap_hour_ms": 0, "last_eval_hour_ms": 0,
            "last_bench_poll_ms": 0, "last_report_date": None,
            "benchmarks": {}, "oneoff_quotes": {}, "portfolios": {},
            "cooldown": {},
        }
        self.state = st
        self.http.state = st

    def save(self):
        atomic_write(self.state_path, self.state)
        atomic_write(self.cache_path, self.cache)

    def load_meta(self):
        meta, ctxs = self.http.hl({"type": "metaAndAssetCtxs"})
        for u in meta["universe"]:
            self.perp_meta[u["name"]] = {"szDecimals": u["szDecimals"], "maxLeverage": u.get("maxLeverage")}
        smeta = self.http.hl({"type": "spotMeta"})
        toks = {t["index"]: t for t in smeta["tokens"]}
        for coin, h in CFG["hedge"].items():
            if h["venue"] != "hl_spot":
                continue
            for u in smeta["universe"]:
                b, q = u["tokens"]
                if toks[b]["name"] == h["token"] and toks[q]["name"] == "USDC":
                    self.spot_meta[coin] = {"symbol": u["name"], "szDecimals": toks[b]["szDecimals"], "token": h["token"]}
            if coin not in self.spot_meta:
                raise RuntimeError(f"HL spot pair for {coin} ({h['token']}/USDC) not found")
        pairs = self.http.get(f"{GATE}/spot/currency_pairs", venue="gate")
        pm = {p["id"]: p for p in pairs}
        for coin, h in CFG["hedge"].items():
            if h["venue"] == "gate":
                p = pm[h["pair"]]
                self.gate_meta[coin] = {"pair": h["pair"], "amount_precision": int(p["amount_precision"]),
                                        "min_quote": float(p.get("min_quote_amount") or 0), "fee_pct": p.get("fee"),
                                        "status": p.get("trade_status")}
        log(f"meta loaded: spot={self.spot_meta} gate={ {k: v['pair'] for k, v in self.gate_meta.items()} }")

    # ---- market polling
    def poll_markets(self, tag="poll"):
        coins = self.all_coins()
        meta, ctxs = self.http.hl({"type": "metaAndAssetCtxs"})
        t_ms = now_ms()
        for u, c in zip(meta["universe"], ctxs):
            if u["name"] in coins:
                mark = float(c["markPx"]); oracle = float(c["oraclePx"])
                self.markets[u["name"]] = {
                    "mark": mark, "oracle": oracle, "funding": float(c["funding"]),
                    "premium": float(c["premium"]) if c.get("premium") is not None else None,
                    "oi_usd": float(c["openInterest"]) * mark, "day_vlm": float(c["dayNtlVlm"]),
                    "mid": float(c["midPx"]) if c.get("midPx") else None, "t_ms": t_ms}
                snaps = self.state["oracle_snaps"].setdefault(u["name"], [])
                snaps.append([t_ms, oracle, mark])
                cutoff = t_ms - 6 * HOUR_MS
                self.state["oracle_snaps"][u["name"]] = [s for s in snaps if s[0] >= cutoff]
        mids = self.http.hl({"type": "allMids"})
        for coin, sm in self.spot_meta.items():
            if sm["symbol"] in mids:
                self.spot_px[coin] = {"mid": float(mids[sm["symbol"]]), "venue": "hl_spot", "symbol": sm["symbol"]}
        u = self.http.get(f"{GATE}/spot/tickers?currency_pair=USDC_USDT", venue="gate")[0]
        self.usdc_usdt = (float(u["highest_bid"]) + float(u["lowest_ask"])) / 2
        for coin, gm in self.gate_meta.items():
            if coin not in coins:
                continue
            t = self.http.get(f"{GATE}/spot/tickers?currency_pair={gm['pair']}", venue="gate")[0]
            bid, ask = float(t["highest_bid"]), float(t["lowest_ask"])
            self.spot_px[coin] = {"mid": (bid + ask) / 2 / self.usdc_usdt, "venue": "gate", "symbol": gm["pair"],
                                  "bid_usdt": bid, "ask_usdt": ask}
        self.last_poll = time.time()
        jl("marks", {"tag": tag, "usdc_usdt_gate": self.usdc_usdt,
                     "perp": {k: {kk: v[kk] for kk in ("mark", "oracle", "funding", "premium", "oi_usd")} for k, v in self.markets.items()},
                     "spot": {k: {"mid_usdc": v["mid"], "venue": v["venue"], "symbol": v["symbol"]} for k, v in self.spot_px.items()}})

    # ---- books / fills (taker, walking real book)
    def book(self, coin, leg):
        """returns (bids, asks) as lists of (px_usdc, size_coin)"""
        if leg == "perp":
            b = self.http.hl({"type": "l2Book", "coin": coin})
            lv = b["levels"]
            return [(float(x["px"]), float(x["sz"])) for x in lv[0]], [(float(x["px"]), float(x["sz"])) for x in lv[1]], "hl_perp"
        h = CFG["hedge"][coin]
        if h["venue"] == "hl_spot":
            b = self.http.hl({"type": "l2Book", "coin": self.spot_meta[coin]["symbol"]})
            lv = b["levels"]
            return [(float(x["px"]), float(x["sz"])) for x in lv[0]], [(float(x["px"]), float(x["sz"])) for x in lv[1]], "hl_spot"
        ob = self.http.get(f"{GATE}/spot/order_book?currency_pair={h['pair']}&limit=50", venue="gate")
        conv = self.usdc_usdt or 1.0
        return ([(float(p) / conv, float(a)) for p, a in ob["bids"]],
                [(float(p) / conv, float(a)) for p, a in ob["asks"]], "gate")

    @staticmethod
    def walk(levels, size):
        rem, cost = size, 0.0
        for px, sz in levels:
            take = min(rem, sz)
            cost += take * px
            rem -= take
            if rem <= 1e-12:
                break
        if rem > 1e-12:
            return None
        return cost / size

    def fee_rates(self, coin, leg):
        f = CFG["fees"]
        if leg == "perp":
            return f["hl_perp_taker"], f["hl_perp_maker"]
        if CFG["hedge"][coin]["venue"] == "hl_spot":
            return f["hl_spot_taker"], f["hl_spot_maker"]
        return f["gate_spot_taker"], f["gate_spot_maker_cf"]

    def fill(self, pid, coin, leg, side, size, reason):
        bids, asks, venue = self.book(coin, leg)
        lv = asks if side == "buy" else bids
        px = self.walk(lv, size)
        if px is None:
            raise RuntimeError(f"book too thin for {coin} {leg} {side} {size}")
        notional = px * size
        tr, mr = self.fee_rates(coin, leg)
        fee = notional * tr
        rec = {"portfolio": pid, "coin": coin, "leg": leg, "venue": venue, "side": side, "size": size,
               "vwap_px_usdc": px, "best_bid": bids[0][0] if bids else None, "best_ask": asks[0][0] if asks else None,
               "notional": notional, "fee": fee, "fee_rate": tr, "fee_maker_cf": notional * mr, "liquidity": "taker",
               "reason": reason, "usdc_usdt_gate": self.usdc_usdt if venue == "gate" else None, "paper": True}
        jl("trades", rec)
        return px, fee, notional * mr

    # ---- funding cache
    def update_funding_cache(self, bootstrap=False):
        for coin in self.all_coins():
            arr = self.cache.get(coin, [])
            last = arr[-1][0] if arr else 0
            start = last + 1 if (last and not bootstrap) else now_ms() - 8 * 24 * HOUR_MS
            while True:
                pts = self.http.hl({"type": "fundingHistory", "coin": coin, "startTime": start})
                have = {a[0] for a in arr}
                for p in pts:
                    if p["time"] not in have:
                        arr.append([p["time"], float(p["fundingRate"]), float(p["premium"])])
                if len(pts) < 500:
                    break
                start = pts[-1]["time"] + 1
            arr.sort()
            cutoff = now_ms() - 10 * 24 * HOUR_MS
            self.cache[coin] = [a for a in arr if a[0] >= cutoff]

    def fstats(self, coin):
        arr = self.cache.get(coin, [])
        rates = [a[1] for a in arr]
        def mean_last(n):
            x = rates[-n:]
            return sum(x) / len(x) * YEAR_H if len(x) >= max(1, int(n * 0.8)) else None
        last24 = rates[-24:]
        flips = sum(1 for a, b in zip(last24, last24[1:]) if (a > 0) != (b > 0) and not (a == 0 or b == 0))
        m = self.markets.get(coin, {})
        return {"mean7d_ann": mean_last(168), "mean3d_ann": mean_last(72), "flips24h": flips,
                "current_ann": m.get("funding", 0) * YEAR_H if m else None, "oi_usd": m.get("oi_usd"),
                "n_hist": len(rates), "last_settled_ms": arr[-1][0] if arr else None}

    # ---- one-off quotes & benchmarks
    def lifi_quote(self, from_chain, to_chain, from_token, to_token, amount_units, from_addr, to_addr):
        q = urllib.parse.urlencode({"fromChain": from_chain, "toChain": to_chain, "fromToken": from_token,
                                    "toToken": to_token, "fromAmount": str(amount_units),
                                    "fromAddress": from_addr, "toAddress": to_addr})
        d = self.http.get(f"https://li.quest/v1/quote?{q}", venue="lifi")
        e = d["estimate"]
        gas = sum(float(g.get("amountUSD") or 0) for g in e.get("gasCosts", []))
        return {"tool": d.get("tool"), "fromAmount": e["fromAmount"], "toAmount": e["toAmount"],
                "toDecimals": d["action"]["toToken"]["decimals"], "fromDecimals": d["action"]["fromToken"]["decimals"],
                "gas_usd": gas, "fees": [(f.get("name"), f.get("amountUSD")) for f in e.get("feeCosts", [])], "fetched_at": iso()}

    def jup_quote(self, in_mint, out_mint, amount_units):
        url = f"https://lite-api.jup.ag/swap/v1/quote?inputMint={in_mint}&outputMint={out_mint}&amount={amount_units}&slippageBps=50"
        d = self.http._req(url, None, venue="jupiter", tries=2)
        return {"inAmount": d["inAmount"], "outAmount": d["outAmount"], "priceImpactPct": d.get("priceImpactPct"),
                "route": [r["swapInfo"].get("label") for r in d.get("routePlan", [])], "fetched_at": iso()}

    def fetch_oneoff(self):
        # Dummy public addresses: quotes only, no signing, no account.
        SOL_ADDR = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        EVM_ADDR = "0x0000000000000000000000000000000000000001"
        USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
        USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        JITO = "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn"
        out = {}
        for cap in sorted({p["capital"] for p in CFG["portfolios"].values()}):
            units = int(round(cap * 1e6))
            k = f"{cap:g}"
            r = {}
            try:
                q = self.lifi_quote("SOL", "1337", "USDT", "USDC", units, SOL_ADDR, EVM_ADDR)
                recv = int(q["toAmount"]) / 10 ** q["toDecimals"]
                r["bridge_in"] = {**q, "received_usdc": recv, "cost_usd": cap - recv + q["gas_usd"]}
            except Exception as e:
                r["bridge_in"] = {"error": str(e)}
            r["bridge_out_est"] = self.quote_bridge_out(cap)
            for name, out_mint in (("bench_usdt_to_usdc", USDC), ("bench_usdt_to_jitosol", JITO)):
                try:
                    q = self.jup_quote(USDT, out_mint, units)
                    r[name] = {"source": "jupiter lite-api", **q}
                except Exception as e:
                    r[name] = {"source": "jupiter lite-api", "error": str(e)}
            # USDT->USDC cost via jupiter (outAmount in USDC 6 dec). If jupiter failed, use LI.FI same-chain quote.
            bq = r.get("bench_usdt_to_usdc", {})
            if "outAmount" in bq:
                r["bench_usdc_cost_usd"] = cap - int(bq["outAmount"]) / 1e6
                r["bench_usdc_cost_source"] = "jupiter"
            else:
                try:
                    q = self.lifi_quote("SOL", "SOL", "USDT", "USDC", units, SOL_ADDR, SOL_ADDR)
                    r["bench_usdt_to_usdc_lifi"] = q
                    r["bench_usdc_cost_usd"] = cap - int(q["toAmount"]) / 10 ** q["toDecimals"] + q["gas_usd"]
                    r["bench_usdc_cost_source"] = "lifi (includes LI.FI 0.25% fee; jupiter unavailable)"
                except Exception as e:
                    r["bench_usdc_cost_usd"] = None
                    r["bench_usdc_cost_source"] = f"unavailable: {e}"
            out[k] = r
        self.state["oneoff_quotes"] = out
        log(f"one-off quotes: " + json.dumps({k: {"bridge_in_cost": v.get('bridge_in', {}).get('cost_usd'),
                                                  "bridge_out_cost": v.get('bridge_out_est', {}).get('cost_usd'),
                                                  "bench_usdc_cost": v.get('bench_usdc_cost_usd')} for k, v in out.items()}))

    def quote_bridge_out(self, cap):
        """Cash-out path: HL withdraw to Arbitrum ($1 fee, charged separately) then LI.FI ARB USDC -> SOL USDT.
        (LI.FI returns 404 for quotes with HyperCore 1337 as source.)"""
        SOL_ADDR = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        EVM_ADDR = "0x0000000000000000000000000000000000000001"
        amt = max(1.0, cap - CFG["oneoff_costs"]["hl_withdraw_fee_usdc"])
        try:
            q = self.lifi_quote("ARB", "SOL", "USDC", "USDT", int(round(amt * 1e6)), EVM_ADDR, SOL_ADDR)
            recv = int(q["toAmount"]) / 10 ** q["toDecimals"]
            return {**q, "route": "HL withdraw->Arbitrum USDC, then LI.FI ARB USDC->SOL USDT", "amount_bridged": amt,
                    "received_usdt": recv, "cost_usd": amt - recv + q["gas_usd"],
                    "note": "Arbitrum-side gas (ETH) for the user tx included in gas_usd as quoted"}
        except Exception as e:
            return {"error": str(e)}

    def ensure_quotes(self):
        """Retry missing reverse-bridge quotes and, if Jupiter becomes reachable, replace the LI.FI-based
        benchmark entry cost with Jupiter's real quote (benchmark value adjusted by the difference)."""
        USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
        USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        for k, r in self.state["oneoff_quotes"].items():
            cap = float(k)
            if "error" in r.get("bridge_out_est", {"error": 1}):
                r["bridge_out_est"] = self.quote_bridge_out(cap)
                log(f"bridge_out quote {k}: {r['bridge_out_est'].get('cost_usd', r['bridge_out_est'].get('error'))}")
            if r.get("bench_usdc_cost_source", "").startswith("lifi"):
                try:
                    q = self.jup_quote(USDT, USDC, int(round(cap * 1e6)))
                    new_cost = cap - int(q["outAmount"]) / 1e6
                    old_cost = r["bench_usdc_cost_usd"]
                    r["bench_usdt_to_usdc"] = {"source": "jupiter lite-api", **q}
                    r["bench_usdc_cost_usd"] = new_cost
                    r["bench_usdc_cost_source"] = f"jupiter (replaced lifi cost {old_cost:.6f} at {iso()})"
                    for pid, p in self.state["portfolios"].items():
                        if abs(p["capital"] - cap) < 1e-9:
                            for bk in ("kamino_usdc", "jitosol_yield"):
                                p["bench"][bk]["value"] += old_cost - new_cost
                                p["bench"][bk]["entry_cost"] = new_cost
                                p["bench"][bk]["entry_cost_source"] = "jupiter"
                    jl("funding_accruals", {"type": "benchmark_entry_cost_update", "capital": cap,
                                            "old_cost_lifi": old_cost, "new_cost_jupiter": new_cost})
                    log(f"bench entry cost {k}: lifi {old_cost:.5f} -> jupiter {new_cost:.5f}")
                except Exception as e:
                    log(f"jupiter still unavailable for bench cost {k}: {str(e)[:120]}")

    def poll_benchmarks(self):
        b = self.state["benchmarks"]
        t = iso()
        try:
            kc = CFG["benchmarks"]["kamino_usdc"]
            rows = self.http.get(kc["url"], venue="kamino")
            r = next(x for x in rows if x["reserve"] == kc["reserve"])
            spot_apy = float(r["supplyApy"])
            end = datetime.now(timezone.utc)
            start = datetime.fromtimestamp(end.timestamp() - 26 * 3600, tz=timezone.utc)
            hurl = (f"https://api.kamino.finance/kamino-market/{kc['url'].split('/kamino-market/')[1].split('/')[0]}"
                    f"/reserves/{kc['reserve']}/metrics/history?env=mainnet-beta"
                    f"&start={start.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={end.strftime('%Y-%m-%dT%H:%M:%SZ')}")
            hist = self.http.get(hurl, venue="kamino")["history"]
            vals = [float(x["metrics"]["supplyInterestAPY"]) for x in hist if x["metrics"].get("supplyInterestAPY") is not None][-24:]
            if len(vals) >= 12:
                apy, method = sum(vals) / len(vals), f"mean of last {len(vals)} hourly supplyInterestAPY (metrics/history)"
            else:
                apy, method = spot_apy, "spot supplyApy (history unavailable)"
            b["kamino_usdc"] = {"apy": apy, "apy_spot_now": spot_apy, "method": method, "polled_at": t, "stale": False,
                                "hourly_min": min(vals) if vals else None, "hourly_max": max(vals) if vals else None,
                                "source": "api.kamino.finance reserves/metrics + metrics/history", "tvl_usd": float(r["totalSupplyUsd"])}
        except Exception as e:
            if "kamino_usdc" in b:
                b["kamino_usdc"]["stale"] = True; b["kamino_usdc"]["stale_err"] = str(e)[:200]
            log(f"kamino poll failed: {e}")
        try:
            d = self.http.get(CFG["benchmarks"]["jitosol"]["url"], venue="jito")
            last = d["apy"][-1]
            b["jitosol"] = {"apy": float(last["data"]), "apy_date": last["date"], "polled_at": t, "stale": False,
                            "source": "kobe.mainnet.jito.network stake_pool_stats apy[-1]"}
        except Exception as e:
            try:
                d = self.http.get(CFG["benchmarks"]["jitosol"]["fallback"], venue="llama")
                last = d["data"][-1]
                b["jitosol"] = {"apy": float(last["apy"]) / 100, "apy_date": last["timestamp"], "polled_at": t,
                                "stale": False, "source": "DefiLlama chart JitoSOL (fallback)"}
            except Exception as e2:
                if "jitosol" in b:
                    b["jitosol"]["stale"] = True; b["jitosol"]["stale_err"] = str(e2)[:200]
                log(f"jito poll failed: {e} / {e2}")
        self.state["last_bench_poll_ms"] = now_ms()
        jl("funding_accruals", {"type": "benchmark_poll", "benchmarks": b})
        log(f"benchmarks: kamino_usdc={b.get('kamino_usdc', {}).get('apy')} jitosol={b.get('jitosol', {}).get('apy')}")

    # ---- portfolios
    def init_portfolios(self):
        for pid, p in CFG["portfolios"].items():
            cap = p["capital"]
            q = self.state["oneoff_quotes"].get(f"{cap:g}", {})
            bridge = q.get("bridge_in", {}).get("cost_usd")
            if bridge is None:
                raise RuntimeError(f"no bridge quote for {pid}; refusing to invent a number")
            acct = CFG["oneoff_costs"]["hl_new_account_fee_usdc"]
            cash = cap - bridge - acct
            bench_cost = q.get("bench_usdc_cost_usd")
            jito_q = q.get("bench_usdt_to_jitosol", {})
            self.state["portfolios"][pid] = {
                "capital": cap, "cash": cash, "positions": {},
                "oneoff": {"bridge_in": bridge, "hl_account_fee": acct},
                "totals": {"funding": 0.0, "fees": 0.0, "fees_maker_cf": 0.0, "realized_spot": 0.0,
                           "realized_perp": 0.0, "n_trades": 0, "n_accruals": 0, "exits_flip": 0, "exits_bar": 0,
                           "liquidations": 0, "margin_topups": 0},
                "nav_peak": cash, "max_dd": 0.0, "nav_last": cash,
                "bench": {
                    "kamino_usdc": {"value": cap - (bench_cost or 0.0), "entry_cost": bench_cost,
                                    "entry_cost_source": q.get("bench_usdc_cost_source"), "last_ms": now_ms()},
                    "jitosol_yield": {"value": cap - (bench_cost or 0.0), "entry_cost": bench_cost,
                                      "entry_cost_note": "USDT->USDC cost used as proxy; see oneoff_quotes bench_usdt_to_jitosol",
                                      "jup_jitosol_quote": jito_q, "last_ms": now_ms()},
                },
            }
            log(f"portfolio {pid}: capital={cap} bridge_in={bridge:.4f} acct_fee={acct} -> cash={cash:.4f}")

    def spot_mark(self, coin):
        s = self.spot_px.get(coin)
        return s["mid"] if s else None

    def pos_value(self, pos):
        coin = pos["coin"]
        sm = self.spot_mark(coin) or pos["spot_entry_px"]
        mk = self.markets.get(coin, {}).get("mark", pos["perp_entry_px"])
        spot_val = pos["size"] * sm
        perp_upnl = pos["size"] * (pos["perp_entry_px"] - mk)
        return spot_val, perp_upnl, sm, mk

    def nav(self, pid):
        p = self.state["portfolios"][pid]
        v = p["cash"]
        for pos in p["positions"].values():
            sv, up, _, _ = self.pos_value(pos)
            v += sv + pos["margin"] + up
        return v

    def open_position(self, pid, coin, target_notional, reason):
        p = self.state["portfolios"][pid]
        L = CFG["rules"]["perp_leverage"]
        mk = self.markets[coin]["mark"]
        sp = self.spot_mark(coin)
        if sp is None:
            return False, "no spot price"
        h = CFG["hedge"][coin]
        dec_p = self.perp_meta[coin]["szDecimals"]
        dec_s = self.spot_meta[coin]["szDecimals"] if h["venue"] == "hl_spot" else self.gate_meta[coin]["amount_precision"]
        dec = min(dec_p, dec_s)
        size = floor_dec(target_notional / max(mk, sp), dec)
        if size <= 0:
            return False, f"size rounds to 0 (step 10^-{dec})"
        ntl = size * mk
        if ntl < 10.0 or size * sp < 10.0:
            return False, f"notional {ntl:.2f} < HL $10 min"
        if h["venue"] == "gate" and size * sp * (self.usdc_usdt or 1) < self.gate_meta[coin]["min_quote"]:
            return False, "below gate min_quote"
        need = size * sp * 1.003 + ntl / L + ntl * 0.001
        if need > p["cash"]:
            return False, f"cash {p['cash']:.2f} < need {need:.2f}"
        spx, sfee, smcf = self.fill(pid, coin, "spot", "buy", size, reason)
        ppx, pfee, pmcf = self.fill(pid, coin, "perp", "sell", size, reason)
        margin = size * ppx / L
        p["cash"] -= size * spx + sfee + margin + pfee
        p["totals"]["fees"] += sfee + pfee
        p["totals"]["fees_maker_cf"] += smcf + pmcf
        p["totals"]["n_trades"] += 2
        pos = {"coin": coin, "opened_at": iso(), "opened_ms": now_ms(), "hedge_venue": h["venue"],
               "spot_symbol": self.spot_px[coin]["symbol"], "size": size, "spot_entry_px": spx, "perp_entry_px": ppx,
               "margin": margin, "leverage": L, "funding_accrued": 0.0, "fees_paid": sfee + pfee,
               "last_funding_ms": now_ms(), "entry_stats": self.fstats(coin)}
        p["positions"][coin] = pos
        jl("positions", {"event": "open", "portfolio": pid, "position": pos, "nav": self.nav(pid)})
        log(f"[{pid}] OPEN {coin} size={size} spot@{spx:.6g} perp@{ppx:.6g} ntl={size*ppx:.2f} fees={sfee+pfee:.4f} "
            f"mean7d={pos['entry_stats']['mean7d_ann']:.4f} cur={pos['entry_stats']['current_ann']:.4f}")
        return True, "ok"

    def close_position(self, pid, coin, reason):
        p = self.state["portfolios"][pid]
        pos = p["positions"][coin]
        size = pos["size"]
        spx, sfee, smcf = self.fill(pid, coin, "spot", "sell", size, reason)
        ppx, pfee, pmcf = self.fill(pid, coin, "perp", "buy", size, reason)
        r_spot = size * (spx - pos["spot_entry_px"])
        r_perp = size * (pos["perp_entry_px"] - ppx)
        p["cash"] += size * spx - sfee + pos["margin"] + r_perp - pfee
        p["totals"]["fees"] += sfee + pfee
        p["totals"]["fees_maker_cf"] += smcf + pmcf
        p["totals"]["realized_spot"] += r_spot
        p["totals"]["realized_perp"] += r_perp
        p["totals"]["n_trades"] += 2
        flag = None
        if pos["hedge_venue"] == "hl_spot" and size * spx < 10:
            flag = "spot sell < 10 USDC HL min: in reality would be stuck as dust"
        jl("positions", {"event": "close", "portfolio": pid, "coin": coin, "reason": reason, "size": size,
                         "spot_exit_px": spx, "perp_exit_px": ppx, "realized_spot": r_spot, "realized_perp": r_perp,
                         "funding_accrued": pos["funding_accrued"], "fees_close": sfee + pfee, "flag": flag,
                         "held_hours": (now_ms() - pos["opened_ms"]) / HOUR_MS})
        log(f"[{pid}] CLOSE {coin} ({reason}) spot {r_spot:+.4f} perp {r_perp:+.4f} funding {pos['funding_accrued']:+.4f}")
        del p["positions"][coin]
        self.state["cooldown"][f"{pid}:{coin}"] = now_ms()

    # ---- funding accrual
    def oracle_at(self, coin, t_ms):
        snaps = self.state["oracle_snaps"].get(coin, [])
        best = min(snaps, key=lambda s: abs(s[0] - t_ms)) if snaps else None
        if best and abs(best[0] - t_ms) <= 5 * 60_000:
            return best[1], "hl_ctx_oraclePx_poll", best[0], (best[0] - t_ms) / 1000
        c = self.http.hl({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1m",
                                                          "startTime": t_ms - 120_000, "endTime": t_ms + 60_000}})
        cands = [x for x in c if x["t"] <= t_ms] or c
        if not cands:
            raise RuntimeError(f"no oracle proxy for {coin} at {t_ms}")
        x = cands[-1]
        return float(x["o"]), "PROXY_perp_1m_candle_open (no oracle poll within 5min)", x["t"], (x["t"] - t_ms) / 1000

    def accrue_funding(self):
        for pid, p in self.state["portfolios"].items():
            for coin, pos in p["positions"].items():
                for t, rate, prem in self.cache.get(coin, []):
                    if t <= pos["last_funding_ms"] or t <= pos["opened_ms"]:
                        continue
                    ox, src, ots, lag = self.oracle_at(coin, t)
                    pay = pos["size"] * ox * rate          # short: -szi*oracle*rate, szi=-size
                    p["cash"] += pay
                    pos["funding_accrued"] += pay
                    pos["last_funding_ms"] = t
                    p["totals"]["funding"] += pay
                    p["totals"]["n_accruals"] += 1
                    jl("funding_accruals", {"type": "funding", "portfolio": pid, "coin": coin, "funding_time_ms": t,
                                            "funding_time": iso(t), "hl_fundingRate": rate, "hl_premium": prem,
                                            "rate_ann": rate * YEAR_H, "position_size": pos["size"], "side": "short",
                                            "oracle_px": ox, "oracle_source": src, "oracle_ts": iso(ots),
                                            "oracle_lag_s": lag, "payment_usdc": pay,
                                            "formula": "payment = size * oracle_px * fundingRate (HL docs: position_size*oracle_price*funding_rate)"})

    def accrue_benchmarks(self):
        b = self.state["benchmarks"]
        t = now_ms()
        for pid, p in self.state["portfolios"].items():
            for key, bkey in (("kamino_usdc", "kamino_usdc"), ("jitosol_yield", "jitosol")):
                bb = p["bench"][key]
                src = b.get(bkey)
                if not src:
                    continue
                dt_h = (t - bb["last_ms"]) / HOUR_MS
                if dt_h <= 0:
                    continue
                before = bb["value"]
                bb["value"] = before * (1 + src["apy"]) ** (dt_h / YEAR_H)
                bb["last_ms"] = t
                jl("funding_accruals", {"type": "benchmark", "portfolio": pid, "bench": key, "apy": src["apy"],
                                        "apy_stale": src.get("stale", False), "hours": dt_h,
                                        "value_before": before, "value_after": bb["value"]})

    # ---- risk
    def margin_checks(self):
        R = CFG["rules"]
        for pid, p in self.state["portfolios"].items():
            for coin in list(p["positions"].keys()):
                pos = p["positions"][coin]
                _, up, _, mk = self.pos_value(pos)
                maxlev = self.perp_meta[coin]["maxLeverage"] or 3
                mm = pos["size"] * mk / (2 * maxlev)
                eq = pos["margin"] + up
                if eq <= mm:
                    p["totals"]["liquidations"] += 1
                    log(f"[{pid}] LIQUIDATION {coin} eq={eq:.4f} mm={mm:.4f}")
                    jl("positions", {"event": "liquidation_warning_close", "portfolio": pid, "coin": coin, "eq": eq, "mm": mm})
                    self.close_position(pid, coin, "liquidation_proxy(close before liq)")
                elif eq < R["margin_topup_when_equity_below_x_mm"] * mm:
                    target = pos["size"] * mk / pos["leverage"]
                    add = max(0.0, target - eq)
                    if add > 0 and p["cash"] >= add:
                        p["cash"] -= add; pos["margin"] += add
                        p["totals"]["margin_topups"] += 1
                        jl("positions", {"event": "margin_topup", "portfolio": pid, "coin": coin, "added": add})
                    elif add > 0:
                        self.close_position(pid, coin, "margin_insufficient_cash")

    # ---- strategy
    def evaluate(self):
        R = CFG["rules"]
        stats = {c: self.fstats(c) for c in self.all_coins()}
        decisions = {}
        for pid, pc in CFG["portfolios"].items():
            p = self.state["portfolios"][pid]
            dlog = []
            # exits
            for coin in list(p["positions"].keys()):
                s = stats[coin]
                held_h = (now_ms() - p["positions"][coin]["opened_ms"]) / HOUR_MS
                if s["flips24h"] >= R["exit_flips_24h_at_least"]:
                    p["totals"]["exits_flip"] += 1
                    self.close_position(pid, coin, f"exit_flips24h={s['flips24h']}")
                    dlog.append(f"exit {coin} flips")
                elif s["mean3d_ann"] is not None and s["mean3d_ann"] < 0:
                    p["totals"]["exits_flip"] += 1
                    self.close_position(pid, coin, f"exit_mean3d_negative={s['mean3d_ann']:.4f}")
                    dlog.append(f"exit {coin} mean3d<0")
                elif (s["mean3d_ann"] is not None and s["mean3d_ann"] < R["exit_mean3d_ann_below"]
                      and held_h >= R["exit_min_hold_hours_for_bar_rule"]):
                    p["totals"]["exits_bar"] += 1
                    self.close_position(pid, coin, f"exit_below_bar mean3d={s['mean3d_ann']:.4f}")
                    dlog.append(f"exit {coin} below bar")
            # entries
            eq = self.nav(pid)
            L = R["perp_leverage"]
            n_total = eq * (1 - R["cash_reserve_frac"]) / (1 + 1 / L)
            k = int(min(pc["max_positions"], max(0, math.floor(n_total / R["min_position_notional"]))))
            if k == 0:
                decisions[pid] = dlog + ["capital too small for any position"]
                continue
            target = n_total / k
            cands = []
            for coin in pc["universe"]:
                if coin in p["positions"]:
                    continue
                s = stats[coin]
                cd = self.state["cooldown"].get(f"{pid}:{coin}")
                why = []
                if s["mean7d_ann"] is None or s["mean7d_ann"] < R["entry_min_mean7d_ann"]:
                    why.append(f"mean7d={s['mean7d_ann']}")
                if R["entry_require_current_funding_positive"] and not (s["current_ann"] and s["current_ann"] > 0):
                    why.append("current<=0")
                if (s["oi_usd"] or 0) < R["entry_min_oi_usd"]:
                    why.append("oi")
                if s["flips24h"] > R["entry_max_flips_24h"]:
                    why.append(f"flips24h={s['flips24h']}")
                if cd and now_ms() - cd < R["reentry_cooldown_hours"] * HOUR_MS:
                    why.append("cooldown")
                if coin not in self.spot_px:
                    why.append("no spot px")
                if why:
                    dlog.append(f"skip {coin}: {','.join(why)}")
                else:
                    cands.append((s["mean7d_ann"], coin))
            cands.sort(reverse=True)
            slots = k - len(p["positions"])
            for _, coin in cands[:max(0, slots)]:
                t = target
                cap = pc.get("weight_caps", {}).get(coin)
                if cap:
                    t = min(t, cap * n_total)
                ok, msg = self.open_position(pid, coin, t, f"entry mean7d={stats[coin]['mean7d_ann']:.4f}")
                dlog.append(f"open {coin}: {msg}")
            decisions[pid] = dlog
        jl("positions", {"event": "evaluation", "stats": stats, "decisions": decisions})
        return decisions

    def snapshot(self, tag="hourly"):
        for pid, p in self.state["portfolios"].items():
            nav = self.nav(pid)
            p["nav_last"] = nav
            if nav > p["nav_peak"]:
                p["nav_peak"] = nav
            dd = (p["nav_peak"] - nav) / p["nav_peak"] if p["nav_peak"] else 0
            p["max_dd"] = max(p["max_dd"], dd)
            poss = []
            for coin, pos in p["positions"].items():
                sv, up, sm, mk = self.pos_value(pos)
                poss.append({"coin": coin, "size": pos["size"], "spot_mid": sm, "perp_mark": mk,
                             "spot_upnl": pos["size"] * (sm - pos["spot_entry_px"]), "perp_upnl": up,
                             "margin": pos["margin"], "funding_accrued": pos["funding_accrued"],
                             "current_funding_ann": self.markets.get(coin, {}).get("funding", 0) * YEAR_H,
                             "hedge_venue": pos["hedge_venue"]})
            jl("positions", {"event": "snapshot", "tag": tag, "portfolio": pid, "nav": nav, "cash": p["cash"],
                             "dd": dd, "max_dd": p["max_dd"], "totals": p["totals"],
                             "bench": {k: v["value"] for k, v in p["bench"].items()}, "positions": poss})

    def write_status(self):
        st = {"service": CFG["service"], "paper_only": True, "pid": os.getpid(), "heartbeat": iso(),
              "heartbeat_ms": now_ms(), "started_at": self.state.get("started_at"), "end_at": None, "run_mode": "indefinite",
              "counters": self.state["counters"], "last_error": self.state.get("last_error"),
              "benchmarks": self.state["benchmarks"], "portfolios": {}}
        for pid, p in self.state["portfolios"].items():
            nav = self.nav(pid) if self.markets else p.get("nav_last")
            cap = p["capital"]
            days = max(1e-9, (now_ms() - (self.state.get("started_ms") or now_ms())) / 86400_000)
            st["portfolios"][pid] = {
                "capital": cap, "nav": nav, "cash": p["cash"], "ret_pct": (nav / cap - 1) * 100,
                "apr_simple_pct": (nav / cap - 1) * 365 / days * 100 if days > 0.04 else None,
                "funding": p["totals"]["funding"], "fees": p["totals"]["fees"], "max_dd_pct": p["max_dd"] * 100,
                "positions": {c: {"size": v["size"], "funding_accrued": v["funding_accrued"],
                                  "current_funding_ann": self.markets.get(c, {}).get("funding", 0) * YEAR_H}
                              for c, v in p["positions"].items()},
                "bench": {k: v["value"] for k, v in p["bench"].items()}}
        atomic_write(DATA / "status.json", st)

    def rotate_logs(self, day):
        """gzip each live log to logs/archive/YYYY-MM/<name>.<day>.gz, verify, then truncate the original.
        Nothing is deleted unless the compressed copy decompresses to the identical bytes."""
        arch = LOGS / "archive" / day[:7]
        arch.mkdir(parents=True, exist_ok=True)
        names = ["positions.jsonl", "funding_accruals.jsonl", "trades.jsonl", "marks.jsonl",
                 "service.log", "watchdog.log", "stdout.log"]
        done = []
        for n in names:
            src = LOGS / n
            if not src.exists() or src.stat().st_size == 0:
                continue
            dst = arch / f"{n}.{day}.gz"
            k = 1
            while dst.exists():
                dst = arch / f"{n}.{day}.{k}.gz"; k += 1
            data = src.read_bytes()
            with gzip.open(dst, "wb", compresslevel=6) as g:
                g.write(data)
            with gzip.open(dst, "rb") as g:
                ok = g.read() == data
            if not ok:
                log(f"ROTATION VERIFY FAILED for {n}; original kept")
                dst.unlink(missing_ok=True)
                continue
            # copy-truncate: keep only bytes appended after our read (other writers, e.g. watchdog/stdout)
            with open(src, "r+b") as fh:
                fh.seek(len(data)); tail = fh.read()
                fh.seek(0); fh.write(tail); fh.truncate()
            done.append(f"{n}->{dst.relative_to(ROOT)} ({len(data)}B)")
        log("rotated " + "; ".join(done) if done else "rotation: nothing to rotate")
        jl("positions", {"event": "log_rotation", "day": day, "archived": done})

    def run_report(self):
        try:
            import subprocess
            subprocess.run([sys.executable, str(ROOT / "report.py")], cwd=str(ROOT), timeout=120, check=False)
        except Exception as e:
            log(f"report failed: {e}")

    # ---- main
    def hourly_cycle(self, hour_ms):
        self.update_funding_cache()
        self.accrue_funding()
        self.accrue_benchmarks()
        self.margin_checks()
        self.evaluate()
        self.snapshot("hourly")
        self.state["last_eval_hour_ms"] = hour_ms
        self.save()
        self.write_status()
        self.run_report()

    def run(self):
        if (DATA / "FINISHED").exists():  # legacy marker from the old 30-day design: ignore and remove
            (DATA / "FINISHED").unlink()
        fresh = self.state is None
        if fresh:
            self.init_state()
        self.load_meta()
        if fresh:
            self.update_funding_cache(bootstrap=True)
            self.poll_markets("startup")
            self.poll_benchmarks()
            self.fetch_oneoff()
            self.init_portfolios()
            self.state["started_at"] = iso(); self.state["started_ms"] = now_ms()
            self.state["last_eval_hour_ms"] = (now_ms() // HOUR_MS) * HOUR_MS
            self.evaluate()
            self.snapshot("startup")
            self.save()
            self.write_status()
            self.run_report()
        else:
            self.poll_markets("resume")
            self.update_funding_cache()
            self.ensure_quotes()
            self.save()
        while not STOP:
            try:
                t = now_ms()
                hour_ms = (t // HOUR_MS) * HOUR_MS
                if self.state["last_snap_hour_ms"] < hour_ms and t - hour_ms >= 15_000:
                    self.poll_markets("funding_snap")
                    self.state["last_snap_hour_ms"] = hour_ms
                elif time.time() - self.last_poll >= CFG["poll_seconds"]:
                    self.poll_markets("poll")
                if self.state["last_eval_hour_ms"] < hour_ms and t - hour_ms >= 120_000:
                    self.hourly_cycle(hour_ms)
                if t - self.state["last_bench_poll_ms"] >= 24 * HOUR_MS:
                    self.poll_benchmarks()
                    self.ensure_quotes()
                today = datetime.now().astimezone().date().isoformat()
                if self.state.get("last_rotation_date") is None:
                    self.state["last_rotation_date"] = today
                elif self.state["last_rotation_date"] != today:
                    # final report for the finished day from the live logs, then archive them
                    self.run_report()
                    self.rotate_logs(self.state["last_rotation_date"])
                    self.state["last_rotation_date"] = today
                    self.save()
                self.write_status()
                self.save()
            except Exception as e:
                self.state["last_error"] = {"at": iso(), "err": f"{type(e).__name__}: {e}"}
                log("ERROR " + traceback.format_exc())
                time.sleep(30)
            for _ in range(20):
                if STOP:
                    break
                time.sleep(1)
        self.save()
        log("stopped")


if __name__ == "__main__":
    Service().run()
