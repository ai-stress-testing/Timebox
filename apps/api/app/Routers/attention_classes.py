"""Attention-class routes — read-only, thin: delegate, convert to Out."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Models.attention_class import AttentionClass
from app.Schemas.attention_class import AttentionClassOut
from app.Services import attention_class_service

router = APIRouter(prefix="/attention-classes", tags=["attention-classes"])


def _to_out(row: AttentionClass) -> AttentionClassOut:
    return AttentionClassOut(
        id=row.id,
        value=row.value,
        label=row.label,
        description=row.description,
        pomodoro_applicable=row.pomodoro_applicable,
        residual_applicable=row.residual_applicable,
        delay_on_no_complete=row.delay_on_no_complete,
        default_r=float(row.default_r),
        default_alarm_class=row.default_alarm_class,
    )


@router.get("", response_model=list[AttentionClassOut])
async def list_attention_classes(
    db: AsyncSession = Depends(get_session),
) -> list[AttentionClassOut]:
    rows = await attention_class_service.list_classes(db)
    return [_to_out(row) for row in rows]
