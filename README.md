# Timebox

**Google Calendar but better + 0-surveillance.**

Single-user monorepo prototype: a chore-optimised calendar with a seeded
Monte Carlo scheduler, AI timeboxing via a local **Ollama** daemon (the only
network egress), pomodoro + residual tracking, and a key-file vault — your
identity and encryption key live in a file *you* keep, wherever you want.

Built spec-driven ([spec-kit](https://github.com/github/spec-kit) layout) with
engineering agents from
[agency-agents](https://github.com/ai-stress-testing/agency-agents) (see
`.claude/agents/`). UI taste: **neural expressive** — dark-first, luminous
gradients, springy motion, all values token-driven.

## How identity works

There are no accounts. On first launch you generate `timebox.key` — a small
JSON file holding your user id (UUIDv7) and a 32-byte secret. Store it on a
USB stick, in your password manager, anywhere. The server keeps only a one-way
HMAC verifier; your event titles, descriptions, notes, and chore names are
AES-256-GCM encrypted at rest with a key derived (HKDF) from that secret.
**Lose the file and the data is unrecoverable — that's the point.**

## Layout

```
apps/api        FastAPI (async SQLAlchemy · SQLite→Postgres seam · Ollama-only LLM seam)
apps/web        React 19 + Vite + TS strict + Tailwind v4 (neural-expressive tokens)
packages/types  API contract (source of truth for both apps)
specs/          spec-kit feature specs (spec / plan / tasks)
.specify/       project constitution
.claude/agents/ engineering agents (backend-architect, frontend-developer, ai-engineer, …)
```

## System requirements

- **Python ≥ 3.11** (3.12 recommended) — SQLite ships bundled with CPython, no extra install.
- **Node ≥ 20** and **npm** (bundled with Node).
- **uv** (optional) — fast venv/installer; the setup falls back to `python -m venv` + `pip` if absent.
- **Ollama** (optional) — only for AI timeboxing; the calendar works fully without it. Set `TIMEBOX_OLLAMA_BASE_URL` / `TIMEBOX_OLLAMA_MODEL`.
- **OS**: Linux, macOS, or Windows (WSL2 recommended on Windows).
- **Zero-prerequisite alternative**: Docker — `docker build -t timebox . && docker run -p 8787:8787 timebox`, then open `http://localhost:8787`. To reach a host Ollama add `-e TIMEBOX_OLLAMA_BASE_URL=http://host.docker.internal:11434 --add-host=host.docker.internal:host-gateway`.

One-command dev start: `./start.sh` boots both the API and web dev server.

## Run it

```bash
# API (http://localhost:8787)
cd apps/api
uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"
.venv/bin/uvicorn app.main:app --port 8787

# Web (http://localhost:5173, proxies /api to :8787)
cd apps/web
npm install
npm run dev

# AI (optional — the calendar works without it)
ollama serve   # config: TIMEBOX_OLLAMA_BASE_URL, TIMEBOX_OLLAMA_MODEL (default llama3.2)
```

Tests: `cd apps/api && .venv/bin/python -m pytest` ·
Web checks: `cd apps/web && npm run build`

## Scaling path

Every production seam already exists as an interface (constitution Article II):
SQLite → PostgreSQL 16 via `TIMEBOX_DATABASE_URL`; in-memory sessions → Redis;
in-process event bus → Redis Streams; inline scheduler → Celery task (the
Monte Carlo pipeline is a pure, seeded function); Ollama stays the only LLM —
by design for this prototype.

Source plan: `kebab-lover-xoxo/Timebox` branch `Pre-Flight-Docs`
(Architecture, DB-Schemas, Code-Standards).
