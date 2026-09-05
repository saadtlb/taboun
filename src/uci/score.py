"""Static UCI score telemetry for bots that only return a move.

This is deliberately not a search score. It evaluates the position after the
chosen move with the evaluation family used by that bot generation. Tournament
adjudication must not use it.
"""

from __future__ import annotations

import chess

from src.evaluation.fast_evaluation_function import evaluate_fast
from src.evaluation.improved_evaluation_function import evaluate_improved
from src.evaluation.material import evaluate_material
from src.evaluation.pesto_evaluation_function import evaluate_pesto
from src.evaluation.simplified_evaluation_function import evaluate_simplified


def evaluation_for_bot(bot_name: str):
    try:
        version = int(bot_name.removeprefix("tabounv"))
    except ValueError:
        return evaluate_material
    if version <= 2:
        return evaluate_material
    if version <= 8:
        return evaluate_simplified
    if version <= 11:
        return evaluate_improved
    if version <= 12:
        return evaluate_fast
    return evaluate_pesto


def score_after_move(
    bot_name: str,
    board: chess.Board,
    move: chess.Move,
) -> tuple[str, int]:
    """Return a UCI ``(kind, value)`` score from the moving side's view."""
    moving_side = board.turn
    position = board.copy(stack=False)
    position.push(move)

    if position.is_checkmate():
        return "mate", 1
    if position.is_game_over(claim_draw=True):
        return "cp", 0

    white_score = evaluation_for_bot(bot_name)(position)
    score = white_score if moving_side == chess.WHITE else -white_score
    return "cp", int(score)
