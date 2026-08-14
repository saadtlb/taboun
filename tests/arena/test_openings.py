from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import chess
import chess.pgn

from src.arena.build_openings import DEFAULT_BOOK, build_opening_suite


def read_games(path: Path) -> list[chess.pgn.Game]:
    games = []
    with path.open(encoding="utf-8") as source:
        while (game := chess.pgn.read_game(source)) is not None:
            games.append(game)
    return games


class OpeningSuiteTests(unittest.TestCase):
    def test_suite_is_deterministic_legal_and_unique(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first_pgn = Path(first_dir) / "openings.pgn"
            first_json = Path(first_dir) / "openings.json"
            second_pgn = Path(second_dir) / "openings.pgn"
            second_json = Path(second_dir) / "openings.json"

            first = build_opening_suite(
                DEFAULT_BOOK,
                first_pgn,
                first_json,
                count=10,
                seed=42,
                min_plies=6,
                max_plies=10,
            )
            second = build_opening_suite(
                DEFAULT_BOOK,
                second_pgn,
                second_json,
                count=10,
                seed=42,
                min_plies=6,
                max_plies=10,
            )

            self.assertEqual(first, second)
            self.assertEqual(first_pgn.read_bytes(), second_pgn.read_bytes())
            self.assertEqual(first_json.read_bytes(), second_json.read_bytes())

            games = read_games(first_pgn)
            lines = [tuple(move.uci() for move in game.mainline_moves()) for game in games]
            self.assertEqual(len(lines), 10)
            self.assertEqual(len(set(lines)), 10)
            self.assertTrue(all(6 <= len(line) <= 10 for line in lines))
            self.assertEqual(json.loads(first_json.read_text())["count"], 10)

    def test_invalid_depth_range_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build_opening_suite(
                    DEFAULT_BOOK,
                    Path(directory) / "openings.pgn",
                    Path(directory) / "openings.json",
                    count=1,
                    seed=1,
                    min_plies=10,
                    max_plies=6,
                )


if __name__ == "__main__":
    unittest.main()
