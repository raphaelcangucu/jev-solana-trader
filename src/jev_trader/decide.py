"""Cliente System One (HTTP para `von serve`, com fallback no processo) e portões."""

from __future__ import annotations

import math
from dataclasses import dataclass

from jev_trader.config import Config
from jev_trader.criteria import DEFAULT_CRITERIA, load_criteria, questions_for

ACTION_INSTRUCTIONS = "buy on strength only when the book can absorb it"

# As perguntas do artigo, fixas. Um `config/criteria.json` aprovado e válido substitui os critérios.
ARTICLE_QUESTIONS = questions_for(DEFAULT_CRITERIA, ACTION_INSTRUCTIONS)


def current_questions(cfg: Config) -> dict:
    """Critérios aprovados se existirem e forem válidos; senão as frases do artigo (fail-safe)."""
    criteria, _source = load_criteria(getattr(cfg, "criteria_path", None))
    return questions_for(criteria, ACTION_INSTRUCTIONS)


@dataclass(frozen=True)
class ModelAnswer:
    ok: bool
    choice: str
    confidence: float
    skip_noul: float
    probabilities: dict[str, float]
    source: str
    error: str | None = None


@dataclass(frozen=True)
class Gate:
    action: str
    reason: str
    execute: bool


def fail_closed(error: str, source: str = "fail-closed") -> ModelAnswer:
    return ModelAnswer(
        ok=False,
        choice="hold",
        confidence=0.0,
        skip_noul=1.0,
        probabilities={"buy": 0.0, "sell": 0.0, "hold": 1.0},
        source=source,
        error=_clip(error),
    )


def parse_system_one_payload(payload: object, source: str) -> ModelAnswer:
    body = _unwrap_answers(payload)
    action = _dig(body, "action")
    skip = _dig(body, "skip_this_cycle")
    if action is None or skip is None:
        return fail_closed("system one payload missing action or skip", source=source)
    choice = _dig(action, "choice")
    if choice is None:
        choice = _dig(action, "value")
    confidence = _dig(action, "confidence")
    probabilities = _dig(action, "probabilities")
    if probabilities is None:
        probabilities = _dig(action, "probs") or {}
    skip_noul = _dig(skip, "noul")
    if skip_noul is None:
        prob = _dig(skip, "prob")
        if prob is not None:
            skip_noul = prob
        else:
            value = _dig(skip, "value")
            if isinstance(value, bool):
                skip_noul = 1.0 if value else 0.0
    if not isinstance(choice, str):
        return fail_closed("system one choice missing", source=source)
    choice = choice.strip().lower()
    if choice not in {"buy", "sell", "hold"}:
        return fail_closed("system one choice outside buy sell hold", source=source)
    try:
        confidence_f = float(confidence)
        skip_f = float(skip_noul)
    except (TypeError, ValueError):
        return fail_closed("system one confidence or skip is not numeric", source=source)
    if not math.isfinite(confidence_f) or not math.isfinite(skip_f):
        return fail_closed("system one confidence or skip is not finite", source=source)
    if not 0.0 <= confidence_f <= 1.0 or not 0.0 <= skip_f <= 1.0:
        return fail_closed("system one confidence or skip outside 0..1", source=source)
    probs: dict[str, float] = {}
    if isinstance(probabilities, dict):
        for key, value in probabilities.items():
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                probs[str(key)] = number
    return ModelAnswer(
        ok=True,
        choice=choice,
        confidence=confidence_f,
        skip_noul=skip_f,
        probabilities=probs,
        source=source,
    )


def apply_thresholds(
    choice: str,
    confidence: float,
    skip_noul: float,
    *,
    confidence_min: float,
    skip_min: float,
) -> Gate:
    if choice not in {"buy", "sell", "hold"}:
        return Gate("hold", "fail_closed", False)
    if skip_noul >= skip_min:
        return Gate("hold", "skip", False)
    if confidence < confidence_min:
        return Gate("hold", "low_confidence", False)
    if choice == "hold":
        return Gate("hold", "model_hold", False)
    return Gate(choice, "execute", True)


def resolve_action(
    model: ModelAnswer,
    *,
    market_ok: bool,
    confidence_min: float,
    skip_min: float,
) -> Gate:
    if not model.ok:
        return Gate("hold", "fail_closed", False)
    if not market_ok:
        return Gate("hold", "market_unavailable", False)
    return apply_thresholds(
        model.choice,
        model.confidence,
        model.skip_noul,
        confidence_min=confidence_min,
        skip_min=skip_min,
    )


def ask_system_one(state: str, cfg: Config) -> ModelAnswer:
    http_error: Exception | None = None
    try:
        return _ask_http(state, cfg)
    except Exception as exc:
        http_error = exc
    try:
        return _ask_local(state, cfg)
    except Exception as exc:
        return fail_closed(f"von http: {http_error}; local: {exc}")


def _ask_http(state: str, cfg: Config) -> ModelAnswer:
    import httpx

    payload = {"model": cfg.von_model, "state": state, "questions": current_questions(cfg)}
    timeout = httpx.Timeout(cfg.von_timeout_s, connect=min(2.0, cfg.von_timeout_s))
    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{cfg.von_base_url}/v1/systemone", json=payload)
        response.raise_for_status()
        body = response.json()
    answer = parse_system_one_payload(body, source="von-http")
    if not answer.ok:
        raise RuntimeError(answer.error or "incomplete system one payload")
    return answer


def _ask_local(state: str, cfg: Config) -> ModelAnswer:
    import von

    choice = getattr(von, "choice", None)
    noul = getattr(von, "noul", None)
    spec = current_questions(cfg)
    if callable(choice) and callable(noul):
        questions = {
            "action": choice(
                instructions=spec["action"]["instructions"],
                criteria=spec["action"]["criteria"],
            ),
            "skip_this_cycle": noul(
                instructions=spec["skip_this_cycle"]["instructions"],
            ),
        }
    else:
        questions = spec
    system_one = getattr(von, "system_one", None)
    if not callable(system_one):
        raise RuntimeError("von.system_one is unavailable")
    try:
        response = system_one(state=state, questions=questions, model=cfg.von_model)
    except TypeError:
        response = system_one(state, questions)
    answer = parse_system_one_payload(response, source="von-local")
    if not answer.ok:
        raise RuntimeError(answer.error or "incomplete local system one payload")
    return answer


def _unwrap_answers(payload: object) -> object:
    answers = _dig(payload, "answers")
    if answers is not None:
        return answers
    return payload


def _dig(obj: object, key: str) -> object:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _clip(text: str) -> str:
    cleaned = " ".join(str(text).split())
    return cleaned[:180]
