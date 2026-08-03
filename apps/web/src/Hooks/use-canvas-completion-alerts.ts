import { useEffect, useRef } from "react";
import { display_seconds } from "../Components/canvas/timer-math";
import type { CanvasItem } from "../lib/api-schemas";
import { notify_timer_complete, request_notification_permission } from "../lib/timer-notify";
import { push_toast } from "../Store/toast-store";

const tick_interval_ms = 1_000;

/** Fires a chime + toast + (permission-gated) desktop notification the
 * instant a running canvas timer's client-computed countdown reaches zero —
 * ahead of the server's own lazy "completed" status flip, which only
 * happens on the next mutation or the 15s poll (see
 * canvas_service.py::_sync_completion and use-canvas.ts's refetchInterval),
 * so the alert isn't delayed by that.
 *
 * Dedup key is (item.id, item.started_at): a timer only ever completes once
 * per run, and a fresh `started_at` from the next Start click naturally
 * re-arms the alert without any explicit reset bookkeeping.
 */
export function use_canvas_completion_alerts(items: CanvasItem[]): void {
  const notified_ref = useRef<Map<string, string | null>>(new Map());

  useEffect(() => {
    request_notification_permission();
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      const now_ms = Date.now();
      for (const item of items) {
        if (item.mode !== "timer" || item.status !== "running") continue;
        if (display_seconds(item, now_ms) > 0) continue;
        if (notified_ref.current.get(item.id) === item.started_at) continue;
        notified_ref.current.set(item.id, item.started_at);
        notify_timer_complete(item.title);
        push_toast(`"${item.title}" finished.`, "ok");
      }
    }, tick_interval_ms);
    return () => clearInterval(id);
  }, [items]);
}
