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
- **Ollama** (optional) — only for AI timeboxing; the calendar works fully without it. See [Running Ollama](#running-ollama-the-ai-provider) below.
- **OS**: Linux, macOS, or Windows (WSL2 recommended on Windows).
- **Zero-prerequisite alternative**: Docker — `docker build -t timebox . && docker run -p 8787:8787 timebox`, then open `http://localhost:8787`. To reach a host Ollama from the container, see [Docker + Ollama networking](#docker--reaching-your-hosts-ollama) — or skip the manual flags entirely with `docker compose up --build`.

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

## Running Ollama (the AI provider)

Ollama powers the optional **AI timebox** feature. Everything else works without
it. Copy-paste to get it running for this instance:

```bash
# 1. Install Ollama — https://ollama.com/download
#    macOS / Windows: download the app.   Linux:
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull the model Timebox defaults to (or any model you prefer)
ollama pull llama3.2

# 3a. Timebox running from source (API on your host) — defaults just work:
ollama serve                       # serves http://localhost:11434

# 3b. Timebox running in Docker (API in a container) — Ollama MUST listen on
#     all interfaces, or the container gets "connection refused":
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# 4. Verify the daemon and model respond
curl http://localhost:11434/api/tags
```

Then point Timebox at it — either way works:

- **In the app**: open **Settings (⚙)**. Provider is already *Ollama*; set **Base
  URL** (`http://localhost:11434`) and **Model** (e.g. `llama3.2`). The header's
  status dot turns green when it connects. (You can also pick a different local
  provider here — LM Studio or any OpenAI-compatible endpoint.)
- **By env var**: `TIMEBOX_OLLAMA_BASE_URL` (default `http://localhost:11434`)
  and `TIMEBOX_OLLAMA_MODEL` (default `llama3.2`) seed the defaults at startup.

## Docker — reaching your host's Ollama

Inside a container, `localhost` is the *container's* loopback, not your machine,
so two things must line up:

1. **Ollama must listen on all interfaces on the host** — not just `127.0.0.1`.
   Start it with `OLLAMA_HOST=0.0.0.0:11434 ollama serve`. This is the #1 reason
   a container can't reach a host Ollama: by default it binds to loopback only
   and refuses the connection.
2. **The container must be told where the host is** via `TIMEBOX_OLLAMA_BASE_URL`.

**Recommended — `docker-compose.yml`** does both automatically (it sets the
`host.docker.internal` mapping and points `TIMEBOX_OLLAMA_BASE_URL` at it for
you, on Linux and Docker Desktop alike) **and falls back automatically** to a
bundled Ollama sidecar (`TIMEBOX_OLLAMA_FALLBACK_BASE_URL`, default
`http://ollama:11434`) if the host one can't be reached — no env var to swap by
hand, no restart:

```bash
# Ollama already running on the host (see "Running Ollama" above)
docker compose up --build

# Fully self-contained instead — an Ollama sidecar on the compose network,
# no host install needed. One command; the app retries the sidecar
# automatically the moment host.docker.internal is unreachable:
docker compose --profile with-ollama up --build
docker compose exec ollama ollama pull llama3.2
```

If a host Ollama *is* reachable, it's still preferred — the sidecar is a
fallback, not a mode switch, so nothing changes for people not using
`--profile with-ollama` at all.

The rest of this section is the equivalent by hand with plain `docker run`, for
anyone not using Compose (no automatic fallback there — pass one
`TIMEBOX_OLLAMA_BASE_URL` and mean it, or add
`-e TIMEBOX_OLLAMA_FALLBACK_BASE_URL=<url>` yourself).

**macOS / Windows** (Docker Desktop resolves `host.docker.internal` for you):

```bash
docker run -p 8787:8787 \
  -e TIMEBOX_OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e TIMEBOX_OLLAMA_MODEL=llama3.2 \
  timebox
```

**Linux** (add the host-gateway mapping so `host.docker.internal` resolves):

```bash
docker run -p 8787:8787 \
  --add-host=host.docker.internal:host-gateway \
  -e TIMEBOX_OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e TIMEBOX_OLLAMA_MODEL=llama3.2 \
  timebox
```

**Linux, simplest** — share the host network stack so `localhost` just works
(Linux only; no `-p` needed, the app is on `http://localhost:8787`):

```bash
docker run --network host \
  -e TIMEBOX_OLLAMA_BASE_URL=http://localhost:11434 \
  -e TIMEBOX_OLLAMA_MODEL=llama3.2 \
  timebox
```

**Ollama in its own container** — put both on a user-defined network and address
it by container name (no `OLLAMA_HOST`/host mapping needed):

```bash
docker network create timebox-net
docker run -d --name ollama --network timebox-net -p 11434:11434 ollama/ollama
docker exec ollama ollama pull llama3.2
docker run -p 8787:8787 --network timebox-net \
  -e TIMEBOX_OLLAMA_BASE_URL=http://ollama:11434 \
  -e TIMEBOX_OLLAMA_MODEL=llama3.2 \
  timebox
```

**Troubleshooting** — the header AI dot is red / "provider unreachable":

- On the host: `curl http://localhost:11434/api/tags`. No response ⇒ Ollama
  isn't running, or isn't bound to `0.0.0.0`.
- From the container: `docker exec <id> wget -qO- http://host.docker.internal:11434/api/tags`.
  Fails ⇒ the host mapping (Linux `--add-host`) or `OLLAMA_HOST` is the problem.
- Everything but AI timeboxing works regardless — a red dot never blocks the app.

## Scaling path

Every production seam already exists as an interface (constitution Article II):
SQLite → PostgreSQL 16 via `TIMEBOX_DATABASE_URL`; in-memory sessions → Redis;
in-process event bus → Redis Streams; inline scheduler → Celery task (the
Monte Carlo pipeline is a pure, seeded function); Ollama stays the only LLM —
by design for this prototype.

Source plan: `kebab-lover-xoxo/Timebox` branch `Pre-Flight-Docs`
(Architecture, DB-Schemas, Code-Standards).
