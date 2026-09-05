"""Legacy in-process arena.

Frozen historical code: repeated start positions, unequal thinking time and
sequential rating updates make its results unusable for published rankings.
The fastchess pipeline in ``src/arena`` replaced it. Run from the repository
root with ``python -m src.arena.legacy.runner``.
"""

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools
from pathlib import Path
from datetime import datetime
from typing import Any

from src.bot import BOT_REGISTRY
from src.arena.legacy.match import play_match
from src.arena.legacy.export import write_results_csv, write_ranking_csv, write_matrix_csv


def run_arena(
    games_per_pair: int = 20,
    results_path: str = "data/arena/legacy/results.csv",
    ranking_path: str = "data/arena/legacy/ranking.csv",
    matrix_path: str = "data/arena/legacy/matrix.csv",
    parallel: bool = False,
    workers: int = 4,
    bot_names: list[str] | None = None,
    resume: bool = False,
) -> None:
    if games_per_pair < 0:
        raise ValueError("games_per_pair must be at least 0.")

    bot_items = select_bot_items(bot_names)
    scores = {name: {"points": 0.0, "wins": 0, "draws": 0, "losses": 0, "games": 0} for name, _ in bot_items}
    matrix_scores = {name: {other: "" for other, _ in bot_items} for name, _ in bot_items}
    elo = {name: 1200.0 for name, _ in bot_items}
    k_factor = 20.0
    pairings = build_pairings(bot_items)

    existing_rows = load_existing_results(results_path, pairings) if resume else {}
    pairings_to_run = prepare_pairings_to_run(pairings, existing_rows, games_per_pair, resume)

    if parallel:
        match_results = run_pairings_parallel(pairings_to_run, workers)
    else:
        match_results = run_pairings_sequential(pairings_to_run)

    new_rows = {pairing_key(result["name_a"], result["name_b"]): match_result_to_row(result) for result in match_results}
    results_rows = build_final_results_rows(pairings, existing_rows, new_rows)

    for result_row in results_rows:
        update_arena_tables_from_row(result_row, scores, matrix_scores, elo, k_factor)

    ranking_rows = build_ranking_rows(scores, elo)
    ranking_rows.sort(key=lambda r: r["points"], reverse=True)

    write_results_csv(results_path, results_rows)
    write_ranking_csv(ranking_path, ranking_rows)
    bot_names = [name for name, _ in bot_items]
    matrix = [[matrix_scores[row][col] if row != col else "" for col in bot_names] for row in bot_names]
    write_matrix_csv(matrix_path, bot_names, matrix)


def build_ranking_rows(scores: dict[str, dict[str, Any]], elo: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {
            "bot": name,
            "points": data["points"],
            "wins": data["wins"],
            "draws": data["draws"],
            "losses": data["losses"],
            "games": data["games"],
            "elo": round(elo[name], 1),
        }
        for name, data in scores.items()
    ]


def build_final_results_rows(
    pairings: list[dict[str, Any]],
    existing_rows: dict[tuple[str, str], dict[str, Any]],
    new_rows: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    final_rows = []

    for pairing in pairings:
        key = pairing_key(pairing["name_a"], pairing["name_b"])
        existing_row = existing_rows.get(key)
        new_row = new_rows.get(key)

        if existing_row and new_row:
            final_rows.append(merge_result_rows(existing_row, new_row))
        elif existing_row:
            final_rows.append(existing_row)
        elif new_row:
            final_rows.append(new_row)

    return final_rows


def match_result_to_row(match_result: dict[str, Any]) -> dict[str, Any]:
    stats = match_result["match"]["stats"]
    return {
        "bot_white": match_result["name_a"],
        "bot_black": match_result["name_b"],
        "games": stats["games"],
        "bot_white_points": stats["bot_a_points"],
        "bot_black_points": stats["bot_b_points"],
        "bot_white_wins": stats["bot_a_wins"],
        "bot_black_wins": stats["bot_b_wins"],
        "draws": stats["draws"],
    }


def merge_result_rows(existing_row: dict[str, Any], new_row: dict[str, Any]) -> dict[str, Any]:
    merged_row = {
        "bot_white": existing_row["bot_white"],
        "bot_black": existing_row["bot_black"],
        "games": int(existing_row["games"]) + int(new_row["games"]),
        "bot_white_points": float(existing_row["bot_white_points"]) + float(new_row["bot_white_points"]),
        "bot_black_points": float(existing_row["bot_black_points"]) + float(new_row["bot_black_points"]),
        "bot_white_wins": int(existing_row["bot_white_wins"]) + int(new_row["bot_white_wins"]),
        "bot_black_wins": int(existing_row["bot_black_wins"]) + int(new_row["bot_black_wins"]),
        "draws": int(existing_row["draws"]) + int(new_row["draws"]),
    }
    validate_result_row(merged_row)
    return merged_row


def prepare_pairings_to_run(
    pairings: list[dict[str, Any]],
    existing_rows: dict[tuple[str, str], dict[str, Any]],
    games_per_pair: int,
    resume: bool,
) -> list[dict[str, Any]]:
    pairings_to_run = []

    for pairing in pairings:
        key = pairing_key(pairing["name_a"], pairing["name_b"])
        existing_row = existing_rows.get(key)
        existing_games = int(existing_row["games"]) if existing_row else 0
        games_to_play = games_per_pair - existing_games

        if resume and existing_games >= games_per_pair:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{timestamp} Resume: skipping {pairing['name_a']} vs {pairing['name_b']} "
                f"({existing_games}/{games_per_pair} games already recorded).",
                flush=True,
            )
            continue

        if resume and existing_games > 0:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{timestamp} Resume: completing {pairing['name_a']} vs {pairing['name_b']} "
                f"({existing_games}/{games_per_pair} games recorded, {games_to_play} left).",
                flush=True,
            )

        pairings_to_run.append({**pairing, "games_to_play": games_to_play})

    return pairings_to_run


def load_existing_results(
    results_path: str,
    pairings: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    path = Path(results_path)
    if not path.exists():
        return {}

    requested_pairings = {pairing_key(pairing["name_a"], pairing["name_b"]): pairing for pairing in pairings}
    rows = {}

    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            return {}

        missing_columns = sorted(set(RESULTS_FIELDNAMES) - set(reader.fieldnames))
        if missing_columns:
            raise ValueError(f"Cannot resume from {results_path}: missing column(s): {', '.join(missing_columns)}")

        for raw_row in reader:
            raw_key = pairing_key(raw_row["bot_white"], raw_row["bot_black"])
            pairing = requested_pairings.get(raw_key)
            if pairing is None:
                continue

            normalized_row = normalize_result_row(raw_row, pairing["name_a"], pairing["name_b"])
            if raw_key in rows:
                raise ValueError(
                    f"Cannot resume from {results_path}: duplicate result row for "
                    f"{normalized_row['bot_white']} vs {normalized_row['bot_black']}"
                )
            rows[raw_key] = normalized_row

    return rows


def normalize_result_row(raw_row: dict[str, Any], name_a: str, name_b: str) -> dict[str, Any]:
    row = {
        "bot_white": raw_row["bot_white"].strip().lower(),
        "bot_black": raw_row["bot_black"].strip().lower(),
        "games": int(raw_row["games"]),
        "bot_white_points": float(raw_row["bot_white_points"]),
        "bot_black_points": float(raw_row["bot_black_points"]),
        "bot_white_wins": int(raw_row["bot_white_wins"]),
        "bot_black_wins": int(raw_row["bot_black_wins"]),
        "draws": int(raw_row["draws"]),
    }

    if row["bot_white"] == name_a and row["bot_black"] == name_b:
        validate_result_row(row)
        return row

    if row["bot_white"] == name_b and row["bot_black"] == name_a:
        normalized_row = {
            "bot_white": name_a,
            "bot_black": name_b,
            "games": row["games"],
            "bot_white_points": row["bot_black_points"],
            "bot_black_points": row["bot_white_points"],
            "bot_white_wins": row["bot_black_wins"],
            "bot_black_wins": row["bot_white_wins"],
            "draws": row["draws"],
        }
        validate_result_row(normalized_row)
        return normalized_row

    raise ValueError(f"Cannot normalize result row for {row['bot_white']} vs {row['bot_black']}")


def validate_result_row(row: dict[str, Any]) -> None:
    games = int(row["games"])
    bot_white_points = float(row["bot_white_points"])
    bot_black_points = float(row["bot_black_points"])
    bot_white_wins = int(row["bot_white_wins"])
    bot_black_wins = int(row["bot_black_wins"])
    draws = int(row["draws"])

    if row["bot_white"] == row["bot_black"]:
        raise ValueError(f"Invalid result row: bot cannot play itself ({row['bot_white']}).")

    if min(games, bot_white_points, bot_black_points, bot_white_wins, bot_black_wins, draws) < 0:
        raise ValueError(f"Invalid result row for {row['bot_white']} vs {row['bot_black']}: negative value.")

    if bot_white_wins + bot_black_wins + draws != games:
        raise ValueError(
            f"Invalid result row for {row['bot_white']} vs {row['bot_black']}: "
            "wins plus draws must equal games."
        )

    if abs((bot_white_points + bot_black_points) - games) > 1e-9:
        raise ValueError(
            f"Invalid result row for {row['bot_white']} vs {row['bot_black']}: "
            "points must add up to games."
        )


def pairing_key(name_a: str, name_b: str) -> tuple[str, str]:
    return tuple(sorted((name_a.strip().lower(), name_b.strip().lower())))


def update_arena_tables_from_row(
    row: dict[str, Any],
    scores: dict[str, dict[str, Any]],
    matrix_scores: dict[str, dict[str, str]],
    elo: dict[str, float],
    k_factor: float,
) -> None:
    name_a = row["bot_white"]
    name_b = row["bot_black"]
    games = int(row["games"])
    bot_a_points = float(row["bot_white_points"])
    bot_b_points = float(row["bot_black_points"])
    bot_a_wins = int(row["bot_white_wins"])
    bot_b_wins = int(row["bot_black_wins"])
    draws = int(row["draws"])

    scores[name_a]["points"] += bot_a_points
    scores[name_a]["wins"] += bot_a_wins
    scores[name_a]["draws"] += draws
    scores[name_a]["losses"] += bot_b_wins
    scores[name_a]["games"] += games

    scores[name_b]["points"] += bot_b_points
    scores[name_b]["wins"] += bot_b_wins
    scores[name_b]["draws"] += draws
    scores[name_b]["losses"] += bot_a_wins
    scores[name_b]["games"] += games

    matrix_scores[name_a][name_b] = f"{bot_a_points:.1f}-{bot_b_points:.1f}"
    matrix_scores[name_b][name_a] = f"{bot_b_points:.1f}-{bot_a_points:.1f}"

    update_elo_from_aggregate(name_a, name_b, bot_a_points, bot_b_points, games, elo, k_factor)


def update_elo_from_aggregate(
    name_a: str,
    name_b: str,
    points_a: float,
    points_b: float,
    games: int,
    elo: dict[str, float],
    k_factor: float,
) -> None:
    if games <= 0:
        return

    rating_a = elo[name_a]
    rating_b = elo[name_b]
    expected_a = 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))
    expected_b = 1.0 - expected_a

    elo[name_a] = rating_a + k_factor * (points_a - expected_a * games)
    elo[name_b] = rating_b + k_factor * (points_b - expected_b * games)


RESULTS_FIELDNAMES = [
    "bot_white",
    "bot_black",
    "games",
    "bot_white_points",
    "bot_black_points",
    "bot_white_wins",
    "bot_black_wins",
    "draws",
]


def select_bot_items(bot_names: list[str] | None = None) -> list[tuple[str, type]]:
    if bot_names is None:
        return list(BOT_REGISTRY.items())

    selected = []
    missing = []
    seen = set()
    duplicates = []

    for raw_name in bot_names:
        name = raw_name.strip().lower()
        if not name:
            continue
        if name in seen:
            duplicates.append(raw_name)
            continue
        seen.add(name)
        if name in BOT_REGISTRY:
            selected.append((name, BOT_REGISTRY[name]))
        else:
            missing.append(raw_name)

    if missing:
        available = ", ".join(BOT_REGISTRY.keys())
        raise ValueError(f"Unknown bot(s): {', '.join(missing)}. Available bots: {available}")

    if duplicates:
        raise ValueError(f"Duplicate bot(s): {', '.join(duplicates)}")

    if len(selected) < 2:
        raise ValueError("Arena needs at least two bots.")

    return selected


def build_pairings(bot_items: list[tuple[str, type]]) -> list[dict[str, Any]]:
    pairings = []

    for index, ((name_a, _), (name_b, _)) in enumerate(itertools.combinations(bot_items, 2)):
        pairings.append(
            {
                "index": index,
                "name_a": name_a,
                "name_b": name_b,
            }
        )

    return pairings


def run_pairings_sequential(pairings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    match_results = []

    for pairing in pairings:
        match_label = f"Match: {pairing['name_a']} vs {pairing['name_b']}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} {match_label}", flush=True)
        match_results.append(
            play_pairing(
                pairing["index"],
                pairing["name_a"],
                pairing["name_b"],
                pairing["games_to_play"],
                match_label,
            )
        )

    return match_results


def run_pairings_parallel(
    pairings: list[dict[str, Any]],
    workers: int,
) -> list[dict[str, Any]]:
    if workers < 1:
        raise ValueError("workers must be at least 1.")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} Running arena in parallel with {workers} workers.", flush=True)

    match_results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                play_pairing,
                pairing["index"],
                pairing["name_a"],
                pairing["name_b"],
                pairing["games_to_play"],
                f"Match: {pairing['name_a']} vs {pairing['name_b']}",
            ): pairing
            for pairing in pairings
        }

        for future in as_completed(futures):
            pairing = futures[future]
            match_result = future.result()
            stats = match_result["match"]["stats"]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{timestamp} Finished: {pairing['name_a']} vs {pairing['name_b']} "
                f"({stats['bot_a_points']:.1f}-{stats['bot_b_points']:.1f})",
                flush=True,
            )
            match_results.append(match_result)

    match_results.sort(key=lambda result: result["index"])
    return match_results


def play_pairing(
    index: int,
    name_a: str,
    name_b: str,
    games_per_pair: int,
    match_label: str | None,
) -> dict[str, Any]:
    class_a = BOT_REGISTRY[name_a]
    class_b = BOT_REGISTRY[name_b]
    match = play_match(class_a, class_b, games=games_per_pair, match_label=match_label)

    return {
        "index": index,
        "name_a": name_a,
        "name_b": name_b,
        "match": match,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the taboun bot arena.")
    parser.add_argument("--games-per-pair", type=int, default=20)
    parser.add_argument("--bots", help="Comma-separated bot names, for example: tabounv7,tabounv8")
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--results-path", default="data/arena/legacy/results.csv")
    parser.add_argument("--ranking-path", default="data/arena/legacy/ranking.csv")
    parser.add_argument("--matrix-path", default="data/arena/legacy/matrix.csv")
    parser.add_argument("--resume", action="store_true", help="Reuse existing results and play only missing games.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        run_arena(
            games_per_pair=args.games_per_pair,
            results_path=args.results_path,
            ranking_path=args.ranking_path,
            matrix_path=args.matrix_path,
            parallel=args.parallel,
            workers=args.workers,
            bot_names=parse_bot_names(args.bots),
            resume=args.resume,
        )
    except ValueError as error:
        raise SystemExit(f"error: {error}") from error


def parse_bot_names(raw_bots: str | None) -> list[str] | None:
    if raw_bots is None:
        return None
    return [name.strip() for name in raw_bots.split(",") if name.strip()]


if __name__ == "__main__":
    main()
