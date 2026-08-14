from __future__ import annotations

import unittest

import chess

from src.uci_score import score_after_move


class StaticScoreTests(unittest.TestCase):
    def test_score_uses_the_moving_side_point_of_view(self) -> None:
        white = chess.Board("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
        black = chess.Board("4k3/4q3/8/8/8/8/8/4K3 b - - 0 1")
        self.assertGreater(score_after_move("tabounv2", white, chess.Move.from_uci("e1d1"))[1], 0)
        self.assertGreater(score_after_move("tabounv2", black, chess.Move.from_uci("e8d8"))[1], 0)

    def test_checkmate_is_reported_as_mate(self) -> None:
        board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")
        self.assertEqual(score_after_move("tabounv12", board, chess.Move.from_uci("f7f8")), ("mate", 1))


if __name__ == "__main__":
    unittest.main()
