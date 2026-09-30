#!/usr/bin/env bash
# One test call to hosted Jev. Never prints the API key.
set -euo pipefail
ROOT=/home/box/solana-trader/paper
PY=/workspace/jev-alts/venvs/von/bin/python
export HF_HOME=/workspace/jev-alts/hf-cache
"$PY" - <<'PY'
import json, os, sys
sys.path.insert(0, "/home/box/solana-trader/paper")
from bot.backends import load_models_cfg, call_hosted_jev, jev_key_status

cfg = load_models_cfg()["backends"]["jev"]
st = jev_key_status()
print(f"jev status={st['status']} enabled={st['enabled']} key_present={st['key_present']} endpoint={st['endpoint']} env={st['api_key_env']}")
if st["status"] == "aguardando chave" or not st["key_present"]:
    print("ok=False error=aguardando chave (set JEV_API_KEY then restart via scripts/restart_models.sh)")
    sys.exit(0)
criteria = json.loads(open("/home/box/solana-trader/paper/criteria_baseline.json").read())
dec = call_hosted_jev(cfg, "deep quiet flat calm night green wide soft late mid quiet held", criteria, 30.0)
# scrub any accidental key leakage
err = dec.get("error")
print(f"ok={dec.get('ok')} chosen={dec.get('chosen_action')} conf={dec.get('confidence')} skip={dec.get('skip_noul')} lat_ms={dec.get('latency_ms')} error={err}")
PY
