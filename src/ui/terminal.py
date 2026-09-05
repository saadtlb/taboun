from typing import List

import chess


def prompt_player_move(board: chess.Board) -> chess.Move | None:
    """Ask for a move in SAN or UCI until a legal one is given.

    Typing ``resign`` (or ``quit``, ``exit``) and confirming returns None.
    """
    while True:
        user_input = input("Your move (SAN or UCI), or resign > ").strip()
        if not user_input:
            print("Please enter a move.")
            continue

        if user_input.lower() in {"resign", "quit", "exit"}:
            confirm = input("Confirm resignation? (y/n) > ").strip().lower()
            if confirm == "y":
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

        print("Illegal move. Try again.")


def format_san_history(start_board: chess.Board, moves: List[chess.Move]) -> str:
    if not moves:
        return "(no moves yet)"
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
