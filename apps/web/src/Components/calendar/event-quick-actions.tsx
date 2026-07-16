import { useState } from "react";
import type { CalendarEvent, EventPatch } from "../../lib/api-schemas";
import { use_update_event } from "../../Hooks/use-events";
import { add_minutes_iso } from "../../lib/time";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Button } from "../ui/button";
import { TextField } from "../ui/field";

const minutes_per_day = 1440;

/** Feature-rich edit shortcuts (issue #9): reschedule and log actuals in one
 * click, all mapping to existing event fields. Non-recurring events only —
 * shifting a virtual occurrence would move the whole series anchor. */
export function EventQuickActions({ event, on_done }: {
  event: CalendarEvent;
  on_done: () => void;
}) {
  const update = use_update_event();
  const [actual, set_actual] = useState(
    event.actual_minutes == null ? "" : String(event.actual_minutes),
  );

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

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-edge p-3">
      <span className="text-xs font-medium tracking-wide text-mid uppercase">Quick actions</span>
      <div className="flex flex-wrap gap-2">
        <Button disabled={update.isPending} onClick={move_tomorrow}>Move to tomorrow</Button>
        <Button disabled={update.isPending} onClick={() => extend(15)}>Extend +15m</Button>
        <Button disabled={update.isPending} onClick={() => extend(30)}>Extend +30m</Button>
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
        <Button variant="primary" disabled={update.isPending} onClick={log_actual}>
          Log
        </Button>
      </div>
    </div>
  );
}
