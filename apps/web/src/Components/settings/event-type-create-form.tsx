import { useState } from "react";
import type { CalendarColor, EventTypeCreate } from "../../lib/api-schemas";
import { event_type_create_schema } from "../../lib/api-schemas";
import { calendar_color_options } from "../../lib/dispatch-maps/labels";
import { Button } from "../ui/button";
import { ColorSwatchPicker } from "../ui/color-swatch-picker";
import { TextField } from "../ui/field";

type EventTypeCreateFormProps = {
  busy: boolean;
  on_submit: (payload: EventTypeCreate) => void;
};

/** Label + color-swatch picker for adding a custom event type. */
export function EventTypeCreateForm({ busy, on_submit }: EventTypeCreateFormProps) {
  const [label, set_label] = useState("");
  const [color, set_color] = useState<CalendarColor>(calendar_color_options[0]);
  const [error, set_error] = useState<string | null>(null);

  const handle_submit = () => {
    const parsed = event_type_create_schema.safeParse({ label: label.trim(), color });
    if (!parsed.success) {
      set_error(parsed.error.issues[0]?.message ?? "Check the label.");
      return;
    }
    set_error(null);
    on_submit(parsed.data);
    set_label("");
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-edge bg-surface-1 p-4">
      <h4 className="font-display text-sm font-bold text-hi">Add a type</h4>
      <TextField
        label="Label"
        value={label}
        placeholder="e.g. Errand"
        onChange={(event) => set_label(event.target.value)}
      />
      <ColorSwatchPicker value={color} on_change={set_color} />
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
      <Button variant="primary" disabled={busy} onClick={handle_submit}>
        {busy ? "Adding…" : "Add type"}
      </Button>
    </div>
  );
}
