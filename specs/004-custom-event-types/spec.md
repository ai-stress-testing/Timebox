# Spec 004 — User-defined event types (GitHub #26)

**Branch:** `sprint-1`
**Pipeline (Ges-Talt agents):** `backend-dev` implements the API/data model →
`frontend-react-dev` implements the UI → `logicians-code-reviewer` /
`logicians-falsifier` verify → Fable verifies live + ships.

## Problem
`event_type` is a fixed enum (`meeting, task, personal, chore, homework,
passive, physical`) hardcoded in the ORM, Pydantic + zod schemas, the
`event-colors` dispatch map, and the event form. Users must be able to create
their own types (label + color); the current seven remain as built-in
**presets**.

## Data model (create_all; prototype has no migrations — fresh DB)
- New `event_types` table (user-scoped, UUIDv7, soft delete):
  `id, user_id, key (slug, unique-per-user), label_enc, color (calendar_color),
  is_preset (bool), is_active (bool), sort_order (int), created/updated/deleted_at`.
- Seed the 7 presets per user (`is_preset=true`, `key` = the preset name) when
  the user's types are first ensured (same bootstrap point as the default
  calendar). Presets are recolorable/hideable but **not deletable**.
- `events.event_type` stays a `String` column but now holds a **`type_key`**
  referencing `event_types.key` (string, not a hard FK — matches the existing
  "color is a display preference, not enforced by DB" stance). Existing rows
  already hold valid preset keys.

## Backend contract (backend-dev)
- `GET /event-types` → active types for the user (presets + custom, ordered by
  `sort_order` then created_at). Ensures presets are seeded first.
- `POST /event-types { label, color }` → custom type (server derives a unique
  `key` slug from the label; 409 on collision after N attempts).
- `PATCH /event-types/{id} { label?, color?, is_active?, sort_order? }`.
- `DELETE /event-types/{id}` → soft-delete a custom type; **409 on a preset**.
- Events: `EventCreate.event_type` / `EventPatch.event_type` become a
  `type_key` string **validated against the user's active types** in the event
  service (unknown key → 422). `EventOut.event_type` stays the key. Do NOT keep
  the static enum for events (that's the whole point) — validate dynamically.
- Colors: the event's display color is resolved from the user's `event_types`
  row, not a hardcoded map; keep a neutral fallback token for an unknown key.
- Encryption: `label_enc` uses the same AES-GCM field codec as event titles.

## Frontend contract (frontend-react-dev)
- `lib/api-schemas.ts`: zod `event_type_summary` (`{id, key, label, color,
  is_preset, is_active, sort_order}`) + list; loosen `event_create_schema`'s
  `event_type` from the enum to a non-empty string (server validates the key).
- `Hooks/use-events.ts`: `use_event_types()` query; create/patch/delete
  mutations invalidating it + events.
- `event-colors` dispatch map → a lookup over the fetched types (key → color
  token) with a neutral fallback; keep the `calendar_color → token` swatch map.
- Event form **Type** dropdown driven by `GET /event-types` (active only) with
  a "＋ New type…" inline create (label + color-swatch picker from the
  `calendar_color` palette). Event blocks/all-day chips color via the lookup.
- A small **Types manager** (Settings section or calendar sub-panel): list,
  add, recolor, reorder, hide; presets can't be deleted (no delete affordance).
- Tokens only — no hardcoded hex/px. Components ≤60 lines.

## Acceptance (Fable verifies live)
- 7 presets seeded per user, behaving exactly as today; a new custom type is
  immediately selectable and colors its events across week + all-day views.
- Rename/recolor updates rendering; deleting a custom type is safe (its events
  fall back to a neutral type/color, no crash); deleting a preset → 409.
- Backend rejects an unknown `type_key` (422); tests cover preset seeding,
  custom CRUD, preset-delete rejection, and an event round-trip with a custom
  type. `pytest` + `ruff` + `tsc` + `vite build` clean.
