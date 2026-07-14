import { useState } from "react";
import { use_respond_prompt } from "../../Hooks/use-pomodoro";
import type { ResidualPrompt } from "../../lib/api-schemas";
import { prompt_actions } from "../../lib/dispatch-maps/prompt-responses";
import { to_error_message } from "../../Services/api-client";
import { push_toast } from "../../Store/toast-store";
import { Button } from "../ui/button";
import { TextField } from "../ui/field";

/** The "Done?" flow after an incomplete session — dispatch-map driven. */
export function ResidualPromptCard({ prompt }: { prompt: ResidualPrompt }) {
  const respond = use_respond_prompt();
  const [remaining, set_remaining] = useState("15");

  const handle_action = (kind_index: number) => {
    const action = prompt_actions[kind_index];
    if (!action) return;
    const body = action.build_body(Number(remaining) || null);
    if (body === null) {
      push_toast("Enter the remaining minutes first.", "danger");
      return;
    }
    respond.mutate(
      { prompt_id: prompt.id, body },
      {
        onSuccess: (result) => {
          const created = result.residual !== null;
          push_toast(
            created ? "Residual saved — it will be rescheduled." : "Noted.",
            "ok",
          );
        },
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  return (
    <div className="animate-pop-in flex flex-col gap-3 rounded-lg border border-warn/40 bg-surface-1 p-5">
      <h4 className="font-display font-bold text-hi">Session ended — done?</h4>
      <p className="text-sm text-mid">
        You closed a pomodoro without marking the task complete.
      </p>
      <TextField
        label="Remaining minutes (if not done)"
        type="number"
        min={1}
        value={remaining}
        onChange={(event) => set_remaining(event.target.value)}
      />
      <div className="flex flex-wrap gap-2">
        {prompt_actions.map((action, index) => (
          <Button
            key={action.kind}
            variant={action.tone}
            disabled={respond.isPending}
            onClick={() => handle_action(index)}
          >
            {action.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
