"""Routine step position renumbering — pure functions (NASA rule 2/3).

No I/O, no DB, no clock reads. `routine_steps.position` must stay a
contiguous 0..n-1 run so the run view's "next step" logic is a plain
`position + 1` lookup rather than "next non-deleted position". Both
functions here take plain in-memory step data and return a
step-id -> new-position mapping for the service layer to persist;
deterministic for identical inputs.
"""
from dataclasses import dataclass
from typing import Protocol


class StepLike(Protocol):
    id: str


@dataclass(frozen=True)
class StepRef:
    id: str


def renumber_positions(
    current_steps: list[StepLike], new_order: list[str]
) -> dict[str, int]:
    """Given the routine's current live steps and a caller-supplied full
    ordering of their ids, return {step_id: new_position} with positions
    0..n-1 in the order given by `new_order`.

    Raises ValueError if `new_order` is not exactly a permutation of the
    current steps' ids (missing id, unknown id, or duplicate) — the caller
    must supply the *complete* ordered list, not a partial diff.
    """
    current_ids = {step.id for step in current_steps}
    if len(new_order) != len(current_ids) or set(new_order) != current_ids:
        raise ValueError("new_order must be a permutation of the routine's current step ids")
    return {step_id: position for position, step_id in enumerate(new_order)}


def renumber_after_delete(
    current_steps: list[StepLike], deleted_id: str
) -> dict[str, int]:
    """Positions for the remaining steps after `deleted_id` is removed,
    preserving relative order and closing the resulting gap so positions
    stay contiguous 0..n-2. `current_steps` must already be ordered by
    position and include the step being deleted (it is simply skipped).
    """
    remaining = [step.id for step in current_steps if step.id != deleted_id]
    return {step_id: position for position, step_id in enumerate(remaining)}
