from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from src.arena.run_tournament import (
    DEFAULT_OPENINGS,
    REPO_ROOT,
    TournamentConfig,
    build_fastchess_command,
    opening_count,
    select_bots,
)


class TournamentCommandTests(unittest.TestCase):
    def config(self) -> TournamentConfig:
        return TournamentConfig(
            bot_names=("tabounv11", "tabounv12"),
            openings_path=DEFAULT_OPENINGS,
            rounds=10,
            concurrency=4,
            time_control="60+0.6",
            seed=20260814,
            max_moves=200,
            time_margin_ms=100,
            python_executable=Path(sys.executable),
            use_affinity=True,
        )

    def test_command_uses_mirrored_openings_and_disables_books(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            command = build_fastchess_command(
                Path("/usr/local/bin/fastchess"),
                self.config(),
                Path(directory),
                resume=False,
            )

        self.assertIn("-repeat", command)
        self.assertIn("-use-affinity", command)
        self.assertIn("tc=60+0.6", command)
        self.assertIn("args=-m src.uci tabounv11 --no-book", command)
        self.assertIn("args=-m src.uci tabounv12 --no-book", command)
        self.assertIn(f"dir={REPO_ROOT}", command)
        self.assertNotIn("-draw", command)
        self.assertNotIn("-resign", command)

    def test_resume_reads_the_existing_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            command = build_fastchess_command(
                Path("/usr/local/bin/fastchess"),
                self.config(),
                run_dir,
                resume=True,
            )
        self.assertIn(f"file={run_dir / 'fastchess.json'}", command)

    def test_bot_selection_is_validated(self) -> None:
        self.assertEqual(select_bots("tabounv12, tabounv11"), ("tabounv12", "tabounv11"))
        with self.assertRaises(ValueError):
            select_bots("tabounv12")
        with self.assertRaises(ValueError):
            select_bots("tabounv12,unknown")

    def test_official_opening_file_has_25_games(self) -> None:
        self.assertEqual(opening_count(DEFAULT_OPENINGS), 25)


if __name__ == "__main__":
    unittest.main()
