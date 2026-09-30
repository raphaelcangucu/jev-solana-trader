"""Pluggable System One decision backends. Simulation only — never signs txs / never reads keys."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path("/home/box/solana-trader/paper")

def load_models_cfg() -> dict:
    return json.loads((ROOT / "models.json").read_text())


def _peak(probs: dict) -> float:
    if not probs:
        return 0.0
    v = sorted((float(x) for x in probs.values()), reverse=True)
    return v[0] if len(v) == 1 else max(0.0, v[0] - v[1])


def _normalize_answer(raw: Any, latency_ms: float, model_id: str) -> dict:
    """Normalize various System One response shapes into bot decision dict."""
    if not isinstance(raw, dict):
        return {
            "ok": False, "error": f"bad_raw:{type(raw).__name__}",
            "chosen_action": "hold", "probabilities": {"buy": 0, "sell": 0, "hold": 1},
            "confidence": 0.0, "skip_noul": 1.0, "latency_ms": round(latency_ms, 2),
            "fail_closed": True, "model": model_id,
        }
    answers = raw.get("answers") or (raw if "action" in raw else {})
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
        for k in ("noul", "prob", "value"):
            if k in skip and skip[k] is not None and not isinstance(skip[k], bool):
                try:
                    skip_noul = float(skip[k])
                    break
                except Exception:
                    pass
        else:
            if isinstance(skip.get("value"), bool):
                skip_noul = 1.0 if skip["value"] else 0.0
    return {
        "ok": True, "error": None,
        "chosen_action": str(choice),
        "probabilities": probs,
        "confidence": float(conf),
        "skip_noul": float(skip_noul),
        "latency_ms": round(latency_ms, 2),
        "fail_closed": False,
        "model": model_id,
        "raw": raw,
    }


def _http_post_json(url: str, payload: dict, timeout: float, headers: dict | None = None) -> tuple[int, Any]:
    data = json.dumps(payload).encode()
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        try:
            return e.code, json.loads(body.decode())
        except Exception:
            return e.code, {"error": body.decode(errors="replace")[:300]}
    except Exception as e:
        return 0, {"error": str(e)}


def call_http_systemone(base_url: str, state: str, criteria: dict, timeout: float, model_id: str,
                        extra_headers: dict | None = None, model_name: str | None = None) -> dict:
    questions = {
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
    payload: dict[str, Any] = {"state": state, "questions": questions}
    if model_name:
        payload["model"] = model_name
    url = base_url.rstrip("/") + "/v1/systemone"
    t0 = time.perf_counter()
    code, raw = _http_post_json(url, payload, timeout, extra_headers)
    lat = (time.perf_counter() - t0) * 1000
    if code != 200 or not isinstance(raw, dict) or raw.get("error"):
        return {
            "ok": False,
            "error": f"http_{code}:{raw.get('error') if isinstance(raw, dict) else raw}",
            "chosen_action": "hold",
            "probabilities": {"buy": 0, "sell": 0, "hold": 1},
            "confidence": 0.0, "skip_noul": 1.0,
            "latency_ms": round(lat, 2), "fail_closed": True, "model": model_id,
        }
    return _normalize_answer(raw, lat, model_id)


def call_hosted_jev(cfg: dict, state: str, criteria: dict, timeout: float) -> dict:
    """Official hosted Jev. Key ONLY from env JEV_API_KEY — never log/write the key."""
    env_name = cfg.get("api_key_env") or "JEV_API_KEY"
    key = os.environ.get(env_name) or ""
    if not key.strip():
        return {
            "ok": False, "error": "aguardando chave",
            "chosen_action": "hold",
            "probabilities": {"buy": 0, "sell": 0, "hold": 1},
            "confidence": 0.0, "skip_noul": 1.0,
            "latency_ms": 0.0, "fail_closed": True, "model": "jev",
            "status": "aguardando chave",
        }
    base = (cfg.get("base_url") or "https://api.typesafe.ai").rstrip("/")
    # Do not put key in any logged structure
    headers = {"Authorization": f"Bearer {key}"}
    return call_http_systemone(
        base, state, criteria, timeout, "jev",
        extra_headers=headers,
        model_name=cfg.get("model_name") or "jev-latest",
    )


def decide(model_id: str, backend_cfg: dict, state: str, criteria: dict, timeout: float = 30.0) -> dict:
    kind = backend_cfg.get("kind") or "http_systemone"
    if kind == "hosted_typesafe":
        return call_hosted_jev(backend_cfg, state, criteria, timeout)
    base = backend_cfg.get("base_url") or ""
    return call_http_systemone(base, state, criteria, timeout, model_id)


def enabled_backends(models_cfg: dict | None = None) -> dict[str, dict]:
    cfg = models_cfg or load_models_cfg()
    out = {}
    for mid, b in (cfg.get("backends") or {}).items():
        if not b.get("enabled"):
            continue
        if b.get("kind") == "hosted_typesafe":
            # enabled in JSON but still needs key; leave in list for status
            out[mid] = b
            continue
        out[mid] = b
    return out


def decide_many(jobs: list[tuple[str, dict, str, dict, float]], max_workers: int = 4) -> dict[str, dict]:
    """Run multiple backend calls concurrently. jobs: (model_id, backend_cfg, state, criteria, timeout)."""
    results: dict[str, dict] = {}
    if not jobs:
        return results
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(jobs)))) as ex:
        futs = {
            ex.submit(decide, mid, bcfg, state, crit, timeout): mid
            for mid, bcfg, state, crit, timeout in jobs
        }
        for fut in as_completed(futs):
            mid = futs[fut]
            try:
                results[mid] = fut.result()
            except Exception as e:
                results[mid] = {
                    "ok": False, "error": f"{type(e).__name__}:{e}",
                    "chosen_action": "hold",
                    "probabilities": {"buy": 0, "sell": 0, "hold": 1},
                    "confidence": 0.0, "skip_noul": 1.0,
                    "latency_ms": 0.0, "fail_closed": True, "model": mid,
                }
    return results


def jev_key_status(models_cfg: dict | None = None) -> dict:
    cfg = (models_cfg or load_models_cfg()).get("backends", {}).get("jev") or {}
    env_name = cfg.get("api_key_env") or "JEV_API_KEY"
    present = bool((os.environ.get(env_name) or "").strip())
    enabled = bool(cfg.get("enabled"))
    if not enabled:
        status = "disabled"
    elif not present:
        status = "aguardando chave"
    else:
        status = "ready"
    return {
        "enabled": enabled,
        "key_present": present,
        "status": status,
        "api_key_env": env_name,
        "endpoint": (cfg.get("base_url") or "https://api.typesafe.ai").rstrip("/") + (cfg.get("endpoint") or "/v1/systemone"),
        "live_trading": False,
    }
