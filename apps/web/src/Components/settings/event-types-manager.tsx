import {
  use_create_event_type,
  use_delete_event_type,
  use_event_types,
  use_update_event_type,
} from "../../Hooks/use-event-types";
import type { CalendarColor, EventTypeCreate, EventTypeSummary } from "../../lib/api-schemas";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { EventTypeCreateForm } from "./event-type-create-form";
import { EventTypeRow } from "./event-type-row";

function EventTypesList({ types, busy, on_recolor, on_toggle_active, on_delete }: {
  types: EventTypeSummary[];
  busy: boolean;
  on_recolor: (id: string, color: CalendarColor) => void;
  on_toggle_active: (type: EventTypeSummary) => void;
  on_delete: (id: string) => void;
}) {
  if (types.length === 0) return <p className="text-sm text-mid">No event types yet.</p>;
  return (
    <ul className="flex flex-col gap-2">
      {types.map((type) => (
        <EventTypeRow
          key={type.id}
          type={type}
          busy={busy}
          on_recolor={(color) => on_recolor(type.id, color)}
          on_toggle_active={() => on_toggle_active(type)}
          on_delete={() => on_delete(type.id)}
        />
      ))}
    </ul>
  );
}

/** Settings section: list, add, recolor, hide, and delete (custom-only) event types. */
export function EventTypesManager() {
  const types = use_event_types();
  const create = use_create_event_type();
  const update = use_update_event_type();
  const remove = use_delete_event_type();
  const busy = create.isPending || update.isPending || remove.isPending;

  const handle_create = (payload: EventTypeCreate) => {
    create.mutate(payload, {
      onSuccess: (created) => push_toast(`"${created.label}" added.`, "ok"),
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_recolor = (id: string, color: CalendarColor) => {
    update.mutate(
      { id, patch: { color } },
      { onError: (cause) => push_toast(to_error_message(cause), "danger") },
    );
  };

  const handle_toggle_active = (type: EventTypeSummary) => {
    update.mutate(
      { id: type.id, patch: { is_active: !type.is_active } },
      {
        onSuccess: () => push_toast(type.is_active ? "Type hidden." : "Type unhidden.", "ok"),
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  const handle_delete = (id: string) => {
    remove.mutate(id, {
      onSuccess: () => push_toast("Type deleted.", "ok"),
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <h3 className="font-display font-bold text-hi">Event types</h3>
      {types.isLoading ? <p className="text-sm text-mid">Loading types…</p> : null}
      {types.isError ? (
        <p role="alert" className="text-sm text-danger">{to_error_message(types.error)}</p>
      ) : null}
      {types.data ? (
        <EventTypesList
          types={types.data}
          busy={busy}
          on_recolor={handle_recolor}
          on_toggle_active={handle_toggle_active}
          on_delete={handle_delete}
        />
      ) : null}
      <EventTypeCreateForm busy={create.isPending} on_submit={handle_create} />
    </div>
  );
}
