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
# The anchor fixes the origin of the relative scale. It must be a frozen bot
# that scores points against the pool: tabounv1 plays random moves and, at real
# time controls, loses every game, which leaves its rating undefined.
DEFAULT_ANCHOR = "tabounv2"
DEFAULT_RATING = 1000.0
DEFAULT_SIMULATIONS = 100_000

Game = tuple[str, str, str]  # white, black, result


def read_games(pgn_path: Path) -> list[Game]:
    """Validate every game and return its (white, black, result) triple."""
    games: list[Game] = []

    with pgn_path.open(encoding="utf-8") as source:
        while game := chess.pgn.read_game(source):
            number = len(games) + 1
            if game.errors:
                raise ValueError(f"game {number} contains PGN errors: {game.errors}")

            white = game.headers.get("White", "").strip()
            black = game.headers.get("Black", "").strip()
            result = game.headers.get("Result", "*")
            if not white or not black or white == black:
                raise ValueError(f"game {number} has invalid player names")
            if result not in {"1-0", "0-1", "1/2-1/2"}:
                raise ValueError(f"game {number} is incomplete: Result={result!r}")

            board = game.board()
            for move in game.mainline_moves():
                if move not in board.legal_moves:
                    raise ValueError(f"game {number} contains illegal move {move.uci()}")
                board.push(move)
            games.append((white, black, result))

    if not games:
        raise ValueError("the PGN contains no games")
    return games


def tally(games: list[Game], excluded: frozenset[str] = frozenset()) -> dict[str, dict[str, int]]:
    """Win/draw/loss totals per player, ignoring games with an excluded player."""
    stats: dict[str, dict[str, int]] = {}
    for white, black, result in games:
        if white in excluded or black in excluded:
            continue
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
    return stats


def read_results(pgn_path: Path) -> tuple[int, dict[str, dict[str, int]]]:
    """Validate every game and return totals indexed by player name."""
    games = read_games(pgn_path)
    return len(games), tally(games)


def split_unrated(games: list[Game]) -> tuple[dict[str, dict[str, int]], list[str]]:
    """Separate the players that scored no point from the rated pool.

    A player without a single win or draw has an undefined rating: Ordo
    reports isolated groups and refuses to run. Its games are removed before
    the fit, and the removal repeats until every remaining player has scored.
    """
    unrated: list[str] = []
    stats = tally(games)
    while True:
        pointless = sorted(
            name for name, totals in stats.items()
            if totals["wins"] == 0 and totals["draws"] == 0
        )
        if not pointless:
            return stats, unrated
        unrated.extend(pointless)
        stats = tally(games, frozenset(unrated))


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


def write_results_pgn(path: Path, games: list[Game], excluded: frozenset[str]) -> int:
    """Write headers-only PGN records for the games between rated players."""
    written = 0
    with path.open("w", encoding="utf-8") as target:
        for white, black, result in games:
            if white in excluded or black in excluded:
                continue
            target.write(
                f'[Event "rated games"]\n[White "{white}"]\n[Black "{black}"]\n'
                f'[Result "{result}"]\n\n{result}\n\n'
            )
            written += 1
    return written


def write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


CSV_COLUMNS = [
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


def write_public_csv(path: Path, rows: list[dict], unrated: list[dict]) -> None:
    """Rated rows first; unrated bots follow with empty rank, rating and margin."""
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in CSV_COLUMNS})
        for entry in unrated:
            writer.writerow({column: entry.get(column) for column in CSV_COLUMNS})


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

    games = read_games(pgn_path)
    all_stats = tally(games)
    if anchor not in all_stats:
        raise ValueError(f"anchor bot {anchor!r} did not play in this run")
    rated_stats, unrated = split_unrated(games)
    if anchor in unrated:
        raise ValueError(
            f"anchor bot {anchor!r} scored no point in this run; choose another --anchor"
        )
    if len(rated_stats) < 2:
        raise ValueError("fewer than two players scored a point; nothing to rank")
    excluded = frozenset(unrated)
    rated_games = sum(1 for white, black, _ in games if white not in excluded and black not in excluded)

    raw_csv = run_dir / "ranking_ordo.csv"
    rated_pgn_path = run_dir / "ranking_rated.pgn"
    if unrated:
        # Ordo's own --exclude option crashes together with --cfs-matrix, so the
        # rated games are handed over as a minimal PGN: headers and results only,
        # which is all a rating fit reads. The file stays with the run.
        write_results_pgn(rated_pgn_path, games, excluded)
        ordo_input = rated_pgn_path
    else:
        rated_pgn_path.unlink(missing_ok=True)
        ordo_input = pgn_path
    command = [
        str(ordo.resolve()),
        "--quiet",
        "--anchor",
        anchor,
        "--average",
        str(anchor_rating),
        "--pgn",
        str(ordo_input.resolve()),
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
    if {row["bot"] for row in rows} != set(rated_stats):
        raise ValueError("Ordo players do not match the rated PGN players")
    for row in rows:
        player_stats = rated_stats[row["bot"]]
        row.update(player_stats)
        if row["played"] != sum(player_stats.values()):
            raise ValueError(f"inconsistent game count for {row['bot']}")

    unrated_rows = [
        {
            "bot": name,
            "points": 0.0,
            "played": sum(all_stats[name].values()),
            **all_stats[name],
            "reason": "no points",
        }
        for name in unrated
    ]

    ranking = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": manifest.get("run_id", run_dir.name),
        "total_games": len(games),
        "rated_games": rated_games,
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
        # Bots without a single point cannot be placed on the scale. Their own
        # totals are reported here and their games do not count for anyone.
        "unrated": unrated_rows,
    }
    write_public_csv(run_dir / "ranking.csv", rows, unrated_rows)
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
    parser.add_argument(
        "--anchor",
        default=DEFAULT_ANCHOR,
        help=f"Bot whose rating is fixed to define the scale (default {DEFAULT_ANCHOR}).",
    )
    parser.add_argument("--anchor-rating", type=float, default=DEFAULT_RATING)
    parser.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS)
    parser.add_argument("--cpus", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if "/" in args.run_id or args.run_id in {"", ".", ".."}:
        raise SystemExit("error: run_id must be one directory name")
    try:
        ranking = build_ranking(
            RUNS_DIR / args.run_id,
            find_ordo(args.ordo),
            anchor=args.anchor,
            anchor_rating=args.anchor_rating,
            simulations=args.simulations,
            cpus=args.cpus,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
    for entry in ranking["unrated"]:
        print(f"unrated: {entry['bot']} scored no point in {entry['played']} games")


if __name__ == "__main__":
    main()
