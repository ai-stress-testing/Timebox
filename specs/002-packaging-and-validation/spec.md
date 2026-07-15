# Spec 002 — Packaging & Boundary-Validation Hardening

**Status:** implemented (prototype)
**Roles:** Fable = orchestrator/macro-planner + verifier · Opus = micro-planner
(granular sub-issues in `tasks.md`) · Sonnet = worker (implementation)

## Macro issue (Fable)

Field report from the user: the app ran on only 1 of 3 machines (missing
prerequisites), the AI path is untested by them, and they want certainty that
every form and every frontend↔backend exchange is schema-validated.

### Deliverable 1 — Boundary validation audit + fixes
Every user-editable form field must pass through zod validation before a
request is built, and every API response must pass through zod `safeParse`
before entering app state. Audit ALL of:
- vault (keyfile read), event create/edit drafts, chore form, plan panel
  (window_days/seed), focus event-picker (intended minutes), finish form
  (meaningful minutes/notes), residual prompt (remaining minutes), AI timebox
  drawer — including every `Number(...)` coercion that currently bypasses zod.
- the api-client response path (including 204 handling) and error envelope.
Backend note: Pydantic strict schemas already gate every route; frontend gaps
are the target. Fix what the audit finds; add nothing speculative.

### Deliverable 2 — README system requirements
A "System requirements" section listing exact prerequisites and versions
(Python ≥3.11, Node ≥20 + npm, uv optional with pip fallback, Ollama optional,
OS notes incl. SQLite bundled with Python), plus the Docker path as the
zero-prerequisite alternative.

### Deliverable 3 — Dockerfile (Alpine)
One multi-stage Dockerfile at the repo root: Node stage builds `apps/web`
dist; `python:3.12-alpine` final stage installs API deps, copies the dist,
and serves BOTH the API and the built web app from one container on one port.
Requires a small backend change: mount the dist as static files in FastAPI
(SPA fallback to index.html) when the directory exists. Non-root user, pinned
base images, no secrets in layers, `.dockerignore`.
Constraint: `TIMEBOX_OLLAMA_BASE_URL` must be overridable so the container
can reach the host's Ollama (`host.docker.internal` / host networking note).

### Deliverable 4 — One-command start script
`./start.sh` at the repo root: checks prerequisites with actionable error
messages, creates the venv + installs deps on first run (uv, pip fallback),
installs npm deps on first run, starts API (:8787) + web dev server (:5173),
prints the URL, and shuts both down cleanly on Ctrl-C. POSIX-friendly bash,
`set -euo pipefail`.

### Acceptance (verified by Fable)
- [x] Backend pytest green; `tsc --noEmit` + `vite build` clean.
- [x] `docker build` succeeds; container boots; `/health` and `/` (web app)
      respond; vault generate→unlock round-trip works inside the container.
- [x] `bash -n start.sh` clean; script starts both processes from a clean
      checkout state and Ctrl-C tears them down.
- [x] Audit table (form → validation path) recorded in tasks.md; every gap
      fixed with zod, none left as `Number()` folklore.
