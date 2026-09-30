"""`python -m jev_trader --dry-run --once`, `python -m jev_trader score` e `python -m jev_trader rewrite`.

Sem subcomando, o comportamento é o de sempre: o ciclo, com `--dry-run` e `--once`.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from datetime import date as Date
from pathlib import Path

from jev_trader.config import load_config
from jev_trader.loop import run_cycle



def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "score":
        return score_main(args[1:])
    if args and args[0] == "rewrite":
        return rewrite_main(args[1:])
    return loop_main(args)


def loop_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="jev_trader",
        epilog="Subcomandos: `score` (placar do livro de papel) e `rewrite` (reescrita noturna).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não abre keypair e não envia swap, mesmo com LIVE_TRADING=1",
    )
    parser.add_argument("--once", action="store_true", help="Um ciclo e sai")
    args = parser.parse_args(argv)
    cfg = load_config()
    dry_run = bool(args.dry_run or not cfg.live_trading)
    if args.once:
        run_cycle(cfg, dry_run=dry_run)
        return 0
    while True:
        try:
            run_cycle(cfg, dry_run=dry_run)
            time.sleep(cfg.loop_seconds)
        except KeyboardInterrupt:
            return 0


def score_main(argv: list[str]) -> int:
    from jev_trader.experiment import ExperimentError, load_experiment
    from jev_trader.records import parse_t, read_jsonl
    from jev_trader.score import render_table, scoreboard

    parser = argparse.ArgumentParser(prog="jev_trader score", description="Placar do livro de papel desde o início do run.")
    parser.add_argument("--json", action="store_true", help="Imprime JSON em vez da tabela")
    parser.add_argument(
        "--since",
        help="ISO 8601; limita hit rate, drawdown e contagem de trades. Sem fuso, BRT. O PnL é sempre desde o início.",
    )
    args = parser.parse_args(argv)
    cfg = load_config()
    since = None
    if args.since:
        since = parse_t(args.since)
        if since is None:
            print(f"--since inválido: {args.since}", file=sys.stderr)
            return 2
    try:
        experiment = load_experiment(cfg.experiment_path)
    except ExperimentError as exc:
        print(f"experimento inválido: {exc}", file=sys.stderr)
        return 2
    board = scoreboard(
        read_jsonl(cfg.decisions_path),
        read_jsonl(cfg.paper_trades_path),
        experiment,
        since=since,
    )
    if args.json:
        print(json.dumps(board, ensure_ascii=False, indent=2))
    else:
        print(render_table(board))
    return 0


def rewrite_main(argv: list[str]) -> int:
    from jev_trader import rewrite
    from jev_trader.criteria import load_criteria
    from jev_trader.experiment import ExperimentError, load_experiment
    from jev_trader.records import now_iso, read_jsonl

    parser = argparse.ArgumentParser(
        prog="jev_trader rewrite",
        description="Reescrita noturna: propõe critérios a partir dos erros confiantes; uma pessoa aprova ou rejeita.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--propose", action="store_true", help="Escreve logs/rewrite_proposals/AAAA-MM-DD.json (pending)")
    mode.add_argument("--approve", metavar="ARQUIVO", help="Promove a proposta para config/criteria.json")
    mode.add_argument("--reject", metavar="ARQUIVO", help="Marca a proposta como rejeitada")
    parser.add_argument("--date", help="Dia BRT a rever (AAAA-MM-DD). Sem data: tudo desde o início do run")
    parser.add_argument(
        "--percentile",
        type=float,
        default=rewrite.DEFAULT_PERCENTILE,
        help="Percentil (nearest-rank) das confianças que define 'confiante' (padrão 90)",
    )
    parser.add_argument(
        "--fixed",
        type=float,
        default=rewrite.DEFAULT_FIXED_BAR,
        help="Barra fixa do artigo, só para comparação na auditoria (padrão 0.8)",
    )
    parser.add_argument(
        "--band",
        type=float,
        default=rewrite.DEFAULT_BAND,
        help="Banda do erro a 15 min, em fração (padrão 0.001 = 0.1%%)",
    )
    parser.add_argument("--by", help="Quem aprova ou rejeita (padrão: $USER)")
    args = parser.parse_args(argv)
    cfg = load_config()
    approver = args.by or os.environ.get("USER") or _login_name()

    try:
        if args.approve:
            record = rewrite.approve(
                Path(args.approve),
                criteria_path=cfg.criteria_path,
                approvals_path=cfg.approvals_path,
                approver=approver,
                now_t=now_iso(),
            )
            print(json.dumps(record, ensure_ascii=False))
            return 0
        if args.reject:
            record = rewrite.reject(
                Path(args.reject),
                approvals_path=cfg.approvals_path,
                approver=approver,
                now_t=now_iso(),
            )
            print(json.dumps(record, ensure_ascii=False))
            return 0
        review_date = Date.fromisoformat(args.date) if args.date else None
        experiment = load_experiment(cfg.experiment_path)
        current, source = load_criteria(cfg.criteria_path)
        proposal = rewrite.build_proposal(
            read_jsonl(cfg.decisions_path),
            experiment,
            current,
            source,
            review_date=review_date,
            today=rewrite.today_brt(),
            percentile=args.percentile,
            fixed_bar=args.fixed,
            band=args.band,
            now_t=now_iso(),
        )
        path = rewrite.write_proposal(cfg.proposals_dir, proposal)
    except (rewrite.RewriteError, ExperimentError, ValueError) as exc:
        print(f"rewrite recusado: {exc}", file=sys.stderr)
        return 2
    audit = proposal["audit"]
    summary = {
        "proposal": str(path),
        "status": proposal["status"],
        "changed": proposal["changed"],
        "percentile_cutoff": audit["percentile"]["cutoff"],
        "percentile_mistakes": audit["percentile"]["n_mistakes"],
        "fixed_mistakes": audit["fixed"]["n_mistakes"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def _login_name() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
