"""Attention-class schemas — read-only metadata, no create/update/delete."""
from app.Schemas.base import ApiModel


class AttentionClassOut(ApiModel):
    id: str
    value: str
    label: str
    description: str
    pomodoro_applicable: bool
    residual_applicable: bool
    delay_on_no_complete: bool
    default_r: float
    default_alarm_class: str | None
