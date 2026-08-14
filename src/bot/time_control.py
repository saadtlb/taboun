"""Small shared clock helpers for the historical Taboun bots."""

from __future__ import annotations

import time


class SearchTimeout(Exception):
    """Raised cooperatively when a search has used its move budget."""


def make_deadline(time_limit: float | None) -> float | None:
    if time_limit is None:
        return None
    if time_limit < 0:
        raise ValueError("time_limit must be non-negative or None.")
    return time.perf_counter() + time_limit


def check_time(deadline: float | None) -> None:
    if deadline is not None and time.perf_counter() >= deadline:
        raise SearchTimeout()
