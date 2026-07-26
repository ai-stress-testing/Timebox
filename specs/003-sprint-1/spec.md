# Sprint 1 — GitHub issues #2–#6

**Branch:** `sprint-1` (off `main`)
**Roles:** Fable/Opus = orchestrator + micro-planner + verifier · Sonnet
engineering agents = workers. Each issue: scoped brief → Sonnet implements →
verify (pytest + tsc + build, e2e where it matters) → commit → close issue.

## Sequencing (file-contention aware)

Track A (calendar — shared event form/schema/grid, **serial**):
1. **#3** Cleaner event UI — single target date, time-only start/end inputs.
2. **#5** All-day row above hour 0.
3. **#2** Repeats UI + backend recurrence expansion.
4. **#4** Delete this / all future (depends on #2 recurrence).

Track B (**parallel**, disjoint files):
- **#6** Unrestrain AI providers — provider/model/endpoint selectable.

## Issue notes

- **#3**: `event-draft.ts` gains a `date_local` + `start_time`/`end_time`
  split; `event-form.tsx` shows one date field + two time inputs; build step
  recomposes ISO. Edit drawer keeps working. No backend change.
- **#5**: `is_all_day` already exists in model + schema. Convention: all-day =
  `start_at` 00:00 local → `end_at` next-day 00:00, `is_all_day=true`. Grid
  gains an all-day strip above hour 0 rendering those events; form gains an
  all-day toggle that hides time inputs.
- **#2**: Event model already has `is_recurring`, `recurrence_freq`,
  `recurrence_rule` (JSONB), `recurrence_end`, `master_event_id`,
  `original_start_at`. Expose a simple weekly-by-weekday rule in the schema;
  store the master; **expand** occurrences within the query window in the
  read path (sparse, Google-style — instances are virtual, not persisted).
  Frontend: repeats section (weekday chips) in the new-event form.
- **#4**: Delete on a recurring event opens a modal: "This event" (write a
  cancelled exception for that date) vs "This and following" (set
  `recurrence_end`). Non-recurring events delete as today.
- **#6**: Generalize the LLM seam. Keep `LlmProvider` protocol; add an
  OpenAI-compatible provider (LM Studio, Ollama `/v1`, any local endpoint)
  alongside native Ollama. Per-user `llm_settings` (provider kind, base_url,
  model, optional api_key encrypted at rest) chosen at runtime; env values are
  the default. Settings surface in the web app. api_key never logged.

## Acceptance (Fable verifies each)
- pytest green; ruff clean; `tsc --noEmit` + `vite build` clean.
- New behavior exercised (unit test or Playwright) before the issue is closed.
- Each issue closed with a short comment referencing the commit.
