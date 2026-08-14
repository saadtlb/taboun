"""Small shared clock helpers for the historical Taboun bots."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Event


class SearchTimeout(Exception):
    """Raised cooperatively when a search has used its move budget."""


@dataclass(frozen=True)
class SearchDeadline:
    expires_at: float
    stop_event: Event | None = None


def make_deadline(
    time_limit: float | None,
    stop_event: Event | None = None,
) -> SearchDeadline | None:
    if time_limit is None:
        return None
    if time_limit < 0:
        raise ValueError("time_limit must be non-negative or None.")
    return SearchDeadline(time.perf_counter() + time_limit, stop_event)


def check_time(deadline: SearchDeadline | None) -> None:
    if deadline is None:
        return
    if deadline.stop_event is not None and deadline.stop_event.is_set():
        raise SearchTimeout()
    if time.perf_counter() >= deadline.expires_at:
        raise SearchTimeout()
