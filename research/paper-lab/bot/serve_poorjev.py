#!/usr/bin/env python3
"""Local poorjev System One HTTP shim — adapts criteria into state; POST /v1/systemone."""
from __future__ import annotations
import json, os, sys, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_JEV_ALTS = os.environ.get("JEV_ALTS_ROOT") or "/workspace/jev-alts"
os.environ.setdefault("HF_HOME", f"{_JEV_ALTS}/hf-cache")
os.environ.setdefault("TRANSFORMERS_CACHE", f"{_JEV_ALTS}/hf-cache")
os.environ.setdefault("HF_HUB_CACHE", f"{_JEV_ALTS}/hf-cache/hub")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

PORT = int(os.environ.get("POORJEV_PORT", "8767"))
CLIENT = None

def get_client():
    global CLIENT
    if CLIENT is None:
        import warnings
        from poorjev import Client
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            CLIENT = Client()
        print("poorjev client loaded", flush=True)
    return CLIENT

def adapt_and_ask(state: str, questions: dict):
    """poorjev Choice takes option list only — prepend criteria into state."""
    import warnings
    from poorjev import Choice, Noul
    action_q = questions.get("action") or {}
    skip_q = questions.get("skip_this_cycle") or {}
    criteria = action_q.get("criteria") or {"buy": "buy", "sell": "sell", "hold": "hold"}
    instr = action_q.get("instructions") or "choose action"
    crit_blob = "; ".join(f"{k}: {v}" for k, v in criteria.items())
    skip_stmt = skip_q.get("instructions") or "skip trading this cycle?"
    short_options = list(criteria.keys()) if criteria else ["buy", "sell", "hold"]
    # ensure buy/sell/hold order if present
    for req in ("buy", "sell", "hold"):
        if req not in short_options:
            short_options.append(req)
    pj_questions = {
        "action": Choice(short_options),
        "skip_this_cycle": Noul(skip_stmt),
    }
    aug = f"Instruction: {instr}. Criteria: {crit_blob}. State: {state}"
    client = get_client()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw_ans = client.ask(aug, pj_questions)
    action = raw_ans["action"]
    skip = raw_ans["skip_this_cycle"]
    probs = getattr(action, "probs", None) or getattr(action, "probabilities", None) or {}
    if hasattr(probs, "items"):
        probs = {k: float(v) for k, v in probs.items()}
    skip_prob = getattr(skip, "prob", None)
    if skip_prob is None:
        skip_prob = getattr(skip, "noul", None)
    if skip_prob is None and hasattr(skip, "value"):
        skip_prob = 1.0 if skip.value else 0.0
    return {
        "answers": {
            "action": {
                "choice": getattr(action, "value", None),
                "confidence": getattr(action, "confidence", None),
                "probabilities": probs,
            },
            "skip_this_cycle": {
                "noul": float(skip_prob) if skip_prob is not None else 0.0,
            },
        },
        "model": "poorjev-local",
        "note": "criteria prepended into state; Choice(options) adapted",
    }

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/health", "/docs", "/openapi.json", "/"):
            self._send(200, {"ok": True, "service": "poorjev-shim", "port": PORT})
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/systemone":
            self._send(404, {"error": "not_found"})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n).decode() or "{}")
            state = payload.get("state") or ""
            questions = payload.get("questions") or {}
            raw = adapt_and_ask(state, questions)
            self._send(200, raw)
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": f"{type(e).__name__}:{e}"})

def main():
    get_client()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"poorjev-shim listening 127.0.0.1:{PORT}", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
