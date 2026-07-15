import type { CalendarEvent } from "../../lib/api-schemas";
import {
  day_start_hour,
  format_day_label,
  format_hour_label,
  is_same_day,
  slot_start,
  visible_hours,
} from "../../lib/time";
import type { WeekRange } from "../../lib/time";
import { EventBlock } from "./event-block";

type WeekGridProps = {
  range: WeekRange;
  events: CalendarEvent[];
  on_slot: (start: Date) => void;
  on_event: (event: CalendarEvent) => void;
};

const hour_rows = Array.from({ length: visible_hours }, (_, i) => day_start_hour + i);

function HourGutter() {
  return (
    <div aria-hidden="true">
      <div className="h-8" />
      {hour_rows.map((hour) => (
        <div key={hour} className="h-(--tb-hour-height) pr-2 text-right font-mono text-xs text-low">
          {format_hour_label(hour)}
        </div>
      ))}
    </div>
  );
}

function DayColumn({ day, events, on_slot, on_event }: {
  day: Date;
  events: CalendarEvent[];
  on_slot: (start: Date) => void;
  on_event: (event: CalendarEvent) => void;
}) {
  const today = is_same_day(day, new Date());
  return (
    <div className="min-w-0 border-l border-edge">
      <div
        className={`flex h-8 items-center justify-center text-xs font-semibold
          ${today ? "text-accent-2" : "text-mid"}`}
      >
        {format_day_label(day)}
      </div>
      <div className="relative" style={{ height: `calc(var(--tb-hour-height) * ${visible_hours})` }}>
        {hour_rows.map((hour) => (
          <button
            key={hour}
            type="button"
            aria-label={`New event on ${format_day_label(day)} at ${format_hour_label(hour)}`}
            onClick={() => on_slot(slot_start(day, hour))}
            className="block h-(--tb-hour-height) w-full cursor-pointer border-t
              border-edge/50 transition-colors duration-(--tb-dur-fast)
              hover:bg-surface-2"
          />
        ))}
        {events.map((event) => (
          <EventBlock key={event.id} event={event} day={day} on_select={on_event} />
        ))}
      </div>
    </div>
  );
}

export function WeekGrid({ range, events, on_slot, on_event }: WeekGridProps) {
  return (
    <div
      className="grid overflow-x-auto rounded-lg border border-edge bg-surface-1"
      style={{ gridTemplateColumns: "var(--tb-gutter-width) repeat(7, minmax(0, 1fr))" }}
    >
      <HourGutter />
      {range.days.map((day) => (
        <DayColumn key={day.toISOString()} day={day} events={events} on_slot={on_slot} on_event={on_event} />
      ))}
    </div>
  );
}
