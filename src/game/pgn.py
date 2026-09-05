import io
from typing import List

import chess
import chess.pgn


def load_board_from_user_choice() -> chess.Board:
    choice = input("Load a position? n = new game, f = FEN, p = PGN > ").strip().lower()
    if choice == "f":
        fen = input("FEN > ").strip()
        try:
            return chess.Board(fen)
        except ValueError:
            print("Invalid FEN, starting a new game.")
    elif choice == "p":
        pgn_text = input("PGN on a single line > ").strip()
        if pgn_text:
            normalized = _normalize_single_line_pgn(pgn_text)
            game = chess.pgn.read_game(io.StringIO(normalized))
            if game:
                board = game.board()
                for move in game.mainline_moves():
                    board.push(move)
                return board
            print("Invalid PGN, starting a new game.")
    return chess.Board()


def _normalize_single_line_pgn(pgn_text: str) -> str:
    # A PGN pasted on one line needs a line break after each header tag,
    # otherwise python-chess misreads some of them.
    if "\n" not in pgn_text:
        pgn_text = pgn_text.replace("] ", "]\n")
    return pgn_text


def save_pgn_from_moves(moves: List[chess.Move], board: chess.Board) -> None:
    choice = input("Save the game as PGN? (y/n) > ").strip().lower()
    if choice != "y":
        return
    path = input("File path (for example game.pgn) > ").strip()
    if not path:
        print("No file given, PGN not saved.")
        return

    game = chess.pgn.Game()
    game.headers["Result"] = board.result(claim_draw=True)
    node = game
    for move in moves:
        node = node.add_variation(move)

    with open(path, "w", encoding="utf-8") as f:
        f.write(str(game))
    print(f"PGN saved to {path}")
