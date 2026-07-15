import { useEffect, useState } from "react";
import type { PomodoroSession } from "../../lib/api-schemas";

const tick_interval_ms = 1_000;

function format_elapsed(total_seconds: number): string {
  const minutes = Math.floor(total_seconds / 60);
  const seconds = total_seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function use_elapsed_seconds(started_at: string): number {
  const [now_ms, set_now_ms] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => set_now_ms(Date.now()), tick_interval_ms);
    return () => clearInterval(timer);
  }, []);
  return Math.max(0, Math.floor((now_ms - new Date(started_at).getTime()) / 1000));
}

/** Large expressive countdown/count-up for the running pomodoro. */
export function SessionTimer({ session, title }: {
  session: PomodoroSession;
  title: string;
}) {
  const elapsed = use_elapsed_seconds(session.started_at);
  const intended_seconds = session.intended_minutes * 60;
  const over_intent = elapsed >= intended_seconds;
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center">
      <p className="text-sm text-mid">Focusing on</p>
      <p className="font-display max-w-md truncate text-lg font-bold text-hi">{title}</p>
      <p
        aria-live="off"
        className={`font-display text-display tracking-hug font-black
          bg-clip-text text-transparent
          [background-image:var(--tb-gradient-accent)]
          ${over_intent ? "animate-pop-in" : ""}`}
      >
        {format_elapsed(elapsed)}
      </p>
      <p className="text-xs text-low">
        intended {session.intended_minutes} min
        {over_intent ? " — checkpoint passed, timer keeps running" : ""}
      </p>
    </div>
  );
}
