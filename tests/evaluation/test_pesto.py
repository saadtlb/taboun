from __future__ import annotations

import unittest

import chess

from src.evaluation.pesto_evaluation_function import MAX_PHASE, evaluate_pesto, game_phase


MIDDLEGAMES = [
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2Q1RK1 b - - 2 11",
    "8/pp3k2/2p2np1/3p1p2/3P1P1P/2P2N2/PP4K1/8 w - - 0 32",
    "r3k2r/ppqn1pp1/2pbpn1p/3p4/3P4/2N1PNP1/PPQ2PBP/R4RK1 w kq - 0 13",
]


class PestoTests(unittest.TestCase):
    def test_start_position_is_balanced_and_fully_middlegame(self) -> None:
        board = chess.Board()
        self.assertEqual(evaluate_pesto(board), 0)
        self.assertEqual(game_phase(board), MAX_PHASE)

    def test_mirrored_position_has_the_opposite_score(self) -> None:
        for fen in MIDDLEGAMES:
            with self.subTest(fen=fen):
                board = chess.Board(fen)
                self.assertEqual(evaluate_pesto(board.mirror()), -evaluate_pesto(board))

    def test_tables_are_read_from_the_right_end(self) -> None:
        # A white pawn on the seventh rank is worth far more than on the second;
        # a wrong vertical flip would invert this.
        near = chess.Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
        far = chess.Board("4k3/4P3/8/8/8/8/8/4K3 w - - 0 1")
        self.assertGreater(evaluate_pesto(far) - evaluate_pesto(near), 100)
        # Same for Black, seen from White's point of view.
        near_black = chess.Board("4k3/4p3/8/8/8/8/8/4K3 w - - 0 1")
        far_black = chess.Board("4k3/8/8/8/8/8/4p3/4K3 w - - 0 1")
        self.assertLess(evaluate_pesto(far_black) - evaluate_pesto(near_black), -100)

    def test_phase_follows_the_remaining_material(self) -> None:
        self.assertEqual(game_phase(chess.Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")), 0)
        self.assertEqual(game_phase(chess.Board("4k3/8/8/8/8/8/8/R3K2R w - - 0 1")), 4)
        promoted = chess.Board("QQQQkQQQ/8/8/8/8/8/8/RNBQKBNR w - - 0 1")
        self.assertEqual(game_phase(promoted), MAX_PHASE)

    def test_extra_material_scores_for_its_owner(self) -> None:
        self.assertGreater(evaluate_pesto(chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")), 400)
        self.assertLess(evaluate_pesto(chess.Board("4k3/8/8/8/8/8/8/3qK3 w - - 0 1")), -800)


if __name__ == "__main__":
    unittest.main()
