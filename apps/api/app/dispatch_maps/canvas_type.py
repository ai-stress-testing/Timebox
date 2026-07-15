"""Canvas event type assignment — the DB-Schemas 'Automatic Assignment Rules'
table as data. Never set by the user; recomputed on create/update.
"""
from app.Schemas.base import AttentionClass, CanvasEventType

ATTENTION_DEFAULTS: dict[AttentionClass, dict[str, object]] = {
    AttentionClass.active: {"pomodoro": True, "residual": True, "default_r": 0.2},
    AttentionClass.involved: {"pomodoro": False, "residual": False, "default_r": 0.3},
    AttentionClass.passive: {"pomodoro": False, "residual": False, "default_r": 0.8},
}

OVERLAP_TYPE_MAP: dict[frozenset[AttentionClass], CanvasEventType] = {
    frozenset({AttentionClass.active}): CanvasEventType.focus_only,
    frozenset({AttentionClass.involved}): CanvasEventType.involved_only,
    frozenset({AttentionClass.passive}): CanvasEventType.passive_multi,
    frozenset({AttentionClass.active, AttentionClass.passive}): CanvasEventType.focus_passive,
    frozenset({AttentionClass.involved, AttentionClass.passive}): CanvasEventType.involved_only,
    frozenset({AttentionClass.active, AttentionClass.involved}): CanvasEventType.focus_only,
    frozenset(
        {AttentionClass.active, AttentionClass.involved, AttentionClass.passive}
    ): CanvasEventType.focus_passive,
}


def assign_canvas_type(
    own_class: AttentionClass, overlapping_classes: frozenset[AttentionClass]
) -> CanvasEventType:
    combined = frozenset({own_class, *overlapping_classes})
    fallback = OVERLAP_TYPE_MAP[frozenset({own_class})]
    return OVERLAP_TYPE_MAP.get(combined, fallback)
