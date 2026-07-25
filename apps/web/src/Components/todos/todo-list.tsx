import { useState } from "react";
import type {
  EventTypeCreate,
  EventTypeSummary,
  Todo,
  TodoScheduleRequest,
} from "../../lib/api-schemas";
import { Button } from "../ui/button";
import { CheckboxField } from "../ui/field";
import { ScheduleTodoForm } from "./schedule-todo-form";

type TodoListProps = {
  todos: Todo[];
  event_types: EventTypeSummary[];
  on_create_type: (payload: EventTypeCreate) => Promise<EventTypeSummary | null>;
  on_schedule: (id: string, payload: TodoScheduleRequest) => void;
  on_mark_done: (id: string) => void;
  on_delete: (id: string) => void;
  busy: boolean;
};

type TodoRowProps = Omit<TodoListProps, "todos"> & { todo: Todo };

function TodoRow({
  todo,
  event_types,
  on_create_type,
  on_schedule,
  on_mark_done,
  on_delete,
  busy,
}: TodoRowProps) {
  const [scheduling, set_scheduling] = useState(false);

  return (
    <li className="flex flex-col gap-3 rounded-md border border-edge bg-surface-2 px-4 py-3
      transition-all duration-(--tb-dur-fast) hover:border-edge-strong">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-hi">{todo.title}</p>
          {todo.estimated_minutes != null ? (
            <p className="text-xs text-mid">{todo.estimated_minutes} min</p>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <CheckboxField
            label="Done"
            checked={false}
            disabled={busy}
            onChange={() => on_mark_done(todo.id)}
          />
          <Button
            variant="subtle"
            disabled={busy}
            onClick={() => set_scheduling((current) => !current)}
          >
            {scheduling ? "Cancel" : "Schedule"}
          </Button>
          <Button
            variant="danger"
            disabled={busy}
            aria-label={`Delete to-do ${todo.title}`}
            onClick={() => on_delete(todo.id)}
          >
            ✕
          </Button>
        </div>
      </div>
      {scheduling ? (
        <ScheduleTodoForm
          todo={todo}
          event_types={event_types}
          on_create_type={on_create_type}
          busy={busy}
          on_cancel={() => set_scheduling(false)}
          on_submit={(payload) => {
            on_schedule(todo.id, payload);
            set_scheduling(false);
          }}
        />
      ) : null}
    </li>
  );
}

export function TodoList({
  todos,
  event_types,
  on_create_type,
  on_schedule,
  on_mark_done,
  on_delete,
  busy,
}: TodoListProps) {
  if (todos.length === 0) {
    return (
      <p className="rounded-md border border-edge bg-surface-1 p-6 text-center text-sm text-mid">
        No open to-dos — add one, then funnel it onto the calendar when you're ready.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2">
      {todos.map((todo) => (
        <TodoRow
          key={todo.id}
          todo={todo}
          event_types={event_types}
          on_create_type={on_create_type}
          on_schedule={on_schedule}
          on_mark_done={on_mark_done}
          on_delete={on_delete}
          busy={busy}
        />
      ))}
    </ul>
  );
}
