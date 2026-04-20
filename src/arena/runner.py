import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bot import BOT_REGISTRY
from arena.match import play_match
from arena.export import write_results_csv, write_ranking_csv, write_matrix_csv


def run_arena(
    games_per_pair: int = 20,
    results_path: str = "arena/results.csv",
    ranking_path: str = "arena/ranking.csv",
    matrix_path: str = "arena/matrix.csv",
    parallel: bool = False,
    workers: int = 4,
    bot_names: list[str] | None = None,
) -> None:
    bot_items = select_bot_items(bot_names)
    results_rows: List[Dict[str, Any]] = []
    scores = {name: {"points": 0.0, "wins": 0, "draws": 0, "losses": 0, "games": 0} for name, _ in bot_items}
    matrix_scores = {name: {other: "" for other, _ in bot_items} for name, _ in bot_items}
    elo = {name: 1200.0 for name, _ in bot_items}
    k_factor = 20.0
    pairings = build_pairings(bot_items)

    if parallel:
        match_results = run_pairings_parallel(pairings, games_per_pair, workers)
    else:
        match_results = run_pairings_sequential(pairings, games_per_pair)

    for match_result in match_results:
        update_arena_tables(match_result, scores, matrix_scores, elo, results_rows, k_factor)

    ranking_rows = [
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

    ranking_rows.sort(key=lambda r: r["points"], reverse=True)

    write_results_csv(results_path, results_rows)
    write_ranking_csv(ranking_path, ranking_rows)
    bot_names = [name for name, _ in bot_items]
    matrix = [[matrix_scores[row][col] if row != col else "" for col in bot_names] for row in bot_names]
    write_matrix_csv(matrix_path, bot_names, matrix)


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


def run_pairings_sequential(pairings: list[dict[str, Any]], games_per_pair: int) -> list[dict[str, Any]]:
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
                games_per_pair,
                match_label,
            )
        )

    return match_results


def run_pairings_parallel(
    pairings: list[dict[str, Any]],
    games_per_pair: int,
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
                games_per_pair,
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


def update_arena_tables(
    match_result: dict[str, Any],
    scores: dict[str, dict[str, Any]],
    matrix_scores: dict[str, dict[str, str]],
    elo: dict[str, float],
    results_rows: List[Dict[str, Any]],
    k_factor: float,
) -> None:
    name_a = match_result["name_a"]
    name_b = match_result["name_b"]
    match = match_result["match"]
    stats = match["stats"]
    results = match["results"]

    # Update scores
    scores[name_a]["points"] += stats["bot_a_points"]
    scores[name_a]["wins"] += stats["bot_a_wins"]
    scores[name_a]["draws"] += stats["draws"]
    scores[name_a]["losses"] += stats["bot_b_wins"]
    scores[name_a]["games"] += stats["games"]

    scores[name_b]["points"] += stats["bot_b_points"]
    scores[name_b]["wins"] += stats["bot_b_wins"]
    scores[name_b]["draws"] += stats["draws"]
    scores[name_b]["losses"] += stats["bot_a_wins"]
    scores[name_b]["games"] += stats["games"]

    results_rows.append(
        {
            "bot_white": name_a,
            "bot_black": name_b,
            "games": stats["games"],
            "bot_white_points": stats["bot_a_points"],
            "bot_black_points": stats["bot_b_points"],
            "bot_white_wins": stats["bot_a_wins"],
            "bot_black_wins": stats["bot_b_wins"],
            "draws": stats["draws"],
        }
    )
    matrix_scores[name_a][name_b] = f"{stats['bot_a_points']:.1f}-{stats['bot_b_points']:.1f}"
    matrix_scores[name_b][name_a] = f"{stats['bot_b_points']:.1f}-{stats['bot_a_points']:.1f}"

    # Update Elo after each game using FIDE formula
    for score_a, score_b in results:
        ra = elo[name_a]
        rb = elo[name_b]
        expected_a = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
        expected_b = 1.0 - expected_a

        elo[name_a] = ra + k_factor * (score_a - expected_a)
        elo[name_b] = rb + k_factor * (score_b - expected_b)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the taboun bot arena.")
    parser.add_argument("--games-per-pair", type=int, default=20)
    parser.add_argument("--bots", help="Comma-separated bot names, for example: tabounv7,tabounv8")
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--results-path", default="arena/results.csv")
    parser.add_argument("--ranking-path", default="arena/ranking.csv")
    parser.add_argument("--matrix-path", default="arena/matrix.csv")
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
        )
    except ValueError as error:
        raise SystemExit(f"error: {error}") from error


def parse_bot_names(raw_bots: str | None) -> list[str] | None:
    if raw_bots is None:
        return None
    return [name.strip() for name in raw_bots.split(",") if name.strip()]


if __name__ == "__main__":
    main()
