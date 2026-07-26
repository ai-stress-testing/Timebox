# Plan — 010 Radial Canvas

Implementation of spec.md's core interaction: directly-created timers/
stopwatches, CRUD via click, drag-to-reposition, optional event link.

## Backend

`Models/canvas.py` (`CanvasItem`, `CanvasPositionHistory`, `CanvasAlarm`) →
`Repositories/canvas_repo.py` → `Services/canvas_service.py`, with the pure
elapsed-time arithmetic isolated in `Pipelines/canvas_timer.py`
(`live_elapsed`, `is_timer_complete`) per this repo's "no I/O in pure
pipelines" convention. `Schemas/canvas.py` + `Routers/canvas.py` (prefix
`/canvas`) follow the events/todos routers' try/except-to-HTTPException
shape exactly. Tests: `tests/test_canvas.py` (integration, `unlocked`
fixture) + `tests/test_canvas_timer.py` (pure unit, no DB).

## Frontend

`lib/api-schemas.ts` (canvas section appended at file end),
`Hooks/use-canvas.ts`, `Pages/canvas-page.tsx` (unrouted — see deviations),
`Components/canvas/{radial-canvas,canvas-item-edit-card,canvas-create-bar,
timer-math}.tsx`. `Components/focus/session-timer.tsx`'s `format_elapsed`
was exported (one-line change) so the canvas reuses it rather than writing
a second mm:ss formatter.

## Deviations

- **`move_item` has no dedicated endpoint.** The spec lists `move_item` as
  its own service function writing `canvas_position_history`, but the API
  surface this spec defines has no `/move` route — only a single
  `PATCH /canvas/items/{id}` for "title/duration/position edits". Folded
  move semantics into `edit_item`: when `r`/`theta` are present in the
  patch, it writes a `canvas_position_history` row before applying them.
  Matches the endpoint list exactly; if a dedicated `/move` endpoint is
  wanted later it's a thin wrapper extraction, not a rewrite.

- **No `attention_classes` table (spec 005 dependency).** Spec 005 isn't
  implemented yet in this codebase (no `attention_classes` model/service
  exists). Per spec 010's own note ("functions without it — fall back to
  literals"), `CanvasItemCreate.attention_class` defaults to the plain
  `AttentionClass.active` enum member instead of a per-user configured
  default. Revisit once 005 lands.

- **`CanvasItemOut` carries an extra `elapsed_seconds` field** not in the
  spec's data model. It's the server's `live_elapsed` computed at response
  time — convenient for the first paint before the client's own tick loop
  takes over, and costs nothing (pure function, no extra query). The
  client's local ticking is still the source of truth after that per spec
  ("client-side interval against a server timestamp, not a per-second
  round-trip").

- **Lazy timer completion writes on GET.** Spec 010 explicitly calls for
  this ("checked lazily on read/tick, not via a background poller") — noted
  here only because it means `list_items`/`get_item` can issue a write
  (status flip to `"completed"`) despite being read endpoints. Same
  discipline the rest of the backend already uses (no hidden schedulers).

- **`canvas.router` is not registered in `app/main.py`, and the canvas
  models are not added to `app/Models/__init__.py`.** Both files are a
  shared coordination point across three parallel feature builds landing
  routers at the same time; wiring them is being done centrally in one pass
  afterward (see the build report for the exact lines needed). To make
  `tests/test_canvas.py` exercise the API end-to-end anyway, the test module
  registers `canvas.router` onto the already-constructed `app` singleton at
  import time (guarded, so it's a no-op once `main.py` wires it for real).
  This is a test-only shim; production wiring still happens in `main.py`.

- **`canvas-page.tsx` is not wired into `app.tsx`'s page dispatch, and no
  `"canvas"` `PageKey`/nav item exists yet** — same three-file coordination
  point (`app.tsx`, `Store/ui-store.ts`, `Components/layout/app-header.tsx`),
  reserved for the same central wiring pass. The page was verified working
  standalone (temporarily swapped into the `"calendar"` dispatch slot,
  driven end-to-end with Playwright, then reverted — see build report).

- **New timer/stopwatch default placement is spread, not identical.** The
  spec says "default r/theta the user can drag to adjust" without pinning
  a specific default; a single fixed default (e.g. always `r=0.5,
  theta=0`) makes back-to-back "New timer" / "New stopwatch" clicks stack
  markers exactly on top of each other, hiding all but the last one until
  the user manually drags them apart. `CanvasCreateBar` instead assigns
  each new item `theta = existing_count * 137.5° (golden angle) mod 360`,
  so items land pre-spread around the ring. `r` stays fixed at `0.5`
  (neutral) since `r` carries the "center = urgent" semantic and shouldn't
  be randomized.

- **The edit-card "Save changes" auto-open-on-create was deliberately
  removed.** An earlier draft auto-selected (and opened the edit drawer
  for) every newly created item; live-testing the create flow showed this
  blocks the "New timer, New stopwatch, New timer…" rapid-fire flow the
  spec calls the core interaction, since the drawer overlay intercepts the
  next click. Creation now just appends to the canvas and toasts; opening
  for edit is exclusively a click on the canvas marker, per spec.
