import { useState } from "react";
import { todo_create_schema } from "../../lib/api-schemas";
import type { TodoCreate } from "../../lib/api-schemas";
import { Button } from "../ui/button";
import { TextField } from "../ui/field";

type TodoDraft = { title: string; estimated_minutes: string };

const empty_draft: TodoDraft = { title: "", estimated_minutes: "" };

function build_todo(draft: TodoDraft): TodoCreate | null {
  const candidate = {
    title: draft.title.trim(),
    ...(draft.estimated_minutes.trim() === ""
      ? {}
      : { estimated_minutes: Number(draft.estimated_minutes) }),
  };
  const parsed = todo_create_schema.safeParse(candidate);
  return parsed.success ? parsed.data : null;
}

export function TodoForm({ on_submit, busy }: {
  on_submit: (todo: TodoCreate) => void;
  busy: boolean;
}) {
  const [draft, set_draft] = useState<TodoDraft>(empty_draft);
  const [error, set_error] = useState<string | null>(null);
  const patch = (value: Partial<TodoDraft>) =>
    set_draft((current) => ({ ...current, ...value }));

  const handle_submit = () => {
    const todo = build_todo(draft);
    if (todo === null) {
      set_error("Check the fields — title is required, minutes must be > 0.");
      return;
    }
    set_error(null);
    on_submit(todo);
    set_draft(empty_draft);
  };

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-edge bg-surface-1 p-5">
      <h3 className="font-display font-bold text-hi">New to-do</h3>
      <TextField
        label="Title"
        value={draft.title}
        placeholder="Reply to the landlord"
        onChange={(event) => patch({ title: event.target.value })}
      />
      <TextField
        label="Estimated minutes (optional)"
        type="number"
        min={1}
        value={draft.estimated_minutes}
        placeholder="Optional"
        onChange={(event) => patch({ estimated_minutes: event.target.value })}
      />
      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
      <Button variant="primary" disabled={busy} onClick={handle_submit}>
        {busy ? "Adding…" : "Add to-do"}
      </Button>
    </div>
  );
}
