import { useState } from "react";
import type {
  EventTypeCreate,
  EventTypeSummary,
  Routine,
  RoutinePatch,
  RoutineRun,
  RoutineScheduleRequest,
} from "../../lib/api-schemas";
import {
  use_delete_routine,
  use_routine_runs,
  use_schedule_routine,
  use_start_run,
  use_update_routine,
} from "../../Hooks/use-routines";
import { color_dot_style, calendar_color_var } from "../../lib/dispatch-maps/event-colors";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { ColorSwatchPicker } from "../ui/color-swatch-picker";
import { TextAreaField, TextField } from "../ui/field";
import { ScheduleRoutineForm } from "./schedule-routine-form";
import { StepBuilder } from "./step-builder";

type CardMode = "none" | "build" | "edit" | "schedule";

const run_status_labels: Record<RoutineRun["status"], string> = {
  pending: "Scheduled, not started",
  in_progress: "In progress",
  completed: "Completed",
  abandoned: "Abandoned",
};

function EditRoutineForm({ routine, on_cancel, on_saved }: {
  routine: Routine;
  on_cancel: () => void;
  on_saved: () => void;
}) {
  const update = use_update_routine();
  const [name, set_name] = useState(routine.name);
  const [description, set_description] = useState(routine.description ?? "");
  const [color, set_color] = useState(routine.color);
  const [error, set_error] = useState<string | null>(null);

  const handle_save = () => {
    const trimmed = name.trim();
    if (trimmed.length === 0) {
      set_error("Name is required.");
      return;
    }
    set_error(null);
    const patch: RoutinePatch = {
      name: trimmed,
      description: description.trim(),
      color,
    };
    update.mutate(
      { id: routine.id, patch },
      {
        onSuccess: () => {
          push_toast("Routine updated.", "ok");
          on_saved();
        },
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-edge bg-surface-1 p-4">
      <TextField label="Name" value={name} onChange={(event) => set_name(event.target.value)} />
      <TextAreaField
        label="Description (optional)"
        value={description}
        onChange={(event) => set_description(event.target.value)}
      />
      <ColorSwatchPicker value={color} on_change={set_color} />
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
      <div className="flex justify-end gap-2">
        <Button variant="subtle" disabled={update.isPending} onClick={on_cancel}>
          Cancel
        </Button>
        <Button variant="primary" disabled={update.isPending} onClick={handle_save}>
          {update.isPending ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}

type RoutineCardProps = {
  routine: Routine;
  event_types: EventTypeSummary[];
  on_create_type: (payload: EventTypeCreate) => Promise<EventTypeSummary | null>;
  on_run_started: (run: RoutineRun) => void;
};

function RoutineCard({ routine, event_types, on_create_type, on_run_started }: RoutineCardProps) {
  const [mode, set_mode] = useState<CardMode>("none");
  const remove = use_delete_routine();
  const start_run = use_start_run(routine.id);
  const schedule = use_schedule_routine(routine.id);
  const runs = use_routine_runs(routine.id);
  const last_run = runs.data?.[0];

  const busy = remove.isPending || start_run.isPending || schedule.isPending;
  const toggle = (next: CardMode) => set_mode((current) => (current === next ? "none" : next));

  const handle_run = () => {
    start_run.mutate(undefined, {
      onSuccess: (run) => on_run_started(run),
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_schedule = (payload: RoutineScheduleRequest) => {
    schedule.mutate(payload, {
      onSuccess: () => {
        push_toast("Scheduled onto the calendar.", "ok");
        set_mode("none");
      },
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_delete = () => {
    remove.mutate(routine.id, {
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  return (
    <li
      className="flex flex-col gap-3 rounded-lg border border-edge bg-surface-2 p-4
        transition-all duration-(--tb-dur-fast) hover:border-edge-strong"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="size-3 shrink-0 rounded-full"
              style={color_dot_style(calendar_color_var[routine.color])}
            />
            <p className="truncate font-display font-bold text-hi">{routine.name}</p>
          </div>
          {routine.description ? (
            <p className="mt-1 line-clamp-2 text-xs text-mid">{routine.description}</p>
          ) : null}
        </div>
        <Button
          variant="danger"
          disabled={busy}
          aria-label={`Delete routine ${routine.name}`}
          onClick={handle_delete}
        >
          ✕
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Badge>
          {routine.step_count} step{routine.step_count === 1 ? "" : "s"}
        </Badge>
        <Badge>
          {routine.estimated_minutes != null ? `${routine.estimated_minutes} min` : "no estimate"}
        </Badge>
        {last_run ? (
          <Badge title={last_run.started_at}>Last run: {run_status_labels[last_run.status]}</Badge>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" disabled={busy} onClick={() => toggle("build")}>
          {mode === "build" ? "Close" : "Build"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={() => toggle("edit")}>
          {mode === "edit" ? "Close" : "Edit"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={() => toggle("schedule")}>
          {mode === "schedule" ? "Close" : "Schedule"}
        </Button>
        <Button variant="primary" disabled={busy || routine.step_count === 0} onClick={handle_run}>
          {start_run.isPending ? "Starting…" : "Run"}
        </Button>
      </div>

      {mode === "build" ? <StepBuilder routine_id={routine.id} /> : null}
      {mode === "edit" ? (
        <EditRoutineForm
          routine={routine}
          on_cancel={() => set_mode("none")}
          on_saved={() => set_mode("none")}
        />
      ) : null}
      {mode === "schedule" ? (
        <ScheduleRoutineForm
          routine={routine}
          event_types={event_types}
          on_create_type={on_create_type}
          busy={schedule.isPending}
          on_cancel={() => set_mode("none")}
          on_submit={handle_schedule}
        />
      ) : null}
    </li>
  );
}

type RoutineListProps = {
  routines: Routine[];
  event_types: EventTypeSummary[];
  on_create_type: (payload: EventTypeCreate) => Promise<EventTypeSummary | null>;
  on_run_started: (run: RoutineRun) => void;
};

/** Card grid — one card per routine, edit/delete/Run/Schedule directly on
 * the card (spec 013: no required navigation to a detail page for those
 * four actions). "Build" is an additional expand mode for the step editor. */
export function RoutineList({ routines, event_types, on_create_type, on_run_started }: RoutineListProps) {
  if (routines.length === 0) {
    return (
      <p className="rounded-md border border-edge bg-surface-1 p-6 text-center text-sm text-mid">
        No routines yet — add one, then build its steps and run it.
      </p>
    );
  }
  return (
    <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {routines.map((routine) => (
        <RoutineCard
          key={routine.id}
          routine={routine}
          event_types={event_types}
          on_create_type={on_create_type}
          on_run_started={on_run_started}
        />
      ))}
    </ul>
  );
}
