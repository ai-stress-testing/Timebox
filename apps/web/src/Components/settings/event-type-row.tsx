import type { CalendarColor, EventTypeSummary } from "../../lib/api-schemas";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { ColorSwatchPicker } from "../ui/color-swatch-picker";

type EventTypeRowProps = {
  type: EventTypeSummary;
  busy: boolean;
  on_recolor: (color: CalendarColor) => void;
  on_toggle_active: () => void;
  on_delete: () => void;
};

/** One row in the Types manager: swatch picker, label, preset badge, and
 * hide/delete controls (delete only ever shown for custom types). */
export function EventTypeRow({ type, busy, on_recolor, on_toggle_active, on_delete }: EventTypeRowProps) {
  return (
    <li className="flex flex-wrap items-center gap-3 rounded-lg border border-edge bg-surface-1 p-3">
      <span className={`text-sm font-medium ${type.is_active ? "text-hi" : "text-low line-through"}`}>
        {type.label}
      </span>
      {type.is_preset ? <Badge>Preset</Badge> : null}
      <ColorSwatchPicker value={type.color} on_change={on_recolor} />
      <div className="ml-auto flex gap-2">
        <Button variant="subtle" disabled={busy} onClick={on_toggle_active}>
          {type.is_active ? "Hide" : "Unhide"}
        </Button>
        {type.is_preset ? null : (
          <Button variant="danger" disabled={busy} onClick={on_delete}>
            Delete
          </Button>
        )}
      </div>
    </li>
  );
}
