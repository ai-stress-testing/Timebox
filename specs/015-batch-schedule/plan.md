# Plan — spec 015 Batch Schedule

Implemented end-to-end per `spec.md`: backend entry point reusing
`schedule_todo` in a loop, frontend modal with a half-hour grid + task dish,
staged local `assignments` map, single confirm request.

## Deviations

- **Shared "Type" selector for the whole batch, not per-item.**
  `BatchScheduleItem.event_type` is per-item in the schema (as specced), but
  the spec's frontend section never designs a per-task event-type control —
  only explicitly excludes a per-task *attention* selector. Rather than
  invent per-badge type pickers (which the spec's UI description doesn't
  call for) or hardcode `"task"` (which would 422 for any user who deleted
  the seeded "task" type), the modal has one `EventTypeField` at the top of
  the assign step whose value is sent for every item in the batch. Editable
  per-event afterward like attention class already is.
- **Keyboard operability via native `<button>` semantics, not custom
  `onKeyDown` handlers.** The acceptance criteria say "Enter/Space on a task
  arms it, Enter/Space on a slot ... assigns it." Every armable/assignable
  element is a real `<button>`, which already fires `onClick` on Enter and
  Space — added handlers would have double-fired the action. This satisfies
  the criterion with less code, not less behavior.
- **Double-click fallback uses a plain native `<select>`, not an ARIA
  `role="listbox"`.** The spec's prose says "a small dropdown/listbox of
  remaining slot times, keyboard-operable." A native `<select>` is
  keyboard-operable out of the box (arrow keys, type-ahead, Enter to
  commit) and needed zero custom ARIA wiring; a hand-rolled listbox would
  have been more code for identical keyboard behavior in this prototype.
- **On a partial batch failure, the modal returns to the "assign" step**
  (not held on "review") so the still-unassigned todos are visible in the
  dish immediately, ready for the user to fix and retry — matches the
  spec's "so the user can retry without redoing what worked" intent more
  directly than re-showing a review list that's now wrong.
- **Move toast reads "Moved to `<time>`."**, not "moved from 2:00pm" as one
  spec passage phrased it — the more detailed frontend section explicitly
  gives the destination-time wording ("brief toast 'Moved to 2:00 PM'"),
  which is what's implemented.
- **Row selection checkbox shows a visible "Select" label** (not
  visually hidden) next to each to-do's existing "Done" checkbox, to avoid
  changing the shared `CheckboxField` component (used across the app) to
  support visually-hidden labels for this one call site. `aria-label`
  carries the specific-todo text for screen readers regardless.

No schema changes, no new tables, no migrations — matches the spec's "Data
model" section exactly.
