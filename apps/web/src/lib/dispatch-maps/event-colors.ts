import type { CSSProperties } from "react";
import type { CalendarColor, EventTypeSummary } from "../api-schemas";

/** calendar_color enum -> color token. Fixed swatch palette (contract enum). */
export const calendar_color_var: Record<CalendarColor, string> = {
  slate: "var(--tb-color-slate)",
  rose: "var(--tb-color-rose)",
  amber: "var(--tb-color-amber)",
  violet: "var(--tb-color-violet)",
  emerald: "var(--tb-color-emerald)",
  sky: "var(--tb-color-sky)",
  stone: "var(--tb-color-stone)",
  orange: "var(--tb-color-orange)",
};

/** Neutral fallback token for an event whose type key is unknown (e.g. its
 * custom type was deleted after the event was created). */
export const neutral_event_color_var = calendar_color_var.stone;

/** event_type key -> resolved color token, built from the user's fetched
 * event types (presets + custom) — replaces the old hardcoded enum map. */
export type EventColorMap = Map<string, string>;

export function build_event_color_map(types: EventTypeSummary[]): EventColorMap {
  return new Map(types.map((type) => [type.key, calendar_color_var[type.color]]));
}

export function resolve_event_color(map: EventColorMap, event_type_key: string): string {
  return map.get(event_type_key) ?? neutral_event_color_var;
}

/** Tinted block styling for a calendar event, from its already-resolved color token. */
export function event_block_style(color_var: string): CSSProperties {
  return {
    background: `color-mix(in oklab, ${color_var} 18%, var(--tb-surface-2))`,
    borderColor: `color-mix(in oklab, ${color_var} 55%, transparent)`,
    boxShadow: `0 0 0 var(--tb-space-unit) color-mix(in oklab, ${color_var} 8%, transparent)`,
  };
}

export function color_dot_style(color_var: string): CSSProperties {
  return { background: color_var };
}
