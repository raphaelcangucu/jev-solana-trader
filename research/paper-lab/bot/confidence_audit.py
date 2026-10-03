"""Auditoria de erros confiantes para a revisão noturna (funções puras, sem I/O).

Substitui o critério antigo "conf > 0,8 e trade com approx_pnl < 0", que nunca dispara com o von
(confianças em ~0,23 e ~0,38) e só olhava vendas (compras nunca eram auditadas).

Definições (ver também `research/paper-lab/README.md`, secção "Revisão noturna por percentil"):

- **Respondida**: linha de decisão em que o modelo respondeu de facto: sem `fail_closed`, `von_ok` não é
  False, `model != "rule"` (regras têm conf=1,0 fixa), confiança finita > 0 e `chosen_action` válida.
  (As cópias do lab de um modelo em falha têm conf 0 → excluídas.)
- **Corte**: percentil P (padrão 90) das confianças respondidas do grupo na janela (`conf >= corte`), ou a
  barra fixa antiga (`conf > barra`) para comparação. Empates: as confianças do von concentram-se em poucos
  valores, e `>=` no percentil pode marcar metade das decisões como "confiantes". Com `tie_rule="auto"`
  (padrão), se `>=` marcar mais de 1,5 × (100−P)% das respondidas passa-se a `conf > corte` (desde que isso
  deixe pelo menos uma linha); `"ge"`/`"gt"` fixam a regra. A regra usada vai em `rule`.
- **Candidatas** (`candidates`):
  - `"chosen"` (padrão): a chamada direcional do modelo (`chosen_action` buy/sell), antes dos portões.
    Os portões de carteira (`insufficient_usdt`, cooldown, limite/h) não dizem nada sobre se o modelo
    acertou; nos logs reais o `relaxed` fica 100% investido e passa a registar `final_action=hold`, pelo que
    auditar só o que virou trade deixava o modelo sem auditoria.
  - `"acted"`: só o que virou ordem paper: `traded`, `decision_id` presente em trades ou `final_action` buy/sell.
- **Erro**: compra seguida de retorno a `horizon_s` abaixo de −`band`; venda seguida de retorno acima de +`band`.
  **Acerto**: movimento além da banda no sentido da chamada. Dentro da banda: `flat`.
  Preço futuro = primeiro ponto da série do mesmo ativo em [t+horizon, t+horizon+tolerance]; sem ponto → não resolvida.
"""
from __future__ import annotations
import bisect
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

BRT = timezone(timedelta(hours=-3))

DEFAULTS = {
    "confidence_percentile": 90,
    "fixed_bar": 0.8,
    "horizon_s": 900,
    "band": 0.001,
    "tolerance_s": 300,
    "candidates": "chosen",
    "min_mistakes": 1,
    "top_words": 8,
    "tie_rule": "auto",
}
DIRECTIONAL = ("buy", "sell")
# Palavras que não descrevem o mercado (posição/humor/fase fixa) não viram frases de critério.
NON_MARKET_WORDS = {"mid", "held", "sold", "bare", "buoyed", "stung", "neutral"}


def review_cfg(cfg: dict | None) -> dict:
    out = dict(DEFAULTS)
    out.update(((cfg or {}).get("review") or {}))
    return out


def _conf(row) -> float | None:
    try:
        c = float(row.get("confidence"))
    except (TypeError, ValueError):
        return None
    return c if math.isfinite(c) else None


def is_answered(row: dict) -> bool:
    if row.get("fail_closed") or row.get("von_ok") is False:
        return False
    if str(row.get("model") or "") == "rule":
        return False
    c = _conf(row)
    if c is None or c <= 0:
        return False
    return row.get("chosen_action") in ("buy", "sell", "hold")


def percentile(values: Iterable[float], p: float) -> float | None:
    """Percentil com interpolação linear (igual ao padrão do numpy)."""
    xs = sorted(float(v) for v in values)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * max(0.0, min(100.0, float(p))) / 100.0
    lo = math.floor(k); hi = math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def asset_of(row: dict) -> str:
    return str(row.get("symbol") or row.get("asset") or "SOL")


def price_of(row: dict) -> float | None:
    for v in (row.get("price_usd"), row.get("price_mark"), (row.get("features") or {}).get("price")):
        try:
            if v is not None and float(v) > 0:
                return float(v)
        except (TypeError, ValueError):
            pass
    return None


def build_series(rows: Iterable[dict], asset: str | None = None) -> dict[str, tuple[list, list]]:
    """{ativo: (ts ordenados, preços)} a partir de linhas com ts + preço (logs de preço ou de decisão).
    `asset` força o ativo (ex.: data/prices.jsonl não tem símbolo → "SOL"). Ignora linhas fabricadas."""
    tmp: dict[str, list] = {}
    for r in rows:
        if r.get("fabricated"):
            continue
        px = price_of(r); ts = r.get("ts")
        if px is None or ts is None:
            continue
        tmp.setdefault(asset or asset_of(r), []).append((float(ts), px))
    out = {}
    for a, pts in tmp.items():
        pts.sort()
        out[a] = ([p[0] for p in pts], [p[1] for p in pts])
    return out


def merge_series(*series: dict) -> dict:
    tmp: dict[str, list] = {}
    for s in series:
        for a, (ts, px) in (s or {}).items():
            tmp.setdefault(a, []).extend(zip(ts, px))
    out = {}
    for a, pts in tmp.items():
        pts = sorted(set(pts))
        out[a] = ([p[0] for p in pts], [p[1] for p in pts])
    return out


def forward_price(series: tuple[list, list] | None, ts: float, horizon_s: float, tolerance_s: float):
    """Primeiro (ts, preço) em [ts+horizon, ts+horizon+tolerance] ou None."""
    if not series:
        return None
    tl, pl = series
    target = float(ts) + float(horizon_s)
    i = bisect.bisect_left(tl, target)
    if i < len(tl) and tl[i] <= target + float(tolerance_s):
        return tl[i], pl[i]
    return None


def classify(side: str, ret: float, band: float) -> str:
    if side == "buy":
        return "mistake" if ret < -band else ("correct" if ret > band else "flat")
    if side == "sell":
        return "mistake" if ret > band else ("correct" if ret < -band else "flat")
    return "flat"


def dedupe_calls(rows: Iterable[dict], window_s: float = 5.0, traded_ids: set | None = None) -> list[dict]:
    """Funde linhas que são a MESMA chamada ao modelo registada por vários portfólios (ex.: baseline e
    relaxed partilham uma chamada von por ciclo). Chave: modelo, ativo, estado, confiança, escolha e preço,
    com |Δts| <= window_s. A linha resultante guarda `_portfolios` e `_acted` (OU entre as fundidas)."""
    traded_ids = traded_ids or set()
    out: list[dict] = []
    last: dict[tuple, dict] = {}
    for r in sorted(rows, key=lambda x: float(x.get("ts") or 0)):
        key = (r.get("model"), asset_of(r), r.get("state"), _conf(r), r.get("chosen_action"), price_of(r))
        acted = is_acted(r, traded_ids)
        prev = last.get(key)
        if prev is not None and abs(float(r.get("ts") or 0) - float(prev.get("ts") or 0)) <= window_s:
            prev["_portfolios"].append(r.get("portfolio"))
            if acted and not prev["_acted"]:
                prev["_acted"] = True
                prev["_acted_side"] = acted_side(r, None)
            continue
        m = dict(r)
        m["_portfolios"] = [r.get("portfolio")]
        m["_acted"] = acted
        m["_acted_side"] = acted_side(r, None) if acted else None
        last[key] = m
        out.append(m)
    return out


def is_acted(row: dict, traded_ids: set) -> bool:
    if "_acted" in row:
        return bool(row["_acted"])
    return bool(row.get("traded")) or row.get("final_action") in DIRECTIONAL or (
        row.get("decision_id") is not None and row.get("decision_id") in traded_ids)


def acted_side(row: dict, trade_side: dict | None) -> str | None:
    if row.get("_acted_side"):
        return row["_acted_side"]
    if row.get("final_action") in DIRECTIONAL:
        return row["final_action"]
    if trade_side and row.get("decision_id") in trade_side:
        return trade_side[row["decision_id"]]
    return row.get("chosen_action") if row.get("chosen_action") in DIRECTIONAL else None


def _words(row) -> list[str]:
    return [w for w in str(row.get("state") or "").split() if w]


def audit(decisions: Iterable[dict], *, prices: dict | None = None, trades: Iterable[dict] | None = None,
          percentile_p: float = 90, fixed_bar: float | None = None, horizon_s: float = 900, band: float = 0.001,
          tolerance_s: float = 300, candidates: str = "chosen", window: tuple | None = None,
          top_words: int = 8, tie_rule: str = "auto") -> dict[str, Any]:
    """Auditoria de um grupo (um modelo/portfólio). `prices` = {ativo: (ts, preços)}; sem série para o ativo
    usa os preços das próprias decisões. `fixed_bar` definido → corte fixo `conf > fixed_bar` (modo antigo)."""
    if candidates not in ("chosen", "acted"):
        raise ValueError("candidates must be 'chosen' or 'acted'")
    rows = [r for r in decisions if r.get("ts") is not None]
    if window:
        a, b = window
        rows = [r for r in rows if (a is None or float(r["ts"]) >= a) and (b is None or float(r["ts"]) < b)]
    trades = list(trades or [])
    traded_ids = {t.get("decision_id") for t in trades if t.get("decision_id")}
    trade_side = {t.get("decision_id"): t.get("side") for t in trades if t.get("decision_id")}
    answered = [r for r in rows if is_answered(r)]
    confs = [_conf(r) for r in answered]
    if fixed_bar is not None:
        cutoff = float(fixed_bar); rule = f"conf > {fixed_bar:g} (barra fixa)"; passes = lambda c: c > cutoff
    else:
        cutoff = percentile(confs, percentile_p)
        if cutoff is None:
            rule = f"conf >= P{percentile_p:g}"; passes = lambda c: False
        else:
            n_ge = sum(1 for c in confs if c >= cutoff); n_gt = sum(1 for c in confs if c > cutoff)
            target = (100.0 - float(percentile_p)) / 100.0 * len(confs)
            strict = tie_rule == "gt" or (tie_rule == "auto" and n_ge > 1.5 * target and n_gt > 0)
            if strict:
                rule = f"conf > P{percentile_p:g}" + (" (empates)" if tie_rule == "auto" else "")
                passes = lambda c: c > cutoff
            else:
                rule = f"conf >= P{percentile_p:g}"; passes = lambda c: c >= cutoff
    series = dict(build_series(rows))
    series.update(prices or {})

    if candidates == "chosen":
        cand = [(r, r["chosen_action"]) for r in answered if r.get("chosen_action") in DIRECTIONAL]
    else:
        cand = []
        for r in answered:
            if is_acted(r, traded_ids):
                s = acted_side(r, trade_side)
                if s in DIRECTIONAL:
                    cand.append((r, s))
    confident = [(r, s) for r, s in cand if passes(_conf(r))]

    by_side = {s: Counter() for s in DIRECTIONAL}
    outcomes = []
    lose = Counter()
    word_total = Counter(); word_mist = Counter()
    for r, side in confident:
        by_side[side]["confident"] += 1
        p0 = price_of(r)
        fwd = forward_price(series.get(asset_of(r)), float(r["ts"]), horizon_s, tolerance_s) if p0 else None
        if fwd is None:
            by_side[side]["unresolved"] += 1
            continue
        ret = fwd[1] / p0 - 1.0
        out = classify(side, ret, band)
        by_side[side]["resolved"] += 1
        by_side[side][out] += 1
        ws = set(_words(r))
        word_total.update(ws)
        item = {"ts": float(r["ts"]), "ts_brt": r.get("ts_brt") or datetime.fromtimestamp(float(r["ts"]), BRT).isoformat(),
                "portfolio": r.get("portfolio"), "portfolios": r.get("_portfolios"), "model": r.get("model"),
                "asset": asset_of(r), "side": side, "confidence": _conf(r), "state": r.get("state"),
                "price": p0, "fwd_price": fwd[1], "fwd_ts": fwd[0], "ret": ret, "outcome": out,
                "decision_id": r.get("decision_id"), "acted": is_acted(r, traded_ids)}
        outcomes.append(item)
        if out == "mistake":
            lose.update(ws); word_mist.update(ws)  # nº de erros em que a palavra aparece

    tot = Counter()
    for c in by_side.values():
        tot.update(c)
    resolved = tot["resolved"]
    ts_all = [float(r["ts"]) for r in rows]
    return {
        "rule": rule, "cutoff": cutoff, "percentile": None if fixed_bar is not None else percentile_p,
        "fixed_bar": fixed_bar, "candidates": candidates, "horizon_s": horizon_s, "band": band,
        "window": (min(ts_all), max(ts_all)) if ts_all else None,
        "n_rows": len(rows), "n_answered": len(answered), "n_unanswered": len(rows) - len(answered),
        "conf_p50": percentile(confs, 50), "conf_max": max(confs) if confs else None,
        "n_candidates": len(cand), "n_confident": len(confident),
        "n_confident_acted": sum(1 for r, _ in confident if is_acted(r, traded_ids)),
        "confident_share": (len(confident) / len(answered)) if answered else None,
        "n_resolved": resolved, "n_unresolved": tot["unresolved"],
        "n_mistakes": tot["mistake"], "n_correct": tot["correct"], "n_flat": tot["flat"],
        "mistake_episodes": episodes([o["ts"] for o in outcomes if o["outcome"] == "mistake"]),
        "hit_rate": (tot["correct"] / resolved) if resolved else None,
        "mistake_rate": (tot["mistake"] / resolved) if resolved else None,
        "by_side": {s: dict(c) for s, c in by_side.items()},
        "lose_words": sorted(lose.items(), key=lambda x: (-x[1], x[0]))[:top_words],  # desempate alfabético (determinístico)
        "word_stats": {w: [word_mist[w], word_total[w]] for w in word_total},
        "mistakes": [o for o in outcomes if o["outcome"] == "mistake"],
        "outcomes": outcomes,
    }


def episodes(ts_list, gap_s: float = 300.0) -> int:
    """Nº de episódios: chamadas consecutivas (ciclos de 15 s num mesmo estado) separadas por > gap_s contam como novo episódio."""
    n = 0; last = None
    for t in sorted(ts_list):
        if last is None or t - last > gap_s:
            n += 1
        last = t
    return n


def summary(a: dict) -> dict:
    """Versão compacta (sem listas longas) para JSON de proposta e relatórios."""
    keys = ("rule", "cutoff", "percentile", "fixed_bar", "candidates", "horizon_s", "band", "n_rows", "n_answered",
            "n_candidates", "n_confident", "confident_share",
            "n_confident_acted", "n_resolved", "n_unresolved", "n_mistakes", "mistake_episodes", "n_correct", "n_flat", "hit_rate",
            "mistake_rate", "by_side", "lose_words")
    return {k: a.get(k) for k in keys}


def distinctive_words(a: dict, side: str | None = None, min_count: int = 2, min_lift: float = 0.15, k: int = 3) -> list[str]:
    """Palavras de estado sobre-representadas nos erros: taxa de erro dado a palavra >= taxa global + min_lift."""
    outs = [o for o in a.get("outcomes") or [] if side is None or o["side"] == side]
    if not outs:
        return []
    base = sum(1 for o in outs if o["outcome"] == "mistake") / len(outs)
    tot = Counter(); mis = Counter()
    for o in outs:
        ws = set(str(o.get("state") or "").split()) - NON_MARKET_WORDS
        tot.update(ws)
        if o["outcome"] == "mistake":
            mis.update(ws)
    cand = [(mis[w] / tot[w], mis[w], w) for w in mis if mis[w] >= min_count and mis[w] / tot[w] >= base + min_lift]
    return [w for _, _, w in sorted(cand, key=lambda x: (-x[0], -x[1], x[2]))[:k]]


def _top_market_words(mistakes: list, side: str, k: int = 3) -> list[str]:
    """Recurso quando não há palavra distintiva (ex.: todos os confiantes erraram no mesmo estado):
    as palavras de mercado mais frequentes nos erros desse lado (desempate alfabético)."""
    c = Counter()
    for m in mistakes:
        if m["side"] == side:
            c.update(set(str(m.get("state") or "").split()) - NON_MARKET_WORDS)
    return [w for w, _ in sorted(c.items(), key=lambda x: (-x[1], x[0]))[:k]]


def propose_criteria(base: dict, a: dict, *, min_mistakes: int = 1, generated_at: str | None = None,
                     source: str = "night_review_percentile_audit") -> dict:
    """Reescrita determinística a partir da auditoria. Só acrescenta frases quando há erros confiantes
    (>= min_mistakes); sem erros a proposta é o texto base inalterado (`changed: False`).
    Nunca escreve ficheiros (portão humano fica com o chamador)."""
    mistakes = a.get("mistakes") or []
    lose = Counter()
    by_side_words = {s: Counter() for s in DIRECTIONAL}
    for m in mistakes:
        ws = str(m.get("state") or "").split()
        lose.update(ws); by_side_words[m["side"]].update(ws)
    extra = {"buy": [], "sell": [], "hold": [], "skip": []}
    if len(mistakes) >= min_mistakes:
        if lose.get("thin", 0) + lose.get("bot_war", 0) >= 1:
            extra["buy"].append("and the book is deep not thin")
            extra["skip"].append("especially when the book is thin or fees feel hostile")
        if lose.get("violent", 0) or lose.get("whipping", 0):
            extra["hold"].append("when the tape is violent or whipping")
            extra["skip"].append("when volatility is violent")
        if by_side_words["buy"].get("fading", 0) or by_side_words["buy"].get("dumping", 0):
            extra["buy"].append("never while the move is fading or dumping")
        if by_side_words["sell"].get("pumping", 0) or by_side_words["sell"].get("lifting", 0):
            extra["sell"].append("not while the move is still lifting or pumping")
        for side in DIRECTIONAL:
            n_side = sum(1 for m in mistakes if m["side"] == side)
            if n_side >= min_mistakes:
                words = distinctive_words(a, side) or _top_market_words(mistakes, side)
                if words:
                    extra[side].append("be wary when the tape reads " + ", ".join(words))
    changed = any(extra.values())
    act = base["action"]
    crit = dict(act["criteria"])
    for k in ("buy", "sell", "hold"):
        if extra[k]:
            crit[k] = crit[k] + "; " + "; ".join(extra[k])
    skip = base["skip_this_cycle"]["instructions"] + ("; " + "; ".join(extra["skip"]) if extra["skip"] else "")
    instr = act["instructions"] + ("; be stricter after overnight audit of confident mistakes" if changed else "")
    return {
        "version": "v2",
        "source": source,
        "parent": base.get("version", "baseline"),
        "generated_at_brt": generated_at or datetime.now(BRT).isoformat(),
        "method": (f"Deterministic rewrite from a percentile confidence audit ({a.get('rule')}, candidates="
                   f"{a.get('candidates')}, horizon {a.get('horizon_s')}s, band {a.get('band')}). Phrases are appended "
                   "only when there are confident mistakes. Baseline untouched (human gate)."),
        "changed": changed,
        "phrases_added": {k: v for k, v in extra.items() if v},
        "action": {"instructions": instr, "criteria": crit},
        "skip_this_cycle": {"instructions": skip},
        "audit": summary(a),
    }


def same_text(a: dict, b: dict) -> bool:
    return a.get("action") == b.get("action") and a.get("skip_this_cycle") == b.get("skip_this_cycle")


def group_rows(rows: Iterable[dict], key: Callable[[dict], Any]) -> dict:
    out: dict = {}
    for r in rows:
        k = key(r)
        if k is not None:
            out.setdefault(k, []).append(r)
    return out
