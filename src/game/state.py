import chess


def describe_outcome(board: chess.Board) -> str:
    outcome = board.outcome()
    if not outcome:
        return "Partie terminee."
    if outcome.winner is None:
        return f"Partie nulle ({outcome.termination.name.lower()})."
    if outcome.winner:
        return f"Vous gagnez ({outcome.termination.name.lower()})."
    return f"Le bot gagne ({outcome.termination.name.lower()})."


def describe_outcome_for_player(board: chess.Board, user_is_white: bool) -> str:
    outcome = board.outcome()
    if not outcome:
        return "Partie terminee."
    if outcome.winner is None:
        return f"Partie nulle ({outcome.termination.name.lower()})."
    if outcome.winner == user_is_white:
        return f"Vous gagnez ({outcome.termination.name.lower()})."
    return f"Le bot gagne ({outcome.termination.name.lower()})."
