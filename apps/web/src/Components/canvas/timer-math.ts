import type { CanvasItem } from "../../lib/api-schemas";

/*
 * Client-side mirror of the backend's `live_elapsed` (Pipelines/canvas_timer.py):
 * a client-side interval computed against the item's server `started_at` +
 * `accumulated_seconds`, not a per-second network round-trip (spec 010).
 * Shared by RadialCanvas (the face on the canvas) and the edit card (the
 * face in the CRUD drawer) so there is exactly one place this arithmetic lives.
 */

export function elapsed_seconds_now(item: CanvasItem, now_ms: number): number {
  if (item.status !== "running" || item.started_at === null) return item.accumulated_seconds;
  const started_ms = new Date(item.started_at).getTime();
  return item.accumulated_seconds + Math.max(0, Math.floor((now_ms - started_ms) / 1000));
}

/** Countdown remaining for a timer, elapsed count-up for a stopwatch —
 * whichever number the face should show. */
export function display_seconds(item: CanvasItem, now_ms: number): number {
  const elapsed = elapsed_seconds_now(item, now_ms);
  if (item.mode === "timer" && item.duration_seconds !== null) {
    return Math.max(0, item.duration_seconds - elapsed);
  }
  return elapsed;
}
