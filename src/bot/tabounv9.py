import chess
import chess.polyglot

from evaluation.improved_evaluation_function import evaluate_improved


class tabounV9:
    """V8 search with an improved positional evaluation."""

    def __init__(self, depth: int = 2) -> None:
        self.depth = depth
        self.transposition_table: dict[int, tuple[int, int, str]] = {}

    def choose_move(self, board: chess.Board) -> chess.Move:
        legal_moves = order_moves(board)
        if not legal_moves:
            raise ValueError("No legal moves available.")

        best_move = legal_moves[0]

        for current_depth in range(1, self.depth + 1):
            is_white_to_play = board.turn == chess.WHITE

            if is_white_to_play:
                best_score = -float("inf")
            else:
                best_score = float("inf")

            alpha = -float("inf")
            beta = float("inf")
            current_best_move = best_move

            for move in order_moves(board, best_move):
                board.push(move)
                score = alphabeta(board, current_depth - 1, alpha, beta, self.transposition_table)
                board.pop()

                if is_white_to_play and score > best_score:
                    best_score = score
                    current_best_move = move
                    alpha = max(alpha, best_score)
                elif not is_white_to_play and score < best_score:
                    best_score = score
                    current_best_move = move
                    beta = min(beta, best_score)

            best_move = current_best_move

        return best_move


def alphabeta(
    board: chess.Board,
    depth: int,
    alpha: float,
    beta: float,
    table: dict[int, tuple[int, int, str]],
) -> int:
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
        return quiescence(board, alpha, beta)

    legal_moves = order_moves(board)
    if not legal_moves:
        return quiescence(board, alpha, beta)

    if board.turn == chess.WHITE:
        best_score = -float("inf")
        for move in legal_moves:
            board.push(move)
            score = alphabeta(board, depth - 1, alpha, beta, table)
            board.pop()
            if score > best_score:
                best_score = score
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
    else:
        best_score = float("inf")
        for move in legal_moves:
            board.push(move)
            score = alphabeta(board, depth - 1, alpha, beta, table)
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


def quiescence(board: chess.Board, alpha: float, beta: float) -> int:
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
        if not board.is_capture(move):
            continue
        board.push(move)
        score = quiescence(board, alpha, beta)
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
