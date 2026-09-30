"""Configuração lida do ambiente. Nenhum segredo tem valor padrão."""

from __future__ import annotations

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
    return Config(
        hot_wallet=EXPERIMENT_WALLET,
        wallet_matches_experiment=configured_wallet == EXPERIMENT_WALLET,
        keypair_path=_path_or_none("SOLANA_KEYPAIR_PATH"),
        live_trading=os.environ.get("LIVE_TRADING", "").strip() == "1",
        von_base_url=os.environ.get("VON_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/"),
        von_model=os.environ.get("VON_MODEL", "von-latest").strip() or "von-latest",
        von_timeout_s=_float("VON_TIMEOUT_S", 8.0),
        confidence_min=_float("CONFIDENCE_THRESHOLD", 0.55),
        skip_min=_float("SKIP_THRESHOLD", 0.55),
        loop_seconds=_float("LOOP_SECONDS", 15.0),
        buy_usdt=_float("BUY_USDT", 1.0),
        sell_sol=_float("SELL_SOL", 0.005),
        max_buy_usdt=_float("MAX_BUY_USDT", 5.0),
        max_sell_sol=_float("MAX_SELL_SOL", 0.01),
        jupiter_ultra_base=os.environ.get("JUPITER_ULTRA_BASE", "https://lite-api.jup.ag").strip().rstrip("/"),
        jupiter_quote_base=os.environ.get("JUPITER_QUOTE_BASE", "https://lite-api.jup.ag").strip().rstrip("/"),
        jupiter_api_key=_path_or_none("JUPITER_API_KEY"),
        rpc_url=os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com").strip(),
        log_dir=Path(os.environ.get("LOG_DIR", "logs").strip() or "logs"),
        paper_cost_bps=_float("PAPER_COST_BPS", 10.0),
        experiment_path=Path(os.environ.get("EXPERIMENT_PATH", "").strip() or "config/experiment.json"),
        criteria_path=Path(os.environ.get("CRITERIA_PATH", "").strip() or "config/criteria.json"),
    )
