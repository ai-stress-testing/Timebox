"""Attention-class table: seed idempotency, GET contract, applicability lookup.

`Routers/attention_classes` is not yet wired into `app.main.create_app()`
(deliberately out of scope for this change — see spec 005 handoff notes);
this module registers it onto the shared test app once so the HTTP-level
acceptance criteria ("GET /attention-classes returns the 3 rows") are
exercised the same way production traffic eventually will be. The guard
makes this a no-op once the router is wired centrally in `main.py`.
"""
from app.Core.config import settings
from app.Core.database import session_factory
from app.main import app
from app.Routers import attention_classes
from app.Services import attention_class_service

_ROUTE_PATH = f"{settings.api_prefix}/attention-classes"
if not any(getattr(route, "path", None) == _ROUTE_PATH for route in app.routes):
    app.include_router(attention_classes.router, prefix=settings.api_prefix)

_EXPECTED = {
    "active": {"pomodoro_applicable": True, "residual_applicable": True, "default_r": 0.2},
    "involved": {"pomodoro_applicable": False, "residual_applicable": False, "default_r": 0.3},
    "passive": {"pomodoro_applicable": False, "residual_applicable": False, "default_r": 0.8},
}


async def test_ensure_seeded_is_idempotent() -> None:
    async with session_factory() as db:
        await attention_class_service.ensure_seeded(db)
        first_rows = await attention_class_service.list_classes(db)
        assert len(first_rows) == 3

        await attention_class_service.ensure_seeded(db)
        second_rows = await attention_class_service.list_classes(db)
        assert len(second_rows) == 3
        assert {row.id for row in first_rows} == {row.id for row in second_rows}


async def test_is_pomodoro_and_residual_applicable_for_all_three_classes() -> None:
    async with session_factory() as db:
        for value, expected in _EXPECTED.items():
            assert (
                await attention_class_service.is_pomodoro_applicable(db, value)
                == expected["pomodoro_applicable"]
            )
            assert (
                await attention_class_service.is_residual_applicable(db, value)
                == expected["residual_applicable"]
            )


async def test_unknown_attention_class_value_is_not_applicable() -> None:
    async with session_factory() as db:
        assert await attention_class_service.is_pomodoro_applicable(db, "bogus") is False
        assert await attention_class_service.is_residual_applicable(db, "bogus") is False


async def test_list_attention_classes_returns_three_rows_with_correct_flags(unlocked) -> None:
    client, _keyfile, headers = unlocked
    res = await client.get("/attention-classes", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    assert len(rows) == 3
    by_value = {row["value"]: row for row in rows}
    assert set(by_value) == set(_EXPECTED)
    for value, expected in _EXPECTED.items():
        row = by_value[value]
        assert row["pomodoro_applicable"] is expected["pomodoro_applicable"]
        assert row["residual_applicable"] is expected["residual_applicable"]
        assert row["default_r"] == expected["default_r"]
        assert row["label"]
        assert row["description"]
        assert "id" in row and "delay_on_no_complete" in row and "default_alarm_class" in row

    # Idempotent: a second GET does not duplicate rows.
    again = await client.get("/attention-classes", headers=headers)
    assert len(again.json()) == 3
