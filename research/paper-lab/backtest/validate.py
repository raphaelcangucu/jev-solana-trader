"""Validação do backtest contra o run ao vivo (só leitura dos logs ao vivo, arquivos incluídos via bot/logio).

- `state_agreement`: na parte da janela em que o run ao vivo já corria, compara as palavras de mercado registadas nas
  decisões ao vivo (portfólio dono do estado) com as reconstruídas pelo backtest no mesmo instante.
- `model_agreement`: para estados ao vivo que também estão na cache do backtest, compara ação e confiança (servidor
  próprio do backtest × servidor ao vivo) — confirma o determinismo e a configuração dos modelos.
- `trade_counts`: trades por portfólio no período comum (ao vivo × simulado), só como ordem de grandeza (as posições no
  início do período comum não são iguais).
"""
from __future__ import annotations

import json
from pathlib import Path

from backtest import models as M
from backtest import states as ST

WORDS = ["depth", "fees", "move", "vol", "tod", "color", "rng", "tex", "phase", "mid", "loud"]


def _iter(live_root: Path, rel: str, since: float):
    from bot import logio
    yield from logio.iter_rows(live_root / rel, since_ts=since, root=live_root)


def state_agreement(live_root: Path, data: dict, start: int, end: int, syms: list[str], max_rows: int = 30000) -> dict:
    out = {}
    g, px = data["sol_grid"]
    samp = ST.sol_sampler(g, px)
    specs = [("SOL", "logs/decisions.jsonl", "baseline", samp)]
    for s in syms:
        if s != "SOL":
            specs.append((s, "logs/meme_decisions.jsonl", f"meme_{s}_baseline", ST.minute_sampler(data["minute"][s])))
    rows_by = {}
    for rel in ("logs/decisions.jsonl", "logs/meme_decisions.jsonl"):
        wanted = {p for (_s, r, p, _f) in specs if r == rel}
        for d in _iter(live_root, rel, start):
            if d.get("portfolio") in wanted and d.get("state") and start <= float(d.get("ts") or 0) < end:
                rows_by.setdefault(d["portfolio"], []).append(d)
    for sym, _rel, port, f in specs:
        rows = rows_by.get(port, [])[-max_rows:]
        n = exact = 0
        agree = {w: 0 for w in WORDS if w != "tex"}
        for d in rows:
            pr = f(int(d["ts"]) // 5 * 5 if sym == "SOL" else int(d["ts"]), 80)
            if pr is None or len(pr) < 2:
                continue
            mk = ST.market_words([float(x) for x in pr], d["ts"])
            w = d["state"].split()
            n += 1
            ok = True
            for i, nm in enumerate(WORDS):
                if nm == "tex":
                    continue
                if w[i] == mk[i]:
                    agree[nm] += 1
                else:
                    ok = False
            exact += ok
        out[sym] = {"n": n, "exact_market": round(exact / n, 4) if n else None,
                    **{k: round(v / n, 4) for k, v in agree.items() if k in ("move", "vol", "color", "rng")}} if n else {"n": 0}
    return out


def model_agreement(live_root: Path, client, start: int, end: int, max_rows: int = 20000) -> dict:
    """Ao vivo: von (baseline/critérios baseline) e laya/poorjev (X_baseline) — mesmos critérios do lab_baseline."""
    out = {}
    pairs = {"baseline": "von", "laya_baseline": "laya", "poorjev_baseline": "poorjev", "jev_baseline": "jev"}
    csha = client.criteria["lab_baseline"][2]
    seen = {}
    for d in _iter(live_root, "logs/decisions.jsonl", start):
        m = pairs.get(d.get("portfolio"))
        if not m or d.get("fail_closed") or not d.get("state") or d.get("confidence") is None:
            continue
        if not (start <= float(d.get("ts") or 0) < end):
            continue
        seen.setdefault(m, {})[d["state"]] = d
    for m, by_state in seen.items():
        n = same = close = 0
        for st, d in list(by_state.items())[:max_rows]:
            hit = client.cache.get(M.answer_key(m, csha, st))
            if hit is None:
                continue
            n += 1
            same += hit["chosen_action"] == d.get("chosen_action")
            close += abs(float(hit["confidence"]) - float(d["confidence"])) <= 0.01
        out[m] = {"states_live": len(by_state), "compared": n, "same_action": round(same / n, 4) if n else None,
                  "conf_within_0.01": round(close / n, 4) if n else None}
    return out


def trade_counts(live_root: Path, sim_trades_by: dict, t0: float, t1: float, names: list[str]) -> dict:
    live = {}
    for rel in ("logs/trades.jsonl", "logs/meme_trades.jsonl"):
        p = live_root / rel
        if not p.exists():
            continue
        with open(p) as fh:
            for line in fh:
                try:
                    t = json.loads(line)
                except Exception:
                    continue
                if t0 <= float(t.get("ts") or 0) < t1:
                    live[t.get("portfolio")] = live.get(t.get("portfolio"), 0) + 1
    out = {}
    for n in names:
        sim = sum(1 for t in sim_trades_by.get(n, []) if t0 <= float(t["ts"]) < t1)
        if n in live or sim:
            out[n] = {"live": live.get(n, 0), "sim": sim}
    return out
