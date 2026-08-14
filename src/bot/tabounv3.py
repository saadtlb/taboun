from threading import Event

import chess

from bot.time_control import SearchDeadline, SearchTimeout, check_time, make_deadline
from evaluation.simplified_evaluation_function import evaluate_simplified


class tabounV3:
    """Minimax bot using a simplified evaluation (material + piece-square tables)."""

    def __init__(
        self,
        depth: int = 2,
        time_limit: float | None = None,
        stop_event: Event | None = None,
    ) -> None:
        self.depth = depth
        self.time_limit = time_limit
        self.stop_event = stop_event

    def choose_move(self, board: chess.Board) -> chess.Move:
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            raise ValueError("No legal moves available.")

        best_move = legal_moves[0]
        deadline = make_deadline(self.time_limit, self.stop_event)

        if deadline is None:
            return search_root(board, self.depth, best_move, None)

        for current_depth in range(1, self.depth + 1):
            try:
                best_move = search_root(board, current_depth, best_move, deadline)
            except SearchTimeout:
                break

        return best_move


def search_root(
    board: chess.Board,
    depth: int,
    previous_best_move: chess.Move,
    deadline: SearchDeadline | None,
) -> chess.Move:
    check_time(deadline)
    is_white_to_play = board.turn == chess.WHITE
    best_score = -float("inf") if is_white_to_play else float("inf")
    best_move = previous_best_move

    for move in list(board.legal_moves):
        check_time(deadline)
        board.push(move)
        try:
            score = minimax(board, depth - 1, deadline)
        finally:
            board.pop()

        if is_white_to_play and score > best_score:
            best_score = score
            best_move = move
        elif not is_white_to_play and score < best_score:
            best_score = score
            best_move = move

    return best_move


def minimax(board: chess.Board, depth: int, deadline: SearchDeadline | None = None) -> int:
    check_time(deadline)
    if depth == 0 or board.is_game_over():
        return evaluate_simplified(board)

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return evaluate_simplified(board)

    is_white_to_play = board.turn == chess.WHITE

    if is_white_to_play:
        best_score = -float("inf")
        for move in legal_moves:
            check_time(deadline)
            board.push(move)
            try:
                score = minimax(board, depth - 1, deadline)
            finally:
                board.pop()
            if score > best_score:
                best_score = score
        return best_score

    best_score = float("inf")
    for move in legal_moves:
        check_time(deadline)
        board.push(move)
        try:
            score = minimax(board, depth - 1, deadline)
        finally:
            board.pop()
        if score < best_score:
            best_score = score
    return best_score
