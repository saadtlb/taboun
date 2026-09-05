"""Validate an arena run and expose it through an atomic latest.json pointer."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data" / "arena"
DEFAULT_BOTS_PATH = REPO_ROOT / "data" / "bots.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_bots(path: Path, participants: set[str]) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("bots"), list):
        raise ValueError("bots.json has an unsupported schema")
    bot_ids = {bot.get("id") for bot in document["bots"]}
    missing = participants - bot_ids
    if missing:
        raise ValueError(f"bots.json is missing: {', '.join(sorted(missing))}")
    return document


def export_games(pgn_path: Path, output_dir: Path, run_id: str) -> tuple[dict, set[str]]:
    """Validate a PGN and create one compact, replayable JSON file per game."""
    summaries: list[dict] = []
    participants: set[str] = set()
    output_dir.mkdir()

    with pgn_path.open(encoding="utf-8") as source:
        while game := chess.pgn.read_game(source):
            number = len(summaries) + 1
            game_id = f"game-{number:06d}"
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
            initial_fen = board.fen()
            moves_uci: list[str] = []
            moves_san: list[str] = []
            for move in game.mainline_moves():
                if move not in board.legal_moves:
                    raise ValueError(f"game {number} contains illegal move {move.uci()}")
                moves_uci.append(move.uci())
                moves_san.append(board.san(move))
                board.push(move)

            headers = {
                key: value
                for key, value in game.headers.items()
                if key
                in {
                    "Event",
                    "Site",
                    "Date",
                    "Round",
                    "White",
                    "Black",
                    "Result",
                    "FEN",
                    "SetUp",
                    "ECO",
                    "Opening",
                    "Variation",
                    "Termination",
                    "GameDuration",
                    "PlyCount",
                }
            }
            summary = {
                "id": game_id,
                "white": white,
                "black": black,
                "result": result,
                "opening": headers.get("Opening") or headers.get("ECO") or "—",
                "termination": headers.get("Termination", "normal"),
                "round": headers.get("Round"),
                "ply_count": len(moves_uci),
            }
            game_document = {
                "schema_version": 1,
                "run_id": run_id,
                **summary,
                "initial_fen": initial_fen,
                "headers": headers,
                "moves_uci": moves_uci,
                "moves_san": moves_san,
            }
            write_json_atomic(output_dir / f"{game_id}.json", game_document)
            summaries.append(summary)
            participants.update((white, black))

    if not summaries:
        raise ValueError("the PGN contains no games")
    index = {
        "schema_version": 1,
        "run_id": run_id,
        "total_games": len(summaries),
        "games": summaries,
    }
    write_json_atomic(output_dir / "index.json", index)
    return index, participants


def validate_ranking(ranking: dict, index: dict, participants: set[str]) -> None:
    if ranking.get("schema_version") != 1:
        raise ValueError("ranking.json has an unsupported schema")
    if ranking.get("total_games") != index["total_games"]:
        raise ValueError("ranking and PGN game totals differ")
    rows = ranking.get("rows")
    unrated = ranking.get("unrated", [])
    if not isinstance(rows, list) or not isinstance(unrated, list):
        raise ValueError("ranking rows are malformed")
    rated_bots = {row.get("bot") for row in rows}
    unrated_bots = {entry.get("bot") for entry in unrated}
    if rated_bots & unrated_bots:
        raise ValueError("a bot cannot be both rated and unrated")
    if rated_bots | unrated_bots != participants:
        raise ValueError("ranking and PGN participants differ")
    for row in rows:
        played = row.get("wins", 0) + row.get("draws", 0) + row.get("losses", 0)
        if row.get("played") != played:
            raise ValueError(f"inconsistent W/D/L totals for {row.get('bot')}")
    for entry in unrated:
        # Unrated means no point at all: every game of that bot is a loss.
        if entry.get("wins", 0) or entry.get("draws", 0) or entry.get("points", 0.0):
            raise ValueError(f"unrated bot {entry.get('bot')} scored points")
        if entry.get("played") != entry.get("losses", 0):
            raise ValueError(f"inconsistent totals for unrated bot {entry.get('bot')}")


def publish_run(run_id: str, data_root: Path, bots_path: Path) -> dict:
    """Publish one complete run. latest.json changes only after every check passes."""
    if "/" in run_id or run_id in {"", ".", ".."}:
        raise ValueError("run_id must be one directory name")
    run_dir = data_root / "runs" / run_id
    manifest_path = run_dir / "manifest.json"
    ranking_path = run_dir / "ranking.json"
    ranking_csv_path = run_dir / "ranking.csv"
    pgn_path = run_dir / "games.pgn"
    for required in (manifest_path, ranking_path, ranking_csv_path, pgn_path, bots_path):
        if not required.is_file():
            raise FileNotFoundError(f"required file not found: {required}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != run_id:
        raise ValueError("manifest run_id does not match its directory")
    if manifest.get("status") != "complete" or manifest.get("return_code") != 0:
        raise ValueError("publication requires a successfully completed tournament")
    if "publication" in manifest or (run_dir / "games").exists():
        raise ValueError("this run has already been published and is immutable")
    if manifest.get("games_sha256") != sha256_file(pgn_path):
        raise ValueError("games.pgn does not match the manifest checksum")

    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
    if ranking.get("run_id") != run_id:
        raise ValueError("ranking run_id does not match its directory")

    with tempfile.TemporaryDirectory(prefix=".publish-", dir=run_dir) as temporary:
        staged = Path(temporary)
        index, participants = export_games(pgn_path, staged / "games", run_id)
        validate_ranking(ranking, index, participants)
        bots = load_bots(bots_path, participants)
        write_json_atomic(staged / "bots.json", bots)

        published_at = datetime.now(timezone.utc).isoformat()
        publication = {
            "published_at": published_at,
            "total_games": index["total_games"],
            "ranking_sha256": sha256_file(ranking_path),
            "ranking_csv_sha256": sha256_file(ranking_csv_path),
            "games_index_sha256": sha256_file(staged / "games" / "index.json"),
            "bots_sha256": sha256_file(staged / "bots.json"),
        }

        shutil.move(staged / "games", run_dir / "games")
        shutil.move(staged / "bots.json", run_dir / "bots.json")
        manifest["publication"] = publication
        write_json_atomic(manifest_path, manifest)

    latest = {
        "schema_version": 1,
        "run_id": run_id,
        "published_at": publication["published_at"],
    }
    data_root.mkdir(parents=True, exist_ok=True)
    write_json_atomic(data_root / "latest.json", latest)
    return latest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="Directory name below data/arena/runs.")
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--bots", type=Path, default=DEFAULT_BOTS_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        latest = publish_run(args.run_id, args.data_root, args.bots)
        print(f"published {latest['run_id']}")
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
