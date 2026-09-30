"""DEPRECADO — variante antiga da revisão noturna (usada só pelo ponto de entrada legado bot/main.py).

`run_night_review` agora delega em `bot.sol_bot.night_review`, que usa a auditoria por percentil partilhada
(`bot/confidence_audit.py`). `_propose_criteria`/`_render_markdown` ficam só como referência histórica do
critério antigo (conf > 0,8 e approx_pnl negativo), que nunca disparava com o von.
Não altera os critérios baseline (portão humano).
"""
from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

BRT = timezone(timedelta(hours=-3))


def run_night_review(cfg: dict, day: str | None = None) -> dict[str, Any]:
    """Compatível com o chamador antigo (cfg de bot.paths.load_config, com `_paths`)."""
    from bot.sol_bot import night_review
    paths = cfg["_paths"]
    proposed = night_review(paths["decisions_log"], paths["trades_log"], paths["criteria_baseline"],
                            paths["review_md"], paths["criteria_v2"], day=day, cfg=cfg,
                            prices_log=paths.get("prices_log"))
    au = proposed["audit"]
    return {
        "review_path": str(paths["review_md"]),
        "criteria_v2_path": str(paths["criteria_v2"]),
        "n_decisions": au["n_rows"],
        "n_answered": au["n_answered"],
        "n_confident": au["n_confident"],
        "confident_mistakes": au["n_mistakes"],
        "cutoff": au["cutoff"],
        "proposed_version": proposed.get("version"),
        "changed": proposed.get("changed"),
    }


def _propose_criteria(
    baseline_path: Path,
    decisions: list,
    trades: list,
    mistakes: list,
    gate_reasons: Counter,
) -> dict:
    with open(baseline_path) as f:
        base = json.load(f)

    # Analyze which state adjectives co-occur with losing sells/buys
    lose_words: Counter = Counter()
    win_words: Counter = Counter()
    for m in mistakes:
        st = (m["decision"].get("state") or "").split()
        lose_words.update(st)
    for d in decisions:
        if float(d.get("confidence") or 0) > 0.8 and d.get("final_action") in ("buy", "sell"):
            # crude: if later we had sell with positive approx — skip
            pass

    # Count regimes where gates blocked a lot → tighten skip language
    low_conf_blocks = gate_reasons.get("low_confidence", 0)
    skip_blocks = gate_reasons.get("skip_noul_high", 0)

    buy_extra = []
    sell_extra = []
    hold_extra = []
    skip_extra = []

    if lose_words.get("thin", 0) + lose_words.get("bot_war", 0) >= 1:
        buy_extra.append("and the book is deep not thin")
        skip_extra.append("especially when the book is thin or fees feel hostile")
    if lose_words.get("violent", 0) >= 1 or lose_words.get("whipping", 0) >= 1:
        buy_extra.append("only if the move is calm enough to trust")
        hold_extra.append("when the tape is violent or whipping")
        skip_extra.append("when volatility is violent")
    if lose_words.get("fading", 0) or lose_words.get("dumping", 0):
        sell_extra.append("when pumping has clearly turned to fading or dumping")
    if low_conf_blocks > max(10, len(decisions) // 5):
        hold_extra.append("whenever conviction is soft")
    if skip_blocks > 5:
        skip_extra.append("when conditions look hostile even if a direction tempts")

    # Default enrichments from article pattern + audit (deterministic)
    buy_c = base["action"]["criteria"]["buy"]
    sell_c = base["action"]["criteria"]["sell"]
    hold_c = base["action"]["criteria"]["hold"]
    skip_i = base["skip_this_cycle"]["instructions"]

    if buy_extra:
        buy_c = buy_c + "; " + "; ".join(buy_extra)
    else:
        buy_c = buy_c + "; prefer deep quiet pumping with calm tape"

    if sell_extra:
        sell_c = sell_c + "; " + "; ".join(sell_extra)
    else:
        sell_c = sell_c + "; prefer fading or dumping with harsh or loud tape"

    if hold_extra:
        hold_c = hold_c + "; " + "; ".join(hold_extra)
    else:
        hold_c = hold_c + "; prefer flat gray chop or unclear mixed signals"

    if skip_extra:
        skip_i = skip_i + "; " + "; ".join(skip_extra)
    else:
        skip_i = skip_i + "; prefer thin bot_war violent conditions"

    # Human gate note: baseline unchanged
    return {
        "version": "v2",
        "source": "night_review_rules_based_summarizer",
        "parent": "baseline",
        "generated_at_brt": datetime.now(tz=BRT).isoformat(),
        "method": (
            "Deterministic rules-based rewrite from audit statistics "
            "(confident>0.8 losing trades word frequencies + gate reason counts). "
            "No LLM API. Baseline criteria file left untouched (human gate)."
        ),
        "audit_summary": {
            "n_decisions": len(decisions),
            "n_trades": len(trades),
            "confident_mistakes": len(mistakes),
            "top_lose_words": lose_words.most_common(8),
            "gate_reasons": dict(gate_reasons),
        },
        "action": {
            "instructions": base["action"]["instructions"]
            + "; be stricter after overnight audit of confident mistakes",
            "criteria": {
                "buy": buy_c,
                "sell": sell_c,
                "hold": hold_c,
            },
        },
        "skip_this_cycle": {
            "instructions": skip_i,
        },
    }


def _render_markdown(
    decisions, trades, mistakes, wins, action_dist, final_dist, gate_reasons, blocked, proposed
) -> str:
    now = datetime.now(tz=BRT).isoformat()
    lines = [
        "# Night review — 2026-09-24",
        "",
        f"**Generated (BRT):** {now}",
        f"**Method:** {proposed.get('method')}",
        "",
        "## Human gate",
        "",
        "- Baseline criteria (`criteria_baseline.json`) was **NOT** modified.",
        "- Proposed rewrite written to `criteria_v2.json`.",
        "- Shadow simulator **v2** starts with the same balances and runs in parallel.",
        "",
        "## Audit snapshot",
        "",
        f"- Decisions (baseline+relaxed): **{len(decisions)}**",
        f"- Trades (baseline+relaxed): **{len(trades)}**",
        f"- Blocked trades (gates): **{blocked}**",
        f"- Confident (>0.8) losing trades audited: **{len(mistakes)}**",
        f"- Confident winning sells noted: **{len(wins)}**",
        "",
        "_Note: audit includes relaxed portfolio trades/decisions (baseline alone often has 0 trades under von conf~0.40)._",
        "",
        "### Chosen action distribution",
        "",
    ]
    for k, v in action_dist.most_common():
        lines.append(f"- `{k}`: {v}")
    lines += ["", "### Final action (after gates)", ""]
    for k, v in final_dist.most_common():
        lines.append(f"- `{k}`: {v}")
    lines += ["", "### Gate reasons", ""]
    if gate_reasons:
        for k, v in gate_reasons.most_common():
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- (none yet)")

    lines += ["", "## Confident mistakes (conf > 0.8, negative approx PnL)", ""]
    if not mistakes:
        lines.append("_None yet — rewrite still applies conservative enrichments from gate stats / priors._")
    else:
        for i, m in enumerate(mistakes[:20], 1):
            d = m["decision"]
            lines.append(
                f"{i}. `{d.get('ts_brt')}` action={d.get('final_action')} conf={d.get('confidence')} "
                f"state=`{d.get('state')}` pnl≈{m.get('pnl')}"
            )

    lines += [
        "",
        "## Proposed criteria (v2)",
        "",
        "```json",
        json.dumps(
            {
                "action": proposed["action"],
                "skip_this_cycle": proposed["skip_this_cycle"],
            },
            indent=2,
        ),
        "```",
        "",
        "## Notes",
        "",
        "- This is a **paper** simulation; fills use Jupiter quotes without signing.",
        "- One night of data is a tiny sample; treat v2 as an A/B shadow, not truth.",
        "",
    ]
    return "\n".join(lines)


def _read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows
