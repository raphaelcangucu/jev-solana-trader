#!/usr/bin/env python3
"""Recomeçar o laboratório do zero (paper only), arquivando a execução atual sem apagar nada.

Generaliza `reset_to_1000usd.py` (execução de $52 → $1.000). Uso no host, com TODOS os bots parados:

    scripts/stop.sh && funding/stop.sh
    python scripts/maintenance/restart_run.py --archive-name run_1000usd_2026-09-24 --capital 1000 --dry-run
    python scripts/maintenance/restart_run.py --archive-name run_1000usd_2026-09-24 --capital 1000
    scripts/start.sh

- Raiz: `PAPER_LAB_ROOT` ou a pasta do lab (ver bot/paths.py). `--root` sobrepõe.
- Move (nunca apaga) o estado da execução para `archive/<nome>/` com o mesmo layout (`data/`, `logs/`, `reports/`,
  `reviews/`, `funding/`); copia (e mantém vivos) configs, critérios e séries de preço.
- `criteria_v2.json` fica vivo: é o que o sol_bot usa como marca de "revisão do v2 feita" (e são os critérios
  do portfólio v2). Por isso `reviews/` pode ser arquivado por inteiro sem relançar a revisão de arranque.
- Recusa se o destino já tiver conteúdo (a menos de `--allow-existing-dir`, e mesmo assim nunca sobrescreve
  um ficheiro), se houver processos vivos (run/*.pid, funding/run/funding.pid) ou heartbeat recente.
- Atualiza `config.json` (`experiment`, `starting_balances`) e `memecoins.json` (`start_usdt_each`).
  Capital SOL: a mesma fração SOL/USDT da execução anterior, escalada a `--capital` ao preço de referência
  (`--ref-price` ou a última linha de `data/prices.jsonl` com ≤ 10 min); `--keep-balances` mantém as quantidades.
Nunca toca em chaves nem em carteira; `live_trading_enabled` continua false.
"""
from __future__ import annotations
import argparse, json, os, shutil, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # código do lab
from bot.paths import ROOT as DEFAULT_ROOT  # noqa: E402

BRT = timezone(timedelta(hours=-3))

COPY = ["config.json", "params.json", "memecoins.json", "models.json", "criteria_baseline.json", "criteria_v2.json",
        "data/params_overlay.json", "data/prices.jsonl", "data/meme/prices"]
MOVE = ["status.json", "data/meme/portfolios", "data/meme/equity", "data/meme/status.json", "data/rules/equity",
        "data/rules/status.json", "data/lab/equity", "data/lab/portfolios", "data/lab/registry.json",
        "data/lab/registry.lock", "data/lab/status.json", "data/nightly", "archive/logs", "archive/data"]
MOVE_GLOBS = ["data/portfolio_*.json", "data/equity_*.jsonl", "logs/*.jsonl", "reports/*", "reviews/*"]
BOT_LOGS = ["sol_bot", "meme_bot", "rules_bot", "lab_bot", "nightly"]            # movidos
SERVICE_LOGS = ["supervisor", "dashboard", "tunnel", "von_serve", "laya_serve", "poorjev_serve",
                "boot_autostart", "start_laya_boot", "start_poorjev_boot"]         # copiados
FUNDING_MOVE = ["funding/data/state.json", "funding/data/status.json", "funding/logs/archive"]
FUNDING_GLOBS = ["funding/logs/*.jsonl", "funding/reports/*"]
KEEP_DIRS = ["reports", "reviews"]  # recriados vazios (.gitkeep) para quem escreve lá


def pid_alive(pidfile: Path) -> bool:
    try:
        pid = int(pidfile.read_text().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def running_processes(root: Path) -> list[str]:
    out = [f"{f.name} (pid vivo)" for f in sorted((root / "run").glob("*.pid")) if pid_alive(f)]
    fp = root / "funding" / "run" / "funding.pid"
    if fp.exists() and pid_alive(fp):
        out.append("funding/run/funding.pid (pid vivo)")
    for st in (root / "status.json", root / "data" / "meme" / "status.json", root / "data" / "lab" / "status.json"):
        try:
            d = json.loads(st.read_text())
            if not d.get("finished") and time.time() - float(d.get("ts") or 0) < 120:
                out.append(f"{st.relative_to(root)} (heartbeat < 120 s)")
        except Exception:
            pass
    return out


def last_price(root: Path, max_age_s: float = 600):
    p = root / "data" / "prices.jsonl"
    if not p.exists():
        return None
    lines = [l for l in p.read_text().splitlines()[-50:] if l.strip()]
    for l in reversed(lines):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if not r.get("fabricated") and time.time() - float(r.get("ts") or 0) <= max_age_s:
            return float(r["price_usd"]), r.get("ts_brt")
    return None


def plan(root: Path, include_funding: bool) -> tuple[list[Path], list[Path]]:
    copies = [root / f for f in COPY] + [root / "logs" / f"{n}.log" for n in SERVICE_LOGS]
    moves = [root / f for f in MOVE] + [root / "logs" / f"{n}.log" for n in BOT_LOGS]
    for g in MOVE_GLOBS:
        moves += sorted(root.glob(g))
    if include_funding:
        moves += [root / f for f in FUNDING_MOVE]
        for g in FUNDING_GLOBS:
            moves += sorted(root.glob(g))
    moves = [p for p in moves if p.exists() and p.name != ".gitkeep"]
    copies = [p for p in copies if p.exists()]
    return copies, moves


def new_balances(cfg: dict, capital: float, ref_price: float, ref_note: str) -> dict:
    old = dict(cfg["starting_balances"])
    frac = old.get("sol_frac")
    if frac is None:
        sv = float(old["sol"]) * float(old.get("ref_price") or ref_price)
        frac = sv / (sv + float(old["usdt"]))
    frac = float(frac)
    return {"sol": round(capital * frac / ref_price, 9), "usdt": round(capital * (1 - frac), 6), "total_usd": float(capital),
            "ref_price": ref_price, "sol_frac": round(frac, 6),
            "note": f"mesma fração SOL da execução anterior ({frac:.6f}) escalada a ${capital:,.0f} a SOL={ref_price} ({ref_note})",
            "previous": {k: old[k] for k in ("sol", "usdt", "total_usd", "ref_price") if k in old}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive-name", required=True, help="ex.: run_1000usd_2026-09-24 (pasta em archive/)")
    ap.add_argument("--capital", type=float, default=1000.0, help="capital por portfólio em US$ (padrão 1000)")
    ap.add_argument("--root", help="raiz do lab (padrão: PAPER_LAB_ROOT ou a pasta do lab)")
    ap.add_argument("--dry-run", action="store_true", help="só imprime o plano; não mexe em nada")
    ap.add_argument("--ref-price", type=float, help="preço SOL de referência para escalar o capital")
    ap.add_argument("--keep-balances", action="store_true", help="mantém starting_balances (sem reescalar)")
    ap.add_argument("--skip-funding", action="store_true", help="não arquiva o serviço funding/ (p1000, p1000_pons)")
    ap.add_argument("--start-brt", help="marcador de início da nova execução (ISO, padrão: agora)")
    ap.add_argument("--end-brt", help="fim da execução arquivada (ISO, padrão: agora)")
    ap.add_argument("--run-name", help="nome da nova execução (padrão: run_<capital>usd_<data do início>)")
    ap.add_argument("--allow-existing-dir", action="store_true",
                    help="aceita destino já existente (ex.: só com relatórios), mas nunca sobrescreve ficheiros")
    a = ap.parse_args(argv)

    root = Path(a.root).expanduser().resolve() if a.root else DEFAULT_ROOT
    dest = root / "archive" / a.archive_name
    now = datetime.now(BRT).isoformat(timespec="seconds")
    start_brt = a.start_brt or now
    end_brt = a.end_brt or now
    cfg = json.loads((root / "config.json").read_text())
    if cfg.get("live_trading_enabled") or not cfg.get("paper_only", True):
        sys.exit("config.json não está em paper only; recuso.")

    busy = running_processes(root)
    if busy:
        sys.exit("bots ainda a correr (pare scripts/stop.sh e funding/stop.sh): " + "; ".join(busy))
    if dest.exists() and any(dest.iterdir()) and not a.allow_existing_dir:
        sys.exit(f"{dest} já tem conteúdo; recuso sobrescrever (use outro --archive-name)")

    copies, moves = plan(root, not a.skip_funding)
    clash = [p for p in copies + moves if (dest / p.relative_to(root)).exists()]
    if clash:
        sys.exit("destino já contém: " + ", ".join(str(p.relative_to(root)) for p in clash[:10]))

    old_bal = dict(cfg["starting_balances"])
    if a.keep_balances:
        new_bal = dict(old_bal)
    else:
        ref = (a.ref_price, "--ref-price") if a.ref_price else last_price(root)
        if not ref:
            sys.exit("sem preço SOL fresco em data/prices.jsonl; passe --ref-price ou --keep-balances")
        new_bal = new_balances(cfg, a.capital, float(ref[0]), str(ref[1]))
    run_name = a.run_name or f"run_{a.capital:.0f}usd_{start_brt[:10]}"
    exp_old = json.loads(json.dumps(cfg.get("experiment") or {}))  # cópia: exp é alterado mais abaixo
    prev = [r for r in exp_old.get("previous_runs") or [] if r.get("name") != a.archive_name]
    prev.append({"name": a.archive_name, "start_brt": exp_old.get("day1_start_brt"), "end_brt": end_brt,
                 "capital_usd_each": exp_old.get("capital_usd_each"), "archive": f"archive/{a.archive_name}"})

    print(json.dumps({"root": str(root), "dest": str(dest), "dry_run": a.dry_run,
                      "copy": [str(p.relative_to(root)) for p in copies],
                      "move": [str(p.relative_to(root)) for p in moves],
                      "new_run": run_name, "start_brt": start_brt, "starting_balances": new_bal,
                      "previous_runs": prev}, indent=1, ensure_ascii=False))
    if a.dry_run:
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    copied, moved = [], []
    for p in copies:
        t = dest / p.relative_to(root); t.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if p.is_dir() else shutil.copy2)(str(p), str(t)); copied.append(str(p.relative_to(root)))
    for p in moves:
        t = dest / p.relative_to(root); t.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(t)); moved.append(str(p.relative_to(root)))
    for d in KEEP_DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        (root / d / ".gitkeep").touch()

    cfg["starting_balances"] = new_bal
    exp = cfg.setdefault("experiment", {})
    exp.update({"run_name": run_name, "mode": "paper", "day1_start_brt": start_brt, "capital_usd_each": float(a.capital),
                "start_marker_note": ("Marcador do recomeço do zero (restart_run.py). Cada portfólio grava o próprio início "
                                      "(created_ts/started_brt) no primeiro ciclo; analytics usa esse valor."),
                "previous_runs": prev})
    (root / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    mp = root / "memecoins.json"
    if mp.exists():
        mc = json.loads(mp.read_text())
        if float(mc.get("start_usdt_each") or 0) != float(a.capital):  # só regista o anterior quando muda
            mc["previous_start_usdt_each"] = mc.get("start_usdt_each"); mc["start_usdt_each"] = float(a.capital)
            mp.write_text(json.dumps(mc, indent=2) + "\n")

    readme = dest / ("README_restart.md" if (dest / "README.md").exists() else "README.md")
    readme.write_text(f"""# Execução arquivada: {a.archive_name}

Execução paper do laboratório, arquivada (movida, nunca apagada) quando o experimento recomeçou do zero como `{run_name}`.

- Início (BRT): {exp_old.get('day1_start_brt')}
- Fim / arquivada em (BRT): {end_brt}
- Capital por portfólio: US$ {exp_old.get('capital_usd_each')}
- Paper only: sem trades reais, sem chaves; a carteira real nunca foi tocada.
- Layout espelha a árvore viva (`data/`, `logs/`, `reports/`, `reviews/`{', `funding/`' if not a.skip_funding else ''}); `archive/logs`, `archive/data` = logs rotacionados desta execução.
- Copiado (continua vivo na nova execução): configs, critérios, `data/params_overlay.json`, `data/prices.jsonl` e `data/meme/prices/` (só dados de mercado).
- `criteria_v2.json` continua vivo (critérios do portfólio v2 e marca de "revisão de arranque feita").
- Movidos: {len(moved)} caminhos; copiados: {len(copied)} (lista completa em `manifest.json`).
""")
    man = dest / ("manifest.json" if not (dest / "manifest.json").exists() else "manifest_restart.json")
    man.write_text(json.dumps({"moved": moved, "copied": copied, "old_starting_balances": old_bal,
                               "new_starting_balances": new_bal, "end_brt": end_brt, "new_run": run_name,
                               "start_brt": start_brt}, indent=1, ensure_ascii=False))
    print(json.dumps({"dest": str(dest), "moved": len(moved), "copied": len(copied), "new_run": run_name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
