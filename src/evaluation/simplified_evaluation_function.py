import chess

"""
The content of this script is a proposed implementation of a work originally posted by Tomasz Michniewski on the Polish chess 
programming discussion list (progszach) that I discovered on chessprogramming.org. 

https://www.chessprogramming.org/Simplified_Evaluation_Function
"""



MATE_SCORE = 10000000

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
}


PAWN_PST = [
    0, 0, 0, 0, 0, 0, 0, 0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, -5, -10, 0, 0, -10, -5, 5,
    5, 10, 10, -20, -20, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]

KNIGHT_PST = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_PST = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_PST = [
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, 10, 10, 10, 10, 5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    0, 0, 0, 5, 5, 0, 0, 0,
]

QUEEN_PST = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5,
    -10, 5, 5, 5, 5, 5, 0, -10,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20,
]

KING_MIDGAME_PST = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20,
]

KING_ENDGAME_PST = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10, 0, 0, -10, -20, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -30, 0, 0, 0, 0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
]


def evaluate_simplified(board: chess.Board) -> int:
    """
    Returns an evaluation score from White's perspective:
    - positive score: White is better
    - negative score: Black is better
    """
    outcome = board.outcome(claim_draw=True)
    if outcome is not None:
        if outcome.winner is None:
            return 0
        return MATE_SCORE if outcome.winner == chess.WHITE else -MATE_SCORE

    endgame = is_endgame(board)

    score = 0

    score += _score_piece_type(board, chess.PAWN, PAWN_PST)
    score += _score_piece_type(board, chess.KNIGHT, KNIGHT_PST)
    score += _score_piece_type(board, chess.BISHOP, BISHOP_PST)
    score += _score_piece_type(board, chess.ROOK, ROOK_PST)
    score += _score_piece_type(board, chess.QUEEN, QUEEN_PST)

    king_table = KING_ENDGAME_PST if endgame else KING_MIDGAME_PST
    score += _score_king(board, king_table)

    return score


def is_endgame(board: chess.Board) -> bool:
    white_queens = len(board.pieces(chess.QUEEN, chess.WHITE))
    black_queens = len(board.pieces(chess.QUEEN, chess.BLACK))

    if white_queens == 0 and black_queens == 0:
        return True

    if white_queens > 0 and _queen_side_is_light(board, chess.WHITE):
        return True

    if black_queens > 0 and _queen_side_is_light(board, chess.BLACK):
        return True

    return False


def _queen_side_is_light(board: chess.Board, color: chess.Color) -> bool:
    rooks = len(board.pieces(chess.ROOK, color))
    bishops = len(board.pieces(chess.BISHOP, color))
    knights = len(board.pieces(chess.KNIGHT, color))
    minor_pieces = bishops + knights
    return rooks == 0 and minor_pieces <= 1


def _score_piece_type(board: chess.Board, piece_type: chess.PieceType, pst: list[int]) -> int:
    value = PIECE_VALUES[piece_type]
    score = 0

    for square in board.pieces(piece_type, chess.WHITE):
        score += value
        score += _pst_value_for_white(square, pst)

    for square in board.pieces(piece_type, chess.BLACK):
        score -= value
        score -= _pst_value_for_black(square, pst)

    return score


def _score_king(board: chess.Board, king_table: list[int]) -> int:
    score = 0

    white_king_squares = list(board.pieces(chess.KING, chess.WHITE))
    black_king_squares = list(board.pieces(chess.KING, chess.BLACK))

    if white_king_squares:
        score += _pst_value_for_white(white_king_squares[0], king_table)

    if black_king_squares:
        score -= _pst_value_for_black(black_king_squares[0], king_table)

    return score


def _pst_value_for_white(square: chess.Square, table_rank8_to1: list[int]) -> int:
    file_index = chess.square_file(square)
    rank_index = chess.square_rank(square)
    table_index = (7 - rank_index) * 8 + file_index
    return table_rank8_to1[table_index]


def _pst_value_for_black(square: chess.Square, table_rank8_to1: list[int]) -> int:
    mirrored = chess.square_mirror(square)
    return _pst_value_for_white(mirrored, table_rank8_to1)

