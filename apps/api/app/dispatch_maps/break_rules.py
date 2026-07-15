"""Focus checkpoint break rule as a data-driven rule list (DB-Schemas.md):
session < 40 min → 5 min flat; session >= 40 min → 50% of logged time.
"""
from collections.abc import Callable

BreakRule = tuple[int, Callable[[int], int]]

BREAK_RULES: tuple[BreakRule, ...] = (
    (40, lambda minutes: round(minutes * 0.5)),
    (0, lambda _minutes: 5),
)


def get_break_minutes(session_minutes: int) -> int:
    matched = next(rule for rule in BREAK_RULES if session_minutes >= rule[0])
    return matched[1](session_minutes)
