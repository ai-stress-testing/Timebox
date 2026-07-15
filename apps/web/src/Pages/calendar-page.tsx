import { useState } from "react";
import { EventDrawer } from "../Components/calendar/event-drawer";
import type { DrawerTarget } from "../Components/calendar/event-drawer";
import { WeekGrid } from "../Components/calendar/week-grid";
import { Button } from "../Components/ui/button";
import { use_events_range } from "../Hooks/use-events";
import type { CalendarEvent } from "../lib/api-schemas";
import { add_days, format_week_title, to_iso, week_range } from "../lib/time";
import { to_error_message } from "../Services/api-client";

function WeekNav({ title, on_shift, on_today }: {
  title: string;
  on_shift: (days: number) => void;
  on_today: () => void;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h2 className="font-display text-title tracking-hug font-bold text-hi">{title}</h2>
      <div className="flex gap-2">
        <Button aria-label="Previous week" onClick={() => on_shift(-7)}>←</Button>
        <Button onClick={on_today}>Today</Button>
        <Button aria-label="Next week" onClick={() => on_shift(7)}>→</Button>
      </div>
    </div>
  );
}

export function CalendarPage() {
  const [anchor, set_anchor] = useState(() => new Date());
  const [target, set_target] = useState<DrawerTarget | null>(null);
  const range = week_range(anchor);
  const events = use_events_range(to_iso(range.start), to_iso(range.end));

  const handle_event = (event: CalendarEvent) => set_target({ kind: "edit", event });
  const handle_slot = (start: Date) => set_target({ kind: "create", start });

  return (
    <section aria-label="Week calendar">
      <WeekNav
        title={format_week_title(range)}
        on_shift={(days) => set_anchor((current) => add_days(current, days))}
        on_today={() => set_anchor(new Date())}
      />
      {events.isError ? (
        <p role="alert" className="mb-3 text-sm text-danger">
          {to_error_message(events.error)}
        </p>
      ) : null}
      <WeekGrid
        range={range}
        events={events.data ?? []}
        on_slot={handle_slot}
        on_event={handle_event}
      />
      {target ? <EventDrawer target={target} on_close={() => set_target(null)} /> : null}
    </section>
  );
}
