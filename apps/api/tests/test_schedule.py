"""Monte Carlo scheduler: determinism, bounds, apply-to-calendar."""
from httpx import AsyncClient

from app.Pipelines.monte_carlo import MAX_MC_ITERATIONS


async def _create_chore(client: AsyncClient, headers: dict[str, str], name: str) -> str:
    res = await client.post(
        "/chores",
        json={
            "name": name,
            "estimated_minutes": 30,
            "n_days": 3,
            "preferred_days": [6],
            "preferred_time_start": "09:00",
            "preferred_time_end": "18:00",
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def test_same_seed_same_schedule(unlocked) -> None:
    client, _keyfile, headers = unlocked
    await _create_chore(client, headers, "Vacuum")
    await _create_chore(client, headers, "Dishes")

    body = {"window_days": 14, "iterations": 50, "seed": 424242}
    first = await client.post("/schedule/runs", json=body, headers=headers)
    second = await client.post("/schedule/runs", json=body, headers=headers)
    assert first.status_code == 201 and second.status_code == 201

    def slots(run: dict) -> list[tuple[str, str, str]]:
        return [
            (o["chore_id"], o["proposed_start_at"], o["proposed_end_at"])
            for o in run["occurrences"]
        ]

    assert slots(first.json()) == slots(second.json())
    assert first.json()["score"] == second.json()["score"]
    assert len(first.json()["occurrences"]) > 0


async def test_iterations_hard_bounded(unlocked) -> None:
    client, _keyfile, headers = unlocked
    res = await client.post(
        "/schedule/runs",
        json={"window_days": 7, "iterations": MAX_MC_ITERATIONS + 1},
        headers=headers,
    )
    assert res.status_code == 422


async def test_apply_creates_chore_events(unlocked) -> None:
    client, _keyfile, headers = unlocked
    await _create_chore(client, headers, "Water plants")
    run = await client.post(
        "/schedule/runs", json={"window_days": 7, "iterations": 20, "seed": 7}, headers=headers
    )
    run_id = run.json()["id"]
    occurrence_count = len(run.json()["occurrences"])

    applied = await client.post(f"/schedule/runs/{run_id}/apply", headers=headers)
    assert applied.status_code == 200
    assert applied.json()["events_created"] == occurrence_count

    again = await client.post(f"/schedule/runs/{run_id}/apply", headers=headers)
    assert again.status_code == 409

    window = run.json()
    events = await client.get(
        "/events",
        params={"start": window["window_start"], "end": window["window_end"]},
        headers=headers,
    )
    chore_events = [e for e in events.json() if e["event_type"] == "chore"]
    assert len(chore_events) == occurrence_count
    assert all(e["title"] == "Water plants" for e in chore_events)


async def test_chore_patch_rejects_bad_time_and_days(unlocked) -> None:
    client, _keyfile, headers = unlocked
    chore_id = await _create_chore(client, headers, "Mop floors")

    bad_time = await client.patch(
        f"/chores/{chore_id}", json={"preferred_time_start": "9am"}, headers=headers
    )
    assert bad_time.status_code == 422

    bad_day = await client.patch(
        f"/chores/{chore_id}", json={"avoid_days": [7]}, headers=headers
    )
    assert bad_day.status_code == 422
