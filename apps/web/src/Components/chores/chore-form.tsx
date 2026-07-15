import { useState } from "react";
import { chore_create_schema } from "../../lib/api-schemas";
import type { ChoreCreate } from "../../lib/api-schemas";
import {
  attention_class_labels,
  attention_class_options,
  weekday_options,
} from "../../lib/dispatch-maps/labels";
import { Button } from "../ui/button";
import { SelectField, TextField } from "../ui/field";

type ChoreDraft = {
  name: string;
  estimated_minutes: string;
  priority: string;
  attention_class: ChoreCreate["attention_class"];
  n_days: string;
  preferred_days: number[];
  preferred_time_start: string;
  preferred_time_end: string;
};

const empty_draft: ChoreDraft = {
  name: "",
  estimated_minutes: "30",
  priority: "3",
  attention_class: "active",
  n_days: "3",
  preferred_days: [],
  preferred_time_start: "",
  preferred_time_end: "",
};

function build_chore(draft: ChoreDraft): ChoreCreate | null {
  const candidate = {
    name: draft.name.trim(),
    estimated_minutes: Number(draft.estimated_minutes),
    priority: Number(draft.priority),
    attention_class: draft.attention_class,
    n_days: Number(draft.n_days),
    preferred_days: draft.preferred_days,
    ...(draft.preferred_time_start === "" ? {} : { preferred_time_start: draft.preferred_time_start }),
    ...(draft.preferred_time_end === "" ? {} : { preferred_time_end: draft.preferred_time_end }),
  };
  const parsed = chore_create_schema.safeParse(candidate);
  return parsed.success ? parsed.data : null;
}

function DayToggles({ draft, on_change }: {
  draft: ChoreDraft;
  on_change: (patch: Partial<ChoreDraft>) => void;
}) {
  const toggle = (value: number) => {
    const has_day = draft.preferred_days.includes(value);
    const next = has_day
      ? draft.preferred_days.filter((day) => day !== value)
      : [...draft.preferred_days, value];
    on_change({ preferred_days: next });
  };
  return (
    <fieldset>
      <legend className="mb-1 block text-xs font-medium tracking-wide text-mid uppercase">
        Preferred days
      </legend>
      <div className="flex flex-wrap gap-1">
        {weekday_options.map((option) => {
          const active = draft.preferred_days.includes(option.value);
          const classes = active
            ? "[background:var(--tb-gradient-accent)] text-accent-ink"
            : "border border-edge text-mid hover:text-hi";
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(option.value)}
              className={`cursor-pointer rounded-full px-3 py-1 text-xs
                font-medium transition-all duration-(--tb-dur-fast)
                ease-spring ${classes}`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export function ChoreForm({ on_submit, busy }: {
  on_submit: (chore: ChoreCreate) => void;
  busy: boolean;
}) {
  const [draft, set_draft] = useState<ChoreDraft>(empty_draft);
  const [error, set_error] = useState<string | null>(null);
  const patch = (value: Partial<ChoreDraft>) =>
    set_draft((current) => ({ ...current, ...value }));

  const handle_submit = () => {
    const chore = build_chore(draft);
    if (chore === null) {
      set_error("Check the fields — name, minutes > 0, every-N ≥ 1, times HH:MM.");
      return;
    }
    set_error(null);
    on_submit(chore);
    set_draft(empty_draft);
  };

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-edge bg-surface-1 p-5">
      <h3 className="font-display font-bold text-hi">New chore</h3>
      <TextField label="Name" value={draft.name} placeholder="Vacuum the flat"
        onChange={(event) => patch({ name: event.target.value })} />
      <div className="grid grid-cols-3 gap-3">
        <TextField label="Minutes" type="number" min={1} value={draft.estimated_minutes}
          onChange={(event) => patch({ estimated_minutes: event.target.value })} />
        <TextField label="Every N days" type="number" min={1} value={draft.n_days}
          onChange={(event) => patch({ n_days: event.target.value })} />
        <TextField label="Priority 1–5" type="number" min={1} max={5} value={draft.priority}
          onChange={(event) => patch({ priority: event.target.value })} />
      </div>
      <SelectField label="Attention" value={draft.attention_class}
        onChange={(event) => patch({ attention_class: event.target.value as ChoreDraft["attention_class"] })}>
        {attention_class_options.map((option) => (
          <option key={option} value={option}>{attention_class_labels[option]}</option>
        ))}
      </SelectField>
      <DayToggles draft={draft} on_change={patch} />
      <div className="grid grid-cols-2 gap-3">
        <TextField label="Not before" type="time" value={draft.preferred_time_start}
          onChange={(event) => patch({ preferred_time_start: event.target.value })} />
        <TextField label="Not after" type="time" value={draft.preferred_time_end}
          onChange={(event) => patch({ preferred_time_end: event.target.value })} />
      </div>
      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
      <Button variant="primary" disabled={busy} onClick={handle_submit}>
        {busy ? "Adding…" : "Add chore"}
      </Button>
    </div>
  );
}
