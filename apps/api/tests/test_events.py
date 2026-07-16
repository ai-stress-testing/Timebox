"""Event CRUD, canvas-type auto-assignment, and encryption at rest."""
from datetime import datetime

import aiosqlite

from app.Core.config import settings
from app.Pipelines.recurrence import expand_occurrences

_WEEK = {"start": "2026-07-13T00:00:00Z", "end": "2026-07-20T00:00:00Z"}


def _event_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Deep work: quarterly report",
        "event_type": "task",
        "attention_class": "active",
        "start_at": "2026-07-14T09:00:00Z",
        "end_at": "2026-07-14T10:30:00Z",
    }
    return {**base, **overrides}


async def test_event_crud_round_trip(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/events", json=_event_payload(), headers=headers)
    assert created.status_code == 201, created.text
    event = created.json()
    assert event["title"] == "Deep work: quarterly report"
    assert event["canvas_event_type"] == "focus_only"

    listed = await client.get("/events", params=_WEEK, headers=headers)
    assert [e["id"] for e in listed.json()] == [event["id"]]

    patched = await client.patch(
        f"/events/{event['id']}", json={"title": "Renamed"}, headers=headers
    )
    assert patched.json()["title"] == "Renamed"

    deleted = await client.delete(f"/events/{event['id']}", headers=headers)
    assert deleted.status_code == 204
    empty = await client.get("/events", params=_WEEK, headers=headers)
    assert empty.json() == []


async def test_canvas_type_overlap_rules(unlocked) -> None:
    client, _keyfile, headers = unlocked
    homework = await client.post(
        "/events", json=_event_payload(title="Homework"), headers=headers
    )
    assert homework.json()["canvas_event_type"] == "focus_only"

    laundry = await client.post(
        "/events",
        json=_event_payload(
            title="Laundry", event_type="passive", attention_class="passive"
        ),
        headers=headers,
    )
    assert laundry.json()["canvas_event_type"] == "focus_passive"

    refreshed = await client.get(f"/events/{homework.json()['id']}", headers=headers)
    assert refreshed.json()["canvas_event_type"] == "focus_passive"

    meeting = await client.post(
        "/events",
        json=_event_payload(
            title="Standup",
            event_type="meeting",
            attention_class="involved",
            start_at="2026-07-14T14:00:00Z",
            end_at="2026-07-14T14:30:00Z",
        ),
        headers=headers,
    )
    assert meeting.json()["canvas_event_type"] == "involved_only"


async def test_all_day_event_excluded_from_timed_overlap(unlocked) -> None:
    client, _keyfile, headers = unlocked
    meeting = await client.post(
        "/events", json=_event_payload(title="Standup"), headers=headers
    )
    assert meeting.json()["canvas_event_type"] == "focus_only"

    holiday = await client.post(
        "/events",
        json=_event_payload(
            title="Public Holiday",
            event_type="personal",
            attention_class="passive",
            start_at="2026-07-14T00:00:00Z",
            end_at="2026-07-15T00:00:00Z",
            is_all_day=True,
        ),
        headers=headers,
    )
    assert holiday.status_code == 201, holiday.text
    assert holiday.json()["is_all_day"] is True

    refreshed = await client.get(f"/events/{meeting.json()['id']}", headers=headers)
    assert refreshed.json()["canvas_event_type"] == "focus_only"


async def test_titles_encrypted_at_rest(unlocked) -> None:
    client, _keyfile, headers = unlocked
    secret_title = "Very private appointment xyzzy"
    await client.post("/events", json=_event_payload(title=secret_title), headers=headers)

    db_path = settings.database_url.rsplit("///", 1)[-1]
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT title_enc FROM events")
        rows = await cursor.fetchall()
    assert rows, "event row must exist"
    stored = rows[0][0]
    assert secret_title not in stored
    assert stored.startswith("v1:")


async def test_end_before_start_rejected(unlocked) -> None:
    client, _keyfile, headers = unlocked
    bad = _event_payload(start_at="2026-07-14T10:00:00Z", end_at="2026-07-14T09:00:00Z")
    res = await client.post("/events", json=bad, headers=headers)
    assert res.status_code == 422


async def test_canvas_type_reverts_when_peer_deleted(unlocked) -> None:
    client, _keyfile, headers = unlocked
    homework = await client.post("/events", json=_event_payload(title="Homework"), headers=headers)
    laundry = await client.post(
        "/events",
        json=_event_payload(title="Laundry", event_type="passive", attention_class="passive"),
        headers=headers,
    )
    assert laundry.json()["canvas_event_type"] == "focus_passive"

    await client.delete(f"/events/{homework.json()['id']}", headers=headers)
    refreshed = await client.get(f"/events/{laundry.json()['id']}", headers=headers)
    assert refreshed.json()["canvas_event_type"] == "passive_multi"


async def test_canvas_type_reverts_when_peer_moves_away(unlocked) -> None:
    client, _keyfile, headers = unlocked
    homework = await client.post("/events", json=_event_payload(title="Homework"), headers=headers)
    laundry = await client.post(
        "/events",
        json=_event_payload(title="Laundry", event_type="passive", attention_class="passive"),
        headers=headers,
    )
    await client.patch(
        f"/events/{homework.json()['id']}",
        json={"start_at": "2026-07-16T09:00:00Z", "end_at": "2026-07-16T10:30:00Z"},
        headers=headers,
    )
    refreshed = await client.get(f"/events/{laundry.json()['id']}", headers=headers)
    assert refreshed.json()["canvas_event_type"] == "passive_multi"


def test_expand_occurrences_weekly_mon_wed_bounded() -> None:
    """Mon/Wed weekly rule anchored on a Monday, expanded over a 2-week window."""
    anchor_start = datetime(2026, 7, 13, 9, 0)  # a Monday
    anchor_end = datetime(2026, 7, 13, 10, 0)
    weekdays = frozenset({1, 3})  # Sun=0 convention: Mon=1, Wed=3
    window_start = datetime(2026, 7, 13, 0, 0)
    window_end = datetime(2026, 7, 27, 0, 0)  # exclusive, 2 weeks

    occurrences = expand_occurrences(
        anchor_start, anchor_end, weekdays, None, window_start, window_end
    )

    dates = [occ.occurrence_date.isoformat() for occ in occurrences]
    assert dates == ["2026-07-13", "2026-07-15", "2026-07-20", "2026-07-22"]
    for occ in occurrences:
        assert occ.start_at.time() == anchor_start.time()
        assert occ.end_at - occ.start_at == anchor_end - anchor_start
    assert isinstance(occurrences, tuple)
    assert len(occurrences) < 400


async def test_recurring_event_expands_within_week(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post(
        "/events",
        json=_event_payload(
            title="Standup",
            start_at="2026-07-13T09:00:00Z",
            end_at="2026-07-13T09:30:00Z",
            is_recurring=True,
            recurrence_weekdays=[1, 3],  # Mon, Wed
            recurrence_end="2026-07-31T23:59:00Z",
        ),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    master = created.json()
    assert master["is_recurring"] is True
    assert master["recurrence_weekdays"] == [1, 3]

    listed = await client.get("/events", params=_WEEK, headers=headers)
    assert listed.status_code == 200, listed.text
    occurrences = listed.json()
    assert len(occurrences) == 2

    occurrence_dates = sorted(occ["occurrence_date"] for occ in occurrences)
    assert occurrence_dates == ["2026-07-13", "2026-07-15"]
    for occ in occurrences:
        assert occ["id"] == master["id"]
        assert occ["master_event_id"] == master["id"]
        assert occ["is_recurring"] is True
        assert occ["start_at"].endswith("T09:00:00Z")
        assert occ["end_at"].endswith("T09:30:00Z")


def _recurring_payload(**overrides: object) -> dict[str, object]:
    return _event_payload(
        title="Standup",
        start_at="2026-07-13T09:00:00Z",  # Monday
        end_at="2026-07-13T09:30:00Z",
        is_recurring=True,
        recurrence_weekdays=[1, 3, 5],  # Mon, Wed, Fri
        **overrides,
    )


async def test_delete_scope_occurrence_removes_only_that_date(unlocked) -> None:
    """(a) scope=occurrence on the Wed date -> Wed gone, Mon+Fri remain."""
    client, _keyfile, headers = unlocked
    created = await client.post("/events", json=_recurring_payload(), headers=headers)
    master_id = created.json()["id"]

    deleted = await client.delete(
        f"/events/{master_id}",
        params={"scope": "occurrence", "occurrence_date": "2026-07-15"},
        headers=headers,
    )
    assert deleted.status_code == 204

    listed = await client.get("/events", params=_WEEK, headers=headers)
    dates = sorted(occ["occurrence_date"] for occ in listed.json())
    assert dates == ["2026-07-13", "2026-07-17"]


async def test_delete_scope_following_cuts_series(unlocked) -> None:
    """(b) scope=following on the Wed date -> Mon remains, Wed+Fri gone; the
    master's recurrence_end moves to just before the cutoff date."""
    client, _keyfile, headers = unlocked
    created = await client.post("/events", json=_recurring_payload(), headers=headers)
    master = created.json()
    assert master["recurrence_end"] is None

    deleted = await client.delete(
        f"/events/{master['id']}",
        params={"scope": "following", "occurrence_date": "2026-07-15"},
        headers=headers,
    )
    assert deleted.status_code == 204

    listed = await client.get("/events", params=_WEEK, headers=headers)
    dates = sorted(occ["occurrence_date"] for occ in listed.json())
    assert dates == ["2026-07-13"]

    refreshed = await client.get(f"/events/{master['id']}", headers=headers)
    assert refreshed.json()["recurrence_end"] == "2026-07-14T23:59:59Z"


async def test_delete_scope_following_from_first_occurrence_removes_series(unlocked) -> None:
    """Cutting "following" from the very first occurrence leaves nothing to
    keep, so the whole master is soft-deleted instead of a no-op cutoff."""
    client, _keyfile, headers = unlocked
    created = await client.post("/events", json=_recurring_payload(), headers=headers)
    master_id = created.json()["id"]

    deleted = await client.delete(
        f"/events/{master_id}",
        params={"scope": "following", "occurrence_date": "2026-07-13"},
        headers=headers,
    )
    assert deleted.status_code == 204

    listed = await client.get("/events", params=_WEEK, headers=headers)
    assert listed.json() == []
    gone = await client.get(f"/events/{master_id}", headers=headers)
    assert gone.status_code == 404


async def test_delete_scope_all_removes_whole_series(unlocked) -> None:
    """(c) scope=all (default) -> whole series gone."""
    client, _keyfile, headers = unlocked
    created = await client.post("/events", json=_recurring_payload(), headers=headers)
    master_id = created.json()["id"]

    deleted = await client.delete(f"/events/{master_id}", headers=headers)
    assert deleted.status_code == 204

    listed = await client.get("/events", params=_WEEK, headers=headers)
    assert listed.json() == []


async def test_delete_non_recurring_event_regression(unlocked) -> None:
    """(d) deleting a non-recurring event still works as before."""
    client, _keyfile, headers = unlocked
    created = await client.post("/events", json=_event_payload(), headers=headers)
    event_id = created.json()["id"]

    deleted = await client.delete(f"/events/{event_id}", headers=headers)
    assert deleted.status_code == 204

    listed = await client.get("/events", params=_WEEK, headers=headers)
    assert listed.json() == []


async def test_delete_occurrence_scope_requires_occurrence_date(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/events", json=_recurring_payload(), headers=headers)
    master_id = created.json()["id"]

    bad = await client.delete(
        f"/events/{master_id}", params={"scope": "occurrence"}, headers=headers
    )
    assert bad.status_code == 400


async def test_delete_following_scope_requires_occurrence_date(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/events", json=_recurring_payload(), headers=headers)
    master_id = created.json()["id"]

    bad = await client.delete(
        f"/events/{master_id}", params={"scope": "following"}, headers=headers
    )
    assert bad.status_code == 400


async def test_recurring_event_listing_is_deterministic(unlocked) -> None:
    client, _keyfile, headers = unlocked
    await client.post(
        "/events",
        json=_event_payload(
            title="Standup",
            start_at="2026-07-13T09:00:00Z",
            end_at="2026-07-13T09:30:00Z",
            is_recurring=True,
            recurrence_weekdays=[1, 3],
        ),
        headers=headers,
    )

    first = await client.get("/events", params=_WEEK, headers=headers)
    second = await client.get("/events", params=_WEEK, headers=headers)
    assert first.json() == second.json()


async def test_title_suggestions_group_and_average(unlocked) -> None:
    client, _keyfile, headers = unlocked
    # two "Gym" events with estimated durations, one "Dentist"
    for start, end, mins in [
        ("2026-07-14T07:00:00Z", "2026-07-14T08:00:00Z", 60),
        ("2026-07-16T07:00:00Z", "2026-07-16T08:30:00Z", 90),
    ]:
        await client.post(
            "/events",
            json={"title": "Gym", "event_type": "physical", "attention_class": "involved",
                  "start_at": start, "end_at": end, "estimated_minutes": mins},
            headers=headers,
        )
    await client.post(
        "/events",
        json=_event_payload(title="Dentist", start_at="2026-07-15T09:00:00Z",
                            end_at="2026-07-15T09:30:00Z"),
        headers=headers,
    )
    res = await client.get("/events/titles", headers=headers)
    assert res.status_code == 200, res.text
    by_title = {row["title"]: row for row in res.json()}
    assert by_title["Gym"]["occurrence_count"] == 2
    assert by_title["Gym"]["avg_minutes"] == 75  # (60 + 90) / 2
    assert by_title["Dentist"]["occurrence_count"] == 1
    # most frequent first
    assert res.json()[0]["title"] == "Gym"
