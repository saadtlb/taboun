from threading import Event

import chess

from bot.time_control import SearchDeadline, SearchTimeout, check_time, make_deadline
from evaluation.simplified_evaluation_function import evaluate_simplified


class tabounV6:
    """Alpha-beta bot with simplified evaluation and quiescence search."""

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
    alpha = -float("inf")
    beta = float("inf")

    for move in list(board.legal_moves):
        check_time(deadline)
        board.push(move)
        try:
            score = alphabeta(board, depth - 1, alpha, beta, deadline)
        finally:
            board.pop()

        if is_white_to_play and score > best_score:
            best_score = score
            best_move = move
            alpha = max(alpha, best_score)
        elif not is_white_to_play and score < best_score:
            best_score = score
            best_move = move
            beta = min(beta, best_score)

    return best_move


def alphabeta(
    board: chess.Board,
    depth: int,
    alpha: float,
    beta: float,
    deadline: SearchDeadline | None = None,
) -> int:
    check_time(deadline)
    if depth == 0 or board.is_game_over():
        return quiescence(board, alpha, beta, deadline)

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return quiescence(board, alpha, beta, deadline)

    if board.turn == chess.WHITE:
        best_score = -float("inf")
        for move in legal_moves:
            check_time(deadline)
            board.push(move)
            try:
                score = alphabeta(board, depth - 1, alpha, beta, deadline)
            finally:
                board.pop()
            if score > best_score:
                best_score = score
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
        return best_score

    best_score = float("inf")
    for move in legal_moves:
        check_time(deadline)
        board.push(move)
        try:
            score = alphabeta(board, depth - 1, alpha, beta, deadline)
        finally:
            board.pop()
        if score < best_score:
            best_score = score
        beta = min(beta, best_score)
        if beta <= alpha:
            break
    return best_score


def quiescence(
    board: chess.Board,
    alpha: float,
    beta: float,
    deadline: SearchDeadline | None = None,
) -> int:
    check_time(deadline)
    # Evaluate only "quiet" positions by extending capture sequences.
    stand_pat = evaluate_simplified(board)

    if board.turn == chess.WHITE:
        if stand_pat >= beta:
            return stand_pat
        alpha = max(alpha, stand_pat)
    else:
        if stand_pat <= alpha:
            return stand_pat
        beta = min(beta, stand_pat)

    for move in board.legal_moves:
        check_time(deadline)
        if not board.is_capture(move):
            continue
        board.push(move)
        try:
            score = quiescence(board, alpha, beta, deadline)
        finally:
            board.pop()

        if board.turn == chess.WHITE:
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        else:
            if score < beta:
                beta = score
            if beta <= alpha:
                break

    return alpha if board.turn == chess.WHITE else beta
