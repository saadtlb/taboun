"""tabounV12: tabounV11 with the phase 0 correctness and speed fixes.

Differences with tabounV11:
- mate scores carry their distance to mate, so the search prefers a mate in 1
  over a mate in 7 and actually converts won endgames,
- terminal positions are detected in the search rather than in the evaluation,
- the transposition table stores the best move and is used to order moves at
  every node, not just at the root,
- move ordering no longer calls gives_check on every move,
- quiescence generates captures only, instead of sorting every legal move and
  then discarding the quiet ones.
"""

import time

import chess

from evaluation.fast_evaluation_function import evaluate_fast
from opening.book import choose_book_move

# Large enough to dominate any positional score, small enough that adding a ply
# count to it never approaches the float infinities used as initial bounds.
MATE_VALUE = 1_000_000
MATE_THRESHOLD = MATE_VALUE - 1_000

EXACT, LOWER_BOUND, UPPER_BOUND = 0, 1, 2

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

PROMOTION_ORDER = {chess.KNIGHT: 1, chess.BISHOP: 2, chess.ROOK: 3, chess.QUEEN: 4}

TT_MOVE_SCORE = 1_000_000
PROMOTION_BASE = 900_000
CAPTURE_BASE = 800_000

# perf_counter() costs more than a node, so the clock is only read periodically.
NODES_PER_TIME_CHECK = 1024


class SearchTimeout(Exception):
    pass


class SearchContext:
    def __init__(self, deadline: float, table: dict, max_table_entries: int) -> None:
        self.deadline = deadline
        self.table = table
        self.max_table_entries = max_table_entries
        self.nodes = 0

    def count_node(self) -> None:
        self.nodes += 1
        if self.nodes % NODES_PER_TIME_CHECK == 0 and time.perf_counter() >= self.deadline:
            raise SearchTimeout()

    def store(self, key, depth: int, score: int, flag: int, move: chess.Move | None, ply: int) -> None:
        if len(self.table) >= self.max_table_entries:
            self.table.clear()
        self.table[key] = (depth, score_to_table(score, ply), flag, move)


class tabounV12:
    """V11 plus distance-to-mate scoring, a move-storing TT, and cheaper ordering."""

    def __init__(
        self,
        depth: int = 64,
        time_limit: float = 1.0,
        quiescence_depth: int = 6,
        max_table_entries: int = 1 << 20,
        use_book: bool = True,
    ) -> None:
        self.depth = depth
        self.time_limit = time_limit
        self.quiescence_depth = quiescence_depth
        self.max_table_entries = max_table_entries
        self.use_book = use_book
        self.transposition_table: dict = {}

    def choose_move(self, board: chess.Board) -> chess.Move:
        if self.use_book:
            book_move = choose_book_move(board)
            if book_move is not None:
                return book_move

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            raise ValueError("No legal moves available.")

        deadline = time.perf_counter() + self.time_limit
        context = SearchContext(deadline, self.transposition_table, self.max_table_entries)
        best_move = legal_moves[0]

        for current_depth in range(1, self.depth + 1):
            try:
                best_move = search_root(board, current_depth, best_move, context, self.quiescence_depth)
            except SearchTimeout:
                break

        return best_move


def search_root(
    board: chess.Board,
    depth: int,
    previous_best_move: chess.Move,
    context: SearchContext,
    quiescence_depth: int,
) -> chess.Move:
    white_to_play = board.turn == chess.WHITE
    best_score = -float("inf") if white_to_play else float("inf")
    alpha, beta = -float("inf"), float("inf")
    best_move = previous_best_move

    for move in order_moves(board, previous_best_move):
        board.push(move)
        try:
            score = alphabeta(board, depth - 1, alpha, beta, 1, context, quiescence_depth)
        finally:
            board.pop()

        if white_to_play and score > best_score:
            best_score, best_move = score, move
            alpha = max(alpha, best_score)
        elif not white_to_play and score < best_score:
            best_score, best_move = score, move
            beta = min(beta, best_score)

    return best_move


def alphabeta(
    board: chess.Board,
    depth: int,
    alpha: float,
    beta: float,
    ply: int,
    context: SearchContext,
    quiescence_depth: int,
) -> int:
    context.count_node()

    if is_draw(board):
        return 0

    key = board._transposition_key()
    table_move = None
    entry = context.table.get(key)
    if entry is not None:
        stored_depth, stored_score, stored_flag, table_move = entry
        if stored_depth >= depth:
            score = score_from_table(stored_score, ply)
            if stored_flag == EXACT:
                return score
            if stored_flag == UPPER_BOUND and score <= alpha:
                return score
            if stored_flag == LOWER_BOUND and score >= beta:
                return score

    if depth <= 0:
        return quiescence(board, alpha, beta, ply, context, quiescence_depth)

    moves = order_moves(board, table_move)
    if not moves:
        return terminal_score(board, ply)

    alpha_original, beta_original = alpha, beta
    white_to_play = board.turn == chess.WHITE
    best_score = -float("inf") if white_to_play else float("inf")
    best_move = moves[0]

    for move in moves:
        board.push(move)
        try:
            score = alphabeta(board, depth - 1, alpha, beta, ply + 1, context, quiescence_depth)
        finally:
            board.pop()

        if white_to_play:
            if score > best_score:
                best_score, best_move = score, move
            alpha = max(alpha, best_score)
        else:
            if score < best_score:
                best_score, best_move = score, move
            beta = min(beta, best_score)

        if alpha >= beta:
            break

    best_score = int(best_score)

    if best_score <= alpha_original:
        flag = UPPER_BOUND
    elif best_score >= beta_original:
        flag = LOWER_BOUND
    else:
        flag = EXACT

    context.store(key, depth, best_score, flag, best_move, ply)
    return best_score


def quiescence(
    board: chess.Board,
    alpha: float,
    beta: float,
    ply: int,
    context: SearchContext,
    remaining_depth: int,
) -> int:
    context.count_node()

    if board.is_check() and not any(board.generate_legal_moves()):
        return terminal_score(board, ply)

    stand_pat = evaluate_fast(board)
    if remaining_depth <= 0:
        return stand_pat

    white_to_play = board.turn == chess.WHITE

    if white_to_play:
        if stand_pat >= beta:
            return stand_pat
        alpha = max(alpha, stand_pat)
        best_score = stand_pat
    else:
        if stand_pat <= alpha:
            return stand_pat
        beta = min(beta, stand_pat)
        best_score = stand_pat

    for move in order_captures(board):
        board.push(move)
        try:
            score = quiescence(board, alpha, beta, ply + 1, context, remaining_depth - 1)
        finally:
            board.pop()

        if white_to_play:
            if score > best_score:
                best_score = score
            alpha = max(alpha, best_score)
        else:
            if score < best_score:
                best_score = score
            beta = min(beta, best_score)

        if alpha >= beta:
            break

    return best_score


def terminal_score(board: chess.Board, ply: int) -> int:
    """Score a position with no legal move. Mates closer to the root score higher."""
    if not board.is_check():
        return 0
    return -(MATE_VALUE - ply) if board.turn == chess.WHITE else MATE_VALUE - ply


def is_draw(board: chess.Board) -> bool:
    if board.halfmove_clock >= 100:
        return True
    if board.is_insufficient_material():
        return True
    # A repetition needs at least 4 reversible plies, and inside the search the
    # first repetition is already treated as a draw.
    return board.halfmove_clock >= 4 and board.is_repetition(2)


def score_to_table(score: int, ply: int) -> int:
    """Make a mate score independent of where the node sits in the tree."""
    if score > MATE_THRESHOLD:
        return score + ply
    if score < -MATE_THRESHOLD:
        return score - ply
    return score


def score_from_table(score: int, ply: int) -> int:
    if score > MATE_THRESHOLD:
        return score - ply
    if score < -MATE_THRESHOLD:
        return score + ply
    return score


def order_moves(board: chess.Board, table_move: chess.Move | None = None) -> list[chess.Move]:
    moves = list(board.legal_moves)
    moves.sort(key=lambda move: move_score(board, move, table_move), reverse=True)
    return moves


def order_captures(board: chess.Board) -> list[chess.Move]:
    captures = list(board.generate_legal_captures())
    captures.sort(key=lambda move: move_score(board, move, None), reverse=True)
    return captures


def move_score(board: chess.Board, move: chess.Move, table_move: chess.Move | None) -> int:
    if table_move is not None and move == table_move:
        return TT_MOVE_SCORE

    score = 0

    if move.promotion:
        score += PROMOTION_BASE + PROMOTION_ORDER.get(move.promotion, 0)

    if board.is_capture(move):
        if board.is_en_passant(move):
            victim_value = PIECE_VALUES[chess.PAWN]
        else:
            victim_value = PIECE_VALUES.get(board.piece_type_at(move.to_square), 0)
        attacker_value = PIECE_VALUES.get(board.piece_type_at(move.from_square), 0)
        score += CAPTURE_BASE + victim_value * 10 - attacker_value

    return score
