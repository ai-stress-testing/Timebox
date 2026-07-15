"""Event CRUD, canvas-type auto-assignment, and encryption at rest."""
import aiosqlite

from app.Core.config import settings

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
