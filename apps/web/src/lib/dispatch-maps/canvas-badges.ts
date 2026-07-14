import type { CanvasEventType } from "../api-schemas";

/** Server-assigned canvas_event_type -> read-only badge label. */
export const canvas_badge_labels: Record<CanvasEventType, string> = {
  focus_only: "Focus only",
  involved_only: "Involved only",
  passive_multi: "Passive multi",
  focus_passive: "Focus + passive",
};
