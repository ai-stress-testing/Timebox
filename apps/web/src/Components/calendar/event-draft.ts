import { event_create_schema } from "../../lib/api-schemas";
import type {
  CalendarEvent,
  EventCreate,
  EventStatus,
} from "../../lib/api-schemas";
import {
  compose_local_iso,
  date_input_value,
  slot_start,
  time_input_value,
} from "../../lib/time";

/**
 * String-typed form state for the event drawer. The target date is a single
 * field shared by start and end (most events happen within one day); start
 * and end are time-only. Kept extensible for an upcoming all-day toggle and
 * repeats section.
 */
export type EventDraft = {
  title: string;
  event_type: EventCreate["event_type"];
  attention_class: NonNullable<EventCreate["attention_class"]>;
  date_local: string;
  start_time: string;
  end_time: string;
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
    date_local: date_input_value(start.toISOString()),
    start_time: time_input_value(start.toISOString()),
    end_time: time_input_value(end.toISOString()),
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
    date_local: date_input_value(event.start_at),
    start_time: time_input_value(event.start_at),
    end_time: time_input_value(event.end_at),
    estimated_minutes:
      event.estimated_minutes == null ? "" : String(event.estimated_minutes),
    description: event.description ?? "",
    status: event.status,
  };
}

export type DraftBuildResult =
  | { ok: true; value: EventCreate }
  | { ok: false; errors: Record<string, string> };

/** Zod issue paths that surface on a different (time-only) form field. */
const error_field_overrides: Record<string, string> = {
  start_at: "start_time",
  end_at: "end_time",
};

/** Validate the draft with zod and produce the EventCreate payload. */
export function build_event_create(draft: EventDraft): DraftBuildResult {
  const estimated = draft.estimated_minutes.trim();
  const candidate = {
    title: draft.title.trim(),
    event_type: draft.event_type,
    attention_class: draft.attention_class,
    start_at: compose_local_iso(draft.date_local, draft.start_time),
    end_at: compose_local_iso(draft.date_local, draft.end_time),
    ...(estimated === "" ? {} : { estimated_minutes: Number(estimated) }),
    ...(draft.description.trim() === ""
      ? {}
      : { description: draft.description.trim() }),
  };
  const parsed = event_create_schema.safeParse(candidate);
  if (parsed.success) return { ok: true, value: parsed.data };
  const errors: Record<string, string> = {};
  for (const issue of parsed.error.issues) {
    const path_key = String(issue.path[0] ?? "form");
    const key = error_field_overrides[path_key] ?? path_key;
    if (!errors[key]) errors[key] = issue.message;
  }
  if (draft.date_local.trim() === "" && (errors.start_time || errors.end_time)) {
    errors.date_local = "Date is required";
  }
  return { ok: false, errors };
}
