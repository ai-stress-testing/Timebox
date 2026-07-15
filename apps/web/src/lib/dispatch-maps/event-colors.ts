import type { CSSProperties } from "react";
import type { CalendarColor, EventType } from "../api-schemas";

/** event_type -> semantic color token (CSS custom property reference). */
export const event_type_color_var: Record<EventType, string> = {
  meeting: "var(--tb-color-sky)",
  task: "var(--tb-color-violet)",
  personal: "var(--tb-color-emerald)",
  chore: "var(--tb-color-amber)",
  homework: "var(--tb-color-rose)",
  passive: "var(--tb-color-slate)",
  physical: "var(--tb-color-orange)",
};

/** calendar_color enum -> color token. */
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

/** Tinted block styling for a calendar event, derived from its type token. */
export function event_block_style(event_type: EventType): CSSProperties {
  const color = event_type_color_var[event_type];
  return {
    background: `color-mix(in oklab, ${color} 18%, var(--tb-surface-2))`,
    borderColor: `color-mix(in oklab, ${color} 55%, transparent)`,
    boxShadow: `0 0 0 var(--tb-space-unit) color-mix(in oklab, ${color} 8%, transparent)`,
  };
}

export function color_dot_style(color_var: string): CSSProperties {
  return { background: color_var };
}
