from threading import Event

import chess
import chess.polyglot

from src.bot.time_control import SearchDeadline, SearchTimeout, check_time, make_deadline
from src.evaluation.improved_evaluation_function import evaluate_improved


class tabounV9:
    """V8 search with an improved positional evaluation."""

    def __init__(
        self,
        depth: int = 2,
        time_limit: float | None = None,
        stop_event: Event | None = None,
    ) -> None:
        self.depth = depth
        self.time_limit = time_limit
        self.stop_event = stop_event
        self.transposition_table: dict[int, tuple[int, int, str]] = {}

    def choose_move(self, board: chess.Board) -> chess.Move:
        legal_moves = order_moves(board)
        if not legal_moves:
            raise ValueError("No legal moves available.")

        best_move = legal_moves[0]
        deadline = make_deadline(self.time_limit, self.stop_event)

        for current_depth in range(1, self.depth + 1):
            try:
                best_move = search_root(
                    board,
                    current_depth,
                    best_move,
                    deadline,
                    self.transposition_table,
                )
            except SearchTimeout:
                break

        return best_move


def search_root(
    board: chess.Board,
    depth: int,
    previous_best_move: chess.Move,
    deadline: SearchDeadline | None,
    table: dict[int, tuple[int, int, str]],
) -> chess.Move:
    check_time(deadline)
    is_white_to_play = board.turn == chess.WHITE
    best_score = -float("inf") if is_white_to_play else float("inf")
    alpha = -float("inf")
    beta = float("inf")
    best_move = previous_best_move

    for move in order_moves(board, previous_best_move):
        check_time(deadline)
        board.push(move)
        try:
            score = alphabeta(board, depth - 1, alpha, beta, table, deadline)
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
    table: dict[int, tuple[int, int, str]],
    deadline: SearchDeadline | None = None,
) -> int:
    check_time(deadline)
    alpha_original = alpha
    beta_original = beta

    key = chess.polyglot.zobrist_hash(board)
    if key in table:
        stored_depth, stored_score, stored_flag = table[key]
        if stored_depth >= depth:
            if stored_flag == "exact":
                return stored_score
            if stored_flag == "alpha" and stored_score <= alpha:
                return stored_score
            if stored_flag == "beta" and stored_score >= beta:
                return stored_score

    if depth == 0 or board.is_game_over():
        return quiescence(board, alpha, beta, deadline)

    legal_moves = order_moves(board)
    if not legal_moves:
        return quiescence(board, alpha, beta, deadline)

    if board.turn == chess.WHITE:
        best_score = -float("inf")
        for move in legal_moves:
            check_time(deadline)
            board.push(move)
            try:
                score = alphabeta(board, depth - 1, alpha, beta, table, deadline)
            finally:
                board.pop()
            if score > best_score:
                best_score = score
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
    else:
        best_score = float("inf")
        for move in legal_moves:
            check_time(deadline)
            board.push(move)
            try:
                score = alphabeta(board, depth - 1, alpha, beta, table, deadline)
            finally:
                board.pop()
            if score < best_score:
                best_score = score
            beta = min(beta, best_score)
            if beta <= alpha:
                break

    if best_score <= alpha_original:
        table[key] = (depth, int(best_score), "alpha")
    elif best_score >= beta_original:
        table[key] = (depth, int(best_score), "beta")
    else:
        table[key] = (depth, int(best_score), "exact")

    return best_score


def quiescence(
    board: chess.Board,
    alpha: float,
    beta: float,
    deadline: SearchDeadline | None = None,
) -> int:
    check_time(deadline)
    # Evaluate only "quiet" positions by extending capture sequences.
    stand_pat = evaluate_improved(board)

    if board.turn == chess.WHITE:
        if stand_pat >= beta:
            return stand_pat
        alpha = max(alpha, stand_pat)
    else:
        if stand_pat <= alpha:
            return stand_pat
        beta = min(beta, stand_pat)

    for move in order_moves(board):
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


def order_moves(board: chess.Board, best_move: chess.Move | None = None) -> list[chess.Move]:
    return sorted(board.legal_moves, key=lambda move: move_score(board, move, best_move), reverse=True)


def move_score(board: chess.Board, move: chess.Move, best_move: chess.Move | None = None) -> int:
    if best_move is not None and move == best_move:
        return 100000

    score = 0

    if move.promotion:
        score += 8000 + PIECE_ORDER.get(move.promotion, 0)

    if board.is_capture(move):
        attacker = board.piece_at(move.from_square)
        victim = board.piece_at(move.to_square)
        if board.is_en_passant(move):
            victim_value = PIECE_VALUES[chess.PAWN]
        elif victim is not None:
            victim_value = PIECE_VALUES.get(victim.piece_type, 0)
        else:
            victim_value = 0

        attacker_value = PIECE_VALUES.get(attacker.piece_type, 0) if attacker is not None else 0
        score += 10000 + victim_value - attacker_value

    if board.gives_check(move):
        score += 500

    return score


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

PIECE_ORDER = {
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
}
