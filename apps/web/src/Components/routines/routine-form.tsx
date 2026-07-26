import { useState } from "react";
import type { CalendarColor, RoutineCreate } from "../../lib/api-schemas";
import { routine_create_schema } from "../../lib/api-schemas";
import { calendar_color_options } from "../../lib/dispatch-maps/labels";
import { Button } from "../ui/button";
import { ColorSwatchPicker } from "../ui/color-swatch-picker";
import { TextAreaField, TextField } from "../ui/field";

export type RoutineDraft = {
  name: string;
  description: string;
  color: CalendarColor;
};

const default_draft = (): RoutineDraft => ({
  name: "",
  description: "",
  color: calendar_color_options[0],
});

function build_routine(draft: RoutineDraft): RoutineCreate | null {
  const candidate = {
    name: draft.name.trim(),
    ...(draft.description.trim() === "" ? {} : { description: draft.description.trim() }),
    color: draft.color,
  };
  const parsed = routine_create_schema.safeParse(candidate);
  return parsed.success ? parsed.data : null;
}

/** New-routine form (name/description/color). Editing an existing routine
 * reuses this same field set inline on its card — see RoutineCard. */
export function RoutineForm({ on_submit, busy }: {
  on_submit: (routine: RoutineCreate) => void;
  busy: boolean;
}) {
  const [draft, set_draft] = useState<RoutineDraft>(default_draft);
  const [error, set_error] = useState<string | null>(null);
  const patch = (value: Partial<RoutineDraft>) =>
    set_draft((current) => ({ ...current, ...value }));

  const handle_submit = () => {
    const routine = build_routine(draft);
    if (routine === null) {
      set_error("Name is required.");
      return;
    }
    set_error(null);
    on_submit(routine);
    set_draft(default_draft());
  };

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-edge bg-surface-1 p-5">
      <h3 className="font-display font-bold text-hi">New routine</h3>
      <TextField
        label="Name"
        value={draft.name}
        placeholder="Morning routine"
        onChange={(event) => patch({ name: event.target.value })}
      />
      <TextAreaField
        label="Description (optional)"
        value={draft.description}
        placeholder="What this routine is for"
        onChange={(event) => patch({ description: event.target.value })}
      />
      <ColorSwatchPicker value={draft.color} on_change={(color) => patch({ color })} />
      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
      <Button variant="primary" disabled={busy} onClick={handle_submit}>
        {busy ? "Adding…" : "Add routine"}
      </Button>
    </div>
  );
}
