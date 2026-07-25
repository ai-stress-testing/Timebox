"""Event-type CRUD, preset seeding/protection, and the type_key event integration."""

_PRESET_KEYS = {"meeting", "task", "personal", "chore", "homework", "passive", "physical"}


def _event_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Deep work: quarterly report",
        "event_type": "task",
        "attention_class": "active",
        "start_at": "2026-07-14T09:00:00Z",
        "end_at": "2026-07-14T10:30:00Z",
    }
    return {**base, **overrides}


async def test_presets_seeded_on_first_list(unlocked) -> None:
    client, _keyfile, headers = unlocked
    res = await client.get("/event-types", headers=headers)
    assert res.status_code == 200, res.text
    types = res.json()
    assert len(types) == 7
    assert {t["key"] for t in types} == _PRESET_KEYS
    assert all(t["is_preset"] is True for t in types)
    assert all(t["is_active"] is True for t in types)

    # Idempotent: a second list call does not re-seed.
    again = await client.get("/event-types", headers=headers)
    assert len(again.json()) == 7


async def test_create_custom_type_appears_in_list_and_on_event(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post(
        "/event-types", json={"label": "Deep Focus", "color": "violet"}, headers=headers
    )
    assert created.status_code == 201, created.text
    custom = created.json()
    assert custom["key"] == "deep-focus"
    assert custom["label"] == "Deep Focus"
    assert custom["color"] == "violet"
    assert custom["is_preset"] is False
    assert custom["is_active"] is True

    listed = await client.get("/event-types", headers=headers)
    assert len(listed.json()) == 8
    assert custom["id"] in {t["id"] for t in listed.json()}

    event = await client.post(
        "/events", json=_event_payload(event_type=custom["key"]), headers=headers
    )
    assert event.status_code == 201, event.text
    assert event.json()["event_type"] == custom["key"]

    fetched = await client.get(f"/events/{event.json()['id']}", headers=headers)
    assert fetched.json()["event_type"] == custom["key"]


async def test_create_custom_type_dedupes_slug(unlocked) -> None:
    client, _keyfile, headers = unlocked
    first = await client.post(
        "/event-types", json={"label": "Focus", "color": "sky"}, headers=headers
    )
    second = await client.post(
        "/event-types", json={"label": "Focus", "color": "amber"}, headers=headers
    )
    assert first.json()["key"] == "focus"
    assert second.json()["key"] == "focus-2"


async def test_patch_recolor_custom_type(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post(
        "/event-types", json={"label": "Errands", "color": "amber"}, headers=headers
    )
    type_id = created.json()["id"]

    patched = await client.patch(
        f"/event-types/{type_id}", json={"color": "rose"}, headers=headers
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["color"] == "rose"
    assert patched.json()["label"] == "Errands"


async def test_delete_custom_type_removes_it(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post(
        "/event-types", json={"label": "Errands", "color": "amber"}, headers=headers
    )
    type_id = created.json()["id"]

    deleted = await client.delete(f"/event-types/{type_id}", headers=headers)
    assert deleted.status_code == 204

    listed = await client.get("/event-types", headers=headers)
    assert type_id not in {t["id"] for t in listed.json()}


async def test_delete_preset_type_rejected(unlocked) -> None:
    client, _keyfile, headers = unlocked
    listed = await client.get("/event-types", headers=headers)
    preset_id = next(t["id"] for t in listed.json() if t["key"] == "meeting")

    deleted = await client.delete(f"/event-types/{preset_id}", headers=headers)
    assert deleted.status_code == 409

    still_listed = await client.get("/event-types", headers=headers)
    assert preset_id in {t["id"] for t in still_listed.json()}


async def test_event_create_with_unknown_type_key_rejected(unlocked) -> None:
    client, _keyfile, headers = unlocked
    res = await client.post(
        "/events", json=_event_payload(event_type="not-a-real-type"), headers=headers
    )
    assert res.status_code == 422
