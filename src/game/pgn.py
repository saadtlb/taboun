import io
from typing import List

import chess
import chess.pgn


def load_board_from_user_choice() -> chess.Board:
    choice = input("Charger une position ? (n=non, f=FEN, p=PGN): ").strip().lower()
    if choice == "f":
        fen = input("FEN: ").strip()
        try:
            return chess.Board(fen)
        except ValueError:
            print("FEN invalide, on démarre une nouvelle partie.")
    elif choice == "p":
        pgn_text = input("PGN (sur une seule ligne): ").strip()
        if pgn_text:
            normalized = _normalize_single_line_pgn(pgn_text)
            game = chess.pgn.read_game(io.StringIO(normalized))
            if game:
                board = game.board()
                for move in game.mainline_moves():
                    board.push(move)
                return board
            print("PGN invalide, on démarre une nouvelle partie.")
    return chess.Board()


def _normalize_single_line_pgn(pgn_text: str) -> str:
    #si tout est sur une seule ligne, on insère des sauts de ligne après chaque header pour aider le parser PGN.
    #problème sur certains pgn
    if "\n" not in pgn_text:
        pgn_text = pgn_text.replace("] ", "]\n")
    return pgn_text


def save_pgn_from_moves(moves: List[chess.Move], board: chess.Board) -> None:
    choice = input("Sauvegarder la partie en PGN ? (o/n): ").strip().lower()
    if choice != "o":
        return
    path = input("Chemin du fichier (ex: partie.pgn): ").strip()
    if not path:
        print("Aucun fichier fourni, PGN non sauvegardé.")
        return

    game = chess.pgn.Game()
    game.headers["Result"] = board.result(claim_draw=True)
    node = game
    for move in moves:
        node = node.add_variation(move)

    with open(path, "w", encoding="utf-8") as f:
        f.write(str(game))
    print(f"PGN sauvegardé dans {path}")
