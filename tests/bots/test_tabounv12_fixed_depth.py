from __future__ import annotations

import unittest

import chess

from src.bot.tabounv12 import tabounV12


# Moves chosen by tabounV12 at depth 3 with the book off, recorded on
# 2026-09-05 from positions of the first 10+0.1 tournament. They pin the
# search itself: a refactor of tabounv12.py must not change one of them.
DEPTH_3_MOVES = [
    ("rnbqk2r/pp3ppp/2p1p3/8/P1pPn3/4PN2/1b3PPP/R2K1BR1 w kq - 0 11", "a1b1"),
    ("r3kbQ1/p4pp1/1p1p1q2/1Np1p3/2P5/4P3/PP1P1PPP/R1B1KB1R b KQq - 0 12", "e8c8"),
    ("r1bqkb1r/pp1ppppp/7n/6n1/1pP5/P1N1PP2/2QP2PP/R1BK1B1R w q - 0 14", "a3b4"),
    ("r1b2n1r/1p1n1Bpp/2pk4/p3N1B1/3PN3/P7/P4PPP/R2QK2R b KQ - 6 15", "d6c7"),
    ("5b1r/pb3p1p/k1N1pP2/2Pp2p1/3P1B2/1Q6/PP3PPP/RN2K2R w KQ - 0 17", "b3a4"),
    ("r1b1kb1r/pp1npppp/2p5/3q4/2pP4/6P1/PP3P1P/R1BK1BNR w kq - 1 11", "f2f3"),
    ("r1bq1rk1/pppn1pbp/5np1/3Pp3/2P3P1/P6P/1Pp1PP2/1RB1KB1R b K - 1 12", "c2b1q"),
    ("rn1qkbn1/p3pp1r/2p3pp/1p1p1P2/2PP4/2NB1N2/PP3PPP/R1BQ1RK1 w - - 2 14", "f5g6"),
]


class TabounV12FixedDepthTests(unittest.TestCase):
    def test_depth_three_moves_are_unchanged(self) -> None:
        for fen, expected in DEPTH_3_MOVES:
            with self.subTest(fen=fen):
                bot = tabounV12(depth=3, time_limit=600.0, use_book=False)
                self.assertEqual(bot.choose_move(chess.Board(fen)).uci(), expected)


if __name__ == "__main__":
    unittest.main()
