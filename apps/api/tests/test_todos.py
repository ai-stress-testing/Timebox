"""Todo CRUD, encryption at rest, and the to-do-to-schedule funnel (issue #12)."""
import aiosqlite

from app.Core.config import settings

_WEEK = {"start": "2026-07-13T00:00:00Z", "end": "2026-07-20T00:00:00Z"}


def _todo_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {"title": "Buy groceries", "estimated_minutes": 30}
    return {**base, **overrides}


async def test_todo_create_and_list_round_trip(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/todos", json=_todo_payload(), headers=headers)
    assert created.status_code == 201, created.text
    todo = created.json()
    assert todo["title"] == "Buy groceries"
    assert todo["estimated_minutes"] == 30
    assert todo["is_done"] is False
    assert todo["scheduled_event_id"] is None

    listed = await client.get("/todos", headers=headers)
    assert listed.status_code == 200, listed.text
    assert [t["id"] for t in listed.json()] == [todo["id"]]


async def test_patch_title_and_is_done(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/todos", json=_todo_payload(), headers=headers)
    todo_id = created.json()["id"]

    patched = await client.patch(
        f"/todos/{todo_id}", json={"title": "Buy oat milk"}, headers=headers
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["title"] == "Buy oat milk"

    done = await client.patch(f"/todos/{todo_id}", json={"is_done": True}, headers=headers)
    assert done.status_code == 200, done.text
    assert done.json()["is_done"] is True

    # done todos drop out of the open list
    listed = await client.get("/todos", headers=headers)
    assert listed.json() == []


async def test_delete_removes_from_open_list(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/todos", json=_todo_payload(), headers=headers)
    todo_id = created.json()["id"]

    deleted = await client.delete(f"/todos/{todo_id}", headers=headers)
    assert deleted.status_code == 204

    listed = await client.get("/todos", headers=headers)
    assert listed.json() == []


async def test_titles_encrypted_at_rest(unlocked) -> None:
    client, _keyfile, headers = unlocked
    secret_title = "Very private errand xyzzy"
    await client.post("/todos", json=_todo_payload(title=secret_title), headers=headers)

    db_path = settings.database_url.rsplit("///", 1)[-1]
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT title_enc FROM todos")
        rows = await cursor.fetchall()
    assert rows, "todo row must exist"
    stored = rows[0][0]
    assert secret_title not in stored
    assert stored.startswith("v1:")


async def test_batch_schedule_single_item_creates_event_and_marks_done(unlocked) -> None:
    """The one-todo case of the batch funnel — this is now the only path
    (the old single-item POST /todos/{id}/schedule endpoint is gone;
    batch-schedule, even with one item, is the sole scheduling entry point)."""
    client, _keyfile, headers = unlocked
    created = await client.post("/todos", json=_todo_payload(), headers=headers)
    todo = created.json()

    scheduled = await client.post(
        "/todos/batch-schedule",
        json={
            "items": [
                {
                    "todo_id": todo["id"],
                    "start_at": "2026-07-14T09:00:00Z",
                    "event_type": "task",
                    "attention_class": "active",
                }
            ]
        },
        headers=headers,
    )
    assert scheduled.status_code == 200, scheduled.text
    result = scheduled.json()["results"][0]
    assert result["ok"] is True
    assert result["event"]["title"] == "Buy groceries"
    assert result["event"]["start_at"] == "2026-07-14T09:00:00Z"
    assert result["event"]["estimated_minutes"] == 30

    # the event is visible via GET /events for the scheduled window
    listed = await client.get("/events", params=_WEEK, headers=headers)
    assert [e["id"] for e in listed.json()] == [result["event"]["id"]]

    # scheduled todos drop out of the open list
    open_todos = await client.get("/todos", headers=headers)
    assert open_todos.json() == []


async def test_batch_schedule_already_scheduled_todo_rejected(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/todos", json=_todo_payload(), headers=headers)
    todo_id = created.json()["id"]

    item = {"todo_id": todo_id, "start_at": "2026-07-14T09:00:00Z", "event_type": "task"}
    first = await client.post("/todos/batch-schedule", json={"items": [item]}, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["results"][0]["ok"] is True

    second = await client.post("/todos/batch-schedule", json={"items": [item]}, headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["results"][0]["ok"] is False


async def test_batch_schedule_all_succeed(unlocked) -> None:
    client, _keyfile, headers = unlocked
    todos = []
    for title in ["Buy groceries", "Walk the dog", "Read a book"]:
        created = await client.post("/todos", json=_todo_payload(title=title), headers=headers)
        todos.append(created.json())

    items = [
        {
            "todo_id": todos[0]["id"],
            "start_at": "2026-07-14T09:00:00Z",
            "event_type": "task",
        },
        {
            "todo_id": todos[1]["id"],
            "start_at": "2026-07-14T10:00:00Z",
            "event_type": "task",
        },
        {
            "todo_id": todos[2]["id"],
            "start_at": "2026-07-14T11:00:00Z",
            "event_type": "task",
        },
    ]
    batch = await client.post("/todos/batch-schedule", json={"items": items}, headers=headers)
    assert batch.status_code == 200, batch.text
    results = batch.json()["results"]
    assert len(results) == 3
    assert all(r["ok"] for r in results)
    assert all(r["event"] is not None for r in results)

    listed = await client.get("/events", params=_WEEK, headers=headers)
    assert len(listed.json()) == 3

    open_todos = await client.get("/todos", headers=headers)
    assert open_todos.json() == []


async def test_batch_schedule_one_failure_others_still_commit(unlocked) -> None:
    client, _keyfile, headers = unlocked
    todos = []
    for title in ["Buy groceries", "Walk the dog"]:
        created = await client.post("/todos", json=_todo_payload(title=title), headers=headers)
        todos.append(created.json())

    # Schedule the same todo twice in one batch: the second occurrence must
    # fail (already scheduled by the first) while the other todo still
    # succeeds and commits.
    items = [
        {
            "todo_id": todos[0]["id"],
            "start_at": "2026-07-14T09:00:00Z",
            "event_type": "task",
        },
        {
            "todo_id": todos[1]["id"],
            "start_at": "2026-07-14T10:00:00Z",
            "event_type": "task",
        },
        {
            "todo_id": todos[0]["id"],
            "start_at": "2026-07-14T13:00:00Z",
            "event_type": "task",
        },
    ]
    batch = await client.post("/todos/batch-schedule", json={"items": items}, headers=headers)
    assert batch.status_code == 200, batch.text
    results = batch.json()["results"]
    assert len(results) == 3
    assert results[0]["ok"] is True
    assert results[1]["ok"] is True
    assert results[2]["ok"] is False
    assert results[2]["detail"] is not None

    listed = await client.get("/events", params=_WEEK, headers=headers)
    assert len(listed.json()) == 2


async def test_batch_schedule_empty_items_rejected(unlocked) -> None:
    client, _keyfile, headers = unlocked
    batch = await client.post("/todos/batch-schedule", json={"items": []}, headers=headers)
    assert batch.status_code == 422


async def test_batch_schedule_attention_class_defaults_to_active(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post("/todos", json=_todo_payload(), headers=headers)
    todo_id = created.json()["id"]

    items = [
        {
            "todo_id": todo_id,
            "start_at": "2026-07-14T09:00:00Z",
            "event_type": "task",
        }
    ]
    batch = await client.post("/todos/batch-schedule", json={"items": items}, headers=headers)
    assert batch.status_code == 200, batch.text
    result = batch.json()["results"][0]
    assert result["ok"] is True
    assert result["event"]["attention_class"] == "active"
