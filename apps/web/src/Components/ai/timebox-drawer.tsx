import { useState } from "react";
import { use_timebox_proposal } from "../../Hooks/use-ai";
import { use_create_event } from "../../Hooks/use-events";
import { event_create_schema, timebox_request_schema } from "../../lib/api-schemas";
import type { TimeboxResponse } from "../../lib/api-schemas";
import { add_days, format_day_and_time, iso_to_local_input, local_input_to_iso, next_full_hour } from "../../lib/time";
import { is_service_unavailable, to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { use_ui_store } from "../../Store/ui-store";
import { Button } from "../ui/button";
import { Drawer } from "../ui/drawer";
import { TextAreaField, TextField } from "../ui/field";

const default_window_days = 3;

function ProposalCard({ result, on_accept, busy }: {
  result: TimeboxResponse;
  on_accept: () => void;
  busy: boolean;
}) {
  return (
    <div className="animate-pop-in flex flex-col gap-3 rounded-lg border border-accent/40 bg-surface-2 p-4 shadow-glow-soft">
      <p className="font-display font-bold text-hi">
        {format_day_and_time(result.proposal.start_at)} →{" "}
        {format_day_and_time(result.proposal.end_at)}
      </p>
      <p className="text-sm text-mid">{result.proposal.rationale}</p>
      <Button variant="primary" disabled={busy} onClick={on_accept}>
        {busy ? "Adding…" : "Add to calendar"}
      </Button>
    </div>
  );
}

export function TimeboxDrawer() {
  const close = use_ui_store((state) => state.close_ai_drawer);
  const propose = use_timebox_proposal();
  const create = use_create_event();
  const now = next_full_hour(new Date());
  const [title, set_title] = useState("");
  const [minutes, set_minutes] = useState("60");
  const [window_start, set_window_start] = useState(iso_to_local_input(now.toISOString()));
  const [window_end, set_window_end] = useState(
    iso_to_local_input(add_days(now, default_window_days).toISOString()),
  );
  const [notes, set_notes] = useState("");
  const [error, set_error] = useState<string | null>(null);

  const handle_propose = async () => {
    set_error(null);
    const candidate = {
      task_title: title.trim(),
      estimated_minutes: Number(minutes),
      window_start: local_input_to_iso(window_start),
      window_end: local_input_to_iso(window_end),
      ...(notes.trim() === "" ? {} : { notes: notes.trim() }),
    };
    const parsed = timebox_request_schema.safeParse(candidate);
    if (!parsed.success) {
      set_error("Fill in a title, minutes > 0, and a valid window.");
      return;
    }
    try {
      await propose.mutateAsync(parsed.data);
    } catch (cause) {
      const message = is_service_unavailable(cause)
        ? "The AI provider isn't reachable — check it's running and the URL in Settings, then try again. Your calendar still works without it."
        : to_error_message(cause);
      set_error(message);
    }
  };

  const handle_accept = async () => {
    if (!propose.data) return;
    const candidate = {
      title: title.trim(),
      event_type: "task" as const,
      start_at: propose.data.proposal.start_at,
      end_at: propose.data.proposal.end_at,
      ...(minutes.trim() === "" ? {} : { estimated_minutes: Number(minutes) }),
    };
    const parsed = event_create_schema.safeParse(candidate);
    if (!parsed.success) {
      push_toast("Check the title and minutes before adding.", "danger");
      return;
    }
    try {
      await create.mutateAsync(parsed.data);
      push_toast("Timeboxed onto your calendar.", "ok");
      close();
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
    }
  };

  return (
    <Drawer title="✦ AI timebox" on_close={close}>
      <div className="flex flex-col gap-4">
        <TextField label="Task" value={title} placeholder="What needs a slot?"
          onChange={(event) => set_title(event.target.value)} />
        <TextField label="Estimated minutes" type="number" min={1} value={minutes}
          onChange={(event) => set_minutes(event.target.value)} />
        <div className="grid grid-cols-2 gap-3">
          <TextField label="Window from" type="datetime-local" value={window_start}
            onChange={(event) => set_window_start(event.target.value)} />
          <TextField label="Window to" type="datetime-local" value={window_end}
            onChange={(event) => set_window_end(event.target.value)} />
        </div>
        <TextAreaField label="Notes (optional)" value={notes}
          onChange={(event) => set_notes(event.target.value)} />
        <Button variant="primary" disabled={propose.isPending} onClick={() => void handle_propose()}>
          {propose.isPending ? "Asking the model…" : "Propose a slot"}
        </Button>
        {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
        {propose.data ? (
          <ProposalCard result={propose.data} on_accept={() => void handle_accept()} busy={create.isPending} />
        ) : null}
      </div>
    </Drawer>
  );
}
