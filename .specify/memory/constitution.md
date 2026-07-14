# Timebox Constitution

Timebox is "Google Calendar but better + 0-surveillance": a chore-optimised calendar
with Monte Carlo scheduling, AI timeboxing, pomodoro tracking, and a radial canvas.
This constitution governs every spec, plan, and line of code in this monorepo.

## Article I — Single User, Zero Surveillance

1. The application serves exactly one user. There are no accounts, no passwords,
   no email, no signup flow.
2. Identity IS the key file. A generated key file (stored wherever the user
   wants — USB stick, password manager, cloud drive) is both the user's id and
   the root of the encryption hierarchy. Upload/point-to the key file to unlock.
3. The server never persists the key. It stores only a one-way verifier
   (HMAC-SHA256 of the secret under a fixed context string). Sensitive user
   content (titles, descriptions, notes) is encrypted at rest with AES-256-GCM
   using a key derived from the key file via HKDF.
4. No telemetry, no analytics, no third-party calls. The only network egress is
   to the user's own local Ollama daemon.
5. Prompt content is never logged or stored — only a SHA-256 hash (per the
   pre-flight Architecture doc).

## Article II — Robust Now, Scalable Later

The prototype runs as two processes (API + web dev server) against SQLite, but
every seam that the full architecture (Postgres, Redis, k3s, vLLM) needs is
already an abstraction:

| Seam | Prototype | Production swap |
|------|-----------|-----------------|
| Relational store | SQLite via async SQLAlchemy 2.0 | PostgreSQL 16 — change `TIMEBOX_DATABASE_URL` |
| LLM runtime | Ollama provider behind `LlmProvider` interface | vLLM provider, same interface (out of scope: this prototype is **Ollama only**) |
| Event bus | In-process async `EventBus` | Redis Streams implementation of same interface |
| Sessions | In-memory `SessionStore` with TTL | Redis-backed implementation of same interface |
| Scheduler compute | Inline async task | Celery worker running the same pure pipeline |

Business logic must not know which side of any seam it is on.

## Article III — Engineering Law (from the pre-flight Code-Standards)

1. Layering: routers → services → repositories. No business logic in routers,
   no SQL outside repositories.
2. NASA-adapted rules: max 60 lines per function; fixed upper bounds on all
   loops and agent iterations; singletons for infrastructure clients created at
   boot; immutable updates; one statement per line; named boolean intermediates.
3. Data-driven dispatch: 3+ case routing uses dispatch maps
   (`dispatch_maps/` in Python, `lib/dispatch-maps/` in TS). No `switch` with
   3+ cases, no nested `if/else` beyond one level.
4. Validation at the boundary: Pydantic v2 `ConfigDict(strict=True)` on every
   API schema; Zod `.safeParse()` on every frontend input and API response.
5. No inline regex (named exports in `patterns.py` / `lib/patterns.ts`), no
   inline crypto (everything in `Core/crypto.py` / `lib/crypto/`).
6. `snake_case` for variables/functions in both languages; `PascalCase` types
   and module directories; `kebab-case` TypeScript filenames.
   **Documented deviation:** Python module *files* use `snake_case.py`, not
   `kebab-case.py` — kebab-case files cannot be imported by the Python runtime.
7. Soft delete only (`deleted_at`), UUID v7 primary keys, partial indexes on
   live-row query paths.
8. Pure-function pipelines: the Monte Carlo scheduler performs no I/O, is
   seeded, reproducible, and iteration-bounded.

## Article IV — Prototype Deviations (explicit, temporary)

- Alembic migrations deferred: schema created via `metadata.create_all` at
  startup. First real deployment must snapshot the schema into an initial
  Alembic migration before any change.
- Single process, no k3s/Vault/Linkerd/Falco: the ops layers of the pre-flight
  Architecture doc apply to production, not this prototype.
- pg_cron purge replaced by an in-app purge task honouring the same 14-day
  hard-purge contract.

## Article V — Spec-Driven Development

Features flow through `specs/<nnn>-<name>/{spec.md,plan.md,tasks.md}`
(spec-kit). No implementation without a spec; no spec without a journey.
Engineering agents in `.claude/agents/` are the default workforce: delegate
scoped chunks (frontend build, scheduler math, reviews) to them often.

## Article VI — Taste

The UI taste is **neural expressive**: dark-first, luminous gradient accents,
expressive display typography, springy micro-motion, organic rounded geometry.
All visual values flow from CSS custom-property tokens — no hardcoded hex or
pixel literals in components.
