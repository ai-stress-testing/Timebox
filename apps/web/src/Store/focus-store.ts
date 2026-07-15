import { create } from "zustand";
import type {
  CalendarEvent,
  PomodoroFinishResult,
  PomodoroSession,
} from "../lib/api-schemas";

/* Running pomodoro survives page switches (UI state, not server state). */

type FocusState = {
  session: PomodoroSession | null;
  event: CalendarEvent | null;
  result: PomodoroFinishResult | null;
  begin: (session: PomodoroSession, event: CalendarEvent) => void;
  complete: (result: PomodoroFinishResult) => void;
  clear: () => void;
};

export const use_focus_store = create<FocusState>()((set) => ({
  session: null,
  event: null,
  result: null,
  begin: (session, event) => set({ session, event, result: null }),
  complete: (result) => set({ result }),
  clear: () => set({ session: null, event: null, result: null }),
}));
