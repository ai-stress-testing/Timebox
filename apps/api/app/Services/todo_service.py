"""Todo service — CRUD plus the to-do-to-schedule funnel (issue #12).

`schedule_todo` reuses `event_service.create_event` rather than duplicating
event-creation logic (canvas-type assignment, encryption, calendar
resolution all stay in one place).
"""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Models.base import utc_now
from app.Models.todo import Todo
from app.Repositories import todo_repo
from app.Schemas.base import AttentionClass
from app.Schemas.event import EventCreate
from app.Schemas.todo import (
    BatchScheduleItem,
    BatchScheduleRequest,
    BatchScheduleResponse,
    BatchScheduleResult,
    TodoCreate,
    TodoOut,
    TodoPatch,
    TodoScheduleRequest,
    TodoScheduleResponse,
)
from app.Services import event_service

# Same fallback duration ScheduleTodoForm uses on the frontend when a todo
# has no estimated_minutes of its own.
_DEFAULT_DURATION_MINUTES = 30


class TodoError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _to_out(todo: Todo, data_key: bytes) -> TodoOut:
    return TodoOut(
        id=todo.id,
        title=crypto.decrypt_field(data_key, todo.title_enc),
        estimated_minutes=todo.estimated_minutes,
        is_done=todo.is_done,
        scheduled_event_id=todo.scheduled_event_id,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
    )


async def create_todo(
    session: AsyncSession, user_id: str, data_key: bytes, payload: TodoCreate
) -> TodoOut:
    todo = Todo(
        user_id=user_id,
        title_enc=crypto.encrypt_field(data_key, payload.title),
        estimated_minutes=payload.estimated_minutes,
        is_done=False,
    )
    todo_repo.add_todo(session, todo)
    await session.commit()
    return _to_out(todo, data_key)


async def list_todos(session: AsyncSession, user_id: str, data_key: bytes) -> list[TodoOut]:
    rows = await todo_repo.list_open(session, user_id)
    return [_to_out(row, data_key) for row in rows]


async def patch_todo(
    session: AsyncSession, user_id: str, data_key: bytes, todo_id: str, payload: TodoPatch
) -> TodoOut:
    todo = await todo_repo.get_todo(session, user_id, todo_id)
    if todo is None:
        raise TodoError(404, "todo not found")
    if payload.title is not None:
        todo.title_enc = crypto.encrypt_field(data_key, payload.title)
    if payload.estimated_minutes is not None:
        todo.estimated_minutes = payload.estimated_minutes
    if payload.is_done is not None:
        todo.is_done = payload.is_done
    await session.commit()
    return _to_out(todo, data_key)


async def delete_todo(session: AsyncSession, user_id: str, todo_id: str) -> None:
    todo = await todo_repo.get_todo(session, user_id, todo_id)
    if todo is None:
        raise TodoError(404, "todo not found")
    todo.deleted_at = utc_now()
    await session.commit()


async def schedule_todo(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    todo_id: str,
    payload: TodoScheduleRequest,
) -> TodoScheduleResponse:
    todo = await todo_repo.get_todo(session, user_id, todo_id)
    if todo is None:
        raise TodoError(404, "todo not found")
    if todo.scheduled_event_id is not None:
        raise TodoError(409, "todo already scheduled")

    title = crypto.decrypt_field(data_key, todo.title_enc)
    event_create = EventCreate(
        title=title,
        event_type=payload.event_type,
        attention_class=payload.attention_class or AttentionClass.active,
        start_at=payload.start_at,
        end_at=payload.end_at,
        estimated_minutes=todo.estimated_minutes,
    )
    created_event = await event_service.create_event(session, user_id, data_key, event_create)

    todo.scheduled_event_id = created_event.id
    todo.is_done = True
    await session.commit()
    return TodoScheduleResponse(todo=_to_out(todo, data_key), event=created_event)


async def _schedule_one(
    session: AsyncSession, user_id: str, data_key: bytes, item: BatchScheduleItem
) -> BatchScheduleResult:
    todo = await todo_repo.get_todo(session, user_id, item.todo_id)
    if todo is None:
        return BatchScheduleResult(todo_id=item.todo_id, ok=False, detail="todo not found")

    duration = todo.estimated_minutes or _DEFAULT_DURATION_MINUTES
    end_at = item.start_at + timedelta(minutes=duration)
    payload = TodoScheduleRequest(
        start_at=item.start_at,
        end_at=end_at,
        event_type=item.event_type,
        attention_class=item.attention_class,
    )
    try:
        response = await schedule_todo(session, user_id, data_key, item.todo_id, payload)
    except TodoError as exc:
        return BatchScheduleResult(todo_id=item.todo_id, ok=False, detail=exc.detail)
    return BatchScheduleResult(todo_id=item.todo_id, ok=True, event=response.event)


async def batch_schedule(
    session: AsyncSession, user_id: str, data_key: bytes, payload: BatchScheduleRequest
) -> BatchScheduleResponse:
    """Schedule many todos in one request via the existing single-item
    `schedule_todo` funnel — one call per item, each independently committed
    (or caught) so a failure on one item never rolls back the others.
    """
    results = [await _schedule_one(session, user_id, data_key, item) for item in payload.items]
    return BatchScheduleResponse(results=results)
