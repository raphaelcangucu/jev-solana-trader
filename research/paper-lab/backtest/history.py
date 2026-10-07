"""Histórico das simulações retroativas: `index.json`, `chart.json` (janelas longas) e `history.md`.

- `index.json` (em <base>/data/backtest): uma entrada por pasta de run com summary.json, ordenada pelo fim da janela
  (mais recente primeiro). Mantido pelo CLI no fim de cada run (`update_index`), e reconstruído a partir das pastas
  sempre que falta ou está inválido — as pastas dos runs são a fonte da verdade, o índice é só um resumo.
- `kind`: "30d" para as janelas mensais (28–31 dias; ex.: 2026-08-06 → 2026-09-06 tem 31 dias), senão "<N>d".
- `latest` continua a apontar para o run mensal ("30d") mais recente pelo fim da janela; um run mais antigo ou longo
  não o muda (`latest_after`).
- `chart.json` (só nas janelas longas): curvas normalizadas a 1000 no início da janela (benchmarks, mediana por
  família, os portfólios em destaque, bot real A/B) com ≤ 1500 pontos, e os vencedores de cada bloco de 30 dias.
- `history.md`: comparação dos runs mensais lado a lado, consistência entre meses e o resumo dos 6 meses.

Só lê summaries/equity já escritos (nada de rede, chaves ou ordens).
"""
from __future__ import annotations

import json
import math
import os
import statistics
from datetime import datetime
from pathlib import Path

import numpy as np

from backtest.simenv import BRT

MAX_CHART_POINTS = 1500
USDC_APY = 0.06
CHART_TOP_FIXED = ["rsi_sol_1h", "relaxed", "poorjev_relaxed", "h1_exits_FARTCOIN_poorjev_relaxed", "relaxed__fork1"]
MEMES = ["BONK", "WIF", "POPCAT", "FARTCOIN", "PNUT", "MEW", "GOAT"]


def _r(x, n=4):
    if x is None:
        return None
    try:
        x = float(x)
    except Exception:
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return round(x, n)


def brt(ts) -> str:
    return datetime.fromtimestamp(int(ts), tz=BRT).isoformat(timespec="seconds")


def run_kind(days) -> str:
    d = float(days or 0)
    return "30d" if 28 <= d <= 31.5 else f"{int(round(d))}d"


def _skill_key(p):
    return p["skill"] if p.get("skill") is not None else -1e18


def top_by(ports, key, n=5):
    if key == "skill":
        ps = sorted(ports, key=lambda p: -_skill_key(p))
    else:
        ps = sorted(ports, key=lambda p: -(p.get("pnl_pct") if p.get("pnl_pct") is not None else -1e18))
    return [{"name": p["name"], "skill": p.get("skill"), "pnl_pct": p.get("pnl_pct")} for p in ps[:n]]


# ------------------------------------------------------------------ índice

def index_entry(summary: dict) -> dict:
    w = summary.get("window") or {}
    ports = summary.get("portfolios") or []
    win = summary.get("winner") or {}
    return {
        "run_id": summary.get("run_id"), "kind": run_kind(w.get("days")),
        "start_brt": w.get("start_brt"), "end_brt": w.get("end_brt"), "days": w.get("days"),
        "generated_brt": summary.get("generated_brt"), "n_portfolios": len(ports),
        "n_winners": sum(1 for p in ports if p.get("verdict") == "vencedora"),
        "n_losers": sum(1 for p in ports if p.get("verdict") == "perdedora"),
        "n_inconclusive": sum(1 for p in ports if p.get("verdict") == "inconclusiva"),
        "winner": {"by_skill": win.get("by_skill"), "by_pnl": win.get("by_pnl"), "by_verdict": win.get("by_verdict")},
        "top_skill": top_by(ports, "skill"), "top_pnl": top_by(ports, "pnl"),
        "realbot": [{"book": b.get("book"), "pnl_pct": b.get("pnl_pct"), "vs_hold": b.get("vs_hold")}
                    for b in summary.get("realbot") or []],
        "assets": {s: a.get("ret_pct") for s, a in (summary.get("assets") or {}).items()},
        "look_ahead_forks": [p["name"] for p in ports if p.get("look_ahead")],
    }


def _end_key(e):
    try:
        return datetime.fromisoformat(e.get("end_brt")).timestamp()
    except Exception:
        return 0.0


def sort_runs(entries):
    return sorted(entries, key=lambda e: (_end_key(e), str(e.get("generated_brt") or ""), str(e.get("run_id"))),
                  reverse=True)


def _run_dirs(base: Path):
    for d in sorted(Path(base).iterdir()) if Path(base).is_dir() else []:
        if d.is_dir() and not d.name.startswith((".", "_")) and (d / "summary.json").is_file():
            yield d


def _write_atomic(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def load_index(base: Path) -> dict | None:
    try:
        idx = json.loads((Path(base) / "index.json").read_text())
        return idx if isinstance(idx, dict) and isinstance(idx.get("runs"), list) else None
    except Exception:
        return None


def update_index(base: Path, summary: dict | None = None) -> dict:
    """Atualiza <base>/index.json: insere/substitui a entrada de `summary` (se dado), acrescenta pastas de run que
    faltem no índice, retira entradas cujas pastas já não existem e ordena pelo fim da janela (mais recente primeiro).
    Sem índice válido, reconstrói tudo a partir das pastas."""
    base = Path(base)
    dirs = {d.name: d for d in _run_dirs(base)}
    idx = load_index(base) or {"runs": []}
    by_id = {e.get("run_id"): e for e in idx["runs"] if e.get("run_id") in dirs}
    if summary is not None and summary.get("run_id"):
        by_id[summary["run_id"]] = index_entry(summary)
    for rid, d in dirs.items():
        if rid not in by_id:
            try:
                by_id[rid] = index_entry(json.loads((d / "summary.json").read_text()))
            except Exception:
                continue
    out = {"updated_brt": datetime.now(tz=BRT).isoformat(timespec="seconds"), "runs": sort_runs(by_id.values())}
    _write_atomic(base / "index.json", json.dumps(out, ensure_ascii=False, indent=1))
    return out


def latest_after(base: Path, run_id: str, kind: str, end_brt: str) -> str | None:
    """Para onde deve apontar `latest` depois deste run: o run mensal mais recente pelo fim da janela.
    Um run que não é mensal, ou mais antigo que o atual, deixa `latest` como está."""
    base = Path(base)
    try:
        cur = (base / "latest").read_text().strip()
    except Exception:
        cur = ""
    if kind != "30d":
        return cur or None
    cur_s = None
    if cur and (base / cur / "summary.json").is_file():
        try:
            cur_s = json.loads((base / cur / "summary.json").read_text())
        except Exception:
            cur_s = None
    if cur_s is None or run_kind((cur_s.get("window") or {}).get("days")) != "30d":
        return run_id
    if cur == run_id:
        return run_id
    cur_end = _end_key({"end_brt": (cur_s.get("window") or {}).get("end_brt")})
    return run_id if _end_key({"end_brt": end_brt}) >= cur_end else cur


# ------------------------------------------------------------------ gráfico (janelas longas)

def month_blocks(start: int, end: int, n: int | None = None, block_s: int = 30 * 86400):
    """Blocos de 30 dias contados do FIM da janela (os mesmos da consistência mensal), do mais antigo ao mais recente."""
    n = n if n is not None else max(1, int(round((end - start) / block_s)))
    out = []
    for k in range(n - 1, -1, -1):
        b = end - block_s * k
        a = max(start, b - block_s)
        mid = datetime.fromtimestamp((a + b) / 2, tz=BRT)
        out.append({"month": mid.strftime("%Y-%m"), "a": int(a), "b": int(b), "start_brt": brt(a), "end_brt": brt(b)})
    return out


def chart_times(start: int, end: int, max_points: int = MAX_CHART_POINTS, unit: int = 3600) -> np.ndarray:
    """Grelha regular (múltiplos de `unit`) de start a end, com ≤ max_points pontos e o fim incluído."""
    span = max(1, end - start)
    step = unit * max(1, math.ceil(span / unit / (max_points - 1)))
    t = np.arange(start, end, step, dtype=np.int64)
    t = np.append(t, end)
    if len(t) > max_points:
        t = np.append(t[: max_points - 1], end)
    return t


def sample_at(ts, vals, t):
    """Valor da última observação com ts ≤ t (a primeira, antes do início)."""
    ts = np.asarray(ts, dtype=float)
    vals = np.asarray(vals, dtype=float)
    i = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(ts) - 1)
    return vals[i]


def norm1000(v):
    v = np.asarray(v, dtype=float)
    base = v[0] if len(v) and v[0] else (v[np.nonzero(v)[0][0]] if np.any(v) else 1.0)
    return v / base * 1000.0


def _rl(v, n=2):
    return [_r(x, n) for x in v]


def chart_top_names(ports: list[dict]) -> list[str]:
    names = [p["name"] for p in sorted(ports, key=lambda p: -_skill_key(p))[:6]]
    names += [p["name"] for p in sorted(ports, key=lambda p: -(p.get("pnl_pct") or -1e18))[:3]]
    have = {p["name"] for p in ports}
    names += [n for n in CHART_TOP_FIXED if n in have]
    out = []
    for n in names:
        if n not in out:
            out.append(n)
    return out


def build_chart(*, start: int, end: int, equity: dict, ports: list[dict], prices: dict, realbot: dict,
                months: list[dict], max_points: int = MAX_CHART_POINTS) -> dict:
    """chart.json. equity: {nome: (ts, equity)}; ports: linhas do summary (name, family, pnl_pct, skill);
    prices: {SYM: (ts, preço)} (SOL e memecoins); realbot: {"A": (ts, equity), ...}; months: linhas já calculadas
    ({month, start_brt, end_brt, top_by_pnl, top_by_skill, sol_ret, memes_ret}). Tudo normalizado: 1000 = início."""
    t = chart_times(start, end, max_points)
    out = {"t": [int(x) for x in t], "start_brt": brt(start), "end_brt": brt(end), "normalized_to": 1000,
           "benchmarks": {}, "families": {}, "top": {}, "realbot": {}, "monthly": months}
    if "SOL" in prices:
        out["benchmarks"]["sol_bh"] = _rl(norm1000(sample_at(*prices["SOL"], t)))
    memes = [s for s in MEMES if s in prices]
    if memes:
        basket = sum(norm1000(sample_at(*prices[s], t)) / len(memes) for s in memes)
        out["benchmarks"]["memes_bh"] = _rl(basket)
        out["benchmarks"]["memes_in_basket"] = memes
    out["benchmarks"]["usdc"] = _rl(1000.0 * (1 + USDC_APY * (t - start) / (365 * 86400)))
    fam: dict = {}
    for p in ports:
        if p["name"] in equity:
            fam.setdefault(p["family"], []).append(norm1000(sample_at(*equity[p["name"]], t)))
    for f, curves in sorted(fam.items()):
        out["families"][f] = _rl(np.median(np.vstack(curves), axis=0))
    for n in chart_top_names(ports):
        if n in equity:
            out["top"][n] = _rl(norm1000(sample_at(*equity[n], t)))
    for k, (ts, eq) in sorted(realbot.items()):
        out["realbot"][k] = _rl(norm1000(sample_at(ts, eq, t)))
    return out


# ------------------------------------------------------------------ history.md

def _fmt(x, n=2, sign=True):
    if x is None:
        return "–"
    return f"{x:+.{n}f}" if sign else f"{x:.{n}f}"


def _load_summaries(base: Path, entries):
    out = []
    for e in entries:
        try:
            out.append(json.loads((Path(base) / e["run_id"] / "summary.json").read_text()))
        except Exception:
            continue
    return out


def _short(s: dict) -> str:
    w = s["window"]
    return f"{w['start_brt'][:10]} → {w['end_brt'][:10]}"


def consistency(monthly: list[dict], top_n: int = 15) -> list[dict]:
    """Por portfólio presente em todos os meses: meses com habilidade > 0, meses a bater o B&H, presenças no top N
    (habilidade e PnL), PnL composto e habilidade somada."""
    if not monthly:
        return []
    names = set.intersection(*[{p["name"] for p in s["portfolios"]} for s in monthly])
    tops_s = [{p["name"] for p in sorted(s["portfolios"], key=lambda p: -_skill_key(p))[:top_n]} for s in monthly]
    tops_p = [{p["name"] for p in sorted(s["portfolios"], key=lambda p: -(p.get("pnl_pct") or -1e18))[:top_n]} for s in monthly]
    P = [{p["name"]: p for p in s["portfolios"]} for s in monthly]
    rows = []
    for n in sorted(names):
        ps = [d[n] for d in P]
        comp = 1.0
        for p in ps:
            comp *= 1 + (p.get("pnl_pct") or 0) / 100
        rows.append({"name": n, "family": ps[0].get("family"),
                     "skill_pos": sum(1 for p in ps if (p.get("skill") or 0) > 0),
                     "beat_bh": sum(1 for p in ps if (p.get("vs_bh") or 0) > 0),
                     "top_skill": sum(1 for k in range(len(ps)) if n in tops_s[k]),
                     "top_pnl": sum(1 for k in range(len(ps)) if n in tops_p[k]),
                     "pnl_comp_pct": (comp - 1) * 100, "skill_sum": sum((p.get("skill") or 0) for p in ps),
                     "pnl_by_month": [p.get("pnl_pct") for p in ps], "skill_by_month": [p.get("skill") for p in ps],
                     "trades": sum(p.get("trades") or 0 for p in ps),
                     "look_ahead": any(p.get("look_ahead") for p in ps)})
    return rows


def history_md(base: Path, index: dict | None = None) -> str:
    base = Path(base)
    index = index or update_index(base)
    runs = index["runs"]
    monthly_e = sorted([e for e in runs if e["kind"] == "30d"], key=_end_key)
    monthly = _load_summaries(base, monthly_e)
    longs = [e for e in runs if e["kind"] != "30d" and (e.get("days") or 0) >= 60]
    L = ["# Histórico das simulações retroativas", "",
         f"Atualizado (BRT): {datetime.now(tz=BRT).isoformat(timespec='seconds')} · runs no índice: {len(runs)} "
         f"({len(monthly)} mensais, {len(longs)} longo(s)). Fonte: `data/backtest/index.json` e os `summary.json` de cada "
         "pasta. Paper only: nada aqui é ordem real.", "",
         "Todos os runs usam o MESMO catálogo e os mesmos pressupostos (instantâneo `inputs/` do run "
         "bt30_2026-10-06: registry, params, overlay, critérios, models.json; custos de execução por ativo medidos nos "
         "fills reais do run ao vivo). Cada run começa com o capital inicial no início da sua janela (não herda posições).", ""]
    if monthly:
        hdr = "| | " + " | ".join(f"**{s['run_id']}**" for s in monthly) + " |"
        sep = "|---|" + "---|" * len(monthly)
        L += ["## Meses lado a lado", "", hdr, sep,
              "| Janela (BRT, 09:00) | " + " | ".join(_short(s) for s in monthly) + " |",
              "| Dias | " + " | ".join(f"{s['window']['days']:g}" for s in monthly) + " |",
              "| Portfólios | " + " | ".join(str(len(s["portfolios"])) for s in monthly) + " |",
              "| Vencedoras / perdedoras / inconclusivas | " + " | ".join(
                  f"{sum(p['verdict'] == 'vencedora' for p in s['portfolios'])} / {sum(p['verdict'] == 'perdedora' for p in s['portfolios'])}"
                  f" / {sum(p['verdict'] == 'inconclusiva' for p in s['portfolios'])}" for s in monthly) + " |",
              "| Maior habilidade | " + " | ".join(f"{s['winner']['by_skill']}" for s in monthly) + " |",
              "| Maior PnL | " + " | ".join(f"{s['winner']['by_pnl']}" for s in monthly) + " |",
              "| Pelo veredito | " + " | ".join(f"{s['winner'].get('by_verdict') or 'nenhum'}" for s in monthly) + " |"]
        for book in ("A", "B"):
            cells = []
            for s in monthly:
                b = next((x for x in s.get("realbot") or [] if x.get("book") == book), None)
                cells.append(f"{_fmt(b['pnl_pct'])}% (vs segurar {_fmt(b['vs_hold'], 3)} $)" if b else "–")
            L.append(f"| Bot real livro {book} | " + " | ".join(cells) + " |")
        L += ["", "### Movimento do mercado (retorno do ativo na janela)", "",
              "| Ativo | " + " | ".join(s["run_id"] for s in monthly) + " |", "|---|" + "---:|" * len(monthly)]
        syms = list((monthly[-1].get("assets") or {}).keys())
        for sym in syms:
            L.append(f"| {sym} | " + " | ".join(_fmt((s["assets"].get(sym) or {}).get("ret_pct")) + "%" for s in monthly) + " |")
        L.append("| Memes (média simples) | " + " | ".join(
            _fmt(statistics.mean([(s["assets"][m] or {}).get("ret_pct") or 0 for m in MEMES if m in s["assets"]])) + "%"
            for s in monthly) + " |")
        for key, title in (("pnl", "Top 5 por PnL"), ("skill", "Top 5 por habilidade (excesso ajustado à exposição, US$)")):
            L += ["", f"### {title}", "", "| # | " + " | ".join(s["run_id"] for s in monthly) + " |",
                  "|---:|" + "---|" * len(monthly)]
            tops = [top_by(s["portfolios"], key) for s in monthly]
            for i in range(5):
                cells = []
                for tp in tops:
                    if i < len(tp):
                        x = tp[i]
                        cells.append(f"{x['name']} ({_fmt(x['pnl_pct'])}%)" if key == "pnl"
                                     else f"{x['name']} ({_fmt(x['skill'])} $, {_fmt(x['pnl_pct'])}%)")
                    else:
                        cells.append("–")
                L.append(f"| {i + 1} | " + " | ".join(cells) + " |")
        notes = [f"{s['run_id']}: " + "; ".join(s.get("notes") or []) for s in monthly if s.get("notes")]
        if notes:
            L += ["", "Notas dos runs: " + " · ".join(notes)]

        rows = consistency(monthly)
        nm = len(monthly)
        good = [r for r in rows if r["skill_pos"] >= 2 or r["top_skill"] >= 2 or r["top_pnl"] >= 2]
        good.sort(key=lambda r: (-r["skill_pos"], -r["top_skill"], -r["skill_sum"]))
        L += ["", "## Quem aparece bem em vários meses", "",
              f"Portfólios presentes nos {nm} meses com habilidade > 0 em ≥ 2 meses, ou no top 15 (habilidade ou PnL) em ≥ 2 "
              "meses. Habilidade = excesso ajustado à exposição (o que sobra do PnL depois de descontar o efeito de estar "
              "exposto ao ativo); positivo em vários meses é o sinal que interessa, PnL alto com habilidade negativa é "
              "só beta (o ativo subiu).", "",
              "| Portfólio | Família | Hab. > 0 | Bate B&H | Top 15 hab. | Top 15 PnL | PnL composto % | Hab. somada $ | "
              "PnL por mês % (antigo → recente) | Hab. por mês $ (antigo → recente) |", "|---|---|---:|---:|---:|---:|---:|---:|---|---|"]
        for r in good[:30]:
            L.append(f"| {r['name']}{' ⚠' if r['look_ahead'] else ''} | {r['family']} | {r['skill_pos']}/{nm} | {r['beat_bh']}/{nm} | "
                     f"{r['top_skill']}/{nm} | {r['top_pnl']}/{nm} | {_fmt(r['pnl_comp_pct'])} | {_fmt(r['skill_sum'])} | "
                     + " · ".join(_fmt(x) for x in r["pnl_by_month"]) + " | " + " · ".join(_fmt(x) for x in r["skill_by_month"]) + " |")
        allpos = [r["name"] for r in rows if r["skill_pos"] == nm]
        L += ["", f"Habilidade positiva em TODOS os {nm} meses: " + (", ".join(allpos) if allpos else "nenhum") + ".",
              "⚠ = fork desenhado com dados de 2026-10-01 → 2026-10-06 (só o mês mais recente tem look-ahead; nos meses "
              "anteriores estes forks estão fora da amostra)."]
    for e in longs[:1]:
        try:
            s = json.loads((base / e["run_id"] / "summary.json").read_text())
        except Exception:
            continue
        ch = {}
        try:
            ch = json.loads((base / e["run_id"] / "chart.json").read_text())
        except Exception:
            pass
        ports = s["portfolios"]
        unit = "meses"
        L += ["", f"## {int(round(s['window']['days']))} dias seguidos — {s['run_id']}", "",
              f"Janela {s['window']['start_brt']} → {s['window']['end_brt']}; capital inicial no início da janela; mesma regra "
              "de veredito com consistência mensal (excesso vs B&H positivo em ≥ 4 de 6 blocos de 30 dias) e métricas sobre "
              "a série horária (ver Pressupostos no report.md do run). Gráfico: `chart.json` na pasta do run.", ""]
        bm = ch.get("benchmarks") or {}
        if bm:
            L += ["| Benchmark (1000 no início) | Fim | Retorno |", "|---|---:|---:|"]
            for k, lab in (("sol_bh", "SOL buy & hold"), ("memes_bh", "Cesto das 7 memecoins (peso igual)"), ("usdc", "USDC a 6%/a")):
                if bm.get(k):
                    L.append(f"| {lab} | {bm[k][-1]:.1f} | {_fmt((bm[k][-1] / 1000 - 1) * 100)}% |")
        L += ["", f"Vereditos: {sum(p['verdict'] == 'vencedora' for p in ports)} vencedoras, "
              f"{sum(p['verdict'] == 'perdedora' for p in ports)} perdedoras, {sum(p['verdict'] == 'inconclusiva' for p in ports)} "
              f"inconclusivas. Maior habilidade: **{s['winner']['by_skill']}**; maior PnL: **{s['winner']['by_pnl']}**; pelo "
              f"veredito: **{s['winner'].get('by_verdict') or 'nenhum'}**.", ""]
        wins = [p for p in ports if p["verdict"] == "vencedora"]
        if wins:
            L.append("Vencedoras: " + ", ".join(f"{p['name']} ({_fmt(p['pnl_pct'])}%, hab. {_fmt(p['skill'])} $)" for p in wins) + ".")
            L.append("")
        hdr = ["| # | Portfólio | Família | PnL % | vs B&H $ | Habilidade $ | MDD % | Trades | Meses > B&H | Veredito |",
               "|---:|---|---|---:|---:|---:|---:|---:|---:|---|"]

        def rows_(ps):
            return [f"| {i} | {p['name']} | {p['family']} | {_fmt(p['pnl_pct'])} | {_fmt(p['vs_bh'])} | **{_fmt(p['skill'])}** | "
                    f"{_fmt(p['max_dd_pct'], 2, False)} | {p['trades']} | {p.get('months_beat_bh', '–')}/{len(p.get('months') or []) or 6} | "
                    f"{p['verdict']} |" for i, p in enumerate(ps, 1)]
        L += ["### Top 15 por PnL", "", *hdr, *rows_(sorted(ports, key=lambda p: -(p["pnl_pct"] or -1e18))[:15]), "",
              "### Top 15 por habilidade", "", *hdr, *rows_(sorted(ports, key=lambda p: -_skill_key(p))[:15])]
        if ch.get("monthly"):
            L += ["", "### Vencedores de cada bloco de 30 dias (dentro do run contínuo)", "",
                  "| Mês | Janela | Maior PnL | Maior habilidade | SOL | Memes |", "|---|---|---|---|---:|---:|"]
            for m in ch["monthly"]:
                L.append(f"| {m['month']} | {m['start_brt'][:10]} → {m['end_brt'][:10]} | {m['top_by_pnl']} "
                         f"({_fmt(m.get('top_by_pnl_pct'))}%) | {m['top_by_skill']} ({_fmt(m.get('top_by_skill_usd'))} $) | "
                         f"{_fmt(m['sol_ret'])}% | {_fmt(m['memes_ret'])}% |")
        fams = s.get("families") or []
        if fams:
            L += ["", "### Famílias (6 meses)", "", "| Família | N | PnL % mediano | Habilidade mediana $ | Batem B&H | Melhor |",
                  "|---|---:|---:|---:|---:|---|"]
            for f in fams:
                L.append(f"| {f['family']} | {f['n']} | {_fmt(f['median_pnl_pct'])} | {_fmt(f.get('median_skill'))} | "
                         f"{f['beat_bh']}/{f['n']} | {f['best']} |")
        rb = s.get("realbot") or []
        if rb:
            L += ["", "Bot real: " + "; ".join(f"livro {b['book']} {_fmt(b['pnl_pct'])}% (vs segurar {_fmt(b['vs_hold'], 3)} $, "
                                               f"{b['trades']} trades)" for b in rb) + "."]
        if monthly:
            mnames = {p["name"]: p for p in ports}
            cons = consistency(monthly)
            both = [r for r in cons if r["skill_pos"] >= 2 and (mnames.get(r["name"], {}).get("skill") or 0) > 0]
            L += ["", "Consistentes nos meses E com habilidade positiva nos 6 meses: " +
                  (", ".join(f"{r['name']} ({r['skill_pos']}/{len(monthly)} meses; 6 meses: hab. "
                             f"{_fmt(mnames[r['name']]['skill'])} $, PnL {_fmt(mnames[r['name']]['pnl_pct'])}%)" for r in
                             sorted(both, key=lambda r: -(mnames[r['name']]['skill'] or 0))) or "nenhum") + "."]
    L += ["", "## Como ler", "",
          "- PnL alto num mês de alta das memecoins é quase sempre beta (comprar e segurar); a habilidade separa isso.",
          "- Os runs mensais começam do zero em cada janela; o run de 6 meses é um único caminho contínuo (posições e "
          "cooldowns herdados de um mês para o outro), por isso os blocos mensais dele não coincidem com os runs mensais.",
          "- Retroativo com estados e custos aproximados: serve para ordenar hipóteses, não para provar uma vencedora.", ""]
    return "\n".join(L)


def write_history(base: Path, summary: dict | None = None) -> dict:
    idx = update_index(base, summary)
    _write_atomic(Path(base) / "history.md", history_md(base, idx))
    return idx
