"""Pomodoro: start/finish, break rule, residual prompt flow."""
from app.dispatch_maps.break_rules import get_break_minutes


def test_break_rule_dispatch() -> None:
    assert get_break_minutes(25) == 5
    assert get_break_minutes(39) == 5
    assert get_break_minutes(40) == 20
    assert get_break_minutes(90) == 45


async def _create_active_event(client, headers) -> str:
    res = await client.post(
        "/events",
        json={
            "title": "Study session",
            "event_type": "homework",
            "attention_class": "active",
            "start_at": "2026-07-14T09:00:00Z",
            "end_at": "2026-07-14T10:00:00Z",
        },
        headers=headers,
    )
    return res.json()["id"]


async def test_pomodoro_completion_flow(unlocked) -> None:
    client, _keyfile, headers = unlocked
    event_id = await _create_active_event(client, headers)

    started = await client.post(
        "/pomodoro/sessions", json={"event_id": event_id, "intended_minutes": 25}, headers=headers
    )
    assert started.status_code == 201, started.text
    session_id = started.json()["id"]

    duplicate = await client.post(
        "/pomodoro/sessions", json={"event_id": event_id, "intended_minutes": 25}, headers=headers
    )
    assert duplicate.status_code == 409

    finished = await client.post(
        f"/pomodoro/sessions/{session_id}/finish",
        json={"completion_flag": True, "notes": "flow state"},
        headers=headers,
    )
    body = finished.json()
    assert body["session"]["completion_flag"] is True
    assert body["break_minutes"] == 5
    assert body["residual_prompt"] is None

    event = await client.get(f"/events/{event_id}", headers=headers)
    assert event.json()["status"] == "completed"


async def test_residual_prompt_flow(unlocked) -> None:
    client, _keyfile, headers = unlocked
    event_id = await _create_active_event(client, headers)
    started = await client.post(
        "/pomodoro/sessions", json={"event_id": event_id, "intended_minutes": 25}, headers=headers
    )
    finished = await client.post(
        f"/pomodoro/sessions/{started.json()['id']}/finish",
        json={"completion_flag": False},
        headers=headers,
    )
    prompt = finished.json()["residual_prompt"]
    assert prompt is not None and prompt["status"] == "pending"

    responded = await client.post(
        f"/pomodoro/prompts/{prompt['id']}/respond",
        json={"response": "confirmed", "remaining_minutes": 20},
        headers=headers,
    )
    body = responded.json()
    assert body["prompt"]["status"] == "confirmed"
    assert body["residual"]["remaining_minutes"] == 20

    again = await client.post(
        f"/pomodoro/prompts/{prompt['id']}/respond",
        json={"response": "dismissed"},
        headers=headers,
    )
    assert again.status_code == 409


async def test_pomodoro_rejected_for_passive_event(unlocked) -> None:
    client, _keyfile, headers = unlocked
    res = await client.post(
        "/events",
        json={
            "title": "Laundry",
            "event_type": "passive",
            "attention_class": "passive",
            "start_at": "2026-07-14T09:00:00Z",
            "end_at": "2026-07-14T10:00:00Z",
        },
        headers=headers,
    )
    started = await client.post(
        "/pomodoro/sessions",
        json={"event_id": res.json()["id"], "intended_minutes": 25},
        headers=headers,
    )
    assert started.status_code == 409
