# Spec 011 — Semantic-similarity layer, privacy-preserving (GitHub #23)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** spec 007 (`duration_profiles`) — this spec is explicitly the
fallback for when spec 007 has too few exact-match samples, not a
replacement for it. Spec 006's `title_hash` helper is the join key.

## Scope change from the original issue

The original issue proposed four vector collections. Two of them
(`chronobiology_signal`, `editor_concepts`) depended on the attention/
behavior-monitoring subsystems this backlog pass explicitly moved away from
— `chronobiology_signal` fed spec 022 (Chronobiology profiles, closed
not-planned) and `editor_concepts` fed the now-deleted Editor Engine issue.
Building either collection today would mean writing a persistence layer for
data no other spec produces. This spec covers only the two collections that
still have a real upstream: `pomodoro_patterns` (duration estimation, feeds
spec 007) and `canvas_behavior` (layout analysis, feeds spec 010). If the
attention-monitoring direction comes back, the other two collections are a
straightforward follow-up spec, not a redesign.

## The privacy problem, and the design decision

Vector similarity search over event/task *labels* normally means embedding
the plaintext ("write quarterly report", "walk the dog") through a language
model and storing those vectors so a brand-new label can find its nearest
neighbors. That means the embedding process — and the vector store — sees
and potentially retains a semantic fingerprint of real, sensitive user
content. That's a real tension with Article I (zero surveillance, field
encryption at rest): even though this app is Ollama-only and local, "local"
doesn't mean "fine to store forever" — a vector database full of
task-content embeddings is a re-identification risk the encrypted SQL
columns were specifically built to avoid.

**Decision: this spec never embeds label text at all.** Instead of semantic
(meaning-based) similarity, it uses **behavioral similarity**: every vector
is built from the same normalized `title_hash` (spec 006) as its identity,
and its embedding is a small numeric feature vector assembled entirely from
already-computed, non-linguistic signals:

```
feature_vector = [
  duration_profiles.total_mean (normalized),
  duration_profiles.meaningful_mean (normalized),
  dow_total_mean[0..6] (the 7 day-of-week buckets, normalized),
  attention_class (one-hot: active/involved/passive),
  canvas_event_type (one-hot),
  is_chore (0/1),
  is_recurring (0/1),
]
```

This is literally what the prompt describing this decision asked for: the
system reasons over "hash X behaves like hash Y" (similar duration, similar
time-of-day pattern, similar attention class) — never "task A means the same
thing as task B." Two completely unrelated activities that happen to take
the same amount of time on the same days will cluster; that's a **known,
accepted tradeoff**, not a bug — it's the cost of never letting content
touch the vector layer. A `chore_completions.soil_state` or
`session_feedback.inferred_performance` field (from other specs, if built)
can join in the same way — numeric/categorical signal only, never text.

**Explicit limitation, stated honestly**: this cannot help with true
cold-start — a title with *zero* prior occurrences has no feature vector
yet (nothing to compute `duration_profiles.total_mean` from), so "estimate a
brand-new task's duration from similar past tasks" only starts working after
spec 007 has *some* signal for it, at which point exact-match (spec 007
directly) is usually already good enough and this layer's marginal value is
for **sparse-but-nonzero** history, not true first-occurrence estimation.
That's a real gap in the original issue's ambition; closing it fully would
require either (a) accepting plaintext exposure to a local embedding step
(a call the constitution's "zero surveillance" bar leans against, even
locally), or (b) a genuine privacy-preserving text-similarity scheme
(locality-sensitive hashing over n-grams, or homomorphic/ZK-style
comparison) — real research-grade work, not a weekend implementation. Flag
as a future spec if first-occurrence estimation becomes a priority; don't
block this spec on solving it.

## Data model

ChromaDB is an external process/library, not a SQL table — but it needs a
durable pointer from the relational side:

```
semantic_vectors   -- SQL-side index, not the vectors themselves
  id                UUIDv7 PK
  user_id           String(36)
  collection        String(32)   -- "pomodoro_patterns" | "canvas_behavior"
  key_hash          String(64)   -- title_hash for pomodoro_patterns; event_id-derived for canvas_behavior
  chroma_id          String(64)   -- the id ChromaDB was given for this vector
  last_computed_at
```

This table exists so a `title_hash` can be re-resolved to (or invalidated
from) its Chroma vector without querying Chroma just to check existence, and
so the whole collection can be rebuilt from SQL source-of-truth if the
Chroma store is ever wiped (embeddings here are **derived data** —
regenerable from `duration_profiles`/`canvas_items`, never the source of
truth themselves).

## Architecture

- New dependency: `chromadb`, run embedded/local (no server process,
  matches "Ollama only, no third-party calls" — Chroma's own default
  embedding function must be **disabled**; this spec supplies its own
  numeric vectors, it does not want Chroma computing text embeddings
  internally).
- `Services/Llm/` is the wrong home (that's the LLM provider seam) —
  `Services/semantic_service.py`:
  - `build_pomodoro_vector(profile: DurationProfileOut) -> list[float]` —
    pure function, the feature assembly described above.
  - `upsert_pattern(user_id, title_hash, profile)` — called from spec 007's
    `record_event_completion` once a profile has enough samples to be
    worth indexing (e.g. `total_sample_count >= 3` — indexing after one
    sample is noise).
  - `find_similar(user_id, target_hash, k=5) -> list[(title_hash,
    distance)]` — nearest-neighbor query, used by the estimate-prefill path
    as spec 007's fallback when `duration_profiles.total_sample_count` for
    the requested hash is 0 or very low: average the `total_mean` of the
    nearest behaviorally-similar hashes instead of returning "no estimate."
  - Same shape for `canvas_behavior` off spec 010's `canvas_items`
    (`r_mean, theta_mean, alarm_count, canvas_event_type, outcome` per the
    original issue body) once spec 010 exists.
- **No new API surface required** — this is purely a backend fallback
  inside the existing estimate-prefill path (spec 006/007's consumers),
  not a user-facing feature with its own endpoint.

## Non-goals

- No semantic/NLP embedding of any title, note, or description text,
  anywhere, ever, in this spec — see the privacy decision above. If a
  future spec genuinely needs text-semantic search, it needs its own
  explicit privacy review, not a quiet extension of this one.
- `chronobiology_signal` and `editor_concepts` collections: out of scope,
  see "Scope change" above.
- No cross-user corpus (obviously, single-user app, but stated for the
  record — every vector is tagged and queried strictly within `user_id`).

## Acceptance criteria

- [ ] `build_pomodoro_vector` is a pure, unit-tested function — given a
      `DurationProfileOut`, produces a deterministic numeric vector with no
      DB or network access.
- [ ] A live test proves no plaintext title, description, or note text ever
      reaches the Chroma collection — only `title_hash`/`event_id`-derived
      keys and numeric feature vectors (inspect what's actually passed to
      the Chroma client in the test, not just the SQL side).
- [ ] `find_similar` on a hash with 3+ samples of its own returns itself as
      the nearest neighbor (distance ≈ 0) and ranks genuinely
      duration/pattern-similar hashes above dissimilar ones in a
      constructed test fixture.
- [ ] A hash with zero samples returns an empty result (proves the
      documented cold-start limitation is enforced, not silently
      papered over with a bad guess).
- [ ] Deleting a user's data (vault reset) removes their vectors from Chroma
      too — no orphaned embeddings survive a user's own data deletion.
