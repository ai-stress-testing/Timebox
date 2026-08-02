import { useState } from "react";
import type { Todo } from "../../lib/api-schemas";
import type { HalfHourSlot } from "../../lib/time";
import { format_half_hour_label, format_time } from "../../lib/time";

const title_char_limit = 10;

function truncate_title(title: string): string {
  return title.length > title_char_limit
    ? `${title.slice(0, title_char_limit)}…`
    : title;
}

type TaskDishProps = {
  todos: Todo[];
  assignments: Map<string, string>;
  armed_id: string | null;
  slots: HalfHourSlot[];
  slot_iso: (slot: HalfHourSlot) => string;
  now_iso: string;
  on_arm: (todo_id: string) => void;
  on_assign: (todo_id: string, iso: string) => void;
};

/** The selected-todos dish, single-select "armed" state, horizontal scroll
 * only. Double-click (or its keyboard equivalent) opens a native <select>
 * of remaining today-slots as the no-drag assignment path (spec 015). */
export function TaskDish({
  todos,
  assignments,
  armed_id,
  slots,
  slot_iso,
  now_iso,
  on_arm,
  on_assign,
}: TaskDishProps) {
  const [dropdown_for, set_dropdown_for] = useState<string | null>(null);

  if (todos.length === 0) {
    return (
      <p className="text-sm text-mid">All selected to-dos are assigned. Review below.</p>
    );
  }

  return (
    <div className="flex max-w-full gap-2 overflow-x-auto overflow-y-hidden pb-1">
      {todos.map((todo) => {
        const assigned_iso = assignments.get(todo.id);
        const is_armed = armed_id === todo.id;
        const is_choosing = dropdown_for === todo.id;
        return (
          <div key={todo.id} className="relative shrink-0">
            <button
              type="button"
              draggable
              tabIndex={0}
              title={todo.title}
              aria-pressed={is_armed}
              onDragStart={(event) => {
                event.dataTransfer.setData("text/plain", todo.id);
                event.dataTransfer.effectAllowed = "move";
              }}
              onClick={() => on_arm(todo.id)}
              onDoubleClick={() => set_dropdown_for(todo.id)}
              className={`flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2
                text-left text-sm transition-all duration-(--tb-dur-fast) ${
                is_armed
                  ? "border-accent bg-accent/10 text-hi shadow-glow-soft"
                  : "border-edge bg-surface-2 text-hi hover:border-edge-strong"
              }`}
            >
              <span className="font-medium">{truncate_title(todo.title)}</span>
              {assigned_iso ? (
                <span className="text-xs text-mid">{format_time(assigned_iso)}</span>
              ) : (
                <span className="text-xs text-low">Unassigned</span>
              )}
            </button>
            {is_choosing ? (
              <div
                className="animate-pop-in absolute top-full left-0 z-10 mt-1 w-40
                  rounded-lg border border-edge bg-surface-1 p-2 shadow-raised"
              >
                <label className="mb-1 block text-xs font-medium tracking-wide text-mid uppercase">
                  Pick a time
                </label>
                <select
                  autoFocus
                  className="w-full rounded-md border border-edge bg-surface-2 px-2 py-1 text-sm text-hi"
                  defaultValue=""
                  onChange={(event) => {
                    const iso = event.target.value;
                    set_dropdown_for(null);
                    if (iso) on_assign(todo.id, iso);
                  }}
                  onBlur={() => set_dropdown_for(null)}
                >
                  <option value="" disabled>
                    Choose…
                  </option>
                  {slots
                    .map((slot) => ({ slot, iso: slot_iso(slot) }))
                    .filter(({ iso }) => iso > now_iso)
                    .map(({ slot, iso }) => (
                      <option key={iso} value={iso}>
                        {format_half_hour_label(slot)}
                      </option>
                    ))}
                </select>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
