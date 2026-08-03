import { useState } from "react";
import { CanvasCreateBar } from "../Components/canvas/canvas-create-bar";
import { CanvasItemEditCard } from "../Components/canvas/canvas-item-edit-card";
import { RadialCanvas } from "../Components/canvas/radial-canvas";
import { use_canvas_completion_alerts } from "../Hooks/use-canvas-completion-alerts";
import {
  use_canvas_items,
  use_create_canvas_item,
  use_delete_canvas_item,
  use_pause_canvas_item,
  use_reset_canvas_item,
  use_start_canvas_item,
  use_update_canvas_item,
} from "../Hooks/use-canvas";
import type { CanvasItem } from "../lib/api-schemas";
import { to_error_message } from "../Services/api-client";
import { push_toast } from "../Store/toast-store";
import { unlock_audio } from "../lib/timer-notify";

/* Not yet wired into app.tsx's page dispatch / ui-store's PageKey /
 * app-header's nav — see the build report. Fully functional standalone. */
export function CanvasPage() {
  const items = use_canvas_items();
  const create = use_create_canvas_item();
  const update = use_update_canvas_item();
  const start = use_start_canvas_item();
  const pause = use_pause_canvas_item();
  const reset = use_reset_canvas_item();
  const remove = use_delete_canvas_item();

  const [selected_id, set_selected_id] = useState<string | null>(null);
  const selected: CanvasItem | undefined = (items.data ?? []).find((item) => item.id === selected_id);

  use_canvas_completion_alerts(items.data ?? []);

  const busy =
    create.isPending ||
    update.isPending ||
    start.isPending ||
    pause.isPending ||
    reset.isPending ||
    remove.isPending;

  const handle_create: Parameters<typeof CanvasCreateBar>[0]["on_create"] = (item) => {
    create.mutate(item, {
      onSuccess: (created) => {
        // Appended to the canvas, not auto-opened — "New timer" / "New
        // stopwatch" is meant to be fired rapidly in a row (spec 010);
        // the user clicks a marker when they're ready to edit it.
        push_toast(`"${created.title}" added to the canvas.`, "ok");
      },
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_move = (id: string, r: number, theta: number) => {
    update.mutate(
      { id, patch: { r, theta } },
      { onError: (cause) => push_toast(to_error_message(cause), "danger") },
    );
  };

  const handle_save = (patch: { title?: string; duration_seconds?: number }) => {
    if (!selected) return;
    update.mutate(
      { id: selected.id, patch },
      {
        onSuccess: () => push_toast("Saved.", "ok"),
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  const handle_delete = () => {
    if (!selected) return;
    remove.mutate(selected.id, {
      onSuccess: () => {
        push_toast("Deleted.", "ok");
        set_selected_id(null);
      },
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  return (
    <section aria-label="Canvas" className="mx-auto flex max-w-3xl flex-col gap-6">
      <h2 className="font-display text-title tracking-hug font-bold text-hi">Canvas</h2>
      <CanvasCreateBar
        on_create={handle_create}
        busy={create.isPending}
        existing_count={(items.data ?? []).length}
      />
      {items.isError ? (
        <p role="alert" className="text-sm text-danger">{to_error_message(items.error)}</p>
      ) : null}
      {items.data && items.data.length === 0 ? (
        <p className="text-center text-sm text-low">
          No timers yet — start one above and it appears on the canvas immediately.
        </p>
      ) : null}
      <RadialCanvas
        items={items.data ?? []}
        on_select={(item) => set_selected_id(item.id)}
        on_move={handle_move}
      />
      {selected ? (
        <CanvasItemEditCard
          item={selected}
          on_close={() => set_selected_id(null)}
          on_save={handle_save}
          on_start={() => {
            // A real user gesture — unlocks the Web Audio chime ahead of
            // time, since the completion alert itself fires with no fresh
            // gesture behind it and autoplay policies would otherwise block it.
            unlock_audio();
            start.mutate(selected.id, {
              onError: (cause) => push_toast(to_error_message(cause), "danger"),
            });
          }}
          on_pause={() =>
            pause.mutate(selected.id, {
              onError: (cause) => push_toast(to_error_message(cause), "danger"),
            })
          }
          on_reset={() =>
            reset.mutate(selected.id, {
              onError: (cause) => push_toast(to_error_message(cause), "danger"),
            })
          }
          on_delete={handle_delete}
          busy={busy}
        />
      ) : null}
    </section>
  );
}
