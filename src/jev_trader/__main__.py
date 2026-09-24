"""`python -m jev_trader --dry-run --once`"""

from __future__ import annotations

import argparse
import time

from jev_trader.config import load_config
from jev_trader.loop import run_cycle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jev_trader")
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


if __name__ == "__main__":
    raise SystemExit(main())
