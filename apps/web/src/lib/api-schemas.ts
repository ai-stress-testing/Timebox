import { z } from "zod";
import { time_hhmm_pattern } from "./patterns";

/*
 * Zod schemas for every type in packages/types/api-contract.md (v1).
 * Every API response passes through `.safeParse` in Services/api-client.ts;
 * every form input is validated with the *Create schemas before sending.
 */

/** Coerce a form's string state into a number before validating it.
 * `z.coerce` turns `"abc"` into `NaN` and `""` into `0`; both then fail the
 * `int()`/`positive()` checks below, closing the NaN-reaches-API hole. */
export const positive_int_from_input = z.coerce.number().int().positive();
export const nonneg_int_from_input = z.coerce.number().int().nonnegative();

/* ---------------------------------------------------------------- enums */

export const event_type_schema = z.enum([
  "meeting",
  "task",
  "personal",
  "chore",
  "homework",
  "passive",
  "physical",
]);
export const attention_class_schema = z.enum(["active", "involved", "passive"]);
export const canvas_event_type_schema = z.enum([
  "focus_only",
  "involved_only",
  "passive_multi",
  "focus_passive",
]);
export const event_status_schema = z.enum([
  "scheduled",
  "in_progress",
  "completed",
  "skipped",
  "cancelled",
]);
export const calendar_color_schema = z.enum([
  "slate",
  "rose",
  "amber",
  "violet",
  "emerald",
  "sky",
  "stone",
  "orange",
]);
export const occurrence_status_schema = z.enum([
  "proposed",
  "scheduled",
  "in_progress",
  "completed",
  "missed",
  "healed",
  "cancelled",
]);
export const run_status_schema = z.enum([
  "pending",
  "running",
  "completed",
  "failed",
  "superseded",
]);
export const pomodoro_status_schema = z.enum([
  "active",
  "completed",
  "abandoned",
]);
export const prompt_status_schema = z.enum([
  "pending",
  "confirmed",
  "completed",
  "timed_out",
  "dismissed",
]);
export const residual_status_schema = z.enum([
  "open",
  "scheduled",
  "completed",
  "abandoned",
]);

export type EventType = z.infer<typeof event_type_schema>;
export type AttentionClass = z.infer<typeof attention_class_schema>;
export type CanvasEventType = z.infer<typeof canvas_event_type_schema>;
export type EventStatus = z.infer<typeof event_status_schema>;
export type CalendarColor = z.infer<typeof calendar_color_schema>;

/* ---------------------------------------------------------------- vault */

export const keyfile_schema = z.object({
  format: z.literal("timebox-keyfile"),
  version: z.literal(1),
  user_id: z.string(),
  secret: z.string(),
  created_at: z.string(),
});
export type Keyfile = z.infer<typeof keyfile_schema>;

export const vault_status_schema = z.object({ registered: z.boolean() });
export const vault_generate_schema = z.object({ keyfile: keyfile_schema });
export const vault_unlock_schema = z.object({
  token: z.string(),
  user_id: z.string(),
  expires_at: z.string(),
});
export type VaultSession = z.infer<typeof vault_unlock_schema>;

/* ------------------------------------------------------------ calendars */

export const calendar_schema = z.object({
  id: z.string(),
  name: z.string(),
  color: calendar_color_schema.nullable(),
  is_visible: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});
export const calendar_list_schema = z.array(calendar_schema);
export type Calendar = z.infer<typeof calendar_schema>;

/* --------------------------------------------------------------- events */

export const event_create_schema = z
  .object({
    title: z.string().min(1, "Title is required"),
    description: z.string().optional(),
    location: z.string().optional(),
    calendar_id: z.string().optional(),
    event_type: event_type_schema,
    attention_class: attention_class_schema.optional(),
    start_at: z.string().min(1, "Start time is required"),
    end_at: z.string().min(1, "End time is required"),
    is_all_day: z.boolean().optional(),
    estimated_minutes: z.number().int().positive().optional(),
    is_recurring: z.boolean().optional(),
    recurrence_weekdays: z.array(z.number().int().min(0).max(6)).optional(),
    recurrence_end: z.string().optional(),
  })
  .refine((value) => value.end_at > value.start_at, {
    message: "End must be after start",
    path: ["end_at"],
  })
  .refine(
    (value) => !value.is_recurring || (value.recurrence_weekdays?.length ?? 0) > 0,
    {
      message: "Pick at least one day",
      path: ["recurrence_weekdays"],
    },
  );
export type EventCreate = z.infer<typeof event_create_schema>;

export const event_schema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().nullish(),
  location: z.string().nullish(),
  calendar_id: z.string(),
  event_type: event_type_schema,
  attention_class: attention_class_schema,
  canvas_event_type: canvas_event_type_schema,
  start_at: z.string(),
  end_at: z.string(),
  is_all_day: z.boolean().nullish(),
  estimated_minutes: z.number().nullish(),
  status: event_status_schema,
  actual_minutes: z.number().nullable(),
  residual_of: z.string().nullable(),
  is_recurring: z.boolean().nullish(),
  recurrence_weekdays: z.array(z.number()).nullish(),
  recurrence_end: z.string().nullable(),
  master_event_id: z.string().nullable(),
  occurrence_date: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export const event_list_schema = z.array(event_schema);
export type CalendarEvent = z.infer<typeof event_schema>;

export const event_title_suggestion_schema = z.object({
  title: z.string(),
  occurrence_count: z.number(),
  avg_minutes: z.number().nullable(),
});
export const event_title_suggestion_list_schema = z.array(event_title_suggestion_schema);
export type EventTitleSuggestion = z.infer<typeof event_title_suggestion_schema>;

export type EventPatch = Partial<EventCreate> & { status?: EventStatus };

/* --------------------------------------------------------------- chores */

const hhmm = z
  .string()
  .regex(time_hhmm_pattern, "Use HH:MM (24h)");

export const chore_create_schema = z.object({
  name: z.string().min(1, "Name is required"),
  estimated_minutes: z.number().int().positive("Must be > 0"),
  priority: z.number().int().min(1).max(5).optional(),
  attention_class: attention_class_schema.optional(),
  color: calendar_color_schema.optional(),
  n_days: z.number().int().min(1, "Every N days, N >= 1"),
  n_min: z.number().int().min(1).optional(),
  n_max: z.number().int().min(1).optional(),
  preferred_days: z.array(z.number().int().min(0).max(6)).optional(),
  avoid_days: z.array(z.number().int().min(0).max(6)).optional(),
  preferred_time_start: hhmm.optional(),
  preferred_time_end: hhmm.optional(),
});
export type ChoreCreate = z.infer<typeof chore_create_schema>;

export const chore_schema = z.object({
  id: z.string(),
  name: z.string(),
  estimated_minutes: z.number(),
  priority: z.number(),
  attention_class: attention_class_schema,
  color: calendar_color_schema.nullish(),
  n_days: z.number(),
  n_min: z.number().nullish(),
  n_max: z.number().nullish(),
  preferred_days: z.array(z.number()).nullish(),
  avoid_days: z.array(z.number()).nullish(),
  preferred_time_start: z.string().nullish(),
  preferred_time_end: z.string().nullish(),
  n_original: z.number(),
  n_current: z.number(),
  is_active: z.boolean(),
  last_completed_at: z.string().nullable(),
  next_due_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export const chore_list_schema = z.array(chore_schema);
export type Chore = z.infer<typeof chore_schema>;

/* ------------------------------------------------------------- schedule */

export const schedule_run_create_schema = z.object({
  window_days: z.number().int().min(1).optional(),
  iterations: z.number().int().min(1).max(10000).optional(),
  seed: z.number().int().optional(),
});
export type ScheduleRunCreate = z.infer<typeof schedule_run_create_schema>;

export const schedule_run_schema = z.object({
  id: z.string(),
  run_type: z.literal("manual"),
  status: run_status_schema,
  window_start: z.string(),
  window_end: z.string(),
  window_days: z.number(),
  iterations: z.number(),
  seed: z.number(),
  score: z.number().nullable(),
  chores_scheduled: z.number().nullable(),
  mean_daily_load: z.number().nullable(),
  load_variance: z.number().nullable(),
  overloaded_days: z.number().nullable(),
  underloaded_days: z.number().nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});
export const schedule_run_list_schema = z.array(schedule_run_schema);
export type ScheduleRun = z.infer<typeof schedule_run_schema>;

export const occurrence_schema = z.object({
  id: z.string(),
  chore_id: z.string(),
  chore_name: z.string(),
  proposed_start_at: z.string(),
  proposed_end_at: z.string(),
  confidence_score: z.number(),
  load_score: z.number(),
  status: occurrence_status_schema,
  event_id: z.string().nullable(),
});
export type Occurrence = z.infer<typeof occurrence_schema>;

export const schedule_run_detail_schema = schedule_run_schema.extend({
  occurrences: z.array(occurrence_schema),
});
export type ScheduleRunDetail = z.infer<typeof schedule_run_detail_schema>;

export const schedule_apply_schema = z.object({ events_created: z.number() });

/* ------------------------------------------------------------- pomodoro */

export const pomodoro_start_schema = z.object({
  event_id: z.string().min(1),
  intended_minutes: positive_int_from_input,
});
export type PomodoroStart = z.infer<typeof pomodoro_start_schema>;

export const pomodoro_finish_input_schema = z.object({
  completion_flag: z.boolean(),
  meaningful_minutes: nonneg_int_from_input.optional(),
  notes: z.string().optional(),
});
export type PomodoroFinishInput = z.infer<typeof pomodoro_finish_input_schema>;

export const pomodoro_session_schema = z.object({
  id: z.string(),
  event_id: z.string(),
  intended_minutes: z.number(),
  actual_minutes: z.number().nullable(),
  meaningful_minutes: z.number().nullable(),
  status: pomodoro_status_schema,
  completion_flag: z.boolean(),
  notes: z.string().nullable(),
  started_at: z.string(),
  ended_at: z.string().nullable(),
});
export const pomodoro_session_list_schema = z.array(pomodoro_session_schema);
export type PomodoroSession = z.infer<typeof pomodoro_session_schema>;

export const residual_prompt_schema = z.object({
  id: z.string(),
  pomodoro_session_id: z.string(),
  event_id: z.string(),
  status: prompt_status_schema,
  prompted_at: z.string(),
  timeout_at: z.string(),
  user_remaining_minutes: z.number().nullable(),
  residual_id: z.string().nullable(),
});
export const residual_prompt_list_schema = z.array(residual_prompt_schema);
export type ResidualPrompt = z.infer<typeof residual_prompt_schema>;

export const task_residual_schema = z.object({
  id: z.string(),
  origin_event_id: z.string(),
  remaining_minutes: z.number(),
  session_count: z.number(),
  status: residual_status_schema,
  next_event_id: z.string().nullable(),
});
export type TaskResidual = z.infer<typeof task_residual_schema>;

export const pomodoro_finish_schema = z.object({
  session: pomodoro_session_schema,
  break_minutes: z.number(),
  residual_prompt: residual_prompt_schema.nullable(),
});
export type PomodoroFinishResult = z.infer<typeof pomodoro_finish_schema>;

export const prompt_response_kind_schema = z.enum([
  "completed",
  "confirmed",
  "dismissed",
]);
export type PromptResponseKind = z.infer<typeof prompt_response_kind_schema>;

export const prompt_respond_body_schema = z.object({
  response: prompt_response_kind_schema,
  remaining_minutes: positive_int_from_input.optional(),
});

export const prompt_respond_schema = z.object({
  prompt: residual_prompt_schema,
  residual: task_residual_schema.nullable(),
});

/* ------------------------------------------------------------------- ai */

export const ai_health_schema = z.object({
  ok: z.boolean(),
  model: z.string(),
  base_url: z.string(),
  detail: z.string().nullable(),
});
export type AiHealth = z.infer<typeof ai_health_schema>;

export const timebox_request_schema = z.object({
  task_title: z.string().min(1, "Task title is required"),
  estimated_minutes: z.number().int().positive("Must be > 0"),
  window_start: z.string().min(1, "Window start is required"),
  window_end: z.string().min(1, "Window end is required"),
  notes: z.string().optional(),
});
export type TimeboxRequest = z.infer<typeof timebox_request_schema>;

export const timebox_response_schema = z.object({
  proposal: z.object({
    start_at: z.string(),
    end_at: z.string(),
    rationale: z.string(),
  }),
  ai_session_id: z.string(),
});
export type TimeboxResponse = z.infer<typeof timebox_response_schema>;

export const llm_provider_kind_schema = z.enum(["ollama", "openai_compat"]);
export type LlmProviderKind = z.infer<typeof llm_provider_kind_schema>;

export const llm_settings_in_schema = z.object({
  provider_kind: llm_provider_kind_schema,
  base_url: z.string().min(1, "Base URL is required").max(500),
  model: z.string().min(1, "Model is required").max(200),
  api_key: z.string().max(500).optional(),
});
export type LlmSettingsIn = z.infer<typeof llm_settings_in_schema>;

export const llm_settings_out_schema = z.object({
  provider_kind: llm_provider_kind_schema,
  base_url: z.string(),
  model: z.string(),
  has_api_key: z.boolean(),
});
export type LlmSettingsOut = z.infer<typeof llm_settings_out_schema>;

/* --------------------------------------------------------------- health */

export const health_schema = z.object({
  ok: z.literal(true),
  service: z.literal("timebox-api"),
});

export const empty_schema = z.void();
