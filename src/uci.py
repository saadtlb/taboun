"""Small UCI adapter for every bot in :mod:`bot`.

The adapter owns protocol parsing and clock allocation. Bots keep their simple
``choose_move(board)`` API and only receive a per-move budget.
"""

from __future__ import annotations

import argparse
import inspect
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import chess


SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bot import BOT_REGISTRY  # noqa: E402


MOVE_OVERHEAD_MS = 25
DEFAULT_MOVES_TO_GO = 30
MAX_SHARE_OF_CLOCK = 0.25
ANALYSIS_LIMIT_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class GoCommand:
    movetime_ms: int | None = None
    white_time_ms: int | None = None
    black_time_ms: int | None = None
    white_increment_ms: int = 0
    black_increment_ms: int = 0
    moves_to_go: int | None = None
    depth: int | None = None
    infinite: bool = False


def parse_go(tokens: list[str]) -> GoCommand:
    values: dict[str, int | bool | None] = {
        "movetime_ms": None,
        "white_time_ms": None,
        "black_time_ms": None,
        "white_increment_ms": 0,
        "black_increment_ms": 0,
        "moves_to_go": None,
        "depth": None,
        "infinite": False,
    }
    names = {
        "movetime": "movetime_ms",
        "wtime": "white_time_ms",
        "btime": "black_time_ms",
        "winc": "white_increment_ms",
        "binc": "black_increment_ms",
        "movestogo": "moves_to_go",
        "depth": "depth",
    }

    index = 0
    while index < len(tokens):
        token = tokens[index].lower()
        if token == "infinite":
            values["infinite"] = True
            index += 1
            continue
        key = names.get(token)
        if key is None or index + 1 >= len(tokens):
            index += 1
            continue
        try:
            values[key] = max(0, int(tokens[index + 1]))
        except ValueError:
            pass
        index += 2

    return GoCommand(**values)


def allocate_time(command: GoCommand, white_to_move: bool) -> float:
    """Return a safe per-move budget in seconds."""
    if command.movetime_ms is not None:
        return max(0.001, (command.movetime_ms - MOVE_OVERHEAD_MS) / 1000)

    remaining_ms = command.white_time_ms if white_to_move else command.black_time_ms
    increment_ms = command.white_increment_ms if white_to_move else command.black_increment_ms
    if remaining_ms is None:
        return float(ANALYSIS_LIMIT_SECONDS)

    usable_ms = max(1, remaining_ms - MOVE_OVERHEAD_MS)
    moves_to_go = max(1, command.moves_to_go or DEFAULT_MOVES_TO_GO)
    target_ms = usable_ms / moves_to_go + increment_ms * 0.8
    maximum_ms = min(usable_ms, max(1, usable_ms * MAX_SHARE_OF_CLOCK))
    return max(0.001, min(target_ms, maximum_ms) / 1000)


def parse_position(tokens: list[str]) -> chess.Board:
    if not tokens:
        raise ValueError("position requires startpos or fen")

    if tokens[0] == "startpos":
        board = chess.Board()
        index = 1
    elif tokens[0] == "fen":
        try:
            moves_index = tokens.index("moves", 1)
        except ValueError:
            moves_index = len(tokens)
        fen = " ".join(tokens[1:moves_index])
        board = chess.Board(fen)
        index = moves_index
    else:
        raise ValueError("position requires startpos or fen")

    if index < len(tokens) and tokens[index] == "moves":
        index += 1
    for raw_move in tokens[index:]:
        move = chess.Move.from_uci(raw_move)
        if move not in board.legal_moves:
            raise ValueError(f"illegal move in position: {raw_move}")
        board.push(move)
    return board


class UciEngine:
    def __init__(
        self,
        bot_name: str,
        *,
        own_book: bool = True,
        output: TextIO = sys.stdout,
    ) -> None:
        if bot_name not in BOT_REGISTRY:
            available = ", ".join(BOT_REGISTRY)
            raise ValueError(f"unknown bot {bot_name!r}; available: {available}")

        self.bot_name = bot_name
        self.bot_class = BOT_REGISTRY[bot_name]
        self.own_book = own_book
        self.output = output
        self.board = chess.Board()
        self.stop_event = threading.Event()
        self.output_lock = threading.Lock()
        self.search_thread: threading.Thread | None = None
        self.search_number = 0
        self.bot = self._new_bot()
        self.original_depth = getattr(self.bot, "depth", None)

    def _new_bot(self):
        parameters = inspect.signature(self.bot_class).parameters
        kwargs = {}
        if "stop_event" in parameters:
            kwargs["stop_event"] = self.stop_event
        if "use_book" in parameters:
            kwargs["use_book"] = self.own_book
        return self.bot_class(**kwargs)

    def send(self, line: str) -> None:
        with self.output_lock:
            print(line, file=self.output, flush=True)

    def reset(self) -> None:
        self.stop()
        self._join_search()
        self.board = chess.Board()
        self.stop_event.clear()
        self.bot = self._new_bot()
        self.original_depth = getattr(self.bot, "depth", None)

    def set_own_book(self, enabled: bool) -> None:
        self.own_book = enabled
        if hasattr(self.bot, "use_book"):
            self.bot.use_book = enabled

    def set_position(self, tokens: list[str]) -> None:
        self.board = parse_position(tokens)

    def start_search(self, command: GoCommand) -> None:
        self.stop()
        self._join_search()
        self.stop_event.clear()
        self.search_number += 1
        search_number = self.search_number
        board = self.board.copy(stack=True)
        budget = allocate_time(command, board.turn == chess.WHITE)

        if hasattr(self.bot, "time_limit"):
            self.bot.time_limit = budget
        if self.original_depth is not None:
            requested = command.depth or self.original_depth
            self.bot.depth = min(self.original_depth, max(1, requested))

        thread = threading.Thread(
            target=self._search,
            args=(search_number, board),
            name=f"uci-{self.bot_name}-search",
            daemon=True,
        )
        self.search_thread = thread
        thread.start()

    def _search(self, search_number: int, board: chess.Board) -> None:
        started = time.perf_counter()
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            self.send("bestmove 0000")
            return

        best_move = legal_moves[0]
        try:
            best_move = self.bot.choose_move(board)
        except Exception as error:  # UCI must still answer every go.
            self.send(f"info string search error: {type(error).__name__}: {error}")

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if search_number != self.search_number:
            return
        self.send(f"info time {elapsed_ms}")
        self.send(f"bestmove {best_move.uci()}")

    def stop(self) -> None:
        if self.search_thread is not None and self.search_thread.is_alive():
            self.stop_event.set()

    def _join_search(self) -> None:
        if self.search_thread is None:
            return
        self.search_thread.join(timeout=2.0)
        if self.search_thread.is_alive():
            self.search_number += 1
        self.search_thread = None

    def handle(self, line: str) -> bool:
        tokens = line.strip().split()
        if not tokens:
            return True

        command = tokens[0].lower()
        args = tokens[1:]

        if command == "uci":
            self.send(f"id name Taboun {self.bot_name}")
            self.send("id author saadtlb")
            self.send(f"option name OwnBook type check default {'true' if self.own_book else 'false'}")
            self.send("uciok")
        elif command == "isready":
            self.send("readyok")
        elif command == "setoption":
            self._handle_setoption(args)
        elif command == "ucinewgame":
            self.reset()
        elif command == "position":
            try:
                self.set_position(args)
            except (ValueError, chess.InvalidMoveError) as error:
                self.send(f"info string position error: {error}")
        elif command == "go":
            self.start_search(parse_go(args))
        elif command == "stop":
            self.stop()
        elif command == "quit":
            self.stop()
            self._join_search()
            return False
        return True

    def _handle_setoption(self, tokens: list[str]) -> None:
        lowered = [token.lower() for token in tokens]
        if "name" not in lowered:
            return
        name_index = lowered.index("name") + 1
        try:
            value_index = lowered.index("value", name_index)
        except ValueError:
            value_index = len(tokens)
        name = " ".join(tokens[name_index:value_index]).strip().lower()
        value = " ".join(tokens[value_index + 1 :]).strip().lower()
        if name == "ownbook":
            self.set_own_book(value not in {"false", "0", "off", "no"})


def run_loop(engine: UciEngine, input_stream: TextIO = sys.stdin) -> None:
    for line in input_stream:
        if not engine.handle(line):
            break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Taboun bot as a UCI engine.")
    parser.add_argument("bot", choices=BOT_REGISTRY, help="Bot version to run.")
    parser.add_argument("--no-book", action="store_true", help="Disable the V11/V12 opening book.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_loop(UciEngine(args.bot, own_book=not args.no_book))


if __name__ == "__main__":
    main()
