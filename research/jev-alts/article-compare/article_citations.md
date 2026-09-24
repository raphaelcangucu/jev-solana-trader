# Article citations — alexsssaint System One pattern

**Source mirror:** https://github.com/juliuss1907/knowledge-base/blob/1c0881d7a02fd310da4a7c4655996797cab2cc2e/raw/posts/2026-09-23_alex-saint-ai-trading-bot-jev-solana.md  
**Original:** https://x.com/alexsssaint/status/2102420062023946602 (title in feed: “save it > run it tonight”; task alias: “how to build a self-rewriting solana trading system on a $8 VPS”)  
**Author:** alex saint (@alexsssaint)  
**Ingested:** 2026-09-23

## Canonical request (article §1)

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer $TYPESAFE_API_KEY
Content-Type: application/json

{
  "model": "jev-latest",
  "state": "thin bot_war pumping violent flat green wide calm early mid quiet held",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "buy on strength only when the book can absorb it",
      "criteria": {
        "buy": "the move is strong and depth is not thin",
        "sell": "the move is fading or fees are climbing",
        "hold": "anything else"
      }
    },
    "skip_this_cycle": {
      "type": "noul",
      "instructions": "conditions are too hostile to trade at all"
    }
  }
}
```

## Canonical example response (article §1)

```
{
  "action": {
    "type": "choice",
    "choice": "hold",
    "probabilities": { "buy": 0.11, "sell": 0.08, "hold": 0.81 },
    "confidence": 0.81
  },
  "skip_this_cycle": { "type": "noul", "noul": 0.22 }
}
```

## Pattern expectations used for scoring

| Expectation | Article evidence |
| --- | --- |
| Wire: `POST /v1/systemone` | curl in §1 |
| State: ~12 adjective words, **no raw numbers** | §2–§3 (“never hand it a number”, “twelve words”) |
| Actions: Choice `buy`/`sell`/`hold` + Noul `skip_this_cycle` | §1, §4 |
| Confidence thresholding: act on high conf; hold on low; night rewrite audits conf **> 0.8** wrong | §1 (“High confidence, act… Low confidence, hold”), §6 |
| Latency: ~0.3 s per answer; loop every **15 s** | §1 (“0.3 seconds”), intro |
| Append-only decision log with conf + skip | §5 JSONL example |
| Fail-closed: no answer → hold | FAQ |

## Adjective vocabulary from article §2

```
depth: thin | deep     (slippage1k > 0.006 → thin)
fees:  bot_war | quiet (feeRatio > 2.5 → bot_war)
move:  pumping | flat  (return15m > 0.02 → pumping)
vol:   violent | calm  (stdev > 0.008 → violent)
```

Plus sample tokens: `green`, `wide`, `early`, `mid`, `held`, and article sell criterion language (“fading”, “fees climbing”).
