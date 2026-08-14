"""Build a relative Elo ranking for one completed arena run with Ordo."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "data" / "arena" / "runs"
DEFAULT_ANCHOR = "tabounv1"
DEFAULT_RATING = 1000.0
DEFAULT_SIMULATIONS = 100_000


def read_results(pgn_path: Path) -> tuple[int, dict[str, dict[str, int]]]:
    """Validate every game and return totals indexed by player name."""
    stats: dict[str, dict[str, int]] = {}
    total_games = 0

    with pgn_path.open(encoding="utf-8") as source:
        while game := chess.pgn.read_game(source):
            total_games += 1
            if game.errors:
                raise ValueError(f"game {total_games} contains PGN errors: {game.errors}")

            white = game.headers.get("White", "").strip()
            black = game.headers.get("Black", "").strip()
            result = game.headers.get("Result", "*")
            if not white or not black or white == black:
                raise ValueError(f"game {total_games} has invalid player names")
            if result not in {"1-0", "0-1", "1/2-1/2"}:
                raise ValueError(f"game {total_games} is incomplete: Result={result!r}")

            board = game.board()
            for move in game.mainline_moves():
                if move not in board.legal_moves:
                    raise ValueError(f"game {total_games} contains illegal move {move.uci()}")
                board.push(move)

            for player in (white, black):
                stats.setdefault(player, {"wins": 0, "draws": 0, "losses": 0})
            if result == "1-0":
                stats[white]["wins"] += 1
                stats[black]["losses"] += 1
            elif result == "0-1":
                stats[black]["wins"] += 1
                stats[white]["losses"] += 1
            else:
                stats[white]["draws"] += 1
                stats[black]["draws"] += 1

    if total_games == 0:
        raise ValueError("the PGN contains no games")
    return total_games, stats


def parse_ordo_csv(path: Path) -> list[dict]:
    """Convert Ordo's CSV output to the small schema used by the site."""
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8-sig") as source:
        for raw in csv.DictReader(source):
            error = raw["ERROR"].strip()
            cfs = raw.get("CFS(%)", "-").strip()
            rows.append(
                {
                    "rank": int(raw["#"]),
                    "bot": raw["PLAYER"],
                    "rating": float(raw["RATING"]),
                    "error_95": None if error == "-" else float(error),
                    "points": float(raw["POINTS"]),
                    "played": int(raw["PLAYED"]),
                    "score_percent": float(raw["(%)"]),
                    "cfs_next_percent": None if cfs == "-" else float(cfs),
                }
            )
    if not rows:
        raise ValueError("Ordo produced an empty ranking")
    return rows


def ordo_version(executable: Path) -> str:
    result = subprocess.run(
        [str(executable), "--version"], capture_output=True, text=True, check=False
    )
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else "unknown"


def write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_public_csv(path: Path, rows: list[dict]) -> None:
    columns = [
        "rank",
        "bot",
        "rating",
        "error_95",
        "points",
        "played",
        "score_percent",
        "wins",
        "draws",
        "losses",
        "cfs_next_percent",
    ]
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def build_ranking(
    run_dir: Path,
    ordo: Path,
    *,
    anchor: str = DEFAULT_ANCHOR,
    anchor_rating: float = DEFAULT_RATING,
    simulations: int = DEFAULT_SIMULATIONS,
    cpus: int = 4,
) -> dict:
    """Validate a run, execute Ordo, and write its public ranking files."""
    manifest_path = run_dir / "manifest.json"
    pgn_path = run_dir / "games.pgn"
    if not manifest_path.is_file() or not pgn_path.is_file():
        raise FileNotFoundError("the run needs manifest.json and games.pgn")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or manifest.get("return_code") != 0:
        raise ValueError("ranking requires a successfully completed tournament")
    if "publication" in manifest:
        raise ValueError("a published run is immutable")
    if simulations < 1 or cpus < 1:
        raise ValueError("simulations and cpus must be positive")

    total_games, stats = read_results(pgn_path)
    if anchor not in stats:
        raise ValueError(f"anchor bot {anchor!r} did not play in this run")

    raw_csv = run_dir / "ranking_ordo.csv"
    command = [
        str(ordo.resolve()),
        "--quiet",
        "--anchor",
        anchor,
        "--average",
        str(anchor_rating),
        "--pgn",
        str(pgn_path.resolve()),
        "--output",
        str((run_dir / "ranking.txt").resolve()),
        "--csv",
        str(raw_csv.resolve()),
        "--simulations",
        str(simulations),
        "--confidence",
        "95",
        "--cfs-matrix",
        str((run_dir / "cfs.csv").resolve()),
        "--cfs-show",
        "--cpus",
        str(cpus),
        "--white-auto",
        "--draw-auto",
    ]
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True)
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"Ordo failed with code {completed.returncode}: {details}")

    rows = parse_ordo_csv(raw_csv)
    if {row["bot"] for row in rows} != set(stats):
        raise ValueError("Ordo players do not match the PGN players")
    for row in rows:
        player_stats = stats[row["bot"]]
        row.update(player_stats)
        if row["played"] != sum(player_stats.values()):
            raise ValueError(f"inconsistent game count for {row['bot']}")

    ranking = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": manifest.get("run_id", run_dir.name),
        "total_games": total_games,
        "rating_system": {
            "name": "Ordo",
            "version": ordo_version(ordo),
            "relative": True,
            "anchor_bot": anchor,
            "anchor_rating": anchor_rating,
            "confidence_percent": 95,
            "simulations": simulations,
            "command": command,
        },
        "rows": rows,
    }
    write_public_csv(run_dir / "ranking.csv", rows)
    write_json_atomic(run_dir / "ranking.json", ranking)
    return ranking


def find_ordo(path: Path | None) -> Path:
    if path is not None:
        executable = path
    elif found := shutil.which("ordo"):
        executable = Path(found)
    else:
        executable = Path.home() / ".local" / "bin" / "ordo"
    if not executable.is_file():
        raise FileNotFoundError("Ordo not found; pass --ordo /path/to/ordo")
    return executable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="Directory name below data/arena/runs.")
    parser.add_argument("--ordo", type=Path, help="Path to the Ordo executable.")
    parser.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS)
    parser.add_argument("--cpus", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if "/" in args.run_id or args.run_id in {"", ".", ".."}:
        raise SystemExit("error: run_id must be one directory name")
    try:
        build_ranking(
            RUNS_DIR / args.run_id,
            find_ordo(args.ordo),
            simulations=args.simulations,
            cpus=args.cpus,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
