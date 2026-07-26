import { useState } from "react";
import type { RoutineStep } from "../../lib/api-schemas";
import {
  use_add_step,
  use_delete_step,
  use_reorder_steps,
  use_routine_steps,
  use_update_step,
} from "../../Hooks/use-routines";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Button } from "../ui/button";
import { CheckboxField, TextField } from "../ui/field";

type StepRowProps = {
  step: RoutineStep;
  is_first: boolean;
  is_last: boolean;
  busy: boolean;
  on_move_up: () => void;
  on_move_down: () => void;
  on_toggle_optional: (value: boolean) => void;
  on_delete: () => void;
};

function StepRow({
  step,
  is_first,
  is_last,
  busy,
  on_move_up,
  on_move_down,
  on_toggle_optional,
  on_delete,
}: StepRowProps) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-md border border-edge
      bg-surface-1 px-3 py-2">
      <div className="flex min-w-0 items-center gap-2">
        <div className="flex flex-col">
          <button
            type="button"
            disabled={busy || is_first}
            aria-label={`Move ${step.name} up`}
            onClick={on_move_up}
            className="cursor-pointer text-mid hover:text-hi disabled:pointer-events-none
              disabled:opacity-30"
          >
            ▲
          </button>
          <button
            type="button"
            disabled={busy || is_last}
            aria-label={`Move ${step.name} down`}
            onClick={on_move_down}
            className="cursor-pointer text-mid hover:text-hi disabled:pointer-events-none
              disabled:opacity-30"
          >
            ▼
          </button>
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-hi">{step.name}</p>
          <p className="text-xs text-mid">{step.estimated_minutes} min</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <CheckboxField
          label="Optional"
          checked={step.is_optional}
          disabled={busy}
          onChange={(event) => on_toggle_optional(event.target.checked)}
        />
        <Button
          variant="danger"
          disabled={busy}
          aria-label={`Delete step ${step.name}`}
          onClick={on_delete}
        >
          ✕
        </Button>
      </div>
    </li>
  );
}

function AddStepForm({ on_submit, busy }: {
  on_submit: (name: string, minutes: number) => void;
  busy: boolean;
}) {
  const [name, set_name] = useState("");
  const [minutes, set_minutes] = useState("5");
  const [error, set_error] = useState<string | null>(null);

  const handle_submit = () => {
    const trimmed = name.trim();
    const parsed_minutes = Number.parseInt(minutes, 10);
    if (trimmed.length === 0) {
      set_error("Step name is required.");
      return;
    }
    if (!Number.isFinite(parsed_minutes) || parsed_minutes <= 0) {
      set_error("Minutes must be a positive number.");
      return;
    }
    set_error(null);
    on_submit(trimmed, parsed_minutes);
    set_name("");
    set_minutes("5");
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <TextField
            label="New step"
            value={name}
            placeholder="e.g. Stretch"
            onChange={(event) => set_name(event.target.value)}
          />
        </div>
        <div className="w-24">
          <TextField
            label="Minutes"
            type="number"
            min={1}
            value={minutes}
            onChange={(event) => set_minutes(event.target.value)}
          />
        </div>
        <Button variant="primary" disabled={busy} onClick={handle_submit}>
          Add
        </Button>
      </div>
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
    </div>
  );
}

/** Step editor for one routine: add/remove/reorder (up-down arrows — a
 * simpler-but-correct alternative to drag-and-drop, per spec 013's
 * non-goals) and per-step optional toggle. Reordering always posts the full
 * ordered id list, matching the reorder endpoint's contract. */
export function StepBuilder({ routine_id }: { routine_id: string }) {
  const steps_query = use_routine_steps(routine_id);
  const add = use_add_step(routine_id);
  const update = use_update_step(routine_id);
  const remove = use_delete_step(routine_id);
  const reorder = use_reorder_steps(routine_id);

  const busy = add.isPending || update.isPending || remove.isPending || reorder.isPending;
  const steps = [...(steps_query.data ?? [])].sort((a, b) => a.position - b.position);

  const swap = (index_a: number, index_b: number) => {
    const ids = steps.map((step) => step.id);
    const tmp = ids[index_a];
    if (tmp === undefined || ids[index_b] === undefined) return;
    ids[index_a] = ids[index_b] as string;
    ids[index_b] = tmp;
    reorder.mutate(ids, {
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-edge bg-surface-1 p-4">
      <p className="text-xs font-medium tracking-wide text-mid uppercase">Steps</p>
      {steps_query.isError ? (
        <p role="alert" className="text-xs text-danger">
          {to_error_message(steps_query.error)}
        </p>
      ) : null}
      {steps.length === 0 ? (
        <p className="text-sm text-mid">No steps yet — add the first one below.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {steps.map((step, index) => (
            <StepRow
              key={step.id}
              step={step}
              is_first={index === 0}
              is_last={index === steps.length - 1}
              busy={busy}
              on_move_up={() => swap(index, index - 1)}
              on_move_down={() => swap(index, index + 1)}
              on_toggle_optional={(value) =>
                update.mutate(
                  { step_id: step.id, patch: { is_optional: value } },
                  { onError: (cause) => push_toast(to_error_message(cause), "danger") },
                )
              }
              on_delete={() =>
                remove.mutate(step.id, {
                  onError: (cause) => push_toast(to_error_message(cause), "danger"),
                })
              }
            />
          ))}
        </ul>
      )}
      <AddStepForm
        busy={busy}
        on_submit={(name, minutes) =>
          add.mutate(
            { name, estimated_minutes: minutes, is_optional: false },
            { onError: (cause) => push_toast(to_error_message(cause), "danger") },
          )
        }
      />
    </div>
  );
}
