# Timebox — single-container image: built web SPA served by the FastAPI app.

# Override behind a registry mirror, e.g.:
#   docker build --build-arg NODE_IMAGE=mirror.gcr.io/library/node:22-alpine \
#                --build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.12-alpine .
ARG NODE_IMAGE=node:22-alpine
ARG PYTHON_IMAGE=python:3.12-alpine

# ---- Stage 1: build the web SPA -------------------------------------------
FROM ${NODE_IMAGE} AS web
WORKDIR /web
COPY apps/web ./
RUN npm ci && npm run build

# ---- Stage 2: API runtime, serves API + built web ---------------------------
FROM ${PYTHON_IMAGE} AS api
WORKDIR /app

COPY apps/api ./apps/api

# cryptography>=42 publishes musllinux_1_2 wheels, so pip installs a prebuilt
# wheel here — do NOT add a Rust/gcc build chain (keeps the image slim, no
# extra toolchain baked into layers).
# Fallback (only if a source build is ever forced on an unsupported arch):
#   apk add --no-cache --virtual .build gcc musl-dev libffi-dev openssl-dev cargo
#   pip install --no-cache-dir .
#   apk del .build
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ./apps/api

COPY --from=web /web/dist /app/web

RUN mkdir -p /app/data \
    && adduser -D -u 1001 timebox \
    && chown -R timebox /app

ENV TIMEBOX_WEB_DIST_DIR=/app/web
ENV TIMEBOX_DATABASE_URL=sqlite+aiosqlite:////app/data/timebox.db

USER timebox

EXPOSE 8787
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
