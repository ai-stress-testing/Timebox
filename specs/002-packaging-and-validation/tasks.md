# Tasks 002 — Packaging & Boundary-Validation Hardening

Worker = Sonnet. Implement in order; each task is self-contained. Conventions
(constitution Art. III): `snake_case`, dispatch maps for 3+ cases, ≤60-line
functions, no inline regex/crypto, Zod `.safeParse()` on every input + response.

## Boundary-validation audit

Every user-editable surface in `apps/web/src` + the api-client. "Wrapped" = a
`Number()`/`trim()` fed into a Zod `.safeParse()` before the body is built (Zod
rejects `NaN`, so those are safe).

| # | Surface | Current validation | Verdict |
|---|---------|--------------------|---------|
| 1 | `Components/vault/read-keyfile.ts` | `keyfile_schema.safeParse` | OK |
| 2 | `Components/calendar/event-draft.ts` `build_event_create` | `event_create_schema.safeParse` (Number wrapped) | OK |
| 3 | `Components/calendar/event-drawer.tsx` create+edit | both call `build_event_create` | OK |
| 4 | `Components/calendar/event-form.tsx` | presentational only, no body built | OK |
| 5 | `Components/chores/chore-form.tsx` `build_chore` | `chore_create_schema.safeParse` (Number wrapped) | OK |
| 6 | `Components/chores/plan-panel.tsx` `handle_plan` | raw `{window_days: Number()||14, seed: Number(seed)}`, **no** safeParse; `schedule_run_create_schema` exists but unused | **GAP** |
| 7 | `Components/focus/event-picker.tsx` | `on_start(sel, Number(minutes)||25)`, no safeParse, no start schema | **GAP** |
| 8 | `Components/focus/finish-form.tsx` `handle_finish` | `Number(meaningful)`, no safeParse, no finish schema | **GAP** |
| 9 | `Components/focus/residual-prompt-card.tsx` | `build_body(Number(remaining)||null)`, dispatch-map guards >0 but no zod | **GAP** (minor) |
| 10 | `Components/ai/timebox-drawer.tsx` `handle_propose` | `timebox_request_schema.safeParse` | OK |
| 11 | `Components/ai/timebox-drawer.tsx` `handle_accept` | builds event create with `Number(minutes)||undefined`, bypasses `event_create_schema` | **GAP** |
| 12 | `Services/api-client.ts` `api_request` response | `schema.safeParse` always | OK |
| 13 | `Services/api-client.ts` `api_request_empty` (204) | no body parse, correct | OK |
| 14 | `Services/api-client.ts` `extract_detail` envelope | `detail_schema = z.object({detail: z.string()})`; FastAPI 422 returns `detail` as an **array**, so safeParse fails → generic message | **GAP** (minor) |

Hooks in `Hooks/*.ts` are typed but do not re-validate bodies — validation MUST
live at the build site (tasks below).

---

## T101 — Shared coercion helpers + missing input schemas  *(foundation; blocks T102–T106)*
File: `apps/web/src/lib/api-schemas.ts`. Add near the top (after imports):
```ts
export const positive_int_from_input = z.coerce.number().int().positive();
export const nonneg_int_from_input = z.coerce.number().int().nonnegative();
```
`z.coerce` turns the form's string state into a number; `"abc"→NaN` and `""→0`
both fail (`positive()`/`int()`), closing the `NaN`-reaches-API hole. Then add:
```ts
export const pomodoro_start_schema = z.object({
  event_id: z.string().min(1),
  intended_minutes: positive_int_from_input,
});
export type PomodoroStart = z.infer<typeof pomodoro_start_schema>;

export const pomodoro_finish_input_schema = z.object({
  completion_flag: z.boolean(),
  meaningful_minutes: nonneg_int_from_input.optional(),
  notes: z.string().optional(),
});
export type PomodoroFinishInput = z.infer<typeof pomodoro_finish_input_schema>;

export const prompt_respond_body_schema = z.object({
  response: prompt_response_kind_schema,
  remaining_minutes: positive_int_from_input.optional(),
});
```
Keep `schedule_run_create_schema` as-is (already `int().min(1)`).

## T102 — plan-panel uses schedule schema  *(dep: T101)*
File: `apps/web/src/Components/chores/plan-panel.tsx`. In `handle_plan`, replace
the inline object with a `schedule_run_create_schema.safeParse` of a candidate
built from the two string states (window_days always present; seed only when
`seed.trim() !== ""`). On `!success`, `push_toast("Check window/seed.", "danger")`
and return. Pass `parsed.data` to `create_run.mutateAsync`.
Closes: non-numeric seed sending `NaN`, and window_days out of `[1,∞)` reaching the API.

## T103 — event-picker validates intended minutes  *(dep: T101)*
File: `apps/web/src/Components/focus/event-picker.tsx`. Replace the `onClick`
`Number(minutes)||25` with a `positive_int_from_input.safeParse(minutes)`; on
failure show inline error state (mirror `chore-form`'s `error` string) and do not
call `on_start`. Pass `parsed.data` as `intended_minutes`.
Closes: fractional/zero/`NaN` minutes reaching `POST /pomodoro/sessions`.

## T104 — finish-form validates via input schema  *(dep: T101)*
File: `apps/web/src/Components/focus/finish-form.tsx`. Build a candidate
`{ completion_flag, meaningful_minutes?, notes? }` (keep the `=== ""` gates for
the optionals) and run `pomodoro_finish_input_schema.safeParse`; on failure set a
local error and return; pass `parsed.data` to `on_finish`. Update `FinishInput`
to `PomodoroFinishInput` (import from api-schemas) so the type is single-sourced.
Closes: `Number("")`/`NaN` meaningful_minutes reaching the finish endpoint.

## T105 — residual prompt validates remaining minutes  *(dep: T101)*
File: `apps/web/src/Components/focus/residual-prompt-card.tsx`. In `handle_action`,
when the action `needs_minutes`, run `positive_int_from_input.safeParse(remaining)`
and pass the parsed number into `action.build_body`; on failure keep the existing
"Enter the remaining minutes first." toast. Leave `prompt-responses.ts` build_body
signatures unchanged (still guard `> 0`). No new dispatch branch.
Closes: raw `Number()` bypassing zod on the residual path.

## T106 — timebox accept reuses event_create_schema  *(dep: T101)*
File: `apps/web/src/Components/ai/timebox-drawer.tsx` `handle_accept`. Build the
event-create candidate (`title`, `event_type: "task"`, `start_at`/`end_at` from
`propose.data.proposal`, `estimated_minutes` from `minutes` only when non-empty)
and run `event_create_schema.safeParse` before `create.mutateAsync`; on failure
`push_toast(...,"danger")` and return.
Closes: `handle_accept` sending an unvalidated body (title/window/minutes) straight to `POST /events`.

## T107 — api-client error envelope tolerates 422 arrays
File: `apps/web/src/Services/api-client.ts`. FastAPI validation errors return
`detail` as a list of `{loc,msg,type}`. Widen `extract_detail` so both shapes are
handled: keep `detail_schema` for the string case, add a second schema
`z.object({ detail: z.array(z.object({ msg: z.string() }).passthrough()).min(1) })`
and, on match, join the `msg` values with "; ". Keep the generic fallback last.
No inline regex; ≤60 lines. Closes: 422s always showing "Request failed (422)".

---

## T108 — README "System requirements" section
File: `README.md`. Add a `## System requirements` section directly above `## Run it`
with these exact bullets:
- **Python ≥ 3.11** (3.12 recommended) — SQLite ships bundled with CPython, no extra install.
- **Node ≥ 20** and **npm** (bundled with Node).
- **uv** (optional) — fast venv/installer; the setup falls back to `python -m venv` + `pip` if absent.
- **Ollama** (optional) — only for AI timeboxing; the calendar works fully without it. Set `TIMEBOX_OLLAMA_BASE_URL` / `TIMEBOX_OLLAMA_MODEL`.
- **OS**: Linux, macOS, or Windows (WSL2 recommended on Windows).
- **Zero-prerequisite alternative**: Docker — `docker build -t timebox . && docker run -p 8787:8787 timebox`, then open `http://localhost:8787`. To reach a host Ollama add `-e TIMEBOX_OLLAMA_BASE_URL=http://host.docker.internal:11434 --add-host=host.docker.internal:host-gateway`.
Also add a one-line pointer to `./start.sh` (one-command dev start).

## T109 — Backend: serve the built SPA as static files  *(blocks T110 verify)*
Three edits so the API can serve the web dist when present:
1. `apps/api/app/Core/config.py` — add `web_dist_dir: str | None = None` to
   `Settings` (env `TIMEBOX_WEB_DIST`). Comment: "SPA dist; when set+exists, API serves the web app at /."
2. `apps/api/app/main.py` — at the END of `create_app` (after routers + `/health`,
   so API routes keep priority) add, guarded:
   ```py
   web_dir = settings.web_dist_dir
   if web_dir and os.path.isdir(web_dir):
       app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
   ```
   Import `os` and `from fastapi.staticfiles import StaticFiles`. Mount LAST so
   `/api/v1/*` and `/health` win. `html=True` serves `index.html` at `/`.
3. `apps/api/app/Middleware/auth.py` — the middleware currently 401s every path
   not in `_OPEN_PATHS`, which would block `/`, `/assets/*`, etc. Pass the api
   prefix into `__init__` (`api_prefix: str`, wire `settings.api_prefix` from
   `main.py`) and in `dispatch` add a named boolean
   `is_api_path = request.url.path.startswith(self._api_prefix)`; short-circuit
   `if not is_api_path or request.url.path in _OPEN_PATHS or request.method == "OPTIONS": return await call_next(request)`.
   Non-API (static/SPA) paths stay open; every `/api/v1/*` route stays locked.

## T110 — Root Dockerfile (multi-stage, Alpine, non-root)  *(dep: T109)*
File: `Dockerfile` at repo root.
- **Stage 1** `FROM node:22-alpine AS web` — `WORKDIR /web`, copy `apps/web`,
  `npm ci && npm run build` → dist at `/web/dist`.
- **Stage 2** `FROM python:3.12-alpine AS api` — `WORKDIR /app`. Copy `apps/api`,
  then `pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .`.
  **Cryptography on musl**: cryptography ≥ 42 publishes `musllinux_1_2` wheels, so
  pip installs a prebuilt wheel — do **not** add a Rust/gcc build chain (keeps the
  image slim, no secrets/toolchain in layers). Fallback note in a comment: if a
  source build is ever forced (unsupported arch), add a virtual pkg
  `apk add --no-cache --virtual .build gcc musl-dev libffi-dev openssl-dev cargo`,
  pip install, then `apk del .build`.
- Copy web dist: `COPY --from=web /web/dist /app/web` and set `ENV TIMEBOX_WEB_DIST=/app/web`.
- Writable data dir + non-root: `RUN mkdir -p /app/data && adduser -D -u 1001 timebox && chown -R timebox /app`; `USER timebox`. Set `ENV TIMEBOX_DATABASE_URL=sqlite+aiosqlite:////app/data/timebox.db`.
- `EXPOSE 8787`; `CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8787"]`.
- Pin base images by the tags above; no `.env`/keys copied (see .dockerignore).

## T111 — .dockerignore
File: `.dockerignore` at repo root. Contents:
`node_modules`, `**/node_modules`, `.venv`, `**/.venv`, `__pycache__`, `**/__pycache__`,
`*.pyc`, `*.egg-info`, `**/*.egg-info`, `.pytest_cache`, `.git`, `.gitignore`,
`**/dist`, `data`, `**/data`, `.env`, `**/.env`, `specs`, `.claude`, `.specify`, `**/tests`.
Keeps secrets, local venvs, the SQLite db, and build caches out of the context.

## T112 — start.sh (one-command dev)
File: `start.sh` at repo root, `#!/usr/bin/env bash`, `set -euo pipefail`.
Behavior contract:
- **Prereq checks** with actionable messages, exit 1 on failure: `python3` present
  and `>= 3.11` ("Install Python ≥ 3.11 — see README System requirements");
  `node` present and `>= 20`; `npm` present. Use `command -v` + version parse
  (no inline regex golfing; simple `cut`/`sort -V` comparison).
- **First-run API setup**: if `apps/api/.venv` missing → prefer
  `uv venv apps/api/.venv && uv pip install -p apps/api/.venv/bin/python -e "apps/api[.dev]"`;
  if `uv` absent, fall back to `python3 -m venv apps/api/.venv` +
  `apps/api/.venv/bin/pip install -e "apps/api[dev]"`. Print which path was taken.
- **First-run web setup**: if `apps/web/node_modules` missing → `(cd apps/web && npm install)`.
- **Start both**: API `apps/api/.venv/bin/uvicorn app.main:app --port 8787` (cwd
  `apps/api`) in background → capture `api_pid`; web `npm run dev` (cwd `apps/web`,
  :5173) in background → capture `web_pid`. Print `Open http://localhost:5173`.
- **Clean shutdown**: `trap 'kill "$api_pid" "$web_pid" 2>/dev/null; wait 2>/dev/null'
  INT TERM EXIT`; `wait` on the two PIDs so Ctrl-C tears both down.
- Must pass `bash -n start.sh`.

---

## Dependency order
T101 → {T102–T106}. T107, T108, T111, T112 independent. T109 → T110.

## Verification checklist (Fable)
- [ ] `cd apps/web && npm run build` clean (tsc --noEmit + vite build).
- [ ] Every GAP row (6, 7, 8, 9, 11, 14) now routes through a zod `.safeParse`; no
      raw `Number()` reaches a hook. Grep `Number(` in `Components/**` — each hit is
      inside a safeParsed candidate.
- [ ] `cd apps/api && .venv/bin/python -m pytest` green (config/main/auth changes).
- [ ] `docker build -t timebox .` succeeds; `docker run -p 8787:8787 timebox` boots.
- [ ] In-container: `GET /health` → 200; `GET /` serves SPA `index.html`;
      `/api/v1/vault/status` → 200 (open); locked `/api/v1/events` → 401; vault
      generate → unlock round-trips.
- [ ] `bash -n start.sh` clean; from a clean checkout it installs deps, starts both
      servers, prints the URL, and Ctrl-C stops both.
- [ ] README `## System requirements` present with all bullets + Docker path.
