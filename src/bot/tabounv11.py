import chess

from bot.tabounv10 import tabounV10
from opening.book import choose_book_move


class tabounV11(tabounV10):
    """V10 with a Komodo Polyglot opening book."""

    def choose_move(self, board: chess.Board) -> chess.Move:
        book_move = choose_book_move(board)
        if book_move is not None:
            return book_move

        return super().choose_move(board)
