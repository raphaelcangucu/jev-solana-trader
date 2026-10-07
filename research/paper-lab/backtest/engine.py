"""Motor do backtest: repete, passo a passo, os bots do run ao vivo sobre as séries históricas.

Reutiliza o código ao vivo (com `simenv` a trocar relógio, ficheiros e cotações):

- sol_bot: `apply_and_maybe_trade` (portões, margem, regime, horário, saídas, teto de exposição, `sim_trade`) para
  baseline, relaxed, híbrido, v2 e portfólios extra (laya, poorjev, jev). Estado de cada chamada como ao vivo: uma
  chamada do von por passo com a posição/humor do baseline (partilhada por baseline/relaxed/híbrido), v2 com a sua
  própria posição, e por modelo extra o estado do primeiro portfólio desse modelo.
- meme_bot: idem por moeda, em rotação (uma moeda por minuto, cada moeda decide a cada 7 min, como ao vivo), estado
  partilhado a partir da posição do `meme_{SYM}_baseline`; von, laya e poorjev; híbrido poorjev+regime.
- lab_bot: a classe `Lab` original (`cycle`, `act`, ensemble por percentil, ordens limite, saídas, forks de critérios)
  alimentada com as linhas de decisão simuladas. Ordens limite enchem quando a mínima/máxima do minuto cruza o limite.
- rules_bot: `RuleForks._one` (os mesmos sinais e portões dos originais de regra) para originais e forks de regra, em
  barras de 1 h fechadas até ao instante simulado.
- bot real: `jev_trader.decide.resolve_action` + `jev_trader.paper._check_exits/_gate_fill` a cada 15 s (livros A e B).
"""
from __future__ import annotations

import copy
import json
import time as _rt
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from backtest import states as ST
from backtest.simenv import BRT, Clock, SimEnv

DUMMY = Path("/nonexistent/backtest/never-written.json")
EQ_EVERY = 300


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=BRT).isoformat(timespec="seconds")


class FeedTail:
    def __init__(self):
        self.rows = []

    def read(self):
        out, self.rows = self.rows, []
        return out


class Recorder:
    """Equity em grelha de 5 min + preço, B&H e quantidade (o formato que bot/analytics._grid_series lê)."""

    def __init__(self):
        self.rows: dict = {}

    def add(self, name, ts, eq, px, bh, q):
        self.rows.setdefault(name, []).append({"ts": ts, "equity": eq, "price": px, "bh_equity": bh, "q": q})


def qty(p):
    return float(p.get("sol") or 0) if p.get("asset_mode", "sol") == "sol" else float(p.get("token") or 0)


def equity_of(p, px):
    return float(p["usdt"]) + qty(p) * px


def bh_of(p, px):
    bh = p["benchmark_buy_hold"]
    return float(bh.get("usdt") or 0) + float(bh.get("sol" if p.get("asset_mode", "sol") == "sol" else "token") or 0) * px


class Engine:
    def __init__(self, *, data, start, end, step, items, client, cfg, memecoins, slip_bps, crit_files, logf=None,
                 jev_ready=False, progress=None, realbot_params=None, realbot_step=15, eq_every=EQ_EVERY):
        import bot.lab_bot as LB
        import bot.rules_bot as RB
        from bot import lab_registry as R
        from bot import params as P
        self.LB, self.RB, self.R, self.P = LB, RB, R, P
        self.data, self.start, self.end, self.step = data, int(start), int(end), int(step)
        self.items = {it["name"]: it for it in items}
        self.client, self.cfg, self.logf = client, cfg, logf
        self.tokens = memecoins["tokens"]
        self.syms = [t["symbol"] for t in self.tokens]
        self.tok = {t["symbol"]: t for t in self.tokens}
        self.start_usdt_meme = float(memecoins.get("start_usdt_each", 1000.0))
        self.jev_ready = jev_ready
        self.progress = progress
        self.realbot_params = realbot_params or {}
        self.realbot_step = realbot_step
        self.eq_every = int(eq_every)      # grelha da equity gravada (5 min; 1 h nas janelas longas, por memória)
        self.clock = Clock(start)
        self.marks: dict = {}
        self.lowhigh: dict = {}
        self.regime_now = None
        self.env = SimEnv(self.clock, self.marks, slip_bps, {t["mint"]: t["symbol"] for t in self.tokens},
                          regime_fn=lambda: self.regime_now)
        self.rec = Recorder()
        self.ports: dict = {}           # nome -> estado (dict no formato dos bots)
        self.asset_of: dict = {}
        self.crit_files = crit_files    # cid -> critérios (já registados no cliente)
        self.counts = {"steps": 0, "sol_decisions": 0, "meme_decisions": 0, "lab_cycles": 0, "rule_bars": 0}
        self.sol_ms = ST.MarketStates(ST.sol_sampler(*data["sol_grid"]))
        self.meme_ms = {s: ST.MarketStates(ST.minute_sampler(data["minute"][s])) for s in self.syms}

    # ------------------------------------------------------------------ preparação
    def _px(self, sym, t):
        return self.data["minute"][sym].close_at(t)

    def setup(self):
        P, R, SB, MB, RB = self.P, self.R, None, None, self.RB
        import bot.sol_bot as SB
        import bot.meme_bot as MB
        self.SB, self.MB = SB, MB
        self.env.install({t["symbol"]: int(t["decimals"]) for t in self.tokens})
        self.clock.now = self.start
        bal = self.cfg["starting_balances"]
        self.sol_frac = float(bal.get("sol_frac") or (bal["sol"] * bal["ref_price"] / bal["total_usd"]))
        total = float(bal.get("total_usd") or 1000.0)
        px0 = {s: self._px(s, self.start) for s in ["SOL"] + self.syms}
        self.px0 = px0
        sol0 = total * self.sol_frac / px0["SOL"]
        usdt0 = total * (1 - self.sol_frac)
        self.sol0, self.usdt0 = sol0, usdt0
        self.eff = {}
        for n, it in self.items.items():
            a = it["asset"]
            self.asset_of[n] = a
            r = it["runner"]
            if r == "sol_bot":
                p = SB.new_portfolio(DUMMY, sol0, usdt0, px0["SOL"], n)
                p["started_brt"] = _iso(self.start); p["model"] = it["model"]
                self.ports[n] = p
                self.eff[n] = P.effective(n)
            elif r == "meme_bot":
                self.ports[n] = MB.new_portfolio(DUMMY, self.start_usdt_meme, px0[a], n)
                self.eff[n] = P.effective(n)
            elif r == "rules_bot":
                if a == "SOL":
                    p = RB.new_sol_portfolio(DUMMY, sol0, usdt0, px0["SOL"], n)
                else:
                    p = RB.new_meme_portfolio(DUMMY, self.start_usdt_meme, px0[a], n)
                p["created_ts"] = self.start
                self.ports[n] = p
            elif r == "lab_bot":
                if a == "SOL":
                    st = R.new_state(n, "SOL", px0["SOL"], sol=sol0, usdt=usdt0)
                else:
                    st = R.new_state(n, a, px0[a], usdt=self.start_usdt_meme)
                st["strategy"] = ("fork:" if it["parent"] else "hyp:") + n
                self.ports[n] = st
        # lab
        reg = R.load()
        reg["portfolios"] = {k: v for k, v in reg["portfolios"].items() if k in self.items}
        self.lab = SimLab(self, reg)
        self.lab.active(P.STORE.overlay())
        # rules (originais + forks de regra) via RuleForks._one
        orig = R.originals()
        rule_entries = {}
        for n, it in self.items.items():
            if it["runner"] != "rules_bot":
                continue
            e = dict(orig.get(n) or reg["portfolios"].get(n) or it["meta"])
            e.setdefault("name", n)
            e["strategy"] = e.get("strategy") or (f"fork:{n}" if it["parent"] else f"rule:{n}")
            if not it["parent"]:
                e["parent"] = None
            rule_entries[n] = e
        self.rules = SimRules(self, rule_entries, reg)
        self.book = SimBook(self.data["hourly"], self.start)
        # quem é dono do estado (posição/humor) de cada chamada, como ao vivo
        self.sol_extra = {}
        for mid, b in (self.client_models_cfg().get("backends") or {}).items():
            if mid == "von" or not b.get("enabled"):
                continue
            ports = [p for p in (b.get("sol_portfolios") or []) if p in self.ports]
            if ports:
                self.sol_extra[mid] = ports
        self.meme_extra = [m for m in ("laya", "poorjev")
                           if any(f"{s}_{m}_baseline" in self.ports for s in self.syms)]
        self.trade_counts_at_start = 0
        return self

    def client_models_cfg(self):
        from bot.backends import load_models_cfg
        return load_models_cfg()

    # ------------------------------------------------------------------ regime de SOL
    def update_regime(self, t):
        self.book.advance(t)
        ind = self.book.ind()
        self.regime_now = bool(ind.get("sol_regime_bull")) if ind.get("ready") else None

    # ------------------------------------------------------------------ passo SOL
    def sol_step(self, t, px):
        SB, P = self.SB, self.P
        mk = self.sol_ms.at(t)
        if mk is None:
            return []
        rows = []
        cfg = self.cfg
        pr = {"source": "backtest"}

        def st_for(p):
            return {"state": ST.compose(mk, SB.position_word(p), p.get("recent_pnl_mood") or "neutral"), "features": {}}

        base = self.ports.get("baseline")
        if base is not None:
            st = st_for(base)
            dec = self.client.get("von", "lab_baseline", st["state"])
            dec["model"] = "von"; dec.setdefault("latency_ms", 0.0); dec.setdefault("error", None)
            for n, prof in (("baseline", "baseline"), ("relaxed", "relaxed")):
                if n in self.ports:
                    rows.append(SB.apply_and_maybe_trade(n, self.ports[n], DUMMY, DUMMY, self.eff[n]["gates"], prof, dec, st,
                                                         px, pr, True, cfg, DUMMY, DUMMY, "baseline", model="von",
                                                         eff=self.eff[n]))
            n = "hybrid_von_relaxed_cap2"
            if n in self.ports:
                rows.append(SB.apply_and_maybe_trade(n, self.ports[n], DUMMY, DUMMY, self.eff[n]["gates"], "relaxed", dec,
                                                     st_for(self.ports[n]), px, pr, True, cfg, DUMMY, DUMMY, "baseline",
                                                     model="von+rules", strategy="rule:hybrid_von_relaxed_cap2",
                                                     eff=self.eff[n], regime_bull=self.regime_now))
        if "v2" in self.ports:
            st_v = st_for(self.ports["v2"])
            dec_v = self.client.get("von", "lab_v2", st_v["state"])
            dec_v["model"] = "von"; dec_v.setdefault("latency_ms", 0.0)
            rows.append(SB.apply_and_maybe_trade("v2", self.ports["v2"], DUMMY, DUMMY, self.eff["v2"]["gates"], "relaxed",
                                                 dec_v, st_v, px, pr, True, cfg, DUMMY, DUMMY, "v2", model="von",
                                                 eff=self.eff["v2"]))
        for mid, names in self.sol_extra.items():
            st0 = st_for(self.ports[names[0]])
            dec_m = self.client.get(mid, "lab_baseline", st0["state"])
            dec_m["model"] = mid; dec_m.setdefault("latency_ms", 0.0)
            for n in names:
                prof = "relaxed" if n.endswith("_relaxed") else "baseline"
                rows.append(SB.apply_and_maybe_trade(n, self.ports[n], DUMMY, DUMMY, self.eff[n]["gates"], prof, dec_m,
                                                     st_for(self.ports[n]), px, pr, True, cfg, DUMMY, DUMMY, "baseline",
                                                     model=mid, eff=self.eff[n]))
        self.counts["sol_decisions"] += 1
        return rows

    # ------------------------------------------------------------------ passo meme
    def meme_step(self, t, sym, px):
        MB = self.MB
        mk = self.meme_ms[sym].at(t)
        if mk is None:
            return []
        t_ = self.tok[sym]
        sol_usd = self.marks.get("SOL") or 0.0
        pb = self.ports.get(f"meme_{sym}_baseline")
        if pb is None:
            return []
        st = {"state": ST.compose(mk, MB.position_word(pb), pb.get("recent_pnl_mood") or "neutral"), "features": {}}
        decs = {"von": self.client.get("von", "lab_baseline", st["state"])}
        for m in self.meme_extra:
            decs[m] = self.client.get(m, "lab_baseline", st["state"])
        rows = []

        def run(n, prof, dec, model, **kw):
            if n not in self.ports:
                return
            d = dict(dec); d["model"] = model; d.setdefault("latency_ms", 0.0)
            e = self.eff[n]
            rows.append(MB.apply_and_maybe_trade(n, self.ports[n], DUMMY, DUMMY, e["gates"], prof, d, st, px, "backtest",
                                                 True, self.cfg, DUMMY, DUMMY, sym, t_["mint"], int(t_["decimals"]),
                                                 sol_usd, model=model, eff=e, **kw))
        run(f"meme_{sym}_baseline", "baseline", decs["von"], "von")
        run(f"meme_{sym}_relaxed", "relaxed", decs["von"], "von")
        for m in self.meme_extra:
            for prof in ("baseline", "relaxed"):
                run(f"{sym}_{m}_{prof}", prof, decs[m], m)
        if "poorjev" in decs:
            n = f"{sym}_hybrid_poorjev_regime"
            run(n, "relaxed", decs["poorjev"], "poorjev+rules", strategy=f"rule:{n}", regime_bull=self.regime_now)
        self.counts["meme_decisions"] += 1
        return rows

    # ------------------------------------------------------------------ equity
    def record(self, t):
        for n, p in self.ports.items():
            a = self.asset_of[n]
            px = self.marks.get(a)
            if px is None:
                continue
            self.rec.add(n, t, equity_of(p, px), px, bh_of(p, px), qty(p))

    # ------------------------------------------------------------------ laço principal
    def run(self):
        t0 = _rt.time()
        n_steps = (self.end - self.start) // self.step
        nsym = len(self.syms)
        self.clock.now = self.start
        for s in ["SOL"] + self.syms:
            self.marks[s] = self._px(s, self.start)
        self.update_regime(self.start)
        self.record(self.start)
        for k in range(1, n_steps + 1):
            t = self.start + k * self.step
            self.clock.now = t
            for s in ["SOL"] + self.syms:
                ms = self.data["minute"][s]
                i = ms.idx_at(t)
                c = float(ms.c[i]) if 0 <= i < len(ms.c) else float("nan")
                if np.isnan(c):
                    self.marks.pop(s, None)
                    self.lowhigh.pop(s, None)
                else:
                    self.marks[s] = c
                    self.lowhigh[s] = (float(ms.l[i]), float(ms.h[i]))
            if t % 3600 == 0 or self.regime_now is None:
                self.update_regime(t)
            sol_rows, meme_rows = [], []
            if "SOL" in self.marks:
                sol_rows = self.sol_step(t, self.marks["SOL"])
            if t % 60 == 0:
                sym = self.syms[((t - self.start) // 60) % nsym]
                if sym in self.marks:
                    meme_rows = self.meme_step(t, sym, self.marks[sym])
            self.lab.feed(sol_rows, meme_rows)
            self.lab.cycle()
            self.counts["lab_cycles"] += 1
            if t % 3600 == 0:
                self.rules.step_all(t)
                self.counts["rule_bars"] += 1
            else:
                self.rules.exits_only(t)
            if (t - self.start) % self.eq_every == 0 or k == n_steps:
                self.record(t)
            self.counts["steps"] += 1
            if self.progress and k % (1440 * max(1, n_steps // 43200)) == 0:
                el = _rt.time() - t0
                self.progress(f"simulação {k}/{n_steps} passos ({k / n_steps * 100:.0f}%), {el:.0f}s, "
                              f"trades {len(self.env.trades)}")
                self.client.cache.commit()
        self.client.cache.commit()
        self.counts["secs"] = round(_rt.time() - t0, 1)
        return self

    # ------------------------------------------------------------------ bot real (livros A/B)
    def run_realbot(self, profiles: dict):
        """profiles: {"A": "relaxed_paper", "B": "relaxed_exits_paper"}. Livro inicial do experimento, desde o início."""
        import jev_trader.paper as JP
        from jev_trader.decide import ModelAnswer, resolve_action
        from jev_trader.exits import ExitParams
        g, px = self.data["sol_grid"]
        gf = ST.ffill(px)
        out = {}
        trades_sink = []
        orig = JP.append_jsonl
        JP.append_jsonl = lambda path, row: trades_sink.append(row)
        try:
            for label, prof in profiles.items():
                vals = self.realbot_params[prof]
                ex = ExitParams.from_dict(vals["exits"])
                cfg = SimpleNamespace(exits=ex, paper_cost_bps=float(vals["paper_cost_bps"]), paper_trades_path=DUMMY,
                                      max_exposure_frac=vals.get("max_exposure_frac"), buy_usdt=float(vals["buy_usdt"]),
                                      max_buy_usdt=float(vals["max_buy_usdt"]), sell_sol=float(vals["sell_sol"]),
                                      max_sell_sol=float(vals["max_sell_sol"]), paper_book_label=label)
                st0, px0 = ST.realbot_state(g, gf, self.start)
                book = JP.PaperBook(run_id="backtest", sol=ST.REAL_SOL_UI, usdt=ST.REAL_USDT_UI, book=label,
                                    start_t=_iso(self.start), start_px=px0, avg_cost=px0, peak_px=px0, updated_t=_iso(self.start))
                trades_sink.clear()
                eq = []
                n_dec = n_exec = 0
                for t in range(self.start, self.end, self.realbot_step):
                    state, p = ST.realbot_state(g, gf, t)
                    if state is None:
                        continue
                    ans = self.client.get("von", "realbot", state)
                    model = ModelAnswer(ok=not ans.get("fail_closed"), choice=ans["chosen_action"],
                                        confidence=float(ans["confidence"]), skip_noul=float(ans["skip_noul"]),
                                        probabilities=ans.get("probabilities") or {}, source="von-backtest")
                    gate = resolve_action(model, market_ok=True, confidence_min=float(vals["confidence_min"]),
                                          skip_min=float(vals["skip_min"]), prob_margin_min=float(vals["prob_margin_min"]))
                    ts = _iso(t)
                    if ex.active:
                        book, _x = JP._check_exits(cfg, book, p, ts)
                    if gate.execute:
                        n_exec += 1
                        _f, _r, book, _tr = JP._gate_fill(cfg, book, side=gate.action, confidence=model.confidence, px=p, t=ts)
                    n_dec += 1
                    if (t - self.start) % self.eq_every == 0:
                        eq.append({"ts": t, "equity": book.usdt + book.sol * p, "price": p,
                                   "bh_equity": ST.REAL_USDT_UI + ST.REAL_SOL_UI * p, "q": book.sol})
                last_p = float(gf[(self.end - int(g[0])) // int(g[1] - g[0])])
                eq.append({"ts": self.end, "equity": book.usdt + book.sol * last_p, "price": last_p,
                           "bh_equity": ST.REAL_USDT_UI + ST.REAL_SOL_UI * last_p, "q": book.sol})
                out[label] = {"profile": prof, "book": book, "equity": eq, "trades": list(trades_sink),
                              "decisions": n_dec, "executes": n_exec}
        finally:
            JP.append_jsonl = orig
        return out


# ---------------------------------------------------------------------- lab


def _make_simlab_class():
    import bot.lab_bot as LB

    class _SimLab(LB.Lab):
        """Lab original sem ficheiros: estado em memória, linhas de decisão injetadas, critérios pelo cliente do backtest."""

        def __init__(self, eng, reg):  # noqa: D401 — não chama Lab.__init__ (lê ficheiros)
            from bot import lab_registry as R
            self.eng = eng
            self.cfg = eng.cfg
            reg = dict(reg)
            reg["_mtime"] = R.mtime()
            self.reg = reg
            self.ports = eng.ports
            self.tails = {"sol": FeedTail(), "meme": FeedTail()}
            self.ens_latest = {}
            self.ens_last_eval = {}
            self.windows = {}
            self.last_eq = {}
            self.errors = 0
            self.cycles = 0
            self.processed = 0
            self.crit = SimCrit(eng)
            self._act = None

        def port(self, name):
            return self.ports[name]

        def save(self, name):
            return None

        def log_eq(self, name, px, force=False):
            return None

        def log_dec(self, *a, **k):
            return None

        def active(self, overlay):
            if self._act is None:
                self._act = super().active(overlay)
                for e in self._act:
                    e["_paused"] = False   # o backtest simula tudo (nenhuma pausa do dashboard)
            return self._act

        def feed(self, sol_rows, meme_rows):
            self.tails["sol"].rows.extend(sol_rows)
            self.tails["meme"].rows.extend(meme_rows)

        def check_limit(self, e, px):
            o = self.port(e["name"]).get("open_order")
            if not o:
                return
            lo, hi = self.eng.lowhigh.get(e["asset"], (px, px))
            if o["side"] == "buy" and lo < o["limit"]:
                return super().check_limit(e, lo)
            if o["side"] == "sell" and hi > o["limit"]:
                return super().check_limit(e, hi)
            return super().check_limit(e, px)

    return _SimLab


def SimLab(eng, reg):
    return _make_simlab_class()(eng, reg)


class SimCrit:
    """Substitui o CriteriaCaller: mesma saída, mas pelo cliente do backtest (servidores próprios + cache)."""

    def __init__(self, eng):
        self.eng = eng
        self.stats = {"calls": 0, "hits": 0, "errors": 0, "fail_closed": 0}
        self.cache = {}

    def decide(self, e, src):
        from bot import lab_criteria as LC
        model = (e.get("model") or "").split("+")[0]
        ref = (e.get("params") or {}).get("criteria") or {}
        state = (src or {}).get("state")
        self.stats["calls"] += 1
        out = None
        if not state or any(ch.isdigit() for ch in str(state)):
            out = None
        else:
            try:
                clean, sha = LC.load_ref(ref)
                cid = f"crit:{sha[:16]}"
                if cid not in self.eng.client.criteria:
                    self.eng.client.register(cid, clean)
                r = self.eng.client.get(model, cid, state)
                if not r.get("fail_closed"):
                    out = {"chosen_action": r["chosen_action"], "probabilities": r.get("probabilities") or {},
                           "confidence": float(r["confidence"]), "skip_noul": float(r["skip_noul"]),
                           "fail_closed": False, "error": None}
            except Exception as ex:  # critérios inválidos → hold
                out = None
                self.stats["errors"] += 1
        if out is None:
            self.stats["fail_closed"] += 1
            out = {"chosen_action": "hold", "probabilities": {"buy": 0.0, "sell": 0.0, "hold": 1.0}, "confidence": 0.0,
                   "skip_noul": 1.0, "fail_closed": True, "error": "fail_closed"}
        out["log"] = {}
        return out


# ---------------------------------------------------------------------- regras


class SimBook:
    """CandleBook com as barras de 1 h FECHADAS até ao instante simulado (ts + 3600 ≤ t)."""

    def __init__(self, hourly: dict, started_ts: float):
        from bot.rules_engine import CandleBook, MEME_GATE_PAIRS
        self._cb = CandleBook.__new__(CandleBook)
        self._cb.sol, self._cb.memes = [], {s: [] for s in MEME_GATE_PAIRS}
        self._cb.started_ts = float(started_ts)
        self._cb.last_acted_bar, self._cb.meta = {}, {}
        self.all = hourly
        self.ts = {k: np.array([b["ts"] for b in v], dtype=np.int64) for k, v in hourly.items()}
        self._t = None
        self._ind = {}

    @property
    def book(self):
        return self._cb

    def advance(self, t):
        hf = int(t) // 3600 * 3600
        if self._t == hf:
            return
        self._t = hf
        self._ind = {}
        for k, bars in self.all.items():
            n = int(np.searchsorted(self.ts[k], hf - 3600, side="right"))   # barras com ts ≤ hf − 3600
            if k == "SOL":
                self._cb.sol = bars[:n]
            else:
                self._cb.memes[k] = bars[:n]

    def ind(self, f=12, s=26, r=14):
        key = (f, s, r)
        if key not in self._ind:
            self._ind[key] = self._cb.sol_indicators(ema_fast=f, ema_slow=s, rsi_period=r)
        return self._ind[key]


def _make_simrules_class():
    import bot.rules_bot as RB

    class _SimRules(RB.RuleForks):
        def __init__(self, eng, entries, reg):
            super().__init__(log=lambda *a, **k: None)
            self.eng = eng
            self.entries = entries
            self.reg = reg
            self._key = ("sim",)
            self.ports = eng.ports
            self.rules_cfg = eng.cfg.get("rule_strategies") or {}
            self.with_exits = set()

        def refresh(self, force=False):
            return False

        def port(self, name):
            return self.ports[name]

        def _log_eq(self, *a, **k):
            return None

        def _args(self, t):
            eng = self.eng
            sb = eng.book
            sb.advance(t)
            ind = sb.ind()
            marks = {s: {"price_usd": p} for s, p in eng.marks.items() if s != "SOL"}
            bull = lambda f, s_: bool(sb.ind(int(f), int(s_)).get("sol_regime_bull"))
            return sb.book, ind, marks, bull

        def step_all(self, t):
            book, ind, marks, bull = self._args(t)
            sol_px = self.eng.marks.get("SOL") or float(ind.get("close") or 0)
            cache = {}
            for name, e in sorted(self.entries.items()):
                if e.get("asset", "SOL") != "SOL" and e.get("asset") not in self.eng.marks:
                    continue
                try:
                    self._one(name, e, book, ind, float(sol_px), marks, True, {}, self.rules_cfg, self.eng.cfg,
                              self.eng.tok, bull, cache, float(t))
                except Exception as ex:
                    self._warn(name, f"erro (hold): {type(ex).__name__}: {ex}")

        def exits_only(self, t):
            """Entre barras, só os forks com saídas ligadas precisam de passo (o _one não age sem barra nova)."""
            if not self.with_exits:
                return
            book, ind, marks, bull = self._args(t)
            sol_px = self.eng.marks.get("SOL") or 0.0
            for name in self.with_exits:
                e = self.entries[name]
                try:
                    self._one(name, e, book, ind, float(sol_px), marks, True, {}, self.rules_cfg, self.eng.cfg,
                              self.eng.tok, bull, {}, float(t))
                except Exception as ex:
                    self._warn(name, f"erro (hold): {type(ex).__name__}: {ex}")

    return _SimRules


def SimRules(eng, entries, reg):
    obj = _make_simrules_class()(eng, entries, reg)
    from bot import params as P
    for n, e in entries.items():
        if e.get("parent"):
            eff = P.effective(n, meta=e, registry=reg)
            if (eff.get("exits") or {}).get("enabled"):
                obj.with_exits.add(n)
    return obj
