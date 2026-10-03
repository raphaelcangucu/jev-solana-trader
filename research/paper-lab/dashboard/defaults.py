"""Parâmetros por portfólio para o dashboard: valores vêm de params.json via bot/params.py (sem overlay = "padrão")."""
from __future__ import annotations
import json
from pathlib import Path

import sys as _sys_paths
_LAB = str(Path(__file__).resolve().parents[1])  # código do lab (research/paper-lab)
if _LAB not in _sys_paths.path:
    _sys_paths.path.insert(0, _LAB)
from bot.paths import ROOT, LAB_DIR  # noqa: E402  (ROOT = PAPER_LAB_ROOT ou a pasta do lab)
from bot import params as P  # noqa: E402

EDITABLE = P.EDITABLE


def load_cfg():
    return json.loads((ROOT / "config.json").read_text())


def _virtual(portfolio: str) -> str:
    """Chaves de grupo antigas do dashboard (meme_baseline, meme_rule_regime, ...) → um portfólio representativo."""
    m = {"meme_baseline": "meme_BONK_baseline", "meme_relaxed": "meme_BONK_relaxed",
         "meme_rule_regime": "BONK_rule_regime", "meme_rule_donch_regime": "BONK_rule_donch_regime",
         "meme_rule_regime_full": "BONK_rule_regime_full", "meme_rule_donch_regime_full": "BONK_rule_donch_regime_full",
         "hybrid_poorjev_regime": "BONK_hybrid_poorjev_regime"}
    return m.get(portfolio, portfolio)


def default_for(portfolio: str) -> dict:
    """Portões padrão (params.json sem o overlay do dashboard) das chaves editáveis."""
    eff, _prov, _errs, _m = P.explain(_virtual(portfolio), use_overlay=False)
    g = eff.get("gates") or {}
    return {k: g.get(k) for k in EDITABLE}


def effective_for(portfolio: str) -> tuple[dict, dict, list]:
    """(efetivo com overlay, proveniência, erros) — para a vista de detalhe."""
    eff, prov, errs, _m = P.explain(_virtual(portfolio))
    return eff, prov, errs


def validate_patch(field: str, value) -> tuple[bool, str, float|int]:
    """Validação de forma (número, intervalo largo). Os limites de segurança (buy_fraction ≤ 0,5, trades/h ≤ 8 salvo
    `limits`) são verificados depois pelo resolver sobre o portfólio inteiro (P.check_overlay_patch)."""
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
