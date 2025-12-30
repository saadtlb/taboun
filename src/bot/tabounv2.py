import chess

from evaluation.material import evaluate_material


class tabounV2:
    """Bot that selects a move using a simple minimax search."""

    def __init__(self, depth: int = 2) -> None:
        self.depth = depth #profondeur 

    def choose_move(self, board: chess.Board) -> chess.Move:
        legal_moves = list(board.legal_moves) #tous les coups possibles
        if not legal_moves:
            raise ValueError("No legal moves available.")

        is_white_to_play = board.turn == chess.WHITE #true si c'est aux Blancs


        #on prépare le score de départ selon le camp
        if is_white_to_play:
            best_score = -float("inf") #blancs veulent maximiser
        else:
            best_score = float("inf") #noirs veulent minimiser

        best_move = legal_moves[0] #coup par défaut

        for move in legal_moves: #on cherche dans tous les coups possibles
            board.push(move) #on simule le coup
            score = minimax(board, self.depth - 1) #score de la suite
            board.pop() #on revient en arrière

            #mise à jour du meilleur coup selon le camp
            if is_white_to_play and score > best_score:
                best_score = score
                best_move = move
            elif not is_white_to_play and score < best_score:
                best_score = score
                best_move = move

        return best_move


def minimax(board: chess.Board, depth: int) -> int:
    if depth == 0 or board.is_game_over():  # condition d'arrêt soit profondeur 0 soit fin de partie
        return evaluate_material(board)

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return evaluate_material(board)

    is_white_to_play = board.turn == chess.WHITE

    if is_white_to_play: #blancs maximisent
        best_score = -float("inf")
        for move in legal_moves:
            board.push(move)
            score = minimax(board, depth - 1)
            board.pop()
            if score > best_score:
                best_score = score
        return best_score

    best_score = float("inf") #noirs minimisent
    for move in legal_moves:
        board.push(move)
        score = minimax(board, depth - 1)
        board.pop()
        if score < best_score:
            best_score = score
    return best_score
