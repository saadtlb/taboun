from datetime import datetime

import chess


def play_game(bot_white_class, bot_black_class, max_plies: int = 400) -> tuple[float, float]:
    """Plays a single game between two bot classes. Returns (white_score, black_score)."""
    board = chess.Board()
    bot_white = bot_white_class()
    bot_black = bot_black_class()
    ply_count = 0

    while not board.is_game_over(claim_draw=True) and ply_count < max_plies:
        if board.turn == chess.WHITE:
            bot = bot_white
        else:
            bot = bot_black

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            break

        move = bot.choose_move(board)
        board.push(move)
        ply_count += 1

    outcome = board.outcome(claim_draw=True)
    if outcome is None or outcome.winner is None:
        return 0.5, 0.5
    if outcome.winner == chess.WHITE:
        return 1.0, 0.0
    return 0.0, 1.0


def play_match(bot_a_class, bot_b_class, games: int = 20, match_label: str | None = None) -> dict:
    """Plays a match between two bot classes (half games each color)."""
    half = games // 2
    stats = {
        "bot_a_points": 0.0,
        "bot_b_points": 0.0,
        "bot_a_wins": 0,
        "bot_b_wins": 0,
        "draws": 0,
        "games": 0,
    }
    results = []

    # bot A as White, bot B as Black
    for index in range(1, half + 1):
        if match_label:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} {match_label} - Game {index}/{games}", flush=True)
        w, b = play_game(bot_a_class, bot_b_class)
        stats["bot_a_points"] += w
        stats["bot_b_points"] += b
        stats["games"] += 1
        if w == 1.0:
            stats["bot_a_wins"] += 1
        elif b == 1.0:
            stats["bot_b_wins"] += 1
        else:
            stats["draws"] += 1
        results.append((w, b))
        print_game_finished(match_label, index, games, stats)

    # bot B as White, bot A as Black
    for index in range(half + 1, games + 1):
        if match_label:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} {match_label} - Game {index}/{games}", flush=True)
        w, b = play_game(bot_b_class, bot_a_class)
        stats["bot_b_points"] += w
        stats["bot_a_points"] += b
        stats["games"] += 1
        if w == 1.0:
            stats["bot_b_wins"] += 1
        elif b == 1.0:
            stats["bot_a_wins"] += 1
        else:
            stats["draws"] += 1
        results.append((b, w))  # perspective consistent: bot_a as White score first
        print_game_finished(match_label, index, games, stats)

    return {"stats": stats, "results": results}


def print_game_finished(match_label: str | None, index: int, games: int, stats: dict) -> None:
    if not match_label:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"{timestamp} {match_label} - Finished game {index}/{games} "
        f"score {stats['bot_a_points']:.1f}-{stats['bot_b_points']:.1f} "
        f"(W:{stats['bot_a_wins']}-{stats['bot_b_wins']}, D:{stats['draws']})",
        flush=True,
    )
