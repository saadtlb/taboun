import chess

from evaluation.simplified_evaluation_function import evaluate_simplified


class tabounV6:
    """Alpha-beta bot with simplified evaluation and quiescence search."""

    def __init__(self, depth: int = 2) -> None:
        self.depth = depth

    def choose_move(self, board: chess.Board) -> chess.Move:
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            raise ValueError("No legal moves available.")

        is_white_to_play = board.turn == chess.WHITE

        if is_white_to_play:
            best_score = -float("inf")
        else:
            best_score = float("inf")

        best_move = legal_moves[0]
        alpha = -float("inf")
        beta = float("inf")

        for move in legal_moves:
            board.push(move)
            score = alphabeta(board, self.depth - 1, alpha, beta)
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


def alphabeta(board: chess.Board, depth: int, alpha: float, beta: float) -> int:
    if depth == 0 or board.is_game_over():
        return quiescence(board, alpha, beta)

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return quiescence(board, alpha, beta)

    if board.turn == chess.WHITE:
        best_score = -float("inf")
        for move in legal_moves:
            board.push(move)
            score = alphabeta(board, depth - 1, alpha, beta)
            board.pop()
            if score > best_score:
                best_score = score
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
        return best_score

    best_score = float("inf")
    for move in legal_moves:
        board.push(move)
        score = alphabeta(board, depth - 1, alpha, beta)
        board.pop()
        if score < best_score:
            best_score = score
        beta = min(beta, best_score)
        if beta <= alpha:
            break
    return best_score


def quiescence(board: chess.Board, alpha: float, beta: float) -> int:
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
