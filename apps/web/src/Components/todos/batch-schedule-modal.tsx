import { useMemo, useRef, useState } from "react";
import type { EventTypeCreate, EventTypeSummary, Todo } from "../../lib/api-schemas";
import { batch_schedule_request_schema } from "../../lib/api-schemas";
import { use_batch_schedule } from "../../Hooks/use-todos";
import { compose_local_iso, date_input_value, format_time, half_hour_slots } from "../../lib/time";
import type { HalfHourSlot } from "../../lib/time";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { use_drawer_behavior } from "../../Hooks/use-drawer-behavior";
import { EventTypeField } from "../calendar/event-type-field";
import { Button } from "../ui/button";
import { TaskDish } from "./task-dish";
import { TimeGridPanel } from "./time-grid-panel";

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

type BatchScheduleModalProps = {
  todos: Todo[];
  event_types: EventTypeSummary[];
  on_create_type: (payload: EventTypeCreate) => Promise<EventTypeSummary | null>;
  on_close: () => void;
};

type Step = "assign" | "review";

/** Batch-schedule modal (spec 015): a today-only half-hour grid on top, a
 * horizontally-scrollable dish of the selected to-dos on the bottom.
 * Everything is staged in local state (`assignments`) until "Schedule All"
 * fires one POST /todos/batch-schedule. */
export function BatchScheduleModal({
  todos,
  event_types,
  on_create_type,
  on_close,
}: BatchScheduleModalProps) {
  const [local_todos, set_local_todos] = useState<Todo[]>(todos);
  const [assignments, set_assignments] = useState<Map<string, string>>(new Map());
  const [armed_id, set_armed_id] = useState<string | null>(null);
  const [step, set_step] = useState<Step>("assign");
  const [shaking_iso, set_shaking_iso] = useState<string | null>(null);
  const [show_close_confirm, set_show_close_confirm] = useState(false);
  const [event_type, set_event_type] = useState(event_types[0]?.key ?? "task");
  const shake_timeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const batch_schedule = use_batch_schedule();

  const slots = useMemo(() => half_hour_slots(), []);
  const today_local = useMemo(() => date_input_value(new Date().toISOString()), []);
  const slot_iso = (slot: HalfHourSlot) =>
    compose_local_iso(today_local, `${pad2(slot.hour % 24)}:${pad2(slot.minute)}`);
  const now_iso = new Date().toISOString();

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const iso of assignments.values()) {
      map.set(iso, (map.get(iso) ?? 0) + 1);
    }
    return map;
  }, [assignments]);

  const request_close = () => {
    if (assignments.size === 0) {
      on_close();
      return;
    }
    set_show_close_confirm(true);
  };

  const { panel_ref, handle_keydown } = use_drawer_behavior(request_close);

  const assign_to_slot = (todo_id: string, iso: string) => {
    if (iso <= now_iso) {
      set_shaking_iso(iso);
      if (shake_timeout.current) clearTimeout(shake_timeout.current);
      shake_timeout.current = setTimeout(() => set_shaking_iso(null), 320);
      push_toast("That time has already passed.", "danger");
      return;
    }
    set_assignments((current) => {
      const next = new Map(current);
      const previous = next.get(todo_id);
      next.set(todo_id, iso);
      if (previous && previous !== iso) {
        push_toast(`Moved to ${format_time(iso)}.`, "info");
      }
      return next;
    });
    set_armed_id(null);
  };

  const handle_grid_activate = (iso: string) => {
    if (!armed_id) return;
    assign_to_slot(armed_id, iso);
  };

  const assignment_entries = useMemo(
    () => Array.from(assignments.entries()).sort(([, a], [, b]) => (a < b ? -1 : 1)),
    [assignments],
  );

  const title_for = (todo_id: string): string =>
    local_todos.find((todo) => todo.id === todo_id)?.title ?? todo_id;

  const handle_schedule_all = async () => {
    set_show_close_confirm(false);
    const items = assignment_entries.map(([todo_id, start_at]) => ({
      todo_id,
      start_at,
      event_type,
    }));
    const parsed = batch_schedule_request_schema.safeParse({ items });
    if (!parsed.success) {
      push_toast(parsed.error.issues[0]?.message ?? "Check the assignments.", "danger");
      return;
    }
    try {
      const response = await batch_schedule.mutateAsync(parsed.data);
      const ok_ids = new Set(response.results.filter((r) => r.ok).map((r) => r.todo_id));
      const failures = response.results.filter((r) => !r.ok);
      set_local_todos((current) => current.filter((todo) => !ok_ids.has(todo.id)));
      set_assignments((current) => {
        const next = new Map(current);
        for (const id of ok_ids) next.delete(id);
        for (const failure of failures) next.delete(failure.todo_id);
        return next;
      });
      if (failures.length === 0) {
        push_toast(`${ok_ids.size} task${ok_ids.size === 1 ? "" : "s"} scheduled.`, "ok");
        on_close();
        return;
      }
      const detail = failures.map((f) => f.detail ?? "Failed").join("; ");
      push_toast(
        `${ok_ids.size} scheduled, ${failures.length} failed: ${detail}`,
        "danger",
      );
      set_step("assign");
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onKeyDown={handle_keydown}>
      <div
        className="animate-fade-in absolute inset-0 bg-overlay backdrop-blur-xs"
        onClick={request_close}
        aria-hidden="true"
      />
      <div
        ref={panel_ref}
        role="dialog"
        aria-modal="true"
        aria-label="Batch schedule to-dos"
        tabIndex={-1}
        className="animate-drawer-in relative flex max-h-[90vh] w-full max-w-2xl flex-col
          gap-4 overflow-y-auto rounded-2xl border border-edge bg-surface-1 p-6 shadow-raised"
      >
        <header className="flex items-center justify-between gap-4">
          <h2 className="font-display text-title tracking-hug font-bold text-hi">
            Batch schedule
          </h2>
          <Button variant="subtle" aria-label="Close" onClick={request_close}>
            <span aria-hidden="true">✕</span>
          </Button>
        </header>

        {show_close_confirm ? (
          <div className="flex flex-col gap-3 rounded-lg border border-edge bg-surface-2 p-4">
            <p className="text-sm text-hi">
              Save these {assignments.size} assignment{assignments.size === 1 ? "" : "s"} or discard them?
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => set_show_close_confirm(false)}>
                Keep editing
              </Button>
              <Button variant="danger" onClick={on_close}>
                Discard
              </Button>
              <Button
                variant="primary"
                disabled={batch_schedule.isPending}
                onClick={() => void handle_schedule_all()}
              >
                Save
              </Button>
            </div>
          </div>
        ) : step === "assign" ? (
          <>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-mid">Today only, half-hour slots.</p>
              <div className="w-48">
                <EventTypeField
                  value={event_type}
                  event_types={event_types}
                  on_change={set_event_type}
                  on_create_type={on_create_type}
                />
              </div>
            </div>
            <TimeGridPanel
              slots={slots}
              slot_iso={slot_iso}
              counts={counts}
              armed={armed_id !== null}
              shaking_iso={shaking_iso}
              now_iso={now_iso}
              on_drop_todo_id={assign_to_slot}
              on_activate={handle_grid_activate}
            />
            <TaskDish
              todos={local_todos}
              assignments={assignments}
              armed_id={armed_id}
              slots={slots}
              slot_iso={slot_iso}
              now_iso={now_iso}
              on_arm={(id) => set_armed_id((current) => (current === id ? null : id))}
              on_assign={assign_to_slot}
            />
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={request_close}>
                Cancel
              </Button>
              <Button
                variant="primary"
                disabled={assignments.size === 0}
                onClick={() => set_step("review")}
              >
                Review ({assignments.size})
              </Button>
            </div>
          </>
        ) : (
          <>
            <ul className="flex flex-col gap-1">
              {assignment_entries.map(([todo_id, iso]) => (
                <li
                  key={todo_id}
                  className="flex items-center justify-between rounded-md border
                    border-edge bg-surface-2 px-3 py-2 text-sm text-hi"
                >
                  <span className="truncate">{title_for(todo_id)}</span>
                  <span className="text-mid">{format_time(iso)}</span>
                </li>
              ))}
            </ul>
            <p className="text-sm text-mid">
              {assignment_entries.length} to-do{assignment_entries.length === 1 ? "" : "s"} will be scheduled.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => set_step("assign")}>
                Back
              </Button>
              <Button
                variant="primary"
                disabled={batch_schedule.isPending}
                onClick={() => void handle_schedule_all()}
              >
                {batch_schedule.isPending ? "Scheduling…" : "Schedule All"}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
