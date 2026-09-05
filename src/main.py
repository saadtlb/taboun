from typing import Optional

import chess

from src.bot import BOT_REGISTRY
from src.game.pgn import load_board_from_user_choice
from src.game.runner import run_bot_vs_bot, run_human_vs_bot


def select_bot(prompt: str = "Choisis le bot"):
    bots = list(BOT_REGISTRY.items())
    if not bots:
        raise ValueError("Aucun bot disponible.")
    while True:
        print("Bots disponibles:")
        for index, (name, _) in enumerate(bots, start=1):
            print(f"{index}) {name}")

        choice = input(f"{prompt} (nom ou numero): ").strip().lower()
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(bots):
                return bots[index - 1][1]()
        else:
            for name, bot_class in bots:
                if choice == name.lower():
                    return bot_class()

        print("Choix invalide. Reessaie.")


def choose_color() -> bool:
    choice = input("Tu veux jouer (b)lancs ou (n)oirs ? ").strip().lower()
    return choice != "n"  # défaut: blancs


def choose_mode() -> str:
    while True:
        choice = input("Mode: 1) humain vs bot  2) bot vs bot : ").strip()
        if choice == "1":
            return "human_vs_bot"
        if choice == "2":
            return "bot_vs_bot"
        print("Choix invalide. Tape 1 ou 2.")


def main() -> None:
    board = load_board_from_user_choice()
    mode = choose_mode()
    user_is_white: Optional[bool] = None

    if mode == "human_vs_bot":
        bot = select_bot()
        user_is_white = choose_color()
        run_human_vs_bot(board, bot, user_is_white)
    else:
        bot_white = select_bot("Bot pour les blancs")
        bot_black = select_bot("Bot pour les noirs")
        run_bot_vs_bot(board, bot_white, bot_black)


if __name__ == "__main__":
    main()
