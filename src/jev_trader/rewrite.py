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

Banda do erro (`band_mode`): `"vol"` (padrão) = `band_k` (0,5) × mediana do |retorno a 15 min| do SOL na própria
série `px_in` do log de decisões, na janela de 3 dias que acaba na última decisão revista, limitada a
[0,05%, 1,5%]; com menos de 30 retornos recua para a banda fixa `band`. `"fixed"` = `band` (0,1%), o modo antigo.

Palavras das frases: por lift, não por frequência. Por lado, lift = % dos erros com a palavra − % dos acertos com a
palavra; uma palavra só dispara frase com lift >= 0,2 (> 0), em >= 3 erros, >= 2 episódios de erro (separados por
mais de 5 min) e com >= 3 acertos de referência. Palavras de fundo (calm/deep/quiet… presentes em todos os erros e
acertos) ficam com lift 0. Sem palavra elegível → critérios iguais (`changed: false`).
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import os
from collections import Counter
from collections.abc import Mapping
from datetime import date as Date
from datetime import datetime, timedelta
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
from jev_trader.score import HORIZON, TOLERANCE, Timeline, build_timeline, forward_return, select_run

DEFAULT_PERCENTILE = 90.0
DEFAULT_FIXED_BAR = 0.8
DEFAULT_BAND = 0.001
DEFAULT_BAND_MODE = "vol"
DEFAULT_BAND_K = 0.5
DEFAULT_BAND_WINDOW = timedelta(days=3)
DEFAULT_BAND_FLOOR = 0.0005
DEFAULT_BAND_CAP = 0.015
DEFAULT_BAND_MIN_N = 30
BAND_MODES = ("fixed", "vol")
LIFT_DEFAULTS = {"min_lift": 0.2, "min_count": 3, "min_episodes": 2, "min_ref": 3}
EPISODE_GAP = timedelta(minutes=5)
LIFT_TABLE_ROWS = 8
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


def vol_band(
    timeline: Timeline,
    t_end: datetime | None,
    *,
    k: float = DEFAULT_BAND_K,
    window: timedelta = DEFAULT_BAND_WINDOW,
    floor: float = DEFAULT_BAND_FLOOR,
    cap: float = DEFAULT_BAND_CAP,
    min_n: int = DEFAULT_BAND_MIN_N,
    fallback: float = DEFAULT_BAND,
    horizon: timedelta = HORIZON,
    tolerance: timedelta = TOLERANCE,
) -> dict:
    """Banda = k × mediana de |retorno a 15 min| na janela [t_end − window, t_end] da série de `px_in`, limitada a
    [floor, cap]. Só retornos com o preço posterior também <= t_end. Menos de `min_n` retornos → `fallback`."""
    rets: list[float] = []
    if t_end is not None:
        times, prices = timeline.times, timeline.prices
        lo = bisect.bisect_left(times, t_end - window)
        hi = bisect.bisect_right(times, t_end - horizon)
        for i in range(lo, hi):
            j = bisect.bisect_left(times, times[i] + horizon)
            if j >= len(times) or times[j] > times[i] + horizon + tolerance or times[j] > t_end:
                continue
            rets.append(abs(prices[j] / prices[i] - 1.0))
    median = _median(rets)
    detail = {
        "k": k,
        "floor": floor,
        "cap": cap,
        "window_days": window.total_seconds() / 86400,
        "n": len(rets),
        "t_end": t_end.isoformat() if t_end is not None else None,
        "median_abs_ret": None if median is None else round(median, 8),
    }
    if len(rets) < int(min_n) or median is None:
        return {"band": float(fallback), "source": "fallback_fixed", "clamped": None, **detail}
    raw = float(k) * median
    value = min(float(cap), max(float(floor), raw))
    clamped = "floor" if raw < floor else ("cap" if raw > cap else None)
    return {"band": round(value, 8), "source": "vol", "clamped": clamped, **detail}


def word_lift(
    mistakes: list[dict],
    correct: list[dict],
    *,
    min_lift: float = LIFT_DEFAULTS["min_lift"],
    min_count: int = LIFT_DEFAULTS["min_count"],
    min_episodes: int = LIFT_DEFAULTS["min_episodes"],
    min_ref: int = LIFT_DEFAULTS["min_ref"],
    alpha: float = 0.5,
) -> list[dict]:
    """Tabela por palavra de estado (um só lado): % nos erros, % nos acertos, lift = diferença, log-odds suavizado
    (informativo), episódios de erro e `eligible` (pode disparar frase). Ordenada por lift desc."""
    n_m, n_o = len(mistakes), len(correct)
    in_err: Counter = Counter()
    in_ok: Counter = Counter()
    times: dict[str, list[datetime]] = {}
    for row in mistakes:
        words = set(str(row.get("state") or "").split())
        in_err.update(words)
        moment = parse_t(row.get("t"))
        for word in words:
            if moment is not None:
                times.setdefault(word, []).append(moment)
    for row in correct:
        in_ok.update(set(str(row.get("state") or "").split()))
    table = []
    for word in set(in_err) | set(in_ok):
        err_share = in_err[word] / n_m if n_m else None
        ok_share = in_ok[word] / n_o if n_o else None
        lift = err_share - ok_share if err_share is not None and ok_share is not None else None
        log_odds = None
        if n_m and n_o:
            log_odds = math.log((in_err[word] + alpha) / (n_m - in_err[word] + alpha)) - math.log(
                (in_ok[word] + alpha) / (n_o - in_ok[word] + alpha)
            )
        episodes = _episodes(times.get(word, []))
        eligible = (
            lift is not None
            and lift > 0
            and lift >= min_lift
            and n_o >= min_ref
            and in_err[word] >= min_count
            and episodes >= min_episodes
        )
        table.append(
            {
                "word": word,
                "n_err": in_err[word],
                "n_ok": in_ok[word],
                "err_share": None if err_share is None else round(err_share, 4),
                "ok_share": None if ok_share is None else round(ok_share, 4),
                "lift": None if lift is None else round(lift, 4),
                "log_odds": None if log_odds is None else round(log_odds, 3),
                "episodes": episodes,
                "eligible": eligible,
            }
        )
    table.sort(
        key=lambda r: (-(r["lift"] if r["lift"] is not None else -9.0), -(r["log_odds"] or 0.0), -r["n_err"], r["word"])
    )
    return table


def audit(
    answered: list[dict],
    timeline: Timeline,
    *,
    cutoff: float | None,
    band: float,
    lift: Mapping[str, float] | None = None,
) -> dict:
    """Confiantes = conf >= corte e ação final buy/sell (passaram os portões). Erro fora da banda a 15 min;
    acerto = movimento além da banda a favor; dentro da banda = flat. `word_lift` por lado (erros vs acertos)."""
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
    resolved = unresolved = flat = 0
    mistakes: list[dict] = []
    correct: list[dict] = []
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
        right = ret > band if side == "buy" else ret < -band
        item = {
            "t": row.get("t"),
            "action": side,
            "conf": _conf(row),
            "state": row.get("state"),
            "px_in": price,
            "px_later": later,
            "t_later": later_t,
            "ret": round(ret, 8),
            "band": band,
        }
        if wrong:
            mistakes.append(item)
        elif right:
            correct.append(item)
        else:
            flat += 1
    words: Counter = Counter()
    for mistake in mistakes:
        words.update(set(str(mistake.get("state") or "").split()))
    params = {**LIFT_DEFAULTS, **(lift or {})}
    tables = {
        side: word_lift(
            [m for m in mistakes if m["action"] == side], [c for c in correct if c["action"] == side], **params
        )
        for side in ("buy", "sell")
    }
    return {
        "cutoff": cutoff,
        "band": band,
        "n_answered": len(answered),
        "n_confident": len(confident),
        "n_model_directional_above_cutoff_blocked": blocked_above,
        "n_resolved": resolved,
        "n_unresolved": unresolved,
        "n_mistakes": len(mistakes),
        "n_correct": len(correct),
        "n_flat": flat,
        "mistakes": mistakes,
        "correct": correct,
        "word_counts": dict(sorted(words.items(), key=lambda item: (-item[1], item[0]))),
        "word_lift": {side: rows[:LIFT_TABLE_ROWS] for side, rows in tables.items()},
        "lift_words": {side: [r["word"] for r in rows if r["eligible"]] for side, rows in tables.items()},
    }


def propose_criteria(
    current: dict[str, str],
    mistakes: list[dict],
    correct: list[dict] | None = None,
    *,
    min_lift: float = LIFT_DEFAULTS["min_lift"],
    min_count: int = LIFT_DEFAULTS["min_count"],
    min_episodes: int = LIFT_DEFAULTS["min_episodes"],
    min_ref: int = LIFT_DEFAULTS["min_ref"],
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Acrescenta frases conforme as palavras de estado com lift positivo de cada lado (erros vs acertos `correct`
    do mesmo lado; ver `word_lift`). Palavra de fundo (tão frequente nos acertos como nos erros) não dispara nada.

    Sem erros, sem acertos de referência (`correct` None/vazio) ou sem palavra elegível → critérios iguais aos atuais.
    Palavras elegíveis que não casam com nenhuma regra → FALLBACK_PHRASE. Frase já presente ou que passaria do
    limite não entra.
    """
    proposed = dict(current)
    additions: dict[str, list[str]] = {key: [] for key in CRITERIA_KEYS}
    correct = correct or []
    for side in ("buy", "sell"):
        side_mistakes = [m for m in mistakes if m.get("action") == side]
        if not side_mistakes:
            continue
        table = word_lift(
            side_mistakes,
            [c for c in correct if c.get("action") == side],
            min_lift=min_lift,
            min_count=min_count,
            min_episodes=min_episodes,
            min_ref=min_ref,
        )
        distinctive = {row["word"] for row in table if row["eligible"]}
        if not distinctive:
            continue
        fired = False
        for rule_side, triggers, target, phrase in RULES:
            if rule_side != side or not (triggers & distinctive):
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
    band_mode: str = DEFAULT_BAND_MODE,
    band_k: float = DEFAULT_BAND_K,
    band_window: timedelta = DEFAULT_BAND_WINDOW,
    band_floor: float = DEFAULT_BAND_FLOOR,
    band_cap: float = DEFAULT_BAND_CAP,
    band_min_n: int = DEFAULT_BAND_MIN_N,
    lift: Mapping[str, float] | None = None,
) -> dict:
    """Proposta completa. O texto sai da auditoria por percentil; a barra fixa fica só para comparação.
    `band` é a banda fixa (modo "fixed") ou o recurso do modo "vol" quando há poucos retornos na janela."""
    if band_mode not in BAND_MODES:
        raise RewriteError(f"band_mode must be one of {BAND_MODES}")
    run = select_run(decisions, experiment)
    timeline = build_timeline(run)
    if review_date is None:
        window = run
    else:
        window = [row for row in run if _brt_date(row.get("t")) == review_date]
    if band_mode == "vol":
        ends = [m for m in (parse_t(row.get("t")) for row in window) if m is not None]
        band_detail = vol_band(
            timeline, max(ends) if ends else None, k=band_k, window=band_window, floor=band_floor, cap=band_cap,
            min_n=band_min_n, fallback=band,
        )
    else:
        band_detail = {"band": band, "source": "fixed"}
    used_band = band_detail["band"]
    params = {**LIFT_DEFAULTS, **(lift or {})}
    answered = model_answered(window)
    confidences = [c for c in (_conf(row) for row in answered) if c is not None]
    cut = percentile_cutoff(confidences, percentile)
    by_percentile = audit(answered, timeline, cutoff=cut, band=used_band, lift=params)
    by_fixed = audit(answered, timeline, cutoff=fixed_bar, band=used_band, lift=params)
    proposed, additions = propose_criteria(current, by_percentile["mistakes"], by_percentile["correct"], **params)
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
            "band": used_band,
            "band_mode": band_mode,
            "band_fixed": band,
            "band_detail": band_detail,
            "word_selection": {"method": "lift", **params},
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
    band_mode: str = DEFAULT_BAND_MODE,
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
        percentile=percentile, fixed_bar=fixed_bar, band=band, now_t=now_t, band_mode=band_mode,
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


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _episodes(times: list[datetime], gap: timedelta = EPISODE_GAP) -> int:
    """Nº de episódios: momentos separados por mais de `gap` contam como episódio novo."""
    count = 0
    last = None
    for moment in sorted(times):
        if last is None or moment - last > gap:
            count += 1
        last = moment
    return count


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
