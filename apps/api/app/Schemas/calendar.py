"""Calendar schemas."""
from pydantic import Field

from app.Schemas.base import ApiModel, CalendarColor, CalendarColorField, UtcDateTime


class CalendarCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    color: CalendarColorField | None = None


class CalendarOut(ApiModel):
    id: str
    name: str
    color: CalendarColor | None
    is_visible: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime
