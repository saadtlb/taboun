import chess

from bot.tabounv1 import tabounV1
from bot.tabounv2 import tabounV2


def prompt_player_move(board: chess.Board) -> chess.Move | None:
    """Request a move from the user in SAN or UCI until a legal move is given.
    Type 'abandon' to resign (returns None).
    """
    while True:
        user_input = input("Votre coup (SAN ou UCI) / 'abandon': ").strip()
        if not user_input:
            print("Merci d'entrer un coup.")
            continue

        if user_input.lower() in {"abandon", "resign", "quit", "exit"}: #fonction d'abandon
            return None

        move = None
        try:
            move = board.parse_san(user_input) #essaye d'abord de parser le coup en SAN
        except ValueError:
            try:
                candidate = chess.Move.from_uci(user_input) #essaye ensuite de parser le coup en UCI
                if candidate in board.legal_moves:
                    move = candidate
            except ValueError:
                move = None

        if move and move in board.legal_moves:
            return move

        print("Coup invalide. Essayez encore.")


def describe_outcome(board: chess.Board) -> str:
    outcome = board.outcome() #obtenir le resultat de la partie, si outcome est None la partie n'est pas terminee
    if not outcome: 
        return "Partie terminee."
    if outcome.winner is None:
        return f"Partie nulle ({outcome.termination.name.lower()})."
    if outcome.winner:
        return f"Vous gagnez ({outcome.termination.name.lower()})."
    return f"Le bot gagne ({outcome.termination.name.lower()})."


def select_bot():
    while True:
        choice = input("Choisis le bot: 1) tabounV1 (random)  2) tabounV2 (minimax): ").strip()
        if choice == "1":
            return tabounV1()
        if choice == "2":
            return tabounV2()
        print("Choix invalide. Tape 1 ou 2.")


def main() -> None:
    board = chess.Board()
    bot = select_bot()
    print("Bienvenue ! Vous jouez les blancs contre un bot.\n")

    while not board.is_game_over():
        print(board)
        player_move = prompt_player_move(board) #demande le coup du joueur
        board.push(player_move)

        if board.is_game_over(): 
            break

        bot_move = bot.choose_move(board) #le bot choisit son coup
        bot_move_san = board.san(bot_move) #convertit le coup du bot en SAN pour l'affichage
        board.push(bot_move)   #le bot joue son coup
        print(f"Bot joue : {bot_move_san}\n")

    print(board)
    print(describe_outcome(board))


if __name__ == "__main__":
    main()
