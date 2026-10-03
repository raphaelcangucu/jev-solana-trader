#!/usr/bin/env python3
"""Resumo curto do run em paper (saúde, placar desde o início e na janela recente, bot real).

Só leitura sobre PAPER_LAB_ROOT; escreve apenas reports/summary_latest.md.
  python scripts/summary.py [--hours 4]
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from bot.paths import ROOT  # noqa: E402
from bot.lib import BRT, brt_iso  # noqa: E402
from bot import analytics as A  # noqa: E402

PROCS = ["supervisor", "von", "laya", "poorjev", "sol", "meme", "rules", "lab", "nightly", "dashboard"]
STATUS = {"sol": "status.json", "meme": "data/meme/status.json", "rules": "data/rules/status.json",
          "lab": "data/lab/status.json", "nightly": "data/nightly/status.json"}


def _alive(name: str) -> bool:
    try:
        os.kill(int((ROOT / "run" / f"{name}.pid").read_text().strip()), 0)
        return True
    except (OSError, ValueError):
        return False


def _restarts_since(t0: float) -> dict[str, int]:
    out: dict[str, int] = {}
    log = ROOT / "logs" / "supervisor.log"
    if not log.exists():
        return out
    for line in log.read_text(errors="replace").splitlines()[-4000:]:
        m = re.match(r"(\S+) starting (\w+)", line)
        if m:
            try:
                if datetime.fromisoformat(m.group(1)).timestamp() >= t0:
                    out[m.group(2)] = out.get(m.group(2), 0) + 1
            except ValueError:
                pass
    return out


def _real_bot() -> dict | None:
    repo = LAB.parents[1]
    py = os.environ.get("TRADER_PYTHON") or str(repo / ".venv" / "bin" / "python")
    try:
        r = subprocess.run([py, "-m", "jev_trader", "score", "--json"], cwd=repo, capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 else {"erro": (r.stderr or r.stdout)[-300:]}
    except Exception as ex:  # resumo nunca falha por causa do bot real
        return {"erro": str(ex)[:300]}


def _row(s: dict) -> str:
    return (f"| {s['name']} | {A.fmt(s.get('pnl_pct'), 2, True)}% | {A.fmt(s.get('pnl'), 2, True)} | "
            f"{A.fmt(s.get('exposure_pct'), 0)}% | {A.fmt(s.get('ex_exposure'), 2, True)} | {s.get('trades', 0)} ({s.get('buys', 0)}/{s.get('sells', 0)}) |")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--hours", type=float, default=4.0); ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    now = time.time(); t_win = now - a.hours * 3600
    L = [f"# Resumo do run paper — {brt_iso()[:16].replace('T', ' ')} BRT", ""]

    # 1) saúde
    down = [p for p in PROCS if not _alive(p)]
    st_lines = []
    for k, f in STATUS.items():
        try:
            d = json.loads((ROOT / f).read_text()); age = now - float(d.get("ts") or 0)
            st_lines.append(f"{k} {int(age)}s/{d.get('errors', 0)} erros" + (" **PARADO?**" if age > 300 else ""))
        except Exception:
            st_lines.append(f"{k} sem status")
    rs = _restarts_since(t_win)
    free = shutil.disk_usage(str(ROOT)).free / 1e9
    L += ["## Saúde", "",
          f"- Processos: {'todos ativos' if not down else 'PARADOS: ' + ', '.join(down)} · heartbeat/erros: " + "; ".join(st_lines),
          f"- Reinícios nas últimas {a.hours:g} h: {', '.join(f'{k}×{v}' for k, v in rs.items()) or 'nenhum'} · disco livre {free:.0f} GB", ""]

    # 2) placar
    cat, _ = A.catalog(); tb = A.load_trades()
    tot, win = [], []
    for n, m in cat.items():
        try:
            s = A.window_stats(m, tb, 0, now)
            if not s.get("empty"):
                tot.append(s)
            w = A.window_stats(m, tb, t_win, now)
            if not w.get("empty"):
                win.append(w)
        except Exception:
            continue
    start = min((m["start_ts"] for m in cat.values() if m.get("start_ts")), default=now)
    hdr = ["| Portfólio | PnL % | PnL US$ | Exposição | Excesso aj. exposição US$ | Trades (C/V) |", "|---|---:|---:|---:|---:|---|"]
    tot.sort(key=lambda s: s.get("pnl_pct") or 0, reverse=True)
    by_ex = sorted([s for s in tot if s.get("ex_exposure") is not None], key=lambda s: s["ex_exposure"], reverse=True)
    L += [f"## Desde o início ({(now - start) / 86400:.1f} dias, {len(tot)} portfólios)", "",
          f"Melhores por PnL:", ""] + hdr + [_row(s) for s in tot[:a.top]]
    L += ["", "Piores por PnL:", ""] + hdr + [_row(s) for s in tot[-a.top:][::-1]]
    L += ["", "Melhor seleção (excesso ajustado à exposição, o que não é só beta):", ""] + hdr + [_row(s) for s in by_ex[:a.top]]
    ntr = sum(s.get("trades", 0) for s in win)
    active = sorted([s for s in win if s.get("trades")], key=lambda s: s["trades"], reverse=True)[:a.top]
    L += ["", f"## Últimas {a.hours:g} h", "", f"- Trades: {ntr} em {sum(1 for s in win if s.get('trades'))} portfólios"
          + (f"; mais ativos: {', '.join(f'{s['name']} ({s['trades']})' for s in active)}" if active else "")]
    try:
        v = json.loads((ROOT / "data" / "nightly" / "verdicts.json").read_text())["verdicts"]
        cnt: dict[str, int] = {}
        for x in v.values():
            cnt[x["verdict"]] = cnt.get(x["verdict"], 0) + 1
        L.append(f"- Vereditos: {', '.join(f'{k} {c}' for k, c in sorted(cnt.items()))} (mínimos: ≥30 RT e ≥21 dias)")
    except Exception:
        pass

    # 2b) forks: cada um contra o pai, na mesma janela (desde a criação do fork)
    forks = [m for m in cat.values() if m.get("parent")]
    if forks:
        L += ["", f"## Forks ({len(forks)})", "",
              "| Fork | O que mudou | Idade | PnL fork − pai (pp) | Habilidade fork − pai US$ | Trades fork/pai |", "|---|---|---:|---:|---:|---|"]
        for m in sorted(forks, key=lambda m: m["start_ts"]):
            par = cat.get(m["parent"])
            try:
                f = A.window_stats(m, tb, m["start_ts"], now)
                p = A.window_stats(par, tb, m["start_ts"], now) if par else {"empty": True}
            except Exception:
                continue
            if f.get("empty") or p.get("empty"):
                L.append(f"| {m['name']} | {json.dumps(m.get('params_diff'), ensure_ascii=False)[:60]} | {(now - m['start_ts']) / 3600:.0f} h | – | – | – |")
                continue
            dsk = (f.get("ex_exposure") or 0) - (p.get("ex_exposure") or 0)
            L.append(f"| {m['name']} | {json.dumps(m.get('params_diff'), ensure_ascii=False)[:60]} | {(now - m['start_ts']) / 3600:.0f} h | "
                     f"{f['pnl_pct'] - p['pnl_pct']:+.2f} | {dsk:+.2f} | {f.get('trades', 0)}/{p.get('trades', 0)} |")

    # 3) bot real em paper
    rb = _real_bot()
    L += ["", "## Bot real (paper, livro da carteira)", ""]
    if rb and "erro" not in rb:
        pb, ph, hr, dd, tr = rb["paper_book"], rb["pnl_vs_hold"], rb["hit_rate"], rb["drawdown"], rb["trades"]
        L += [f"- Livro de papel: {pb['sol']:.6f} SOL + {pb['usdt']:.2f} USDT = US$ {ph['paper_value_usd']:.2f} (SOL {rb['last_px']})",
              f"- PnL contra segurar o livro: {ph['usd']:+.2f} US$ ({ph['pct']:+.2f}%)",
              f"- Hit rate a 15 min: {hr['hits']}/{hr['resolved']}" + (f" ({hr['rate'] * 100:.0f}%)" if hr.get("rate") is not None else ""),
              f"- Max drawdown: {dd['pct']:.2f}% · trades: {tr['total']} ({tr['buy']} compras / {tr['sell']} vendas)"]
    else:
        L.append(f"- indisponível: {(rb or {}).get('erro')}")
    L.append("")
    text = "\n".join(L)
    out = ROOT / "reports" / "summary_latest.md"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
