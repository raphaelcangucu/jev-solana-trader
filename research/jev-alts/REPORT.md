# Open-source TypeSafe Jev alternatives — comparison report

**Date:** 2026-09-23 22:53 -03 (America/Sao_Paulo)  
**Goal:** Local CPU-friendly System One decision layer for a Solana trading loop  
**Workdir:** `/workspace/jev-alts/`  
**Smoke state:** `thin bot_war pumping violent flat green wide calm early mid quiet held`  
**Questions:** `action` Choice(buy/sell/hold) + `skip_this_cycle` Noul  

Hardware for smoke tests: Linux box, **no NVIDIA GPU**, 8 vCPU, ~15 GiB RAM, Python 3.13.

---

## 1. Ranked candidate table (stars + maturity)

Stars/forks/last-push captured from GitHub/PyPI on 2026-09-23. Times below are converted to America/Sao_Paulo (-03).

| Rank | Project | Stars | Forks | Open issues | License | Last push (-03) | PyPI | `/v1/systemone` | CPU / no big GPU? | Notes |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- |
| 1 | **Laya** ([NandhaKishorM/laya](https://github.com/NandhaKishorM/laya), HF `convaiinnovations/laya`) | **20607** | 1759 | 87 | Apache-2.0 | 2026-09-23 15:05 | `laya` 0.3.11 | Yes (`laya-serve` / `Agent.system_one`) | **Yes** (~421M encoder) | Most mature open System One package |
| 2 | **SemIf / OpenJev** ([TheoLeeCJ/SemIf-OpenJev](https://github.com/TheoLeeCJ/SemIf-OpenJev)) | 4105 | 277 | 26 | MIT | 2026-09-23 15:48 | — | Scorer / demo (not drop-in server focus) | Partial (llama.cpp GGUF CPU; primary path 4B GPU/MLX) | Highest-visibility “semantic if” research fork |
| 3 | **NanoJev** ([TianyuCodings/NanoJev](https://github.com/TianyuCodings/NanoJev)) | 2121 | 228 | 7 | MIT | 2026-09-21 06:58 | — | Service exists in repo | Needs Qwen3-0.6B + training stack | Game/ViZDoom replica, not trading-oriented |
| 4 | **LocalJev** ([githubnext/localjev](https://github.com/githubnext/localjev)) | 736 | 47 | 3 | MIT | 2026-09-18 17:19 | — | **Yes** | Needs DiffusionGemma via oMLX / large local LLM | Bun/TS bridge; not CPU-small |
| 5 | **von** ([wfzyx/von](https://github.com/wfzyx/von)) | 588 | 46 | 2 | Apache-2.0 | 2026-09-23 22:45 | `von-sdk` 1.2.1 | **Yes** | **Yes** (~395M ModernBERT) | Sub-15ms GPU claim; strong local drop-in |
| 6 | **simple-jev** ([featherless-ai/simple-jev](https://github.com/featherless-ai/simple-jev)) | 502 | 58 | 5 | Apache-2.0 | 2026-09-23 17:58 | — (git install) | **Yes** (alias of `/v1/classifier`) | Yes with small HF model; big models need GPU | Turn any open model into classifier/jev |
| 7 | **OpenJev (DiffusionGemma)** ([razorback16/openjev](https://github.com/razorback16/openjev)) | 374 | 30 | 3 | Apache-2.0 | 2026-09-22 23:04 | — | **Yes** | **No** (vLLM + ~18GB DiffusionGemma) | Closest wire-compat to hosted Jev |
| 8 | **openjev-sglang** ([ekzhang/openjev-sglang](https://github.com/ekzhang/openjev-sglang)) | 305 | 36 | 3 | — | 2026-09-21 02:01 | — | **Yes** | **No** (SGLang GPU) | Prefill-only open endpoint |
| 9 | **openJev-verdict-2.0** ([Heman10x-NGU/openJev-verdict-2.0](https://github.com/Heman10x-NGU/openJev-verdict-2.0)) | 279 | 41 | 3 | Apache-ish (NOASSERTION) | 2026-09-20 11:54 | — | Engine/API in repo | Likely yes (~151M) | Strong typed-decisions bench claims |
| 10 | **OpenJev (SiliconLab)** ([SiliconLabAI/OpenJev](https://github.com/SiliconLabAI/OpenJev)) | 113 | 27 | 2 | MIT | 2026-09-21 23:50 | — | Via Mapika/decider backend | decider-2b needs ~4GB CUDA | Playground + multiple backends |
| 11 | **OpenDecision** ([deepanwadhwa/OpenDecision](https://github.com/deepanwadhwa/OpenDecision)) | 56 | 3 | 2 | Apache-2.0 | 2026-09-21 10:38 | `OpenDecision` 0.1.1 | **Yes** | Yes (ModernBERT zeroshot) | Docs + tests; Py≥3.13 |
| 12 | **open-alternative-jev** ([ikermoel/open-alternative-jev](https://github.com/ikermoel/open-alternative-jev)) | 51 | — | — | Apache-2.0 | 2026-09-22 02:05 | `open-alternative-jev` | No HTTP drop-in (in-process) | Needs large open LLM / GPU | Strong zero-shot benches on big models |
| 13 | **JevK5** ([allebee/jevk5](https://github.com/allebee/jevk5)) | 46 | 4 | 1 | Apache-2.0 | 2026-09-23 16:06 | — | **Yes** | **No** (Qwen3.5-4B CUDA) | High JevBench open ranking |
| 14 | **OpenJev / OpenJevPro** ([zhangcy122/OpenJev](https://github.com/zhangcy122/OpenJev), [OpenJevPro](https://github.com/zhangcy122/OpenJevPro)) | 25 / 0 | 0 | 0 | PolyForm NC (Pro) | 2026-09-23 22:23 / 2026-09-20 05:01 | `openjevpro` 0.1.0 | Claims TypeSafe-style API | Client wraps LLM backends | **Non-commercial** Pro license |
| 15 | **poorjev** ([rupeshpoojary9/poorjev](https://github.com/rupeshpoojary9/poorjev)) | 7 | 0 | 0 | MIT | 2026-09-21 03:59 | `poorjev` 0.1.0 | No (Python `Client.ask`) | **Yes** (~DeBERTa NLI ~400MB) | Calibrated local “poor man’s Jev” |
| 16 | **decision-jef** ([bet0x/decision-jef](https://github.com/bet0x/decision-jef)) | 1 | — | — | MIT | 2026-09-23 17:58 | `decision-jef` 0.6.0 | Mentions wire compat | Likely yes (~307M) | `Decider.decide()`; HF weights |
| — | **Kev** (PyPI `kev`) | — | — | — | Apache-2.0 | — | unrelated ORM | No | — | **Not a Jev alternative** |
| — | **jeff** (PyPI `jeff`) | — | — | — | MIT | — | license CLI | No | — | **Not a Jev alternative** |
| — | **LocalJev** PyPI | — | — | — | — | — | not on PyPI | — | — | Use GitHub variants |
| — | **NanoJev / open-alternative-jev / simple-jev** PyPI names | — | — | — | — | — | often absent | — | — | Prefer GitHub |

### Maturity lens (beyond stars)

| Tier | Projects | Why |
| --- | --- | --- |
| A — production-shaped local encoders | **Laya**, **von**, OpenDecision, poorjev, decision-jef, verdict-2.0 | Real PyPI/HF weights, Choice/Noul/Score, CPU-feasible |
| B — LLM logit bridges | SemIf, simple-jev, open-alternative-jev, JevK5 | Flexible quality, usually GPU / multi-GB |
| C — heavy drop-in Jev servers | razorback16/openjev, openjev-sglang, githubnext/localjev | Best wire parity; need vLLM/SGLang/oMLX + large models |
| D — demos / wrong names | NanoJev (games), Kev, jeff, OpenJevPro (NC) | Skip for Solana loop |

---

## 2. Top CPU picks selected for smoke tests

Constraint: run on this CPU Linux box **without** vLLM/SGLang/DiffusionGemma.

| Pick | Why selected |
| --- | --- |
| **von** (`von-sdk`) | Native `/v1/systemone` + `von.system_one()` / `von.decide()`, Apache-2.0, ~395M, recent push, mid stars but purpose-built |
| **Laya** (`laya`) | Highest stars/maturity, `Agent.system_one`, CPU path documented, Apache-2.0 |
| **poorjev** (`poorjev[local]`) | Explicit CPU/offline default, MIT, smallest operational footprint |

Not smoke-tested here (GPU/heavy or secondary): SemIf, NanoJev, LocalJev, simple-jev (would need chosen small model), OpenJev/SGLang, JevK5, open-alternative-jev, OpenDecision, decision-jef, OpenJevPro.

---

## 3. Smoke test results

Shared payload in `smoke/payload.json`. Separate venvs under `venvs/{von,laya,poorjev}/`. HF cache: `/workspace/jev-alts/hf-cache` (~4.1 GiB total after three models).

### Summary

| Candidate | Install | Smoke | Cold latency | Warm latency | Sample decision | Model download |
| --- | --- | --- | --- | --- | --- | --- |
| **von** 1.2.1 | **PASS** | **PASS** | 44710 ms (incl. first load) | **377 ms** | action=**hold** (0.84), skip noul=0.36 | `wfzyx/von` (~3.16 GB: model.safetensors + option_marker.pt) |
| **laya** 0.3.11 | **PASS** | **PASS** | load 12173 ms; infer 305 ms | **299 ms** | action=**hold** (0.36, conf 0.001), skip noul=0.59 | `convaiinnovations/laya` (~0.85 GB) |
| **poorjev** 0.1.0 | **PASS** | **PASS** | 13132 ms (first NLI load) | **138 ms** | action=**hold** (0.986), skip=False (p≈0.0004) | DeBERTa zeroshot ~0.38 GB (measured) |

### von — sample JSON

```json
{
  "ok": true,
  "cold_ms": 44710.04,
  "warm_ms": 376.57,
  "answers": {
    "action": {
      "type": "choice",
      "choice": "hold",
      "probabilities": {"buy": 0.0868, "sell": 0.0736, "hold": 0.8396},
      "confidence": 0.759
    },
    "skip_this_cycle": {"type": "noul", "noul": 0.3602}
  },
  "usage": {"input_tokens": 59, "output_tokens": 2},
  "model": "von-1.2.0"
}
```

- Install: `pip install von-sdk` (pulled torch 2.14 + transformers).  
- Force CPU: `VON_DEVICE=cpu`.  
- HTTP: `von` CLI `serve` exposes `POST /v1/systemone`.

### laya — sample JSON

```json
{
  "ok": true,
  "cold_ms": 304.91,
  "warm_ms": 299.30,
  "load_ms": 12173.44,
  "response": {
    "model": "laya-rl-agent",
    "answers": {
      "action": {
        "type": "choice",
        "choice": "hold",
        "probabilities": {"buy": 0.3255, "sell": 0.3165, "hold": 0.3579},
        "confidence": 0.0013
      },
      "skip_this_cycle": {"type": "noul", "noul": 0.5861, "confidence": 0.5861}
    },
    "usage": {"input_tokens": 173, "output_tokens": 0}
  }
}
```

- Install: `pip install laya`.  
- API: `Agent(..., device="cpu").system_one(state, questions)`.  
- Warning on load: invalid temperature calibration → treat confidence as uncalibrated for this checkpoint path.  
- Near-uniform buy/sell/hold suggests the English checkpoint is **uncertain** on terse memecoin jargon (useful abstention signal).

### poorjev — sample JSON

```json
{
  "ok": true,
  "cold_ms": 13132.29,
  "warm_ms": 137.78,
  "answers": {
    "action": {
      "value": "hold",
      "confidence": 0.986,
      "probs": {"buy": 0.0072, "sell": 0.0063, "hold": 0.9865}
    },
    "skip_this_cycle": {"value": false, "prob": 0.00041, "confidence": 0.9996}
  },
  "note": "Choice API takes option list, not criteria dict; no POST /v1/systemone"
}
```

- Install: `pip install "poorjev[local]"`.  
- API: `Client().ask(state, {Choice([...]), Noul(...)})` — **not** TypeSafe wire-identical.  
- Extreme confidence on token-soup state is a calibration risk for trading; use abstention thresholds carefully.

### Errors

None of the three failed install or inference. Minor notes only (HF unauthenticated warning; laya temperature RuntimeWarning; poorjev torch.jit FutureWarning).

---

## 4. Recommendation for a Solana trading decision loop

### Recommended pick: **von** (`von-sdk` + HF `wfzyx/von`)

**Rationale**

1. **Drop-in System One contract** — `POST /v1/systemone` and `von.system_one()` with Choice / Noul / Score criteria dicts matching TypeSafe-style clients.  
2. **CPU-viable today** — smoke warm ~380 ms on this box; no vLLM/SGLang; claimed ~15–18 ms on GPU if you add one later.  
3. **Trading-smoke behavior** — clear `hold` with 0.84 probability and moderate skip-noul (0.36), which is actionable with thresholds (`hold` unless max(p)≥τ and skip_noul&lt;σ).  
4. **License** — Apache-2.0 (commercial-friendly vs OpenJevPro PolyForm NC).  
5. **Ops fit** — single `pip install von-sdk`, local weights, isolated venv already proven at `/workspace/jev-alts/venvs/von`.

**Suggested loop policy (sketch)**

```text
state = feature_string(tape)   # keep short; von used 59 input tokens here
answers = von.system_one(state, {
  "action": Choice(...buy/sell/hold criteria...),
  "skip_this_cycle": Noul("..."),
})
if answers["skip_this_cycle"].noul >= 0.55: skip
elif answers["action"].confidence < 0.55: hold / skip
else: execute answers["action"].choice with size ~ confidence
```

Target latency budget: keep model warm in-process; 300–400 ms CPU is fine for multi-second Solana decision cadence, not for sub-slot HFT.

### Runner-up: **Laya**

Use if you want the largest community footprint, multilingual router, or `laya-serve` HTTP. Prefer checkpoint `convaiinnovations/laya-typed-decisions` for decision-shaped work, and treat low confidence as abstain (this smoke’s near-uniform probs are a feature for risk control).

### Third: **poorjev**

Good as a **tiny offline gate** or prototype, but rework clients to its `Choice([...])` API and do **not** trust raw 0.99 confidences without your own calibration on trading labels.

### Explicitly avoid for this CPU Solana bot

- razorback16/openjev, openjev-sglang, githubnext/localjev, JevK5, SemIf-4B primary path — GPU / large LLM stacks.  
- OpenJevPro — PolyForm Noncommercial.  
- PyPI `kev` / `jeff` — unrelated.

---

## 5. Artifacts

| Path | Contents |
| --- | --- |
| `/workspace/jev-alts/REPORT.md` | This report |
| `/workspace/jev-alts/smoke/payload.json` | Trading smoke payload |
| `/workspace/jev-alts/results/*_install.log` | Install logs |
| `/workspace/jev-alts/results/*_smoke.json` | Structured smoke outputs |
| `/workspace/jev-alts/venvs/{von,laya,poorjev}` | Isolated installs (~5.6 GiB each, mostly torch) |
| `/workspace/jev-alts/hf-cache` | Shared model cache (~4.1 GiB) |
| `/workspace/jev-alts/readmes/` | Cached upstream READMEs |
| `/workspace/jev-alts/github_meta.json` | Partial GitHub metadata snapshot |

---

## 6. One-line summary

**Stars leaders:** Laya (20.6k) ≫ SemIf (4.1k) ≫ NanoJev (2.1k) ≫ LocalJev (736) ≫ von (588) ≫ simple-jev (502).  
**Smoke-tested:** von / laya / poorjev — **all PASS on CPU**.  
**Recommend for Solana trading loop:** **von** (drop-in `/v1/systemone`, clear hold probs, Apache-2.0, CPU OK); keep **Laya** as mature alternative if you standardize on its SDK.
