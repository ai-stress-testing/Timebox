"""Duration-profile learning (spec 007): Welford stats over event/chore
completions, plus the read-side prefill lookup.

`duration_profiles.router` is not yet mounted on `app` in `app.main` (out of
this agent's edit scope — orchestrator wires it, see final report). It is
mounted here directly onto the shared `app` instance so these tests exercise
the real HTTP path; this has no effect on production wiring.
"""
from sqlalchemy import select

from app.Core.config import settings
from app.Core.database import session_factory
from app.main import app
from app.Models.chore import ChoreDefinition
from app.Routers import duration_profiles
from app.Services import duration_profile_service

app.include_router(duration_profiles.router, prefix=settings.api_prefix)


def _event_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Deep work: quarterly report",
        "event_type": "task",
        "attention_class": "active",
        "start_at": "2026-07-14T09:00:00Z",
        "end_at": "2026-07-14T10:30:00Z",
    }
    return {**base, **overrides}


async def _create_and_complete(client, headers, title: str, actual_minutes: int) -> None:
    created = await client.post("/events", json=_event_payload(title=title), headers=headers)
    assert created.status_code == 201, created.text
    patched = await client.patch(
        f"/events/{created.json()['id']}",
        json={"actual_minutes": actual_minutes},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text


async def test_recording_three_completions_produces_correct_mean(unlocked) -> None:
    client, _keyfile, headers = unlocked
    for minutes in (30, 45, 60):
        await _create_and_complete(client, headers, "Weekly review", minutes)

    looked_up = await client.get(
        "/duration-profiles/lookup", params={"title": "weekly review"}, headers=headers
    )
    assert looked_up.status_code == 200, looked_up.text
    body = looked_up.json()
    assert body["total_sample_count"] == 3
    assert body["total_mean"] == (30 + 45 + 60) / 3


async def test_title_normalization_is_case_and_whitespace_insensitive(unlocked) -> None:
    client, _keyfile, headers = unlocked
    await _create_and_complete(client, headers, "  Grocery Run  ", 25)

    looked_up = await client.get(
        "/duration-profiles/lookup", params={"title": "grocery run"}, headers=headers
    )
    assert looked_up.status_code == 200, looked_up.text
    assert looked_up.json()["total_sample_count"] == 1
    assert looked_up.json()["total_mean"] == 25.0


async def test_lookup_404_for_unknown_title(unlocked) -> None:
    client, _keyfile, headers = unlocked
    res = await client.get(
        "/duration-profiles/lookup", params={"title": "never seen this"}, headers=headers
    )
    assert res.status_code == 404


async def test_patch_without_actual_minutes_does_not_record(unlocked) -> None:
    client, _keyfile, headers = unlocked
    created = await client.post(
        "/events", json=_event_payload(title="Untouched title"), headers=headers
    )
    await client.patch(
        f"/events/{created.json()['id']}",
        json={"title": "Untouched title (renamed)"},
        headers=headers,
    )
    res = await client.get(
        "/duration-profiles/lookup", params={"title": "Untouched title"}, headers=headers
    )
    assert res.status_code == 404


async def test_chore_completion_updates_mc_weight(unlocked) -> None:
    """`chore_entropy_service.record_completion` (the real chore-completion
    call site) receives only a `completed_at` timestamp today, no actual
    duration figure — there's nothing to feed `record_chore_completion` at
    that call site (see agent report). This test exercises the service
    function directly to prove the write reaches `ChoreDefinition.mc_weight`,
    ready for whichever future spec starts passing a real duration in.
    """
    client, _keyfile, headers = unlocked
    created = await client.post(
        "/chores",
        json={"name": "Deep clean kitchen", "estimated_minutes": 60, "n_days": 7},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    chore_id = created.json()["id"]

    async with session_factory() as session:
        chore = (
            await session.execute(select(ChoreDefinition).where(ChoreDefinition.id == chore_id))
        ).scalar_one()
        assert float(chore.mc_weight) == 1.0

        # First sample: mean equals the sample itself, no ratio to derive a
        # weight from yet — mc_weight stays at its 1.0 default.
        await duration_profile_service.record_chore_completion(session, chore.user_id, chore, 60)
        await session.commit()
        assert float(chore.mc_weight) == 1.0

        # Second sample: this chore is consistently taking 2x its estimate,
        # so mc_weight should move away from 1.0 (upweighted toward "give
        # this more MC weight since it runs long").
        await duration_profile_service.record_chore_completion(session, chore.user_id, chore, 120)
        await session.commit()
        assert float(chore.mc_weight) != 1.0

    async with session_factory() as session:
        refetched = (
            await session.execute(select(ChoreDefinition).where(ChoreDefinition.id == chore_id))
        ).scalar_one()
        assert float(refetched.mc_weight) != 1.0
