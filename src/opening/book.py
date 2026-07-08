from pathlib import Path

import chess
import chess.polyglot


DEFAULT_BOOK_PATH = Path(__file__).resolve().parents[2] / "data" / "openings" / "books" / "komodo3.bin"


def choose_book_move(board: chess.Board, book_path: Path = DEFAULT_BOOK_PATH) -> chess.Move | None:
    if not book_path.exists():
        return None

    try:
        with chess.polyglot.open_reader(str(book_path)) as reader:
            entry = reader.weighted_choice(board)
    except IndexError:
        return None

    if entry.move not in board.legal_moves:
        return None

    return entry.move
