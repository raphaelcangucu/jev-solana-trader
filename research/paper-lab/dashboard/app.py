#!/usr/bin/env python3
"""Paper trading dashboard — SIMULATION ONLY. No live trading. No keypair access."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, time
from urllib.parse import parse_qs
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
import uvicorn

import sys as _sys_paths
_LAB = str(Path(__file__).resolve().parents[1])  # código do lab (research/paper-lab)
if _LAB not in _sys_paths.path:
    _sys_paths.path.insert(0, _LAB)
from bot.paths import ROOT, LAB_DIR  # noqa: E402  (ROOT = PAPER_LAB_ROOT ou a pasta do lab)
from bot import params as P  # noqa: E402  (params.json por tipo de teste; resolver + validação)
DASH = ROOT / "dashboard"          # dados locais: .auth, url.txt (fora do git)
DASH_CODE = LAB_DIR / "dashboard"  # código: static/, defaults.py, api_v2.py
BRT = timezone(timedelta(hours=-3))
security = HTTPBasic(auto_error=False)
SESSION_COOKIE = "lab_session"

# Hard deny — never serve these
FORBIDDEN_NAMES = {"keypair.json", "secret.b58", ".auth"}
FORBIDDEN_PREFIXES = (str(ROOT.parent / "keypair.json"),
                      str(ROOT.parent / "secret.b58"))

app = FastAPI(title="Paper Solana Simulator", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(DASH_CODE / "static")), name="static")


def brt_iso(ts=None):
    return datetime.fromtimestamp(ts or time.time(), tz=BRT).isoformat()


def read_auth():
    raw = (DASH / ".auth").read_text().strip()
    user, _, pw = raw.partition(":")
    return user, pw


def _session_token() -> str:
    """Token do cookie de sessão: HMAC derivado do .auth (muda se a senha mudar)."""
    key = hashlib.sha256((DASH / ".auth").read_bytes()).digest()
    return hmac.new(key, b"lab-session-v1", hashlib.sha256).hexdigest()


def _creds_ok(username: str, password: str) -> bool:
    user, pw = read_auth()
    return secrets.compare_digest(username, user) & secrets.compare_digest(password, pw)


def require_auth(request: Request, credentials: HTTPBasicCredentials | None = Depends(security)):
    """HTTP Basic (scripts, curl) ou cookie de sessão de /login (navegador sem diálogo Basic)."""
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie and secrets.compare_digest(cookie, _session_token()):
        return read_auth()[0]
    if credentials and _creds_ok(credentials.username, credentials.password):
        return credentials.username
    if request.method == "GET" and not request.url.path.startswith("/api"):
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Basic"},
    )


_LOGIN_HTML = """<!doctype html><html lang="pt"><head><meta charset="utf-8"><title>Paper lab — entrar</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui,sans-serif;background:#0f1115;color:#e6e6e6;display:grid;place-items:center;height:100vh;margin:0}
form{background:#181b22;padding:24px 28px;border-radius:10px;display:grid;gap:10px;min-width:260px}
input,button{font:inherit;padding:8px 10px;border-radius:6px;border:1px solid #333;background:#0f1115;color:inherit}
button{background:#2d6cdf;border:0;cursor:pointer}p{margin:0;color:#f87171;font-size:14px}</style></head>
<body><form method="post" action="/login"><strong>Paper lab (simulação)</strong>
<input name="username" placeholder="utilizador" autocomplete="username" required>
<input name="password" type="password" placeholder="senha" autocomplete="current-password" required>
<button type="submit">Entrar</button>__ERR__</form></body></html>"""


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return _LOGIN_HTML.replace("__ERR__", "")


@app.post("/login")
async def login_submit(request: Request):
    form = parse_qs((await request.body()).decode("utf-8", "replace"))
    if not _creds_ok((form.get("username") or [""])[0], (form.get("password") or [""])[0]):
        return HTMLResponse(_LOGIN_HTML.replace("__ERR__", "<p>Credenciais inválidas.</p>"), status_code=401)
    resp = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    # Só 127.0.0.1: sem Secure (HTTP local); HttpOnly + SameSite=Strict contra uso cruzado.
    resp.set_cookie(SESSION_COOKIE, _session_token(), httponly=True, samesite="strict", max_age=40 * 86400)
    return resp


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def read_jsonl(path: Path, limit: int | None = None):
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    if limit:
        return rows[-limit:]
    return rows


def safe_paper_path(rel: str) -> Path:
    """Resolve a path under paper/ only; block traversal and key files."""
    rel = (rel or "").lstrip("/")
    if ".." in rel.split("/") or rel.startswith(".."):
        raise HTTPException(403, "path traversal blocked")
    name = Path(rel).name
    if name in FORBIDDEN_NAMES or name.endswith(".b58"):
        raise HTTPException(403, "forbidden file")
    target = (ROOT / rel).resolve()
    root_res = ROOT.resolve()
    if not str(target).startswith(str(root_res) + os.sep) and target != root_res:
        raise HTTPException(403, "outside paper root")
    for bad in FORBIDDEN_PREFIXES:
        if str(target) == bad or str(target).startswith(bad):
            raise HTTPException(403, "forbidden")
    # also block absolute escape to parent solana-trader keys
    if "keypair" in target.name.lower() or "secret" in target.name.lower():
        raise HTTPException(403, "forbidden name")
    return target


def load_overlay() -> dict:
    return read_json(ROOT / "data" / "params_overlay.json", {"bots": {}, "portfolios": {}}) or {"bots": {}, "portfolios": {}}


def save_overlay(obj: dict):
    path = ROOT / "data" / "params_overlay.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)


def log_param_change(portfolio: str, field: str, old, new, who="dashboard"):
    row = {
        "ts": time.time(), "ts_brt": brt_iso(),
        "portfolio": portfolio, "field": field,
        "old": old, "new": new, "who": who,
    }
    with open(ROOT / "logs" / "param_changes.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def _pid_running(pid: int) -> bool:
    """Portável (Linux e macOS): sinal 0 só testa a existência do processo."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def pid_alive(name: str) -> dict:
    pf = ROOT / "run" / f"{name}.pid"
    if not pf.exists():
        return {"name": name, "running": False, "pid": None}
    try:
        pid = int(pf.read_text().strip())
        running = (ROOT / "run").exists() and (_pid_running(pid))
        return {"name": name, "running": running, "pid": pid}
    except Exception:
        return {"name": name, "running": False, "pid": None}


def portfolio_names() -> list[str]:
    names = ["baseline", "relaxed", "v2", "grid_sol_2pct", "rsi_sol_1h", "hybrid_von_relaxed_cap2"]
    models = read_json(ROOT / "models.json", {}) or {}
    for mid, b in (models.get("backends") or {}).items():
        if mid == "von":
            continue
        for p in b.get("sol_portfolios") or []:
            if p not in names:
                names.append(p)
    # meme virtual portfolios for controls
    for suffix in ("meme_baseline", "meme_relaxed", "meme_rule_regime", "meme_rule_donch_regime", "hybrid_poorjev_regime"):
        if suffix not in names:
            names.append(suffix)
    # per-coin rule pause keys (optional)
    memecoins = read_json(ROOT / "memecoins.json", {}) or {}
    for t in memecoins.get("tokens") or []:
        sym = t["symbol"]
        for suf in ("_rule_regime", "_rule_donch_regime", "_hybrid_poorjev_regime", "_rule_regime_full", "_rule_donch_regime_full"):
            n = f"{sym}{suf}"
            if n not in names:
                names.append(n)
    for suffix in ("meme_rule_regime_full", "meme_rule_donch_regime_full"):
        if suffix not in names:
            names.append(suffix)
    reg = read_json(ROOT / "data" / "lab" / "registry.json", {}) or {}
    for n in (reg.get("portfolios") or {}):
        if n not in names:
            names.append(n)
    return names


V2_DIST = LAB_DIR / "dashboard-v2" / "dist"
NO_CACHE = {"Cache-Control": "no-cache"}


def _v2_ready() -> bool:
    return (V2_DIST / "index.html").exists() and os.environ.get("DASHBOARD_UI", "v2") != "legacy"


@app.get("/", response_class=HTMLResponse)
def index(_: str = Depends(require_auth)):
    """New UI (dashboard-v2 build) by default; legacy stays at /legacy."""
    if _v2_ready():
        return HTMLResponse((V2_DIST / "index.html").read_text(), headers=NO_CACHE)
    return (DASH_CODE / "static" / "index.html").read_text()


@app.get("/legacy", response_class=HTMLResponse)
@app.get("/legacy/", response_class=HTMLResponse)
def legacy_index(_: str = Depends(require_auth)):
    return (DASH_CODE / "static" / "index.html").read_text()


@app.get("/assets/{fname:path}")
def v2_assets(fname: str, _: str = Depends(require_auth)):
    """Hashed static build assets (behind the same basic auth)."""
    base = (V2_DIST / "assets").resolve()
    target = (base / fname).resolve()
    if not str(target).startswith(str(base) + os.sep) or not target.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(target, headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/favicon.svg")
def v2_favicon(_: str = Depends(require_auth)):
    f = V2_DIST / "favicon.svg"
    if not f.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(f)


@app.get("/api/health")
def api_health(_: str = Depends(require_auth)):
    status_j = read_json(ROOT / "status.json", {}) or {}
    meme = read_json(ROOT / "data" / "meme" / "status.json", {}) or {}
    age = time.time() - float(status_j.get("ts") or 0) if status_j else None
    procs = [pid_alive(n) for n in ("supervisor", "von", "laya", "poorjev", "sol", "meme", "rules", "lab", "nightly", "dashboard", "tunnel")]
    url = ""
    up = DASH / "url.txt"
    if up.exists():
        url = up.read_text().strip()
    return {
        "ts_brt": brt_iso(),
        "heartbeat_age_s": age,
        "sol_status": status_j,
        "meme_status": meme,
        "processes": procs,
        "dashboard_url": url,
        "paper_only": True,
        "live_trading": False,
    }


@app.get("/api/overview")
def api_overview(_: str = Depends(require_auth)):
    status_j = read_json(ROOT / "status.json", {}) or {}
    price = status_j.get("price_usd")
    ports = {}
    for name in portfolio_names():
        if name.startswith("meme_"):
            continue
        pdata = read_json(ROOT / "data" / f"portfolio_{name}.json")
        if not pdata and name not in status_j:
            continue
        st = status_j.get(name) or {}
        sol = float((st.get("sol") if st.get("sol") is not None else (pdata or {}).get("sol") or 0))
        usdt = float((st.get("usdt") if st.get("usdt") is not None else (pdata or {}).get("usdt") or 0))
        eq = float(st.get("equity_usd") or (usdt + sol * float(price or 0)))
        start_sol = float((pdata or {}).get("start_sol") or 0)
        start_usdt = float((pdata or {}).get("start_usdt") or 0)
        start_eq = start_usdt + start_sol * float((pdata or {}).get("start_price") or price or 0)
        bh = start_usdt + start_sol * float(price or 0)
        exp = (100.0 * sol * float(price or 0) / eq) if eq > 0 and price else 0.0
        ports[name] = {
            "sol": sol, "usdt": usdt, "equity_usd": eq,
            "pnl_vs_start": eq - start_eq,
            "pnl_vs_bh": eq - bh,
            "sol_exposure_pct": exp,
            "trades": st.get("trades") if st.get("trades") is not None else (pdata or {}).get("trade_count"),
            "last_final": st.get("last_final"),
            "last_chosen": st.get("last_chosen"),
            "last_conf": st.get("last_conf"),
            "gate_reasons": st.get("gate_reasons"),
            "model": st.get("model") or (pdata or {}).get("model") or ("von" if name in ("baseline","relaxed","v2") else None),
            "started_brt": (pdata or {}).get("started_brt"),
        }
    # Merge rule SOL portfolios from rules status / files
    rules_st = read_json(ROOT / "data" / "rules" / "status.json", {}) or {}
    for rname, rp in (rules_st.get("portfolios") or {}).items():
        pdata = read_json(ROOT / "data" / f"portfolio_{rname}.json") or {}
        sol = float(rp.get("sol") if rp.get("sol") is not None else pdata.get("sol") or 0)
        usdt = float(rp.get("usdt") if rp.get("usdt") is not None else pdata.get("usdt") or 0)
        eq = float(rp.get("equity_usd") or (usdt + sol * float(price or 0)))
        start_sol = float(pdata.get("start_sol") or 0)
        start_usdt = float(pdata.get("start_usdt") or 0)
        start_eq = start_usdt + start_sol * float(pdata.get("start_price") or price or 0)
        bh = float(rp.get("bh_equity") or (start_usdt + start_sol * float(price or 0)))
        ports[rname] = {
            "sol": sol, "usdt": usdt, "equity_usd": eq,
            "pnl_vs_start": eq - start_eq, "pnl_vs_bh": eq - bh,
            "sol_exposure_pct": (100.0 * sol * float(price or 0) / eq) if eq and price else 0.0,
            "trades": rp.get("trades") if rp.get("trades") is not None else pdata.get("trade_count"),
            "last_final": rp.get("last_signal"), "last_chosen": rp.get("last_signal"),
            "last_conf": 1.0, "gate_reasons": rp.get("gate_reasons"),
            "model": "rule", "strategy": rp.get("strategy"),
            "started_brt": pdata.get("started_brt"),
            "indicators": rp.get("indicators"), "position": rp.get("position"),
        }
    # hybrid from sol status if present
    if "hybrid_von_relaxed_cap2" in status_j and "hybrid_von_relaxed_cap2" not in ports:
        st = status_j["hybrid_von_relaxed_cap2"] or {}
        pdata = read_json(ROOT / "data" / "portfolio_hybrid_von_relaxed_cap2.json") or {}
        sol = float(st.get("sol") if st.get("sol") is not None else pdata.get("sol") or 0)
        usdt = float(st.get("usdt") if st.get("usdt") is not None else pdata.get("usdt") or 0)
        eq = float(st.get("equity_usd") or (usdt + sol * float(price or 0)))
        start_eq = float(pdata.get("start_usdt") or 0) + float(pdata.get("start_sol") or 0) * float(pdata.get("start_price") or price or 0)
        bh = float(pdata.get("start_usdt") or 0) + float(pdata.get("start_sol") or 0) * float(price or 0)
        ports["hybrid_von_relaxed_cap2"] = {
            "sol": sol, "usdt": usdt, "equity_usd": eq,
            "pnl_vs_start": eq - start_eq, "pnl_vs_bh": eq - bh,
            "sol_exposure_pct": (100.0 * sol * float(price or 0) / eq) if eq and price else 0.0,
            "trades": st.get("trades"), "last_final": st.get("last_final"),
            "last_chosen": st.get("last_chosen"), "last_conf": st.get("last_conf"),
            "gate_reasons": st.get("gate_reasons"), "model": st.get("model"),
            "strategy": st.get("strategy"), "started_brt": st.get("started_brt") or pdata.get("started_brt"),
            "sol_regime_bull": st.get("sol_regime_bull"),
        }

    return {
        "price_usd": price,
        "price_source": status_j.get("price_source"),
        "portfolios": ports,
        "jev": status_j.get("jev"),
        "models": status_j.get("models"),
        "review_done": status_j.get("review_done"),
        "extra_latencies_ms": status_j.get("extra_latencies_ms"),
        "cycle_wall_ms": status_j.get("cycle_wall_ms"),
        "cycles": status_j.get("cycles"),
        "errors": status_j.get("errors"),
    }


@app.get("/api/equity")
def api_equity(_: str = Depends(require_auth)):
    out = {}
    for name in portfolio_names():
        if name.startswith("meme_"):
            continue
        rows = read_jsonl(ROOT / "data" / f"equity_{name}.jsonl")
        # downsample to ~400 points
        if len(rows) > 400:
            step = len(rows) // 400
            rows = rows[::step]
        out[name] = [
            {
                "ts": r.get("ts"), "ts_brt": brt_iso(r["ts"]) if r.get("ts") else None,
                "equity": r.get("equity"), "bh_equity": r.get("bh_equity"),
                "all_usdt_equity": r.get("all_usdt_equity"), "price": r.get("price"),
            }
            for r in rows
        ]
    return out


@app.get("/api/decisions")
def api_decisions(limit: int = 50, _: str = Depends(require_auth)):
    rows = read_jsonl(ROOT / "logs" / "decisions.jsonl", limit=max(1, min(limit, 200)))
    # return newest last already; reverse for newest-first UI
    rows = list(reversed(rows))
    return [
        {
            "ts_brt": r.get("ts_brt"), "portfolio": r.get("portfolio"), "model": r.get("model"),
            "state": r.get("state"), "chosen_action": r.get("chosen_action"),
            "confidence": r.get("confidence"), "skip_noul": r.get("skip_noul"),
            "final_action": r.get("final_action"), "gate_reasons": r.get("gate_reasons"),
        }
        for r in rows
    ]


@app.get("/api/trades")
def api_trades(limit: int = 50, _: str = Depends(require_auth)):
    rows = read_jsonl(ROOT / "logs" / "trades.jsonl", limit=max(1, min(limit, 200)))
    rows = list(reversed(rows))
    out = []
    for r in rows:
        fill = r.get("fill") or {}
        out.append({
            "ts_brt": r.get("ts_brt"), "portfolio": r.get("portfolio"),
            "side": r.get("side"), "price_mark": r.get("price_mark"),
            "fill_mode": fill.get("fill_mode") or (r.get("quote") or {}).get("fill_mode"),
            "fill": fill, "paper_only": r.get("paper_only", True),
        })
    return out


@app.get("/api/memes")
def api_memes(_: str = Depends(require_auth)):
    memecoins = read_json(ROOT / "memecoins.json", {}) or {}
    st = read_json(ROOT / "data" / "meme" / "status.json", {}) or {}
    toks = st.get("tokens") or {}
    rows = []
    for t in memecoins.get("tokens") or []:
        sym = t["symbol"]
        v = toks.get(sym) or {}
        b = v.get("baseline") or {}
        r = v.get("relaxed") or {}
        models = v.get("models") or {}
        # flatten for UI: von + each extra model
        model_cols = {
            "von": {
                "baseline_equity": b.get("equity_usd"), "baseline_trades": b.get("trades"),
                "relaxed_equity": r.get("equity_usd"), "relaxed_trades": r.get("trades"),
                "bh_equity": b.get("bh_equity") or r.get("bh_equity"),
            }
        }
        for mid, md in models.items():
            bb = md.get("baseline") or {}; rr = md.get("relaxed") or {}
            model_cols[mid] = {
                "baseline_equity": bb.get("equity_usd"), "baseline_trades": bb.get("trades"),
                "relaxed_equity": rr.get("equity_usd"), "relaxed_trades": rr.get("trades"),
                "bh_equity": bb.get("bh_equity") or rr.get("bh_equity"),
                "started_brt": bb.get("started_brt") or rr.get("started_brt"),
            }
        rows.append({
            "symbol": sym, "mint": t.get("mint"),
            "price": v.get("price"), "price_source": v.get("price_source"),
            "baseline_equity": b.get("equity_usd"), "baseline_trades": b.get("trades"),
            "relaxed_equity": r.get("equity_usd"), "relaxed_trades": r.get("trades"),
            "bh_equity": b.get("bh_equity") or r.get("bh_equity"),
            "models": model_cols,
        })
    return {
        "tokens": rows,
        "restart_brt": st.get("restart_brt"),
        "price_policy": st.get("price_policy"),
        "meme_models_enabled": st.get("meme_models_enabled"),
        "last_models": st.get("last_models"),
        "cycle_wall_ms": st.get("cycle_wall_ms"),
        "extra_latencies_ms": st.get("extra_latencies_ms"),
    }


@app.get("/api/reviews")
def api_reviews(_: str = Depends(require_auth)):
    files = sorted((ROOT / "reviews").glob("*.md"))
    return {
        "review_done": (read_json(ROOT / "status.json", {}) or {}).get("review_done"),
        "files": [f.name for f in files],
        "criteria": ["criteria_baseline.json", "criteria_v2.json"],
    }


@app.get("/api/file")
def api_file(path: str, _: str = Depends(require_auth)):
    target = safe_paper_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "not found")
    if target.suffix.lower() not in (".md", ".json", ".txt", ".jsonl"):
        raise HTTPException(403, "file type not allowed")
    # limit size
    if target.stat().st_size > 2_000_000:
        raise HTTPException(413, "too large")
    return PlainTextResponse(target.read_text(errors="replace"))


@app.get("/api/params")
def api_params(_: str = Depends(require_auth)):
    import importlib.util
    spec = importlib.util.spec_from_file_location("defaults", DASH_CODE / "defaults.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    df, ED = mod.default_for, mod.EDITABLE
    overlay = load_overlay()
    out = {"bots": overlay.get("bots") or {}, "portfolios": {}, "editable": list(ED)}
    for name in portfolio_names():
        d = df(name)
        ov = (overlay.get("portfolios") or {}).get(name) or {}
        merged = dict(d)
        try:  # valores efetivos (params.json + overlay) quando o nome é um portfólio real
            eff, _prov, errs = mod.effective_for(name)
            if not eff.get("failsafe"):
                merged.update({k: (eff.get("gates") or {}).get(k) for k in ED})
            merged["params_errors"] = errs
        except Exception:
            for k in ED:
                if k in ov and ov[k] is not None:
                    merged[k] = ov[k]
        merged["paused"] = bool(ov.get("paused"))
        merged["is_baseline_control"] = name == "baseline" or name.endswith("_baseline") or name == "meme_baseline"
        out["portfolios"][name] = merged
    models = read_json(ROOT / "models.json", {}) or {}
    out["models"] = {
        mid: {
            "enabled": bool(b.get("enabled")),
            "memes_enabled": bool(b.get("memes_enabled")),
            "label": b.get("label"), "kind": b.get("kind"),
        }
        for mid, b in (models.get("backends") or {}).items()
    }
    out["jev"] = (read_json(ROOT / "status.json", {}) or {}).get("jev")
    return out


@app.post("/api/params/{portfolio}")
async def api_set_params(portfolio: str, request: Request, _: str = Depends(require_auth)):
    import importlib.util
    spec = importlib.util.spec_from_file_location("defaults", DASH_CODE / "defaults.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    default_for, validate_patch, EDITABLE = mod.default_for, mod.validate_patch, mod.EDITABLE
    if portfolio not in portfolio_names():
        raise HTTPException(404, "unknown portfolio")
    body = await request.json()
    overlay = load_overlay()
    ports = overlay.setdefault("portfolios", {})
    cur = ports.setdefault(portfolio, {})
    changes = []
    if "paused" in body:
        old = bool(cur.get("paused"))
        new = bool(body["paused"])
        if old != new:
            cur["paused"] = new
            changes.append(log_param_change(portfolio, "paused", old, new))
    pending = []
    for field in EDITABLE:
        if field not in body:
            continue
        ok, msg, val = validate_patch(field, body[field])
        if not ok:
            raise HTTPException(400, f"{field}: {msg}")
        old = cur.get(field, default_for(portfolio).get(field))
        if old != val:
            cur[field] = val
            pending.append((field, old, val))
    # Limites de segurança e coerência: o resolver valida o portfólio inteiro com o overlay novo antes de gravar.
    if pending and P.classify(portfolio) is not None:
        errs = P.check_overlay_patch(portfolio, overlay)
        if errs:
            raise HTTPException(400, "params inválidos: " + "; ".join(errs[:5]))
    for field, old, val in pending:
        changes.append(log_param_change(portfolio, field, old, val))
    save_overlay(overlay)
    return {"ok": True, "portfolio": portfolio, "changes": changes,
            "warning": "Baseline é o controle fiel ao artigo — altere com cuidado." if (portfolio == "baseline" or portfolio.endswith("_baseline")) else None}


@app.post("/api/params/{portfolio}/restore")
def api_restore(portfolio: str, _: str = Depends(require_auth)):
    import importlib.util
    spec = importlib.util.spec_from_file_location("defaults", DASH_CODE / "defaults.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    default_for, EDITABLE = mod.default_for, mod.EDITABLE
    if portfolio not in portfolio_names():
        raise HTTPException(404, "unknown portfolio")
    overlay = load_overlay()
    ports = overlay.setdefault("portfolios", {})
    old = dict(ports.get(portfolio) or {})
    defaults = default_for(portfolio)
    # Restaurar = apagar os overrides em tempo real: volta a valer params.json (tipo/perfil/portfólio).
    ports[portfolio] = {"paused": False}
    for field in list(EDITABLE) + ["paused"]:
        if field in old:
            log_param_change(portfolio, field, old.get(field), defaults.get(field) if field != "paused" else False, who="restore")
    save_overlay(overlay)
    return {"ok": True, "portfolio": portfolio, "params": {"paused": False, **defaults}}


# ---- params.json por tipo de teste (leitura com proveniência; edição validada) ----
@app.get("/api/params/effective/{portfolio}")
def api_params_effective(portfolio: str, static: bool = False, _: str = Depends(require_auth)):
    """Parâmetros efetivos de um portfólio, com a camada de cada valor e os erros de validação."""
    eff, prov, errs, meta = P.explain(portfolio, use_overlay=not static)
    if meta.get("test_type") is None and errs and "desconhecido" in errs[0]:
        raise HTTPException(404, "unknown portfolio")
    return {"portfolio": portfolio, "meta": meta, "effective": eff, "provenance": prov, "errors": errs,
            "summary": P.summary(eff), "params_path": str(P.params_path()), "static": static}


@app.get("/api/params/types")
def api_params_types(_: str = Depends(require_auth)):
    """Vista por tipo de teste (sem camada de portfólio) + documento bruto."""
    doc = P.STORE.doc() or {}
    out = {}
    for t in sorted(doc.get("types") or {}):
        eff, prov, errs = P.type_view(t, doc=doc)
        out[t] = {"effective": eff, "provenance": prov, "errors": errs, "summary": P.summary(eff),
                  "layer": (doc.get("types") or {}).get(t)}
    return {"params_path": str(P.params_path()), "doc_errors": P.STORE.doc_errors, "types": out,
            "profiles": doc.get("profiles"), "defaults": doc.get("defaults")}


@app.get("/api/params/doc")
def api_params_doc(_: str = Depends(require_auth)):
    return {"params_path": str(P.params_path()), "doc": P.STORE.doc(), "doc_errors": P.STORE.doc_errors}


@app.post("/api/params/layer/{section}/{key}")
async def api_params_layer(section: str, key: str, request: Request, _: str = Depends(require_auth)):
    """Edita uma camada de params.json (types/profiles/models/assets/portfolios). Corpo: {"set": {grupo: {...}},
    "unset": ["grupo.chave"]} ou só o objeto de set. Recusa (400) se algum portfólio ficar inválido."""
    body = await request.json()
    try:
        res = P.write_layer(section, key, body, who="dashboard")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, **res}


@app.post("/api/bots/{bot}/pause")
async def api_bot_pause(bot: str, request: Request, _: str = Depends(require_auth)):
    if bot not in ("sol", "meme", "rules", "lab"):
        raise HTTPException(404, "bot must be sol|meme|rules|lab")
    body = await request.json()
    paused = bool(body.get("paused"))
    overlay = load_overlay()
    bots = overlay.setdefault("bots", {})
    key = f"{bot}_paused"
    old = bool(bots.get(key))
    bots[key] = paused
    save_overlay(overlay)
    log_param_change(f"bot:{bot}", "paused", old, paused)
    return {"ok": True, "bot": bot, "paused": paused}


@app.post("/api/models/{model_id}/enable")
async def api_model_enable(model_id: str, request: Request, _: str = Depends(require_auth)):
    models_path = ROOT / "models.json"
    models = read_json(models_path, {}) or {}
    backends = models.setdefault("backends", {})
    if model_id not in backends:
        raise HTTPException(404, "unknown model")
    body = await request.json()
    note = None
    if "enabled" in body:
        enabled = bool(body.get("enabled"))
        old = bool(backends[model_id].get("enabled"))
        backends[model_id]["enabled"] = enabled
        log_param_change(f"model:{model_id}", "enabled", old, enabled)
        if model_id == "jev" and enabled:
            note = "Jev habilitado no models.json; se JEV_API_KEY ausente no supervisor, status=aguardando chave. Reinicie via stop/start apos exportar a chave."
    if "memes_enabled" in body:
        me = bool(body.get("memes_enabled"))
        old_m = bool(backends[model_id].get("memes_enabled"))
        backends[model_id]["memes_enabled"] = me
        log_param_change(f"model:{model_id}", "memes_enabled", old_m, me)
        if model_id == "von" and not me:
            note = (note or "") + " von meme e o padrao; desabilitar memes_enabled so afeta novos ciclos extras (von continua via codigo)."
            backends[model_id]["memes_enabled"] = True  # von meme always on
            note = "von memes_enabled permanece True (portfolios von de meme nao sao desligados)."
    models_path.write_text(json.dumps(models, indent=2) + "\n")
    return {
        "ok": True, "model": model_id,
        "enabled": bool(backends[model_id].get("enabled")),
        "memes_enabled": bool(backends[model_id].get("memes_enabled")),
        "note": note,
    }


@app.get("/api/rules")
def api_rules(_: str = Depends(require_auth)):
    return read_json(ROOT / "data" / "rules" / "status.json", {}) or {}

def _last_mark(asset: str):
    p = ROOT / "data" / "prices.jsonl" if asset == "SOL" else ROOT / "data" / "meme" / "prices" / f"{asset}.jsonl"
    try:
        with open(p, "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 4096))
            return float(json.loads([l for l in f.read().split(b"\n") if l.strip()][-1])["price_usd"])
    except Exception:
        return None


def _port_summary(name: str, file: Path, asset: str):
    d = read_json(file, {}) or {}
    if not d:
        return {"name": name}
    px = _last_mark(asset)
    q = float(d.get("sol") or 0) if d.get("asset_mode", "sol") == "sol" else float(d.get("token") or 0)
    eq = float(d.get("usdt") or 0) + q * (px or 0)
    start = float((d.get("benchmark_all_usdt") or {}).get("usdt") or 0)
    bh = d.get("benchmark_buy_hold") or {}
    bh_eq = float(bh.get("usdt") or 0) + float(bh.get("sol" if d.get("asset_mode", "sol") == "sol" else "token") or 0) * (px or 0)
    return {"name": name, "asset": asset, "equity_usd": eq, "start_value": start, "pnl": eq - start, "vs_bh": eq - bh_eq,
            "trades": d.get("trade_count", 0), "started_brt": d.get("started_brt"), "open_order": bool(d.get("open_order")),
            "exposure_pct": (q * (px or 0) / eq * 100) if eq else None}


def _lab_params(name, e):
    """Parâmetros efetivos (sem campos internos) para a vista do lab; forks mostram também o diff."""
    try:
        eff = P.explain(name, meta=e)[0]
        return {k: eff.get(k) for k in ("gates", "exec", "exits", "hours", "ensemble", "regime_filter")}
    except Exception:
        return e.get("params")


@app.get("/api/lab")
def api_lab(_: str = Depends(require_auth)):
    import sys as _s
    if str(LAB_DIR) not in _s.path:
        _s.path.insert(0, str(LAB_DIR))
    from bot import lab_registry as R
    reg = read_json(ROOT / "data" / "lab" / "registry.json", {}) or {}
    st = read_json(ROOT / "data" / "lab" / "status.json", {}) or {}
    ver = (read_json(ROOT / "data" / "nightly" / "verdicts.json", {}) or {})
    verdicts = ver.get("verdicts") or {}
    overlay = load_overlay()
    paused = {n: bool(((overlay.get("portfolios") or {}).get(n) or {}).get("paused")) for n in (reg.get("portfolios") or {})}
    orig = R.originals()
    hyps = []
    for n, e in (reg.get("portfolios") or {}).items():
        s = _port_summary(n, R.port_path(n), e["asset"])
        s.update({"label": e.get("label"), "hyp": e.get("hyp"), "kind": e.get("kind"), "status": e.get("status"),
                  "parent": e.get("parent"), "lineage": e.get("lineage"), "params": _lab_params(n, e),
                  "test_type": e.get("test_type"),
                  "params_diff": e.get("params_diff"), "created_brt": e.get("created_brt"), "paused": paused.get(n, False),
                  "verdict": (verdicts.get(n) or {}).get("verdict", "inconclusivo"),
                  "progress": ((verdicts.get(n) or {}).get("progress") or {}).get("text")})
        hyps.append(s)
    lineages = []
    for lin, d in (reg.get("lineages") or {}).items():
        members = []
        for m in d.get("members") or [lin]:
            if m in (reg.get("portfolios") or {}):
                e = reg["portfolios"][m]; s = _port_summary(m, R.port_path(m), e["asset"]); s["status"] = e.get("status")
            elif m in orig:
                s = _port_summary(m, Path(orig[m]["file"]), orig[m]["asset"]); s["status"] = "active (original, nunca alterado)"
            else:
                continue
            s["verdict"] = (verdicts.get(m) or {}).get("verdict", "inconclusivo")
            s["progress"] = ((verdicts.get(m) or {}).get("progress") or {}).get("text")
            s["is_lead"] = d.get("lead") == m
            members.append(s)
        lineages.append({"lineage": lin, "lead": d.get("lead"), "members": members})
    orig_verdicts = [{"name": n, "verdict": v.get("verdict"), "progress": (v.get("progress") or {}).get("text"), "reason": v.get("reason")}
                     for n, v in verdicts.items() if n in orig]
    return {"status": st, "hypotheses": hyps, "lineages": lineages, "verdicts_ts_brt": ver.get("ts_brt"),
            "original_verdicts": orig_verdicts, "nightly": read_json(ROOT / "data" / "nightly" / "status.json", {}) or {},
            "lab_paused": bool((overlay.get("bots") or {}).get("lab_paused")),
            "verdict_rule": "inconclusivo até ≥30 RT fechados e ≥21 dias (≥28 p/ regras 1h e filtros de regime); lead fork = base p/ tuning, não é veredito"}


@app.get("/api/param_changes")
def api_param_changes(limit: int = 100, _: str = Depends(require_auth)):
    rows = read_jsonl(ROOT / "logs" / "param_changes.jsonl", limit=max(1, min(limit, 500)))
    return list(reversed(rows))


# ---- dashboard v2 API (/api/v2/*, SSE at /api/v2/stream) ----
try:
    import sys as _sys
    if str(DASH_CODE) not in _sys.path:
        _sys.path.insert(0, str(DASH_CODE))
    from api_v2 import make_router as _make_v2_router
    app.include_router(_make_v2_router(require_auth, {
        "portfolio_names": portfolio_names,
        "load_overlay": load_overlay,
        "api_params_raw": lambda: api_params("internal"),
        "api_lab_raw": lambda: api_lab("internal"),
    }))
except Exception as _e:  # never take the legacy dashboard down because of v2
    print("api_v2 not loaded:", repr(_e), flush=True)


def main():
    port = int(os.environ.get("DASHBOARD_PORT", "8787"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
