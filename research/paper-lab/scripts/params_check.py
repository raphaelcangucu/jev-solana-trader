#!/usr/bin/env python3
"""Verifica params.json: imprime os parâmetros efetivos de todos os portfólios conhecidos (originais dos bots,
hipóteses do lab, forks do registry) e sai com código 1 se houver erros de validação. Paper only, só leitura.

    python scripts/params_check.py                     # tabela de todos, com overlay do dashboard
    python scripts/params_check.py --static            # sem overlay (o que params.json sozinho define)
    python scripts/params_check.py --name relaxed      # um portfólio, com a camada de cada valor (proveniência)
    python scripts/params_check.py --types             # vista por tipo de teste (sem camada de portfólio)
    python scripts/params_check.py --json              # tudo em JSON

Raiz: PAPER_LAB_ROOT (ou a pasta do lab); ficheiro: PAPER_LAB_PARAMS, senão <raiz>/params.json, senão o do lab.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # código do lab
from bot import params as P  # noqa: E402


def row(n, eff, m):
    g = eff.get("gates") or {}
    ex = eff.get("exits") or {}
    xe = eff.get("exec") or {}
    return [n, m.get("test_type") or "–", m.get("profile") or "–", (m.get("model") or "–"), m.get("runner") or "–",
            g.get("min_confidence"), g.get("min_prob_margin") if g.get("margin_gate") else "–", g.get("max_skip_noul"),
            g.get("cooldown_seconds"), g.get("max_trades_per_hour"), g.get("buy_fraction_usdt"),
            "–" if g.get("max_exposure_frac") is None else g.get("max_exposure_frac"),
            xe.get("mode"), "sim" if ex.get("enabled") else "–", "–" if eff.get("hours") is None else eff["hours"],
            "sim" if (eff.get("regime_filter") or {}).get("enabled") else "–",
            "sim" if eff.get("paused") else "–", (m.get("parent") or "–")]


HEAD = ["portfólio", "tipo", "perfil", "modelo", "runner", "conf", "margem", "skip<", "cooldown", "max/h", "compra",
        "exp.máx", "exec", "saídas", "horas", "regime", "pausado", "pai"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--name")
    ap.add_argument("--static", action="store_true", help="sem o overlay do dashboard")
    ap.add_argument("--types", action="store_true")
    ap.add_argument("--json", action="store_true")
    x = ap.parse_args()
    store = P.Store(min_interval=0)
    doc = store.doc()
    reg = P._registry()
    print(f"params: {store.path}", file=sys.stderr)
    if doc is None:
        print("ERRO: " + "; ".join(store.doc_errors), file=sys.stderr)
        return 1
    if x.types:
        out = {}
        bad = 0
        for t in sorted(doc.get("types") or {}):
            eff, prov, errs = P.type_view(t, doc=doc)
            out[t] = {"effective": eff, "provenance": prov, "errors": errs}
            bad += bool(errs)
            if not x.json:
                print(f"\n## {t}" + (f"  ERROS: {'; '.join(errs)}" if errs else ""))
                print("  " + P.summary(eff))
        if x.json:
            print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return 1 if bad else 0
    names = [x.name] if x.name else P.all_names(reg)
    results = {}
    nerr = 0
    for n in names:
        eff, prov, errs, m = store.explain(n, use_overlay=not x.static, registry=reg)
        results[n] = (eff, prov, errs, m)
        nerr += bool(errs)
    if x.json:
        print(json.dumps({n: {"meta": m, "effective": e, "provenance": p, "errors": er}
                          for n, (e, p, er, m) in results.items()}, indent=2, ensure_ascii=False, default=str))
    elif x.name:
        eff, prov, errs, m = results[x.name]
        print(f"# {x.name}  ({m.get('test_type')}, perfil {m.get('profile')}, modelo {m.get('model')}, runner {m.get('runner')}"
              + (f", fork de {m.get('parent')}" if m.get("parent") else "") + ")")
        print(P.summary(eff))
        for path in sorted(prov):
            sect, _, key = path.partition(".")
            cur = eff
            for k in path.split("."):
                cur = cur.get(k) if isinstance(cur, dict) else None
            print(f"  {path:45s} = {json.dumps(cur, ensure_ascii=False):24s} ← {prov[path]}")
        for e in errs:
            print(f"  ERRO: {e}")
    else:
        rows = [HEAD] + [[str(v) for v in row(n, e, m)] for n, (e, _p, _er, m) in results.items()]
        w = [max(len(r[i]) for r in rows) for i in range(len(HEAD))]
        for i, r in enumerate(rows):
            print("  ".join(c.ljust(w[j]) for j, c in enumerate(r)))
            if i == 0:
                print("  ".join("-" * w[j] for j in range(len(HEAD))))
        for n, (_e, _p, errs, _m) in results.items():
            for e in errs:
                print(f"ERRO {n}: {e}", file=sys.stderr)
        print(f"\n{len(results)} portfólios, {nerr} com erros.", file=sys.stderr)
    return 1 if nerr else 0


if __name__ == "__main__":
    raise SystemExit(main())
