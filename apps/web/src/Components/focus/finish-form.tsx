import { useState } from "react";
import { pomodoro_finish_input_schema } from "../../lib/api-schemas";
import type { PomodoroFinishInput } from "../../lib/api-schemas";
import { Button } from "../ui/button";
import { CheckboxField, TextAreaField, TextField } from "../ui/field";

export type { PomodoroFinishInput as FinishInput } from "../../lib/api-schemas";

/** End-of-session form: done flag, meaningful minutes, notes. */
export function FinishForm({ on_finish, busy }: {
  on_finish: (input: PomodoroFinishInput) => void;
  busy: boolean;
}) {
  const [done, set_done] = useState(true);
  const [meaningful, set_meaningful] = useState("");
  const [notes, set_notes] = useState("");
  const [error, set_error] = useState<string | null>(null);

  const handle_finish = () => {
    const meaningful_trimmed = meaningful.trim();
    const candidate = {
      completion_flag: done,
      ...(meaningful_trimmed === "" ? {} : { meaningful_minutes: meaningful_trimmed }),
      ...(notes.trim() === "" ? {} : { notes: notes.trim() }),
    };
    const parsed = pomodoro_finish_input_schema.safeParse(candidate);
    if (!parsed.success) {
      set_error("Meaningful minutes must be a whole number ≥ 0.");
      return;
    }
    set_error(null);
    on_finish(parsed.data);
  };

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-edge bg-surface-1 p-5">
      <CheckboxField
        label="Task is finished"
        checked={done}
        onChange={(event) => set_done(event.target.checked)}
      />
      <TextField
        label="Meaningful minutes (optional)"
        type="number"
        min={0}
        value={meaningful}
        placeholder="How much of it was real focus?"
        error={error ?? undefined}
        onChange={(event) => set_meaningful(event.target.value)}
      />
      <TextAreaField
        label="Notes (optional, encrypted at rest)"
        value={notes}
        onChange={(event) => set_notes(event.target.value)}
      />
      <Button variant="primary" disabled={busy} onClick={handle_finish}>
        {busy ? "Finishing…" : "■ Finish session"}
      </Button>
    </div>
  );
}
