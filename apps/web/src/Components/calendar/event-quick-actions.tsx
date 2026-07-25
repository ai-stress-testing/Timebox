import { useState } from "react";
import type { CalendarEvent, EventPatch } from "../../lib/api-schemas";
import { use_split_event, use_update_event } from "../../Hooks/use-events";
import {
  add_minutes_iso,
  compose_local_iso,
  date_input_value,
  minutes_between,
  time_input_value,
} from "../../lib/time";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Button } from "../ui/button";
import { TextField } from "../ui/field";

const minutes_per_day = 1440;

/** Default split point: the event's midpoint, as an <input type=time> value. */
function default_split_time(event: CalendarEvent): string {
  const midpoint = add_minutes_iso(
    event.start_at,
    Math.round(minutes_between(event.start_at, event.end_at) / 2),
  );
  return time_input_value(midpoint);
}

/** Feature-rich edit shortcuts (issue #9): reschedule and log actuals in one
 * click, all mapping to existing event fields. Non-recurring events only —
 * shifting a virtual occurrence would move the whole series anchor. */
export function EventQuickActions({ event, on_done }: {
  event: CalendarEvent;
  on_done: () => void;
}) {
  const update = use_update_event();
  const split = use_split_event();
  const [actual, set_actual] = useState(
    event.actual_minutes == null ? "" : String(event.actual_minutes),
  );
  const [split_time, set_split_time] = useState(() => default_split_time(event));

  const apply = (patch: EventPatch, message: string) => {
    update.mutate(
      { id: event.id, patch },
      {
        onSuccess: () => {
          push_toast(message, "ok");
          on_done();
        },
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  const move_tomorrow = () =>
    apply(
      {
        start_at: add_minutes_iso(event.start_at, minutes_per_day),
        end_at: add_minutes_iso(event.end_at, minutes_per_day),
      },
      "Moved to tomorrow.",
    );

  const extend = (mins: number) =>
    apply({ end_at: add_minutes_iso(event.end_at, mins) }, `Extended by ${mins} min.`);

  const log_actual = () => {
    const minutes = Number(actual);
    if (!Number.isInteger(minutes) || minutes < 0) {
      push_toast("Enter whole minutes ≥ 0.", "danger");
      return;
    }
    apply({ actual_minutes: minutes }, "Logged actual time.");
  };

  const do_split = () => {
    const split_at = compose_local_iso(date_input_value(event.start_at), split_time);
    if (!split_at) {
      push_toast("Enter a valid split time.", "danger");
      return;
    }
    split.mutate(
      { id: event.id, split_at },
      {
        onSuccess: () => {
          push_toast("Event split in two.", "ok");
          on_done();
        },
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  const busy = update.isPending || split.isPending;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-edge p-3">
      <span className="text-xs font-medium tracking-wide text-mid uppercase">Quick actions</span>
      <div className="flex flex-wrap gap-2">
        <Button disabled={busy} onClick={move_tomorrow}>Move to tomorrow</Button>
        <Button disabled={busy} onClick={() => extend(15)}>Extend +15m</Button>
        <Button disabled={busy} onClick={() => extend(30)}>Extend +30m</Button>
      </div>
      <div className="flex items-end gap-2">
        <TextField
          label="Actual minutes"
          type="number"
          min={0}
          value={actual}
          placeholder="How long did it really take?"
          onChange={(event_) => set_actual(event_.target.value)}
        />
        <Button variant="primary" disabled={busy} onClick={log_actual}>
          Log
        </Button>
      </div>
      <div className="flex items-end gap-2">
        <TextField
          label="Split at"
          type="time"
          value={split_time}
          onChange={(event_) => set_split_time(event_.target.value)}
        />
        <Button disabled={busy} onClick={do_split}>
          Split into two
        </Button>
      </div>
    </div>
  );
}
