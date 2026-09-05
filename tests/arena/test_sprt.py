from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from src.arena.run_sprt import build_sprt_command, read_decision


class SprtCommandTests(unittest.TestCase):
    def test_command_is_paired_bounded_and_uses_equal_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = build_sprt_command(
                Path("/usr/local/bin/fastchess"),
                candidate="tabounv12",
                baseline="tabounv11",
                python=Path(sys.executable),
                openings=root / "openings.pgn",
                run_dir=root,
                time_control="60+0.6",
                concurrency=4,
                max_pairs=500,
                seed=20260814,
                elo0=0,
                elo1=5,
                alpha=0.05,
                beta=0.05,
                max_moves=200,
                resume=False,
            )
        self.assertEqual(command.count("-engine"), 2)
        self.assertIn("args=-m src.uci tabounv12 --no-book", command)
        self.assertIn("args=-m src.uci tabounv11 --no-book", command)
        self.assertIn("tc=60+0.6", command)
        self.assertIn("-repeat", command)
        self.assertIn("-sprt", command)
        self.assertIn("model=normalized", command)
        self.assertIn("500", command)
        self.assertNotIn("-draw", command)
        self.assertNotIn("-resign", command)

    def test_decision_is_explicit(self) -> None:
        self.assertEqual(read_decision(["SPRT: H1 was accepted"]), "h1_accepted")
        self.assertEqual(read_decision(["SPRT: H0 was accepted"]), "h0_accepted")
        self.assertEqual(read_decision(["SPRT still running"]), "inconclusive_at_limit")


if __name__ == "__main__":
    unittest.main()
