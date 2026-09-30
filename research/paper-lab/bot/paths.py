"""Resolução única de caminhos do laboratório (paper only).

- `LAB_DIR`: onde está o código (`research/paper-lab/`), derivado deste ficheiro.
- `ROOT`: raiz dos dados/estado do laboratório. Env `PAPER_LAB_ROOT` se definida, senão `LAB_DIR`.
  No host antigo as duas coincidiam (`/home/box/solana-trader/paper`); aponte `PAPER_LAB_ROOT` para uma
  exportação para ler os logs dela sem copiar nada para o repositório.
- `JEV_ALTS_ROOT`: venvs e cache HF dos modelos (von/Laya/poorjev). Env `JEV_ALTS_ROOT`, padrão `/workspace/jev-alts`.
- `STRATEGY_RESEARCH_ROOT`: dados da pesquisa de regras. Env `STRATEGY_RESEARCH_ROOT`, padrão `/workspace/strategy-research`.

O valor é lido na importação; defina as variáveis antes de importar `bot.*`.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parents[1]


def lab_root() -> Path:
    env = os.environ.get("PAPER_LAB_ROOT")
    return Path(env).expanduser().resolve() if env else LAB_DIR


ROOT = lab_root()
CONFIG_PATH = ROOT / "config.json"
JEV_ALTS_ROOT = Path(os.environ.get("JEV_ALTS_ROOT") or "/workspace/jev-alts")
STRATEGY_RESEARCH_ROOT = Path(os.environ.get("STRATEGY_RESEARCH_ROOT") or "/workspace/strategy-research")

# Caminhos relativos a ROOT usados pelos pontos de entrada antigos (bot/main.py, meme_main.py, review.py).
# config.json atual não tem bloco "paths"; estes padrões substituem o que faltar.
DEFAULT_PATHS = {
    "decisions_log": "logs/decisions.jsonl",
    "trades_log": "logs/trades.jsonl",
    "prices_log": "data/prices.jsonl",
    "status": "status.json",
    "portfolio_baseline": "data/portfolio_baseline.json",
    "equity_baseline": "data/equity_baseline.jsonl",
    "criteria_baseline": "criteria_baseline.json",
    "criteria_v2": "criteria_v2.json",
    "review_md": "reviews/night_review_legacy.md",
}


def resolve_root(cfg_root: str | None = None) -> Path:
    """PAPER_LAB_ROOT > paths.root absoluto do config > LAB_DIR. paths.root relativo resolve contra LAB_DIR."""
    if os.environ.get("PAPER_LAB_ROOT"):
        return lab_root()
    if cfg_root:
        p = Path(cfg_root).expanduser()
        return p if p.is_absolute() else (LAB_DIR / p).resolve()
    return LAB_DIR


def load_config(config_path: Path | None = None) -> dict:
    """config.json com `_paths` resolvidos (Path absolutos). Relativos são resolvidos contra a raiz."""
    path = Path(config_path) if config_path else CONFIG_PATH
    cfg = json.loads(path.read_text())
    raw = dict(DEFAULT_PATHS)
    raw.update(cfg.get("paths") or {})
    root = resolve_root(raw.get("root"))
    resolved = {"root": root}
    for k, v in raw.items():
        if k == "root":
            continue
        p = Path(v)
        resolved[k] = p if p.is_absolute() else root / p
    cfg.setdefault("paths", {})["root"] = str(root)
    cfg["_paths"] = resolved
    return cfg


def assert_no_keypair_touch(cfg: dict) -> None:
    cfg["_forbidden_paths"] = set(cfg.get("forbid_keypair_paths", []))
