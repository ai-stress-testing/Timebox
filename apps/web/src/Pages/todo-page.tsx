import { useEffect, useState } from "react";
import type { EventTypeCreate, EventTypeSummary } from "../lib/api-schemas";
import { BatchScheduleModal } from "../Components/todos/batch-schedule-modal";
import { TodoForm } from "../Components/todos/todo-form";
import { TodoList } from "../Components/todos/todo-list";
import { use_create_event_type, use_event_types } from "../Hooks/use-event-types";
import {
  use_create_todo,
  use_delete_todo,
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
  const types = use_event_types();
  const create_type = use_create_event_type();

  const [selected_ids, set_selected_ids] = useState<Set<string>>(new Set());
  const [batch_modal_open, set_batch_modal_open] = useState(false);

  const busy = create.isPending || update.isPending || remove.isPending;

  const handle_toggle_select = (id: string) => {
    set_selected_ids((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handle_close_batch_modal = () => {
    set_batch_modal_open(false);
    set_selected_ids(new Set());
  };

  // Ctrl+Shift+S opens the batch scheduler against the current selection
  // (spec 015), scoped to this page via a plain keydown listener.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "s") {
        if (selected_ids.size === 0) return;
        event.preventDefault();
        set_batch_modal_open(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selected_ids]);

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
        on_mark_done={handle_mark_done}
        on_delete={handle_delete}
        busy={busy}
        selected_ids={selected_ids}
        on_toggle_select={handle_toggle_select}
        on_open_batch_schedule={() => set_batch_modal_open(true)}
      />
      <TodoForm on_submit={handle_create} busy={create.isPending} />
      {batch_modal_open ? (
        <BatchScheduleModal
          todos={(todos.data ?? []).filter((todo) => selected_ids.has(todo.id))}
          event_types={active_types(types.data)}
          on_create_type={handle_create_type}
          on_close={handle_close_batch_modal}
        />
      ) : null}
    </section>
  );
}
