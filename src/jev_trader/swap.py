"""Jupiter Ultra: /ultra/v1/order + /ultra/v1/execute. Assina só o slot do taker."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from jev_trader.config import SOL_DECIMALS, USDT_DECIMALS, USDT_MINT, WSOL_MINT, Config


class SwapError(Exception):
    pass


def sign_versioned_for_taker(raw: bytes, taker) -> bytes:
    """Assina somente o slot do taker.

    Transação gasless tem dois signatários: o gas payer da Jupiter no slot 0 e o
    taker no seguinte. O slot do payer permanece `Signature.default()` quando ainda
    está vazio, para o `/execute` completar a co-assinatura. Uma assinatura que a
    Jupiter já tenha colocado no slot 0 é preservada. O construtor
    `VersionedTransaction(message, [keypair])` não é usado, porque ele trata o
    taker como primeiro signatário.
    """
    from solders.message import to_bytes_versioned
    from solders.signature import Signature
    from solders.transaction import VersionedTransaction

    transaction = VersionedTransaction.from_bytes(raw)
    message = transaction.message
    required = int(message.header.num_required_signatures)
    keys = list(message.account_keys)
    existing = list(transaction.signatures)
    signatures = [
        existing[index] if index < len(existing) else Signature.default()
        for index in range(required)
    ]
    taker_pubkey = taker.pubkey()
    taker_at = next((index for index in range(required) if keys[index] == taker_pubkey), None)
    if taker_at is None:
        raise SwapError("taker is not a required signer on the Jupiter transaction")
    taker_signature = taker.sign_message(to_bytes_versioned(message))
    if required >= 2 and taker_at != 0:
        if _is_default_signature(signatures[0]):
            signatures[0] = Signature.default()
        signatures[taker_at] = taker_signature
    else:
        signatures[taker_at] = taker_signature
    signed = VersionedTransaction.populate(message, signatures)
    return bytes(signed)


def execute_swap(cfg: Config, *, side: str, confidence: float) -> dict:
    if side not in {"buy", "sell"}:
        raise SwapError("only buy and sell are executable")
    if not cfg.live_trading:
        raise SwapError("live trading is off")
    if not cfg.wallet_matches_experiment:
        raise SwapError("HOT_WALLET_ADDRESS does not match the experiment wallet")
    if not cfg.keypair_path:
        raise SwapError("SOLANA_KEYPAIR_PATH is unset")
    taker = _load_keypair(cfg.keypair_path)
    if str(taker.pubkey()) != cfg.hot_wallet:
        raise SwapError("keypair pubkey does not match the experiment wallet")

    import httpx

    input_mint, output_mint, amount, input_decimals, output_decimals = _order_spec(
        cfg, side=side, confidence=confidence
    )
    headers = {"User-Agent": "jev-solana-trader/0.1", "Accept": "application/json"}
    if cfg.jupiter_api_key:
        headers["x-api-key"] = cfg.jupiter_api_key
    timeout = httpx.Timeout(20.0, connect=5.0)
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        order_response = client.get(
            f"{cfg.jupiter_ultra_base}/ultra/v1/order",
            params={
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "taker": cfg.hot_wallet,
            },
        )
        order_response.raise_for_status()
        order = order_response.json()
        transaction_b64 = order.get("transaction")
        request_id = order.get("requestId")
        if not transaction_b64 or not request_id:
            message = order.get("error") or order.get("errorMessage") or "order response missing transaction"
            raise SwapError(_public_error(str(message), cfg))
        signed = sign_versioned_for_taker(base64.b64decode(transaction_b64), taker)
        execute_response = client.post(
            f"{cfg.jupiter_ultra_base}/ultra/v1/execute",
            json={
                "signedTransaction": base64.b64encode(signed).decode("ascii"),
                "requestId": request_id,
            },
        )
        execute_response.raise_for_status()
        body = execute_response.json()
    status = str(body.get("status") or "")
    signature = body.get("signature")
    if not signature or status.lower() == "failed":
        message = body.get("error") or status or "execute failed"
        raise SwapError(_public_error(str(message), cfg))
    return {
        "ok": True,
        "kind": "ultra",
        "side": side,
        "input_mint": input_mint,
        "output_mint": output_mint,
        "in_amount": str(order.get("inAmount") or amount),
        "out_amount": str(order.get("outAmount") or ""),
        "in_amount_ui": _atoms_to_ui(order.get("inAmount") or amount, input_decimals),
        "out_amount_ui": _atoms_to_ui(order.get("outAmount") or "0", output_decimals),
        "signature": signature,
        "request_id": request_id,
        "status": status or "Success",
        "gasless": bool(order.get("gasless")),
        "signature_fee_payer": order.get("signatureFeePayer"),
        "wallet": cfg.hot_wallet,
    }


def order_size_ui(cfg: Config, *, side: str, confidence: float) -> float:
    """Tamanho nominal da ordem (USDT na compra, SOL na venda). O paper usa a mesma conta."""
    if side == "buy":
        return min(cfg.buy_usdt, cfg.max_buy_usdt) * confidence
    return min(cfg.sell_sol, cfg.max_sell_sol) * confidence


def _order_spec(cfg: Config, *, side: str, confidence: float) -> tuple[str, str, str, int, int]:
    ui = order_size_ui(cfg, side=side, confidence=confidence)
    if side == "buy":
        return USDT_MINT, WSOL_MINT, str(_ui_to_atoms(ui, USDT_DECIMALS)), USDT_DECIMALS, SOL_DECIMALS
    return WSOL_MINT, USDT_MINT, str(_ui_to_atoms(ui, SOL_DECIMALS)), SOL_DECIMALS, USDT_DECIMALS


def _load_keypair(path: str):
    from solders.keypair import Keypair

    file_path = Path(path)
    if not file_path.is_file():
        raise SwapError("keypair file not found")
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise SwapError("keypair file is not valid JSON") from None
    if not isinstance(data, list) or not all(isinstance(item, int) and 0 <= item <= 255 for item in data):
        raise SwapError("keypair file must be a JSON byte array")
    blob = bytes(data)
    if len(blob) == 64:
        return Keypair.from_bytes(blob)
    if len(blob) == 32:
        return Keypair.from_seed(blob)
    raise SwapError("keypair file must contain 32 or 64 bytes")


def _ui_to_atoms(amount_ui: float, decimals: int) -> int:
    atoms = int(round(amount_ui * (10**decimals)))
    return max(atoms, 1)


def _atoms_to_ui(amount: str, decimals: int) -> float:
    try:
        return int(amount) / (10**decimals)
    except (TypeError, ValueError):
        return 0.0


def _is_default_signature(signature) -> bool:
    from solders.signature import Signature

    return bytes(signature) == bytes(Signature.default())


def _public_error(text: str, cfg: Config) -> str:
    cleaned = " ".join(text.split())
    secret = cfg.jupiter_api_key
    if secret:
        cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned[:180]
