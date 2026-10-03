"""Critérios de texto próprios de um fork do lab (paper only): validação, armazenamento, hash e resumo.

Um *fork de critérios* difere do pai só no texto das perguntas enviadas ao modelo (instruções da ação, critérios
buy/sell/hold e instruções do skip), no esquema de `criteria_*.json`:

    {"action": {"instructions": "...", "criteria": {"buy": "...", "sell": "...", "hold": "..."}},
     "skip_this_cycle": {"instructions": "..."}}

Regras (o modelo nunca vê números, como o estado de adjetivos): nenhum dígito, textos não vazios, limites de tamanho,
nenhuma chave extra nas partes enviadas ao modelo. O ficheiro fica em `data/lab/criteria/<fork>.json` (nunca é
sobrescrito) e o registry referencia-o no diff do fork: `params_diff.criteria = {"file": ..., "sha256": ...}` (grupo
`criteria` de bot/params.py). O lab_bot verifica o sha256 a cada carga; ficheiro em falta, inválido ou alterado →
hold (fail-closed).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bot.paths import ROOT

MAX_INSTRUCTIONS = 300
MAX_CRITERION = 400
MAX_TOTAL = 1600
CRIT_KEYS = ("buy", "sell", "hold")
REL_DIR = "data/lab/criteria/"


class CriteriaTextError(ValueError):
    pass


def crit_dir() -> Path:
    return ROOT / "data" / "lab" / "criteria"


def _text(v, where: str, cap: int) -> str:
    if not isinstance(v, str):
        raise CriteriaTextError(f"{where}: tem de ser texto")
    t = " ".join(v.split())
    if not t:
        raise CriteriaTextError(f"{where}: vazio")
    if any(c.isdigit() for c in t):
        raise CriteriaTextError(f"{where}: contém dígitos (o modelo nunca vê números)")
    if len(t) > cap:
        raise CriteriaTextError(f"{where}: {len(t)} caracteres (máximo {cap})")
    return t


def validate(doc) -> dict:
    """Documento limpo só com as partes enviadas ao modelo. Levanta CriteriaTextError."""
    if not isinstance(doc, dict):
        raise CriteriaTextError("critérios: tem de ser um objeto JSON")
    act = doc.get("action")
    if not isinstance(act, dict):
        raise CriteriaTextError("action: obrigatório (objeto com instructions e criteria)")
    extra = set(act) - {"instructions", "criteria"}
    if extra:
        raise CriteriaTextError(f"action: chaves desconhecidas {sorted(extra)}")
    crit = act.get("criteria")
    if not isinstance(crit, dict):
        raise CriteriaTextError("action.criteria: obrigatório (buy, sell, hold)")
    extra = set(crit) - set(CRIT_KEYS)
    if extra:
        raise CriteriaTextError(f"action.criteria: chaves desconhecidas {sorted(extra)}")
    skip = doc.get("skip_this_cycle")
    if not isinstance(skip, dict):
        raise CriteriaTextError("skip_this_cycle: obrigatório (objeto com instructions)")
    extra = set(skip) - {"instructions"}
    if extra:
        raise CriteriaTextError(f"skip_this_cycle: chaves desconhecidas {sorted(extra)}")
    clean = {
        "action": {"instructions": _text(act.get("instructions"), "action.instructions", MAX_INSTRUCTIONS),
                   "criteria": {k: _text(crit.get(k), f"action.criteria.{k}", MAX_CRITERION) for k in CRIT_KEYS}},
        "skip_this_cycle": {"instructions": _text(skip.get("instructions"), "skip_this_cycle.instructions", MAX_CRITERION)},
    }
    total = len(clean["action"]["instructions"]) + sum(len(v) for v in clean["action"]["criteria"].values()) + \
        len(clean["skip_this_cycle"]["instructions"])
    if total > MAX_TOTAL:
        raise CriteriaTextError(f"critérios: {total} caracteres no total (máximo {MAX_TOTAL})")
    return clean


def model_part(doc: dict) -> dict:
    """Só as partes enviadas ao modelo (sem validar)."""
    a = doc.get("action") or {}
    return {"action": {"instructions": a.get("instructions"), "criteria": dict(a.get("criteria") or {})},
            "skip_this_cycle": {"instructions": (doc.get("skip_this_cycle") or {}).get("instructions")}}


def digest(clean: dict) -> str:
    return hashlib.sha256(json.dumps(model_part(clean), sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def rel_path(name: str) -> str:
    if not name or any(c in name for c in "/\\") or ".." in name:
        raise CriteriaTextError(f"nome inválido: {name!r}")
    return f"{REL_DIR}{name}.json"


def abs_path(rel: str) -> Path:
    if not (isinstance(rel, str) and rel.startswith(REL_DIR) and rel.endswith(".json") and ".." not in rel
            and "/" not in rel[len(REL_DIR):]):
        raise CriteriaTextError(f"caminho de critérios inválido: {rel!r}")
    return crit_dir() / rel[len(REL_DIR):]


def store(name: str, clean: dict, meta: dict | None = None) -> dict:
    """Grava data/lab/criteria/<name>.json (nunca sobrescreve). Devolve a referência {"file", "sha256"}."""
    rel = rel_path(name)
    p = abs_path(rel)
    if p.exists():
        raise CriteriaTextError(f"{rel} já existe (critérios nunca são sobrescritos)")
    p.parent.mkdir(parents=True, exist_ok=True)
    sha = digest(clean)
    doc = dict(meta or {}, version=name, sha256=sha, **model_part(clean))
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(p)
    return {"file": rel, "sha256": sha}


def load_ref(ref: dict) -> tuple[dict, str]:
    """(critérios limpos, sha256) a partir da referência do registry. Verifica o hash. Levanta CriteriaTextError."""
    if not isinstance(ref, dict) or not ref.get("file"):
        raise CriteriaTextError("referência de critérios sem 'file'")
    p = abs_path(ref["file"])
    try:
        doc = json.loads(p.read_text())
    except FileNotFoundError:
        raise CriteriaTextError(f"{ref['file']} não existe") from None
    except Exception as e:
        raise CriteriaTextError(f"{ref['file']} ilegível: {type(e).__name__}") from None
    clean = validate(model_part(doc))
    sha = digest(clean)
    if ref.get("sha256") and ref["sha256"] != sha:
        raise CriteriaTextError(f"{ref['file']}: sha256 diferente do registry (ficheiro alterado)")
    return clean, sha


def load_file(path: Path) -> dict:
    """Critérios de um ficheiro no esquema criteria_*.json (aceita chaves extra no topo, ex.: version/note)."""
    try:
        doc = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise CriteriaTextError(f"{path} não existe") from None
    except Exception as e:
        raise CriteriaTextError(f"{path} ilegível: {type(e).__name__}: {e}") from None
    if not isinstance(doc, dict):
        raise CriteriaTextError("critérios: tem de ser um objeto JSON")
    return validate(model_part(doc) if "action" in doc else doc)


def base_criteria(source: str | None, eff: dict | None = None) -> tuple[dict, str]:
    """Critérios que um portfólio usa hoje: os próprios (eff.criteria), senão os do bot da fonte
    (`v2` → criteria_v2.json; os restantes von/laya/poorjev SOL e memes → criteria_baseline.json)."""
    ref = (eff or {}).get("criteria")
    if ref and ref.get("file"):
        clean, _sha = load_ref(ref)
        return clean, ref["file"]
    name = "criteria_v2.json" if source == "v2" else "criteria_baseline.json"
    return validate(model_part(json.loads((ROOT / name).read_text()))), name


def summary(clean: dict, width: int = 70) -> str:
    def cut(t):
        return t if len(t) <= width else t[: width - 1] + "…"
    c = clean["action"]["criteria"]
    return f"compra: {cut(c['buy'])} | venda: {cut(c['sell'])} | skip: {cut(clean['skip_this_cycle']['instructions'])}"
