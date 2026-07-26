import { useState } from "react";
import { canvas_item_create_schema } from "../../lib/api-schemas";
import type { CanvasItemCreate, CanvasMode } from "../../lib/api-schemas";
import { Button } from "../ui/button";
import { TextField } from "../ui/field";

/* "New timer" / "New stopwatch" — the two primary creation actions, front
 * and center per specs/010-radial-canvas/spec.md: this is the core flow,
 * not a secondary affordance. */

type CanvasDraft = { title: string; duration_minutes: string };
const empty_draft: CanvasDraft = { title: "", duration_minutes: "25" };
const seconds_per_minute = 60;
// Golden angle spread: each successive default placement lands at a new
// angle far from every prior one, so items created back-to-back (the
// expected "New timer, New stopwatch, New timer…" flow) don't stack
// exactly on top of each other before the user drags them apart.
const golden_angle_deg = 137.5;

function build_item(
  mode: CanvasMode,
  draft: CanvasDraft,
  existing_count: number,
): CanvasItemCreate | null {
  const candidate = {
    title: draft.title.trim(),
    mode,
    theta: (existing_count * golden_angle_deg) % 360,
    ...(mode === "timer"
      ? { duration_seconds: Math.round(Number(draft.duration_minutes) * seconds_per_minute) }
      : {}),
  };
  const parsed = canvas_item_create_schema.safeParse(candidate);
  return parsed.success ? parsed.data : null;
}

export function CanvasCreateBar({ on_create, busy, existing_count }: {
  on_create: (item: CanvasItemCreate) => void;
  busy: boolean;
  existing_count: number;
}) {
  const [draft, set_draft] = useState<CanvasDraft>(empty_draft);
  const [error, set_error] = useState<string | null>(null);

  const submit = (mode: CanvasMode) => {
    const item = build_item(mode, draft, existing_count);
    if (item === null) {
      set_error(
        mode === "timer"
          ? "Give it a title and a duration in whole minutes (> 0)."
          : "Give it a title.",
      );
      return;
    }
    set_error(null);
    on_create(item);
    set_draft(empty_draft);
  };

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-edge bg-surface-1 p-5">
      <h3 className="font-display font-bold text-hi">New timer / stopwatch</h3>
      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-48 flex-1">
          <TextField
            label="Title"
            value={draft.title}
            placeholder="Deep work sprint"
            onChange={(event) =>
              set_draft((current) => ({ ...current, title: event.target.value }))
            }
          />
        </div>
        <div className="w-32">
          <TextField
            label="Minutes (timer)"
            type="number"
            min={1}
            value={draft.duration_minutes}
            onChange={(event) =>
              set_draft((current) => ({ ...current, duration_minutes: event.target.value }))
            }
          />
        </div>
        <Button variant="primary" disabled={busy} onClick={() => submit("timer")}>
          {busy ? "Adding…" : "New timer"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={() => submit("stopwatch")}>
          {busy ? "Adding…" : "New stopwatch"}
        </Button>
      </div>
      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
    </div>
  );
}
