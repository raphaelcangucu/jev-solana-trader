"""Modelos para o backtest: servidores próprios, cache em disco das respostas e Jev hospedado com teto de chamadas.

- Servidores locais (von, Laya, poorjev) arrancados com os MESMOS comandos de scripts/start_{von,laya,poorjev}.sh, mas
  nas portas 8865/8866/8867 e com logs/pids próprios — nunca se chama as portas do run ao vivo (8765–8767).
- Cache sqlite: chave = sha256(modelo | sha dos critérios | estado). Só respostas válidas (não fail-closed) entram.
  Os modelos são determinísticos (README do lab), por isso uma chamada por par (critérios, estado) chega.
- Jev hospedado (api.typesafe.ai) via bot.backends.call_hosted_jev; a chave vem de ~/.config/jev/secrets.env para o
  ambiente do processo e nunca é impressa nem gravada. Teto de chamadas (`jev_max_calls`); acima dele → fail-closed
  (hold) e a cobertura fica no relatório.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bot import backends as BK

PORTS = {"von": 8865, "laya": 8866, "poorjev": 8867}
# chamadas concorrentes por modelo: o poorjev corre em MPS (GPU Apple) e chamadas concorrentes no mesmo processo
# abortam o servidor ("A command encoder is already encoding"); ao vivo também é chamado uma vez de cada vez.
WORKERS = {"von": 1, "laya": 1, "poorjev": 1, "jev": 3}
LIVE_PORTS = {8765, 8766, 8767}
LAB = Path(__file__).resolve().parents[1]


def crit_sha(criteria: dict, extra: str = "") -> str:
    """sha256 da parte enviada ao modelo (instructions + criteria + skip) e de um sufixo (ex.: campo model)."""
    part = {"action": {"instructions": criteria["action"]["instructions"], "criteria": criteria["action"]["criteria"]},
            "skip_this_cycle": {"instructions": criteria["skip_this_cycle"]["instructions"]}}
    blob = json.dumps(part, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "|" + extra
    return hashlib.sha256(blob.encode()).hexdigest()


def answer_key(model: str, csha: str, state: str) -> str:
    return hashlib.sha256(f"{model}|{csha}|{state}".encode()).hexdigest()


def load_secrets(path: Path = Path.home() / ".config" / "jev" / "secrets.env") -> list[str]:
    """Carrega KEY=VALUE para os.environ (sem imprimir valores). Devolve só os NOMES carregados."""
    names = []
    if not path.exists():
        return names
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.replace("export ", "").strip()
        v = v.strip().strip('"').strip("'")
        if k and v:
            os.environ[k] = v
            names.append(k)
    return names


# ------------------------------------------------------------------ servidores

def _ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def server_env(jev_alts: Path) -> dict:
    env = dict(os.environ)
    env.update({"VON_DEVICE": "cpu", "HF_HOME": str(jev_alts / "hf-cache"), "TRANSFORMERS_CACHE": str(jev_alts / "hf-cache"),
                "HF_HUB_CACHE": str(jev_alts / "hf-cache" / "hub"), "TOKENIZERS_PARALLELISM": "false",
                "JEV_ALTS_ROOT": str(jev_alts), "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
                "OPENBLAS_NUM_THREADS": "2", "VECLIB_MAXIMUM_THREADS": "2", "NUMEXPR_NUM_THREADS": "2",
                "LAYA_PORT": str(PORTS["laya"]), "POORJEV_PORT": str(PORTS["poorjev"])})
    env.pop("JEV_API_KEY", None)
    return env


def start_servers(run_dir: Path, jev_alts: Path, models=("von", "laya", "poorjev"), logf=None, wait_s: int = 600,
                  background: bool = False) -> dict:
    """Arranca os servidores próprios (nice 10). Devolve {modelo: pid}. Reutiliza um servidor já de pé na porta."""
    run_dir.mkdir(parents=True, exist_ok=True)
    env = server_env(jev_alts)
    pids = {}
    cmds = {
        "von": [str(jev_alts / "venvs/von/bin/von"), "serve", "--host", "127.0.0.1", "--port", str(PORTS["von"]), "--device", "cpu"],
        "laya": [str(jev_alts / "venvs/laya/bin/python"), str(LAB / "bot/serve_laya.py")],
        "poorjev": [str(jev_alts / "venvs/poorjev/bin/python"), str(LAB / "bot/serve_poorjev.py")],
    }
    health = {"von": f"http://127.0.0.1:{PORTS['von']}/openapi.json", "laya": f"http://127.0.0.1:{PORTS['laya']}/health",
              "poorjev": f"http://127.0.0.1:{PORTS['poorjev']}/health"}
    for m in models:
        assert PORTS[m] not in LIVE_PORTS
        if _ready(health[m]):
            pids[m] = None
            continue
        lf = open(run_dir / f"{m}_serve.log", "a")
        # prioridade de fundo (macOS: QoS background → núcleos de eficiência) + nice: o run ao vivo fica com os P-cores
        pre = (["taskpolicy", "-b"] if (background and shutil.which("taskpolicy")) else []) + ["nice", "-n", "15"]
        p = subprocess.Popen(pre + cmds[m], stdout=lf, stderr=subprocess.STDOUT, env=env,
                             cwd=str(LAB), start_new_session=True)
        (run_dir / f"{m}.pid").write_text(str(p.pid))
        pids[m] = p.pid
    t0 = time.time()
    for m in models:
        while not _ready(health[m]):
            if time.time() - t0 > wait_s:
                raise RuntimeError(f"servidor {m} não respondeu em {wait_s}s (ver {run_dir}/{m}_serve.log)")
            time.sleep(2)
    # aquecimento: UMA chamada sequencial por servidor antes de qualquer paralelismo (os shims carregam o modelo na
    # primeira chamada sem trinco; chamadas concorrentes nessa altura carregavam o modelo várias vezes e o poorjev caía)
    q = {"action": {"instructions": "warm up", "criteria": {"buy": "buy", "sell": "sell", "hold": "hold"}},
         "skip_this_cycle": {"instructions": "skip"}}
    for m in models:
        r = BK.call_http_systemone(f"http://127.0.0.1:{PORTS[m]}", "deep quiet flat calm mid gray wide soft mid mid quiet held",
                                   q, 300.0, m)
        if r.get("fail_closed"):
            raise RuntimeError(f"servidor {m} falhou o aquecimento: {r.get('error')}")
    return pids


def stop_servers(run_dir: Path, models=("von", "laya", "poorjev")):
    """Pára SÓ os servidores do backtest (pids gravados em run_dir; grupo de processo próprio)."""
    for m in models:
        pf = run_dir / f"{m}.pid"
        if not pf.exists():
            continue
        try:
            pid = int(pf.read_text())
            cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
            # só mata se o pid ainda for o NOSSO servidor (evita matar um pid reutilizado)
            if ("serve" in cmd) and (str(PORTS[m]) in cmd or f"serve_{m}" in cmd):
                os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            pass
        pf.unlink(missing_ok=True)


# ------------------------------------------------------------------ cache + cliente

class ModelCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS answers (key TEXT PRIMARY KEY, model TEXT, csha TEXT, state TEXT, "
                        "resp TEXT, ts REAL)")
        self.db.commit()
        self.lock = threading.Lock()
        self.mem: dict = {}

    def load(self, model: str, csha: str) -> int:
        n = 0
        for key, state, resp in self.db.execute("SELECT key, state, resp FROM answers WHERE model=? AND csha=?", (model, csha)):
            self.mem[key] = json.loads(resp)
            n += 1
        return n

    def get(self, key: str):
        hit = self.mem.get(key)
        if hit is not None:
            return hit
        row = self.db.execute("SELECT resp FROM answers WHERE key=?", (key,)).fetchone()
        if row:
            self.mem[key] = json.loads(row[0])
            return self.mem[key]
        return None

    def put(self, key: str, model: str, csha: str, state: str, resp: dict):
        with self.lock:
            self.mem[key] = resp
            self.db.execute("INSERT OR REPLACE INTO answers VALUES (?,?,?,?,?,?)",
                            (key, model, csha, state, json.dumps(resp), time.time()))

    def commit(self):
        with self.lock:
            self.db.commit()


def _slim(r: dict) -> dict:
    return {"chosen_action": r.get("chosen_action"), "probabilities": r.get("probabilities") or {},
            "confidence": float(r.get("confidence") or 0.0), "skip_noul": float(r.get("skip_noul") or 0.0)}


FAIL = {"chosen_action": "hold", "probabilities": {"buy": 0.0, "sell": 0.0, "hold": 1.0}, "confidence": 0.0,
        "skip_noul": 1.0, "fail_closed": True, "ok": False}


class ModelClient:
    """Respostas por (modelo, critérios, estado): cache → servidor próprio / Jev hospedado. Contadores por modelo."""

    def __init__(self, cache: ModelCache, jev_cfg: dict | None = None, jev_max_calls: int = 20000, timeout: float = 30.0,
                 workers: int = 4, logf=None):
        self.cache = cache
        self.jev_cfg = jev_cfg or {}
        self.jev_max = int(jev_max_calls)
        self.timeout = timeout
        self.workers = workers
        self.logf = logf
        self.criteria: dict = {}        # cid -> (model_name, criteria dict, csha)
        self.stats: dict = {}
        self.lock = threading.Lock()
        self.jev_budget_hit = False
        self.guard = None          # callable → True se o run ao vivo está saudável (prefetch espera se False)
        self.chunk = 10            # o guarda é consultado a cada `chunk` chamadas por modelo
        self.guard_paused_s = 0.0

    def wait_guard(self, max_wait: float = 1800.0) -> float:
        """Espera (até max_wait s) enquanto o guarda disser que o run ao vivo está lento. Devolve os segundos parados."""
        if self.guard is None:
            return 0.0
        w0 = time.time()
        while not self.guard() and time.time() - w0 < max_wait:
            time.sleep(15)
        dt = time.time() - w0
        with self.lock:
            self.guard_paused_s += dt
        return dt

    def register(self, cid: str, criteria: dict, model_field: str | None = None) -> str:
        csha = crit_sha(criteria, model_field or "")
        self.criteria[cid] = (model_field, criteria, csha)
        return csha

    def _st(self, model):
        return self.stats.setdefault(model, {"calls": 0, "cache_hits": 0, "errors": 0, "fail_closed": 0, "lookups": 0,
                                             "budget_skipped": 0, "confs": []})

    def _call(self, model: str, cid: str, state: str) -> dict | None:
        model_field, crit, csha = self.criteria[cid]
        if model == "jev":
            with self.lock:
                if self._st("jev")["calls"] >= self.jev_max:
                    self.jev_budget_hit = True
                    self._st("jev")["budget_skipped"] += 1
                    return None
                self._st("jev")["calls"] += 1
            r = BK.call_hosted_jev(self.jev_cfg, state, crit, self.timeout)
        else:
            with self.lock:
                self._st(model)["calls"] += 1
            r = BK.call_http_systemone(f"http://127.0.0.1:{PORTS[model]}", state, crit, self.timeout, model,
                                       model_name=model_field)
        if not r or r.get("fail_closed") or not r.get("ok", True) or r.get("chosen_action") not in ("buy", "sell", "hold"):
            with self.lock:
                st = self._st(model)
                st["errors"] += 1
                st["last_error"] = str((r or {}).get("error"))[:120]
                st["consec_errors"] = st.get("consec_errors", 0) + 1
                # disjuntor do Jev: muitos erros sem nenhuma resposta válida, ou 50 seguidos (chave expirada a meio)
                if model == "jev" and ((st["errors"] >= 50 and st.get("ok", 0) == 0) or st["consec_errors"] >= 50):
                    self.jev_budget_hit = True
            return None
        with self.lock:
            self._st(model)["ok"] = self._st(model).get("ok", 0) + 1
            self._st(model)["consec_errors"] = 0
        return _slim(r)

    def get(self, model: str, cid: str, state: str) -> dict:
        """Resposta (cache ou chamada síncrona). Falha → fail-closed (hold)."""
        _mf, _c, csha = self.criteria[cid]
        st = self._st(model)
        st["lookups"] += 1
        key = answer_key(model, csha, state)
        hit = self.cache.get(key)
        if hit is not None:
            st["cache_hits"] += 1
            st["confs"].append(float(hit.get("confidence") or 0.0))
            return dict(hit, fail_closed=False, ok=True)
        if model == "jev" and self.jev_budget_hit:
            st["fail_closed"] += 1
            st["budget_skipped"] += 1
            return dict(FAIL)
        if model != "jev":
            self.wait_guard()      # chamadas síncronas (fora da pré-busca) também respeitam o guarda do run ao vivo
        r = None
        for attempt in range(3):
            r = self._call(model, cid, state)
            if r is not None or (model == "jev" and self.jev_budget_hit):
                break
            time.sleep(1 + attempt)
        if r is None:
            st["fail_closed"] += 1
            return dict(FAIL)
        self.cache.put(key, model, csha, state, r)
        st["confs"].append(float(r.get("confidence") or 0.0))
        return dict(r, fail_closed=False, ok=True)

    def prefetch(self, jobs: list[tuple[str, str, str]], progress_every: int = 500, label: str = "") -> dict:
        """Chama em paralelo (≤ workers por modelo) os pares ainda fora da cache. jobs: (modelo, cid, estado)."""
        todo = []
        seen = set()
        for m, cid, s in jobs:
            key = answer_key(m, self.criteria[cid][2], s)
            if key in seen or self.cache.get(key) is not None:
                continue
            seen.add(key)
            todo.append((m, cid, s, key))
        by_model: dict = {}
        for j in todo:
            by_model.setdefault(j[0], []).append(j)
        done = {"todo": len(todo), "ok": 0, "fail": 0}
        if not todo:
            return done
        t0 = time.time()
        from bot.lib import BRT  # noqa: F401  (garante bot importado)
        from backtest.data import log
        prog = {"n": 0, "paused": 0.0}
        lock = threading.Lock()

        def run_model(m, js):
            # cada modelo no seu ritmo; entre blocos o guarda confirma que o run ao vivo está saudável (senão espera)
            with ThreadPoolExecutor(max_workers=min(self.workers, WORKERS.get(m, 1))) as ex:
                for i in range(0, len(js), self.chunk):
                    if self.guard is not None:
                        dt = self.wait_guard()
                        with lock:
                            prog["paused"] += dt
                    futs = {ex.submit(self._call_retry, mm, cid, s): (mm, cid, s, key) for (mm, cid, s, key) in js[i:i + self.chunk]}
                    for f in as_completed(futs):
                        mm, cid, s, key = futs[f]
                        r = f.result()
                        with lock:
                            prog["n"] += 1
                            n = prog["n"]
                            if r is not None:
                                self.cache.put(key, mm, self.criteria[cid][2], s, r)
                                done["ok"] += 1
                            else:
                                done["fail"] += 1
                        if n % progress_every == 0:
                            self.cache.commit()
                            el = time.time() - t0
                            log(f"prefetch {label}: {n}/{len(todo)} ({el:.0f}s, {n / max(el, 1e-6):.1f}/s)", self.logf)

        ths = [threading.Thread(target=run_model, args=(m, js), daemon=True) for m, js in by_model.items()]
        for th in ths:
            th.start()
        for th in ths:
            th.join()
        paused = prog["paused"]
        done["paused_s"] = round(paused, 1)
        self.cache.commit()
        done["secs"] = round(time.time() - t0, 1)
        return done

    def _call_retry(self, m, cid, s):
        for attempt in range(3):
            r = self._call(m, cid, s)
            if r is not None or (m == "jev" and self.jev_budget_hit):
                return r
            time.sleep(1 + attempt)
        return None


def live_guard(live_root: Path, max_wall_ms: float = 5000.0, max_age_s: float = 60.0, log=None):
    """Guarda do run ao vivo (só leitura de status.json): saudável se o último ciclo do sol_bot é recente (batimento
    ≤ 60 s) e rápido (wall ≤ 5 s). Fora disso a pré-busca (e qualquer chamada síncrona a um servidor local) pára."""
    state = {"last": None}

    def ok():
        try:
            st = json.loads((Path(live_root) / "status.json").read_text())
            age = time.time() - float(st.get("ts") or 0)
            wall = float(st.get("cycle_wall_ms") or 0)
        except Exception:
            return True
        good = age <= max_age_s and wall <= max_wall_ms
        if not good and log and state["last"] != "bad":
            log(f"run ao vivo lento (ciclo {wall:.0f} ms, idade {age:.0f}s): pré-busca em pausa")
        if good and log and state["last"] == "bad":
            log("run ao vivo recuperou: pré-busca retoma")
        state["last"] = "good" if good else "bad"
        return good
    return ok
