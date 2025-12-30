from typing import List

import chess


def prompt_player_move(board: chess.Board) -> chess.Move | None:
    """Request a move from the user in SAN or UCI until a legal move is given.
    Type 'abandon' to resign (returns None).
    """
    while True:
        user_input = input("Votre coup (SAN ou UCI) / 'abandon': ").strip()
        if not user_input:
            print("Merci d'entrer un coup.")
            continue

        if user_input.lower() in {"abandon", "resign", "quit", "exit"}:
            confirm = input("Confirmer l'abandon ? (o/n): ").strip().lower()
            if confirm == "o":
                return None
            continue

        move = None
        try:
            move = board.parse_san(user_input)
        except ValueError:
            try:
                candidate = chess.Move.from_uci(user_input)
                if candidate in board.legal_moves:
                    move = candidate
            except ValueError:
                move = None

        if move and move in board.legal_moves:
            return move

        print("Coup invalide. Essayez encore.")


def format_san_history(start_board: chess.Board, moves: List[chess.Move]) -> str:
    if not moves:
        return "(aucun coup)"
    board = start_board.copy(stack=False)
    tokens: List[str] = []
    for move in moves:
        san = board.san(move)
        if board.turn == chess.WHITE:
            tokens.append(f"{board.fullmove_number}. {san}")
        else:
            tokens.append(san)
        board.push(move)
    return " ".join(tokens)
