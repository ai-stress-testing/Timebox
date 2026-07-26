import { useEffect, useState } from "react";
import { format_elapsed } from "../focus/session-timer";
import { display_seconds } from "./timer-math";
import { Button } from "../ui/button";
import { Drawer } from "../ui/drawer";
import { TextField } from "../ui/field";
import type { CanvasItem } from "../../lib/api-schemas";

const tick_interval_ms = 1_000;
const seconds_per_minute = 60;

/** Clicking a canvas item opens this for its full CRUD surface: edit
 * title/duration, start/pause/reset, delete (spec 010's "core interaction"). */
export function CanvasItemEditCard({
  item,
  on_close,
  on_save,
  on_start,
  on_pause,
  on_reset,
  on_delete,
  busy,
}: {
  item: CanvasItem;
  on_close: () => void;
  on_save: (patch: { title?: string; duration_seconds?: number }) => void;
  on_start: () => void;
  on_pause: () => void;
  on_reset: () => void;
  on_delete: () => void;
  busy: boolean;
}) {
  const [title, set_title] = useState(item.title);
  const [duration_minutes, set_duration_minutes] = useState(
    item.duration_seconds !== null ? String(item.duration_seconds / seconds_per_minute) : "",
  );
  const [now_ms, set_now_ms] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => set_now_ms(Date.now()), tick_interval_ms);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    set_title(item.title);
    set_duration_minutes(
      item.duration_seconds !== null ? String(item.duration_seconds / seconds_per_minute) : "",
    );
  }, [item.id, item.title, item.duration_seconds]);

  const handle_save = () => {
    const patch: { title?: string; duration_seconds?: number } = {};
    const trimmed = title.trim();
    if (trimmed !== "" && trimmed !== item.title) patch.title = trimmed;
    if (item.mode === "timer") {
      const minutes = Number(duration_minutes);
      const current_minutes = (item.duration_seconds ?? 0) / seconds_per_minute;
      if (Number.isFinite(minutes) && minutes > 0 && minutes !== current_minutes) {
        patch.duration_seconds = Math.round(minutes * seconds_per_minute);
      }
    }
    if (Object.keys(patch).length > 0) on_save(patch);
  };

  return (
    <Drawer title={item.mode === "timer" ? "Edit timer" : "Edit stopwatch"} on_close={on_close}>
      <div className="flex flex-col gap-5">
        <p
          className="font-display text-display tracking-hug text-center font-black
            bg-clip-text text-transparent [background-image:var(--tb-gradient-accent)]"
        >
          {format_elapsed(display_seconds(item, now_ms))}
        </p>
        <p className="text-center text-xs text-low">
          {item.status === "running"
            ? "running"
            : item.status === "completed"
              ? "completed"
              : "paused"}
        </p>

        <TextField label="Title" value={title} onChange={(event) => set_title(event.target.value)} />
        {item.mode === "timer" ? (
          <TextField
            label="Duration (minutes)"
            type="number"
            min={1}
            value={duration_minutes}
            onChange={(event) => set_duration_minutes(event.target.value)}
          />
        ) : null}
        <Button variant="ghost" disabled={busy} onClick={handle_save}>
          Save changes
        </Button>

        <div className="flex flex-wrap gap-2 border-t border-edge pt-4">
          <Button
            variant="primary"
            disabled={busy || item.status === "running" || item.status === "completed"}
            onClick={on_start}
          >
            Start
          </Button>
          <Button variant="ghost" disabled={busy || item.status !== "running"} onClick={on_pause}>
            Pause
          </Button>
          <Button variant="ghost" disabled={busy} onClick={on_reset}>
            Reset
          </Button>
          <Button variant="danger" disabled={busy} onClick={on_delete}>
            Delete
          </Button>
        </div>
      </div>
    </Drawer>
  );
}
