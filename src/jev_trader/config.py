"""Configuração lida do ambiente e de `config/params.json`. Nenhum segredo tem valor padrão.

Portões e tamanhos: `defaults` → `profiles.<PARAMS_PROFILE>` (padrão `relaxed_paper`) de `config/params.json`
(env `PARAMS_PATH`), e por cima as variáveis de ambiente antigas (`CONFIDENCE_THRESHOLD`, `SKIP_THRESHOLD`, ...),
por compatibilidade. Ficheiro inválido ou perfil desconhecido → valores do artigo (fail-safe). Um perfil
`paper_only` nunca vale com `LIVE_TRADING=1`: cai no `article`.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

EXPERIMENT_WALLET = "GNJv4FcMb4j1A6NFiVaaHkGVTZ5p5A7ea9GsFgccS75r"
WSOL_MINT = "So11111111111111111111111111111111111111112"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
USDT_DECIMALS = 6
SOL_DECIMALS = 9


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# Valores do artigo (e os antigos padrões do ambiente): base e fail-safe dos perfis.
ARTICLE_PARAMS = {
    "confidence_min": 0.55,
    "skip_min": 0.55,
    "prob_margin_min": 0.0,
    "buy_usdt": 1.0,
    "sell_sol": 0.005,
    "max_buy_usdt": 5.0,
    "max_sell_sol": 0.01,
    "loop_seconds": 15.0,
    "paper_cost_bps": 10.0,
}
PARAM_GROUPS = {
    "gates": ("confidence_min", "skip_min", "prob_margin_min"),
    "sizing": ("buy_usdt", "sell_sol", "max_buy_usdt", "max_sell_sol"),
    "cycle": ("loop_seconds",),
    "paper": ("paper_cost_bps",),
}
PARAM_ENV = {
    "confidence_min": "CONFIDENCE_THRESHOLD",
    "skip_min": "SKIP_THRESHOLD",
    "prob_margin_min": "PROB_MARGIN_MIN",
    "buy_usdt": "BUY_USDT",
    "sell_sol": "SELL_SOL",
    "max_buy_usdt": "MAX_BUY_USDT",
    "max_sell_sol": "MAX_SELL_SOL",
    "loop_seconds": "LOOP_SECONDS",
    "paper_cost_bps": "PAPER_COST_BPS",
}
DEFAULT_PROFILE = "relaxed_paper"
_RANGES = {
    "confidence_min": (0.0, 1.0),
    "skip_min": (0.0, 1.0),
    "prob_margin_min": (0.0, 1.0),
    "buy_usdt": (0.0, 1e6),
    "sell_sol": (0.0, 1e6),
    "max_buy_usdt": (0.0, 1e6),
    "max_sell_sol": (0.0, 1e6),
    "loop_seconds": (1.0, 86400.0),
    "paper_cost_bps": (0.0, 1000.0),
}


def _flatten(layer: object, where: str, errors: list[str]) -> dict:
    out: dict = {}
    if not isinstance(layer, dict):
        errors.append(f"{where}: tem de ser um objeto")
        return out
    for group, values in layer.items():
        if group in ("note", "paper_only", "description") or group.startswith("_"):
            continue
        keys = PARAM_GROUPS.get(group)
        if keys is None or not isinstance(values, dict):
            errors.append(f"{where}: grupo desconhecido '{group}'")
            continue
        for key, value in values.items():
            if key == "note" or key.startswith("_"):
                continue
            if key not in keys:
                errors.append(f"{where}.{group}: chave desconhecida '{key}'")
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                errors.append(f"{where}.{group}.{key}: tem de ser número")
                continue
            lo, hi = _RANGES[key]
            if not lo <= float(value) <= hi:
                errors.append(f"{where}.{group}.{key}: {value} fora de [{lo}, {hi}]")
                continue
            out[key] = float(value)
    return out


def load_params(path: Path, profile: str, *, live: bool = False) -> tuple[dict, str, list[str]]:
    """(valores, perfil usado, erros) de `config/params.json`. Nunca levanta: erro → valores do artigo."""
    errors: list[str] = []
    values = dict(ARTICLE_PARAMS)
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return values, "article", [f"{path} em falta: valores do artigo"]
    except Exception as exc:
        return values, "article", [f"{path} ilegível ({type(exc).__name__}): valores do artigo"]
    if not isinstance(doc, dict):
        return values, "article", [f"{path}: raiz tem de ser um objeto"]
    profiles = doc.get("profiles") or {}
    used = profile
    if used not in profiles:
        errors.append(f"perfil desconhecido '{profile}': uso 'article'")
        used = "article"
    if live and isinstance(profiles.get(used), dict) and profiles[used].get("paper_only"):
        errors.append(f"perfil '{used}' é só paper e LIVE_TRADING=1: uso 'article'")
        used = "article"
    layer_errors: list[str] = []
    merged = _flatten(doc.get("defaults") or {}, "defaults", layer_errors)
    if used in profiles:
        merged.update(_flatten(profiles[used], f"profiles.{used}", layer_errors))
    if layer_errors:
        return values, "article", errors + layer_errors + ["params inválidos: valores do artigo"]
    values.update(merged)
    return values, used, errors


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return float(raw)


def _path_or_none(name: str) -> str | None:
    raw = os.environ.get(name, "").strip()
    return raw or None


@dataclass(frozen=True)
class Config:
    hot_wallet: str
    wallet_matches_experiment: bool
    keypair_path: str | None
    live_trading: bool
    von_base_url: str
    von_model: str
    von_timeout_s: float
    confidence_min: float
    skip_min: float
    loop_seconds: float
    buy_usdt: float
    sell_sol: float
    max_buy_usdt: float
    max_sell_sol: float
    jupiter_ultra_base: str
    jupiter_quote_base: str
    jupiter_api_key: str | None
    rpc_url: str
    log_dir: Path
    # Paper trading: custo (slippage + fee) contra o trader, em pontos-base sobre o `px_in`.
    paper_cost_bps: float = 10.0
    experiment_path: Path = Path("config/experiment.json")
    criteria_path: Path = Path("config/criteria.json")
    # Portão de margem de probabilidade (escolhida − segunda); 0 = desligado (artigo).
    prob_margin_min: float = 0.0
    params_profile: str = "article"
    params_errors: tuple[str, ...] = ()

    @property
    def decisions_path(self) -> Path:
        return self.log_dir / "decisions.jsonl"

    @property
    def trades_path(self) -> Path:
        return self.log_dir / "trades.jsonl"

    @property
    def paper_book_path(self) -> Path:
        return self.log_dir / "paper_book.json"

    @property
    def paper_trades_path(self) -> Path:
        return self.log_dir / "paper_trades.jsonl"

    @property
    def proposals_dir(self) -> Path:
        return self.log_dir / "rewrite_proposals"

    @property
    def approvals_path(self) -> Path:
        return self.log_dir / "rewrite_approvals.jsonl"


def load_config(dotenv: Path | None = None) -> Config:
    _load_dotenv(dotenv if dotenv is not None else Path(".env"))
    configured_wallet = os.environ.get("HOT_WALLET_ADDRESS", EXPERIMENT_WALLET).strip()
    if not configured_wallet:
        configured_wallet = EXPERIMENT_WALLET
    live = os.environ.get("LIVE_TRADING", "").strip() == "1"
    params, profile, params_errors = load_params(
        Path(os.environ.get("PARAMS_PATH", "").strip() or "config/params.json"),
        os.environ.get("PARAMS_PROFILE", "").strip() or DEFAULT_PROFILE,
        live=live,
    )
    p = {key: _float(env, params[key]) for key, env in PARAM_ENV.items()}
    return Config(
        hot_wallet=EXPERIMENT_WALLET,
        wallet_matches_experiment=configured_wallet == EXPERIMENT_WALLET,
        keypair_path=_path_or_none("SOLANA_KEYPAIR_PATH"),
        live_trading=live,
        von_base_url=os.environ.get("VON_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/"),
        von_model=os.environ.get("VON_MODEL", "von-latest").strip() or "von-latest",
        von_timeout_s=_float("VON_TIMEOUT_S", 8.0),
        confidence_min=p["confidence_min"],
        skip_min=p["skip_min"],
        loop_seconds=p["loop_seconds"],
        buy_usdt=p["buy_usdt"],
        sell_sol=p["sell_sol"],
        max_buy_usdt=p["max_buy_usdt"],
        max_sell_sol=p["max_sell_sol"],
        jupiter_ultra_base=os.environ.get("JUPITER_ULTRA_BASE", "https://lite-api.jup.ag").strip().rstrip("/"),
        jupiter_quote_base=os.environ.get("JUPITER_QUOTE_BASE", "https://lite-api.jup.ag").strip().rstrip("/"),
        jupiter_api_key=_path_or_none("JUPITER_API_KEY"),
        rpc_url=os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com").strip(),
        log_dir=Path(os.environ.get("LOG_DIR", "logs").strip() or "logs"),
        paper_cost_bps=p["paper_cost_bps"],
        experiment_path=Path(os.environ.get("EXPERIMENT_PATH", "").strip() or "config/experiment.json"),
        criteria_path=Path(os.environ.get("CRITERIA_PATH", "").strip() or "config/criteria.json"),
        prob_margin_min=p["prob_margin_min"],
        params_profile=profile,
        params_errors=tuple(params_errors),
    )
