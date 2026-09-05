from __future__ import annotations

import time
import unittest
from unittest.mock import patch

import chess

from src.bot.tabounv12 import tabounV12
from src.bot.tabounv13 import tabounV13
from src.evaluation.fast_evaluation_function import evaluate_fast
from src.evaluation.pesto_evaluation_function import evaluate_pesto


def snapshot(board: chess.Board) -> tuple[str, tuple[chess.Move, ...]]:
    return board.fen(), tuple(board.move_stack)


class TabounV13Tests(unittest.TestCase):
    def test_is_v12_search_with_pesto_evaluation(self) -> None:
        self.assertTrue(issubclass(tabounV13, tabounV12))
        self.assertIs(tabounV13.evaluate, evaluate_pesto)
        self.assertIs(tabounV12.evaluate, evaluate_fast)

    def test_finds_mate_in_one_at_fixed_depth(self) -> None:
        board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
        move = tabounV13(depth=2, time_limit=60.0, use_book=False).choose_move(board)
        self.assertEqual(move.uci(), "h5f7")

    def test_finds_mate_in_two_at_fixed_depth(self) -> None:
        # 1. Ra6 bxa6 2. b7#, a classic: the only winning first move.
        board = chess.Board("kbK5/pp6/1P6/8/8/8/8/R7 w - - 0 1")
        before = snapshot(board)
        move = tabounV13(depth=3, time_limit=60.0, use_book=False).choose_move(board)
        self.assertEqual(move.uci(), "a1a6")
        self.assertEqual(snapshot(board), before)

    def test_book_can_be_disabled_and_is_on_by_default(self) -> None:
        with patch("src.bot.tabounv12.choose_book_move") as book:
            move = tabounV13(depth=1, time_limit=0.05, use_book=False).choose_move(chess.Board())
        self.assertIn(move, chess.Board().legal_moves)
        book.assert_not_called()

        book_move = chess.Move.from_uci("e2e4")
        with patch("src.bot.tabounv12.choose_book_move", return_value=book_move) as book:
            self.assertEqual(tabounV13().choose_move(chess.Board()), book_move)
        book.assert_called_once()

    def test_respects_a_short_budget_and_leaves_the_board_intact(self) -> None:
        board = chess.Board("r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2Q1RK1 b - - 2 11")
        before = snapshot(board)
        started = time.perf_counter()
        move = tabounV13(time_limit=0.02, use_book=False).choose_move(board)
        elapsed = time.perf_counter() - started
        self.assertIn(move, board.legal_moves)
        self.assertEqual(snapshot(board), before)
        self.assertLess(elapsed, 0.15)


if __name__ == "__main__":
    unittest.main()
