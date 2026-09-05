"""tabounV13: tabounV12's search with the PeSTO evaluation.

One change. The hand-written evaluation of V9 to V12 (Michniewski tables, a
two-state king table, mobility, bishop pair, pawn structure, king safety) is
replaced by PeSTO's tapered piece-square tables: two tables per piece, tuned
with Texel's method, blended by game phase. The search, move ordering,
transposition table, time management and opening book are V12's, untouched.

Expected effects: a more accurate evaluation, and a cheaper one, because the
mobility term used to generate every legal move of both sides at each leaf.
"""

from src.bot.tabounv12 import tabounV12
from src.evaluation.pesto_evaluation_function import evaluate_pesto


class tabounV13(tabounV12):
    """V12 search, PeSTO tapered evaluation."""

    evaluate = staticmethod(evaluate_pesto)
