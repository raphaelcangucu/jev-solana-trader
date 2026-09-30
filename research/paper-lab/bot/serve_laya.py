#!/usr/bin/env python3
"""Local Laya System One HTTP shim — POST /v1/systemone. Simulation aid only."""
from __future__ import annotations
import json, os, sys, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("HF_HOME", "/workspace/jev-alts/hf-cache")
os.environ.setdefault("TRANSFORMERS_CACHE", "/workspace/jev-alts/hf-cache")
os.environ.setdefault("HF_HUB_CACHE", "/workspace/jev-alts/hf-cache/hub")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

PORT = int(os.environ.get("LAYA_PORT", "8766"))
AGENT = None

def get_agent():
    global AGENT
    if AGENT is None:
        import warnings
        from laya import Agent
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            AGENT = Agent(device="cpu")
        print("laya agent loaded", flush=True)
    return AGENT

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
            self._send(200, {"ok": True, "service": "laya-shim", "port": PORT})
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
            agent = get_agent()
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                raw = agent.system_one(state, questions)
            if isinstance(raw, dict) and "answers" not in raw and "action" in raw:
                raw = {"answers": raw, "model": "laya-local"}
            elif isinstance(raw, dict) and "model" not in raw:
                raw = dict(raw)
                raw.setdefault("model", "laya-local")
            self._send(200, raw if isinstance(raw, dict) else {"answers": raw})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": f"{type(e).__name__}:{e}"})

def main():
    # warm load in main thread
    get_agent()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"laya-shim listening 127.0.0.1:{PORT}", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
