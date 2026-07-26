import { useEffect, useState } from "react";
import type {
  CalendarEvent,
  EventCreate,
  EventPatch,
  EventTypeCreate,
  EventTypeSummary,
} from "../../lib/api-schemas";
import { canvas_badge_labels } from "../../lib/dispatch-maps/canvas-badges";
import {
  use_create_event,
  use_delete_event,
  use_event_titles,
  use_update_event,
} from "../../Hooks/use-events";
import type { DeleteScope } from "../../Hooks/use-events";
import { use_create_event_type, use_event_types } from "../../Hooks/use-event-types";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Drawer } from "../ui/drawer";
import { DeleteScopeDialog } from "./delete-scope-dialog";
import type { DeleteScopeChoice } from "./delete-scope-dialog";
import { build_event_create, draft_from_event, draft_from_slot } from "./event-draft";
import type { EventDraft } from "./event-draft";
import { EventFormFields } from "./event-form";
import { EventQuickActions } from "./event-quick-actions";

export type DrawerTarget = { kind: "create"; start: Date } | { kind: "edit"; event: CalendarEvent };

type EventDrawerProps = { target: DrawerTarget; on_close: () => void };

function initial_draft(target: DrawerTarget, default_event_type: string): EventDraft {
  return target.kind === "create"
    ? draft_from_slot(target.start, default_event_type)
    : draft_from_event(target.event);
}

/** Only active types are selectable when creating/editing an event. */
function active_types(types: EventTypeSummary[] | undefined): EventTypeSummary[] {
  return (types ?? []).filter((type) => type.is_active);
}

/** Recurrence editing is out of scope for the patch endpoint (issue #2) —
 * strip those fields so editing an occurrence's other fields doesn't 422. */
function to_patch(payload: EventCreate): EventPatch {
  const { is_recurring: _r, recurrence_weekdays: _w, recurrence_end: _e, ...patch } = payload;
  return patch;
}

export function EventDrawer({ target, on_close }: EventDrawerProps) {
  const types = use_event_types();
  const create_type = use_create_event_type();
  const selectable_types = active_types(types.data);
  const [draft, set_draft] = useState<EventDraft>(() =>
    initial_draft(target, selectable_types[0]?.key ?? "task"),
  );
  const [errors, set_errors] = useState<Record<string, string>>({});
  const [show_delete_scope, set_show_delete_scope] = useState(false);

  // Types may resolve after the drawer mounts; on create, reconcile the draft's
  // type to the first active one if the initial default (e.g. a hidden "task")
  // isn't selectable — otherwise submit would 422 on a hidden key.
  useEffect(() => {
    if (target.kind !== "create") return;
    const keys = active_types(types.data).map((type) => type.key);
    const first = keys[0];
    if (first === undefined) return;
    set_draft((current) =>
      keys.includes(current.event_type) ? current : { ...current, event_type: first },
    );
  }, [target.kind, types.data]);
  const create = use_create_event();
  const update = use_update_event();
  const remove = use_delete_event();
  const titles = use_event_titles();
  const busy = create.isPending || update.isPending || remove.isPending;
  const is_edit = target.kind === "edit";
  const idle_label = is_edit ? "Save changes" : "Create event";
  const save_label = busy ? "Saving…" : idle_label;

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

  const handle_save = async () => {
    const built = build_event_create(draft);
    if (!built.ok) {
      set_errors(built.errors);
      return;
    }
    try {
      if (is_edit) {
        await update.mutateAsync({ id: target.event.id, patch: to_patch(built.value) });
      } else {
        await create.mutateAsync(built.value);
      }
      push_toast(is_edit ? "Event updated." : "Event created.", "ok");
      on_close();
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
    }
  };

  const run_delete = async (scope: DeleteScope) => {
    if (!is_edit) return;
    try {
      await remove.mutateAsync({
        id: target.event.id,
        scope,
        occurrence_date: target.event.occurrence_date,
      });
      push_toast("Event deleted.", "ok");
      on_close();
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
    }
  };

  /* Recurring events with a known occurrence date pop the scope choice;
   * everything else (non-recurring, or a recurring row with no occurrence
   * date to anchor on) deletes immediately, scope="all", as before. */
  const handle_delete = () => {
    if (!is_edit) return;
    const is_recurring_occurrence =
      Boolean(target.event.is_recurring) && target.event.occurrence_date != null;
    if (is_recurring_occurrence) {
      set_show_delete_scope(true);
      return;
    }
    void run_delete("all");
  };

  const handle_scope_choice = (choice: DeleteScopeChoice) => {
    set_show_delete_scope(false);
    void run_delete(choice);
  };

  return (
    <>
      <Drawer title={is_edit ? "Edit event" : "New event"} on_close={on_close}>
        <div className="flex flex-col gap-5">
          {is_edit ? (
            <Badge title="Assigned automatically by the server">
              Canvas: {canvas_badge_labels[target.event.canvas_event_type]}
            </Badge>
          ) : null}
          <EventFormFields
            draft={draft}
            errors={errors}
            on_change={(patch) => set_draft((current) => ({ ...current, ...patch }))}
            title_suggestions={titles.data ?? []}
            event_types={selectable_types}
            on_create_type={handle_create_type}
          />
          {is_edit && !target.event.is_recurring ? (
            <EventQuickActions event={target.event} on_done={on_close} />
          ) : null}
          <div className="flex items-center justify-between gap-3">
            {is_edit ? (
              <Button variant="danger" disabled={busy} onClick={handle_delete}>
                Delete
              </Button>
            ) : (
              <span />
            )}
            <Button variant="primary" disabled={busy} onClick={() => void handle_save()}>
              {save_label}
            </Button>
          </div>
        </div>
      </Drawer>
      {show_delete_scope ? (
        <DeleteScopeDialog
          on_choose={handle_scope_choice}
          on_cancel={() => set_show_delete_scope(false)}
          busy={busy}
        />
      ) : null}
    </>
  );
}
