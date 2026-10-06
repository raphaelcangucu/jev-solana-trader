"""Catálogo atual do run ao vivo, a partir de um instantâneo só de leitura dos ficheiros de configuração.

`snapshot()` copia (nunca escreve no run ao vivo) config.json, params.json, models.json, memecoins.json, critérios,
`data/lab/registry.json`, `data/lab/criteria/*.json` e `data/params_overlay.json` para `<run>/inputs/`. O backtest
aponta `PAPER_LAB_ROOT` para essa pasta ANTES de importar `bot.*`, e o resolver de parâmetros (bot/params.py) e o
registry (bot/lab_registry.py) leem o instantâneo — os mesmos parâmetros efetivos do run ao vivo no instante da cópia.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

FILES = ["config.json", "params.json", "models.json", "memecoins.json", "criteria_baseline.json", "criteria_v2.json",
         "data/lab/registry.json", "data/params_overlay.json"]


def snapshot(live_root: Path, dest: Path) -> dict:
    """Cópia dos ficheiros de configuração do run ao vivo. Devolve {ficheiro: sha256[:16]}."""
    dest.mkdir(parents=True, exist_ok=True)
    out = {}
    for rel in FILES:
        src = live_root / rel
        if not src.exists():
            continue
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        out[rel] = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
    cdir = live_root / "data" / "lab" / "criteria"
    if cdir.exists():
        for f in sorted(cdir.glob("*.json")):
            dst = dest / "data" / "lab" / "criteria" / f.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            out[f"data/lab/criteria/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    for d in ("logs", "data/rules", "data/meme", "reports"):
        (dest / d).mkdir(parents=True, exist_ok=True)
    return out


SOL_GATED = ("baseline", "relaxed", "v2", "laya_baseline", "laya_relaxed", "poorjev_baseline", "poorjev_relaxed")


def family_of(name: str, meta: dict) -> str:
    asset = meta.get("asset") or "SOL"
    cls = "SOL" if asset == "SOL" else "Meme"
    if meta.get("parent"):
        return f"{cls} · forks"
    if meta.get("hyp"):
        return f"{cls} · hipóteses (lab)"
    kind = meta.get("kind")
    if kind == "rule":
        return f"{cls} · regras"
    if meta.get("test_type") == "hybrid":
        return f"{cls} · híbridos"
    model = (meta.get("model") or "").split("+")[0]
    return f"{cls} · {model or '?'}"


def build(models_cfg: dict, jev_ready: bool) -> list[dict]:
    """Lista de portfólios do catálogo atual: originais dos bots, Jev (models.json), hipóteses e forks do registry.
    Cada item: name, meta (para P.effective), family, asset, model, test_type, profile, parent, is_fork, label, runner."""
    from bot import lab_registry as R
    from bot import params as P
    reg = R.load()
    items = []
    seen = set()

    def add(name, meta, runner):
        if name in seen:
            return
        seen.add(name)
        m = P.classify(name, registry=reg) or {}
        items.append({
            "name": name, "meta": meta, "runner": runner, "family": family_of(name, meta),
            "asset": meta.get("asset") or "SOL", "model": meta.get("model"),
            "test_type": m.get("test_type") or meta.get("test_type"), "profile": meta.get("profile"),
            "parent": meta.get("parent"), "is_fork": bool(meta.get("parent")),
            "label": meta.get("label") or name, "kind": meta.get("kind"),
        })

    for n, m in R.originals().items():
        add(n, dict(m, name=n), m["runner"])
    for mid, b in (models_cfg.get("backends") or {}).items():
        if mid == "von" or not b.get("enabled"):
            continue
        if b.get("kind") == "hosted_typesafe" and not jev_ready:
            continue
        for pname in b.get("sol_portfolios") or []:
            if pname in seen:
                continue
            prof = "relaxed" if pname.endswith("_relaxed") else "baseline"
            add(pname, {"name": pname, "asset": "SOL", "kind": "gated", "model": mid, "profile": prof,
                        "test_type": "model_gated", "runner": "sol_bot", "label": f"{b.get('label') or mid} {prof}"},
                "sol_bot")
    for n, e in (reg.get("portfolios") or {}).items():
        if e.get("status", "active") != "active":
            continue
        add(n, dict(e, name=n), "rules_bot" if R.is_rule_fork(e) else "lab_bot")
    return items
