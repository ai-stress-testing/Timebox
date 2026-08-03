"""Missed-detection pass + drift-triggered healing (spec 008).

Pure-function tests need no DB (`decide_transitions`, `compute_drift_ratio`,
`nudge_n_toward_original`); the integration tests seed occurrences/events
directly via a raw session (same pattern as test_duration_profiles.py) and
drive the real `chore_missed_detection_service.run_missed_detection` pass.
"""
from datetime import timedelta

from sqlalchemy import select

from app.Core.database import session_factory
from app.Models.base import utc_now
from app.Models.chore import ChoreDefinition
from app.Models.chore_healing import ChoreNHistory, ScheduleHealingLog
from app.Models.event import Event
from app.Models.schedule import ChoreOccurrence, ScheduleRun
from app.Pipelines.chore_healing import (
    OccurrenceWindow,
    compute_drift_ratio,
    decide_transitions,
    nudge_n_toward_original,
)
from app.Services import chore_missed_detection_service

# --------------------------------------------------------------- unit tests


def _window(
    event_id: str | None = "evt-1", proposed_end_at=None, status: str = "scheduled"
) -> OccurrenceWindow:
    return OccurrenceWindow(
        id="occ-1", status=status, event_id=event_id, proposed_end_at=proposed_end_at
    )


def test_completed_in_time_transitions_to_completed() -> None:
    now = utc_now()
    window = _window(proposed_end_at=now - timedelta(hours=1))
    decisions = decide_transitions([(window, "completed", now)])
    assert len(decisions) == 1
    assert decisions[0].occurrence_id == "occ-1"
    assert decisions[0].new_status == "completed"


def test_missed_deleted_event_transitions_to_missed() -> None:
    now = utc_now()
    window = _window(proposed_end_at=now - timedelta(hours=1))
    # event not found -> caller passes None for linked_event_status
    decisions = decide_transitions([(window, None, now)])
    assert len(decisions) == 1
    assert decisions[0].new_status == "missed"


def test_missed_never_completed_transitions_to_missed() -> None:
    now = utc_now()
    window = _window(proposed_end_at=now - timedelta(hours=1))
    decisions = decide_transitions([(window, "scheduled", now)])
    assert len(decisions) == 1
    assert decisions[0].new_status == "missed"


def test_not_yet_due_is_untouched() -> None:
    now = utc_now()
    window = _window(proposed_end_at=now + timedelta(hours=1))
    decisions = decide_transitions([(window, "completed", now)])
    assert decisions == []


def test_no_event_id_is_untouched() -> None:
    now = utc_now()
    window = _window(event_id=None, proposed_end_at=now - timedelta(hours=1))
    decisions = decide_transitions([(window, None, now)])
    assert decisions == []


def test_compute_drift_ratio_all_completed() -> None:
    assert compute_drift_ratio(missed=0, completed=5) == 0.0


def test_compute_drift_ratio_all_missed() -> None:
    assert compute_drift_ratio(missed=5, completed=0) == 1.0


def test_compute_drift_ratio_empty() -> None:
    assert compute_drift_ratio(missed=0, completed=0) == 0.0


def test_compute_drift_ratio_mixed() -> None:
    assert compute_drift_ratio(missed=2, completed=3) == 0.4


def test_nudge_moves_toward_original_without_overshooting() -> None:
    assert nudge_n_toward_original(n_current=3, n_original=10, n_min=1, n_max=30) == 6
    assert nudge_n_toward_original(n_current=3, n_original=10, n_min=1, n_max=5) == 5


def test_nudge_is_noop_when_already_at_original() -> None:
    assert nudge_n_toward_original(n_current=7, n_original=7, n_min=1, n_max=30) == 7


# ---------------------------------------------------------- integration tests


async def _create_chore(client, headers, **overrides: object) -> dict:
    payload = {
        "name": "Water plants",
        "estimated_minutes": 15,
        "n_days": 10,
        "n_min": 1,
        "n_max": 30,
        **overrides,
    }
    res = await client.post("/chores", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def _seed_occurrence(
    session, *, user_id: str, chore_id: str, run_id: str, event_status: str, minutes_ago: int = 60
) -> None:
    proposed_end = utc_now() - timedelta(minutes=minutes_ago)
    event = Event(
        calendar_id="test-calendar",
        user_id=user_id,
        event_type="chore",
        status=event_status,
        title_enc="irrelevant-for-this-test",
        start_at=proposed_end - timedelta(minutes=15),
        end_at=proposed_end,
    )
    session.add(event)
    await session.flush()
    session.add(
        ChoreOccurrence(
            schedule_run_id=run_id,
            chore_id=chore_id,
            user_id=user_id,
            proposed_start_at=proposed_end - timedelta(minutes=15),
            proposed_end_at=proposed_end,
            confidence_score=0.9,
            load_score=0.5,
            status="scheduled",
            event_id=event.id,
        )
    )
    await session.flush()


async def _add_run(session, user_id: str) -> ScheduleRun:
    run = ScheduleRun(
        user_id=user_id,
        window_start=utc_now() - timedelta(days=1),
        window_end=utc_now(),
        window_days=1,
        iterations=1,
        seed=1,
    )
    session.add(run)
    await session.flush()
    return run


async def test_chore_crossing_drift_threshold_gets_healed(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await _create_chore(client, headers, n_days=10, n_min=1, n_max=30)
    chore_id = created["id"]
    # Relax n_current down from n_original so healing has somewhere to move it.
    patched = await client.patch(f"/chores/{chore_id}", json={"n_days": 3}, headers=headers)
    assert patched.status_code == 200, patched.text

    async with session_factory() as session:
        chore = (
            await session.execute(select(ChoreDefinition).where(ChoreDefinition.id == chore_id))
        ).scalar_one()
        user_id = chore.user_id
        assert chore.n_current == 3
        assert chore.n_original == 10

        run = await _add_run(session, user_id)
        # 3 missed, 1 completed -> drift = 0.75, well over the 0.4 threshold.
        for _ in range(3):
            await _seed_occurrence(
                session,
                user_id=user_id,
                chore_id=chore_id,
                run_id=run.id,
                event_status="scheduled",
            )
        await _seed_occurrence(
            session, user_id=user_id, chore_id=chore_id, run_id=run.id, event_status="completed"
        )
        await session.commit()

        transitioned = await chore_missed_detection_service.run_missed_detection(session)
        assert transitioned == 4

        history_rows = (
            (await session.execute(select(ChoreNHistory).where(ChoreNHistory.chore_id == chore_id)))
            .scalars()
            .all()
        )
        assert len(history_rows) == 1
        assert history_rows[0].reason == "healing"
        assert history_rows[0].n_before == 3

        log_rows = (
            (
                await session.execute(
                    select(ScheduleHealingLog).where(ScheduleHealingLog.schedule_run_id == run.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(log_rows) == 1
        assert log_rows[0].n_adjustments == 1
        assert log_rows[0].occurrences_missed == 3

        refreshed = (
            await session.execute(select(ChoreDefinition).where(ChoreDefinition.id == chore_id))
        ).scalar_one()
        assert 3 < refreshed.n_current <= 10  # moved toward n_original, within bounds


async def test_chore_below_threshold_gets_no_spurious_rows(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await _create_chore(client, headers, n_days=10, n_min=1, n_max=30)
    chore_id = created["id"]

    async with session_factory() as session:
        chore = (
            await session.execute(select(ChoreDefinition).where(ChoreDefinition.id == chore_id))
        ).scalar_one()
        user_id = chore.user_id

        run = await _add_run(session, user_id)
        # 1 missed, 4 completed -> drift = 0.2, below threshold: no healing.
        await _seed_occurrence(
            session, user_id=user_id, chore_id=chore_id, run_id=run.id, event_status="scheduled"
        )
        for _ in range(4):
            await _seed_occurrence(
                session,
                user_id=user_id,
                chore_id=chore_id,
                run_id=run.id,
                event_status="completed",
            )
        await session.commit()

        transitioned = await chore_missed_detection_service.run_missed_detection(session)
        assert transitioned == 5

        history_rows = (
            (await session.execute(select(ChoreNHistory).where(ChoreNHistory.chore_id == chore_id)))
            .scalars()
            .all()
        )
        assert history_rows == []

        log_rows = (
            (
                await session.execute(
                    select(ScheduleHealingLog).where(ScheduleHealingLog.schedule_run_id == run.id)
                )
            )
            .scalars()
            .all()
        )
        assert log_rows == []

        refreshed = (
            await session.execute(select(ChoreDefinition).where(ChoreDefinition.id == chore_id))
        ).scalar_one()
        assert refreshed.n_current == created["n_current"]
