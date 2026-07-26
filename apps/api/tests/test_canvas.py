"""Canvas item CRUD, start/pause/reset transitions, event-link snapshotting,
lazy timer completion, and encryption at rest.

DEVIATION (see specs/010-radial-canvas/plan.md "deviations"): `app.main`
registers routers centrally and is a shared file this build intentionally
does not touch (three features are landing routers in parallel; wiring
happens in one pass afterward). To exercise the canvas API end-to-end here
without editing `main.py`, this module registers `canvas.router` onto the
already-constructed `app` singleton at import time, guarded so it's a no-op
once main.py wires it in for real.
"""
import aiosqlite

from app.Core.config import settings
from app.main import app
from app.Routers.canvas import router as canvas_router

if not any(
    getattr(route, "path", "").startswith(f"{settings.api_prefix}/canvas") for route in app.routes
):
    app.include_router(canvas_router, prefix=settings.api_prefix)


def _timer_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Quick focus block",
        "mode": "timer",
        "duration_seconds": 1500,
    }
    return {**base, **overrides}


def _stopwatch_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {"title": "Ad-hoc stopwatch", "mode": "stopwatch"}
    return {**base, **overrides}


def _event_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Deep work: quarterly report",
        "event_type": "task",
        "attention_class": "active",
        "start_at": "2026-07-14T09:00:00Z",
        "end_at": "2026-07-14T10:30:00Z",
    }
    return {**base, **overrides}


async def _rewind_started_at(item_id: str, seconds: int) -> None:
    """Simulate `seconds` of real elapsed time deterministically, without a
    real sleep, by rewinding the persisted `started_at` directly in the
    live SQLite file — same live-DB-touch pattern as the encryption test."""
    db_path = settings.database_url.rsplit("///", 1)[-1]
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE canvas_items SET started_at = datetime(started_at, ?) WHERE id = ?",
            (f"-{seconds} seconds", item_id),
        )
        await db.commit()


async def test_create_timer_and_stopwatch_independent_of_event(unlocked) -> None:
    client, _keyfile, headers = unlocked
    timer = await client.post("/canvas/items", json=_timer_payload(), headers=headers)
    assert timer.status_code == 201, timer.text
    body = timer.json()
    assert body["title"] == "Quick focus block"
    assert body["mode"] == "timer"
    assert body["duration_seconds"] == 1500
    assert body["status"] == "paused"
    assert body["event_id"] is None
    assert body["accumulated_seconds"] == 0

    stopwatch = await client.post("/canvas/items", json=_stopwatch_payload(), headers=headers)
    assert stopwatch.status_code == 201, stopwatch.text
    assert stopwatch.json()["mode"] == "stopwatch"
    assert stopwatch.json()["duration_seconds"] is None

    listed = await client.get("/canvas/items", headers=headers)
    assert listed.status_code == 200, listed.text
    ids = {item["id"] for item in listed.json()}
    assert body["id"] in ids
    assert stopwatch.json()["id"] in ids


async def test_timer_requires_duration(unlocked) -> None:
    client, _keyfile, headers = unlocked
    res = await client.post(
        "/canvas/items", json=_timer_payload(duration_seconds=None), headers=headers
    )
    assert res.status_code == 422


async def test_start_pause_reset_produces_expected_accumulated_seconds(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/canvas/items", json=_stopwatch_payload(), headers=headers)
    item_id = created.json()["id"]

    started = await client.post(f"/canvas/items/{item_id}/start", headers=headers)
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "running"
    assert started.json()["started_at"] is not None

    await _rewind_started_at(item_id, 30)

    paused = await client.post(f"/canvas/items/{item_id}/pause", headers=headers)
    assert paused.status_code == 200, paused.text
    assert paused.json()["status"] == "paused"
    assert paused.json()["accumulated_seconds"] == 30
    assert paused.json()["started_at"] is None

    reset = await client.post(f"/canvas/items/{item_id}/reset", headers=headers)
    assert reset.status_code == 200, reset.text
    assert reset.json()["status"] == "paused"
    assert reset.json()["accumulated_seconds"] == 0
    assert reset.json()["started_at"] is None


async def test_timer_reaching_zero_transitions_to_completed(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post(
        "/canvas/items", json=_timer_payload(duration_seconds=60), headers=headers
    )
    item_id = created.json()["id"]

    started = await client.post(f"/canvas/items/{item_id}/start", headers=headers)
    assert started.status_code == 200, started.text

    # Rewind past the 60s target — completion is checked lazily on the next
    # read/tick, never via a background poller.
    await _rewind_started_at(item_id, 90)

    listed = await client.get("/canvas/items", headers=headers)
    assert listed.status_code == 200, listed.text
    item = next(row for row in listed.json() if row["id"] == item_id)
    assert item["status"] == "completed"
    assert item["accumulated_seconds"] == 60
    assert item["started_at"] is None

    # Starting an already-completed timer is rejected, not silently restarted.
    restart = await client.post(f"/canvas/items/{item_id}/start", headers=headers)
    assert restart.status_code == 409


async def test_edit_and_delete_do_not_touch_linked_event(unlocked) -> None:
    client, _keyfile, headers = unlocked
    event = await client.post("/events", json=_event_payload(), headers=headers)
    assert event.status_code == 201, event.text
    event_id = event.json()["id"]
    original_updated_at = event.json()["updated_at"]

    linked = await client.post(
        "/canvas/items",
        json=_timer_payload(event_id=event_id),
        headers=headers,
    )
    assert linked.status_code == 201, linked.text
    item = linked.json()
    # attention_class/canvas_event_type snapshotted from the linked event.
    assert item["attention_class"] == event.json()["attention_class"]
    assert item["canvas_event_type"] == event.json()["canvas_event_type"]

    edited = await client.patch(
        f"/canvas/items/{item['id']}",
        json={"title": "Renamed timer", "r": 0.2, "theta": 90},
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "Renamed timer"
    assert edited.json()["r"] == 0.2

    deleted = await client.delete(f"/canvas/items/{item['id']}", headers=headers)
    assert deleted.status_code == 204

    still_there = await client.get("/canvas/items", headers=headers)
    assert item["id"] not in {row["id"] for row in still_there.json()}

    # The linked event is completely untouched.
    unchanged = await client.get(f"/events/{event_id}", headers=headers)
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["title"] == "Deep work: quarterly report"
    assert unchanged.json()["updated_at"] == original_updated_at


async def test_titles_encrypted_at_rest(unlocked) -> None:
    client, _keyfile, headers = unlocked
    secret_title = "Very private focus block xyzzy"
    created = await client.post(
        "/canvas/items", json=_timer_payload(title=secret_title), headers=headers
    )
    assert created.status_code == 201, created.text

    db_path = settings.database_url.rsplit("///", 1)[-1]
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT title_enc FROM canvas_items")
        rows = await cursor.fetchall()
    assert rows, "canvas item row must exist"
    stored = rows[0][0]
    assert secret_title not in stored
    assert stored.startswith("v1:")


async def test_alarm_create_and_acknowledge(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/canvas/items", json=_timer_payload(), headers=headers)
    item_id = created.json()["id"]

    alarm = await client.post(
        f"/canvas/items/{item_id}/alarms",
        json={"alarm_class": "focus_checkpoint", "offset_seconds": 600},
        headers=headers,
    )
    assert alarm.status_code == 201, alarm.text
    assert alarm.json()["status"] == "pending"
    alarm_id = alarm.json()["id"]

    acked = await client.patch(
        f"/canvas/alarms/{alarm_id}", json={"status": "acknowledged"}, headers=headers
    )
    assert acked.status_code == 200, acked.text
    assert acked.json()["status"] == "acknowledged"
    assert acked.json()["acknowledged_at"] is not None
