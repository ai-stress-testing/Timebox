import { useState } from "react";
import type {
  CalendarColor,
  EventTypeCreate,
  EventTypeSummary,
} from "../../lib/api-schemas";
import { calendar_color_options } from "../../lib/dispatch-maps/labels";
import { event_type_create_schema } from "../../lib/api-schemas";
import { Button } from "../ui/button";
import { ColorSwatchPicker } from "../ui/color-swatch-picker";
import { SelectField, TextField } from "../ui/field";

const new_type_value = "__new__";

type CreateHandler = (payload: EventTypeCreate) => Promise<EventTypeSummary | null>;

function NewTypeForm({ on_cancel, on_create_type, on_created }: {
  on_cancel: () => void;
  on_create_type: CreateHandler;
  on_created: (key: string) => void;
}) {
  const [label, set_label] = useState("");
  const [color, set_color] = useState<CalendarColor>(calendar_color_options[0]);
  const [error, set_error] = useState<string | null>(null);
  const [busy, set_busy] = useState(false);

  const handle_create = async () => {
    const parsed = event_type_create_schema.safeParse({ label: label.trim(), color });
    if (!parsed.success) {
      set_error(parsed.error.issues[0]?.message ?? "Check the label.");
      return;
    }
    set_busy(true);
    const created = await on_create_type(parsed.data);
    set_busy(false);
    if (created) on_created(created.key);
  };

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-edge p-3">
      <TextField
        label="New type label"
        value={label}
        placeholder="e.g. Errand"
        onChange={(event) => set_label(event.target.value)}
      />
      <ColorSwatchPicker value={color} on_change={set_color} />
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
      <div className="flex justify-end gap-2">
        <Button variant="subtle" disabled={busy} onClick={on_cancel}>Cancel</Button>
        <Button variant="primary" disabled={busy} onClick={() => void handle_create()}>
          {busy ? "Creating…" : "Create"}
        </Button>
      </div>
    </div>
  );
}

type EventTypeFieldProps = {
  value: string;
  event_types: EventTypeSummary[];
  on_change: (key: string) => void;
  on_create_type: CreateHandler;
};

/** Type dropdown driven by the user's active event types, plus a "+ New
 * type…" affordance that opens an inline create-then-select flow. */
export function EventTypeField({ value, event_types, on_change, on_create_type }: EventTypeFieldProps) {
  const [creating, set_creating] = useState(false);
  if (creating) {
    return (
      <div className="block">
        <span className="mb-1 block text-xs font-medium tracking-wide text-mid uppercase">
          Type
        </span>
        <NewTypeForm
          on_cancel={() => set_creating(false)}
          on_create_type={on_create_type}
          on_created={(key) => {
            on_change(key);
            set_creating(false);
          }}
        />
      </div>
    );
  }
  const is_known = event_types.some((type) => type.key === value);
  return (
    <SelectField
      label="Type"
      value={value}
      onChange={(event) => {
        const next = event.target.value;
        if (next === new_type_value) {
          set_creating(true);
          return;
        }
        on_change(next);
      }}
    >
      {is_known || value === "" ? null : (
        <option value={value}>{value} (inactive)</option>
      )}
      {event_types.map((type) => (
        <option key={type.key} value={type.key}>{type.label}</option>
      ))}
      <option value={new_type_value}>＋ New type…</option>
    </SelectField>
  );
}
