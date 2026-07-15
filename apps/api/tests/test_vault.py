"""Vault journey: generate → unlock → locked-route enforcement → tamper rejection."""
from httpx import AsyncClient


async def test_status_starts_unregistered(client: AsyncClient) -> None:
    res = await client.get("/vault/status")
    assert res.status_code == 200
    assert res.json() == {"registered": False}


async def test_generate_then_unlock_flow(client: AsyncClient) -> None:
    generated = await client.post("/vault/generate")
    assert generated.status_code == 200
    keyfile = generated.json()["keyfile"]
    assert keyfile["format"] == "timebox-keyfile"

    second = await client.post("/vault/generate")
    assert second.status_code == 409

    unlocked = await client.post("/vault/unlock", json={"keyfile": keyfile})
    assert unlocked.status_code == 200
    body = unlocked.json()
    assert body["user_id"] == keyfile["user_id"]
    assert body["token"]


async def test_routes_locked_without_token(client: AsyncClient) -> None:
    res = await client.get("/events", params={"start": "2026-01-01T00:00:00Z", "end": "2026-01-08T00:00:00Z"})
    assert res.status_code == 401


async def test_tampered_keyfile_rejected_generically(client: AsyncClient) -> None:
    generated = await client.post("/vault/generate")
    keyfile = generated.json()["keyfile"]
    tampered = {**keyfile, "secret": keyfile["secret"][:-4] + "AAAA"}
    res = await client.post("/vault/unlock", json={"keyfile": tampered})
    assert res.status_code == 401
    assert res.json()["detail"] == "unlock failed"


async def test_reset_erases_everything(unlocked) -> None:
    client, keyfile, headers = unlocked
    res = await client.post("/vault/reset", json={"confirm": "ERASE"}, headers=headers)
    assert res.status_code == 204
    status = await client.get("/vault/status")
    assert status.json() == {"registered": False}
    relock = await client.post("/vault/unlock", json={"keyfile": keyfile})
    assert relock.status_code == 401
