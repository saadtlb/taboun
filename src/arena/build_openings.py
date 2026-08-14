"""Build a deterministic PGN opening suite from a Polyglot book."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import chess
import chess.pgn
import chess.polyglot


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOK = REPO_ROOT / "data" / "openings" / "books" / "komodo3.bin"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "openings" / "arena_openings.pgn"
DEFAULT_SUMMARY = REPO_ROOT / "data" / "openings" / "arena_openings.json"
DEFAULT_SEED = 20260814


@dataclass(frozen=True)
class OpeningSummary:
    seed: int
    count: int
    min_plies: int
    max_plies: int
    book_sha256: str
    pgn_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_weighted_entry(entries: list[chess.polyglot.Entry], rng: random.Random) -> chess.polyglot.Entry:
    total_weight = sum(max(0, entry.weight) for entry in entries)
    if total_weight <= 0:
        return entries[rng.randrange(len(entries))]

    choice = rng.randrange(total_weight)
    for entry in entries:
        choice -= max(0, entry.weight)
        if choice < 0:
            return entry
    return entries[-1]


def sample_line(
    reader: chess.polyglot.MemoryMappedReader,
    rng: random.Random,
    target_plies: int,
) -> tuple[chess.Move, ...]:
    board = chess.Board()
    moves = []
    for _ in range(target_plies):
        entries = list(reader.find_all(board))
        if not entries:
            break
        entry = choose_weighted_entry(entries, rng)
        if entry.move not in board.legal_moves:
            break
        moves.append(entry.move)
        board.push(entry.move)
    return tuple(moves)


def build_lines(
    book_path: Path,
    *,
    count: int,
    seed: int,
    min_plies: int,
    max_plies: int,
) -> list[tuple[chess.Move, ...]]:
    if count < 1:
        raise ValueError("count must be at least 1")
    if min_plies < 1 or max_plies < min_plies:
        raise ValueError("plies must satisfy 1 <= min_plies <= max_plies")
    if not book_path.is_file():
        raise FileNotFoundError(f"opening book not found: {book_path}")

    rng = random.Random(seed)
    unique_lines: dict[tuple[str, ...], tuple[chess.Move, ...]] = {}
    max_attempts = max(1_000, count * 500)

    with chess.polyglot.open_reader(str(book_path)) as reader:
        for _ in range(max_attempts):
            target_plies = rng.randint(min_plies, max_plies)
            line = sample_line(reader, rng, target_plies)
            if len(line) < min_plies:
                continue
            key = tuple(move.uci() for move in line)
            unique_lines.setdefault(key, line)
            if len(unique_lines) == count:
                break

    if len(unique_lines) != count:
        raise RuntimeError(
            f"book produced only {len(unique_lines)} unique lines after {max_attempts} attempts; "
            f"requested {count}"
        )
    return list(unique_lines.values())


def write_openings(path: Path, lines: list[tuple[chess.Move, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered_games = []

    for index, line in enumerate(lines, start=1):
        game = chess.pgn.Game()
        game.headers["Event"] = "Taboun Arena Opening"
        game.headers["Site"] = "geheim.land"
        game.headers["Round"] = str(index)
        game.headers["Result"] = "*"
        node = game
        for move in line:
            node = node.add_variation(move)
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        rendered_games.append(game.accept(exporter).strip())

    path.write_text("\n\n".join(rendered_games) + "\n", encoding="utf-8")


def build_opening_suite(
    book_path: Path,
    output_path: Path,
    summary_path: Path,
    *,
    count: int,
    seed: int,
    min_plies: int,
    max_plies: int,
) -> OpeningSummary:
    lines = build_lines(
        book_path,
        count=count,
        seed=seed,
        min_plies=min_plies,
        max_plies=max_plies,
    )
    write_openings(output_path, lines)
    summary = OpeningSummary(
        seed=seed,
        count=count,
        min_plies=min(len(line) for line in lines),
        max_plies=max(len(line) for line in lines),
        book_sha256=sha256_file(book_path),
        pgn_sha256=sha256_file(output_path),
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(asdict(summary), indent=2) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=Path, default=DEFAULT_BOOK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--min-plies", type=int, default=6)
    parser.add_argument("--max-plies", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        summary = build_opening_suite(
            args.book,
            args.output,
            args.summary,
            count=args.count,
            seed=args.seed,
            min_plies=args.min_plies,
            max_plies=args.max_plies,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
    print(json.dumps(asdict(summary), indent=2))


if __name__ == "__main__":
    main()
