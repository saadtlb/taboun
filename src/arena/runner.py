import itertools
from datetime import datetime
from typing import List, Dict, Any

from bot import BOT_REGISTRY
from arena.match import play_match
from arena.export import write_results_csv, write_ranking_csv, write_matrix_csv


def run_arena(
    games_per_pair: int = 20,
    results_path: str = "arena/results.csv",
    ranking_path: str = "arena/ranking.csv",
    matrix_path: str = "arena/matrix.csv",
) -> None:
    bot_items = list(BOT_REGISTRY.items())
    results_rows: List[Dict[str, Any]] = []
    scores = {name: {"points": 0.0, "wins": 0, "draws": 0, "losses": 0, "games": 0} for name, _ in bot_items}
    matrix_scores = {name: {other: "" for other, _ in bot_items} for name, _ in bot_items}

    for (name_a, class_a), (name_b, class_b) in itertools.combinations(bot_items, 2):
        match_label = f"Match: {name_a} vs {name_b}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} {match_label}")
        match = play_match(class_a, class_b, games=games_per_pair, match_label=match_label)
        stats = match["stats"]

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

    ranking_rows = [
        {
            "bot": name,
            "points": data["points"],
            "wins": data["wins"],
            "draws": data["draws"],
            "losses": data["losses"],
            "games": data["games"],
        }
        for name, data in scores.items()
    ]

    ranking_rows.sort(key=lambda r: r["points"], reverse=True)

    write_results_csv(results_path, results_rows)
    write_ranking_csv(ranking_path, ranking_rows)
    bot_names = [name for name, _ in bot_items]
    matrix = [[matrix_scores[row][col] if row != col else "" for col in bot_names] for row in bot_names]
    write_matrix_csv(matrix_path, bot_names, matrix)


if __name__ == "__main__":
    run_arena()
