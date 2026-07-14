import { event_create_schema } from "../../lib/api-schemas";
import type {
  CalendarEvent,
  EventCreate,
  EventStatus,
} from "../../lib/api-schemas";
import {
  iso_to_local_input,
  local_input_to_iso,
  slot_start,
} from "../../lib/time";

/** String-typed form state for the event drawer. */
export type EventDraft = {
  title: string;
  event_type: EventCreate["event_type"];
  attention_class: NonNullable<EventCreate["attention_class"]>;
  start_local: string;
  end_local: string;
  estimated_minutes: string;
  description: string;
  status: EventStatus;
};

export function draft_from_slot(start: Date): EventDraft {
  const end = slot_start(start, start.getHours() + 1);
  return {
    title: "",
    event_type: "task",
    attention_class: "active",
    start_local: iso_to_local_input(start.toISOString()),
    end_local: iso_to_local_input(end.toISOString()),
    estimated_minutes: "",
    description: "",
    status: "scheduled",
  };
}

export function draft_from_event(event: CalendarEvent): EventDraft {
  return {
    title: event.title,
    event_type: event.event_type,
    attention_class: event.attention_class,
    start_local: iso_to_local_input(event.start_at),
    end_local: iso_to_local_input(event.end_at),
    estimated_minutes:
      event.estimated_minutes == null ? "" : String(event.estimated_minutes),
    description: event.description ?? "",
    status: event.status,
  };
}

export type DraftBuildResult =
  | { ok: true; value: EventCreate }
  | { ok: false; errors: Record<string, string> };

/** Validate the draft with zod and produce the EventCreate payload. */
export function build_event_create(draft: EventDraft): DraftBuildResult {
  const estimated = draft.estimated_minutes.trim();
  const candidate = {
    title: draft.title.trim(),
    event_type: draft.event_type,
    attention_class: draft.attention_class,
    start_at: local_input_to_iso(draft.start_local),
    end_at: local_input_to_iso(draft.end_local),
    ...(estimated === "" ? {} : { estimated_minutes: Number(estimated) }),
    ...(draft.description.trim() === ""
      ? {}
      : { description: draft.description.trim() }),
  };
  const parsed = event_create_schema.safeParse(candidate);
  if (parsed.success) return { ok: true, value: parsed.data };
  const errors: Record<string, string> = {};
  for (const issue of parsed.error.issues) {
    const key = String(issue.path[0] ?? "form");
    if (!errors[key]) errors[key] = issue.message;
  }
  return { ok: false, errors };
}
