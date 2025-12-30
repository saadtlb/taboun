import random
import chess


class tabounV1:
    """Bot that selects a random legal move on the given board."""

    def choose_move(self, board: chess.Board) -> chess.Move:
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            raise ValueError("No legal moves available.")
        return random.choice(legal_moves)
