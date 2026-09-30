"""Von System One client — HTTP to long-running von serve. Fail-closed to hold."""
from __future__ import annotations
import json, time, urllib.request, urllib.error
from pathlib import Path
from typing import Any

def load_criteria(path: Path) -> dict:
    return json.loads(Path(path).read_text())

def criteria_to_questions(criteria: dict) -> dict:
    return {
        "action": {
            "type": "choice",
            "instructions": criteria["action"]["instructions"],
            "criteria": criteria["action"]["criteria"],
        },
        "skip_this_cycle": {
            "type": "noul",
            "instructions": criteria["skip_this_cycle"]["instructions"],
        },
    }

class VonClient:
    def __init__(self, cfg: dict):
        self.base = cfg["von"]["base_url"].rstrip("/")
        self.timeout = float(cfg["von"].get("timeout_seconds", 30))

    def system_one(self, state: str, criteria: dict) -> dict[str, Any]:
        body = json.dumps({"state": state, "questions": criteria_to_questions(criteria)}).encode()
        req = urllib.request.Request(
            f"{self.base}/v1/systemone", data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST",
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read().decode())
            return normalize(raw, (time.perf_counter()-t0)*1000, True, None)
        except Exception as e:
            return normalize(None, (time.perf_counter()-t0)*1000, False, f"{type(e).__name__}: {e}")

def normalize(raw: Any, latency_ms: float, ok: bool, error: str | None) -> dict:
    if not ok or raw is None:
        return {
            "ok": False, "error": error or "unknown", "chosen_action": "hold",
            "probabilities": {"buy": 0.0, "sell": 0.0, "hold": 1.0},
            "confidence": 0.0, "skip_noul": 1.0, "latency_ms": round(latency_ms, 2),
            "raw": None, "fail_closed": True,
        }
    answers = raw.get("answers") if isinstance(raw, dict) else None
    if answers is None and isinstance(raw, dict) and "action" in raw:
        answers = raw
    if not isinstance(answers, dict):
        answers = {}
    action = answers.get("action") or {}
    skip = answers.get("skip_this_cycle") or {}
    probs = {k: float(v) for k, v in (action.get("probabilities") or action.get("probs") or {}).items()}
    choice = action.get("choice") or action.get("value") or "hold"
    conf = action.get("confidence")
    try:
        conf = float(conf) if conf is not None else _peak(probs)
    except Exception:
        conf = _peak(probs)
    skip_noul = 0.0
    if isinstance(skip, dict):
        for key in ("noul", "prob", "value"):
            if key in skip and skip[key] is not None and not isinstance(skip[key], bool):
                try:
                    skip_noul = float(skip[key]); break
                except Exception:
                    pass
    return {
        "ok": True, "error": None, "chosen_action": str(choice), "probabilities": probs,
        "confidence": float(conf), "skip_noul": float(skip_noul),
        "latency_ms": round(latency_ms, 2), "raw": raw, "fail_closed": False,
        "model": raw.get("model") if isinstance(raw, dict) else None,
        "usage": raw.get("usage") if isinstance(raw, dict) else None,
    }

def _peak(probs: dict) -> float:
    if not probs: return 0.0
    vals = sorted((float(v) for v in probs.values()), reverse=True)
    return vals[0] if len(vals)==1 else max(0.0, vals[0]-vals[1])
