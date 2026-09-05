"""Command line entry point: ``python -m src.uci tabounv12 [--no-book]``."""

from __future__ import annotations

import argparse

from src.bot import BOT_REGISTRY
from src.uci.engine import UciEngine, run_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.uci",
        description="Run a Taboun bot as a UCI engine.",
    )
    parser.add_argument("bot", choices=BOT_REGISTRY, help="Bot version to run.")
    parser.add_argument("--no-book", action="store_true", help="Disable the V11/V12 opening book.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_loop(UciEngine(args.bot, own_book=not args.no_book))


if __name__ == "__main__":
    main()
