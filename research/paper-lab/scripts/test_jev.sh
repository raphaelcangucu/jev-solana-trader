#!/usr/bin/env bash
# One test call to hosted Jev. Never prints the API key.
set -euo pipefail
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # código do lab (research/paper-lab)
ROOT="${PAPER_LAB_ROOT:-$LAB}"                           # dados/estado (logs, data, run, status.json)
JEV_ALTS="${JEV_ALTS_ROOT:-/workspace/jev-alts}"         # venvs + hf-cache dos modelos
export PAPER_LAB_ROOT="$ROOT" JEV_ALTS_ROOT="$JEV_ALTS"
PY=$JEV_ALTS/venvs/von/bin/python
export HF_HOME=$JEV_ALTS/hf-cache
PAPER_LAB_CODE="$LAB" "$PY" - <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["PAPER_LAB_CODE"])
from bot.backends import load_models_cfg, call_hosted_jev, jev_key_status

cfg = load_models_cfg()["backends"]["jev"]
st = jev_key_status()
print(f"jev status={st['status']} enabled={st['enabled']} key_present={st['key_present']} endpoint={st['endpoint']} env={st['api_key_env']}")
if st["status"] == "aguardando chave" or not st["key_present"]:
    print("ok=False error=aguardando chave (set JEV_API_KEY then restart via scripts/restart_models.sh)")
    sys.exit(0)
criteria = json.loads(open(os.path.join(os.environ["PAPER_LAB_ROOT"], "criteria_baseline.json")).read())
dec = call_hosted_jev(cfg, "deep quiet flat calm night green wide soft late mid quiet held", criteria, 30.0)
# scrub any accidental key leakage
err = dec.get("error")
print(f"ok={dec.get('ok')} chosen={dec.get('chosen_action')} conf={dec.get('confidence')} skip={dec.get('skip_noul')} lat_ms={dec.get('latency_ms')} error={err}")
PY
