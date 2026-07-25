import type { CalendarEvent } from "../../lib/api-schemas";
import type { EventColorMap } from "../../lib/dispatch-maps/event-colors";
import {
  day_start_hour,
  format_day_label,
  format_hour_label,
  is_same_day,
  slot_start,
  visible_hours,
} from "../../lib/time";
import type { WeekRange } from "../../lib/time";
import { AllDayStrip } from "./all-day-strip";
import { EventBlock } from "./event-block";

type WeekGridProps = {
  range: WeekRange;
  events: CalendarEvent[];
  color_map: EventColorMap;
  on_slot: (start: Date) => void;
  on_event: (event: CalendarEvent) => void;
};

const hour_rows = Array.from({ length: visible_hours }, (_, i) => day_start_hour + i);

function HourGutter() {
  return (
    <div aria-hidden="true">
      <div className="sticky top-(--tb-header-height) z-30 h-8 border-b border-edge bg-surface-1" />
      {hour_rows.map((hour) => (
        <div key={hour} className="h-(--tb-hour-height) pr-2 text-right font-mono text-xs text-low">
          {format_hour_label(hour)}
        </div>
      ))}
    </div>
  );
}

function DayColumn({ day, events, color_map, on_slot, on_event }: {
  day: Date;
  events: CalendarEvent[];
  color_map: EventColorMap;
  on_slot: (start: Date) => void;
  on_event: (event: CalendarEvent) => void;
}) {
  const today = is_same_day(day, new Date());
  return (
    <div className="min-w-0 border-l border-edge">
      <div
        className={`sticky top-(--tb-header-height) z-30 flex h-8 items-center
          justify-center border-b border-edge bg-surface-1 text-xs font-semibold
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
          <EventBlock
            key={`${event.id}:${event.start_at}`}
            event={event}
            day={day}
            color_map={color_map}
            on_select={on_event}
          />
        ))}
      </div>
    </div>
  );
}

/** Timed events drive the hour grid; all-day events render only in the strip above it. */
function split_by_all_day(events: CalendarEvent[]): {
  timed: CalendarEvent[];
  all_day: CalendarEvent[];
} {
  const all_day = events.filter((event) => event.is_all_day === true);
  const timed = events.filter((event) => event.is_all_day !== true);
  return { timed, all_day };
}

export function WeekGrid({ range, events, color_map, on_slot, on_event }: WeekGridProps) {
  const { timed, all_day } = split_by_all_day(events);
  return (
    <div className="rounded-lg border border-edge bg-surface-1">
      <AllDayStrip days={range.days} events={all_day} color_map={color_map} on_event={on_event} />
      <div
        className="grid"
        style={{ gridTemplateColumns: "var(--tb-gutter-width) repeat(7, minmax(0, 1fr))" }}
      >
        <HourGutter />
        {range.days.map((day) => (
          <DayColumn
            key={day.toISOString()}
            day={day}
            events={timed}
            color_map={color_map}
            on_slot={on_slot}
            on_event={on_event}
          />
        ))}
      </div>
    </div>
  );
}
