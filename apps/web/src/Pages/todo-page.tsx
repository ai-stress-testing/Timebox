import type { EventTypeCreate, EventTypeSummary, TodoScheduleRequest } from "../lib/api-schemas";
import { TodoForm } from "../Components/todos/todo-form";
import { TodoList } from "../Components/todos/todo-list";
import { use_create_event_type, use_event_types } from "../Hooks/use-event-types";
import {
  use_create_todo,
  use_delete_todo,
  use_schedule_todo,
  use_todos,
  use_update_todo,
} from "../Hooks/use-todos";
import { to_error_message } from "../Services/api-client";
import { push_toast } from "../Store/toast-store";

/** Only active types are selectable when scheduling a to-do onto the calendar. */
function active_types(types: EventTypeSummary[] | undefined): EventTypeSummary[] {
  return (types ?? []).filter((type) => type.is_active);
}

export function TodoPage() {
  const todos = use_todos();
  const create = use_create_todo();
  const update = use_update_todo();
  const remove = use_delete_todo();
  const schedule = use_schedule_todo();
  const types = use_event_types();
  const create_type = use_create_event_type();

  const busy =
    create.isPending || update.isPending || remove.isPending || schedule.isPending;

  const handle_create = (todo: Parameters<typeof create.mutate>[0]) => {
    create.mutate(todo, {
      onSuccess: () => push_toast("To-do added.", "ok"),
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_mark_done = (id: string) => {
    update.mutate(
      { id, patch: { is_done: true } },
      {
        onSuccess: () => push_toast("To-do marked done.", "ok"),
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  const handle_delete = (id: string) => {
    remove.mutate(id, {
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_schedule = (id: string, payload: TodoScheduleRequest) => {
    schedule.mutate(
      { id, payload },
      {
        onSuccess: () => push_toast("Scheduled onto the calendar.", "ok"),
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  const handle_create_type = async (
    payload: EventTypeCreate,
  ): Promise<EventTypeSummary | null> => {
    try {
      const created = await create_type.mutateAsync(payload);
      push_toast(`Type "${created.label}" created.`, "ok");
      return created;
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
      return null;
    }
  };

  return (
    <section aria-label="To do" className="flex flex-col gap-6">
      <h2 className="font-display text-title tracking-hug font-bold text-hi">To do</h2>
      {todos.isError ? (
        <p role="alert" className="text-sm text-danger">{to_error_message(todos.error)}</p>
      ) : null}
      <TodoList
        todos={todos.data ?? []}
        event_types={active_types(types.data)}
        on_create_type={handle_create_type}
        on_schedule={handle_schedule}
        on_mark_done={handle_mark_done}
        on_delete={handle_delete}
        busy={busy}
      />
      <TodoForm on_submit={handle_create} busy={create.isPending} />
    </section>
  );
}
