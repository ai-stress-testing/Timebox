# Tasks 001 — Ordered breakdown

## Phase 0 — Scaffold
- [x] T001 Monorepo layout, constitution, spec, plan, agent definitions
- [x] T002 Shared API contract (`packages/types/api-contract.md`)

## Phase 1 — Backend foundation
- [x] T010 Config (pydantic-settings), structured logging, trace_id middleware
- [x] T011 Async SQLAlchemy engine (SQLite default, URL-swappable), UUIDv7 +
      soft-delete base model, startup create_all
- [x] T012 `Core/crypto.py`: HKDF, AES-256-GCM field codec, HMAC verifier
- [x] T013 `Core/sessions.py`: in-memory TTL SessionStore (interface Redis-ready)
- [x] T014 Vault service + router: generate / unlock / status / reset
- [x] T015 Session auth middleware (bearer → user_id + data key)

## Phase 2 — Calendar core
- [x] T020 Calendar + Event models, strict schemas, repositories
- [x] T021 Canvas-type dispatch map + overlap detection
- [x] T022 Events router (CRUD, range query), default calendar bootstrap

## Phase 3 — Chores + Monte Carlo
- [x] T030 Chore models + CRUD
- [x] T031 Pure MC pipeline (seeded, bounded) + batch rebalance
- [x] T032 Schedule service: snapshot → run → persist → apply-to-events

## Phase 4 — Pomodoro + residuals
- [x] T040 Pomodoro sessions (start/stop, break rule dispatch)
- [x] T041 Residual prompts → task residuals flow

## Phase 5 — AI (Ollama only)
- [x] T050 LlmProvider protocol + Ollama implementation (config-driven)
- [x] T051 Prompt sanitiser + patterns + security logging (hash only)
- [x] T052 `/ai/timebox` slot proposal + `ai_sessions` persistence

## Phase 6 — Frontend (delegated: frontend-developer agent)
- [x] T060 Vite/React/TS/Tailwind scaffold + neural-expressive tokens
- [x] T061 Vault page (generate/download, drop-to-unlock)
- [x] T062 Week calendar grid + event drawer
- [x] T063 Chores page (definitions, run plan, apply)
- [x] T064 Focus page (pomodoro, residual prompt) + AI timebox drawer

## Phase 7 — Verify & ship
- [x] T070 Backend pytest suite (vault, canvas rules, MC determinism, sanitiser)
- [x] T071 `tsc --noEmit` + production build clean
- [x] T072 code-reviewer agent pass, fixes applied
- [x] T073 Commit + push `claude/timebox-monorepo-prototype-n0jpsy`
