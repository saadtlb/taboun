from __future__ import annotations

import io
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

import chess

from src.uci.engine import GoCommand, UciEngine, allocate_time, parse_go, parse_position


REPO_ROOT = Path(__file__).resolve().parents[2]


class ParsingTests(unittest.TestCase):
    def test_position_keeps_move_stack(self) -> None:
        board = parse_position(["startpos", "moves", "e2e4", "e7e5", "g1f3"])
        self.assertEqual([move.uci() for move in board.move_stack], ["e2e4", "e7e5", "g1f3"])

    def test_fen_position(self) -> None:
        board = parse_position(
            "fen 8/8/8/8/8/5k2/8/7K w - - 0 1 moves h1g1".split()
        )
        self.assertEqual(board.peek().uci(), "h1g1")

    def test_go_parser_ignores_unknown_tokens(self) -> None:
        command = parse_go("wtime 60000 btime 50000 winc 600 binc 300 depth 8 unknown".split())
        self.assertEqual(command.white_time_ms, 60000)
        self.assertEqual(command.black_increment_ms, 300)
        self.assertEqual(command.depth, 8)

    def test_time_allocation_keeps_clock_reserve(self) -> None:
        command = GoCommand(white_time_ms=60_000, white_increment_ms=600)
        budget = allocate_time(command, white_to_move=True)
        self.assertGreater(budget, 1.0)
        self.assertLess(budget, 15.0)

    def test_movetime_reserves_protocol_overhead(self) -> None:
        self.assertEqual(allocate_time(GoCommand(movetime_ms=1000), True), 0.975)


class InProcessProtocolTests(unittest.TestCase):
    def test_handshake_and_book_option(self) -> None:
        output = io.StringIO()
        engine = UciEngine("tabounv11", output=output)
        self.assertTrue(engine.handle("uci"))
        engine.handle("setoption name OwnBook value false")
        engine.handle("isready")
        self.assertFalse(engine.bot.use_book)
        self.assertIn("uciok", output.getvalue())
        self.assertIn("readyok", output.getvalue())


class SubprocessProtocolTests(unittest.TestCase):
    def start_engine(self, bot: str) -> subprocess.Popen[str]:
        process = subprocess.Popen(
            [sys.executable, "-m", "src.uci", bot, "--no-book"],
            cwd=REPO_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        os.set_blocking(process.stdout.fileno(), False)
        return process

    def send(self, process: subprocess.Popen[str], command: str) -> None:
        assert process.stdin is not None
        process.stdin.write(command + "\n")
        process.stdin.flush()

    def read_until(self, process: subprocess.Popen[str], prefix: str, timeout: float = 2.0) -> str:
        assert process.stdout is not None
        deadline = time.monotonic() + timeout
        lines = []
        while time.monotonic() < deadline:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.01)
                continue
            line = line.strip()
            lines.append(line)
            if line.startswith(prefix):
                return line
        self.fail(f"did not receive {prefix!r}; received {lines!r}")

    def stop_engine(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            self.send(process, "quit")
            process.wait(timeout=3)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()

    def test_search_returns_legal_move(self) -> None:
        process = self.start_engine("tabounv4")
        try:
            self.send(process, "uci")
            self.read_until(process, "uciok")
            self.send(process, "isready")
            self.read_until(process, "readyok")
            self.send(process, "position startpos moves e2e4 e7e5")
            self.send(process, "go movetime 100")
            bestmove = self.read_until(process, "bestmove")
            move = chess.Move.from_uci(bestmove.split()[1])
            board = chess.Board()
            board.push_uci("e2e4")
            board.push_uci("e7e5")
            self.assertIn(move, board.legal_moves)
        finally:
            self.stop_engine(process)

    def test_stop_interrupts_search(self) -> None:
        process = self.start_engine("tabounv12")
        try:
            self.send(process, "position startpos")
            self.send(process, "go infinite")
            time.sleep(0.05)
            started = time.monotonic()
            self.send(process, "stop")
            self.read_until(process, "bestmove", timeout=1.0)
            self.assertLess(time.monotonic() - started, 1.0)
        finally:
            self.stop_engine(process)


if __name__ == "__main__":
    unittest.main()
