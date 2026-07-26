"""Routine tests: run lifecycle, skip/abandon paths, reorder-after-delete,
and the schedule_routine -> real calendar event funnel.

`routines.router`/`routines.runs_router` are not wired into `app.main`'s
`create_app()` yet (that's done centrally once the three parallel spec-013
sibling features land — see the final report's "wire me in" snippets), so
this module attaches both routers to the already-built `app` instance here,
at import time, before any test runs. `app.Models.routine` is imported for
its side effect of registering the four new tables on `Base.metadata` so
the per-test `_fresh_db` fixture in conftest.py creates them.
"""
import app.Models.routine  # noqa: F401  (registers tables on Base.metadata)
from app.Core.config import settings
from app.main import app as fastapi_app
from app.Routers import routines as routines_router

_ROUTINES_PREFIX = f"{settings.api_prefix}/routines"
if not any(
    getattr(route, "path", "").startswith(_ROUTINES_PREFIX) for route in fastapi_app.routes
):
    fastapi_app.include_router(routines_router.router, prefix=settings.api_prefix)
    fastapi_app.include_router(routines_router.runs_router, prefix=settings.api_prefix)


def _routine_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {"name": "Morning routine", "color": "sky"}
    return {**base, **overrides}


async def _create_routine(client, headers, **overrides: object) -> dict:
    res = await client.post("/routines", json=_routine_payload(**overrides), headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def _add_step(
    client, headers, routine_id: str, name: str, minutes: int, optional: bool = False
) -> dict:
    res = await client.post(
        f"/routines/{routine_id}/steps",
        json={"name": name, "estimated_minutes": minutes, "is_optional": optional},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


async def test_routine_crud_and_derived_estimate(unlocked) -> None:
    client, _keyfile, headers = unlocked
    routine = await _create_routine(client, headers, name="Gym circuit", color="amber")
    assert routine["step_count"] == 0
    assert routine["estimated_minutes"] is None

    await _add_step(client, headers, routine["id"], "Warm up", 5)
    await _add_step(client, headers, routine["id"], "Lift", 30)

    listed = await client.get("/routines", headers=headers)
    assert listed.status_code == 200
    found = next(r for r in listed.json() if r["id"] == routine["id"])
    assert found["step_count"] == 2
    assert found["estimated_minutes"] == 35

    patched = await client.patch(
        f"/routines/{routine['id']}", json={"name": "Gym circuit v2"}, headers=headers
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Gym circuit v2"

    deleted = await client.delete(f"/routines/{routine['id']}", headers=headers)
    assert deleted.status_code == 204
    after = await client.get("/routines", headers=headers)
    assert routine["id"] not in {r["id"] for r in after.json()}


async def test_full_run_lifecycle_start_advance_finish(unlocked) -> None:
    client, _keyfile, headers = unlocked
    routine = await _create_routine(client, headers, name="Closing checklist")
    step1 = await _add_step(client, headers, routine["id"], "Lock doors", 2)
    step2 = await _add_step(client, headers, routine["id"], "Turn off lights", 3)

    started = await client.post(f"/routines/{routine['id']}/runs", headers=headers)
    assert started.status_code == 201, started.text
    run = started.json()
    assert run["status"] == "in_progress"
    assert len(run["steps"]) == 2
    assert run["steps"][0]["status"] == "active"
    assert run["steps"][0]["routine_step_id"] == step1["id"]
    assert run["steps"][1]["status"] == "pending"

    step_run_1_id = run["steps"][0]["id"]
    advanced_1 = await client.post(
        f"/runs/{run['id']}/steps/{step_run_1_id}/advance",
        json={"actual_minutes": 4},
        headers=headers,
    )
    assert advanced_1.status_code == 200, advanced_1.text
    mid = advanced_1.json()
    assert mid["status"] == "in_progress"
    assert mid["steps"][0]["status"] == "done"
    assert mid["steps"][0]["actual_minutes"] == 4
    assert mid["steps"][1]["status"] == "active"
    assert mid["steps"][1]["routine_step_id"] == step2["id"]

    step_run_2_id = mid["steps"][1]["id"]
    advanced_2 = await client.post(
        f"/runs/{run['id']}/steps/{step_run_2_id}/advance",
        json={"actual_minutes": 6},
        headers=headers,
    )
    assert advanced_2.status_code == 200, advanced_2.text
    finished = advanced_2.json()
    # Auto-completes once no pending steps remain.
    assert finished["status"] == "completed"
    assert finished["ended_at"] is not None
    assert finished["total_actual_minutes"] == 10

    history = await client.get(f"/routines/{routine['id']}/runs", headers=headers)
    assert history.status_code == 200
    assert any(r["id"] == run["id"] for r in history.json())


async def test_explicit_finish_run(unlocked) -> None:
    client, _keyfile, headers = unlocked
    routine = await _create_routine(client, headers, name="Single-step routine")
    await _add_step(client, headers, routine["id"], "Only step", 5)

    started = await client.post(f"/routines/{routine['id']}/runs", headers=headers)
    run = started.json()
    step_run_id = run["steps"][0]["id"]

    advanced = await client.post(
        f"/runs/{run['id']}/steps/{step_run_id}/advance",
        json={"actual_minutes": 5},
        headers=headers,
    )
    assert advanced.json()["status"] == "completed"

    # Finishing an already-completed run is rejected (no longer in_progress).
    refinish = await client.post(f"/runs/{run['id']}/finish", headers=headers)
    assert refinish.status_code == 409


async def test_skip_path_optional_step_only(unlocked) -> None:
    client, _keyfile, headers = unlocked
    routine = await _create_routine(client, headers, name="Skippable routine")
    required = await _add_step(client, headers, routine["id"], "Required step", 5, optional=False)
    optional = await _add_step(client, headers, routine["id"], "Optional step", 5, optional=True)
    assert required["is_optional"] is False
    assert optional["is_optional"] is True

    started = await client.post(f"/routines/{routine['id']}/runs", headers=headers)
    run = started.json()
    required_run_id = run["steps"][0]["id"]

    # Cannot skip the required (non-optional) step.
    rejected = await client.post(
        f"/runs/{run['id']}/steps/{required_run_id}/advance",
        json={"skipped": True},
        headers=headers,
    )
    assert rejected.status_code == 409

    done_required = await client.post(
        f"/runs/{run['id']}/steps/{required_run_id}/advance",
        json={"actual_minutes": 5},
        headers=headers,
    )
    assert done_required.status_code == 200
    mid = done_required.json()
    optional_run_id = mid["steps"][1]["id"]
    assert mid["steps"][1]["status"] == "active"

    skipped = await client.post(
        f"/runs/{run['id']}/steps/{optional_run_id}/advance",
        json={"skipped": True},
        headers=headers,
    )
    assert skipped.status_code == 200, skipped.text
    final = skipped.json()
    assert final["status"] == "completed"
    assert final["steps"][1]["status"] == "skipped"
    # Skipped optional steps are excluded from total_actual_minutes.
    assert final["total_actual_minutes"] == 5


async def test_abandon_path_leaves_completed_actuals_intact(unlocked) -> None:
    client, _keyfile, headers = unlocked
    routine = await _create_routine(client, headers, name="Abandon me")
    await _add_step(client, headers, routine["id"], "Step one", 5)
    await _add_step(client, headers, routine["id"], "Step two", 10)

    started = await client.post(f"/routines/{routine['id']}/runs", headers=headers)
    run = started.json()
    step_run_1_id = run["steps"][0]["id"]

    advanced = await client.post(
        f"/runs/{run['id']}/steps/{step_run_1_id}/advance",
        json={"actual_minutes": 5},
        headers=headers,
    )
    assert advanced.status_code == 200

    abandoned = await client.post(f"/runs/{run['id']}/abandon", headers=headers)
    assert abandoned.status_code == 200, abandoned.text
    result = abandoned.json()
    assert result["status"] == "abandoned"
    # First step's actual is untouched by abandoning.
    assert result["steps"][0]["status"] == "done"
    assert result["steps"][0]["actual_minutes"] == 5
    assert result["steps"][1]["status"] == "active"

    # The routine definition itself is unaffected.
    routines = await client.get("/routines", headers=headers)
    found = next(r for r in routines.json() if r["id"] == routine["id"])
    assert found["step_count"] == 2


async def test_reorder_persists_and_delete_closes_gap(unlocked) -> None:
    client, _keyfile, headers = unlocked
    routine = await _create_routine(client, headers, name="Reorder me")
    step_a = await _add_step(client, headers, routine["id"], "A", 1)
    step_b = await _add_step(client, headers, routine["id"], "B", 2)
    step_c = await _add_step(client, headers, routine["id"], "C", 3)
    assert [step_a["position"], step_b["position"], step_c["position"]] == [0, 1, 2]

    reordered = await client.post(
        f"/routines/{routine['id']}/steps/reorder",
        json={"ordered_step_ids": [step_c["id"], step_a["id"], step_b["id"]]},
        headers=headers,
    )
    assert reordered.status_code == 200, reordered.text
    by_id = {s["id"]: s["position"] for s in reordered.json()}
    assert by_id[step_c["id"]] == 0
    assert by_id[step_a["id"]] == 1
    assert by_id[step_b["id"]] == 2

    # Delete the mid-sequence step (now step_a, position 1) and confirm no gaps.
    deleted = await client.delete(
        f"/routines/{routine['id']}/steps/{step_a['id']}", headers=headers
    )
    assert deleted.status_code == 204

    remaining = await client.get(f"/routines/{routine['id']}/steps", headers=headers)
    assert remaining.status_code == 200
    positions = sorted(s["position"] for s in remaining.json())
    assert positions == list(range(len(positions)))
    assert step_a["id"] not in {s["id"] for s in remaining.json()}


async def test_schedule_routine_creates_real_event(unlocked) -> None:
    client, _keyfile, headers = unlocked
    routine = await _create_routine(client, headers, name="Wake-up sequence", color="violet")
    await _add_step(client, headers, routine["id"], "Stretch", 10)
    await _add_step(client, headers, routine["id"], "Shower", 15)

    scheduled = await client.post(
        f"/routines/{routine['id']}/schedule",
        json={"start_at": "2026-07-27T07:00:00Z", "event_type": "task"},
        headers=headers,
    )
    assert scheduled.status_code == 200, scheduled.text
    body = scheduled.json()
    assert body["event"]["title"] == "Wake-up sequence"
    assert body["event"]["start_at"] == "2026-07-27T07:00:00Z"
    assert body["event"]["end_at"] == "2026-07-27T07:25:00Z"
    assert body["event"]["estimated_minutes"] == 25
    assert body["run"]["event_id"] == body["event"]["id"]
    assert body["run"]["status"] == "pending"

    listed = await client.get(
        "/events?start=2026-07-27T00:00:00Z&end=2026-07-28T00:00:00Z", headers=headers
    )
    assert listed.status_code == 200
    assert body["event"]["id"] in {e["id"] for e in listed.json()}


async def test_schedule_routine_without_steps_rejected(unlocked) -> None:
    client, _keyfile, headers = unlocked
    routine = await _create_routine(client, headers, name="Empty routine")
    scheduled = await client.post(
        f"/routines/{routine['id']}/schedule",
        json={"start_at": "2026-07-27T07:00:00Z", "event_type": "task"},
        headers=headers,
    )
    assert scheduled.status_code == 409
