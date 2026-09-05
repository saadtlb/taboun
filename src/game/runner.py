from typing import List

import chess

from src.game.pgn import save_pgn_from_moves
from src.ui.terminal import prompt_player_move, format_san_history


def run_human_vs_bot(
    board: chess.Board,
    bot,
    user_is_white: bool,
) -> None:
    start_board = board.copy(stack=False)
    move_history: List[chess.Move] = []
    resigned = False

    print(f"Welcome. You play {'white' if user_is_white else 'black'} against {bot.__class__.__name__}.\n")

    while not board.is_game_over():
        print(board)
        if move_history:
            print("Moves so far", format_san_history(start_board, move_history))

        user_to_play = (board.turn == chess.WHITE and user_is_white) or (board.turn == chess.BLACK and not user_is_white)

        if user_to_play:
            player_move = prompt_player_move(board)
            if player_move is None:
                resigned = True
                print("You resign.")
                break
            board.push(player_move)
            move_history.append(player_move)
        else:
            bot_move = bot.choose_move(board)
            bot_move_san = board.san(bot_move)
            board.push(bot_move)
            move_history.append(bot_move)
            print(f"Bot plays {bot_move_san}\n")

    print(board)
    if not resigned:
        _print_human_vs_bot_outcome(board, user_is_white, bot)
        save_pgn_from_moves(move_history, board)


def run_bot_vs_bot(
    board: chess.Board,
    bot_white,
    bot_black,
) -> None:
    start_board = board.copy(stack=False)
    move_history: List[chess.Move] = []

    print(f"Bot vs bot. White is {bot_white.__class__.__name__}, black is {bot_black.__class__.__name__}.\n")

    while not board.is_game_over():
        print(board)
        if move_history:
            print("Moves so far", format_san_history(start_board, move_history))

        current_bot = bot_white if board.turn == chess.WHITE else bot_black
        bot_move = current_bot.choose_move(board)
        bot_move_san = board.san(bot_move)
        board.push(bot_move)
        move_history.append(bot_move)
        print(f"{'White' if board.turn == chess.BLACK else 'Black'} plays {bot_move_san}\n")

    print(board)
    _print_bot_vs_bot_outcome(board, bot_white, bot_black)
    save_pgn_from_moves(move_history, board)


def _termination(board: chess.Board) -> str:
    return board.outcome().termination.name.lower().replace("_", " ")


def _print_human_vs_bot_outcome(board: chess.Board, user_is_white: bool, bot) -> None:
    outcome = board.outcome()
    if not outcome:
        print("Game over.")
        return
    if outcome.winner is None:
        print(f"Draw ({_termination(board)}).")
        return

    winner_is_white = outcome.winner == chess.WHITE
    if winner_is_white == user_is_white:
        print(f"You win ({_termination(board)}).")
        return

    bot_color = "white" if winner_is_white else "black"
    print(f"Bot {bot.__class__.__name__} wins with {bot_color} ({_termination(board)}).")


def _print_bot_vs_bot_outcome(board: chess.Board, bot_white, bot_black) -> None:
    outcome = board.outcome()
    if not outcome:
        print("Game over.")
        return
    if outcome.winner is None:
        print(f"Draw ({_termination(board)}).")
        return

    if outcome.winner == chess.WHITE:
        winner_name = bot_white.__class__.__name__
        color = "white"
    else:
        winner_name = bot_black.__class__.__name__
        color = "black"

    print(f"Bot {winner_name} wins with {color} ({_termination(board)}).")
