# Plan 001 — Technical Plan

## Monorepo layout

```
Timebox/
├── .specify/memory/constitution.md   # project law (spec-kit)
├── specs/001-single-user-prototype/  # this spec
├── .claude/agents/                   # engineering agents (agency-agents style)
├── apps/
│   ├── api/                          # FastAPI service
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── main.py               # app factory + lifespan
│   │   │   ├── Core/                 # config, db, crypto, event bus, sessions, patterns
│   │   │   ├── Models/               # SQLAlchemy ORM (UUIDv7, soft delete)
│   │   │   ├── Schemas/              # Pydantic v2 strict schemas
│   │   │   ├── Routers/              # thin routers → services
│   │   │   ├── Services/             # business logic (+ Llm/ provider abstraction)
│   │   │   ├── Middleware/           # session auth, prompt sanitiser
│   │   │   ├── Pipelines/            # pure functions: Monte Carlo, purge
│   │   │   └── dispatch_maps/        # data-driven dispatch tables
│   │   └── tests/
│   └── web/                          # React 19 + Vite + TS strict + Tailwind
│       └── src/
│           ├── Components/           # kebab-case files, PascalCase exports
│           ├── Hooks/  Pages/  Services/  Store/  Types/
│           └── lib/                  # patterns.ts, crypto/, dispatch-maps/, tokens.css
└── packages/
    └── types/                        # shared API contract (source of truth for both apps)
        └── api-contract.md
```

## Identity & encryption (the key file)

- `POST /api/v1/vault/generate` → creates `{format:"timebox-keyfile", version:1,
  user_id: uuid7, secret: base64url(32 bytes), created_at}`; server stores
  `vault_identity(user_id, verifier=HMAC(secret,"timebox-verifier-v1"))` only.
  Refused once an identity exists (single user).
- `POST /api/v1/vault/unlock` (key file JSON body) → constant-time verifier
  check → opaque random session token (in-memory `SessionStore`, 12h TTL,
  sliding). Response: `{token, user_id, expires_at}`.
- Data key = `HKDF-SHA256(secret, info="timebox-data-v1")`, held only inside
  the session entry; every request decrypt/encrypt uses the session's key.
- Field encryption: `Core/crypto.py` — AES-256-GCM, random 12-byte nonce,
  payload stored `v1:<b64 nonce>:<b64 ciphertext>`. Encrypted columns: event
  title/description/location, chore name, pomodoro/residual notes.
- Losing the key file = data unrecoverable by design. `vault/reset` requires
  explicit `confirm:"ERASE"` and soft-deletes everything.

## Data model (trimmed from DB-Schemas.md, same shapes)

`vault_identity`, `calendars`, `events` (typed columns incl. attention_class,
canvas_event_type, estimated/actual minutes, recurrence basics, residual chain),
`chore_definitions` (n_original/n_current/n_min/n_max, preferred/avoid days,
time window, mc_weight), `schedule_runs` (seed, iterations, score, load
metrics), `chore_occurrences` (confidence_score, load_score, status → event),
`pomodoro_sessions`, `residual_prompts`, `task_residuals`, `ai_sessions`
(prompt_hash only). All tables: UUIDv7 PK, created/updated/deleted_at.

## Canvas event type assignment

`dispatch_maps/canvas_type.py` implements the DB-Schemas rule table:
single event → {active: focus_only, involved: involved_only, passive:
passive_multi}; overlap → frozenset map {active+passive: focus_passive, …}.
Runs on every event create/update using the overlap index query.

## Monte Carlo scheduler

`Pipelines/monte_carlo.py` — pure, seeded (`random.Random(seed)`), no I/O.
Inputs are frozen dataclass snapshots (chores, busy intervals, window, weights).
Each iteration samples candidate slots per due chore occurrence and scores:
preference match + conflict penalty + daily-load balance. Best iteration wins;
output `ScheduledSlot[]` with confidence 0–1. Hard bound
`MAX_MC_ITERATIONS = 10_000` (default 2_000). A lightweight batch-rebalance
pass shifts occurrences from overloaded to underloaded days within n bounds.
Service layer snapshots the DB, runs the pipeline, persists run + occurrences.

## LLM service (Ollama only)

- `Services/Llm/base.py`: `LlmProvider` protocol — `chat(messages, timeout)`.
- `Services/Llm/ollama.py`: httpx async client → `POST {base_url}/api/chat`,
  base URL + model from config (`~/.timebox/config.json` or env), never
  hardcoded. 120s timeout ceiling.
- `Middleware/prompt_sanitiser.py`: strips control chars (keep \n\t), enforces
  max length, blocklist regexes from `Core/patterns.py` (ignore-previous-
  instructions, "you are now", "system:"). Applied inside the AI service path
  so no route can bypass it. Violations → 400 generic, security-event log line
  with hash only.
- `POST /api/v1/ai/timebox` → sanitise → build typed messages (user text never
  concatenated into the system prompt) → Ollama → parse slot proposal →
  persist `ai_sessions` row (hash, model, duration).

## Cross-cutting

- Config: pydantic-settings, `TIMEBOX_` env prefix; SQLite default
  `./data/timebox.db`; strict validation at startup.
- EventBus: `Core/event_bus.py` async in-process pub/sub, Redis-Streams-shaped
  interface (`publish(stream, payload)`, `subscribe(stream)`).
- Logging: structured JSON — timestamp, level, service, trace_id, message;
  trace_id middleware sets header + log context. No PII in logs.
- Purge: `Pipelines/purge.py` hard-deletes soft-deleted rows older than 14
  days, appends to `purge_audit`; runs on startup + daily timer task.
- Tests: pytest + pytest-asyncio + httpx ASGI transport; deterministic, no
  sleeps. Ollama faked via provider stub.

## Frontend (neural expressive)

- Vite + React 19 + TS strict + Tailwind; tokens in `src/lib/tokens.css` as
  CSS custom properties (dark-first, violet→sky gradient accents, glow
  shadows, springy `--ease-spring` motion, `--radius` organic corners).
- TanStack Query for server state, Zustand for UI state, Zod parsing on every
  response (`lib/api-schemas.ts`).
- Pages: Vault (generate/unlock), Week calendar (grid, event create/edit
  drawer), Chores (definitions + run/apply plan), Focus (pomodoro + residual
  prompt), AI timebox drawer.
- No component may hardcode hex/px values; tokens only.

## Delegation (agency-agents)

- `frontend-developer` agent: builds `apps/web` against
  `packages/types/api-contract.md`.
- `backend-architect` agent: consulted for API/service seams.
- `ai-engineer` agent: Ollama provider + sanitiser hardening.
- `code-reviewer` agent: pre-push review of the full diff.
