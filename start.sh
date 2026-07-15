#!/usr/bin/env bash
# One-command dev start: checks prerequisites, installs deps on first run,
# starts the API (:8787) and web dev server (:5173), and tears both down on
# Ctrl-C. See README "System requirements" for the manual install path.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

check_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Install Python >= 3.11 — see README System requirements" >&2
    exit 1
  fi
  local version
  version="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  local lowest
  lowest="$(printf '%s\n' "$version" "3.11" | sort -V | head -n1)"
  if [ "$lowest" != "3.11" ]; then
    echo "Python $version found — install Python >= 3.11 — see README System requirements" >&2
    exit 1
  fi
}

check_node() {
  if ! command -v node >/dev/null 2>&1; then
    echo "Install Node >= 20 — see README System requirements" >&2
    exit 1
  fi
  local version
  version="$(node -v | tr -d 'v')"
  local major
  major="$(echo "$version" | cut -d. -f1)"
  if [ "$major" -lt 20 ]; then
    echo "Node $version found — install Node >= 20 — see README System requirements" >&2
    exit 1
  fi
}

check_npm() {
  if ! command -v npm >/dev/null 2>&1; then
    echo "Install npm (bundled with Node) — see README System requirements" >&2
    exit 1
  fi
}

setup_api() {
  if [ -d "apps/api/.venv" ]; then
    return
  fi
  if command -v uv >/dev/null 2>&1; then
    echo "Setting up apps/api venv with uv…"
    uv venv apps/api/.venv
    uv pip install -p apps/api/.venv/bin/python -e "apps/api[dev]"
  else
    echo "uv not found — falling back to python -m venv + pip…"
    python3 -m venv apps/api/.venv
    apps/api/.venv/bin/pip install -e "apps/api[dev]"
  fi
}

setup_web() {
  if [ -d "apps/web/node_modules" ]; then
    return
  fi
  echo "Installing web dependencies…"
  (cd apps/web && npm install)
}

check_python
check_node
check_npm
setup_api
setup_web

(cd apps/api && exec .venv/bin/uvicorn app.main:app --port 8787) &
api_pid=$!

(cd apps/web && exec npm run dev) &
web_pid=$!

# npm/sh interpose between us and vite, so signal the whole descendant tree
# depth-first (bounded — NASA rule 2).
kill_tree() {
  local pid=$1
  local depth=${2:-0}
  if [ "$depth" -ge 10 ]; then
    return
  fi
  local child
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    kill_tree "$child" $((depth + 1))
  done
  kill -TERM "$pid" 2>/dev/null || true
}

shutdown() {
  trap - INT TERM EXIT
  kill_tree "$web_pid"
  kill_tree "$api_pid"
  wait 2>/dev/null || true
}
trap shutdown INT TERM EXIT

echo "Open http://localhost:5173"

wait "$api_pid" "$web_pid"
