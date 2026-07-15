import { EventPicker } from "../Components/focus/event-picker";
import { FinishForm } from "../Components/focus/finish-form";
import type { FinishInput } from "../Components/focus/finish-form";
import { ResidualPromptCard } from "../Components/focus/residual-prompt-card";
import { SessionTimer } from "../Components/focus/session-timer";
import { Button } from "../Components/ui/button";
import {
  use_finish_session,
  use_pending_prompts,
  use_start_session,
} from "../Hooks/use-pomodoro";
import type { CalendarEvent } from "../lib/api-schemas";
import { to_error_message } from "../Services/api-client";
import { use_focus_store } from "../Store/focus-store";
import { push_toast } from "../Store/toast-store";

function BreakBanner() {
  const result = use_focus_store((state) => state.result);
  const clear = use_focus_store((state) => state.clear);
  if (result === null) return null;
  return (
    <div className="animate-pop-in flex items-center justify-between gap-3 rounded-lg border border-ok/40 bg-surface-1 p-5">
      <p className="text-sm text-hi">
        Session logged — take a{" "}
        <span className="font-display font-bold text-ok">{result.break_minutes} minute</span>{" "}
        break.
      </p>
      <Button variant="subtle" onClick={clear}>Dismiss</Button>
    </div>
  );
}

function RunningSession() {
  const session = use_focus_store((state) => state.session);
  const event = use_focus_store((state) => state.event);
  const complete = use_focus_store((state) => state.complete);
  const finish = use_finish_session();
  if (session === null || event === null) return null;

  const handle_finish = (input: FinishInput) => {
    finish.mutate(
      { session_id: session.id, ...input },
      {
        onSuccess: (result) => complete(result),
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  return (
    <>
      <SessionTimer session={session} title={event.title} />
      <FinishForm on_finish={handle_finish} busy={finish.isPending} />
    </>
  );
}

export function FocusPage() {
  const session = use_focus_store((state) => state.session);
  const result = use_focus_store((state) => state.result);
  const begin = use_focus_store((state) => state.begin);
  const start = use_start_session();
  const prompts = use_pending_prompts();
  const is_running = session !== null && result === null;

  const handle_start = (event: CalendarEvent, intended_minutes: number) => {
    start.mutate(
      { event_id: event.id, intended_minutes },
      {
        onSuccess: (started) => begin(started, event),
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  return (
    <section aria-label="Focus" className="mx-auto flex max-w-2xl flex-col gap-5">
      <h2 className="font-display text-title tracking-hug font-bold text-hi">Focus</h2>
      <BreakBanner />
      {(prompts.data ?? []).map((prompt) => (
        <ResidualPromptCard key={prompt.id} prompt={prompt} />
      ))}
      {is_running ? (
        <RunningSession />
      ) : (
        <EventPicker on_start={handle_start} busy={start.isPending} />
      )}
    </section>
  );
}
