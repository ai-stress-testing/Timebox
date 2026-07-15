import type { CalendarEvent } from "../../lib/api-schemas";
import { event_block_style } from "../../lib/dispatch-maps/event-colors";
import { date_input_value } from "../../lib/time";

type AllDayStripProps = {
  days: Date[];
  events: CalendarEvent[];
  on_event: (event: CalendarEvent) => void;
};

function events_for_day(events: CalendarEvent[], day: Date): CalendarEvent[] {
  const day_key = date_input_value(day.toISOString());
  return events.filter((event) => date_input_value(event.start_at) === day_key);
}

function AllDayChip({ event, on_event }: {
  event: CalendarEvent;
  on_event: (event: CalendarEvent) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => on_event(event)}
      aria-label={`${event.title}, all day`}
      style={event_block_style(event.event_type)}
      className="block w-full cursor-pointer truncate rounded-full border
        px-2 py-0.5 text-left text-xs font-semibold text-hi
        transition-transform duration-(--tb-dur-fast) ease-spring
        hover:scale-[1.02] hover:shadow-glow-soft"
    >
      {event.title}
    </button>
  );
}

function AllDayDayCell({ day, events, on_event }: {
  day: Date;
  events: CalendarEvent[];
  on_event: (event: CalendarEvent) => void;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-1 border-l border-edge px-1 py-1">
      {events_for_day(events, day).map((event) => (
        <AllDayChip key={event.id} event={event} on_event={on_event} />
      ))}
    </div>
  );
}

/** All-day lane, rendered directly above the hour grid, aligned to the same 7 day columns. */
export function AllDayStrip({ days, events, on_event }: AllDayStripProps) {
  if (events.length === 0) return null;
  return (
    <div
      className="grid border-b border-edge bg-surface-1"
      style={{ gridTemplateColumns: "var(--tb-gutter-width) repeat(7, minmax(0, 1fr))" }}
    >
      <div
        aria-hidden="true"
        className="py-1 pr-2 text-right font-mono text-[0.6rem] uppercase text-low"
      >
        All day
      </div>
      {days.map((day) => (
        <AllDayDayCell key={day.toISOString()} day={day} events={events} on_event={on_event} />
      ))}
    </div>
  );
}
