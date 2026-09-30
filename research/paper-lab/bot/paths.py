from __future__ import annotations
import json
from pathlib import Path

ROOT = Path("/home/box/solana-trader/paper")
CONFIG_PATH = ROOT / "config.json"

def load_config() -> dict:
    cfg = json.loads(CONFIG_PATH.read_text())
    root = Path(cfg["paths"]["root"])
    resolved = {}
    for k, v in cfg["paths"].items():
        if k == "root":
            resolved[k] = root
        else:
            p = Path(v)
            resolved[k] = p if p.is_absolute() else root / p
    cfg["_paths"] = resolved
    return cfg

def assert_no_keypair_touch(cfg: dict) -> None:
    cfg["_forbidden_paths"] = set(cfg.get("forbid_keypair_paths", []))
