import chess

from evaluation.simplified_evaluation_function import evaluate_simplified


class tabounV3:
    """Minimax bot using a simplified evaluation (material + piece-square tables)."""

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

        for move in legal_moves:
            board.push(move)
            score = minimax(board, self.depth - 1)
            board.pop()

            if is_white_to_play and score > best_score:
                best_score = score
                best_move = move
            elif not is_white_to_play and score < best_score:
                best_score = score
                best_move = move

        return best_move


def minimax(board: chess.Board, depth: int) -> int:
    if depth == 0 or board.is_game_over():
        return evaluate_simplified(board)

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return evaluate_simplified(board)

    is_white_to_play = board.turn == chess.WHITE

    if is_white_to_play:
        best_score = -float("inf")
        for move in legal_moves:
            board.push(move)
            score = minimax(board, depth - 1)
            board.pop()
            if score > best_score:
                best_score = score
        return best_score

    best_score = float("inf")
    for move in legal_moves:
        board.push(move)
        score = minimax(board, depth - 1)
        board.pop()
        if score < best_score:
            best_score = score
    return best_score

