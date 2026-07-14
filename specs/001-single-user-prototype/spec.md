# Spec 001 — Single-User Timebox Prototype

**Status:** implemented (prototype)
**Source plan:** kebab-lover-xoxo/Timebox `Pre-Flight-Docs` branch
(Architecture.md, DB-Schemas.md, Code-Standards.md)

## Problem

One person wants a privacy-absolute calendar that schedules their chores for
them, timeboxes their tasks with a local LLM, and learns their focus patterns —
without an account, a password, or a byte of surveillance.

## Critical journeys

### J1 — Key vault: generate, stash, unlock
1. First launch shows the vault screen. User clicks **Generate key** →
   downloads `timebox.key` (JSON: format tag, version, `user_id` UUIDv7,
   32-byte secret). The server registers only a verifier, never the secret.
2. User stores the file anywhere they like (USB, password manager, drive).
3. Any later visit: drop/upload `timebox.key` → session opens. Wrong or
   malformed file → generic rejection, no detail leaked.
4. All sensitive event/chore text is AES-256-GCM encrypted at rest with a key
   HKDF-derived from the key file. Losing the file means losing the data —
   stated plainly in the UI.

### J2 — Calendar core
1. User sees a week view. Default calendar exists after first unlock.
2. Create/edit/delete events with `event_type` (meeting, task, personal,
   chore, homework, passive, physical) and `attention_class`
   (active / involved / passive).
3. The system auto-assigns `canvas_event_type` (focus_only, involved_only,
   passive_multi, focus_passive) from attention class + overlap detection —
   never set by the user (DB-Schemas "Automatic Assignment Rules").

### J3 — Chore scheduling (Monte Carlo)
1. User defines chores: name, estimated minutes, priority 1–5, every-n-days
   frequency (n_min/n_max bounds), preferred/avoid days, preferred time window.
2. User hits **Plan my chores** → seeded Monte Carlo run samples free slots
   over the window (default 49 days, bounded iterations), scores by preference
   + conflict + load balance, and writes ranked `chore_occurrences`.
3. User applies the proposal → occurrences become real chore events.
4. Every run is reproducible: seed + parameters stored on `schedule_runs`.

### J4 — AI timeboxing (Ollama only)
1. User asks "timebox this task" → the LLM service reads the task + existing
   events and proposes an optimal slot with a rationale.
2. Every prompt passes the prompt sanitiser (control-char strip, length bound,
   injection-pattern blocklist) before reaching Ollama. Failures return a
   generic 400.
3. Only the SHA-256 hash of the prompt is stored (`ai_sessions`).
4. Ollama down → graceful, actionable error; the calendar keeps working.

### J5 — Pomodoro + residuals
1. Starting a focus event opens a pomodoro session (active attention class
   only). Break rule: session < 40 min → 5 min break; ≥ 40 min → 50% of logged
   time.
2. Session ends without completion → a residual prompt asks "Done?"; if not,
   the user confirms remaining minutes and a residual task is created for
   rescheduling.

## Non-goals (this spec)

- Multi-user, sharing, ACL enforcement beyond the single agent grantee.
- Radial canvas UI, editor engine, keystroke analytics (future specs 002+).
- vLLM, Redis, Postgres, k3s — seams exist, implementations deferred.
- Recurrence exceptions (RRULE storage exists; expansion is basic).

## Acceptance criteria

- [x] Key generate → unlock → CRUD round-trip works with encryption at rest
      (DB file contains no plaintext titles).
- [x] Unlock with a tampered key file is rejected with a generic error.
- [x] Canvas event type auto-assignment matches the DB-Schemas rule table for
      all attention-class combinations.
- [x] Two Monte Carlo runs with the same seed and inputs produce identical
      occurrence sets; iterations are hard-bounded.
- [x] Prompt sanitiser blocks the documented injection signatures and
      over-length prompts; prompts are stored as hashes only.
- [x] API rejects any request without a valid session token except vault +
      health routes.
- [x] Backend test suite green; frontend type-checks and builds clean.
