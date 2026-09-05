import chess

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
}

MATE_SCORE = 10000000


def evaluate_material(board: chess.Board) -> int:
    outcome = board.outcome(claim_draw=True)  # is the game over?
    if outcome is not None:
        if outcome.winner is None:
            return 0  # draw
        return MATE_SCORE if outcome.winner == chess.WHITE else -MATE_SCORE  # White or Black wins

    white_score = 0
    black_score = 0

    for piece_type, value in PIECE_VALUES.items():
        white_score += len(board.pieces(piece_type, chess.WHITE)) * value
        black_score += len(board.pieces(piece_type, chess.BLACK)) * value

    return white_score - black_score
