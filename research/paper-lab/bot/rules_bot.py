#!/usr/bin/env python3
"""Paper rule-based portfolios (SOL grid/RSI + meme regime/donch). Simulation only.

Também executa os forks de regras do registry do lab (classe RuleForks): mesmos sinais, parâmetros do fork."""
from __future__ import annotations
import json, os, signal as osignal, sys, time, traceback, uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # código do lab (não PAPER_LAB_ROOT)
from bot.paths import ROOT, LAB_DIR  # noqa: E402

from bot.lib import (
    brt_now, brt_iso, load_cfg, assert_no_keys, jupiter_quote, fetch_sol_price,
    fetch_meme_prices, append_jsonl, write_json, read_jsonl, USDT, SOL,
)
from bot.rules_engine import (
    CandleBook, grid_signal, rsi_signal, MEME_GATE_PAIRS, load_rule_enabled, meme_rule_signal, RULE_KIND,
)
from bot import params as P
from bot import lab_registry as R

STOP = False

def _sig(*_a):
    global STOP
    STOP = True


def new_sol_portfolio(path: Path, sol: float, usdt: float, price: float, name: str) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    data = {
        "name": name, "asset_mode": "sol", "sol": sol, "usdt": usdt, "token": 0.0,
        "start_sol": sol, "start_usdt": usdt, "start_price": price,
        "benchmark_buy_hold": {"sol": sol, "usdt": usdt},
        "benchmark_all_usdt": {"usdt": usdt + sol * price},
        "realized_pnl_usdt": 0.0, "fees_paid_usdt": 0.0, "fees_paid_sol": 0.0,
        "trade_count": 0, "last_trade_ts": None, "trade_timestamps": [],
        "position": "held" if sol > 1e-9 else "flat", "recent_pnl_mood": "neutral",
        "created_ts": time.time(), "strategy": f"rule:{name}",
        "rule_state": {},
    }
    write_json(path, data)
    return data


def new_meme_portfolio(path: Path, usdt: float, price: float, name: str) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    bh_token = (usdt / price) if price > 0 else 0.0
    data = {
        "name": name, "asset_mode": "token", "sol": 0.0, "usdt": usdt, "token": 0.0,
        "start_sol": 0.0, "start_usdt": usdt, "start_token": 0.0, "start_price": price,
        "benchmark_buy_hold": {"token": bh_token, "usdt": 0.0},
        "benchmark_all_usdt": {"usdt": usdt},
        "realized_pnl_usdt": 0.0, "fees_paid_usdt": 0.0, "fees_paid_sol": 0.0,
        "trade_count": 0, "last_trade_ts": None, "trade_timestamps": [],
        "position": "flat", "recent_pnl_mood": "neutral", "created_ts": time.time(),
        "strategy": f"rule:{name}", "rule_state": {},
    }
    write_json(path, data)
    return data


def equity_sol(d, price):
    return float(d["usdt"]) + float(d["sol"]) * price


def equity_meme(d, price):
    return float(d["usdt"]) + float(d.get("token") or 0) * price


def bh_sol(d, price):
    bh = d["benchmark_buy_hold"]
    return float(bh["usdt"]) + float(bh["sol"]) * price


def bh_meme(d, price):
    bh = d["benchmark_buy_hold"]
    return float(bh.get("usdt") or 0) + float(bh.get("token") or 0) * price


def _cooldown_ok(pdata, gcfg, now):
    last = pdata.get("last_trade_ts")
    if last is not None and now - float(last) < float(gcfg["cooldown_seconds"]):
        return False, "cooldown"
    stamps = [float(t) for t in pdata.get("trade_timestamps") or []]
    if len([t for t in stamps if t >= now - 3600]) >= int(gcfg["max_trades_per_hour"]):
        return False, "max_trades_hour"
    return True, None


def sim_trade_sol(side, data, gcfg, fees, market, price, decision_id, trades_log, strategy_tag):
    extra = float(fees.get("extra_slippage_bps", 5))
    net_sol = float(fees.get("assumed_network_fee_sol", 5e-6))
    net_usdt = net_sol * price
    slip = int(market.get("slippage_bps", 50))
    pnl = 0.0
    q = None
    fill_meta = {}
    if side == "buy":
        usdt_in = float(data["usdt"]) * float(gcfg["buy_fraction_usdt"])
        if usdt_in < float(gcfg["min_usdt_trade"]):
            return None
        try:
            q = jupiter_quote({"market": market}, USDT, SOL, usdt_in, 6, slip)
            out = float(q["outAmount"]) / 1e9
            out_net = max(0.0, out - out * (extra / 10000.0) - net_sol)
            fill_meta = {"fill_mode": q.get("_fill_mode", "jupiter_quote"), "quote_source": q.get("_quote_source")}
        except Exception as e:
            px = price * (1.0 + (slip + extra) / 10000.0)
            out_net = max(0.0, usdt_in / px - net_sol)
            fill_meta = {"fill_mode": "mark", "mark_price": price, "effective_price": px,
                         "quote_error": f"{type(e).__name__}:{e}"}
        fee = usdt_in * (extra / 10000.0) + net_usdt
        data["usdt"] -= usdt_in
        data["sol"] = float(data["sol"]) + out_net
        data["fees_paid_usdt"] += fee
        data["fees_paid_sol"] += net_sol
        fill = {"side": "buy", "usdt_in": usdt_in, "sol_out_net": out_net, "fee_usdt": fee, **fill_meta}
    else:
        sol_in = float(data["sol"])
        if sol_in < float(gcfg["min_sol_trade"]):
            return None
        to_swap = max(0.0, sol_in - net_sol)
        if to_swap < float(gcfg["min_sol_trade"]):
            return None
        try:
            q = jupiter_quote({"market": market}, SOL, USDT, to_swap, 9, slip)
            out = float(q["outAmount"]) / 1e6
            out_net = max(0.0, out - out * (extra / 10000.0))
            fill_meta = {"fill_mode": q.get("_fill_mode", "jupiter_quote"), "quote_source": q.get("_quote_source")}
        except Exception as e:
            px = price * (1.0 - (slip + extra) / 10000.0)
            out_net = max(0.0, to_swap * px - net_usdt)
            fill_meta = {"fill_mode": "mark", "mark_price": price, "effective_price": px,
                         "quote_error": f"{type(e).__name__}:{e}"}
        fee = float(to_swap * price) * (extra / 10000.0) + net_usdt
        pnl = out_net - to_swap * price
        data["sol"] = 0.0
        data["usdt"] += out_net
        data["fees_paid_usdt"] += fee
        data["fees_paid_sol"] += net_sol
        data["realized_pnl_usdt"] += pnl
        fill = {"side": "sell", "sol_in": to_swap, "usdt_out_net": out_net, "fee_usdt": fee,
                "approx_pnl": pnl, **fill_meta}
    now = time.time()
    data["trade_count"] += 1
    data["last_trade_ts"] = now
    data["trade_timestamps"] = (data.get("trade_timestamps") or [])[-99:] + [now]
    data["position"] = "held" if float(data["sol"]) > 1e-6 else ("sold" if data["trade_count"] > 0 else "flat")
    data["recent_pnl_mood"] = "buoyed" if pnl > 0.05 else ("stung" if pnl < -0.05 else "neutral")
    quote_info = None
    if q:
        quote_info = {
            "inAmount": q.get("inAmount"), "outAmount": q.get("outAmount"),
            "priceImpactPct": q.get("priceImpactPct"),
            "routeLabels": [r.get("swapInfo", {}).get("label") for r in (q.get("routePlan") or [])],
        }
    else:
        quote_info = {"fill_mode": fill_meta.get("fill_mode"), "mark_price": price}
    row = {
        "ts": now, "ts_brt": brt_iso(now), "portfolio": data["name"], "decision_id": decision_id,
        "side": side, "price_mark": price, "fill": fill, "quote": quote_info,
        "paper_only": True, "signed": False, "sent": False,
        "strategy": strategy_tag,
        "portfolio_after": {"sol": data["sol"], "usdt": data["usdt"], "equity": equity_sol(data, price)},
    }
    append_jsonl(trades_log, row)
    return row


def sim_trade_meme(side, data, gcfg, fees, market, price, decision_id, trades_log,
                   mint, decimals, sol_usd, strategy_tag):
    extra = float(fees.get("extra_slippage_bps", 5))
    net_sol = float(fees.get("assumed_network_fee_sol", 5e-6))
    net_usdt = net_sol * sol_usd
    slip = max(50, int(market.get("slippage_bps", 50)))
    pnl = 0.0
    data.setdefault("token", 0.0)
    q = None
    fill_meta = {}
    if side == "buy":
        usdt_in = float(data["usdt"]) * float(gcfg["buy_fraction_usdt"])
        if usdt_in < float(gcfg["min_usdt_trade"]):
            return None
        usdt_swap = max(0.0, usdt_in - net_usdt)
        try:
            q = jupiter_quote({"market": market}, USDT, mint, usdt_swap, 6, slip)
            out = float(q["outAmount"]) / (10 ** decimals)
            out_net = max(0.0, out - out * (extra / 10000.0))
            fill_meta = {"fill_mode": q.get("_fill_mode", "jupiter_quote"), "quote_source": q.get("_quote_source")}
        except Exception as e:
            px = price * (1.0 + (slip + extra) / 10000.0)
            out_net = usdt_swap / px if px > 0 else 0.0
            fill_meta = {"fill_mode": "mark", "mark_price": price, "effective_price": px,
                         "quote_error": f"{type(e).__name__}:{e}"}
        fee = usdt_in * (extra / 10000.0) + net_usdt
        data["usdt"] -= usdt_in
        data["token"] = float(data["token"]) + out_net
        data["fees_paid_usdt"] += fee
        fill = {"side": "buy", "usdt_in": usdt_in, "token_out_net": out_net, "fee_usdt": fee,
                "mint": mint, **fill_meta}
    else:
        tok = float(data["token"])
        if tok * price < float(gcfg["min_usdt_trade"]):
            return None
        try:
            q = jupiter_quote({"market": market}, mint, USDT, tok, decimals, slip)
            out = float(q["outAmount"]) / 1e6
            out_net = max(0.0, out - out * (extra / 10000.0) - net_usdt)
            fill_meta = {"fill_mode": q.get("_fill_mode", "jupiter_quote"), "quote_source": q.get("_quote_source")}
        except Exception as e:
            px = price * (1.0 - (slip + extra) / 10000.0)
            out_net = max(0.0, tok * px - net_usdt)
            fill_meta = {"fill_mode": "mark", "mark_price": price, "effective_price": px,
                         "quote_error": f"{type(e).__name__}:{e}"}
        fee = float(tok * price) * (extra / 10000.0) + net_usdt
        pnl = out_net - tok * price
        data["token"] = 0.0
        data["usdt"] += out_net
        data["fees_paid_usdt"] += fee
        data["realized_pnl_usdt"] += pnl
        fill = {"side": "sell", "token_in": tok, "usdt_out_net": out_net, "fee_usdt": fee,
                "approx_pnl": pnl, "mint": mint, **fill_meta}
    now = time.time()
    data["trade_count"] += 1
    data["last_trade_ts"] = now
    data["trade_timestamps"] = (data.get("trade_timestamps") or [])[-99:] + [now]
    data["position"] = "held" if float(data["token"]) > 1e-12 else ("sold" if data["trade_count"] > 0 else "flat")
    data["recent_pnl_mood"] = "buoyed" if pnl > 0.05 else ("stung" if pnl < -0.05 else "neutral")
    quote_info = None
    if q:
        quote_info = {
            "inAmount": q.get("inAmount"), "outAmount": q.get("outAmount"),
            "priceImpactPct": q.get("priceImpactPct"),
        }
    else:
        quote_info = {"fill_mode": fill_meta.get("fill_mode"), "mark_price": price}
    row = {
        "ts": now, "ts_brt": brt_iso(now), "portfolio": data["name"], "decision_id": decision_id,
        "side": side, "price_mark": price, "fill": fill, "quote": quote_info,
        "paper_only": True, "signed": False, "sent": False, "strategy": strategy_tag,
        "portfolio_after": {"token": data["token"], "usdt": data["usdt"], "equity": equity_meme(data, price)},
    }
    append_jsonl(trades_log, row)
    return row


def log_decision(path, **kwargs):
    row = {"ts": time.time(), "ts_brt": brt_iso(), **kwargs}
    append_jsonl(path, row)
    return row


class RuleForks:
    """Executor dos forks de regras: entradas do registry do lab com `kind=rule` e pai (`lab_registry.is_rule_fork`).

    Corre no mesmo ciclo e com o mesmo CandleBook dos originais, com os mesmos sinais (grid_signal, rsi_signal,
    meme_rule_signal) e os mesmos portões (cooldown, trades/h, mínimos, teto de exposição), mas com os parâmetros
    efetivos do fork (params.json: pai sem overlay + diff do registry + portfolios.<fork> + overlay do fork).
    Extras só dos forks: `exits` (TP/SL/trailing a cada ciclo, no preço de marcação; reentrada bloqueada
    `reentry_cooldown_min`) e `regime_filter` (compras só com SOL EMA 12 > 26).

    Estado em data/lab/portfolios/<fork>.json (criado por create_fork com os saldos atuais do pai), equity em
    data/lab/equity/<fork>.jsonl, trades nos logs dos originais (trades.jsonl / meme_trades.jsonl, portfolio=<fork>),
    decisões em logs/lab_decisions.jsonl — o mesmo formato dos forks do lab_bot (catalog, veredito, resumo, dashboard).
    Recarrega o registry por mtime. Fail-closed: parâmetros inválidos (erros do resolver), estado em falta ou erro
    interno → hold, registado (sem nunca afetar os originais)."""

    EQ_EVERY = 60.0

    def __init__(self, log=print):
        self.log = log
        self._key = ("never",)
        self.reg: dict = {"portfolios": {}, "lineages": {}}
        self.entries: dict = {}
        self.ports: dict = {}
        self.last_bar: dict = {}
        self.last_eq: dict = {}
        self._warned: dict = {}
        self.trades_sol = ROOT / "logs" / "trades.jsonl"
        self.trades_meme = ROOT / "logs" / "meme_trades.jsonl"
        self.decisions = ROOT / "logs" / "lab_decisions.jsonl"

    @staticmethod
    def _reg_key():
        try:
            st = R.REG.stat()
            return (st.st_mtime_ns, st.st_size)
        except FileNotFoundError:
            return None

    def refresh(self, force: bool = False) -> bool:
        """Relê o registry se mudou (mtime/tamanho). True se recarregou."""
        k = self._reg_key()
        if not force and k == self._key:
            return False
        reg = R.load()
        reg.pop("_mtime", None)
        self._key = k
        self.reg = reg
        new = {n: e for n, e in (reg.get("portfolios") or {}).items()
               if R.is_rule_fork(e) and e.get("status", "active") == "active"}
        added = sorted(set(new) - set(self.entries))
        self.ports = {}  # relê o estado do disco depois de uma mudança no registry
        self.entries = new
        if added:
            self.log(f"rules_bot: forks de regra ativos +{added} (total {len(new)})", flush=True)
        return True

    def _warn(self, name, msg):
        if self._warned.get(name) != msg:
            self._warned[name] = msg
            self.log(f"rules_bot fork {name}: {msg}", flush=True)

    def port(self, name):
        if name not in self.ports:
            self.ports[name] = json.loads(R.port_path(name).read_text())
        return self.ports[name]

    def _log_eq(self, name, port, px, force=False):
        now = time.time()
        if not force and now - self.last_eq.get(name, 0.0) < self.EQ_EVERY:
            return
        self.last_eq[name] = now
        sol_mode = port.get("asset_mode", "sol") == "sol"
        append_jsonl(R.eq_path(name), {
            "ts": now, "price": px, "sol": port.get("sol", 0.0), "token": port.get("token", 0.0), "usdt": port["usdt"],
            "equity": equity_sol(port, px) if sol_mode else equity_meme(port, px),
            "bh_equity": bh_sol(port, px) if sol_mode else bh_meme(port, px),
            "all_usdt_equity": float(port["benchmark_all_usdt"]["usdt"]), "trade_count": port["trade_count"],
            "portfolio": name})

    def step(self, book, *, ind, sol_px, marks, allow, overlay, rules_cfg, cfg, token_by_sym, bull, now=None) -> dict:
        """Um ciclo para todos os forks de regra. `ind` = book.sol_indicators() (12/26/14) do ciclo; `bull(f, s)` = regime
        de SOL com EMAs f/s. Devolve o resumo por fork para data/rules/status.json."""
        self.refresh()
        cache: dict = {}
        out = {}
        for name, e in sorted(self.entries.items()):
            try:
                out[name] = self._one(name, e, book, ind, float(sol_px), marks or {}, allow, overlay or {}, rules_cfg or {},
                                      cfg, token_by_sym or {}, bull, cache, now if now is not None else time.time())
            except Exception as ex:
                self._warn(name, f"erro (hold): {type(ex).__name__}: {ex}")
                out[name] = {"error": f"{type(ex).__name__}: {ex}", "last_signal": "hold", "parent": e.get("parent")}
        return out

    def _one(self, name, e, book, ind, sol_px, marks, allow, overlay, rules_cfg, cfg, token_by_sym, bull, cache, now):
        kind = RULE_KIND.get(e.get("test_type"))
        asset = e.get("asset") or "SOL"
        tag = e.get("strategy") or f"fork:{name}"
        port = self.port(name)
        eff = P.effective(name, meta=e, registry=self.reg)
        perr = P.STORE.errors.get(name)
        rp = eff.get("rule") or {}
        gcfg = eff["gates"]
        ex = eff.get("exits") or {}
        fees, market = P.fees_market(eff, cfg)
        bad = None
        if perr:
            bad = "params_invalidos"
            self._warn(name, f"parâmetros inválidos → hold: {'; '.join(perr[:3])}")
        elif eff.get("failsafe") or not kind or not rp:
            bad = "params_invalidos"
            self._warn(name, f"sem parâmetros de regra válidos (tipo {e.get('test_type')!r}) → hold")
        enabled = load_rule_enabled(overlay, name, rules_cfg) and not eff.get("paused")

        # preço de marcação e barra fechada de 1 h que conta para este fork
        mint, decs, mi = None, 6, {}
        if asset == "SOL":
            px = sol_px
            bar_ts, ready = ind.get("bar_ts"), bool(ind.get("ready"))
        else:
            mark = marks.get(asset) or {}
            px = float(mark.get("price_usd") or 0)
            if px <= 0 and book.memes.get(asset):
                px = float(book.memes[asset][-1]["close"])
            tmeta = token_by_sym.get(asset) or {}
            mint, decs = tmeta.get("mint"), int(tmeta.get("decimals") or 6)
            n_d = int(rp.get("donchian", 20))
            ck = ("meme", asset, n_d)
            if ck not in cache:
                cache[ck] = book.meme_indicators(asset, donchian=n_d)
            mi = cache[ck]
            bar_ts, ready = mi.get("bar_ts"), bool(mi.get("ready"))
            if not mint:
                bad = bad or "sem_mint"
        if px <= 0:
            return {"last_signal": "hold", "gate_reasons": ["sem_preco"], "parent": e.get("parent"), "strategy": tag}

        sol_mode = asset == "SOL"
        qty_of = (lambda: float(port.get("sol") or 0)) if sol_mode else (lambda: float(port.get("token") or 0))

        def trade(side, g):
            before = qty_of()
            if sol_mode:
                tr = sim_trade_sol(side, port, g, fees, market, px, did, self.trades_sol, tag)
            else:
                tr = sim_trade_meme(side, port, g, fees, market, px, did, self.trades_meme, mint, decs, sol_px, tag)
            if tr:
                P.track_fill(port, side, before, tr["fill"], px)
            return tr

        def log_dec(chosen, final, reasons, traded, extra=None):
            eq = equity_sol(port, px) if sol_mode else equity_meme(port, px)
            append_jsonl(self.decisions, {
                "ts": time.time(), "ts_brt": brt_iso(), "portfolio": name, "strategy": tag, "asset": asset,
                "model": "rule", "rule": kind, "parent": e.get("parent"), "decision_id": did, "chosen_action": chosen,
                "confidence": None, "final_action": final, "gate_reasons": reasons, "traded": traded, "price_usd": px,
                "equity_usd": eq, "bar_ts": bar_ts, "params_rule": {k: v for k, v in rp.items() if k != "timeframe"},
                **(extra or {})})

        dirty = False
        signal, reasons, traded = "hold", [], False
        did = str(uuid.uuid4())

        # 1) saídas (só forks com exits.enabled): a cada ciclo, no preço de marcação; ignoram cooldown (como no lab_bot)
        if allow and enabled and not bad and ex.get("enabled") and qty_of() * px >= 1.0:
            before_peak = port.get("peak_price")
            why = P.check_exit(port, ex, px)
            dirty = dirty or port.get("peak_price") != before_peak
            if why:
                tr = trade("sell", gcfg)
                traded = tr is not None
                if traded:
                    port["reentry_block_until"] = now + 60 * float(ex.get("reentry_cooldown_min", 30))
                    if kind == "grid":
                        port["rule_state"] = dict(port.get("rule_state") or {}, buys_open=0, ref=px)
                log_dec("sell", "sell" if traded else "hold", [why] + ([] if traded else ["sim_trade_none"]), traded,
                        {"exit": why, "entry_price": port.get("entry_price"), "peak_price": port.get("peak_price")})
                signal, reasons, dirty = ("sell" if traded else "hold"), [why], True
                did = str(uuid.uuid4())

        # 2) sinal da regra numa barra de 1 h nova, fechada depois do arranque do rules_bot e da criação do fork
        new_bar = ready and bar_ts is not None and bar_ts != self.last_bar.get(name)
        start = max(float(book.started_ts or 0), float(port.get("created_ts") or 0))
        can = bool(allow and new_bar and (bar_ts + 3600) > start)
        if can and not traded:
            self.last_bar[name] = bar_ts
            dirty = True
            ind_x = {"bar_ts": bar_ts}
            chosen = "hold"
            if not enabled:
                reasons = ["paused_or_disabled"]
            elif bad:
                reasons = [bad]
            else:
                reasons = []
                if kind == "grid":
                    rs = dict(port.get("rule_state") or {})
                    if not rs:
                        rs = {"ref": float(ind["close"]), "buys_open": 0}
                    chosen, rs2 = grid_signal(rs, float(ind["close"]), grid_pct=float(rp["grid_pct"]), levels=int(rp["levels"]))
                    port["rule_state"] = rs2
                    ind_x["grid"] = dict(rs2)
                elif kind == "rsi":
                    n = int(rp["rsi_period"])
                    ck = ("rsi", n)
                    if ck not in cache:
                        cache[ck] = ind if n == 14 else book.sol_indicators(rsi_period=n)
                    ir = cache[ck]
                    chosen = rsi_signal(ir.get("rsi"), ir.get("rsi_prev"), float(rp["lo"]), float(rp["hi"]))
                    ind_x.update(rsi=ir.get("rsi"), rsi_prev=ir.get("rsi_prev"))
                else:
                    p_bull = bull(int(rp["ema_fast"]), int(rp["ema_slow"]))
                    held = float(port.get("token") or 0) > 1e-12
                    chosen, rr = meme_rule_signal(kind, held, p_bull, mi.get("donchian20_signal") or "hold")
                    reasons += rr
                    ind_x.update(sol_regime_bull=p_bull, donch=mi.get("donchian20_signal"))
                final = chosen
                if final == "buy" and (eff.get("regime_filter") or {}).get("enabled"):
                    final, rr = P.regime_block(eff, final, ind.get("sol_regime_bull") if ind.get("ready") else None)
                    reasons += rr
                if final == "buy" and ex.get("enabled") and now < float(port.get("reentry_block_until") or 0):
                    final = "hold"; reasons.append("reentry_cooldown")
                ok, why = _cooldown_ok(port, gcfg, time.time())
                if final in ("buy", "sell") and not ok:
                    final = "hold"; reasons.append(why)
                if final == "buy" and float(port["usdt"]) * float(gcfg["buy_fraction_usdt"]) < float(gcfg["min_usdt_trade"]):
                    final = "hold"; reasons.append("insufficient_usdt")
                if final == "sell":
                    if sol_mode and qty_of() < float(gcfg["min_sol_trade"]):
                        final = "hold"; reasons.append("insufficient_sol")
                    elif not sol_mode and qty_of() * px < float(gcfg["min_usdt_trade"]):
                        final = "hold"; reasons.append("insufficient_token")
                g_trade = gcfg
                if final == "buy":
                    g_trade, why = P.cap_buy(gcfg, port, px)
                    if why:
                        final = "hold"; reasons.append(why)
                if final in ("buy", "sell"):
                    try:
                        traded = trade(final, g_trade) is not None
                    except Exception as ex_:
                        traded = False; reasons.append(f"sim_err:{type(ex_).__name__}")
                    if not traded:
                        reasons.append("sim_trade_none"); final = "hold"
                    elif kind == "grid":
                        rs = port["rule_state"]
                        if final == "buy":
                            rs["buys_open"] = int(rs.get("buys_open") or 0) + 1
                        else:
                            rs["buys_open"] = 0
                            rs["ref"] = float(ind["close"])
                signal = final
            log_dec(chosen, signal, reasons, traded, {"indicators": ind_x})
        elif can and traded:
            self.last_bar[name] = bar_ts  # a saída já operou neste ciclo; a barra fica consumida

        if dirty or traded:
            write_json(R.port_path(name), port)
        self._log_eq(name, port, px, force=traded)
        eq = equity_sol(port, px) if sol_mode else equity_meme(port, px)
        return {"equity_usd": eq, "usdt": port["usdt"], ("sol" if sol_mode else "token"): qty_of(),
                "trades": port["trade_count"], "last_signal": signal, "position": port.get("position"),
                "gate_reasons": reasons, "bh_equity": bh_sol(port, px) if sol_mode else bh_meme(port, px),
                "strategy": tag, "parent": e.get("parent"), "lineage": e.get("lineage"), "asset": asset,
                "rule": {k: v for k, v in rp.items() if k != "timeframe"}, "params_ok": not bad}


def main() -> int:
    osignal.signal(osignal.SIGTERM, _sig)
    osignal.signal(osignal.SIGINT, _sig)
    cfg = load_cfg()
    assert_no_keys(cfg)
    rules_cfg = cfg.get("rule_strategies") or {}
    cycle = float(rules_cfg.get("cycle_seconds", 30))
    end_at = datetime.fromisoformat(cfg["end_at_brt"])
    # Portões e parâmetros das regras por portfólio: params.json (types.rule_*), via bot/params.py.
    bal = cfg["starting_balances"]
    meme_cfg = json.loads((ROOT / "memecoins.json").read_text())
    tokens = meme_cfg["tokens"]
    start_usdt_meme = float(meme_cfg.get("start_usdt_each", 1000.0))
    max_age = float(cfg["market"].get("max_price_age_seconds", 120))

    decisions_log = ROOT / "logs" / "decisions.jsonl"
    trades_log = ROOT / "logs" / "trades.jsonl"
    meme_dec_log = ROOT / "logs" / "meme_decisions.jsonl"
    meme_tr_log = ROOT / "logs" / "meme_trades.jsonl"
    status_path = ROOT / "data" / "rules" / "status.json"
    port_dir = ROOT / "data"
    meme_port = ROOT / "data" / "meme" / "portfolios"
    meme_eq = ROOT / "data" / "meme" / "equity"
    prices_dir = ROOT / "data" / "meme" / "prices"
    for d in (status_path.parent, meme_port, meme_eq, prices_dir, ROOT / "data" / "rules" / "equity"):
        d.mkdir(parents=True, exist_ok=True)

    print(f"rules_bot warm-up starting pid={os.getpid()}", flush=True)
    book = CandleBook()
    warm = book.warm_up()
    print(f"rules_bot warm-up done: {json.dumps(warm, default=str)}", flush=True)

    prices_log = ROOT / "data" / "prices.jsonl"
    try:
        prow = fetch_sol_price(cfg, prices_log)
        sol_px = float(prow["price_usd"])
    except Exception as e:
        sol_px = float(book.sol[-1]["close"]) if book.sol else 100.0
        print(f"rules_bot sol price fallback close={sol_px}: {e}", flush=True)

    start_brt = brt_iso()
    # SOL rule portfolios
    grid = new_sol_portfolio(port_dir / "portfolio_grid_sol_2pct.json",
                             bal["sol"], bal["usdt"], sol_px, "grid_sol_2pct")
    rsi_p = new_sol_portfolio(port_dir / "portfolio_rsi_sol_1h.json",
                              bal["sol"], bal["usdt"], sol_px, "rsi_sol_1h")
    for p, tag in ((grid, "grid_sol_2pct"), (rsi_p, "rsi_sol_1h")):
        if "started_brt" not in p:
            p["started_brt"] = start_brt
            p["strategy"] = f"rule:{tag}"
            write_json(port_dir / f"portfolio_{tag}.json", p)
    if not grid.get("rule_state"):
        ind = book.sol_indicators()
        grid["rule_state"] = {"ref": float(ind.get("close") or sol_px), "buys_open": 0}
        write_json(port_dir / "portfolio_grid_sol_2pct.json", grid)

    # Meme rule portfolios
    marks = fetch_meme_prices(cfg, tokens, prices_dir, max_age=max_age)
    regime_ports = {}
    donch_ports = {}
    full_regime_ports = {}
    full_donch_ports = {}
    token_by_sym = {t["symbol"]: t for t in tokens}
    for t in tokens:
        sym = t["symbol"]
        px = float((marks.get(sym) or {}).get("price_usd") or 0)
        if px <= 0 and book.memes.get(sym):
            px = float(book.memes[sym][-1]["close"])
        if px <= 0:
            continue
        rn = f"{sym}_rule_regime"
        dn = f"{sym}_rule_donch_regime"
        rp = new_meme_portfolio(meme_port / f"{rn}.json", start_usdt_meme, px, rn)
        dp = new_meme_portfolio(meme_port / f"{dn}.json", start_usdt_meme, px, dn)
        for p, n in ((rp, rn), (dp, dn)):
            if "started_brt" not in p:
                p["started_brt"] = start_brt
                p["strategy"] = f"rule:{n}"
                write_json(meme_port / f"{n}.json", p)
        regime_ports[sym] = rp
        donch_ports[sym] = dp
        # Faithful research variants (2026-09-24 evening): 100% in when signal on, 100% out otherwise.
        for n, store in ((f"{sym}_rule_regime_full", full_regime_ports), (f"{sym}_rule_donch_regime_full", full_donch_ports)):
            fp = new_meme_portfolio(meme_port / f"{n}.json", start_usdt_meme, px, n)
            if "started_brt" not in fp:
                fp["started_brt"] = start_brt
                fp["strategy"] = f"rule:{n}"
                fp["sizing"] = "full"
                write_json(meme_port / f"{n}.json", fp)
            store[sym] = fp

    # Forks de regras (registry do lab): mesmos sinais com parâmetros próprios; hot reload do registry por mtime.
    forks = RuleForks()
    forks.refresh(force=True)
    print(f"rules_bot forks de regra: {sorted(forks.entries) or 'nenhum'}", flush=True)

    # last acted bar tracking (don't re-act same bar)
    last_sol_bar = None
    last_meme_bar = {s: None for s in MEME_GATE_PAIRS}

    cycles = errors = 0
    started = time.time()
    finished = False
    # Print initial indicator state
    ind0 = book.sol_indicators()
    print(
        f"rules_bot start pid={os.getpid()} at={start_brt} "
        f"SOL close={ind0.get('close')} ema12={ind0.get('ema12')} ema26={ind0.get('ema26')} "
        f"rsi={ind0.get('rsi')} regime_bull={ind0.get('sol_regime_bull')} "
        f"grid_ref={grid['rule_state'].get('ref')} buys_open={grid['rule_state'].get('buys_open')}",
        flush=True,
    )
    for sym in list(regime_ports):
        mi = book.meme_indicators(sym)
        print(f"  meme {sym}: close={mi.get('close')} donch={mi.get('donchian20_signal')} bars={mi.get('n_bars')}", flush=True)

    while not STOP:
        t0 = time.time()
        now = brt_now()
        allow = now < end_at
        if now >= end_at and not finished:
            finished = True
            print("rules_bot end window", flush=True)
        try:
            overlay = P.STORE.overlay()
            if (overlay.get("bots") or {}).get("rules_paused"):
                allow = False

            # refresh closed bars
            book.refresh_closed()
            ind = book.sol_indicators()
            try:
                prow = fetch_sol_price(cfg, prices_log)
                sol_px = float(prow["price_usd"])
                sol_src = prow.get("source")
            except Exception:
                sol_px = float(ind.get("close") or sol_px)
                sol_src = "candle_close"
            marks = fetch_meme_prices(cfg, tokens, prices_dir, max_age=max_age)
            sol_usd = sol_px

            bar_ts = ind.get("bar_ts")
            new_sol_bar = bar_ts is not None and bar_ts != last_sol_bar and ind.get("ready")
            # Only trade if bar closed AFTER warm-up start
            can_trade_sol = (
                allow and new_sol_bar and bar_ts is not None
                and (bar_ts + 3600) > book.started_ts
            )

            snap_ports = {}

            # ---- SOL GRID ----
            strat = "grid_sol_2pct"
            tag = f"rule:{strat}"
            eff = P.effective(strat)
            gcfg, rp = eff["gates"], eff.get("rule") or {}
            fees, market = P.fees_market(eff, cfg)
            enabled = load_rule_enabled(overlay, strat, rules_cfg) and not eff["paused"]
            signal = "hold"
            reasons = []
            traded = False
            did = str(uuid.uuid4())
            if not enabled:
                reasons.append("paused_or_disabled")
            elif not ind.get("ready"):
                reasons.append("indicators_not_ready")
            elif not can_trade_sol:
                reasons.append("waiting_new_bar_after_start" if allow else "run_ended")
                signal = "hold"
            else:
                rs = dict(grid.get("rule_state") or {})
                # evaluate on closed bar close
                px_bar = float(ind["close"])
                signal, rs2 = grid_signal(rs, px_bar, grid_pct=float(rp.get("grid_pct", 0.02)), levels=int(rp.get("levels", 4)))
                grid["rule_state"] = rs2
                ok, why = _cooldown_ok(grid, gcfg, time.time())
                final = signal
                if signal in ("buy", "sell") and not ok:
                    final = "hold"
                    reasons.append(why)
                if final == "buy" and float(grid["usdt"]) * float(gcfg["buy_fraction_usdt"]) < float(gcfg["min_usdt_trade"]):
                    final = "hold"; reasons.append("insufficient_usdt")
                if final == "sell" and float(grid["sol"]) < float(gcfg["min_sol_trade"]):
                    final = "hold"; reasons.append("insufficient_sol")
                g_trade = gcfg
                if final == "buy":
                    g_trade, why = P.cap_buy(gcfg, grid, sol_px)
                    if why:
                        final = "hold"; reasons.append(why)
                if final in ("buy", "sell"):
                    try:
                        tr = sim_trade_sol(final, grid, g_trade, fees, market,
                                           sol_px, did, trades_log, tag)
                        traded = tr is not None
                        if traded:
                            if final == "buy":
                                grid["rule_state"]["buys_open"] = int(grid["rule_state"].get("buys_open") or 0) + 1
                            else:
                                grid["rule_state"]["buys_open"] = 0
                                grid["rule_state"]["ref"] = float(ind["close"])
                        else:
                            reasons.append("sim_trade_none")
                            final = "hold"
                    except Exception as e:
                        reasons.append(f"sim_err:{type(e).__name__}")
                        final = "hold"
                signal = final
            write_json(port_dir / "portfolio_grid_sol_2pct.json", grid)
            eq = equity_sol(grid, sol_px)
            append_jsonl(ROOT / "data" / "equity_grid_sol_2pct.jsonl", {
                "ts": time.time(), "price": sol_px, "sol": grid["sol"], "usdt": grid["usdt"],
                "equity": eq, "bh_equity": bh_sol(grid, sol_px),
                "all_usdt_equity": float(grid["benchmark_all_usdt"]["usdt"]),
                "trade_count": grid["trade_count"], "portfolio": strat,
            })
            log_decision(decisions_log, decision_id=did, portfolio=strat, strategy=tag,
                         chosen_action=signal, final_action=signal, gate_reasons=reasons,
                         confidence=1.0, skip_noul=0.0, traded=traded,
                         price_usd=sol_px, price_source=sol_src, model="rule",
                         indicators={"ema12": ind.get("ema12"), "ema26": ind.get("ema26"),
                                     "rsi": ind.get("rsi"), "bar_ts": bar_ts,
                                     "grid": grid.get("rule_state")},
                         equity_usd=eq, sol=grid["sol"], usdt=grid["usdt"],
                         bar_acted=bool(can_trade_sol and enabled))
            snap_ports[strat] = {
                "sol": grid["sol"], "usdt": grid["usdt"], "equity_usd": eq,
                "trades": grid["trade_count"], "last_signal": signal,
                "position": grid["position"], "gate_reasons": reasons,
                "indicators": {"grid": grid.get("rule_state"), "close_1h": ind.get("close")},
                "bh_equity": bh_sol(grid, sol_px), "strategy": tag,
            }

            # ---- SOL RSI ----
            strat = "rsi_sol_1h"
            tag = f"rule:{strat}"
            eff = P.effective(strat)
            gcfg, rp = eff["gates"], eff.get("rule") or {}
            fees, market = P.fees_market(eff, cfg)
            enabled = load_rule_enabled(overlay, strat, rules_cfg) and not eff["paused"]
            rsi_n = int(rp.get("rsi_period", 14))
            ind_rsi = ind if rsi_n == 14 else book.sol_indicators(rsi_period=rsi_n)
            signal = "hold"
            reasons = []
            traded = False
            did = str(uuid.uuid4())
            if not enabled:
                reasons.append("paused_or_disabled")
            elif not ind.get("ready"):
                reasons.append("indicators_not_ready")
            elif not can_trade_sol:
                reasons.append("waiting_new_bar_after_start" if allow else "run_ended")
            else:
                signal = rsi_signal(ind_rsi.get("rsi"), ind_rsi.get("rsi_prev"), float(rp.get("lo", 30)), float(rp.get("hi", 70)))
                final = signal
                ok, why = _cooldown_ok(rsi_p, gcfg, time.time())
                if final in ("buy", "sell") and not ok:
                    final = "hold"; reasons.append(why)
                if final == "buy" and float(rsi_p["usdt"]) * float(gcfg["buy_fraction_usdt"]) < float(gcfg["min_usdt_trade"]):
                    final = "hold"; reasons.append("insufficient_usdt")
                if final == "sell" and float(rsi_p["sol"]) < float(gcfg["min_sol_trade"]):
                    final = "hold"; reasons.append("insufficient_sol")
                g_trade = gcfg
                if final == "buy":
                    g_trade, why = P.cap_buy(gcfg, rsi_p, sol_px)
                    if why:
                        final = "hold"; reasons.append(why)
                if final in ("buy", "sell"):
                    try:
                        tr = sim_trade_sol(final, rsi_p, g_trade, fees, market,
                                           sol_px, did, trades_log, tag)
                        traded = tr is not None
                        if not traded:
                            final = "hold"; reasons.append("sim_trade_none")
                    except Exception as e:
                        final = "hold"; reasons.append(f"sim_err:{type(e).__name__}")
                signal = final
            write_json(port_dir / "portfolio_rsi_sol_1h.json", rsi_p)
            eq = equity_sol(rsi_p, sol_px)
            append_jsonl(ROOT / "data" / "equity_rsi_sol_1h.jsonl", {
                "ts": time.time(), "price": sol_px, "sol": rsi_p["sol"], "usdt": rsi_p["usdt"],
                "equity": eq, "bh_equity": bh_sol(rsi_p, sol_px),
                "all_usdt_equity": float(rsi_p["benchmark_all_usdt"]["usdt"]),
                "trade_count": rsi_p["trade_count"], "portfolio": strat,
            })
            log_decision(decisions_log, decision_id=did, portfolio=strat, strategy=tag,
                         chosen_action=signal, final_action=signal, gate_reasons=reasons,
                         confidence=1.0, skip_noul=0.0, traded=traded,
                         price_usd=sol_px, price_source=sol_src, model="rule",
                         indicators={"rsi": ind_rsi.get("rsi"), "rsi_prev": ind_rsi.get("rsi_prev"), "bar_ts": bar_ts,
                                     "rsi_period": rsi_n},
                         equity_usd=eq, sol=rsi_p["sol"], usdt=rsi_p["usdt"],
                         bar_acted=bool(can_trade_sol and enabled))
            snap_ports[strat] = {
                "sol": rsi_p["sol"], "usdt": rsi_p["usdt"], "equity_usd": eq,
                "trades": rsi_p["trade_count"], "last_signal": signal,
                "position": rsi_p["position"], "gate_reasons": reasons,
                "indicators": {"rsi": ind.get("rsi"), "rsi_prev": ind.get("rsi_prev")},
                "bh_equity": bh_sol(rsi_p, sol_px), "strategy": tag,
            }

            if can_trade_sol:
                last_sol_bar = bar_ts

            # ---- MEMES: regime + donch_regime ----
            meme_snap = {}
            bull = bool(ind.get("sol_regime_bull"))
            bull_by = {(12, 26): bull}  # regime por (ema_fast, ema_slow) de params.json, calculado uma vez por ciclo

            def _bull(f, s_):
                if (f, s_) not in bull_by:
                    bull_by[(f, s_)] = bool(book.sol_indicators(ema_fast=f, ema_slow=s_).get("sol_regime_bull"))
                return bull_by[(f, s_)]
            for sym, pdata in list(regime_ports.items()):
                tmeta = token_by_sym.get(sym) or {}
                mint = tmeta.get("mint")
                decs = int(tmeta.get("decimals") or 6)
                mark = marks.get(sym) or {}
                px = float(mark.get("price_usd") or 0)
                if px <= 0 and book.memes.get(sym):
                    px = float(book.memes[sym][-1]["close"])
                if px <= 0 or not mint:
                    continue
                mi = book.meme_indicators(sym)
                m_bar = mi.get("bar_ts")
                new_m = m_bar is not None and m_bar != last_meme_bar.get(sym) and mi.get("ready")
                can_m = allow and new_m and m_bar is not None and (m_bar + 3600) > book.started_ts

                # regime-only: buy/hold when bull and flat→buy into position; sell all when not bull
                _variants = [
                    ("regime", pdata, f"{sym}_rule_regime"),
                    ("donch", donch_ports[sym], f"{sym}_rule_donch_regime"),
                ]
                if sym in full_regime_ports:
                    _variants.append(("regime_full", full_regime_ports[sym], f"{sym}_rule_regime_full"))
                if sym in full_donch_ports:
                    _variants.append(("donch_full", full_donch_ports[sym], f"{sym}_rule_donch_regime_full"))
                for snap_kind, port, strat_name in _variants:
                    kind = "regime" if snap_kind.startswith("regime") else "donch"
                    is_full = snap_kind.endswith("_full")
                    tag = f"rule:{strat_name}"
                    # params.json: types.rule_regime / rule_donchian (+ variants.full: compra 100%, spot sem alavancagem)
                    eff = P.effective(strat_name)
                    gcfg, rp = eff["gates"], eff.get("rule") or {}
                    fees, market = P.fees_market(eff, cfg)
                    # pausa: o próprio nome ou a chave de grupo meme_rule_*[_full] (pause_keys em lab_registry.originals)
                    enabled = load_rule_enabled(overlay, strat_name, rules_cfg) and not eff["paused"]
                    p_bull = _bull(int(rp.get("ema_fast", 12)), int(rp.get("ema_slow", 26)))
                    n_d = int(rp.get("donchian", 20))
                    mi_p = mi if n_d == 20 else book.meme_indicators(sym, donchian=n_d)
                    signal = "hold"
                    reasons = []
                    traded = False
                    did = str(uuid.uuid4())
                    if not enabled:
                        reasons.append("paused_or_disabled")
                    elif not can_m:
                        reasons.append("waiting_new_bar_after_start" if allow else "run_ended")
                    else:
                        held = float(port.get("token") or 0) > 1e-12
                        # regime: segura só com SOL em alta; donch: compra no rompimento com SOL em alta, vende no
                        # rompimento para baixo ou na saída do regime (rules_engine.meme_rule_signal, igual nos forks)
                        signal, rr = meme_rule_signal(kind, held, p_bull, mi_p.get("donchian20_signal") or "hold")
                        reasons += rr
                        final = signal
                        ok, why = _cooldown_ok(port, gcfg, time.time())
                        if final in ("buy", "sell") and not ok:
                            final = "hold"; reasons.append(why)
                        if final == "buy" and float(port["usdt"]) * float(gcfg["buy_fraction_usdt"]) < float(gcfg["min_usdt_trade"]):
                            final = "hold"; reasons.append("insufficient_usdt")
                        if final == "sell" and float(port.get("token") or 0) * px < float(gcfg["min_usdt_trade"]):
                            final = "hold"; reasons.append("insufficient_token")
                        g_trade = gcfg
                        if final == "buy":
                            g_trade, why = P.cap_buy(gcfg, port, px)
                            if why:
                                final = "hold"; reasons.append(why)
                        if final in ("buy", "sell"):
                            try:
                                tr = sim_trade_meme(final, port, g_trade, fees, market,
                                                    px, did, meme_tr_log, mint, decs, sol_usd, tag)
                                traded = tr is not None
                                if not traded:
                                    final = "hold"; reasons.append("sim_trade_none")
                            except Exception as e:
                                final = "hold"; reasons.append(f"sim_err:{type(e).__name__}")
                        signal = final
                    write_json(meme_port / f"{strat_name}.json", port)
                    eq = equity_meme(port, px)
                    append_jsonl(meme_eq / f"{strat_name}.jsonl", {
                        "ts": time.time(), "price": px, "token": port.get("token"), "usdt": port["usdt"],
                        "equity": eq, "bh_equity": bh_meme(port, px),
                        "all_usdt_equity": float(port["benchmark_all_usdt"]["usdt"]),
                        "trade_count": port["trade_count"], "portfolio": strat_name,
                    })
                    log_decision(meme_dec_log, decision_id=did, portfolio=strat_name, strategy=tag,
                                 symbol=sym, chosen_action=signal, final_action=signal,
                                 gate_reasons=reasons, confidence=1.0, skip_noul=0.0,
                                 traded=traded, price_usd=px, price_source=mark.get("source"),
                                 model="rule",
                                 indicators={"sol_regime_bull": p_bull, "donch": mi_p.get("donchian20_signal"),
                                             "sol_ema12": ind.get("ema12"), "sol_ema26": ind.get("ema26"),
                                             "bar_ts": m_bar},
                                 equity_usd=eq, token=port.get("token"), usdt=port["usdt"],
                                 bar_acted=bool(can_m and enabled))
                    meme_snap.setdefault(sym, {})[snap_kind] = {
                        "equity_usd": eq, "usdt": port["usdt"], "token": port.get("token"),
                        "trades": port["trade_count"], "last_signal": signal,
                        "position": port["position"], "bh_equity": bh_meme(port, px),
                        "strategy": tag, "gate_reasons": reasons,
                    }
                if can_m:
                    last_meme_bar[sym] = m_bar

            # ---- FORKS de regras: depois dos originais, isolados (um erro aqui nunca afeta os originais) ----
            try:
                fork_snap = forks.step(book, ind=ind, sol_px=sol_px, marks=marks, allow=allow, overlay=overlay,
                                       rules_cfg=rules_cfg, cfg=cfg, token_by_sym=token_by_sym, bull=_bull)
            except Exception as fe:
                fork_snap = {"_error": f"{type(fe).__name__}: {fe}"}
                print(f"rules_bot forks error: {fe}\n{traceback.format_exc()}", flush=True)

            cycles += 1
            status = {
                "ok": True, "ts": time.time(), "ts_brt": brt_iso(), "cycles": cycles,
                "errors": errors, "pid": os.getpid(), "finished": finished or not allow,
                "paper_only": True, "started_brt": start_brt,
                "warm_up": warm, "sol_price": sol_px, "sol_price_source": sol_src,
                "indicators": {
                    "sol": {
                        "close_1h": ind.get("close"), "ema12": ind.get("ema12"),
                        "ema26": ind.get("ema26"), "rsi": ind.get("rsi"),
                        "rsi_prev": ind.get("rsi_prev"),
                        "regime_bull": ind.get("sol_regime_bull"),
                        "bar_ts": ind.get("bar_ts"), "bar_brt": ind.get("bar_brt"),
                        "n_bars": ind.get("n_bars"), "ready": ind.get("ready"),
                    },
                    "memes": {s: book.meme_indicators(s) for s in regime_ports},
                },
                "portfolios": snap_ports,
                "meme_portfolios": meme_snap,
                "rule_forks": fork_snap,
                "uptime_seconds": round(time.time() - started, 1),
                "end_at_brt": cfg["end_at_brt"],
            }
            write_json(status_path, status)
            print(
                f"rules cycle={cycles} sol={sol_px:.3f} rsi={ind.get('rsi')} "
                f"bull={ind.get('sol_regime_bull')} "
                f"grid_sig={snap_ports.get('grid_sol_2pct',{}).get('last_signal')} "
                f"rsi_sig={snap_ports.get('rsi_sol_1h',{}).get('last_signal')} "
                f"grid_eq={snap_ports.get('grid_sol_2pct',{}).get('equity_usd')} "
                f"rsi_eq={snap_ports.get('rsi_sol_1h',{}).get('equity_usd')}",
                flush=True,
            )
        except Exception as e:
            errors += 1
            print(f"rules_bot error: {e}\n{traceback.format_exc()}", flush=True)
            write_json(status_path, {
                "ok": False, "error": str(e), "ts_brt": brt_iso(),
                "cycles": cycles, "errors": errors, "pid": os.getpid(),
            })

        if finished:
            break
        sleep_for = max(1.0, cycle - (time.time() - t0))
        end_sleep = time.time() + sleep_for
        while time.time() < end_sleep and not STOP:
            time.sleep(max(0.0, min(0.5, end_sleep - time.time())))

    print("rules_bot exit", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
