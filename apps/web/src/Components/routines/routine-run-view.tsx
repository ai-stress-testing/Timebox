import { useEffect, useState } from "react";
import type { RoutineRun } from "../../lib/api-schemas";
import { use_abandon_run, use_advance_step } from "../../Hooks/use-routines";
import { format_elapsed } from "../focus/session-timer";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Button } from "../ui/button";

const tick_interval_ms = 1_000;

/** Elapsed seconds since `started_at`, freezable via a shared pause window
 * (`pause_started_ms`/`pause_accum_ms`) — the run view has no server-side
 * "paused" state (spec 013 is silent on pause persistence, and adding a
 * third run/step-run status was out of scope for this slice), so Pause only
 * freezes the on-screen clocks; it does not stop the wall-clock the server
 * uses to compute a step's `actual_minutes` on Done. See plan.md deviations.
 */
function elapsed_seconds(
  started_at: string,
  now_ms: number,
  paused: boolean,
  pause_started_ms: number | null,
  pause_accum_ms: number,
): number {
  const effective_now = paused && pause_started_ms != null ? pause_started_ms : now_ms;
  const elapsed_ms = effective_now - new Date(started_at).getTime() - pause_accum_ms;
  return Math.max(0, Math.floor(elapsed_ms / 1000));
}

function use_pausable_clock() {
  const [now_ms, set_now_ms] = useState(() => Date.now());
  const [paused, set_paused] = useState(false);
  const [pause_started_ms, set_pause_started_ms] = useState<number | null>(null);
  const [pause_accum_ms, set_pause_accum_ms] = useState(0);

  useEffect(() => {
    if (paused) return;
    const timer = setInterval(() => set_now_ms(Date.now()), tick_interval_ms);
    return () => clearInterval(timer);
  }, [paused]);

  const toggle_pause = () => {
    if (paused) {
      set_pause_accum_ms((accum) =>
        pause_started_ms != null ? accum + (Date.now() - pause_started_ms) : accum,
      );
      set_pause_started_ms(null);
      set_paused(false);
      set_now_ms(Date.now());
    } else {
      set_pause_started_ms(Date.now());
      set_paused(true);
    }
  };

  return { now_ms, paused, pause_started_ms, pause_accum_ms, toggle_pause };
}

type RoutineRunViewProps = {
  run: RoutineRun;
  routine_name: string;
  on_run_updated: (run: RoutineRun) => void;
  on_exit: () => void;
};

export function RoutineRunView({ run, routine_name, on_run_updated, on_exit }: RoutineRunViewProps) {
  const advance = use_advance_step();
  const abandon = use_abandon_run();
  const clock = use_pausable_clock();

  const current_step = run.steps.find((step) => step.status === "active");
  const done_count = run.steps.filter((step) => step.status === "done" || step.status === "skipped")
    .length;

  const busy = advance.isPending || abandon.isPending;

  const step_elapsed = current_step?.started_at
    ? elapsed_seconds(
        current_step.started_at,
        clock.now_ms,
        clock.paused,
        clock.pause_started_ms,
        clock.pause_accum_ms,
      )
    : 0;
  const run_elapsed = elapsed_seconds(
    run.started_at,
    clock.now_ms,
    clock.paused,
    clock.pause_started_ms,
    clock.pause_accum_ms,
  );

  const handle_advance = (skipped: boolean) => {
    if (!current_step) return;
    advance.mutate(
      { run_id: run.id, step_run_id: current_step.id, payload: { skipped } },
      {
        onSuccess: (updated) => on_run_updated(updated),
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  const handle_abandon = () => {
    abandon.mutate(run.id, {
      onSuccess: (updated) => {
        push_toast("Run abandoned.", "ok");
        on_run_updated(updated);
      },
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  if (run.status !== "in_progress") {
    const summary_label = run.status === "completed" ? "Routine completed" : "Run abandoned";
    return (
      <section aria-label="Routine run summary" className="flex flex-col items-center gap-4 py-12 text-center">
        <h2 className="font-display text-title font-bold text-hi">{summary_label}</h2>
        <p className="text-sm text-mid">{routine_name}</p>
        <p className="font-display text-display font-black text-hi">
          {run.total_actual_minutes ?? 0} min
        </p>
        <p className="text-xs text-low">
          {done_count} of {run.steps.length} step{run.steps.length === 1 ? "" : "s"} logged
        </p>
        <Button variant="primary" onClick={on_exit}>
          Back to routines
        </Button>
      </section>
    );
  }

  return (
    <section aria-label="Routine run" className="flex flex-col items-center gap-6 py-10 text-center">
      <p className="text-sm text-mid">Running</p>
      <p className="font-display max-w-md truncate text-lg font-bold text-hi">{routine_name}</p>

      <div className="flex flex-col items-center gap-1">
        <p className="text-xs text-low">
          Step {done_count + 1} of {run.steps.length}
        </p>
        <p className="font-display text-lg font-bold text-hi">
          {current_step?.step_name ?? "—"}
        </p>
        <p
          aria-live="off"
          className="font-display text-display tracking-hug font-black
            bg-clip-text text-transparent [background-image:var(--tb-gradient-accent)]"
        >
          {format_elapsed(step_elapsed)}
        </p>
        {current_step ? (
          <p className="text-xs text-low">estimated {current_step.estimated_minutes} min</p>
        ) : null}
      </div>

      <p className="text-xs text-mid">
        whole run: <span className="font-medium text-hi">{format_elapsed(run_elapsed)}</span>
      </p>

      <div className="flex flex-wrap justify-center gap-2">
        <Button variant="primary" disabled={busy || !current_step} onClick={() => handle_advance(false)}>
          {advance.isPending ? "Saving…" : "Done"}
        </Button>
        {current_step?.is_optional ? (
          <Button variant="ghost" disabled={busy} onClick={() => handle_advance(true)}>
            Skip
          </Button>
        ) : null}
        <Button variant="ghost" disabled={busy} onClick={clock.toggle_pause}>
          {clock.paused ? "Resume" : "Pause"}
        </Button>
        <Button variant="danger" disabled={busy} onClick={handle_abandon}>
          Abandon
        </Button>
      </div>
    </section>
  );
}
