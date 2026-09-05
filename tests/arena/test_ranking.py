from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.arena.ranking import (
    build_ranking,
    parse_ordo_csv,
    read_results,
    split_unrated,
)


ORDO = Path(shutil.which("ordo") or Path.home() / ".local/bin/ordo")


def game_pgn(white: str, black: str, result: str) -> str:
    return f'''[Event "Ranking test"]
[White "{white}"]
[Black "{black}"]
[Result "{result}"]

1. e4 e5 {result}
'''


def repeated_pgn(games: int = 30) -> str:
    """tabounv1 and tabounv2 draw every game, colours alternating."""
    documents = []
    for number in range(1, games + 1):
        white, black = ("tabounv1", "tabounv2") if number % 2 else ("tabounv2", "tabounv1")
        documents.append(game_pgn(white, black, "1/2-1/2"))
    return "\n".join(documents)


def pointless_pgn() -> str:
    """tabounv2 and tabounv3 draw 30 games; tabounv1 loses its four games."""
    documents = []
    for number in range(1, 31):
        white, black = ("tabounv2", "tabounv3") if number % 2 else ("tabounv3", "tabounv2")
        documents.append(game_pgn(white, black, "1/2-1/2"))
    documents.append(game_pgn("tabounv1", "tabounv2", "0-1"))
    documents.append(game_pgn("tabounv2", "tabounv1", "1-0"))
    documents.append(game_pgn("tabounv1", "tabounv3", "0-1"))
    documents.append(game_pgn("tabounv3", "tabounv1", "1-0"))
    return "\n".join(documents)


def write_run(run_dir: Path, pgn: str) -> None:
    (run_dir / "games.pgn").write_text(pgn, encoding="utf-8")
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": "test", "status": "complete", "return_code": 0}),
        encoding="utf-8",
    )


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

    def test_splits_pointless_players_until_everyone_has_scored(self) -> None:
        games = [("tabounv2", "tabounv3", "1/2-1/2")] * 4
        games += [("tabounv1", "tabounv2", "0-1"), ("tabounv3", "tabounv1", "1-0")]
        # tabounv4 only scores against tabounv1: once tabounv1 is removed, it
        # has no point left and must leave the rated pool as well.
        games += [("tabounv4", "tabounv1", "1-0"), ("tabounv1", "tabounv4", "0-1")]
        games += [("tabounv4", "tabounv2", "0-1"), ("tabounv3", "tabounv4", "1-0")]

        stats, unrated = split_unrated(games)

        self.assertEqual(unrated, ["tabounv1", "tabounv4"])
        self.assertEqual(set(stats), {"tabounv2", "tabounv3"})
        self.assertEqual(stats["tabounv2"], {"wins": 0, "draws": 4, "losses": 0})

    @unittest.skipUnless(ORDO.is_file(), "Ordo is not installed")
    def test_builds_ranking_with_ordo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            write_run(run_dir, repeated_pgn())
            ranking = build_ranking(run_dir, ORDO, simulations=1_000, cpus=1)

            self.assertEqual(ranking["total_games"], 30)
            self.assertEqual(ranking["rated_games"], 30)
            self.assertEqual({row["bot"] for row in ranking["rows"]}, {"tabounv1", "tabounv2"})
            self.assertEqual(ranking["unrated"], [])
            self.assertEqual(ranking["rating_system"]["anchor_bot"], "tabounv2")
            self.assertTrue((run_dir / "ranking.csv").is_file())
            self.assertTrue((run_dir / "cfs.csv").is_file())
            self.assertFalse((run_dir / "ranking_rated.pgn").exists())

    @unittest.skipUnless(ORDO.is_file(), "Ordo is not installed")
    def test_ordo_lists_pointless_bots_as_unrated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            write_run(run_dir, pointless_pgn())
            ranking = build_ranking(run_dir, ORDO, simulations=1_000, cpus=1)

            self.assertEqual(ranking["total_games"], 34)
            self.assertEqual(ranking["rated_games"], 30)
            self.assertEqual({row["bot"] for row in ranking["rows"]}, {"tabounv2", "tabounv3"})
            for row in ranking["rows"]:
                self.assertEqual(row["played"], 30, row)  # games against tabounv1 do not count
            self.assertEqual(
                ranking["unrated"],
                [
                    {
                        "bot": "tabounv1",
                        "points": 0.0,
                        "played": 4,
                        "wins": 0,
                        "draws": 0,
                        "losses": 4,
                        "reason": "no points",
                    }
                ],
            )
            rated_pgn = (run_dir / "ranking_rated.pgn").read_text(encoding="utf-8")
            self.assertEqual(rated_pgn.count("[Result "), 30)
            self.assertNotIn("tabounv1", rated_pgn)
            csv_lines = (run_dir / "ranking.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(csv_lines), 4)  # header, two rated rows, one unrated row
            self.assertTrue(csv_lines[-1].startswith(",tabounv1,,,0.0,4,"))

            with self.assertRaisesRegex(ValueError, "scored no point"):
                build_ranking(run_dir, ORDO, anchor="tabounv1", simulations=1_000, cpus=1)


if __name__ == "__main__":
    unittest.main()
