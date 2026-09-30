"""Critérios do modelo: as frases do artigo por omissão, ou `config/criteria.json` depois de aprovado por uma pessoa."""

from __future__ import annotations

import json
from pathlib import Path

CRITERIA_KEYS = ("buy", "sell", "hold", "skip")
MAX_CRITERION_CHARS = 400

# As frases do artigo. Ficam no ar enquanto não há critério aprovado e válido.
DEFAULT_CRITERIA: dict[str, str] = {
    "buy": "the move is strong and depth is not thin",
    "sell": "the move is fading or fees are climbing",
    "hold": "anything else",
    "skip": "conditions are too hostile to trade at all",
}


class CriteriaError(ValueError):
    pass


def validate_criteria(data: object) -> dict[str, str]:
    """Devolve só as quatro chaves, limpas. Texto vazio, com dígitos ou longo demais → `CriteriaError`.

    O modelo nunca vê números: o estado não tem dígitos e os critérios também não podem ter.
    """
    if not isinstance(data, dict):
        raise CriteriaError("criteria must be a JSON object")
    clean: dict[str, str] = {}
    for key in CRITERIA_KEYS:
        value = data.get(key)
        if not isinstance(value, str):
            raise CriteriaError(f"criteria {key} must be a string")
        text = " ".join(value.split())
        if not text:
            raise CriteriaError(f"criteria {key} is empty")
        if any(character.isdigit() for character in text):
            raise CriteriaError(f"criteria {key} contains a digit")
        if len(text) > MAX_CRITERION_CHARS:
            raise CriteriaError(f"criteria {key} is longer than {MAX_CRITERION_CHARS} characters")
        clean[key] = text
    return clean


def load_criteria(path: Path | None) -> tuple[dict[str, str], str]:
    """(critérios, origem). Qualquer problema com o ficheiro → frases do artigo, origem `default`."""
    if path is None:
        return dict(DEFAULT_CRITERIA), "default"
    try:
        if not path.is_file():
            return dict(DEFAULT_CRITERIA), "default"
        data = json.loads(path.read_text(encoding="utf-8"))
        return validate_criteria(data), "file"
    except Exception:
        return dict(DEFAULT_CRITERIA), "default"


def questions_for(criteria: dict[str, str], instructions: str) -> dict:
    return {
        "action": {
            "type": "choice",
            "instructions": instructions,
            "criteria": {
                "buy": criteria["buy"],
                "sell": criteria["sell"],
                "hold": criteria["hold"],
            },
        },
        "skip_this_cycle": {
            "type": "noul",
            "instructions": criteria["skip"],
        },
    }
