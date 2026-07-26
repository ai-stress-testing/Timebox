"""Chore entropy (spec 012): recommended_split, days_until_due, completion flow."""
from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.Models.base import utc_now
from app.Pipelines.chore_entropy import days_until_due, recommended_split

# --------------------------------------------------------------- unit tests


def test_recommended_split_one_early_completion_barely_moves_off_n_current() -> None:
    # n_current=7, one observation at 4 days: weight = 1/(1+3) = 0.25, so the
    # recommendation should sit much closer to 7 than to 4.
    result = recommended_split(
        n_current=7, expectation_days=4.0, sample_count=1, n_min=1, n_max=30
    )
    blended = 0.25 * 4.0 + 0.75 * 7.0  # 5.75 -> 6
    assert result == round(blended)
    assert result != 4
    assert 4 < result < 7


def test_recommended_split_ten_consistent_completions_moves_close_to_expectation() -> None:
    # weight = 10/(10+3) ~= 0.77, so the recommendation should land near the
    # observed expectation_days rather than the stale n_current.
    result = recommended_split(
        n_current=7, expectation_days=4.0, sample_count=10, n_min=1, n_max=30
    )
    # weight=10/13≈0.77 pulls the result much closer to expectation_days (4)
    # than the single-sample case did, though shrinkage never fully reaches it.
    assert result <= 5
    assert result < 6


def test_recommended_split_clamped_to_bounds() -> None:
    # Raw blend would land at ~9 (weight 0.5, midpoint of 2 and 16), but n_max
    # clamps it down; a low n_min case clamps up.
    high = recommended_split(
        n_current=16, expectation_days=2.0, sample_count=3, n_min=1, n_max=5
    )
    assert high == 5

    low = recommended_split(
        n_current=1, expectation_days=50.0, sample_count=3, n_min=1, n_max=3
    )
    assert low == 3


@pytest.mark.parametrize(
    "delta_days,expected",
    [(5, 5), (0, 0), (-3, -3)],
)
def test_days_until_due(delta_days: int, expected: int) -> None:
    now = utc_now()
    due = now + timedelta(days=delta_days)
    assert days_until_due(due, now) == expected


def test_days_until_due_none_when_no_due_date() -> None:
    assert days_until_due(None, utc_now()) is None


# ---------------------------------------------------------- integration tests


async def _create_chore(client: AsyncClient, headers: dict[str, str], **overrides: object) -> dict:
    payload = {
        "name": "Mop floors",
        "estimated_minutes": 15,
        "n_days": 7,
        "n_min": 1,
        "n_max": 14,
        **overrides,
    }
    res = await client.post("/chores", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def test_get_chores_returns_days_until_due_matching_hand_computed_value(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await _create_chore(client, headers)
    chore_id = created["id"]

    # A fresh chore's next_due_at is set to created_at + n_days (7).
    listed = await client.get("/chores", headers=headers)
    assert listed.status_code == 200, listed.text
    row = next(c for c in listed.json() if c["id"] == chore_id)
    assert row["days_until_due"] in (6, 7)  # created "now"; allow a day's rounding slack
    assert row["recommended_n"] is None  # no completions logged yet


async def test_complete_chore_logs_first_completion_without_recommendation(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await _create_chore(client, headers)
    chore_id = created["id"]

    completed = await client.post(f"/chores/{chore_id}/complete", json={}, headers=headers)
    assert completed.status_code == 200, completed.text
    body = completed.json()
    assert body["last_completed_at"] is not None
    # First completion has no prior gap to learn from yet.
    assert body["recommended_n"] is None


async def test_completing_a_chore_early_repeatedly_drives_recommended_n_below_n_current(
    unlocked,
) -> None:
    client, _keyfile, headers = unlocked
    created = await _create_chore(client, headers, n_days=7, n_min=1, n_max=14)
    chore_id = created["id"]

    now = utc_now()
    # First completion establishes last_completed_at (no Welford update yet).
    first = await client.post(
        f"/chores/{chore_id}/complete",
        json={"completed_at": now.isoformat() + "Z"},
        headers=headers,
    )
    assert first.status_code == 200, first.text

    # Then complete it several more times, always ~3 days apart — well
    # under the scheduled 7-day cadence.
    when = now
    last_body = None
    for _ in range(6):
        when = when + timedelta(days=3)
        res = await client.post(
            f"/chores/{chore_id}/complete",
            json={"completed_at": when.isoformat() + "Z"},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        last_body = res.json()

    assert last_body is not None
    assert last_body["recommended_n"] is not None
    assert last_body["recommended_n"] < created["n_current"]


async def test_complete_unknown_chore_404s(unlocked) -> None:
    client, _keyfile, headers = unlocked
    res = await client.post("/chores/not-a-real-id/complete", json={}, headers=headers)
    assert res.status_code == 404
