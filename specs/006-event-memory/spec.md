# Spec 006 — `event_memory` prefill table (GitHub #15)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** spec 007 (`duration_profiles`) for the statistically-grounded
estimate link — build 007 first, or stub `duration_profile_id` as nullable
and backfill once 007 lands.

## Problem

Issue #8 already shipped a title datalist: `event_service.title_suggestions`
scans the user's last 500 events, groups by **decrypted plaintext title**
in-process, and returns `{title, occurrence_count, avg_minutes}` computed
fresh on every call (`_event_minutes` + `_mean_minutes` in
`event_service.py`). That works but: (1) it re-scans and re-decrypts up to
500 rows on every keystroke-adjacent call, (2) it only remembers *duration*,
not the `attention_class` / `canvas_event_type` the user always ends up
picking for "Gym" or "Dentist", so those fields reset to the form default
every time, and (3) grouping by plaintext title means two users' identical
`title_hash` can never accidentally collide (good), but there's no stable
key to join against — a typo-fixed retitle silently starts a new group.

`event_memory` replaces the scan with a maintained-on-write table keyed by a
**title hash**, and widens what's remembered.

## Data model

```
event_memory
  id                    UUIDv7 PK
  user_id               String(36)
  title_hash            String(64)   -- SHA-256 hex of the normalized (trim+lowercase) title
  event_type            String(64)   -- last-used type_key
  attention_class       String(16)
  canvas_event_type     String(16) nullable  -- last computed value, informational only
                                              -- (still server-assigned per event, never copied in as an override)
  estimated_minutes     Integer nullable
  duration_profile_id   String(36) nullable  -- FK-by-convention to spec 007's duration_profiles.id
  occurrence_count      Integer default 1
  last_seen_at          DateTime
  created_at / updated_at / deleted_at

  unique index on (user_id, title_hash) where deleted_at is null
```

`title_hash`, not the plaintext title: this table's *keys* don't need to be
readable (nothing displays "the memory row for hash abc123"), only the
*join* needs to work, and hashing avoids a second place storing the same
sensitive text `events.title_enc` already encrypts. The **display** title
still comes from the event itself — `event_memory` is a lookup table, not a
source of truth for titles. Same normalize-then-hash pattern this spec
establishes is reused by spec 007 (`duration_profiles.label` join key).

## Architecture

- `Models/event_memory.py` — table above.
- `Core/patterns.py` or a small `Core/title_hash.py` — `normalize_title(s) ->
  str` (trim + casefold) and `hash_title(s) -> str` (SHA-256 hex of the
  normalized form). One function, reused by spec 007 — do not duplicate the
  normalization rule.
- `Repositories/event_memory_repo.py` — `get_by_hash(session, user_id,
  title_hash)`, `upsert(session, user_id, title_hash, **fields)`.
- `Services/event_memory_service.py`:
  - `remember(session, user_id, title, event_type, attention_class,
    canvas_event_type, estimated_minutes)` — called from
    `event_service.create_event` (and only on **create**, not every patch —
    remembering mid-edit churn would make the "usual" value noisy) after the
    event is persisted. Upserts by `title_hash`: increments
    `occurrence_count`, bumps `last_seen_at`, overwrites the remembered
    `event_type`/`attention_class`/`estimated_minutes` with the just-used
    values (last-write-wins — simplest correct policy; a user who changes
    how they classify "Gym" wants the new classification remembered, not the
    old one).
  - `recall(session, user_id, title) -> EventMemoryOut | None` — hash the
    input title, look up. Called from the event-create path (server-side, so
    the frontend doesn't need its own hashing) to prefill a response the
    create form can read *before* the user finishes typing/submitting — see
    API below.
- **API**: `GET /events/memory?title=<str>` — hashes server-side, returns the
  remembered `{event_type, attention_class, estimated_minutes,
  occurrence_count}` or 404. This **replaces** `GET /events/titles` (issue
  #8's endpoint) as the datalist's data source for prefill, but
  `GET /events/titles` can stay as-is for the autocomplete *list itself*
  (it's a distinct query shape — "all titles I've used" vs. "what do I
  usually do for this exact title") unless you want to fold both into one
  response; not required for this spec to land.
- **Frontend**: the event form's existing title-autocomplete flow (from #8)
  gains a debounced call to `GET /events/memory` on exact-match blur/select,
  prefilling `event_type` + `attention_class` + `estimated_minutes` if the
  fields are still at their defaults (never clobber a value the user already
  typed).

## Non-goals

- No cross-user memory (obviously — single-user app, but worth stating: this
  table is exactly as user-scoped as everything else, no shared corpus).
- No forgetting/decay policy (an old one-off "Dentist" visit from a year ago
  still prefills today) — acceptable for v1; a `last_seen_at`-based decay is
  a future refinement, not blocking.
- Does not change how `canvas_event_type` is computed — still always
  server-assigned by `assign_canvas_type` on the real event; the memory
  row's `canvas_event_type` is informational/read-only.

## Acceptance criteria

- [ ] Creating an event with a new title creates a memory row;
      creating a second event with the same normalized title (different
      case/whitespace) hits the **same** row (`occurrence_count` becomes 2,
      not a new row) — proves normalization+hash join works.
- [ ] `GET /events/memory?title=Gym` after creating one "Gym" event with
      `event_type=physical, attention_class=involved, estimated_minutes=60`
      returns exactly those three values.
- [ ] Creating a second "Gym" event with a different `event_type` updates
      the memory row to the new value (last-write-wins verified).
- [ ] `event_memory` rows never contain plaintext titles at rest (only
      `title_hash`) — a direct-DB-read test analogous to
      `test_titles_encrypted_at_rest` in `test_events.py`.
- [ ] Deleting all events with a given title does **not** delete the memory
      row (memory persists independent of event lifecycle — it's "what you
      usually do", not "what currently exists").
