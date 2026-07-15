import { useState } from "react";
import type { CalendarEvent, EventCreate, EventPatch } from "../../lib/api-schemas";
import { canvas_badge_labels } from "../../lib/dispatch-maps/canvas-badges";
import {
  use_create_event,
  use_delete_event,
  use_update_event,
} from "../../Hooks/use-events";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Drawer } from "../ui/drawer";
import { build_event_create, draft_from_event, draft_from_slot } from "./event-draft";
import type { EventDraft } from "./event-draft";
import { EventFormFields } from "./event-form";

export type DrawerTarget = { kind: "create"; start: Date } | { kind: "edit"; event: CalendarEvent };

type EventDrawerProps = { target: DrawerTarget; on_close: () => void };

function initial_draft(target: DrawerTarget): EventDraft {
  return target.kind === "create"
    ? draft_from_slot(target.start)
    : draft_from_event(target.event);
}

/** Recurrence editing is out of scope for the patch endpoint (issue #2) —
 * strip those fields so editing an occurrence's other fields doesn't 422. */
function to_patch(payload: EventCreate): EventPatch {
  const { is_recurring: _r, recurrence_weekdays: _w, recurrence_end: _e, ...patch } = payload;
  return patch;
}

export function EventDrawer({ target, on_close }: EventDrawerProps) {
  const [draft, set_draft] = useState<EventDraft>(() => initial_draft(target));
  const [errors, set_errors] = useState<Record<string, string>>({});
  const create = use_create_event();
  const update = use_update_event();
  const remove = use_delete_event();
  const busy = create.isPending || update.isPending || remove.isPending;
  const is_edit = target.kind === "edit";
  const idle_label = is_edit ? "Save changes" : "Create event";
  const save_label = busy ? "Saving…" : idle_label;

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

  const handle_delete = async () => {
    if (!is_edit) return;
    try {
      await remove.mutateAsync(target.event.id);
      push_toast("Event deleted.", "ok");
      on_close();
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
    }
  };

  return (
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
        />
        <div className="flex items-center justify-between gap-3">
          {is_edit ? (
            <Button variant="danger" disabled={busy} onClick={() => void handle_delete()}>
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
  );
}
