"""Evaluation for tabounV12.

Unlike `evaluate_simplified` and `evaluate_improved`, this function never scores
mate, stalemate or draws. Detecting them here is both slow and wrong: the
evaluation cannot see the search depth, so every mate scores the same and the
engine has no reason to prefer a mate in 1 over a mate in 7. tabounV12 detects
terminal positions in the search, where `ply` is known.

Callers must therefore only pass positions that are not game over.
"""

import chess

from src.evaluation.simplified_evaluation_function import (
    BISHOP_PST,
    KING_ENDGAME_PST,
    KING_MIDGAME_PST,
    KNIGHT_PST,
    PAWN_PST,
    PIECE_VALUES,
    QUEEN_PST,
    ROOK_PST,
    index_by_square,
    is_endgame,
)

_PST = {
    chess.PAWN: index_by_square(PAWN_PST),
    chess.KNIGHT: index_by_square(KNIGHT_PST),
    chess.BISHOP: index_by_square(BISHOP_PST),
    chess.ROOK: index_by_square(ROOK_PST),
    chess.QUEEN: index_by_square(QUEEN_PST),
}
_KING_MG = index_by_square(KING_MIDGAME_PST)
_KING_EG = index_by_square(KING_ENDGAME_PST)

_PIECE_TYPES = (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)

_FILE_MASKS = [chess.BB_FILES[file_index] for file_index in range(8)]
_ADJACENT_FILE_MASKS = [
    (chess.BB_FILES[file_index - 1] if file_index > 0 else 0)
    | (chess.BB_FILES[file_index + 1] if file_index < 7 else 0)
    for file_index in range(8)
]


def _passed_pawn_masks(color: chess.Color) -> list[int]:
    masks = []
    for square in chess.SQUARES:
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)
        span = _FILE_MASKS[file_index] | _ADJACENT_FILE_MASKS[file_index]
        if color == chess.WHITE:
            ahead = ~0 << (8 * (rank_index + 1))
        else:
            ahead = (1 << (8 * rank_index)) - 1
        masks.append(span & ahead & chess.BB_ALL)
    return masks


_PASSED_MASKS = {chess.WHITE: _passed_pawn_masks(chess.WHITE), chess.BLACK: _passed_pawn_masks(chess.BLACK)}

MOBILITY_WEIGHT = 2
BISHOP_PAIR_BONUS = 30
DOUBLED_PAWN_PENALTY = 15
ISOLATED_PAWN_PENALTY = 10
PASSED_PAWN_BASE = 20
PASSED_PAWN_PER_RANK = 8
PAWN_SHIELD_BONUS = 8
CENTRAL_KING_PENALTY = 25
CASTLED_KING_BONUS = 15


def evaluate_fast(board: chess.Board) -> int:
    """Score a non-terminal position from White's perspective."""
    score = _material_and_placement(board)
    score += _mobility(board)
    score += _bishop_pair(board)
    score += _pawn_structure(board)
    score += _king_safety(board)
    return score


def _material_and_placement(board: chess.Board) -> int:
    score = 0

    for piece_type in _PIECE_TYPES:
        value = PIECE_VALUES[piece_type]
        white_table, black_table = _PST[piece_type]
        for square in board.pieces(piece_type, chess.WHITE):
            score += value + white_table[square]
        for square in board.pieces(piece_type, chess.BLACK):
            score -= value + black_table[square]

    white_table, black_table = _KING_EG if is_endgame(board) else _KING_MG

    white_king = board.king(chess.WHITE)
    if white_king is not None:
        score += white_table[white_king]

    black_king = board.king(chess.BLACK)
    if black_king is not None:
        score -= black_table[black_king]

    return score


def _mobility(board: chess.Board) -> int:
    """Attacked-square count, a cheap stand-in for a legal move count."""
    white = 0
    black = 0

    for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        for square in board.pieces(piece_type, chess.WHITE):
            white += chess.popcount(board.attacks_mask(square) & ~board.occupied_co[chess.WHITE])
        for square in board.pieces(piece_type, chess.BLACK):
            black += chess.popcount(board.attacks_mask(square) & ~board.occupied_co[chess.BLACK])

    return (white - black) * MOBILITY_WEIGHT


def _bishop_pair(board: chess.Board) -> int:
    score = 0
    if chess.popcount(board.bishops & board.occupied_co[chess.WHITE]) >= 2:
        score += BISHOP_PAIR_BONUS
    if chess.popcount(board.bishops & board.occupied_co[chess.BLACK]) >= 2:
        score -= BISHOP_PAIR_BONUS
    return score


def _pawn_structure(board: chess.Board) -> int:
    white_pawns = board.pawns & board.occupied_co[chess.WHITE]
    black_pawns = board.pawns & board.occupied_co[chess.BLACK]
    return _pawns_for_color(white_pawns, black_pawns, chess.WHITE) - _pawns_for_color(
        black_pawns, white_pawns, chess.BLACK
    )


def _pawns_for_color(own_pawns: int, enemy_pawns: int, color: chess.Color) -> int:
    score = 0

    for file_index in range(8):
        count = chess.popcount(own_pawns & _FILE_MASKS[file_index])
        if count > 1:
            score -= (count - 1) * DOUBLED_PAWN_PENALTY
        if count and not own_pawns & _ADJACENT_FILE_MASKS[file_index]:
            score -= count * ISOLATED_PAWN_PENALTY

    masks = _PASSED_MASKS[color]
    for square in chess.scan_forward(own_pawns):
        if enemy_pawns & masks[square]:
            continue
        rank_index = chess.square_rank(square)
        progress = rank_index if color == chess.WHITE else 7 - rank_index
        score += PASSED_PAWN_BASE + progress * PASSED_PAWN_PER_RANK

    return score


def _king_safety(board: chess.Board) -> int:
    if is_endgame(board):
        return 0
    return _king_safety_for_color(board, chess.WHITE) - _king_safety_for_color(board, chess.BLACK)


def _king_safety_for_color(board: chess.Board, color: chess.Color) -> int:
    king_square = board.king(color)
    if king_square is None:
        return 0

    score = 0
    king_file = chess.square_file(king_square)
    king_rank = chess.square_rank(king_square)

    if king_file in (3, 4):
        score -= CENTRAL_KING_PENALTY

    shield_rank = king_rank + 1 if color == chess.WHITE else king_rank - 1
    if 0 <= shield_rank <= 7:
        own_pawns = board.pawns & board.occupied_co[color]
        shield = 0
        for file_index in range(max(0, king_file - 1), min(7, king_file + 1) + 1):
            shield |= chess.BB_SQUARES[chess.square(file_index, shield_rank)]
        score += chess.popcount(own_pawns & shield) * PAWN_SHIELD_BONUS

    back_rank = 0 if color == chess.WHITE else 7
    if king_rank == back_rank and king_file not in (3, 4):
        score += CASTLED_KING_BONUS

    return score
