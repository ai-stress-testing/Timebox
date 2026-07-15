import { useState } from "react";
import { use_apply_run, use_create_run } from "../../Hooks/use-schedule";
import type { Occurrence, ScheduleRunDetail } from "../../lib/api-schemas";
import { format_day_and_time } from "../../lib/time";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Button } from "../ui/button";
import { TextField } from "../ui/field";

function ConfidenceBar({ value }: { value: number }) {
  return (
    <span
      role="img"
      aria-label={`Confidence ${Math.round(value * 100)}%`}
      className="block h-1.5 w-24 overflow-hidden rounded-full bg-surface-3"
    >
      <span
        className="block h-full rounded-full [background:var(--tb-gradient-accent)]"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </span>
  );
}

function OccurrenceRow({ occurrence }: { occurrence: Occurrence }) {
  return (
    <li className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
      <div className="min-w-0">
        <span className="block truncate font-medium text-hi">{occurrence.chore_name}</span>
        <span className="block text-xs text-mid">
          {format_day_and_time(occurrence.proposed_start_at)}
        </span>
      </div>
      <ConfidenceBar value={occurrence.confidence_score} />
    </li>
  );
}

function RunSummary({ run }: { run: ScheduleRunDetail }) {
  return (
    <p className="text-xs text-mid">
      {run.chores_scheduled ?? 0} occurrences · seed{" "}
      <span className="font-mono text-accent-2">{run.seed}</span> · load variance{" "}
      {run.load_variance ?? 0}
    </p>
  );
}

export function PlanPanel() {
  const [window_days, set_window_days] = useState("14");
  const [seed, set_seed] = useState("");
  const [run, set_run] = useState<ScheduleRunDetail | null>(null);
  const create_run = use_create_run();
  const apply_run = use_apply_run();

  const handle_plan = async () => {
    try {
      const detail = await create_run.mutateAsync({
        window_days: Number(window_days) || 14,
        ...(seed.trim() === "" ? {} : { seed: Number(seed) }),
      });
      set_run(detail);
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
    }
  };

  const handle_apply = async () => {
    if (run === null) return;
    try {
      const result = await apply_run.mutateAsync(run.id);
      push_toast(`${result.events_created} chore events added to your calendar.`, "ok");
      set_run(null);
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
    }
  };

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-edge bg-surface-1 p-5">
      <h3 className="font-display font-bold text-hi">Plan my chores</h3>
      <div className="grid grid-cols-2 gap-3">
        <TextField label="Window (days)" type="number" min={1} max={90} value={window_days}
          onChange={(event) => set_window_days(event.target.value)} />
        <TextField label="Seed (optional)" type="number" value={seed} placeholder="Random"
          onChange={(event) => set_seed(event.target.value)} />
      </div>
      <Button variant="primary" disabled={create_run.isPending} onClick={() => void handle_plan()}>
        {create_run.isPending ? "Sampling schedules…" : "✦ Run Monte Carlo plan"}
      </Button>
      {run ? (
        <div className="flex flex-col gap-2">
          <RunSummary run={run} />
          <ul className="max-h-72 divide-y divide-edge overflow-y-auto rounded-md border border-edge bg-surface-2">
            {run.occurrences.map((occurrence) => (
              <OccurrenceRow key={occurrence.id} occurrence={occurrence} />
            ))}
          </ul>
          <Button disabled={apply_run.isPending} onClick={() => void handle_apply()}>
            {apply_run.isPending ? "Applying…" : "Apply to calendar"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
