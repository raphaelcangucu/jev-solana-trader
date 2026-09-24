# Article pattern comparison — von / Laya / poorjev

**Date:** 2026-09-23 23:11 -03 (America/Sao_Paulo)  
**Goal:** Rank local System One alternatives by proximity to the alexsssaint / TypeSafe Jev trading loop pattern  
**Workdir:** `/workspace/jev-alts/article-compare/`  
**Hot wallet / swaps:** untouched (paused)

## Article recovered

| Field | Value |
| --- | --- |
| Title (tweet) | “save it > run it tonight” |
| Task alias | “how to build a self-rewriting solana trading system on a $8 VPS” |
| Author | alex saint (@alexsssaint) |
| Original | https://x.com/alexsssaint/status/2102420062023946602 |
| Mirror used | https://github.com/juliuss1907/knowledge-base/blob/1c0881d7a02fd310da4a7c4655996797cab2cc2e/raw/posts/2026-09-23_alex-saint-ai-trading-bot-jev-solana.md |
| Citations saved | `article-compare/article_citations.md` |

### Pattern checklist (from article)

- Decision every **~15 s**; hosted Jev answer ~**0.3 s**
- State = **~12 adjective words**, arithmetic stays in code (no raw decimals)
- `POST /v1/systemone` with Choice `buy|sell|hold` + Noul `skip_this_cycle`
- **High confidence → act; low confidence → hold**; night rewrite audits cases with conf **> 0.8** that went wrong
- Append-only JSONL decision log
- Fail-closed: no answer → hold

### Canonical article example (same state as smoke)

```json
{"action":{"choice":"hold","probabilities":{"buy":0.11,"sell":0.08,"hold":0.81},"confidence":0.81},"skip_this_cycle":{"noul":0.22}}
```

Article criteria used verbatim in this harness (not the longer smoke criteria):

- buy: “the move is strong and depth is not thin”
- sell: “the move is fading or fees are climbing”
- hold: “anything else”
- skip noul: “conditions are too hostile to trade at all”

---

## Ranked recommendation

| Rank | Model | Total /10 | Wire `/v1/systemone` | Warm latency | Sharpness | Behavior sanity | Article-example L1 |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | **von** | **6.82** | Yes | 387.3 ms | 2.97 | 6.15 | 2.0209 |
| 2 | **laya** | **6.73** | Yes | 238.3 ms | 2.49 | 6.15 | 2.321 |
| 3 | **poorjev** | **6.27** | No (adapted) | 144.7 ms | 8.77 | 4.62 | 1.3249 |

### Winner: **von** (`von-sdk` / HF `wfzyx/von`)

**Wire into the Solana bot first.** Closest overall to the article machine:

1. **Native TypeSafe-shaped API** — `von.system_one()` and `von serve` → `POST /v1/systemone` (article curl is drop-in against local server).
2. **Usable calibrated-ish outputs** — full `probabilities` + `confidence` + continuous `noul` skip that actually moves across regimes (Δskip≈0.13).
3. **Directional sanity** — bullish adjective states lean **buy**, bearish lean **sell** (4/4 directed cases).
4. **Latency** — warm mean **~380 ms** on this CPU box; fine vs 15 s loop (article cites ~300 ms hosted).
5. **Deterministic** — all 3× repeats identical (good for threshold tuning / night-log diffs).

**Caveats**

- On the **exact article sample state + article criteria**, von chose **sell** (p≈0.48) with low conf (0.23), not the hosted Jev **hold@0.81 / skip@0.22**. Local weights ≠ hosted Jev; do not expect bit-identical answers.
- Quiet / choppy cases did not prefer hold (often buy/sell with modest peakiness). Treat **confidence gates** (article: act only when high conf; night audits >0.8) as mandatory — raw argmax is not enough.
- Prior smoke with *richer* criteria produced hold@0.84; **criteria text dominates**. Keep article criteria as the live prompt surface the night model rewrites.

### Runner-up: **Laya**

- Also native `Agent.system_one` / `laya-serve` `/v1/systemone`.
- Faster warm (~230 ms); **skip noul spans ~0.00–0.88** — excellent for “hostile → skip” gating.
- Confidence often ~0 / near-uniform action mass (checkpoint calibration warning). Use **skip + peakiness**, not raw confidence, if you pick Laya.
- Quiet states leaned buy; bearish_late_dump misfired to buy.

### Third: **poorjev**

- Fastest (~130 ms) and **sharpest** peaks — looks decisive.
- **Not wire-compatible** (`Client.ask` + `Choice([...])`; criteria had to be prepended into state).
- Skip ≈ **0 always** → veto channel dead; overconfident buys on hostile/late-dump states. OK only as a secondary offline probe after recalibration — **do not** drop in as the article decision layer.

---

## Score breakdown (weights)

| Dimension | Weight | What “good” means |
| --- | ---: | --- |
| Wire/API | 0.20 | Native `/v1/systemone` or equivalent Choice/Noul criteria dict |
| Output shape | 0.15 | Action probs + confidence + continuous skip for thresholds |
| Decision sharpness | 0.20 | Peaked distribution (article thresholds need clear mass) |
| Latency | 0.15 | Comfortable vs ~15 s loop; prefer ~article 300 ms |
| Behavioral sanity | 0.20 | Bullish→buy, bearish→sell, quiet/hostile→hold/skip (assumptions below) |
| Article-example proximity | 0.10 | L1 vs hold@0.81 / skip@0.22 on the sample state |

| Model | Wire | Output | Sharp | Latency | Behavior | Art.prox | **Total** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| von | 10 | 10 | 2.97 | 10 | 6.15 | 0 | **6.82** |
| laya | 10 | 10 | 2.49 | 10 | 6.15 | 0 | **6.73** |
| poorjev | 2 | 9 | 8.77 | 10 | 4.62 | 3.38 | **6.27** |

---

## Behavioral assumptions (documented)

The article only publishes **one** labelled example (sample state → hold). Sanity checks below are **our** regime hypotheses for adjective states crafted in article style:

| Regime | Expectation |
| --- | --- |
| Bullish (`deep quiet pumping calm early green…`) | buy mass > sell |
| Bearish (`thin bot_war fading/dumping violent late red…`) | sell mass > buy |
| Quiet (`deep quiet flat calm…`) | hold wins or hold highest |
| Hostile / high-vol thin | elevated skip **or** hold (not aggressive buy) |
| Article sample | prefer hold (hosted example) |

### Behavior scorecards

**von** — 8/13 pts

- bullish_deep_pump: buy>sell (0.52>0.37) +2
- bullish_early_strength: buy>sell (0.59>0.26) +2
- bearish_fade_botwar: sell>buy (0.56>0.29) +2
- bearish_late_dump: sell>buy (0.57>0.25) +2
- quiet_chop: FAIL not hold (buy)
- deep_calm_flat: FAIL not hold (sell)
- choppy_hostile: FAIL aggressive (sell, skip=0.27)
- high_vol_pump_thin: FAIL aggressive (sell, skip=0.23)
- article_sample: FAIL sell

**laya** — 8/13 pts

- bullish_deep_pump: buy>sell (0.47>0.31) +2
- bullish_early_strength: buy>sell (0.54>0.27) +2
- bearish_fade_botwar: sell>buy (0.84>0.11) +2
- bearish_late_dump: FAIL sell<=buy (0.39<=0.44)
- quiet_chop: FAIL not hold (buy)
- deep_calm_flat: FAIL not hold (buy)
- choppy_hostile: skip/hold ok (skip=0.55, act=buy) +1
- high_vol_pump_thin: skip/hold ok (skip=0.77, act=sell) +1
- article_sample: FAIL sell

**poorjev** — 6/13 pts

- bullish_deep_pump: buy>sell (0.93>0.01) +2
- bullish_early_strength: buy>sell (0.54>0.00) +2
- bearish_fade_botwar: sell>buy (0.98>0.02) +2
- bearish_late_dump: FAIL sell<=buy (0.01<=0.96)
- quiet_chop: FAIL not hold (buy)
- deep_calm_flat: FAIL not hold (buy)
- choppy_hostile: FAIL aggressive (buy, skip=0.00)
- high_vol_pump_thin: FAIL aggressive (buy, skip=0.00)
- article_sample: FAIL buy

---

## Per-case evidence table (mean of 3 deterministic reps)

### Actions / confidence / skip

| Case | Regime | von | laya | poorjev |
| --- | --- | --- | --- | --- |
| `article_sample` | article_example | sell c=0.23 sk=0.14 | sell c=0.01 sk=0.67 | buy c=0.52 sk=0.00 |
| `bullish_deep_pump` | bullish | buy c=0.27 sk=0.17 | buy c=0.05 sk=0.67 | buy c=0.93 sk=0.00 |
| `bullish_early_strength` | bullish | buy c=0.38 sk=0.19 | buy c=0.09 sk=0.00 | buy c=0.54 sk=0.00 |
| `bearish_fade_botwar` | bearish | sell c=0.35 sk=0.21 | sell c=0.50 sk=0.66 | sell c=0.98 sk=0.00 |
| `bearish_late_dump` | bearish | sell c=0.36 sk=0.22 | buy c=0.06 sk=0.88 | buy c=0.96 sk=0.00 |
| `choppy_hostile` | choppy_hostile | sell c=0.33 sk=0.27 | buy c=0.02 sk=0.55 | buy c=0.62 sk=0.00 |
| `quiet_chop` | quiet | buy c=0.20 sk=0.19 | buy c=0.02 sk=0.08 | buy c=0.52 sk=0.00 |
| `high_vol_pump_thin` | high_vol | sell c=0.35 sk=0.23 | sell c=0.01 sk=0.77 | buy c=0.79 sk=0.00 |
| `deep_calm_flat` | quiet | sell c=0.21 sk=0.17 | buy c=0.03 sk=0.06 | buy c=0.95 sk=0.00 |

### Probability mass (buy / sell / hold)

| Case | von | laya | poorjev |
| --- | --- | --- | --- |
| `article_sample` | b=0.38 s=0.48 h=0.13 | b=0.34 s=0.38 h=0.28 | b=0.52 s=0.00 h=0.48 |
| `bullish_deep_pump` | b=0.52 s=0.37 h=0.12 | b=0.47 s=0.31 h=0.21 | b=0.93 s=0.01 h=0.07 |
| `bullish_early_strength` | b=0.59 s=0.26 h=0.15 | b=0.54 s=0.27 h=0.19 | b=0.54 s=0.00 h=0.46 |
| `bearish_fade_botwar` | b=0.29 s=0.56 h=0.15 | b=0.11 s=0.84 h=0.06 | b=0.02 s=0.98 h=0.00 |
| `bearish_late_dump` | b=0.25 s=0.57 h=0.17 | b=0.44 s=0.39 h=0.17 | b=0.96 s=0.01 h=0.03 |
| `choppy_hostile` | b=0.28 s=0.56 h=0.17 | b=0.42 s=0.33 h=0.25 | b=0.62 s=0.00 h=0.38 |
| `quiet_chop` | b=0.47 s=0.40 h=0.14 | b=0.41 s=0.35 h=0.24 | b=0.52 s=0.00 h=0.48 |
| `high_vol_pump_thin` | b=0.31 s=0.57 h=0.12 | b=0.34 s=0.38 h=0.28 | b=0.79 s=0.00 h=0.20 |
| `deep_calm_flat` | b=0.41 s=0.47 h=0.11 | b=0.45 s=0.31 h=0.24 | b=0.95 s=0.01 h=0.04 |

### Latency & determinism

| Model | Cold/load (1st) | Warm mean | Warm p95 | Errors | 3× variance |
| --- | ---: | ---: | ---: | ---: | --- |
| von | 5918 ms | 387.3 ms | 505.0 ms | 0 | none (deterministic) |
| laya | 5580 ms | 238.3 ms | 287.4 ms | 0 | none (deterministic) |
| poorjev | 7095 ms | 144.7 ms | 178.9 ms | 0 | none (deterministic) |

All three models returned **identical** answers across 3 repeats per case on CPU (temperature/noise not exposed or effectively greedy).

---

## API path notes

| Model | In-process | HTTP | Criteria fidelity |
| --- | --- | --- | --- |
| von | `von.system_one(state, {Choice, Noul})` | `von serve` → `POST /v1/systemone` | Full criteria dict (article-identical) |
| laya | `Agent(...).system_one(state, questions_dict)` | `laya-serve` → `/v1/systemone` | Full criteria dict |
| poorjev | `Client().ask(state, {Choice([..]), Noul(stmt)})` | none in package | Criteria **prepended into state string**; Choice is option list only |

---

## Suggested bot policy if wiring von

```text
answers = von.system_one(adjective_state, article_questions)
action, conf = answers["action"].choice, answers["action"].confidence
skip = answers["skip_this_cycle"].noul

if skip >= 0.55:          # hostile veto (tune on your log)
    log(hold/skip); return
if conf < 0.55:          # article: low conf → hold; night audits >0.8 mistakes
    log(hold); return
else:
    execute(action) with size ~ conf
```

Append-only log fields (article §5): `t, state, action, conf, skip, px_in, px_15m`.

---

## Artifacts

| Path | Contents |
| --- | --- |
| `article-compare/article_citations.md` | Snippets + thresholds from article |
| `article-compare/cases.json` | 9 adjective states + article questions |
| `article-compare/runners/run_{von,laya,poorjev}.py` | Per-venv harness |
| `article-compare/raw/*_runs.json` | Full raw probs / latency / errors |
| `article-compare/raw/*_runs.log` | Console logs |
| `article-compare/raw/scores.json` | Numeric scorecard |
| `ARTICLE_COMPARE.md` | This report |

Candidates evaluated: only **von, laya, poorjev** (already installed under `venvs/`). No other `/workspace/jev-alts` installs were present.

## One-line summary

**Rank:** von (6.82) > laya (6.73) > poorjev (6.27). **Wire von** into the bot for article-shaped `/v1/systemone` + directional sanity; keep **confidence/skip thresholds**; do not expect hosted-Jev identical hold@0.81 on the sample state.
