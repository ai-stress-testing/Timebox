import { useMemo } from "react";
import type { HalfHourSlot } from "../../lib/time";
import { format_half_hour_label } from "../../lib/time";

export type SlotAssignmentCounts = Map<string, number>;

type TimeGridPanelProps = {
  slots: HalfHourSlot[];
  slot_iso: (slot: HalfHourSlot) => string;
  counts: SlotAssignmentCounts;
  armed: boolean;
  shaking_iso: string | null;
  now_iso: string;
  on_drop_todo_id: (todo_id: string, iso: string) => void;
  on_activate: (iso: string) => void;
};

/** Today-only half-hour grid, vertical scroll only (spec 015). Each cell
 * accepts a native HTML5 drag-drop from the task dish, a click while a task
 * is armed, or Enter/Space while focused and a task is armed. */
export function TimeGridPanel({
  slots,
  slot_iso,
  counts,
  armed,
  shaking_iso,
  now_iso,
  on_drop_todo_id,
  on_activate,
}: TimeGridPanelProps) {
  const rows = useMemo(
    () => slots.map((slot) => ({ slot, iso: slot_iso(slot) })),
    [slots, slot_iso],
  );

  return (
    <div
      className="flex max-h-64 flex-col overflow-x-hidden overflow-y-auto rounded-lg
        border border-edge bg-surface-1"
    >
      {rows.map(({ slot, iso }) => {
        const count = counts.get(iso) ?? 0;
        const is_past = iso <= now_iso;
        const is_shaking = shaking_iso === iso;
        return (
          <button
            key={iso}
            type="button"
            tabIndex={0}
            aria-label={`${format_half_hour_label(slot)}${count > 0 ? `, ${count} assigned` : ""}`}
            data-past={is_past ? "true" : undefined}
            className={`flex shrink-0 items-center justify-between border-b border-edge
              px-3 py-2 text-left text-sm transition-colors duration-(--tb-dur-fast)
              last:border-b-0 ${is_past ? "text-low" : "text-hi hover:bg-surface-2"}
              ${armed && !is_past ? "cursor-pointer" : ""}
              ${is_shaking ? "animate-shake" : ""}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const todo_id = event.dataTransfer.getData("text/plain");
              if (todo_id) on_drop_todo_id(todo_id, iso);
            }}
            onClick={() => on_activate(iso)}
          >
            <span>{format_half_hour_label(slot)}</span>
            {count > 0 ? (
              <span
                className="inline-flex min-w-5 items-center justify-center rounded-full
                  bg-accent px-1.5 py-0.5 text-xs font-semibold text-accent-ink"
              >
                {count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
