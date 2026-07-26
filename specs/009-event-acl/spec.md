# Spec 009 — `event_acl`: scoped access grants for calendars/events (GitHub #19)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** nothing structurally, but is the biggest architectural
departure of this batch — it's the first time anything other than the vault
owner authenticates against this API. Read the "Why this is harder than it
looks" section before scoping an implementation pass.

## Problem

Every route today trusts one thing: `SessionAuthMiddleware` resolves a
bearer token to `(user_id, data_key)` via the in-memory `SessionStore`, and
that's the *only* identity the app has ever had (constitution Article I: one
user, no accounts). The `ai_sessions` table already proves prompts flow to
an external LLM provider — but that provider is called *by* the server with
the server's own resolved `data_key`, not authenticated as a separate
principal. There's no code path today where "someone other than the owner"
holds a credential. `event_acl` introduces that concept for the first time.

## Why this is harder than it looks

Every existing endpoint implicitly assumes `SessionContext.user_id` **is**
the resource owner and grants full access. Enforcing scoped ACL either means
(a) every repository query gains an ACL check, which touches nearly the
entire backend, or (b) a **separate, additive** grant-authenticated surface
that coexists with the existing owner-only routes rather than retrofitting
them. This spec chooses **(b)** deliberately — it's the only way to land a
real, scoped, revocable grant without a full-codebase migration blocking it.
Full enforcement on the existing owner routes is an explicit non-goal below.

## Data model

```
event_acl
  id                UUIDv7 PK
  resource_type      String(16)   -- "calendar" | "event"
  resource_id        String(36)
  scope              String(16)   -- "read" | "schedule" (propose/read only; "write" deferred, see non-goals)
  grantee_type        String(16)   -- "agent" (only type this spec implements)
  grantee_id          String(36)   -- opaque, assigned at grant creation
  grant_secret_verifier String(88)  -- HMAC verifier, same pattern as VaultIdentity.verifier — the raw secret is returned once at creation and never stored
  granted_by          String(36)   -- the owner's user_id
  granted_at
  expires_at          DateTime nullable  -- null = no expiry (discouraged, allowed)
  revoked_at          DateTime nullable
```

No `deleted_at`/soft-delete via `EntityMixin` — `revoked_at` is the correct
verb here (a grant is *revoked*, not *deleted*; the row must stay queryable
for audit even after revocation, so it needs its own explicit-intent column
rather than the generic soft-delete convention).

## Architecture

**Credential shape** mirrors the vault's own identity pattern exactly
(`Core/crypto.py::compute_verifier`/`generate_secret`): granting access
generates a random secret, returns it **once** in the grant-creation
response, and persists only its HMAC verifier. A grantee authenticates with
`Authorization: Bearer <grant_id>.<secret>` (the `.`-joined form lets the
middleware look up the row by `grant_id` without a table scan, then verify
the secret against the stored verifier — same shape a lot of API-key schemes
use, e.g. Stripe's `sk_live_<id>_<secret>`-style split).

- `Models/event_acl.py` — table above.
- `Repositories/event_acl_repo.py` — `get_by_id`, `list_for_owner`,
  `add_grant`, `revoke` (sets `revoked_at`).
- `Services/event_acl_service.py`:
  - `create_grant(session, owner_user_id, resource_type, resource_id, scope,
    expires_at) -> (GrantOut, raw_secret)` — owner-authenticated (existing
    `SessionContext`), validates the resource belongs to the owner.
  - `resolve_grant(session, grant_id, secret) -> GrantContext | None` — the
    new auth path: verify the secret against the stored verifier, check
    `revoked_at is None` and `expires_at` hasn't passed, return a
    **narrowed** context (`resource_type`, `resource_id`, `scope`,
    `owner_user_id` — not a general `user_id` like `SessionContext`, so
    handlers can't accidentally treat a grant like full ownership).
  - `revoke_grant(session, owner_user_id, grant_id)`.
- **Auth wiring**: a new `GrantAuthMiddleware` (or a branch inside
  `SessionAuthMiddleware` keyed on whether the bearer token contains a `.`,
  since owner session tokens from `SessionStore` don't) resolves grant
  tokens on a **separate route prefix**, e.g. `/api/v1/grants/*`, that never
  overlaps with the owner's `/api/v1/events`, `/api/v1/calendars`, etc.
  Concretely: `GET /grants/calendars/{id}/events?start&end` — a read-only
  events-in-range endpoint that checks the resolved grant's `resource_id`
  matches the requested calendar and `scope` includes `read`, then calls the
  **existing** `event_service.list_events` with the *owner's* `user_id`
  (looked up from the grant) — reusing existing read logic, not
  duplicating it.
- **Owner-side management API** (existing owner auth,
  `SessionContext`-gated, alongside `/calendars`, `/events`):
  `POST /event-acl` (create + returns the one-time secret),
  `GET /event-acl` (list the owner's active grants, never re-exposes
  secrets), `DELETE /event-acl/{id}` (revoke).
- **Frontend**: a Settings sub-panel listing active grants with revoke
  buttons, and a "Create agent grant" flow that displays the generated
  credential exactly once (same UX pattern as the vault's key-file download
  — shown once, gone if you didn't save it).

## Non-goals

- **No write scope in this spec.** `scope="schedule"` in the data model
  above is aspirational plumbing for a future spec — this spec only
  implements and enforces `scope="read"`. Letting a grantee create/modify
  events is a materially bigger trust boundary (an agent could double-book
  or corrupt the calendar) and deserves its own spec once read-only grants
  are proven.
- **No retrofit of existing owner routes.** `/api/v1/events`,
  `/api/v1/calendars`, etc. are untouched — they remain exactly as
  owner-only as they are today. This spec is purely additive.
- **No household/coaching (human grantee) UI** — `grantee_type` is modeled
  to allow it later, but `"human"` is not implemented or exposed in this
  spec; only `"agent"`.
- Does not change how the *existing* `ai_sessions` flow calls the LLM
  provider (that's server-to-provider, not provider-to-server, and stays
  exactly as implicitly trusted as it is today) — this spec is about
  something *external* authenticating *into* Timebox, which nothing does
  yet.

## Acceptance criteria

- [ ] Creating a grant returns a secret exactly once; the stored row never
      contains it in retrievable form (verifier-only, same live-DB-read
      test pattern as `test_titles_encrypted_at_rest`).
- [ ] A valid, unexpired, unrevoked grant token can call
      `GET /grants/calendars/{id}/events` and see exactly that calendar's
      events in range — verified against the same data the owner sees via
      the normal authenticated route.
- [ ] A grant token cannot access any `resource_id` other than the one it
      was scoped to (403), cannot access `/api/v1/*` owner routes at all
      (401, wrong auth namespace), and stops working immediately after
      `DELETE /event-acl/{id}` or once `expires_at` passes.
- [ ] Revoking a grant is idempotent and does not affect other grants for
      the same resource.
- [ ] Every existing owner-only route's test suite passes unmodified —
      proves this spec didn't touch the existing trust boundary.
