"""Pure unit tests for Pipelines/routine_steps.py — no DB, no app, no I/O."""
import pytest

from app.Pipelines.routine_steps import StepRef, renumber_after_delete, renumber_positions


def _refs(*ids: str) -> list[StepRef]:
    return [StepRef(id=i) for i in ids]


def test_renumber_positions_full_reorder() -> None:
    current = _refs("a", "b", "c")
    result = renumber_positions(current, ["c", "a", "b"])
    assert result == {"c": 0, "a": 1, "b": 2}


def test_renumber_positions_identity() -> None:
    current = _refs("a", "b", "c")
    result = renumber_positions(current, ["a", "b", "c"])
    assert result == {"a": 0, "b": 1, "c": 2}


def test_renumber_positions_rejects_missing_id() -> None:
    current = _refs("a", "b", "c")
    with pytest.raises(ValueError):
        renumber_positions(current, ["a", "b"])


def test_renumber_positions_rejects_unknown_id() -> None:
    current = _refs("a", "b")
    with pytest.raises(ValueError):
        renumber_positions(current, ["a", "b", "z"])


def test_renumber_positions_rejects_duplicate() -> None:
    current = _refs("a", "b")
    with pytest.raises(ValueError):
        renumber_positions(current, ["a", "a"])


def test_renumber_after_delete_closes_mid_gap() -> None:
    current = _refs("a", "b", "c", "d")
    result = renumber_after_delete(current, "b")
    assert result == {"a": 0, "c": 1, "d": 2}


def test_renumber_after_delete_first() -> None:
    current = _refs("a", "b", "c")
    result = renumber_after_delete(current, "a")
    assert result == {"b": 0, "c": 1}


def test_renumber_after_delete_last() -> None:
    current = _refs("a", "b", "c")
    result = renumber_after_delete(current, "c")
    assert result == {"a": 0, "b": 1}


def test_renumber_after_delete_id_not_present_is_noop_on_others() -> None:
    current = _refs("a", "b", "c")
    result = renumber_after_delete(current, "not-there")
    assert result == {"a": 0, "b": 1, "c": 2}
