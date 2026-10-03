#!/usr/bin/env python3
"""Lab bot (paper only): hypothesis portfolios (H1-H4) + tuning forks. Never signs/sends.

Reuses the decisions the existing bots already log (tails logs/decisions.jsonl and
logs/meme_decisions.jsonl); it makes NO extra model calls. Portfolios live in data/lab/portfolios,
equity in data/lab/equity, trades go to the shared logs/trades.jsonl / logs/meme_trades.jsonl
(tagged strategy=hyp:* or fork:*), decisions to logs/lab_decisions.jsonl, limit orders to logs/lab_orders.jsonl.
Registry (hypotheses + forks + lineages): data/lab/registry.json (see bot/lab_registry.py).
"""
from __future__ import annotations
import json, os, signal, sys, time, traceback, uuid
from collections import deque
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # código do lab (não PAPER_LAB_ROOT)
from bot.paths import ROOT, LAB_DIR  # noqa: E402
from bot.lib import brt_iso, brt_now, load_cfg, apply_gates, append_jsonl, write_json, BRT
from bot import lab_registry as R
import bot.sol_bot as SB
import bot.meme_bot as MB

STOP = False
def _sig(*_a):
    global STOP
    STOP = True

DEC_SOL = ROOT / "logs" / "decisions.jsonl"
DEC_MEME = ROOT / "logs" / "meme_decisions.jsonl"
TR_SOL = ROOT / "logs" / "trades.jsonl"
TR_MEME = ROOT / "logs" / "meme_trades.jsonl"
LAB_DEC = ROOT / "logs" / "lab_decisions.jsonl"
ORDERS = ROOT / "logs" / "lab_orders.jsonl"
STATUS = ROOT / "data" / "lab" / "status.json"
TOKENS = {t["symbol"]: t for t in json.loads((ROOT / "memecoins.json").read_text())["tokens"]}


class Tail:
    """Incremental reader of an append-only JSONL file (complete lines only).
    Rotation-safe (bot/logio.py): keeps the fd open; when the path's inode changes it drains the old
    inode, switches to the new file and skips seeded rows (ts <= last seen ts)."""
    def __init__(self, path: Path, from_end=True):
        self.path = path; self.buf = b""; self.fh = None; self.ino = None; self.last_ts = 0.0
        if path.exists():
            self.fh = open(path, "rb"); self.ino = os.fstat(self.fh.fileno()).st_ino
            if from_end:
                self.fh.seek(0, 2)

    def _drain(self, skip_old=False):
        out = []
        if not self.fh:
            return out
        data = self.buf + self.fh.read()
        lines = data.split(b"\n"); self.buf = lines.pop()
        for l in lines:
            if not l.strip():
                continue
            try: r = json.loads(l)
            except Exception: continue
            t = float(r.get("ts") or 0)
            if skip_old and t <= self.last_ts:
                continue
            self.last_ts = max(self.last_ts, t)
            out.append(r)
        return out

    def read(self):
        out = self._drain()
        try:
            st = os.stat(self.path)
        except FileNotFoundError:
            return out
        if self.fh is None or st.st_ino != self.ino:
            if self.fh:
                out += self._drain(); self.fh.close()
            self.fh = open(self.path, "rb"); self.ino = os.fstat(self.fh.fileno()).st_ino; self.buf = b""
            out += self._drain(skip_old=True)
        return out


def last_row(path: Path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 4096))
            lines = [l for l in f.read().split(b"\n") if l.strip()]
        return json.loads(lines[-1]) if lines else None
    except Exception:
        return None


def mark(asset: str, max_age=120.0):
    p = ROOT / "data" / "prices.jsonl" if asset == "SOL" else ROOT / "data" / "meme" / "prices" / f"{asset}.jsonl"
    r = last_row(p)
    if not r or r.get("stale") or r.get("fabricated") or not r.get("price_usd"):
        return None
    if time.time() - float(r["ts"]) > max_age:
        return None
    return float(r["price_usd"])


def equity(p, px):
    return float(p["usdt"]) + (float(p["sol"]) if p["asset_mode"] == "sol" else float(p.get("token") or 0)) * px

def bh_equity(p, px):
    bh = p["benchmark_buy_hold"]
    return float(bh.get("usdt", 0)) + float(bh.get("sol" if p["asset_mode"] == "sol" else "token", 0)) * px

def qty(p):
    return float(p["sol"]) if p["asset_mode"] == "sol" else float(p.get("token") or 0)


def gates_for(entry, cfg, overlay):
    base = dict(cfg["gates_relaxed"] if entry.get("profile") == "relaxed" else cfg["gates"])
    base.setdefault("min_prob_margin", 0.0)
    for k, v in (entry.get("params", {}).get("gates") or {}).items():
        base[k] = v
    ov = (overlay.get("portfolios") or {}).get(entry["name"]) or {}
    # Only risk-reducing overlay keys from dashboard are honored; nightly never edits originals.
    for k in ("cooldown_seconds", "max_trades_per_hour", "buy_fraction_usdt"):
        if ov.get(k) is not None:
            base[k] = ov[k]
    return R.clamp_gates(base)


class Lab:
    def __init__(self):
        self.cfg = load_cfg()
        self.reg = R.load()
        self.ports = {}
        self.tails = {"sol": Tail(DEC_SOL), "meme": Tail(DEC_MEME)}
        self.ens_latest = {}   # asset -> model -> row
        self.ens_last_eval = {}
        self.windows = {}      # (class, model) -> deque
        self.last_eq = {}
        self.errors = 0; self.cycles = 0
        self.processed = 0
        self._seed_windows()

    # ---------- portfolios ----------
    def port(self, name):
        if name not in self.ports:
            self.ports[name] = json.loads(R.port_path(name).read_text())
        return self.ports[name]

    def save(self, name):
        write_json(R.port_path(name), self.ports[name])

    def log_eq(self, name, px, force=False):
        now = time.time()
        if not force and now - self.last_eq.get(name, 0) < 60:
            return
        p = self.port(name); self.last_eq[name] = now
        append_jsonl(R.eq_path(name), {
            "ts": now, "price": px, "sol": p["sol"], "token": p.get("token", 0.0), "usdt": p["usdt"],
            "equity": equity(p, px), "bh_equity": bh_equity(p, px),
            "all_usdt_equity": float(p["benchmark_all_usdt"]["usdt"]), "trade_count": p["trade_count"],
            "portfolio": name})

    # ---------- ensemble percentile windows ----------
    def _seed_windows(self):
        ens = [e for e in self.reg["portfolios"].values() if e["kind"] == "ensemble"]
        if not ens:
            return
        for cls, path in (("sol", DEC_SOL), ("meme", DEC_MEME)):
            try:
                with open(path, "rb") as f:
                    f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 12_000_000))
                    lines = f.read().split(b"\n")[1:]
            except Exception:
                continue
            for l in lines:
                try: d = json.loads(l)
                except Exception: continue
                m = self._ens_model_of(cls, d.get("portfolio"))
                if m and d.get("confidence") is not None and not d.get("fail_closed"):
                    self._win(cls, m).append(float(d["confidence"]))

    def _win(self, cls, model):
        k = (cls, model)
        if k not in self.windows:
            n = int(((self.cfg.get("lab") or {}).get("ensemble_window") or {}).get(cls, 480 if cls == "sol" else 200))
            self.windows[k] = deque(maxlen=n)
        return self.windows[k]

    @staticmethod
    def _ens_model_of(cls, pname):
        if not pname:
            return None
        if cls == "sol":
            return {"baseline": "von", "poorjev_baseline": "poorjev", "laya_baseline": "laya"}.get(pname)
        if pname.startswith("meme_") and pname.endswith("_baseline"):
            return "von"
        if pname.endswith("_poorjev_baseline"):
            return "poorjev"
        if pname.endswith("_laya_baseline"):
            return "laya"
        return None

    @staticmethod
    def _asset_of(cls, d):
        return "SOL" if cls == "sol" else d.get("symbol")

    def _pct(self, cls, model, conf):
        w = self._win(cls, model)
        if not w:
            return None, 0
        lo = sum(1 for x in w if x < conf); eq = sum(1 for x in w if x == conf)
        return (lo + 0.5 * eq) / len(w), len(w)

    # ---------- trading ----------
    def market_trade(self, e, side, px, did):
        p = self.port(e["name"]); g = e["_g"]
        tag = e["strategy"]
        before = qty(p)
        if e["asset"] == "SOL":
            tr = SB.sim_trade(side, p, g, self.cfg["fees"], self.cfg["market"], px, did, TR_SOL, strategy=tag)
        else:
            t = TOKENS[e["asset"]]
            sol_usd = mark("SOL", 600) or 0.0
            tr = MB.sim_trade(side, p, g, self.cfg["fees"], self.cfg["market"], px, did, TR_MEME,
                              t["mint"], int(t["decimals"]), sol_usd, strategy=tag)
        if tr:
            self._track(p, side, before, tr, px)
            self.save(e["name"]); self.log_eq(e["name"], px, force=True)
        return tr

    def _track(self, p, side, before, tr, px):
        f = tr["fill"]
        if side == "buy":
            got = float(f.get("sol_out_net") or f.get("token_out_net") or 0)
            cost = float(f["usdt_in"])
            prev_e = float(p.get("entry_price") or px)
            tot = before + got
            p["entry_price"] = ((before * prev_e) + cost) / tot if tot > 0 else px
            p["peak_price"] = max(float(p.get("peak_price") or 0), px) if before > 0 else px
        else:
            p["entry_price"] = None; p["peak_price"] = None

    def place_limit(self, e, side, px, did):
        p = self.port(e["name"]); ex = e["params"]["exec"]; g = e["_g"]
        off = float(ex.get("offset_bps", 10)) / 1e4
        if side == "buy":
            usdt_in = float(p["usdt"]) * float(g["buy_fraction_usdt"])
            if usdt_in < float(g["min_usdt_trade"]):
                return None
            order = {"side": "buy", "limit": px * (1 - off), "usdt_in": usdt_in}
        else:
            q = qty(p)
            if q * px < float(g["min_usdt_trade"]):
                return None
            order = {"side": "sell", "limit": px * (1 + off), "qty": q}
        order.update({"id": str(uuid.uuid4()), "placed_ts": time.time(), "placed_brt": brt_iso(), "mid": px,
                      "expires_ts": time.time() + 60 * float(ex.get("ttl_min", 15)), "decision_id": did})
        p["open_order"] = order; self.save(e["name"])
        append_jsonl(ORDERS, {"ts": time.time(), "ts_brt": brt_iso(), "portfolio": e["name"], "event": "placed", **order})
        return order

    def check_limit(self, e, px):
        p = self.port(e["name"]); o = p.get("open_order")
        if not o:
            return
        ex = e["params"]["exec"]; fee_bps = float(ex.get("fee_bps", 10)) / 1e4
        net_sol = float(self.cfg["fees"].get("assumed_network_fee_sol", 5e-6)); net_usdt = net_sol * px
        now = time.time()
        filled = (o["side"] == "buy" and px < o["limit"]) or (o["side"] == "sell" and px > o["limit"])
        if not filled:
            if now >= o["expires_ts"]:
                append_jsonl(ORDERS, {"ts": now, "ts_brt": brt_iso(), "portfolio": e["name"], "event": "cancelled",
                                      "id": o["id"], "side": o["side"], "limit": o["limit"], "last_mark": px})
                p["open_order"] = None; self.save(e["name"])
            return
        lim = o["limit"]; before = qty(p)
        if o["side"] == "buy":
            usdt_in = min(float(o["usdt_in"]), float(p["usdt"]))
            got = max(0.0, usdt_in * (1 - fee_bps) / lim - net_sol)
            fee = usdt_in * fee_bps + net_usdt
            p["usdt"] -= usdt_in; p["sol"] = float(p["sol"]) + got
            fill = {"side": "buy", "usdt_in": usdt_in, "sol_out_net": got, "fee_usdt": fee, "fill_mode": "limit_sim",
                    "limit_price": lim, "mark_price": px, "order_id": o["id"], "placed_ts": o["placed_ts"]}
            pnl = 0.0
        else:
            q = min(float(o["qty"]), float(p["sol"]))
            out = max(0.0, q * lim * (1 - fee_bps) - net_usdt)
            fee = q * lim * fee_bps + net_usdt
            pnl = out - q * px
            p["sol"] = float(p["sol"]) - q; p["usdt"] += out
            p["realized_pnl_usdt"] = float(p.get("realized_pnl_usdt", 0)) + pnl
            fill = {"side": "sell", "sol_in": q, "usdt_out_net": out, "fee_usdt": fee, "fill_mode": "limit_sim",
                    "limit_price": lim, "mark_price": px, "order_id": o["id"], "placed_ts": o["placed_ts"], "approx_pnl": pnl}
        p["fees_paid_usdt"] = float(p.get("fees_paid_usdt", 0)) + fee
        p["fees_paid_sol"] = float(p.get("fees_paid_sol", 0)) + net_sol
        p["trade_count"] += 1; p["last_trade_ts"] = now
        p["trade_timestamps"] = (p.get("trade_timestamps") or [])[-99:] + [now]
        p["position"] = "held" if float(p["sol"]) > 1e-6 else "sold"
        p["open_order"] = None
        row = {"ts": now, "ts_brt": brt_iso(now), "portfolio": e["name"], "decision_id": o["decision_id"],
               "side": o["side"], "price_mark": px, "fill": fill, "quote": {"fill_mode": "limit_sim"},
               "paper_only": True, "signed": False, "sent": False, "strategy": e["strategy"],
               "portfolio_after": {"sol": p["sol"], "usdt": p["usdt"], "equity": equity(p, px)}}
        append_jsonl(TR_SOL, row)
        append_jsonl(ORDERS, {"ts": now, "ts_brt": brt_iso(), "portfolio": e["name"], "event": "filled", "id": o["id"],
                              "side": o["side"], "limit": lim, "mark": px, "wait_s": round(now - o["placed_ts"], 1)})
        self._track(p, o["side"], before, row, lim)
        self.save(e["name"]); self.log_eq(e["name"], px, force=True)

    def check_exits(self, e, px):
        ex = (e.get("params") or {}).get("exits")
        p = self.port(e["name"])
        if not ex or qty(p) * px < 1.0:
            return
        entry = float(p.get("entry_price") or p.get("start_price") or px)
        peak = max(float(p.get("peak_price") or entry), px); p["peak_price"] = peak
        r = px / entry - 1
        why = None
        if r >= float(ex["tp"]):
            why = "take_profit"
        elif r <= -float(ex["sl"]):
            why = "stop_loss"
        elif peak / entry - 1 >= float(ex.get("trail_arm", ex["trail"])) and px <= peak * (1 - float(ex["trail"])):
            why = "trailing_stop"
        if not why:
            return
        did = str(uuid.uuid4())
        tr = self.market_trade(e, "sell", px, did)
        if tr:
            p["reentry_block_until"] = time.time() + 60 * float(ex.get("reentry_cooldown_min", 30))
            self.save(e["name"])
        self.log_dec(e, None, "sell", None, "sell" if tr else "hold", [why] + ([] if tr else ["sim_none"]), bool(tr), px,
                     extra={"entry_price": entry, "peak_price": peak, "ret_from_entry": r})

    def log_dec(self, e, src, chosen, conf, final, reasons, traded, px, extra=None):
        p = self.port(e["name"])
        append_jsonl(LAB_DEC, {"ts": time.time(), "ts_brt": brt_iso(), "portfolio": e["name"], "strategy": e["strategy"],
                               "asset": e["asset"], "source_decision_id": (src or {}).get("decision_id"),
                               "model": e.get("model"), "chosen_action": chosen, "confidence": conf,
                               "final_action": final, "gate_reasons": reasons, "traded": traded, "price_usd": px,
                               "equity_usd": equity(p, px), **(extra or {})})

    def act(self, e, chosen, conf, probs, skip, px, src, extra=None):
        p = self.port(e["name"]); prm = e.get("params") or {}
        reasons = []
        hours = prm.get("hours")
        if hours is not None and brt_now().hour not in hours:
            reasons.append("outside_hours")
        if chosen == "buy" and time.time() < float(p.get("reentry_block_until") or 0):
            reasons.append("reentry_cooldown")
        if p.get("open_order") and chosen in ("buy", "sell"):
            reasons.append("order_open")
        g = apply_gates(chosen, conf, skip, p, e["_g"], px, probabilities=probs,
                        profile="relaxed" if e.get("profile") == "relaxed" else "baseline")
        final = g["final_action"] if not reasons else "hold"
        reasons = g["gate_reasons"] + reasons
        traded = False
        if final in ("buy", "sell"):
            did = (src or {}).get("decision_id") or str(uuid.uuid4())
            if (prm.get("exec") or {}).get("mode") == "limit":
                o = self.place_limit(e, final, px, did)
                reasons.append("limit_placed" if o else "limit_none")
            else:
                traded = bool(self.market_trade(e, final, px, did))
                if not traded:
                    reasons.append("sim_none")
        self.log_dec(e, src, chosen, conf, final, reasons, traded, px, extra)
        self.log_eq(e["name"], px)

    # ---------- main processing ----------
    def active(self, overlay):
        out = []
        paused_all = bool((overlay.get("bots") or {}).get("lab_paused"))
        for e in self.reg["portfolios"].values():
            if e.get("status") != "active":
                continue
            e = dict(e)
            e["_paused"] = paused_all or bool(((overlay.get("portfolios") or {}).get(e["name"]) or {}).get("paused"))
            e["_g"] = gates_for(e, self.cfg, overlay)
            if e["kind"] == "ensemble":
                e["_g"]["min_confidence"] = float(e["params"]["ensemble"].get("pct_threshold", 0.8))
                e["_g"]["max_skip_noul"] = 1.01
            out.append(e)
        return out

    def cycle(self):
        if R.mtime() != self.reg.get("_mtime"):
            self.reg = R.load()
        overlay = {}
        pop = ROOT / "data" / "params_overlay.json"
        if pop.exists():
            try: overlay = json.loads(pop.read_text())
            except Exception: overlay = {}
        act = self.active(overlay)
        by_source = {}
        for e in act:
            if e["kind"] == "gated":
                by_source.setdefault((e["cls"], e["source"]), []).append(e)
        new = {"sol": self.tails["sol"].read(), "meme": self.tails["meme"].read()}
        for cls, rows in new.items():
            for d in rows:
                pn = d.get("portfolio")
                m = self._ens_model_of(cls, pn)
                if m and d.get("confidence") is not None:
                    a = self._asset_of(cls, d)
                    self.ens_latest.setdefault(a, {})[m] = d
                for e in by_source.get((cls, pn), []):
                    if e["_paused"]:
                        continue
                    px = mark(e["asset"]) or d.get("price_usd")
                    if not px:
                        continue
                    self.processed += 1
                    self.act(e, d.get("chosen_action"), float(d.get("confidence") or 0), d.get("probabilities"),
                             float(d.get("skip_noul") or 0), float(px), d)
                if m and d.get("confidence") is not None and not d.get("fail_closed"):
                    d["_pct_pending"] = True
        # ensemble evaluation
        for e in act:
            if e["kind"] != "ensemble" or e["_paused"]:
                continue
            a = e["asset"]; cls = e["cls"]; lat = self.ens_latest.get(a) or {}
            von = lat.get("von")
            if not von or von["ts"] <= self.ens_last_eval.get(e["name"], 0):
                continue
            span = 30 if cls == "sol" else 120
            peers = {m: r for m, r in lat.items() if abs(r["ts"] - von["ts"]) <= span}
            if len(peers) < 3 and time.time() - von["ts"] < (10 if cls == "sol" else 45):
                continue  # wait for peers from the same cycle
            self.ens_last_eval[e["name"]] = von["ts"]
            prm = e["params"]["ensemble"]
            pcts = {}; ns = {}
            for m, r in peers.items():
                pc, n = self._pct(cls, m, float(r["confidence"]))
                if pc is not None and n >= int(prm.get("min_window", 100)):
                    pcts[m] = pc; ns[m] = n
            votes = {"buy": [], "sell": []}
            for m, r in peers.items():
                if r.get("chosen_action") in votes and m in pcts and not r.get("fail_closed"):
                    votes[r["chosen_action"]].append(m)
            side = max(votes, key=lambda s: (len(votes[s]), sum(pcts[m] for m in votes[s])))
            agree = votes[side]
            comb = sum(pcts[m] for m in agree) / len(agree) if agree else 0.0
            chosen = side if len(agree) >= int(prm.get("min_agree", 2)) else "hold"
            px = mark(a) or von.get("price_usd")
            if px:
                self.act(e, chosen, comb if chosen != "hold" else 0.0, None, 0.0, float(px), von,
                         extra={"ens_pcts": {m: round(v, 3) for m, v in pcts.items()}, "ens_agree": agree,
                                "ens_combined_pct": round(comb, 3), "ens_window_n": ns})
        # update percentile windows AFTER scoring
        for cls, rows in new.items():
            for d in rows:
                if d.pop("_pct_pending", False):
                    self._win(cls, self._ens_model_of(cls, d.get("portfolio"))).append(float(d["confidence"]))
        # per-cycle: limit orders, exits, equity marks
        for e in act:
            px = mark(e["asset"])
            if px is None:
                continue
            if (e.get("params") or {}).get("exec", {}).get("mode") == "limit":
                self.check_limit(e, px)
            if not e["_paused"]:
                self.check_exits(e, px)
            self.log_eq(e["name"], px)
        return act


def main():
    signal.signal(signal.SIGTERM, _sig); signal.signal(signal.SIGINT, _sig)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    created = R.ensure_hypotheses(load_cfg())
    lab = Lab()
    print(f"lab_bot start pid={os.getpid()} at={brt_iso()} created={created} active={sum(1 for e in lab.reg['portfolios'].values() if e.get('status')=='active')}", flush=True)
    started = time.time()
    while not STOP:
        t0 = time.time()
        try:
            act = lab.cycle(); lab.cycles += 1
            snap = {}
            for e in act:
                p = lab.port(e["name"]); px = mark(e["asset"], 600)
                snap[e["name"]] = {"equity_usd": equity(p, px) if px else None, "trades": p["trade_count"],
                                   "usdt": p["usdt"], "qty": qty(p), "open_order": bool(p.get("open_order")),
                                   "paused": e["_paused"], "kind": e["kind"], "hyp": e.get("hyp"),
                                   "parent": e.get("parent"), "lineage": e.get("lineage")}
            write_json(STATUS, {"ok": True, "ts": time.time(), "ts_brt": brt_iso(), "pid": os.getpid(),
                                "cycles": lab.cycles, "errors": lab.errors, "processed_source_decisions": lab.processed,
                                "finished": False, "paper_only": True, "uptime_seconds": round(time.time() - started, 1),
                                "portfolios": snap})
        except Exception as ex:
            lab.errors += 1
            print(f"lab cycle error: {ex}\n{traceback.format_exc()}", flush=True)
            write_json(STATUS, {"ok": False, "error": str(ex), "ts_brt": brt_iso(), "pid": os.getpid(),
                                "cycles": lab.cycles, "errors": lab.errors, "finished": False})
        if lab.cycles % 20 == 1:
            print(f"lab cycle={lab.cycles} processed={lab.processed} errors={lab.errors}", flush=True)
        end = time.time() + max(1.0, 15 - (time.time() - t0))
        while time.time() < end and not STOP:
            time.sleep(0.5)
    print("lab_bot stopped", flush=True)


if __name__ == "__main__":
    main()
