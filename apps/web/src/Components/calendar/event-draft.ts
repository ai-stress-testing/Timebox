import { event_create_schema } from "../../lib/api-schemas";
import type {
  CalendarEvent,
  EventCreate,
  EventStatus,
} from "../../lib/api-schemas";
import {
  compose_local_iso,
  date_input_value,
  next_day_midnight_iso,
  slot_start,
  time_input_value,
} from "../../lib/time";

/**
 * String-typed form state for the event drawer. The target date is a single
 * field shared by start and end (most events happen within one day); start
 * and end are time-only unless `is_all_day` is set, in which case the time
 * fields are ignored and the whole day is boxed. `repeats`/`repeat_weekdays`/
 * `repeat_until` back the weekly-by-weekday repeats section — `repeat_until`
 * is a "YYYY-MM-DD" date string, "" meaning open-ended.
 */
export type EventDraft = {
  title: string;
  event_type: EventCreate["event_type"];
  attention_class: NonNullable<EventCreate["attention_class"]>;
  date_local: string;
  start_time: string;
  end_time: string;
  is_all_day: boolean;
  estimated_minutes: string;
  description: string;
  status: EventStatus;
  repeats: boolean;
  repeat_weekdays: number[];
  repeat_until: string;
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
    is_all_day: false,
    estimated_minutes: "",
    description: "",
    status: "scheduled",
    repeats: false,
    repeat_weekdays: [],
    repeat_until: "",
  };
}

/** Sensible time-field defaults for an all-day event, in case the toggle is unchecked. */
const default_all_day_times = { start_time: "09:00", end_time: "10:00" } as const;

export function draft_from_event(event: CalendarEvent): EventDraft {
  const is_all_day = event.is_all_day ?? false;
  return {
    title: event.title,
    event_type: event.event_type,
    attention_class: event.attention_class,
    date_local: date_input_value(event.start_at),
    start_time: is_all_day
      ? default_all_day_times.start_time
      : time_input_value(event.start_at),
    end_time: is_all_day
      ? default_all_day_times.end_time
      : time_input_value(event.end_at),
    is_all_day,
    estimated_minutes:
      event.estimated_minutes == null ? "" : String(event.estimated_minutes),
    description: event.description ?? "",
    status: event.status,
    repeats: event.is_recurring ?? false,
    repeat_weekdays: event.recurrence_weekdays ?? [],
    repeat_until: event.recurrence_end ? date_input_value(event.recurrence_end) : "",
  };
}

export type DraftBuildResult =
  | { ok: true; value: EventCreate }
  | { ok: false; errors: Record<string, string> };

/** Zod issue paths that surface on a different (time-only) form field. */
const error_field_overrides: Record<string, string> = {
  start_at: "start_time",
  end_at: "end_time",
  recurrence_weekdays: "repeat_weekdays",
  recurrence_end: "repeat_until",
};

/** Start/end ISO instants for the draft's temporal fields. */
function draft_span(draft: EventDraft): { start_at: string; end_at: string } {
  if (draft.is_all_day) {
    return {
      start_at: compose_local_iso(draft.date_local, "00:00"),
      end_at: next_day_midnight_iso(draft.date_local),
    };
  }
  return {
    start_at: compose_local_iso(draft.date_local, draft.start_time),
    end_at: compose_local_iso(draft.date_local, draft.end_time),
  };
}

/** Repeats fields, included only while `repeats` is on (see build_event_create). */
function draft_repeats(draft: EventDraft): Partial<EventCreate> {
  if (!draft.repeats) return {};
  const until = draft.repeat_until.trim();
  return {
    is_recurring: true,
    recurrence_weekdays: draft.repeat_weekdays,
    ...(until === "" ? {} : { recurrence_end: compose_local_iso(until, "23:59") }),
  };
}

/** Validate the draft with zod and produce the EventCreate payload. */
export function build_event_create(draft: EventDraft): DraftBuildResult {
  const estimated = draft.estimated_minutes.trim();
  const candidate = {
    title: draft.title.trim(),
    event_type: draft.event_type,
    attention_class: draft.attention_class,
    ...draft_span(draft),
    is_all_day: draft.is_all_day,
    ...(estimated === "" ? {} : { estimated_minutes: Number(estimated) }),
    ...(draft.description.trim() === ""
      ? {}
      : { description: draft.description.trim() }),
    ...draft_repeats(draft),
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
