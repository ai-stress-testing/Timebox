import { useState } from "react";
import { use_events_range } from "../../Hooks/use-events";
import type { CalendarEvent } from "../../lib/api-schemas";
import { add_days, format_day_and_time, to_iso } from "../../lib/time";
import { Button } from "../ui/button";
import { SelectField, TextField } from "../ui/field";

const pick_window_days = 7;
const default_intent_minutes = "25";

function is_startable(event: CalendarEvent): boolean {
  const is_active = event.attention_class === "active";
  const is_open = event.status === "scheduled" || event.status === "in_progress";
  return is_active && is_open;
}

/** Pick an upcoming active-attention event and start a pomodoro on it. */
function build_pick_window(): { start: string; end: string } {
  const now = new Date();
  return { start: to_iso(now), end: to_iso(add_days(now, pick_window_days)) };
}

export function EventPicker({ on_start, busy }: {
  on_start: (event: CalendarEvent, intended_minutes: number) => void;
  busy: boolean;
}) {
  const [window_range] = useState(build_pick_window);
  const events = use_events_range(window_range.start, window_range.end);
  const candidates = (events.data ?? []).filter(is_startable);
  const [selected_id, set_selected_id] = useState("");
  const [minutes, set_minutes] = useState(default_intent_minutes);
  const selected = candidates.find((event) => event.id === selected_id) ?? candidates[0];

  if (events.isPending) {
    return <p className="text-sm text-mid">Loading upcoming events…</p>;
  }
  if (candidates.length === 0) {
    return (
      <p className="rounded-md border border-edge bg-surface-1 p-6 text-center text-sm text-mid">
        No upcoming active-attention events in the next {pick_window_days} days.
        Create a task or homework event on the calendar first.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-edge bg-surface-1 p-5">
      <SelectField
        label="Event"
        value={selected?.id ?? ""}
        onChange={(event) => set_selected_id(event.target.value)}
      >
        {candidates.map((event) => (
          <option key={event.id} value={event.id}>
            {event.title} — {format_day_and_time(event.start_at)}
          </option>
        ))}
      </SelectField>
      <TextField
        label="Intended minutes"
        type="number"
        min={1}
        value={minutes}
        onChange={(event) => set_minutes(event.target.value)}
      />
      <Button
        variant="primary"
        disabled={busy || selected === undefined}
        onClick={() => selected && on_start(selected, Number(minutes) || 25)}
      >
        {busy ? "Starting…" : "▶ Start pomodoro"}
      </Button>
    </div>
  );
}
