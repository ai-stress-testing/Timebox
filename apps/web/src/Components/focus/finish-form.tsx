import { useState } from "react";
import { Button } from "../ui/button";
import { CheckboxField, TextAreaField, TextField } from "../ui/field";

export type FinishInput = {
  completion_flag: boolean;
  meaningful_minutes?: number;
  notes?: string;
};

/** End-of-session form: done flag, meaningful minutes, notes. */
export function FinishForm({ on_finish, busy }: {
  on_finish: (input: FinishInput) => void;
  busy: boolean;
}) {
  const [done, set_done] = useState(true);
  const [meaningful, set_meaningful] = useState("");
  const [notes, set_notes] = useState("");

  const handle_finish = () => {
    const meaningful_trimmed = meaningful.trim();
    on_finish({
      completion_flag: done,
      ...(meaningful_trimmed === "" ? {} : { meaningful_minutes: Number(meaningful_trimmed) }),
      ...(notes.trim() === "" ? {} : { notes: notes.trim() }),
    });
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
