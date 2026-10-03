"""Parâmetros por tipo de teste (paper only): resolver com herança em camadas, validação e hot reload.

Fonte única: `params.json` (env `PAPER_LAB_PARAMS`, senão `<PAPER_LAB_ROOT>/params.json`, senão o da pasta do lab).
Camadas, da mais fraca para a mais forte (deep-merge; listas e escalares substituem):

    defaults → profiles.<perfil> (extends primeiro) → types.<tipo> → types.<tipo>.variants.<variante>
    → models.<modelo> → assets.<sol|meme> → assets.meme.symbols.<SYM> → portfolios.<nome>
    → overlay em tempo real (`data/params_overlay.json`, escrito pelo dashboard)

Forks: parâmetros efetivos do pai SEM o overlay do pai → diff do fork (registry, `params_diff`) → portfolios.<fork>
→ overlay do fork.

`resolve(meta) -> (efetivo, proveniência)`; `Store.effective(nome)` valida e, em erro, fica nos últimos parâmetros
válidos daquele portfólio (nunca derruba um bot). Sem nenhum válido: parâmetros do artigo com `paused: true`
(fail-closed = hold). Recarrega por mtime de params.json, do overlay e do registry do lab.
"""
from __future__ import annotations

import copy
import json
import os
import time
from datetime import datetime
from pathlib import Path

from bot.paths import ROOT, LAB_DIR

GROUPS = ("gates", "exec", "exits", "hours", "ensemble", "rule", "regime_filter", "tuning", "limits")
SCHEMA = {
    "gates": ("min_confidence", "min_prob_margin", "margin_gate", "max_skip_noul", "cooldown_seconds",
              "max_trades_per_hour", "buy_fraction_usdt", "min_usdt_trade", "min_sol_trade", "max_exposure_frac"),
    "exec": ("mode", "extra_slippage_bps", "slippage_bps", "network_fee_sol", "offset_bps", "ttl_min", "fee_bps"),
    "exits": ("enabled", "tp", "sl", "trail", "trail_arm", "reentry_cooldown_min"),
    "ensemble": ("min_agree", "pct_threshold", "min_window"),
    "rule": ("grid_pct", "levels", "timeframe", "rsi_period", "lo", "hi", "ema_fast", "ema_slow", "donchian"),
    "regime_filter": ("enabled", "require_bull_for_buy", "block_if_unknown"),
    "tuning": ("enabled", "params", "bounds", "max_rel_change", "steps", "train_frac", "min_improvement_pct",
               "trade_penalty_bps"),
    "limits": ("buy_fraction_usdt_max", "max_trades_per_hour_max", "max_exposure_frac_max", "leverage"),
}
DOC_KEYS = ("note", "description", "label")
TOP_KEYS = ("version", "paper_only", "note", "defaults", "profiles", "types", "models", "assets", "portfolios")
# Tetos absolutos: nem um bloco `limits` passa daqui (spot, sem alavancagem).
ABSOLUTE = {"buy_fraction_usdt_max": 1.0, "max_trades_per_hour_max": 60, "max_exposure_frac_max": 1.0}
LAB_TYPES = {"H1": "lab_h1_exits", "H2": "lab_h2_ensemble", "H3": "lab_h3_limit", "H4": "lab_h4_hours"}
# Chaves planas do overlay antigo (dashboard) → gates.<chave>.
OVERLAY_FLAT = SCHEMA["gates"]
EDITABLE = ("min_confidence", "min_prob_margin", "max_skip_noul", "buy_fraction_usdt", "cooldown_seconds",
            "max_trades_per_hour")

FAILSAFE = {
    "gates": {"min_confidence": 0.6, "min_prob_margin": 0.0, "margin_gate": False, "max_skip_noul": 0.5,
              "cooldown_seconds": 120, "max_trades_per_hour": 8, "buy_fraction_usdt": 0.25, "min_usdt_trade": 1.0,
              "min_sol_trade": 0.001, "max_exposure_frac": None},
    "exec": {"mode": "market", "extra_slippage_bps": 5, "slippage_bps": 50, "network_fee_sol": 5e-06,
             "offset_bps": 10, "ttl_min": 15, "fee_bps": 10},
    "exits": {"enabled": False, "reentry_cooldown_min": 30},
    "hours": None,
    "regime_filter": {"enabled": False, "require_bull_for_buy": True, "block_if_unknown": True},
    "tuning": {"enabled": False, "params": [], "bounds": {}},
    "limits": {"buy_fraction_usdt_max": 0.5, "max_trades_per_hour_max": 8, "max_exposure_frac_max": 1.0,
               "leverage": "never"},
    "paused": True, "paper_only": True, "failsafe": True,
}


def params_path() -> Path:
    env = os.environ.get("PAPER_LAB_PARAMS")
    if env:
        return Path(env).expanduser()
    p = ROOT / "params.json"
    return p if p.exists() else LAB_DIR / "params.json"


def overlay_path() -> Path:
    return ROOT / "data" / "params_overlay.json"


# ---------------------------------------------------------------- classificação (meta por portfólio)

def _registry():
    from bot import lab_registry as R
    try:
        return R.load()
    except Exception:
        return {"portfolios": {}, "lineages": {}}


def _meta_from(name: str, e: dict, runner: str) -> dict:
    asset = e.get("asset") or "SOL"
    hyp = e.get("hyp")
    test_type = e.get("test_type") or LAB_TYPES.get(hyp or "")
    return {
        "name": name, "test_type": test_type, "profile": e.get("profile") or "baseline", "variant": e.get("variant"),
        "model": ((e.get("model") or "").split("+")[0] or None), "asset": asset,
        "asset_class": "sol" if asset == "SOL" else "meme", "symbol": None if asset == "SOL" else asset,
        "runner": e.get("runner") or runner, "pause_keys": list(e.get("pause_keys") or [name]),
        "parent": e.get("parent"), "params_diff": e.get("params_diff") or {}, "kind": e.get("kind"),
        "source": e.get("source"), "hyp": hyp, "lineage": e.get("lineage"),
    }


def classify(name: str, entry: dict | None = None, registry: dict | None = None) -> dict | None:
    """meta de um portfólio: entrada do registry do lab (hipóteses e forks), original de bot, hipótese ainda não
    criada, ou nome com sufixo _baseline/_relaxed/_article (portfólios extra de models.json). None se desconhecido."""
    from bot import lab_registry as R
    if entry is not None:
        return _meta_from(name, entry, entry.get("runner") or "lab_bot")
    reg = registry if registry is not None else _registry()
    e = (reg.get("portfolios") or {}).get(name)
    if e is not None:
        return _meta_from(name, e, "lab_bot")
    o = R.originals().get(name)
    if o is not None:
        return _meta_from(name, o, o.get("runner") or "sol_bot")
    for h in R.hypothesis_defs():
        if h["name"] == name:
            return _meta_from(name, h, "lab_bot")
    for suf, prof in (("_relaxed", "relaxed"), ("_baseline", "baseline"), ("_article", "baseline")):
        if name.endswith(suf) and "_" in name:
            return _meta_from(name, {"test_type": "model_gated", "profile": prof, "model": name.split("_")[0],
                                     "asset": "SOL", "kind": "gated"}, "sol_bot")
    return None


def all_names(registry: dict | None = None) -> list[str]:
    """Todos os portfólios conhecidos: originais dos bots, hipóteses (criadas ou não) e entradas do registry (forks)."""
    from bot import lab_registry as R
    reg = registry if registry is not None else _registry()
    out = list(R.originals())
    for h in R.hypothesis_defs():
        if h["name"] not in out:
            out.append(h["name"])
    for n in (reg.get("portfolios") or {}):
        if n not in out:
            out.append(n)
    return out


# ---------------------------------------------------------------- merge, camadas e validação

def _mark(v, label, prov, path):
    if isinstance(v, dict) and v:
        for k, v2 in v.items():
            _mark(v2, label, prov, f"{path}.{k}")
    else:
        prov[path] = label


def _merge(dst: dict, src: dict, label: str, prov: dict, prefix: str = ""):
    for k, v in src.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v, label, prov, path + ".")
        else:
            dst[k] = copy.deepcopy(v)
            for p in [p for p in prov if p == path or p.startswith(path + ".")]:
                del prov[p]
            _mark(v, label, prov, path)


def _params_of(layer: dict) -> dict:
    return {k: v for k, v in (layer or {}).items() if k in GROUPS}


def check_layer(layer, label: str, extra=()) -> list[str]:
    """Chaves desconhecidas numa camada (erros de digitação não passam em silêncio)."""
    if layer is None:
        return []
    if not isinstance(layer, dict):
        return [f"{label}: camada tem de ser um objeto"]
    errs = []
    for k, v in layer.items():
        if k.startswith("_") or k in DOC_KEYS or k in extra:
            continue
        if k not in GROUPS:
            errs.append(f"{label}: chave desconhecida '{k}'")
            continue
        if k == "hours":
            continue
        if not isinstance(v, dict):
            errs.append(f"{label}.{k}: tem de ser um objeto")
            continue
        for kk in v:
            if kk.startswith("_") or kk in DOC_KEYS:
                continue
            if kk not in SCHEMA[k]:
                errs.append(f"{label}.{k}: chave desconhecida '{kk}'")
    return errs


def check_doc(doc) -> list[str]:
    if not isinstance(doc, dict):
        return ["params.json: raiz tem de ser um objeto"]
    errs = [f"params.json: chave de topo desconhecida '{k}'" for k in doc if k not in TOP_KEYS and not k.startswith("_")]
    if doc.get("paper_only") is not True:
        errs.append("params.json: paper_only tem de ser true")
    for k in ("defaults", "profiles", "types", "models", "assets", "portfolios"):
        if k in doc and not isinstance(doc[k], dict):
            errs.append(f"params.json: '{k}' tem de ser um objeto")
    return errs


def overlay_layer(meta: dict, overlay: dict | None) -> tuple[dict, bool, list[str]]:
    """(camada, paused, avisos) do overlay do dashboard para este portfólio. Aceita chaves planas antigas
    (min_confidence, cooldown_seconds, ...) e grupos aninhados. O overlay nunca mexe em limits/tuning."""
    ports = (overlay or {}).get("portfolios") or {}
    paused = any(bool((ports.get(k) or {}).get("paused")) for k in (meta.get("pause_keys") or [meta["name"]]))
    ov = ports.get(meta["name"]) or {}
    layer, warn = {}, []
    for k, v in ov.items():
        if k == "paused" or v is None:
            continue
        if k in OVERLAY_FLAT:
            layer.setdefault("gates", {})[k] = v
        elif k in ("limits", "tuning"):
            warn.append(f"overlay: '{k}' não pode ser alterado em tempo real (ignorado)")
        elif k in GROUPS:
            if isinstance(v, dict) and isinstance(layer.get(k), dict):
                layer[k].update(v)
            else:
                layer[k] = v
    return layer, paused, warn


def resolve(meta: dict, doc: dict, overlay: dict | None = None, registry: dict | None = None,
            _depth: int = 0) -> tuple[dict, dict, list[str]]:
    """-> (efetivo, proveniência {caminho: camada}, erros de estrutura). Não valida valores (ver validate)."""
    errs: list[str] = []
    eff: dict = {}
    prov: dict = {}
    name = meta["name"]
    layers: list[tuple[str, dict, tuple]] = []
    if meta.get("parent"):
        if _depth > 20:
            return eff, prov, [f"{name}: cadeia de forks demasiado longa"]
        pmeta = classify(meta["parent"], registry=registry)
        if pmeta is None:
            errs.append(f"{name}: pai desconhecido '{meta['parent']}'")
        else:
            eff, prov, perr = resolve(pmeta, doc, None, registry, _depth + 1)
            errs += perr
        layers.append((f"fork:{name}", meta.get("params_diff") or {}, ()))
    else:
        layers.append(("defaults", doc.get("defaults") or {}, ()))
        profiles = doc.get("profiles") or {}
        chain, cur, seen = [], meta.get("profile") or "baseline", set()
        while cur:
            if cur in seen:
                errs.append(f"profiles: extends em ciclo em '{cur}'")
                break
            seen.add(cur)
            lay = profiles.get(cur)
            if lay is None:
                errs.append(f"{name}: perfil desconhecido '{cur}'")
                break
            chain.append((cur, lay))
            cur = lay.get("extends") if isinstance(lay, dict) else None
        for pn, lay in reversed(chain):
            layers.append((f"profiles.{pn}", lay, ("extends",)))
        t = meta.get("test_type")
        tl = (doc.get("types") or {}).get(t) if t else None
        if tl is None:
            errs.append(f"{name}: tipo de teste desconhecido '{t}'")
        else:
            layers.append((f"types.{t}", tl, ("variants",)))
            v = meta.get("variant")
            if v:
                vl = (tl.get("variants") or {}).get(v)
                if vl is None:
                    errs.append(f"{name}: variante desconhecida '{t}.variants.{v}'")
                else:
                    layers.append((f"types.{t}.variants.{v}", vl, ()))
        m = meta.get("model")
        if m and m in (doc.get("models") or {}):
            layers.append((f"models.{m}", doc["models"][m], ()))
        ac = meta.get("asset_class") or "sol"
        al = (doc.get("assets") or {}).get(ac)
        if al is not None:
            layers.append((f"assets.{ac}", al, ("symbols",)))
            sym = meta.get("symbol")
            sl = ((al.get("symbols") or {}) if isinstance(al, dict) else {}).get(sym) if sym else None
            if sl is not None:
                layers.append((f"assets.{ac}.symbols.{sym}", sl, ()))
    pl = (doc.get("portfolios") or {}).get(name)
    if pl is not None:
        layers.append((f"portfolios.{name}", pl, ()))
    for label, lay, extra in layers:
        errs += check_layer(lay, label, extra)
        if isinstance(lay, dict):
            _merge(eff, _params_of(lay), label, prov)
    paused = False
    if overlay is not None:
        ol, paused, warn = overlay_layer(meta, overlay)
        errs += check_layer(ol, "overlay")
        _merge(eff, ol, "overlay", prov)
        errs += warn
    eff["paused"] = paused
    eff["paper_only"] = True
    return eff, prov, errs


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate(eff: dict, meta: dict | None = None) -> list[str]:
    """Valores e limites de segurança. Lista vazia = válido."""
    E: list[str] = []
    meta = meta or {}

    def chk(path, v, lo=None, hi=None, integer=False, none_ok=False, lo_open=False):
        if v is None and none_ok:
            return
        if not _num(v):
            E.append(f"{path}: tem de ser número (recebido {v!r})")
            return
        if integer and float(v) != int(v):
            E.append(f"{path}: tem de ser inteiro")
        if lo is not None and (v <= lo if lo_open else v < lo):
            E.append(f"{path}: {v} abaixo do mínimo {lo}")
        if hi is not None and v > hi:
            E.append(f"{path}: {v} acima do máximo {hi}")

    if eff.get("paper_only") is not True:
        E.append("paper_only tem de ser true")
    lim = eff.get("limits") or {}
    for k, cap in ABSOLUTE.items():
        chk(f"limits.{k}", lim.get(k), 0, cap, lo_open=True)
    if lim.get("leverage", "never") != "never":
        E.append("limits.leverage: só 'never' (sem alavancagem)")
    bmax = lim.get("buy_fraction_usdt_max") if _num(lim.get("buy_fraction_usdt_max")) else 0.5
    tmax = lim.get("max_trades_per_hour_max") if _num(lim.get("max_trades_per_hour_max")) else 8
    xmax = lim.get("max_exposure_frac_max") if _num(lim.get("max_exposure_frac_max")) else 1.0

    g = eff.get("gates") or {}
    for k in ("min_confidence", "min_prob_margin", "max_skip_noul"):
        chk(f"gates.{k}", g.get(k), 0.0, 1.0)
    chk("gates.cooldown_seconds", g.get("cooldown_seconds"), 0, 86400, integer=True)
    chk("gates.max_trades_per_hour", g.get("max_trades_per_hour"), 1, tmax, integer=True)
    chk("gates.buy_fraction_usdt", g.get("buy_fraction_usdt"), 0.0, bmax, lo_open=True)
    chk("gates.min_usdt_trade", g.get("min_usdt_trade"), 0.0)
    chk("gates.min_sol_trade", g.get("min_sol_trade"), 0.0)
    chk("gates.max_exposure_frac", g.get("max_exposure_frac"), 0.0, xmax, none_ok=True, lo_open=True)
    if not isinstance(g.get("margin_gate"), bool):
        E.append("gates.margin_gate: tem de ser true/false")

    ex = eff.get("exec") or {}
    if ex.get("mode") not in ("market", "limit"):
        E.append(f"exec.mode: 'market' ou 'limit' (recebido {ex.get('mode')!r})")
    for k in ("extra_slippage_bps", "slippage_bps", "offset_bps", "fee_bps"):
        chk(f"exec.{k}", ex.get(k), 0, 1000)
    chk("exec.ttl_min", ex.get("ttl_min"), 0, 1440, lo_open=True)
    chk("exec.network_fee_sol", ex.get("network_fee_sol"), 0.0, 0.01)

    xt = eff.get("exits") or {}
    if not isinstance(xt.get("enabled"), bool):
        E.append("exits.enabled: tem de ser true/false")
    if xt.get("enabled"):
        for k in ("tp", "sl", "trail"):
            chk(f"exits.{k}", xt.get(k), 0.0, 1.0, lo_open=True)
        chk("exits.trail_arm", xt.get("trail_arm", xt.get("trail")), 0.0, 1.0)
        chk("exits.reentry_cooldown_min", xt.get("reentry_cooldown_min", 30), 0, 10080)

    h = eff.get("hours")
    if h is not None:
        if not isinstance(h, list) or not h or not all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 23 for x in h):
            E.append(f"hours: null ou lista não vazia de horas BRT 0..23 (recebido {h!r})")

    rf = eff.get("regime_filter") or {}
    for k in SCHEMA["regime_filter"]:
        if not isinstance(rf.get(k), bool):
            E.append(f"regime_filter.{k}: tem de ser true/false")

    en = eff.get("ensemble")
    if en is not None:
        chk("ensemble.min_agree", en.get("min_agree"), 1, 3, integer=True)
        chk("ensemble.pct_threshold", en.get("pct_threshold"), 0.0, 1.0)
        chk("ensemble.min_window", en.get("min_window"), 1, integer=True)

    ru = eff.get("rule") or {}
    tt = meta.get("test_type")
    need = {"rule_grid": ("grid_pct", "levels"), "rule_rsi": ("rsi_period", "lo", "hi"),
            "rule_regime": ("ema_fast", "ema_slow"), "rule_donchian": ("ema_fast", "ema_slow", "donchian")}.get(tt, ())
    for k in need:
        if k not in ru:
            E.append(f"rule.{k}: obrigatório para {tt}")
    if "grid_pct" in ru:
        chk("rule.grid_pct", ru["grid_pct"], 0.0, 0.5, lo_open=True)
    for k in ("levels", "rsi_period", "ema_fast", "ema_slow", "donchian"):
        if k in ru:
            chk(f"rule.{k}", ru[k], 1, 1000, integer=True)
    for k in ("lo", "hi"):
        if k in ru:
            chk(f"rule.{k}", ru[k], 0, 100)
    if _num(ru.get("ema_fast")) and _num(ru.get("ema_slow")) and ru["ema_fast"] >= ru["ema_slow"]:
        E.append("rule.ema_fast tem de ser menor que rule.ema_slow")
    if _num(ru.get("lo")) and _num(ru.get("hi")) and ru["lo"] >= ru["hi"]:
        E.append("rule.lo tem de ser menor que rule.hi")

    tu = eff.get("tuning") or {}
    for p in tu.get("params") or []:
        sect = str(p).split(".", 1)[0]
        if "." not in str(p) or sect not in GROUPS or str(p).split(".", 1)[1] not in SCHEMA.get(sect, ()):
            E.append(f"tuning.params: caminho desconhecido '{p}'")
    for p, b in (tu.get("bounds") or {}).items():
        if not (isinstance(b, list) and len(b) == 2 and _num(b[0]) and _num(b[1]) and b[0] <= b[1]):
            E.append(f"tuning.bounds.{p}: [mín, máx] com mín ≤ máx")
    if "max_rel_change" in tu:
        chk("tuning.max_rel_change", tu["max_rel_change"], 0.0, 1.0, lo_open=True)
    if "steps" in tu and not (isinstance(tu["steps"], list) and all(_num(s) and s > 0 for s in tu["steps"])):
        E.append("tuning.steps: lista de multiplicadores positivos")

    runner = meta.get("runner")
    if runner == "rules_bot":
        if xt.get("enabled") or h is not None or ex.get("mode") == "limit" or rf.get("enabled"):
            E.append("rules_bot não suporta exits/hours/exec.mode=limit/regime_filter (use um portfólio do lab)")
    elif runner in ("sol_bot", "meme_bot") and ex.get("mode") == "limit":
        E.append(f"{runner}: exec.mode=limit só existe no lab_bot")
    if meta.get("kind") == "ensemble" and en is None:
        E.append("ensemble: obrigatório para portfólios kind=ensemble")
    return E


# ---------------------------------------------------------------- store (hot reload, fail-closed)

class Store:
    def __init__(self, path: Path | None = None, overlay: Path | None = None, min_interval: float = 1.0, log=print):
        self._path = path
        self._ov_path = overlay
        self.min_interval = min_interval
        self.log = log
        self._doc = None
        self._doc_key = None
        self.doc_errors: list[str] = []
        self._ov = {}
        self._ov_key = None
        self._reg_key = None
        self._last_stat = 0.0
        self._ver = 0
        self._cache: dict = {}
        self._last_valid: dict = {}
        self.errors: dict = {}
        self._reported: dict = {}

    @property
    def path(self) -> Path:
        return Path(self._path) if self._path else params_path()

    @property
    def ov_path(self) -> Path:
        return Path(self._ov_path) if self._ov_path else overlay_path()

    @staticmethod
    def _key(p: Path):
        try:
            st = p.stat()
            return (st.st_mtime_ns, st.st_size)
        except FileNotFoundError:
            return None

    def refresh(self, force: bool = False):
        now = time.time()
        if not force and now - self._last_stat < self.min_interval:
            return
        self._last_stat = now
        changed = False
        k = self._key(self.path)
        if k != self._doc_key:
            self._doc_key = k
            changed = True
            try:
                doc = json.loads(self.path.read_text())
                errs = check_doc(doc)
            except Exception as e:
                doc, errs = None, [f"params.json ilegível ({self.path}): {type(e).__name__}: {e}"]
            if errs:
                self.doc_errors = errs
                self.log(f"params: {errs[0]} — mantenho os últimos parâmetros válidos", flush=True)
            else:
                self.doc_errors = []
                self._doc = doc
        k = self._key(self.ov_path)
        if k != self._ov_key:
            self._ov_key = k
            changed = True
            if k is None:
                self._ov = {}
            else:
                try:
                    self._ov = json.loads(self.ov_path.read_text()) or {}
                except Exception as e:
                    self.log(f"params: overlay ilegível ({type(e).__name__}) — mantenho o anterior", flush=True)
        from bot import lab_registry as R
        k = R.mtime()
        if k != self._reg_key:
            self._reg_key = k
            changed = True
        if changed:
            self._ver += 1

    def doc(self) -> dict | None:
        self.refresh()
        return self._doc

    def overlay(self) -> dict:
        self.refresh()
        return self._ov

    def explain(self, name: str, meta: dict | None = None, *, use_overlay: bool = True, registry: dict | None = None,
                doc: dict | None = None, overlay: dict | None = None):
        """-> (efetivo, proveniência, erros, meta). Sem fail-closed (para dashboard, nightly e params_check)."""
        doc = doc if doc is not None else self.doc()
        m = classify(name, entry=meta, registry=registry)
        if m is None:
            return copy.deepcopy(FAILSAFE), {}, [f"{name}: portfólio desconhecido"], {"name": name}
        if doc is None:
            return copy.deepcopy(FAILSAFE), {}, list(self.doc_errors) or ["params.json em falta"], m
        ov = (overlay if overlay is not None else self.overlay()) if use_overlay else None
        eff, prov, errs = resolve(m, doc, ov, registry)
        errs = errs + validate(eff, m)
        return eff, prov, errs, m

    def effective(self, name: str, meta: dict | None = None, registry: dict | None = None) -> dict:
        """Parâmetros efetivos validados. Em erro: últimos válidos deste portfólio; senão os estáticos (sem overlay)
        se forem válidos; senão FAILSAFE (artigo + paused). Nunca levanta exceção."""
        try:
            self.refresh()
            hit = self._cache.get(name)
            if hit is not None and hit[0] == self._ver:
                return copy.deepcopy(hit[1])  # cópia: nenhum bot altera o cache por engano
            eff, _prov, errs, m = self.explain(name, meta, registry=registry)
            if errs:
                self._report(name, errs)
                if name in self._last_valid:
                    out = copy.deepcopy(self._last_valid[name])
                else:
                    st, _p, errs2, _m = self.explain(name, meta, use_overlay=False, registry=registry)
                    if errs2:
                        out = copy.deepcopy(FAILSAFE)
                    else:
                        out = st
                        out["paused"] = overlay_layer(m, self._ov)[1]  # pausar é sempre seguro
            else:
                self.errors.pop(name, None)
                self._reported.pop(name, None)
                self._last_valid[name] = copy.deepcopy(eff)
                out = eff
            self._cache[name] = (self._ver, out)
            return copy.deepcopy(out)
        except Exception as e:  # nunca derruba um bot
            self._report(name, [f"erro interno do resolver: {type(e).__name__}: {e}"])
            return copy.deepcopy(self._last_valid.get(name) or FAILSAFE)

    def _report(self, name, errs):
        self.errors[name] = list(errs)
        key = tuple(errs)
        if self._reported.get(name) != key:
            self._reported[name] = key
            self.log(f"params: {name} inválido ({'; '.join(errs[:3])}) — fail-closed nos últimos parâmetros válidos",
                     flush=True)


STORE = Store()


def effective(name: str, meta: dict | None = None, registry: dict | None = None) -> dict:
    return STORE.effective(name, meta, registry)


def explain(name: str, meta: dict | None = None, **kw):
    return STORE.explain(name, meta, **kw)


def type_view(test_type: str, profile: str | None = None, asset_class: str = "sol", doc: dict | None = None):
    """Parâmetros de um tipo de teste sem camada de portfólio (dashboard: vista por tipo)."""
    doc = doc if doc is not None else STORE.doc()
    if doc is None:
        return copy.deepcopy(FAILSAFE), {}, list(STORE.doc_errors)
    prof = profile or ("relaxed" if test_type in ("hybrid", "lab_h1_exits", "lab_h3_limit", "lab_h4_hours") else "baseline")
    meta = {"name": f"<tipo:{test_type}>", "test_type": test_type, "profile": prof, "asset_class": asset_class,
            "variant": None, "model": None, "symbol": None, "runner": None}
    eff, prov, errs = resolve(meta, doc)
    return eff, prov, errs + validate(eff, meta)


# ---------------------------------------------------------------- escrita (dashboard) com validação

def _set_path(d: dict, dotted: str, value):
    ks = dotted.split(".")
    for k in ks[:-1]:
        d = d.setdefault(k, {})
    d[ks[-1]] = value


def _unset_path(d: dict, dotted: str):
    ks = dotted.split(".")
    for k in ks[:-1]:
        d = d.get(k)
        if not isinstance(d, dict):
            return
    d.pop(ks[-1], None)


def apply_patch(layer: dict, patch: dict) -> dict:
    """{"set": {grupo: {...}}, "unset": ["grupo.chave"]} (ou só o objeto de set). Devolve a camada nova."""
    out = copy.deepcopy(layer or {})
    patch = patch if isinstance(patch, dict) else {}
    if "set" in patch or "unset" in patch:
        sets, unsets = patch.get("set") or {}, patch.get("unset") or []
    else:
        sets, unsets = patch, []
    for g, vals in sets.items():
        if isinstance(vals, dict) and isinstance(out.get(g), dict):
            _merge(out[g], vals, "", {})
        else:
            out[g] = copy.deepcopy(vals)
    for p in unsets:
        _unset_path(out, str(p))
    return out


def check_all(doc: dict, registry: dict | None = None, overlay: dict | None = None, names=None) -> dict:
    """{nome: [erros]} para todos os portfólios conhecidos com o documento dado (só os com erros)."""
    reg = registry if registry is not None else _registry()
    out = {}
    for n in names or all_names(reg):
        m = classify(n, registry=reg)
        if m is None:
            out[n] = ["portfólio desconhecido"]
            continue
        eff, _prov, errs = resolve(m, doc, overlay, reg)
        errs = errs + validate(eff, m)
        if errs:
            out[n] = errs
    return out


def write_layer(section: str, key: str, patch: dict, who: str = "dashboard", path: Path | None = None) -> dict:
    """Edita params.json (types/profiles/models/assets/portfolios) com validação de TODOS os portfólios antes de gravar.
    Escrita atómica; cada mudança vai para logs/param_changes.jsonl. Levanta ValueError com os erros."""
    if section not in ("types", "profiles", "models", "assets", "portfolios", "defaults"):
        raise ValueError(f"secção inválida: {section}")
    path = Path(path) if path else params_path()
    doc = json.loads(path.read_text())
    old = copy.deepcopy(doc.get(section, {}).get(key) if section != "defaults" else doc.get("defaults"))
    if section != "defaults" and section != "portfolios" and old is None:
        raise ValueError(f"{section}.{key} não existe (crie-o no ficheiro)")
    new = apply_patch(old or {}, patch)
    errs = check_layer(new, f"{section}.{key}", ("variants", "extends", "symbols"))
    new_doc = copy.deepcopy(doc)
    if section == "defaults":
        new_doc["defaults"] = new
    else:
        new_doc.setdefault(section, {})[key] = new
    errs += check_doc(new_doc)
    bad = check_all(new_doc)
    if section == "portfolios":
        reg = _registry()
        if key not in all_names(reg):
            errs.append(f"portfolios.{key}: portfólio desconhecido")
    if errs or bad:
        raise ValueError(json.dumps({"layer": errs, "portfolios": bad}, ensure_ascii=False))
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(new_doc, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)
    changes = _diff_paths(old or {}, new)
    log = ROOT / "logs" / "param_changes.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as f:
        for p, (a, b) in changes.items():
            f.write(json.dumps({"ts": time.time(), "ts_brt": datetime.now().astimezone().isoformat(),
                                "type": "params_json", "layer": f"{section}.{key}", "field": p, "old": a, "new": b,
                                "who": who}, ensure_ascii=False) + "\n")
    STORE.refresh(force=True)
    return {"layer": f"{section}.{key}", "changes": {p: {"old": a, "new": b} for p, (a, b) in changes.items()}}


def _flat_leaves(d, prefix=""):
    out = {}
    if isinstance(d, dict) and d:
        for k, v in d.items():
            out.update(_flat_leaves(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = d
    return out


def _diff_paths(a: dict, b: dict) -> dict:
    fa, fb = _flat_leaves(a), _flat_leaves(b)
    return {k: (fa.get(k), fb.get(k)) for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)}


def check_overlay_patch(name: str, overlay: dict) -> list[str]:
    """Erros que um overlay novo causaria a este portfólio (o dashboard recusa antes de gravar)."""
    eff, _p, errs, _m = STORE.explain(name, overlay=overlay)
    return errs


# ---------------------------------------------------------------- ajudas para os bots

def fees_market(eff: dict, cfg: dict) -> tuple[dict, dict]:
    """fees/market do config.json com custos da execução simulada vindos de exec."""
    ex = eff.get("exec") or {}
    fees = dict(cfg.get("fees") or {})
    market = dict(cfg.get("market") or {})
    if "extra_slippage_bps" in ex:
        fees["extra_slippage_bps"] = ex["extra_slippage_bps"]
    if "network_fee_sol" in ex:
        fees["assumed_network_fee_sol"] = ex["network_fee_sol"]
    if "slippage_bps" in ex:
        market["slippage_bps"] = ex["slippage_bps"]
    return fees, market


def qty_of(pdata: dict) -> float:
    return float(pdata.get("sol") or 0) if pdata.get("asset_mode", "sol") == "sol" else float(pdata.get("token") or 0)


def cap_buy(gates: dict, pdata: dict, price: float) -> tuple[dict, str | None]:
    """gates.max_exposure_frac: a compra nunca leva a exposição ao ativo acima do teto (fração do valor do portfólio).
    Reduz a fração da compra até caber; sem espaço para min_usdt_trade → (gates, 'max_exposure')."""
    cap = gates.get("max_exposure_frac")
    if cap is None:
        return gates, None
    pos = qty_of(pdata) * float(price or 0)
    usdt = float(pdata.get("usdt") or 0)
    room = float(cap) * (usdt + pos) - pos
    if usdt <= 0 or room < float(gates.get("min_usdt_trade", 1.0)):
        return gates, "max_exposure"
    if usdt * float(gates["buy_fraction_usdt"]) <= room:
        return gates, None
    g = dict(gates)
    g["buy_fraction_usdt"] = room / usdt
    return g, None


def regime_block(eff: dict, chosen: str, bull) -> tuple[str, list[str]]:
    """Filtro de regime de SOL nas compras (híbridos). bull None = regime desconhecido."""
    rf = eff.get("regime_filter") or {}
    if not rf.get("enabled") or chosen != "buy":
        return chosen, []
    if bull is None:
        return ("hold", ["sol_regime_unknown"]) if rf.get("block_if_unknown", True) else (chosen, [])
    if rf.get("require_bull_for_buy", True) and not bull:
        return "hold", ["sol_regime_bear_block_buy"]
    return chosen, []


def sol_regime_bull(root: Path | None = None):
    """Regime de SOL publicado pelo rules_bot (data/rules/status.json); None se indisponível."""
    try:
        st = json.loads(((root or ROOT) / "data" / "rules" / "status.json").read_text())
    except Exception:
        return None
    return ((st.get("indicators") or {}).get("sol") or {}).get("regime_bull")


def outside_hours(eff: dict, hour: int) -> bool:
    h = eff.get("hours")
    return h is not None and hour not in h


def check_exit(pdata: dict, ex: dict, px: float) -> str | None:
    """TP/SL/trailing sobre a posição (sol_bot/meme_bot). Sem preço de entrada registado, começa a contar agora."""
    if not ex or not ex.get("enabled") or qty_of(pdata) * px < 1.0:
        return None
    entry = float(pdata.get("entry_price") or 0)
    if entry <= 0:
        pdata["entry_price"] = px
        pdata["peak_price"] = px
        return None
    peak = max(float(pdata.get("peak_price") or entry), px)
    pdata["peak_price"] = peak
    r = px / entry - 1
    if r >= float(ex["tp"]):
        return "take_profit"
    if r <= -float(ex["sl"]):
        return "stop_loss"
    if peak / entry - 1 >= float(ex.get("trail_arm", ex["trail"])) and px <= peak * (1 - float(ex["trail"])):
        return "trailing_stop"
    return None


def track_fill(pdata: dict, side: str, before_qty: float, fill: dict, px: float):
    """Preço médio de entrada e pico (para as saídas)."""
    if side == "buy":
        got = float(fill.get("sol_out_net") or fill.get("token_out_net") or 0)
        cost = float(fill.get("usdt_in") or 0)
        prev = float(pdata.get("entry_price") or px)
        tot = before_qty + got
        pdata["entry_price"] = ((before_qty * prev) + cost) / tot if tot > 0 else px
        pdata["peak_price"] = max(float(pdata.get("peak_price") or 0), px) if before_qty > 0 else px
    else:
        pdata["entry_price"] = None
        pdata["peak_price"] = None


def pre_gate(eff: dict, chosen: str, pdata: dict, hour: int, now: float) -> list[str]:
    """Motivos para segurar antes dos portões (sol_bot/meme_bot): horário e reentrada bloqueada após uma saída.
    O filtro de regime é à parte (regime_block), porque muda a ação registada como antes no híbrido."""
    reasons = []
    if chosen in ("buy", "sell") and outside_hours(eff, hour):
        reasons.append("outside_hours")
    if chosen == "buy" and (eff.get("exits") or {}).get("enabled") and now < float(pdata.get("reentry_block_until") or 0):
        reasons.append("reentry_cooldown")
    return reasons


def summary(eff: dict) -> str:
    """Resumo de uma linha dos parâmetros efetivos (relatórios)."""
    g = eff.get("gates") or {}
    parts = [f"conf≥{g.get('min_confidence')}" + (f" margem≥{g.get('min_prob_margin')}" if g.get("margin_gate") else "")
             + f" skip<{g.get('max_skip_noul')}", f"cooldown {g.get('cooldown_seconds')}s", f"≤{g.get('max_trades_per_hour')}/h",
             f"compra {float(g.get('buy_fraction_usdt') or 0) * 100:g}% USDT"]
    if g.get("max_exposure_frac") is not None:
        parts.append(f"exposição ≤{float(g['max_exposure_frac']) * 100:g}%")
    ex = eff.get("exits") or {}
    if ex.get("enabled"):
        parts.append(f"saídas TP {float(ex['tp']) * 100:g}% / SL {float(ex['sl']) * 100:g}% / trailing {float(ex['trail']) * 100:g}%"
                     f" (arma +{float(ex.get('trail_arm', ex['trail'])) * 100:g}%), reentrada {ex.get('reentry_cooldown_min')} min")
    xe = eff.get("exec") or {}
    if xe.get("mode") == "limit":
        parts.append(f"limite mid∓{xe.get('offset_bps')} bps, {xe.get('ttl_min')} min, taxa {xe.get('fee_bps')} bps")
    if eff.get("hours") is not None:
        parts.append(f"horas BRT {eff['hours']}")
    if (eff.get("regime_filter") or {}).get("enabled"):
        parts.append("filtro de regime SOL nas compras")
    en = eff.get("ensemble")
    if en:
        parts.append(f"ensemble ≥{en.get('min_agree')} modelos, percentil ≥{en.get('pct_threshold')}, janela ≥{en.get('min_window')}")
    ru = eff.get("rule")
    if ru:
        parts.append("regra " + ", ".join(f"{k}={v}" for k, v in ru.items() if k != "timeframe"))
    if eff.get("paused"):
        parts.append("PAUSADO")
    return " · ".join(parts)
