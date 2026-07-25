import type { CalendarEvent } from "../../lib/api-schemas";
import type { EventColorMap } from "../../lib/dispatch-maps/event-colors";
import { event_block_style, resolve_event_color } from "../../lib/dispatch-maps/event-colors";
import { event_day_layout } from "../../lib/time";
import { format_time_range } from "../../lib/time";

type EventBlockProps = {
  event: CalendarEvent;
  day: Date;
  color_map: EventColorMap;
  on_select: (event: CalendarEvent) => void;
};

/** One positioned event inside a day column of the week grid. */
export function EventBlock({ event, day, color_map, on_select }: EventBlockProps) {
  const layout = event_day_layout(event.start_at, event.end_at, day);
  if (layout === null) return null;
  const is_done = event.status === "completed";
  return (
    <button
      type="button"
      onClick={() => on_select(event)}
      aria-label={`${event.title}, ${format_time_range(event.start_at, event.end_at)}`}
      style={{
        top: `${layout.top_pct}%`,
        height: `${layout.height_pct}%`,
        ...event_block_style(resolve_event_color(color_map, event.event_type)),
      }}
      className={`absolute inset-x-0.5 z-10 cursor-pointer overflow-hidden
        rounded-sm border px-1.5 py-0.5 text-left transition-all
        duration-(--tb-dur-fast) ease-spring hover:z-20 hover:scale-[1.02]
        hover:shadow-glow-soft ${is_done ? "opacity-50" : ""}`}
    >
      <span className="block truncate text-xs font-semibold text-hi">
        {event.is_recurring ? (
          <span aria-label="repeats" title="Repeats">↻ </span>
        ) : null}
        {is_done ? <s>{event.title}</s> : event.title}
      </span>
      <span className="block truncate text-xs text-mid">
        {format_time_range(event.start_at, event.end_at)}
      </span>
    </button>
  );
}
