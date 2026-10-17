"""Moedas extra só para o backtest (overlay sobre o instantâneo `inputs/`), sem tocar no memecoins.json do lab.

`backtest/assets_extra.json` lista moedas candidatas (mint, decimais, fontes de 1 m, par da Gate.io, custo de execução
assumido) e os portfólios a simular por moeda (modelos de nome com `{SYM}`). O CLI (`scripts/backtest_30d.py
--assets-extra FICHEIRO --only-assets extra|SYM,SYM`):

1. escreve em `<run>/inputs/memecoins.json` as moedas do run (as do instantâneo + as extra, filtradas por
   `--only-assets`; o original fica em `inputs/memecoins_base.json`) ANTES de importar `bot.*` — o lab_bot lê os
   tokens desse ficheiro;
2. acrescenta as moedas extra a `bot.lab_registry.SYMS` e a `bot.rules_engine.MEME_GATE_PAIRS` no processo do
   backtest, para os originais (`meme_{SYM}_baseline/relaxed`, `{SYM}_poorjev_*`, …) e as hipóteses existirem com os
   MESMOS parâmetros das famílias meme (params.json resolvido com asset=<SYM>);
3. semeia no registry do instantâneo as hipóteses H1 das moedas extra (`h1_exits_{SYM}_poorjev_relaxed`, a mesma
   definição de `lab_registry.hypothesis_defs`);
4. filtra o catálogo para os portfólios pedidos e acrescenta um portfólio "só segurar" por moeda (`{SYM}_buy_hold`).

Paper only: nada aqui assina, envia ou lê chaves.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("assets_extra.json")
SOURCES = ("bybit", "kucoin", "binance", "okx")
B58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
SYM_RE = re.compile(r"^[A-Z0-9]{2,12}$")
BH_FAMILY = "Meme · só segurar"


def load(path: Path | str | None = None) -> dict:
    """Lê e valida o ficheiro de moedas extra. Levanta ValueError com todos os erros."""
    p = Path(path) if path else DEFAULT_PATH
    doc = json.loads(Path(p).read_text())
    errs = check(doc)
    if errs:
        raise ValueError(f"{p}: " + "; ".join(errs))
    return doc


def check(doc: dict) -> list[str]:
    errs = []
    toks = doc.get("tokens")
    if not isinstance(toks, list) or not toks:
        return ["tokens: lista não vazia obrigatória"]
    seen = set()
    for i, t in enumerate(toks):
        s = t.get("symbol")
        where = f"tokens[{i}]{'(' + s + ')' if s else ''}"
        if not isinstance(s, str) or not SYM_RE.match(s):
            errs.append(f"{where}: symbol inválido")
        elif s in seen:
            errs.append(f"{where}: symbol repetido")
        seen.add(s)
        if not isinstance(t.get("mint"), str) or not B58.match(t["mint"]):
            errs.append(f"{where}: mint inválido (base58, 32–44 caracteres)")
        if not isinstance(t.get("decimals"), int) or not 0 <= t["decimals"] <= 12:
            errs.append(f"{where}: decimals inteiro 0–12")
        src = t.get("sources")
        if not isinstance(src, list) or not src:
            errs.append(f"{where}: sources (lista de [fonte, instrumento]) obrigatória")
        else:
            for x in src:
                if not (isinstance(x, (list, tuple)) and len(x) == 2 and x[0] in SOURCES and isinstance(x[1], str) and x[1]):
                    errs.append(f"{where}: fonte inválida {x!r} (fontes: {', '.join(SOURCES)})")
        q = t.get("quote_slippage_bps")
        if not isinstance(q, (int, float)) or not 0 <= float(q) <= 500:
            errs.append(f"{where}: quote_slippage_bps numérico 0–500")
    per = doc.get("rotation_period_min")
    if per is not None and (not isinstance(per, int) or per < 1):
        errs.append("rotation_period_min: inteiro ≥ 1")
    for tpl in doc.get("portfolios") or []:
        if "{SYM}" not in tpl:
            errs.append(f"portfolios: '{tpl}' sem {{SYM}}")
    return errs


def symbols(doc: dict) -> list[str]:
    return [t["symbol"] for t in doc["tokens"]]


def parse_only(arg: str | None, doc: dict | None, base_syms: list[str]) -> list[str] | None:
    """`--only-assets`: None (todas), 'extra' (as do ficheiro extra) ou lista 'JUP,BONK'. Valida contra as conhecidas."""
    if not arg:
        return None
    extra = symbols(doc) if doc else []
    if arg.strip().lower() == "extra":
        if not extra:
            raise ValueError("--only-assets extra sem --assets-extra")
        return list(extra)
    out = [s.strip().upper() for s in arg.split(",") if s.strip()]
    known = set(base_syms) | set(extra) | {"SOL"}
    bad = [s for s in out if s not in known]
    if bad:
        raise ValueError(f"--only-assets: desconhecidas {bad} (conhecidas: {sorted(known)})")
    return out


def merged_memecoins(base: dict, doc: dict | None, only: list[str] | None) -> dict:
    """memecoins.json do run: tokens do instantâneo + extra (sem repetir símbolos), filtrados por `only`."""
    out = dict(base)
    toks = [dict(t) for t in base.get("tokens") or []]
    have = {t["symbol"] for t in toks}
    for t in (doc or {}).get("tokens") or []:
        if t["symbol"] in have:
            raise ValueError(f"{t['symbol']}: já existe no memecoins.json do run; o overlay só acrescenta moedas novas")
        toks.append({k: t[k] for k in ("symbol", "mint", "decimals", "coingecko_id", "gate_pair") if k in t}
                    | {"why": "backtest only (assets_extra.json)", "extra": True})
    if only is not None:
        toks = [t for t in toks if t["symbol"] in only]
    out["tokens"] = toks
    if doc:
        out["extra_overlay"] = {"symbols": symbols(doc), "only_assets": only, "note": doc.get("note")}
    return out


def patch_symbols(syms: list[str], gate_pairs: dict | None = None, tokens: list[dict] | None = None) -> dict:
    """Acrescenta moedas a lab_registry.SYMS, rules_engine.MEME_GATE_PAIRS e (se dados) lab_bot.TOKENS, só no
    processo do backtest. Devolve o estado anterior para `unpatch_symbols` (testes)."""
    from bot import lab_registry as R
    from bot import rules_engine as RE
    import bot.lab_bot as LB
    saved = {"SYMS": list(R.SYMS), "PAIRS": dict(RE.MEME_GATE_PAIRS), "TOKENS": dict(LB.TOKENS)}
    R.SYMS = list(R.SYMS) + [s for s in syms if s not in R.SYMS]
    for s in syms:
        RE.MEME_GATE_PAIRS.setdefault(s, (gate_pairs or {}).get(s) or f"{s}_USDT")
    for t in tokens or []:
        LB.TOKENS.setdefault(t["symbol"], t)   # o lab_bot lê memecoins.json na importação
    return saved


def unpatch_symbols(saved: dict) -> None:
    from bot import lab_registry as R
    from bot import rules_engine as RE
    import bot.lab_bot as LB
    R.SYMS = list(saved["SYMS"])
    RE.MEME_GATE_PAIRS.clear(); RE.MEME_GATE_PAIRS.update(saved["PAIRS"])
    LB.TOKENS.clear(); LB.TOKENS.update(saved["TOKENS"])


def seed_hypotheses(reg_path: Path, syms: list[str], created_brt: str) -> list[str]:
    """Semeia no registry do instantâneo as hipóteses meme (H1/H2 das definições ao vivo) das moedas extra que ainda
    não existem. Devolve os nomes criados. Só escreve no `inputs/` do run."""
    from bot import lab_registry as R
    reg = json.loads(reg_path.read_text()) if reg_path.exists() else {"portfolios": {}, "lineages": {}}
    reg.setdefault("portfolios", {}); reg.setdefault("lineages", {})
    made = []
    for h in R.hypothesis_defs():
        if h.get("asset") not in syms or h["name"] in reg["portfolios"]:
            continue
        e = dict(h, status="active", created_brt=created_brt, strategy=f"hyp:{h['name']}", lineage=h["name"],
                 parent=None, is_original=True, backtest_only=True)
        reg["portfolios"][h["name"]] = e
        reg["lineages"].setdefault(h["name"], {"root": h["name"], "lead": None, "members": [h["name"]]})
        made.append(h["name"])
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=1))
    return made


def wanted_names(doc: dict | None, syms: list[str]) -> set[str] | None:
    """Nomes de portfólio pedidos pelos modelos `portfolios` do ficheiro extra (None = todos os do catálogo)."""
    tpls = (doc or {}).get("portfolios")
    if not tpls:
        return None
    return {t.replace("{SYM}", s) for t in tpls for s in syms}


def filter_items(items: list[dict], only: list[str] | None, names: set[str] | None) -> list[dict]:
    out = []
    for it in items:
        if only is not None and it["asset"] not in only:
            continue
        if names is not None and it["asset"] != "SOL" and it["name"] not in names:
            continue
        out.append(it)
    return out


def buy_hold_rows(rows: list[dict]) -> list[dict]:
    """Equity do "só segurar" a partir das linhas gravadas de um portfólio da moeda (bh_equity = 100% na moeda desde o
    início da janela, sem custos de entrada — o mesmo B&H contra o qual todos os portfólios da moeda são medidos)."""
    out = []
    for r in rows:
        px = float(r["price"])
        out.append({"ts": r["ts"], "equity": r["bh_equity"], "price": px, "bh_equity": r["bh_equity"],
                    "q": (float(r["bh_equity"]) / px) if px > 0 else 0.0})
    return out


def buy_hold_item(sym: str) -> dict:
    n = f"{sym}_buy_hold"
    return {"name": n, "meta": {"name": n, "asset": sym, "kind": "buy_hold", "model": "hold", "test_type": "buy_hold"},
            "runner": None, "family": BH_FAMILY, "asset": sym, "model": "hold", "test_type": "buy_hold",
            "profile": None, "parent": None, "is_fork": False, "label": f"Só segurar {sym}", "kind": "buy_hold"}
