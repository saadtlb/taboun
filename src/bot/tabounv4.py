import chess

from evaluation.simplified_evaluation_function import evaluate_simplified


class tabounV4:
    """Alpha-beta bot with simplified evaluation"""

    def __init__(self, depth: int = 3) -> None:
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
        return evaluate_simplified(board)

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return evaluate_simplified(board)

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
