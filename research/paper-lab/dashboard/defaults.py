"""Default gate params per portfolio (mirrors config.json)."""
from __future__ import annotations
import json
from pathlib import Path

import sys as _sys_paths
_LAB = str(Path(__file__).resolve().parents[1])  # código do lab (research/paper-lab)
if _LAB not in _sys_paths.path:
    _sys_paths.path.insert(0, _LAB)
from bot.paths import ROOT, LAB_DIR  # noqa: E402  (ROOT = PAPER_LAB_ROOT ou a pasta do lab)

EDITABLE = (
    "min_confidence", "min_prob_margin", "max_skip_noul",
    "buy_fraction_usdt", "cooldown_seconds", "max_trades_per_hour",
)

def load_cfg():
    return json.loads((ROOT / "config.json").read_text())

def default_for(portfolio: str) -> dict:
    cfg = load_cfg()
    base = dict(cfg["gates"])
    rel = dict(cfg.get("gates_relaxed") or base)
    rel.setdefault("min_prob_margin", 0.20)
    base.setdefault("min_prob_margin", 0.0)
    if portfolio in ("relaxed",) or portfolio.endswith("_relaxed") or portfolio == "v2":
        return {k: rel.get(k) for k in EDITABLE}
    if portfolio.endswith("_article"):
        return {k: base.get(k) for k in EDITABLE}
    # baseline / *_baseline / meme baselines
    return {k: base.get(k) for k in EDITABLE}

def validate_patch(field: str, value) -> tuple[bool, str, float|int]:
    try:
        if field in ("min_confidence", "min_prob_margin", "max_skip_noul", "buy_fraction_usdt"):
            v = float(value)
        else:
            v = int(value)
    except Exception:
        return False, "invalid number", 0
    if field in ("min_confidence", "min_prob_margin", "max_skip_noul"):
        if not (0.0 <= v <= 1.0):
            return False, "must be 0..1", v
    if field == "buy_fraction_usdt":
        if not (0.05 <= v <= 1.0):
            return False, "buy fraction must be 0.05..1", v
    if field == "cooldown_seconds":
        if v < 15:
            return False, "cooldown >= 15s", v
    if field == "max_trades_per_hour":
        if not (1 <= v <= 60):
            return False, "max/h must be 1..60", v
    return True, "ok", v
