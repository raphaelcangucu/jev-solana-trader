"""Reescrita noturna com corte de confiança por percentil e portão humano.

`propose`: relê as decisões, separa as confiantes que erraram a 15 min e escreve uma proposta
`pending`. `approve`/`reject`: uma pessoa decide; só a aprovação escreve `config/criteria.json`.

Caminho autónomo (decisão do utilizador, 2026-10-03, SÓ em paper): `build_autonomous_proposal` usa a mesma auditoria
por percentil mas com o texto escrito pela revisão noturna do Claude, e `approve(..., autonomous=True)` aprova sem
pessoa apenas se `paper_guard` não encontrar nenhum motivo de recusa (LIVE_TRADING=1 no ambiente ou no `.env`,
`config/experiment.json` sem `"mode": "paper"`, perfil de parâmetros ativo sem `paper_only`). O caminho humano
(`rewrite --approve`) não muda.

Percentil: método nearest-rank. Com as n confianças ordenadas, o corte do percentil P é o valor
na posição ceil(P/100 × n) (base 1). O corte é sempre uma confiança observada.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from collections.abc import Mapping
from datetime import date as Date
from datetime import datetime
from pathlib import Path

from jev_trader.criteria import (
    CRITERIA_KEYS,
    MAX_CRITERION_CHARS,
    CriteriaError,
    load_criteria,
    validate_criteria,
)
from jev_trader.config import DEFAULT_PROFILE, load_params
from jev_trader.experiment import Experiment
from jev_trader.records import append_jsonl, brt_clock, parse_t, write_json_atomic
from jev_trader.score import Timeline, build_timeline, forward_return, select_run

DEFAULT_PERCENTILE = 90.0
DEFAULT_FIXED_BAR = 0.8
DEFAULT_BAND = 0.001
FAIL_CLOSED_SOURCE = "fail-closed"

# Regras determinísticas: palavra de estado frequente nos erros → frase acrescentada a um critério.
# Cada regra: (lado do erro, palavras-gatilho, critério alvo, frase).
RULES: tuple[tuple[str, frozenset[str], str, str], ...] = (
    ("buy", frozenset({"thin"}), "buy", "only when depth is deep not thin"),
    ("buy", frozenset({"wide"}), "buy", "only when the spread is tight"),
    ("buy", frozenset({"bot_war", "harsh"}), "buy", "only when fees are quiet"),
    ("buy", frozenset({"bot_war", "harsh"}), "skip", "when fees turn into a bot war"),
    ("buy", frozenset({"violent", "loud"}), "buy", "only when the tape is calm"),
    ("buy", frozenset({"violent", "loud"}), "hold", "when the tape is violent or loud"),
    ("buy", frozenset({"late"}), "buy", "not late in the range"),
    ("buy", frozenset({"fading", "dumping", "red"}), "buy", "never into a fading or red tape"),
    ("buy", frozenset({"gray"}), "buy", "not when the tape is flat and gray"),
    ("sell", frozenset({"pumping", "green"}), "sell", "not while the move is pumping green"),
    ("sell", frozenset({"early"}), "sell", "not early in the range"),
    ("sell", frozenset({"thin"}), "sell", "only when depth is deep not thin"),
    ("sell", frozenset({"wide"}), "sell", "only when the spread is tight"),
    ("sell", frozenset({"bot_war", "harsh"}), "sell", "not on fees alone"),
    ("sell", frozenset({"violent", "loud"}), "sell", "only when the tape is calm"),
    ("sell", frozenset({"violent", "loud"}), "hold", "when the tape is violent or loud"),
    ("sell", frozenset({"gray"}), "sell", "not when the tape is flat and gray"),
)
FALLBACK_PHRASE = "only when the move and the book agree"


class RewriteError(ValueError):
    pass


def percentile_cutoff(values: list[float], percentile: float) -> float | None:
    """Nearest-rank. Lista vazia → None."""
    if not values:
        return None
    if not 0 < percentile <= 100:
        raise RewriteError("percentile must be in (0, 100]")
    ordered = sorted(values)
    rank = max(math.ceil(percentile / 100 * len(ordered)), 1)
    return ordered[rank - 1]


def model_answered(decisions: list[dict]) -> list[dict]:
    """Decisões em que o von respondeu: fonte diferente de fail-closed e `model_action` presente."""
    kept = []
    for row in decisions:
        if row.get("source") == FAIL_CLOSED_SOURCE or row.get("model_action") is None:
            continue
        if _conf(row) is None:
            continue
        kept.append(row)
    return kept


def audit(
    answered: list[dict],
    timeline: Timeline,
    *,
    cutoff: float | None,
    band: float,
) -> dict:
    """Confiantes = conf >= corte e ação final buy/sell (passaram os portões). Erro fora da banda a 15 min."""
    confident = []
    blocked_above = 0
    if cutoff is not None:
        for row in answered:
            conf = _conf(row)
            if conf is None or conf < cutoff:
                continue
            if row.get("action") in {"buy", "sell"}:
                confident.append(row)
            elif row.get("model_action") in {"buy", "sell"}:
                blocked_above += 1
    resolved = unresolved = 0
    mistakes: list[dict] = []
    for row in confident:
        moment = parse_t(row.get("t"))
        price = _positive(row.get("px_in"))
        if moment is None or price is None:
            unresolved += 1
            continue
        ret, later, later_t = forward_return(timeline, moment, price)
        if ret is None:
            unresolved += 1
            continue
        resolved += 1
        side = row["action"]
        wrong = ret < -band if side == "buy" else ret > band
        if wrong:
            mistakes.append(
                {
                    "t": row.get("t"),
                    "action": side,
                    "conf": _conf(row),
                    "state": row.get("state"),
                    "px_in": price,
                    "px_later": later,
                    "t_later": later_t,
                    "ret": round(ret, 8),
                }
            )
    words: Counter = Counter()
    for mistake in mistakes:
        words.update(set(str(mistake.get("state") or "").split()))
    return {
        "cutoff": cutoff,
        "n_answered": len(answered),
        "n_confident": len(confident),
        "n_model_directional_above_cutoff_blocked": blocked_above,
        "n_resolved": resolved,
        "n_unresolved": unresolved,
        "n_mistakes": len(mistakes),
        "mistakes": mistakes,
        "word_counts": dict(sorted(words.items(), key=lambda item: (-item[1], item[0]))),
    }


def propose_criteria(current: dict[str, str], mistakes: list[dict]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Acrescenta frases conforme as palavras que aparecem em pelo menos metade dos erros de cada lado.

    Sem erros → critérios iguais aos atuais. Frase já presente ou que passaria do limite não entra.
    """
    proposed = dict(current)
    additions: dict[str, list[str]] = {key: [] for key in CRITERIA_KEYS}
    for side in ("buy", "sell"):
        side_mistakes = [m for m in mistakes if m.get("action") == side]
        if not side_mistakes:
            continue
        counts: Counter = Counter()
        for mistake in side_mistakes:
            counts.update(set(str(mistake.get("state") or "").split()))
        frequent = {word for word, count in counts.items() if count * 2 >= len(side_mistakes)}
        fired = False
        for rule_side, triggers, target, phrase in RULES:
            if rule_side != side or not (triggers & frequent):
                continue
            fired = True
            _append(proposed, additions, target, phrase)
        if not fired:
            _append(proposed, additions, side, FALLBACK_PHRASE)
    return proposed, {key: value for key, value in additions.items() if value}


def build_proposal(
    decisions: list[dict],
    experiment: Experiment,
    current: dict[str, str],
    current_source: str,
    *,
    review_date: Date | None,
    today: Date,
    percentile: float = DEFAULT_PERCENTILE,
    fixed_bar: float = DEFAULT_FIXED_BAR,
    band: float = DEFAULT_BAND,
    now_t: str,
) -> dict:
    """Proposta completa. O texto sai da auditoria por percentil; a barra fixa fica só para comparação."""
    run = select_run(decisions, experiment)
    timeline = build_timeline(run)
    if review_date is None:
        window = run
    else:
        window = [row for row in run if _brt_date(row.get("t")) == review_date]
    answered = model_answered(window)
    confidences = [c for c in (_conf(row) for row in answered) if c is not None]
    cut = percentile_cutoff(confidences, percentile)
    by_percentile = audit(answered, timeline, cutoff=cut, band=band)
    by_fixed = audit(answered, timeline, cutoff=fixed_bar, band=band)
    proposed, additions = propose_criteria(current, by_percentile["mistakes"])
    label = (review_date or today).isoformat()
    return {
        "date": label,
        "title": f"Reescrita noturna — {label}",
        "run_id": experiment.run_id,
        "generated_t": now_t,
        "window": {
            "review_date": review_date.isoformat() if review_date else None,
            "from": window[0].get("t") if window else None,
            "to": window[-1].get("t") if window else None,
            "n_decisions": len(window),
        },
        "status": "pending",
        "changed": proposed != current,
        "current_source": current_source,
        "current_criteria": current,
        "proposed_criteria": proposed,
        "additions": additions,
        "audit": {
            "driver": "percentile",
            "band": band,
            "horizon_min": 15,
            "tolerance_min": 5,
            "percentile": {"method": "nearest-rank", "percentile": percentile, **by_percentile},
            "fixed": {"method": "fixed", "bar": fixed_bar, **by_fixed},
        },
    }


def write_proposal(directory: Path, proposal: dict, *, filename: str | None = None) -> Path:
    """`AAAA-MM-DD.json` (ou `filename`). Uma proposta já aprovada ou rejeitada não é sobrescrita."""
    path = directory / (filename or f"{proposal['date']}.json")
    if path.is_file():
        try:
            status = json.loads(path.read_text(encoding="utf-8")).get("status")
        except (OSError, json.JSONDecodeError, AttributeError):
            status = None
        if status != "pending":
            raise RewriteError(f"{path} already exists with status {status}; not overwriting")
    write_json_atomic(path, proposal)
    return path


def read_pending(path: Path) -> dict:
    try:
        proposal = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RewriteError(f"proposal unreadable: {exc}") from None
    if not isinstance(proposal, dict):
        raise RewriteError("proposal must be a JSON object")
    if proposal.get("status") != "pending":
        raise RewriteError(f"proposal status is {proposal.get('status')!r}, not 'pending'")
    return proposal


def approve(
    path: Path,
    *,
    criteria_path: Path,
    approvals_path: Path,
    approver: str,
    now_t: str,
    autonomous: bool = False,
    guard_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict:
    """Valida, escreve `config/criteria.json` de forma atómica, marca a proposta e anexa o registo.

    Proposta feita sobre critérios que já não são os do ar (outra aprovação entretanto) é recusada.
    `autonomous=True` (aprovação sem pessoa): exige `guard_root` (raiz do bot real) e recusa, antes de escrever
    qualquer coisa, se `paper_guard` devolver algum motivo.
    """
    if autonomous:
        if guard_root is None:
            raise RewriteError("autonomous approval needs guard_root")
        refused = paper_guard(Path(guard_root), env)
        if refused:
            raise RewriteError("autonomous approval refused: " + "; ".join(refused))
    proposal = read_pending(path)
    try:
        criteria = validate_criteria(proposal.get("proposed_criteria"))
    except CriteriaError as exc:
        raise RewriteError(f"proposed criteria invalid: {exc}") from None
    live, _source = load_criteria(criteria_path)
    if proposal.get("current_criteria") != live:
        raise RewriteError("proposal was built on criteria that are no longer live; propose again")
    write_json_atomic(
        criteria_path,
        {**criteria, "approved_t": now_t, "proposal": str(path), "run_id": proposal.get("run_id")},
    )
    digest = hashlib.sha256(criteria_path.read_bytes()).hexdigest()
    marks = {"status": "approved", "approved_t": now_t, "approved_by": approver, "criteria_sha256": digest}
    if autonomous:
        marks["autonomous"] = True
    write_json_atomic(path, {**proposal, **marks})
    record = {
        "t": now_t,
        "decision": "approved",
        "proposal": str(path),
        "criteria_path": str(criteria_path),
        "criteria_sha256": digest,
        "approver": approver,
    }
    if autonomous:
        record["autonomous"] = True
        record["reason"] = proposal.get("reason")
    append_jsonl(approvals_path, record)
    return record


# ------------------------------------------------------------------ caminho autónomo (só paper)

GUARD_ENV_KEYS = ("LIVE_TRADING", "PARAMS_PROFILE", "PARAMS_PATH", "EXPERIMENT_PATH")


def _dotenv_keys(path: Path, keys: tuple[str, ...]) -> dict[str, str]:
    """Só as chaves pedidas de um `.env` (nunca devolve nem imprime as outras)."""
    out: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for raw in lines:
        line = raw.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in keys:
            out[key] = value.strip().strip('"').strip("'")
    return out


def _under(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else root / p


def paper_guard(root: Path, env: Mapping[str, str] | None = None) -> list[str]:
    """Motivos para RECUSAR uma aprovação autónoma (lista vazia = bot real em paper). Fail-closed: qualquer leitura
    impossível conta como motivo. Vê o ambiente do processo e só as chaves LIVE_TRADING/PARAMS_*/EXPERIMENT_PATH
    do `.env` da raiz do bot real."""
    env = os.environ if env is None else env
    dot = _dotenv_keys(root / ".env", GUARD_ENV_KEYS)
    reasons: list[str] = []
    if str(env.get("LIVE_TRADING", "")).strip() == "1":
        reasons.append("LIVE_TRADING=1 no ambiente")
    if dot.get("LIVE_TRADING", "").strip() == "1":
        reasons.append("LIVE_TRADING=1 no .env do bot real")
    exp_path = _under(root, env.get("EXPERIMENT_PATH") or dot.get("EXPERIMENT_PATH") or "config/experiment.json")
    try:
        mode = json.loads(exp_path.read_text(encoding="utf-8")).get("mode")
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        mode = None
        reasons.append(f"experiment.json ilegível ou em falta ({type(exc).__name__})")
    else:
        if mode != "paper":
            reasons.append(f"experiment.json mode={mode!r} (tem de ser 'paper')")
    params_path = _under(root, env.get("PARAMS_PATH") or dot.get("PARAMS_PATH") or "config/params.json")
    profile = env.get("PARAMS_PROFILE") or dot.get("PARAMS_PROFILE") or DEFAULT_PROFILE
    _values, used, errors = load_params(params_path, profile, live=False)
    try:
        doc = json.loads(params_path.read_text(encoding="utf-8"))
        paper_only = bool(((doc.get("profiles") or {}).get(used) or {}).get("paper_only"))
    except (OSError, json.JSONDecodeError, AttributeError):
        paper_only = False
    if used != profile:
        reasons.append(f"perfil de parâmetros '{profile}' não resolve (usado '{used}'): {'; '.join(errors)[:200]}")
    if not paper_only:
        reasons.append(f"perfil de parâmetros ativo '{used}' não é paper_only")
    return reasons


def build_autonomous_proposal(
    decisions: list[dict],
    experiment: Experiment,
    current: dict[str, str],
    current_source: str,
    proposed: dict,
    *,
    author: str,
    reason: str,
    review_date: Date | None,
    today: Date,
    now_t: str,
    percentile: float = DEFAULT_PERCENTILE,
    fixed_bar: float = DEFAULT_FIXED_BAR,
    band: float = DEFAULT_BAND,
) -> dict:
    """Proposta com a mesma auditoria por percentil de `build_proposal`, mas com o texto `proposed` escrito pela
    revisão autónoma (validado: quatro chaves, sem dígitos, ≤ 400 caracteres). Sem mudança → RewriteError."""
    try:
        criteria = validate_criteria(proposed)
    except CriteriaError as exc:
        raise RewriteError(f"proposed criteria invalid: {exc}") from None
    if criteria == current:
        raise RewriteError("proposed criteria are identical to the live criteria")
    proposal = build_proposal(
        decisions, experiment, current, current_source, review_date=review_date, today=today,
        percentile=percentile, fixed_bar=fixed_bar, band=band, now_t=now_t,
    )
    proposal.update(
        {
            "title": f"Reescrita autónoma ({author}) — {proposal['date']}",
            "author": author,
            "reason": reason,
            "proposed_criteria": criteria,
            "deterministic_proposal": proposal["proposed_criteria"],
            "additions": {},
            "changed": True,
        }
    )
    return proposal


def reject(path: Path, *, approvals_path: Path, approver: str, now_t: str) -> dict:
    proposal = read_pending(path)
    write_json_atomic(path, {**proposal, "status": "rejected", "rejected_t": now_t, "rejected_by": approver})
    record = {
        "t": now_t,
        "decision": "rejected",
        "proposal": str(path),
        "criteria_path": None,
        "criteria_sha256": None,
        "approver": approver,
    }
    append_jsonl(approvals_path, record)
    return record


def today_brt() -> Date:
    return datetime.now(brt_clock()).date()


def _append(proposed: dict[str, str], additions: dict[str, list[str]], target: str, phrase: str) -> None:
    text = proposed[target]
    if phrase in text:
        return
    candidate = f"{text}; {phrase}"
    if len(candidate) > MAX_CRITERION_CHARS:
        return
    proposed[target] = candidate
    additions[target].append(phrase)


def _brt_date(text: object) -> Date | None:
    moment = parse_t(text)
    if moment is None:
        return None
    return moment.astimezone(brt_clock()).date()


def _conf(row: dict) -> float | None:
    value = row.get("conf")
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None
