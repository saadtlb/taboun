import chess

from bot.tabounv10 import tabounV10
from opening.book import choose_book_move


class tabounV11(tabounV10):
    """V10 with a Komodo Polyglot opening book."""

    def __init__(
        self,
        depth: int = 4,
        time_limit: float = 1.0,
        quiescence_depth: int = 4,
        use_book: bool = True,
    ) -> None:
        super().__init__(depth=depth, time_limit=time_limit, quiescence_depth=quiescence_depth)
        self.use_book = use_book

    def choose_move(self, board: chess.Board) -> chess.Move:
        if self.use_book:
            book_move = choose_book_move(board)
            if book_move is not None:
                return book_move

        return super().choose_move(board)
