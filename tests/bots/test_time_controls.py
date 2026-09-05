from __future__ import annotations

import time
import unittest
from unittest.mock import patch

import chess

from src.bot import BOT_REGISTRY
from src.bot.tabounv11 import tabounV11
from src.bot.tabounv12 import tabounV12


POSITIONS = {
    "start": (
        chess.STARTING_FEN,
        {
            "tabounv2": "g1h3",
            "tabounv3": "g1f3",
            "tabounv4": "g1f3",
            "tabounv5": "g1f3",
            "tabounv6": "g1f3",
            "tabounv7": "g1f3",
            "tabounv8": "g1f3",
            "tabounv9": "g1f3",
            "tabounv10": "g1f3",
        },
    ),
    "developed": (
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        {
            "tabounv2": "f3g1",
            "tabounv3": "b1c3",
            "tabounv4": "f1b5",
            "tabounv5": "f1b5",
            "tabounv6": "b1c3",
            "tabounv7": "b1c3",
            "tabounv8": "b1c3",
            "tabounv9": "b1c3",
            "tabounv10": "b1c3",
        },
    ),
    "black_to_move": (
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
        {
            "tabounv2": "g8e7",
            "tabounv3": "g8f6",
            "tabounv4": "d8f6",
            "tabounv5": "d8f6",
            "tabounv6": "g8f6",
            "tabounv7": "g8f6",
            "tabounv8": "g8f6",
            "tabounv9": "b8c6",
            "tabounv10": "b8c6",
        },
    ),
}


def board_snapshot(board: chess.Board) -> tuple[str, tuple[chess.Move, ...]]:
    return board.fen(), tuple(board.move_stack)


class HistoricalMoveTests(unittest.TestCase):
    def test_default_moves_are_unchanged(self) -> None:
        for position_name, (fen, expected_moves) in POSITIONS.items():
            for bot_name, expected_move in expected_moves.items():
                with self.subTest(position=position_name, bot=bot_name):
                    board = chess.Board(fen)
                    before = board_snapshot(board)
                    move = BOT_REGISTRY[bot_name]().choose_move(board)
                    self.assertEqual(move.uci(), expected_move)
                    self.assertEqual(board_snapshot(board), before)


class TimedSearchTests(unittest.TestCase):
    def test_v2_to_v9_return_legal_move_without_mutating_board(self) -> None:
        for version in range(2, 10):
            bot_name = f"tabounv{version}"
            with self.subTest(bot=bot_name):
                board = chess.Board()
                before = board_snapshot(board)
                started = time.perf_counter()
                move = BOT_REGISTRY[bot_name](depth=8, time_limit=0.005).choose_move(board)
                elapsed = time.perf_counter() - started

                self.assertIn(move, board.legal_moves)
                self.assertEqual(board_snapshot(board), before)
                self.assertLess(elapsed, 0.25)

    def test_negative_time_limit_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BOT_REGISTRY["tabounv2"](time_limit=-1).choose_move(chess.Board())


class OpeningBookOptionTests(unittest.TestCase):
    def test_v11_can_disable_book(self) -> None:
        with patch("src.bot.tabounv11.choose_book_move") as choose_book_move:
            move = tabounV11(depth=1, time_limit=0.05, use_book=False).choose_move(chess.Board())
        self.assertIn(move, chess.Board().legal_moves)
        choose_book_move.assert_not_called()

    def test_v12_can_disable_book(self) -> None:
        with patch("src.bot.tabounv12.choose_book_move") as choose_book_move:
            move = tabounV12(depth=1, time_limit=0.05, use_book=False).choose_move(chess.Board())
        self.assertIn(move, chess.Board().legal_moves)
        choose_book_move.assert_not_called()

    def test_book_remains_enabled_by_default(self) -> None:
        book_move = chess.Move.from_uci("e2e4")
        with patch("src.bot.tabounv11.choose_book_move", return_value=book_move) as v11_book:
            self.assertEqual(tabounV11().choose_move(chess.Board()), book_move)
        with patch("src.bot.tabounv12.choose_book_move", return_value=book_move) as v12_book:
            self.assertEqual(tabounV12().choose_move(chess.Board()), book_move)
        v11_book.assert_called_once()
        v12_book.assert_called_once()


if __name__ == "__main__":
    unittest.main()
