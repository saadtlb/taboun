from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.arena.ranking import build_ranking, parse_ordo_csv, read_results


def repeated_pgn(games: int = 30) -> str:
    documents = []
    for number in range(1, games + 1):
        white, black = (
            ("tabounv1", "tabounv2") if number % 2 else ("tabounv2", "tabounv1")
        )
        documents.append(
            f'''[Event "Ranking test"]
[White "{white}"]
[Black "{black}"]
[Result "1/2-1/2"]

1. e4 e5 1/2-1/2
'''
        )
    return "\n".join(documents)


class RankingTests(unittest.TestCase):
    def test_reads_completed_results_and_rejects_incomplete_games(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pgn = Path(directory) / "games.pgn"
            pgn.write_text(repeated_pgn(4), encoding="utf-8")
            total, stats = read_results(pgn)
            self.assertEqual(total, 4)
            self.assertEqual(stats["tabounv1"], {"wins": 0, "draws": 4, "losses": 0})

            pgn.write_text('[White "a"]\n[Black "b"]\n[Result "*"]\n\n*\n')
            with self.assertRaisesRegex(ValueError, "incomplete"):
                read_results(pgn)

    def test_parses_ordo_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ordo.csv"
            output.write_text(
                '"#","PLAYER","RATING","ERROR","POINTS","PLAYED","(%)","CFS(%)"\n'
                '1,"tabounv2",1020.0,31.5,16.00,30,53.33,88\n'
                '2,"tabounv1",1000.0,"-",14.00,30,46.67,"-"\n',
                encoding="utf-8",
            )
            rows = parse_ordo_csv(output)
        self.assertEqual(rows[0]["bot"], "tabounv2")
        self.assertEqual(rows[0]["error_95"], 31.5)
        self.assertIsNone(rows[1]["error_95"])

    @unittest.skipUnless(
        shutil.which("ordo") or (Path.home() / ".local/bin/ordo").is_file(),
        "Ordo is not installed",
    )
    def test_builds_ranking_with_ordo(self) -> None:
        ordo = Path(shutil.which("ordo") or Path.home() / ".local/bin/ordo")
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            (run_dir / "games.pgn").write_text(repeated_pgn(), encoding="utf-8")
            (run_dir / "manifest.json").write_text(
                json.dumps({"run_id": "test", "status": "complete", "return_code": 0}),
                encoding="utf-8",
            )
            ranking = build_ranking(run_dir, ordo, simulations=1_000, cpus=1)

            self.assertEqual(ranking["total_games"], 30)
            self.assertEqual({row["bot"] for row in ranking["rows"]}, {"tabounv1", "tabounv2"})
            self.assertTrue((run_dir / "ranking.csv").is_file())
            self.assertTrue((run_dir / "cfs.csv").is_file())


if __name__ == "__main__":
    unittest.main()
