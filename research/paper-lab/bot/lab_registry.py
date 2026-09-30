"""Registry for lab portfolios: hypotheses (H1-H4) and tuning forks, grouped in lineages.

Rules (user, 2026-09-24): originals are NEVER modified. Tuning creates a FORK ({name}__fork{N}) that
starts from its parent's current state/value. A fork that beats its parent out-of-sample becomes the
lineage's *lead fork* (future forks branch from it); the original keeps running untouched.
NOTHING is ever deactivated or retired (user rule): forks that trail are only LABELED in reports.
Resource control is on fork CREATION: at most 1 new fork per lineage per 7 days and a total cap (default 40).
"""
from __future__ import annotations
import fcntl, json, time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from bot.lib import BRT, brt_iso, write_json, append_jsonl

ROOT = Path("/home/box/solana-trader/paper")
LAB = ROOT / "data" / "lab"
REG = LAB / "registry.json"
LOCK = LAB / "registry.lock"
PARAM_LOG = ROOT / "logs" / "param_changes.jsonl"
SYMS = ["BONK", "WIF", "POPCAT", "FARTCOIN", "PNUT", "MEW", "GOAT"]

HARD = {"buy_fraction_usdt": (0.05, 0.5), "max_trades_per_hour": (1, 8), "cooldown_seconds": (30, 3600),
        "min_confidence": (0.0, 0.99), "min_prob_margin": (0.0, 0.9), "max_skip_noul": (0.05, 0.95)}
EXITS_SOL = {"tp": 0.025, "sl": 0.015, "trail": 0.010, "trail_arm": 0.010, "reentry_cooldown_min": 30}
EXITS_MEME = {"tp": 0.06, "sl": 0.04, "trail": 0.03, "trail_arm": 0.03, "reentry_cooldown_min": 30}
LIMIT = {"mode": "limit", "offset_bps": 10, "ttl_min": 15, "fee_bps": 10}
HOURS = [5, 10, 11, 12, 18]
ENS = {"min_agree": 2, "pct_threshold": 0.80, "min_window": 100}


def port_path(name):
    return LAB / "portfolios" / f"{name}.json"

def eq_path(name):
    return LAB / "equity" / f"{name}.jsonl"

def mtime():
    return REG.stat().st_mtime if REG.exists() else None

def load():
    if not REG.exists():
        d = {"portfolios": {}, "lineages": {}, "caps": {"per_lineage_days": 7, "total": 40}}
    else:
        d = json.loads(REG.read_text())
    d["_mtime"] = mtime()
    return d

@contextmanager
def locked():
    LAB.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "a+") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        d = load(); d.pop("_mtime", None)
        try:
            yield d
        finally:
            write_json(REG, d)
            fcntl.flock(lf, fcntl.LOCK_UN)

def clamp_gates(g):
    g = dict(g)
    for k, (lo, hi) in HARD.items():
        if k in g and g[k] is not None:
            v = min(hi, max(lo, float(g[k])))
            g[k] = int(round(v)) if k in ("max_trades_per_hour", "cooldown_seconds") else v
    return g


# ---------- originals (bot-run portfolios) ----------
def originals():
    """name -> meta for the portfolios run by sol_bot/meme_bot/rules_bot (never modified by tuning)."""
    o = {}
    for n, prof, model in [("baseline", "baseline", "von"), ("relaxed", "relaxed", "von"), ("v2", "relaxed", "von"),
                           ("laya_baseline", "baseline", "laya"), ("laya_relaxed", "relaxed", "laya"),
                           ("poorjev_baseline", "baseline", "poorjev"), ("poorjev_relaxed", "relaxed", "poorjev"),
                           ("hybrid_von_relaxed_cap2", "relaxed", "von+rules")]:
        o[n] = {"asset": "SOL", "cls": "sol", "kind": "gated", "source": n, "profile": prof, "model": model,
                "file": str(ROOT / "data" / f"portfolio_{n}.json"), "equity": str(ROOT / "data" / f"equity_{n}.jsonl"),
                "gates": ({"max_trades_per_hour": 2} if n.startswith("hybrid") else {})}
    for n in ["grid_sol_2pct", "rsi_sol_1h"]:
        o[n] = {"asset": "SOL", "cls": "sol", "kind": "rule", "rule": n.split("_")[0], "model": "rule",
                "file": str(ROOT / "data" / f"portfolio_{n}.json"), "equity": str(ROOT / "data" / f"equity_{n}.jsonl")}
    md = ROOT / "data" / "meme"
    for s in SYMS:
        for prof in ("baseline", "relaxed"):
            n = f"meme_{s}_{prof}"
            o[n] = {"asset": s, "cls": "meme", "kind": "gated", "source": n, "profile": prof, "model": "von",
                    "file": str(md / "portfolios" / f"{s}_{prof}.json"), "equity": str(md / "equity" / f"{s}_{prof}.jsonl"), "gates": {}}
            for m in ("laya", "poorjev"):
                n = f"{s}_{m}_{prof}"
                o[n] = {"asset": s, "cls": "meme", "kind": "gated", "source": n, "profile": prof, "model": m,
                        "file": str(md / "portfolios" / f"{n}.json"), "equity": str(md / "equity" / f"{n}.jsonl"), "gates": {}}
        n = f"{s}_hybrid_poorjev_regime"
        o[n] = {"asset": s, "cls": "meme", "kind": "gated", "source": n, "profile": "relaxed", "model": "poorjev+rules",
                "file": str(md / "portfolios" / f"{n}.json"), "equity": str(md / "equity" / f"{n}.jsonl"), "gates": {}}
        for r in ("rule_regime", "rule_donch_regime", "rule_regime_full", "rule_donch_regime_full"):
            n = f"{s}_{r}"
            o[n] = {"asset": s, "cls": "meme", "kind": "rule", "rule": r, "model": "rule",
                    "file": str(md / "portfolios" / f"{n}.json"), "equity": str(md / "equity" / f"{n}.jsonl")}
    return o


# ---------- hypotheses ----------
def hypothesis_defs():
    H = []
    H.append(dict(name="h1_exits_von_relaxed", hyp="H1", asset="SOL", cls="sol", kind="gated", source="relaxed", profile="relaxed",
                  model="von", params={"exits": EXITS_SOL}, label="H1 Saídas (TP/SL/trailing) — von relaxed SOL"))
    for s in SYMS:
        H.append(dict(name=f"h1_exits_{s}_poorjev_relaxed", hyp="H1", asset=s, cls="meme", kind="gated", source=f"{s}_poorjev_relaxed",
                      profile="relaxed", model="poorjev", params={"exits": EXITS_MEME}, label=f"H1 Saídas — poorjev relaxed {s}"))
    H.append(dict(name="h2_ensemble_sol", hyp="H2", asset="SOL", cls="sol", kind="ensemble", profile="baseline", model="ensemble",
                  params={"ensemble": ENS}, label="H2 Ensemble von/poorjev/laya (percentil) — SOL"))
    for s in SYMS:
        H.append(dict(name=f"h2_ensemble_{s}", hyp="H2", asset=s, cls="meme", kind="ensemble", profile="baseline", model="ensemble",
                      params={"ensemble": ENS}, label=f"H2 Ensemble (percentil) — {s}"))
    H.append(dict(name="h3_limit_poorjev_relaxed", hyp="H3", asset="SOL", cls="sol", kind="gated", source="poorjev_relaxed",
                  profile="relaxed", model="poorjev", params={"exec": LIMIT}, label="H3 Ordem limite — poorjev relaxed SOL"))
    H.append(dict(name="h3_limit_hybrid_von_cap2", hyp="H3", asset="SOL", cls="sol", kind="gated", source="hybrid_von_relaxed_cap2",
                  profile="relaxed", model="von+rules", params={"exec": LIMIT, "gates": {"max_trades_per_hour": 2}},
                  label="H3 Ordem limite — hybrid von relaxed cap2"))
    H.append(dict(name="h4_hours_poorjev_relaxed", hyp="H4", asset="SOL", cls="sol", kind="gated", source="poorjev_relaxed",
                  profile="relaxed", model="poorjev", params={"hours": HOURS}, label="H4 Filtro de horário — poorjev relaxed SOL"))
    H.append(dict(name="h4_hours_von_relaxed", hyp="H4", asset="SOL", cls="sol", kind="gated", source="relaxed",
                  profile="relaxed", model="von", params={"hours": HOURS}, label="H4 Filtro de horário — von relaxed SOL"))
    return H


def _mark(asset):
    p = ROOT / "data" / "prices.jsonl" if asset == "SOL" else ROOT / "data" / "meme" / "prices" / f"{asset}.jsonl"
    with open(p, "rb") as f:
        f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 4096))
        return float(json.loads([l for l in f.read().split(b"\n") if l.strip()][-1])["price_usd"])


def new_state(name, asset, px, sol=0.0, usdt=0.0, token=0.0, extra=None):
    mode = "sol" if asset == "SOL" else "token"
    d = {"name": name, "asset_mode": mode, "asset": asset, "sol": sol, "usdt": usdt, "token": token,
         "start_sol": sol, "start_usdt": usdt, "start_token": token, "start_price": px,
         "benchmark_buy_hold": ({"sol": sol, "usdt": usdt} if mode == "sol" else {"token": token + usdt / px, "usdt": 0.0}),
         "benchmark_all_usdt": {"usdt": usdt + (sol if mode == "sol" else token) * px},
         "realized_pnl_usdt": 0.0, "fees_paid_usdt": 0.0, "fees_paid_sol": 0.0, "trade_count": 0,
         "last_trade_ts": None, "trade_timestamps": [], "position": "held" if (sol or token) else "flat",
         "recent_pnl_mood": "neutral", "created_ts": time.time(), "started_brt": brt_iso(),
         "entry_price": px if (sol or token) else None, "peak_price": px if (sol or token) else None}
    d.update(extra or {})
    return d


def ensure_hypotheses(cfg):
    created = []
    bal = cfg["starting_balances"]
    with locked() as reg:
        for h in hypothesis_defs():
            if h["name"] in reg["portfolios"]:
                continue
            px = _mark(h["asset"])
            if h["asset"] == "SOL":
                st = new_state(h["name"], "SOL", px, sol=float(bal["sol"]), usdt=float(bal["usdt"]))
            else:
                st = new_state(h["name"], h["asset"], px, usdt=float(json.loads((ROOT / "memecoins.json").read_text()).get("start_usdt_each", 1000.0)))
            st["strategy"] = f"hyp:{h['name']}"
            write_json(port_path(h["name"]), st)
            e = dict(h, status="active", created_brt=st["started_brt"], strategy=st["strategy"], lineage=h["name"], parent=None,
                     is_original=True)
            reg["portfolios"][h["name"]] = e
            reg["lineages"].setdefault(h["name"], {"root": h["name"], "lead": None, "members": [h["name"]]})
            created.append((h["name"], st["started_brt"]))
    if created:
        note = ROOT / "reports" / "hypotheses_start.md"
        txt = note.read_text() if note.exists() else (
            "# Portfólios de hipótese (lab) — horários de início (BRT)\n\n"
            "Paper only. Rodam em `bot/lab_bot.py` reaproveitando as decisões já logadas (sem chamadas extras aos modelos).\n"
            f"SOL começa com {bal['sol']} SOL + {bal['usdt']} USDT (≈ ${bal.get('total_usd', '?')}); memes com {json.loads((ROOT / 'memecoins.json').read_text()).get('start_usdt_each')} USDT.\n\n"
            "Parâmetros iniciais:\n"
            f"- H1 saídas memes: TP +{EXITS_MEME['tp']*100:.0f}%, SL −{EXITS_MEME['sl']*100:.0f}%, trailing {EXITS_MEME['trail']*100:.0f}% (arma após +{EXITS_MEME['trail_arm']*100:.0f}%), reentrada bloqueada {EXITS_MEME['reentry_cooldown_min']} min.\n"
            f"- H1 saídas SOL (von relaxed): TP +{EXITS_SOL['tp']*100:.1f}%, SL −{EXITS_SOL['sl']*100:.1f}%, trailing {EXITS_SOL['trail']*100:.1f}% (arma após +{EXITS_SOL['trail_arm']*100:.1f}%).\n"
            f"- H2 ensemble: percentil da confiança de cada modelo na janela móvel própria (SOL 480 decisões ≈ 2 h; memes 200 por modelo, todas as moedas), ≥{ENS['min_agree']} modelos concordando e percentil médio ≥ {ENS['pct_threshold']:.2f}; mínimo {ENS['min_window']} amostras na janela.\n"
            f"- H3 limite: preço mid ∓ {LIMIT['offset_bps']} bps, validade {LIMIT['ttl_min']} min, preenche só se o mark cruzar o limite (estritamente); taxa assumida {LIMIT['fee_bps']} bps + taxa de rede, sem slippage.\n"
            f"- H4 horários BRT permitidos: {HOURS} (compras e vendas).\n\n")
        for n, t in created:
            txt += f"- **{n}** iniciado {t}\n"
        note.write_text(txt)
    return created


def create_fork(parent, params_diff, reason, dry_run=False, cfg=None, caps_override=None):
    """Fork `parent` (original bot portfolio or lab portfolio) with params_diff. Returns fork name."""
    orig = originals()
    with locked() as reg:
        if parent in reg["portfolios"]:
            pe = reg["portfolios"][parent]; lineage = pe["lineage"]
            pstate = json.loads(port_path(parent).read_text())
            base = {k: pe.get(k) for k in ("asset", "cls", "kind", "source", "profile", "model")}
            params = json.loads(json.dumps(pe.get("params") or {}))
        elif parent in orig:
            m = orig[parent]; lineage = parent
            if m["kind"] != "gated":
                raise ValueError(f"fork of rule original {parent} not supported by lab executor yet")
            pstate = json.loads(Path(m["file"]).read_text())
            base = {k: m.get(k) for k in ("asset", "cls", "kind", "source", "profile", "model")}
            params = {"gates": dict(m.get("gates") or {})}
            reg["lineages"].setdefault(parent, {"root": parent, "lead": None, "members": [parent]})
        else:
            raise KeyError(parent)
        caps = dict({"per_lineage_days": 7, "total": 40}, **(caps_override or {}))
        reg["caps"] = caps
        forks_all = [e for e in reg["portfolios"].values() if e.get("parent")]
        recent = [e for e in forks_all if e["lineage"] == lineage and
                  time.time() - datetime.fromisoformat(e["created_brt"]).timestamp() < caps["per_lineage_days"] * 86400]
        if recent:
            return None, f"cap_1_fork_per_{caps['per_lineage_days']}d (último: {recent[-1]['name']})"
        if len(forks_all) >= caps["total"]:
            return None, f"cap_total_{caps['total']}_atingido"
        n = 1 + sum(1 for e in reg["portfolios"].values() if e.get("lineage") == lineage and e.get("parent"))
        name = f"{lineage}__fork{n}"
        for sect, vals in params_diff.items():
            params.setdefault(sect, {}).update(vals)
        if dry_run:
            return name, "dry_run"
        px = _mark(base["asset"])
        st = new_state(name, base["asset"], px, sol=float(pstate.get("sol") or 0), usdt=float(pstate["usdt"]),
                       token=float(pstate.get("token") or 0))
        if pstate.get("entry_price"):
            st["entry_price"] = pstate["entry_price"]
        st["strategy"] = f"fork:{name}"; st["fork_of"] = parent
        write_json(port_path(name), st)
        e = dict(base, name=name, status="active", created_brt=st["started_brt"], strategy=st["strategy"], lineage=lineage,
                 parent=parent, params=params, params_diff=params_diff, reason=reason, is_original=False,
                 label=f"Fork {n} de {parent}", start_value=st["benchmark_all_usdt"]["usdt"])
        reg["portfolios"][name] = e
        reg["lineages"].setdefault(lineage, {"root": lineage, "lead": None, "members": [lineage]})["members"].append(name)
    append_jsonl(PARAM_LOG, {"ts": time.time(), "ts_brt": brt_iso(), "type": "fork_created", "portfolio": name, "parent": parent,
                             "lineage": lineage, "params_diff": params_diff, "reason": reason, "who": "nightly"})
    return name, "created"


def label(name, label_text, reason):
    """Report-only label (e.g. 'atrás da original'). Never changes status: forks keep running forever."""
    with locked() as reg:
        e = reg["portfolios"][name]; e["report_label"] = label_text; e["report_label_brt"] = brt_iso(); e["report_label_reason"] = reason


def set_lead(lineage, name, reason):
    with locked() as reg:
        reg["lineages"].setdefault(lineage, {"root": lineage, "lead": None, "members": [lineage]})["lead"] = name
    append_jsonl(PARAM_LOG, {"ts": time.time(), "ts_brt": brt_iso(), "type": "lead_fork", "lineage": lineage, "portfolio": name,
                             "reason": reason, "who": "nightly"})
