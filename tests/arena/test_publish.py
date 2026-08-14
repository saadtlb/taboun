from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.arena.publish import publish_run, sha256_file


PGN = '''[Event "Castling"]
[White "tabounv1"]
[Black "tabounv2"]
[Result "1-0"]
[Termination "adjudication"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. O-O 1-0

[Event "En passant"]
[White "tabounv2"]
[Black "tabounv1"]
[Result "1-0"]
[Termination "adjudication"]

1. e4 a6 2. e5 d5 3. exd6 1-0

[Event "Promotion"]
[SetUp "1"]
[FEN "7k/P7/8/8/8/8/8/7K w - - 0 1"]
[White "tabounv1"]
[Black "tabounv2"]
[Result "1/2-1/2"]
[Termination "adjudication"]

1. a8=Q+ 1/2-1/2
'''


class PublishTests(unittest.TestCase):
    def test_publishes_valid_replay_files_and_latest_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "arena"
            run_dir = root / "runs" / "test-run"
            run_dir.mkdir(parents=True)
            pgn_path = run_dir / "games.pgn"
            pgn_path.write_text(PGN, encoding="utf-8")
            manifest = {
                "run_id": "test-run",
                "status": "complete",
                "return_code": 0,
                "games_sha256": sha256_file(pgn_path),
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            rows = [
                {
                    "bot": bot,
                    "played": 3,
                    "wins": 1,
                    "draws": 1,
                    "losses": 1,
                }
                for bot in ("tabounv1", "tabounv2")
            ]
            (run_dir / "ranking.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": "test-run",
                        "total_games": 3,
                        "rows": rows,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "ranking.csv").write_text("bot,played\ntabounv1,3\n", encoding="utf-8")
            bots_path = Path(directory) / "bots.json"
            bots_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "bots": [{"id": "tabounv1"}, {"id": "tabounv2"}],
                    }
                ),
                encoding="utf-8",
            )

            latest = publish_run("test-run", root, bots_path)

            self.assertEqual(latest["run_id"], "test-run")
            index = json.loads((run_dir / "games/index.json").read_text())
            self.assertEqual(index["total_games"], 3)
            castle = json.loads((run_dir / "games/game-000001.json").read_text())
            en_passant = json.loads((run_dir / "games/game-000002.json").read_text())
            promotion = json.loads((run_dir / "games/game-000003.json").read_text())
            self.assertIn("e1g1", castle["moves_uci"])
            self.assertIn("e5d6", en_passant["moves_uci"])
            self.assertEqual(promotion["moves_uci"], ["a7a8q"])
            self.assertEqual(
                json.loads((root / "latest.json").read_text())["run_id"], "test-run"
            )
            with self.assertRaisesRegex(ValueError, "immutable"):
                publish_run("test-run", root, bots_path)

    def test_latest_is_not_written_when_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "arena"
            run_dir = root / "runs/bad-run"
            run_dir.mkdir(parents=True)
            (run_dir / "games.pgn").write_text(PGN.replace('1/2-1/2\n', '*\n', 1))
            for name in ("manifest.json", "ranking.json"):
                (run_dir / name).write_text("{}")
            (run_dir / "ranking.csv").write_text("x")
            bots = Path(directory) / "bots.json"
            bots.write_text('{}')
            with self.assertRaises(ValueError):
                publish_run("bad-run", root, bots)
            self.assertFalse((root / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()
