import chess

from src.evaluation.simplified_evaluation_function import is_endgame, static_score_simplified, terminal_score


def evaluate_improved(board: chess.Board) -> int:
    """
    Returns an evaluation score from White's perspective.
    Positive score means White is better, negative score means Black is better.
    """
    terminal = terminal_score(board)
    if terminal is not None:
        return terminal

    score = static_score_simplified(board)

    score += evaluate_mobility(board)
    score += evaluate_bishop_pair(board)
    score += evaluate_pawn_structure(board)
    score += evaluate_king_safety(board)
    score += evaluate_development(board)

    return score


def evaluate_mobility(board: chess.Board) -> int:
    white_mobility = count_legal_moves_for_color(board, chess.WHITE)
    black_mobility = count_legal_moves_for_color(board, chess.BLACK)
    return (white_mobility - black_mobility) * 2


def evaluate_bishop_pair(board: chess.Board) -> int:
    score = 0

    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        score += 30
    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        score -= 30

    return score


def evaluate_pawn_structure(board: chess.Board) -> int:
    score = 0

    score += evaluate_doubled_pawns(board, chess.WHITE)
    score -= evaluate_doubled_pawns(board, chess.BLACK)
    score += evaluate_isolated_pawns(board, chess.WHITE)
    score -= evaluate_isolated_pawns(board, chess.BLACK)
    score += evaluate_passed_pawns(board, chess.WHITE)
    score -= evaluate_passed_pawns(board, chess.BLACK)

    return score


def evaluate_doubled_pawns(board: chess.Board, color: chess.Color) -> int:
    penalty = 0

    for file_index in range(8):
        pawns_on_file = 0
        for square in board.pieces(chess.PAWN, color):
            if chess.square_file(square) == file_index:
                pawns_on_file += 1
        if pawns_on_file > 1:
            penalty -= (pawns_on_file - 1) * 15

    return penalty


def evaluate_isolated_pawns(board: chess.Board, color: chess.Color) -> int:
    penalty = 0
    pawn_files = set()

    for square in board.pieces(chess.PAWN, color):
        pawn_files.add(chess.square_file(square))

    for square in board.pieces(chess.PAWN, color):
        file_index = chess.square_file(square)
        has_left_neighbor = file_index - 1 in pawn_files
        has_right_neighbor = file_index + 1 in pawn_files

        if not has_left_neighbor and not has_right_neighbor:
            penalty -= 10

    return penalty


def evaluate_passed_pawns(board: chess.Board, color: chess.Color) -> int:
    bonus = 0

    for square in board.pieces(chess.PAWN, color):
        if is_passed_pawn(board, square, color):
            rank = chess.square_rank(square)
            if color == chess.WHITE:
                progress = rank
            else:
                progress = 7 - rank
            bonus += 20 + progress * 8

    return bonus


def is_passed_pawn(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    file_index = chess.square_file(square)
    rank = chess.square_rank(square)
    enemy_color = not color

    for enemy_square in board.pieces(chess.PAWN, enemy_color):
        enemy_file = chess.square_file(enemy_square)
        enemy_rank = chess.square_rank(enemy_square)

        if abs(enemy_file - file_index) > 1:
            continue

        if color == chess.WHITE and enemy_rank > rank:
            return False
        if color == chess.BLACK and enemy_rank < rank:
            return False

    return True


def evaluate_king_safety(board: chess.Board) -> int:
    if is_endgame(board):
        return 0

    return king_safety_for_color(board, chess.WHITE) - king_safety_for_color(board, chess.BLACK)


def king_safety_for_color(board: chess.Board, color: chess.Color) -> int:
    king_square = board.king(color)
    if king_square is None:
        return 0

    score = 0
    king_file = chess.square_file(king_square)
    king_rank = chess.square_rank(king_square)

    if king_file in [3, 4]:
        score -= 25

    score += count_pawn_shield(board, king_square, color) * 8

    if king_rank in back_ranks_for_color(color) and king_file in [0, 1, 2, 5, 6, 7]:
        score += 15

    return score


def count_pawn_shield(board: chess.Board, king_square: chess.Square, color: chess.Color) -> int:
    king_file = chess.square_file(king_square)
    king_rank = chess.square_rank(king_square)
    shield_rank = king_rank + 1 if color == chess.WHITE else king_rank - 1
    count = 0

    if shield_rank < 0 or shield_rank > 7:
        return 0

    for file_index in [king_file - 1, king_file, king_file + 1]:
        if file_index < 0 or file_index > 7:
            continue
        square = chess.square(file_index, shield_rank)
        piece = board.piece_at(square)
        if piece == chess.Piece(chess.PAWN, color):
            count += 1

    return count


def evaluate_development(board: chess.Board) -> int:
    if is_endgame(board) or board.fullmove_number > 15:
        return 0

    score = 0

    score -= undeveloped_piece_penalty(board, chess.WHITE)
    score += undeveloped_piece_penalty(board, chess.BLACK)

    return score


def undeveloped_piece_penalty(board: chess.Board, color: chess.Color) -> int:
    penalty = 0

    for square in starting_minor_piece_squares(color):
        piece = board.piece_at(square)
        if piece is not None and piece.color == color and piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
            penalty += 12

    return penalty


def count_legal_moves_for_color(board: chess.Board, color: chess.Color) -> int:
    if board.turn == color:
        return board.legal_moves.count()

    # Flipping the side to move in place avoids copying the board. Move generation
    # reads only turn, occupancy, castling rights and ep_square, so the count is
    # the same as on a copy; the original turn is always restored.
    board.turn = color
    try:
        return board.legal_moves.count()
    finally:
        board.turn = not color


def starting_minor_piece_squares(color: chess.Color) -> list[chess.Square]:
    if color == chess.WHITE:
        return [chess.B1, chess.C1, chess.F1, chess.G1]
    return [chess.B8, chess.C8, chess.F8, chess.G8]


def back_ranks_for_color(color: chess.Color) -> list[int]:
    if color == chess.WHITE:
        return [0]
    return [7]
