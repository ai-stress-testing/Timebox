# Timebox API Contract v1

Source of truth for both `apps/api` (implements) and `apps/web` (consumes).
Base URL: `http://localhost:8787/api/v1`. All timestamps are ISO-8601 UTC.
JSON everywhere. Errors: `{ "detail": string }` — 401 no/expired session,
400 validation or sanitiser rejection (generic), 404 missing, 409 conflict.

Auth: `Authorization: Bearer <token>` on every route **except**
`/vault/status`, `/vault/generate`, `/vault/unlock`, `/health`.

## Enums

```
event_type       = meeting | task | personal | chore | homework | passive | physical
attention_class  = active | involved | passive
canvas_event_type= focus_only | involved_only | passive_multi | focus_passive
event_status     = scheduled | in_progress | completed | skipped | cancelled
calendar_color   = slate | rose | amber | violet | emerald | sky | stone | orange
occurrence_status= proposed | scheduled | in_progress | completed | missed | healed | cancelled
run_status       = pending | running | completed | failed | superseded
pomodoro_status  = active | completed | abandoned
prompt_status    = pending | confirmed | completed | timed_out | dismissed
```

## Vault

| Route | Body | Response |
|---|---|---|
| `GET /vault/status` | — | `{ registered: boolean }` |
| `POST /vault/generate` | — | `{ keyfile: Keyfile }` · 409 if an identity already exists |
| `POST /vault/unlock` | `{ keyfile: Keyfile }` | `{ token: string, user_id: uuid, expires_at: iso }` · 401 generic on any mismatch |
| `POST /vault/lock` | — | 204 |
| `POST /vault/reset` | `{ confirm: "ERASE" }` | 204 — soft-deletes all data |

```ts
type Keyfile = {
  format: "timebox-keyfile"; version: 1;
  user_id: string;            // uuid7 — the user's identity
  secret: string;             // base64url, 32 bytes — never sent anywhere else
  created_at: string;
};
```
The web app must offer the generated keyfile as a download (`timebox.key`) and
must state that losing it makes the data unrecoverable.

## Calendars

`GET /calendars` → `Calendar[]` · `POST /calendars {name, color?}` → `Calendar`

`Calendar = { id, name, color: calendar_color|null, is_visible, created_at, updated_at }`
(`color: null` marks the default calendar, auto-created on first unlock.)

## Events

| Route | Notes |
|---|---|
| `GET /events?start=iso&end=iso` | events overlapping the range → `Event[]` |
| `POST /events` | `EventCreate` → `Event` (201) |
| `GET /events/{id}` · `PATCH /events/{id}` (partial `EventCreate` + `status`) · `DELETE` → 204 |

```ts
type EventCreate = {
  title: string; description?: string; location?: string;
  calendar_id?: string;                 // default calendar if omitted
  event_type: EventType;
  attention_class?: AttentionClass;     // default "active"
  start_at: string; end_at: string;     // end > start
  is_all_day?: boolean;
  estimated_minutes?: number;
};
type Event = EventCreate & {
  id: string; calendar_id: string; attention_class: AttentionClass;
  canvas_event_type: CanvasEventType;   // ALWAYS server-assigned, read-only
  status: EventStatus; actual_minutes: number|null;
  residual_of: string|null; created_at: string; updated_at: string;
};
```

## Chores

`GET /chores` · `POST /chores` · `PATCH /chores/{id}` · `DELETE /chores/{id}`

```ts
type ChoreCreate = {
  name: string; estimated_minutes: number;     // > 0
  priority?: number;                            // 1..5, default 3
  attention_class?: AttentionClass; color?: CalendarColor;
  n_days: number;                               // every n days, >= 1
  n_min?: number; n_max?: number;               // defaults 1 / 30
  preferred_days?: number[]; avoid_days?: number[];   // 0=Sun..6=Sat
  preferred_time_start?: string; preferred_time_end?: string; // "HH:MM"
};
type Chore = ChoreCreate & {
  id: string; priority: number; attention_class: AttentionClass;
  n_original: number; n_current: number; is_active: boolean;
  last_completed_at: string|null; next_due_at: string|null;
  created_at: string; updated_at: string;
};
```

## Schedule (Monte Carlo)

| Route | Body → Response |
|---|---|
| `POST /schedule/runs` | `{ window_days?: number (default 49), iterations?: number (default 2000, max 10000), seed?: number }` → `ScheduleRunDetail` (201) |
| `GET /schedule/runs?limit=10` | `ScheduleRun[]` (newest first) |
| `GET /schedule/runs/{id}` | `ScheduleRunDetail` |
| `POST /schedule/runs/{id}/apply` | — → `{ events_created: number }`; occurrences → chore events; 409 if already applied |

```ts
type ScheduleRun = {
  id: string; run_type: "manual"; status: RunStatus;
  window_start: string; window_end: string; window_days: number;
  iterations: number; seed: number; score: number|null;
  chores_scheduled: number|null; mean_daily_load: number|null;
  load_variance: number|null; overloaded_days: number|null;
  underloaded_days: number|null; created_at: string; completed_at: string|null;
};
type Occurrence = {
  id: string; chore_id: string; chore_name: string;
  proposed_start_at: string; proposed_end_at: string;
  confidence_score: number; load_score: number;
  status: OccurrenceStatus; event_id: string|null;
};
type ScheduleRunDetail = ScheduleRun & { occurrences: Occurrence[] };
```

## Pomodoro & residuals

| Route | Body → Response |
|---|---|
| `POST /pomodoro/sessions` | `{ event_id: string, intended_minutes: number }` → `PomodoroSession` (201) · 409 if event's attention_class ≠ active or a session is already open |
| `POST /pomodoro/sessions/{id}/finish` | `{ completion_flag: boolean, meaningful_minutes?: number, notes?: string }` → `{ session: PomodoroSession, break_minutes: number, residual_prompt: ResidualPrompt|null }` |
| `GET /pomodoro/sessions?limit=20` | `PomodoroSession[]` |
| `GET /pomodoro/prompts?status=pending` | `ResidualPrompt[]` |
| `POST /pomodoro/prompts/{id}/respond` | `{ response: "completed"|"confirmed"|"dismissed", remaining_minutes?: number }` → `{ prompt: ResidualPrompt, residual: TaskResidual|null }` — `confirmed` requires `remaining_minutes` |

Break rule (server-computed): `actual < 40 min → 5`, `actual >= 40 → round(actual * 0.5)`.

```ts
type PomodoroSession = {
  id: string; event_id: string; intended_minutes: number;
  actual_minutes: number|null; meaningful_minutes: number|null;
  status: PomodoroStatus; completion_flag: boolean; notes: string|null;
  started_at: string; ended_at: string|null;
};
type ResidualPrompt = {
  id: string; pomodoro_session_id: string; event_id: string;
  status: PromptStatus; prompted_at: string; timeout_at: string;
  user_remaining_minutes: number|null; residual_id: string|null;
};
type TaskResidual = {
  id: string; origin_event_id: string; remaining_minutes: number;
  session_count: number; status: "open"|"scheduled"|"completed"|"abandoned";
  next_event_id: string|null;
};
```

## AI (Ollama only)

| Route | Body → Response |
|---|---|
| `GET /ai/health` | — → `{ ok: boolean, model: string, base_url: string, detail: string|null }` (never 5xx: `ok:false` when Ollama is down) |
| `POST /ai/timebox` | `{ task_title: string, estimated_minutes: number, window_start: iso, window_end: iso, notes?: string }` → `{ proposal: { start_at: iso, end_at: iso, rationale: string }, ai_session_id: string }` · 400 generic on sanitiser rejection · 503 `{detail}` when Ollama unreachable |

## Health

`GET /health` (no auth) → `{ ok: true, service: "timebox-api" }`
