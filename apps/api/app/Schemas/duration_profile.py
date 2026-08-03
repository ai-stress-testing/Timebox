"""Duration-profile DTO (spec 007) — read-only, for estimate prefill hints."""
from app.Schemas.base import ApiModel


class DurationProfileOut(ApiModel):
    label_hash: str | None
    chore_id: str | None
    total_sample_count: int
    total_mean: float
    mc_weight: float
