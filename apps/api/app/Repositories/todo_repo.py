"""Todo queries — live rows only (soft delete)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.todo import Todo


async def list_open(session: AsyncSession, user_id: str) -> list[Todo]:
    stmt = (
        select(Todo)
        .where(Todo.user_id == user_id, Todo.is_done.is_(False), Todo.deleted_at.is_(None))
        .order_by(Todo.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_todo(session: AsyncSession, user_id: str, todo_id: str) -> Todo | None:
    stmt = select(Todo).where(
        Todo.id == todo_id,
        Todo.user_id == user_id,
        Todo.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_todo(session: AsyncSession, todo: Todo) -> Todo:
    session.add(todo)
    return todo
