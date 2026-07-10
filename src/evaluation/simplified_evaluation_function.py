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


def terminal_score(board: chess.Board) -> int | None:
    """
    Score of a finished game from White's perspective, or None if the game goes on.

    Equivalent to inspecting ``board.outcome(claim_draw=True)`` but far cheaper:
    ``outcome`` unconditionally runs ``can_claim_threefold_repetition()``, which
    replays the move stack and then pushes every legal move. The two clock guards
    below skip that work when a claim is arithmetically impossible:
    - a fifty-move claim needs halfmove_clock >= 99,
    - a threefold claim needs the position (or one a legal move away) to have
      occurred twice already, which takes at least 3 reversible plies.
    Variant conditions are not checked: these bots only ever play standard chess.
    """
    if board.is_checkmate():
        return -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
    if board.is_insufficient_material():
        return 0
    if not any(board.generate_legal_moves()):
        return 0
    if board.is_seventyfive_moves():
        return 0
    if board.is_fivefold_repetition():
        return 0
    if board.halfmove_clock >= 99 and board.can_claim_fifty_moves():
        return 0
    if board.halfmove_clock >= 3 and board.can_claim_threefold_repetition():
        return 0
    return None


def static_score_simplified(board: chess.Board) -> int:
    """Material plus piece-square tables, assuming the game is not over."""
    score = 0

    for piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        value = PIECE_VALUES[piece_type]
        white_table, black_table = _PST_BY_SQUARE[piece_type]
        for square in board.pieces(piece_type, chess.WHITE):
            score += value + white_table[square]
        for square in board.pieces(piece_type, chess.BLACK):
            score -= value + black_table[square]

    white_table, black_table = _KING_EG_BY_SQUARE if is_endgame(board) else _KING_MG_BY_SQUARE

    white_king = board.king(chess.WHITE)
    if white_king is not None:
        score += white_table[white_king]

    black_king = board.king(chess.BLACK)
    if black_king is not None:
        score -= black_table[black_king]

    return score


def evaluate_simplified(board: chess.Board) -> int:
    """
    Returns an evaluation score from White's perspective:
    - positive score: White is better
    - negative score: Black is better
    """
    terminal = terminal_score(board)
    if terminal is not None:
        return terminal

    return static_score_simplified(board)


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


def _pst_value_for_white(square: chess.Square, table_rank8_to1: list[int]) -> int:
    file_index = chess.square_file(square)
    rank_index = chess.square_rank(square)
    table_index = (7 - rank_index) * 8 + file_index
    return table_rank8_to1[table_index]


def _pst_value_for_black(square: chess.Square, table_rank8_to1: list[int]) -> int:
    mirrored = chess.square_mirror(square)
    return _pst_value_for_white(mirrored, table_rank8_to1)


def _index_by_square(table_rank8_to1: list[int]) -> tuple[list[int], list[int]]:
    white = [_pst_value_for_white(square, table_rank8_to1) for square in chess.SQUARES]
    black = [_pst_value_for_black(square, table_rank8_to1) for square in chess.SQUARES]
    return white, black


_PST_BY_SQUARE = {
    chess.PAWN: _index_by_square(PAWN_PST),
    chess.KNIGHT: _index_by_square(KNIGHT_PST),
    chess.BISHOP: _index_by_square(BISHOP_PST),
    chess.ROOK: _index_by_square(ROOK_PST),
    chess.QUEEN: _index_by_square(QUEEN_PST),
}

_KING_MG_BY_SQUARE = _index_by_square(KING_MIDGAME_PST)
_KING_EG_BY_SQUARE = _index_by_square(KING_ENDGAME_PST)

