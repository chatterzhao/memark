# Mempal Evaluation

Date: 2026-04-11

This note evaluates `mempal`, `mempalace`, and `graphify` from the perspective of `MemArk`.

It is intentionally not a hype comparison. The question is not which project sounds more advanced. The question is which layer each tool actually covers, where the overlaps are real, and where replacing one with another would create product regressions.

## Sources

- `mempal` site: <https://zhanghandong.github.io/mempal/>
- `mempal` repo: <https://github.com/ZhangHanDong/mempal>
- `MemPalace` rewrite rationale: <https://zhanghandong.github.io/mempalace-book/ch26-why-rewrite-in-rust.html>
- `MemPalace` repo: <https://github.com/MemPalace/mempalace>
- `Graphify` repo: <https://github.com/safishamsi/graphify>
- local research already done in this repository:
  - [`docs/RESEARCH_MEMPALACE_USAGE.md`](<repo-root>/docs/RESEARCH_MEMPALACE_USAGE.md)
  - [`docs/RESEARCH_GRAPHIFY_USAGE.md`](<repo-root>/docs/RESEARCH_GRAPHIFY_USAGE.md)
  - [`docs/AI_CONSUMPTION_MODEL.md`](<repo-root>/docs/AI_CONSUMPTION_MODEL.md)

## Executive Conclusion

`mempal` should be evaluated as a potential replacement candidate for the `MemPalace` layer, not for the `Graphify` layer.

`mempal` and `graphify` are mostly complementary.

For `MemArk`, the realistic near-term options are:

- keep `MemPalace + Graphify` as the current layered model
- or test whether `mempal` can replace the memory layer while still keeping `graphify` for graph compilation and structural navigation

The least defensible option would be assuming `mempal` makes `graphify` unnecessary by default. The sources do not support that conclusion.

## 1. `mempal` vs `mempalace`

### Shared intent

These two tools are solving largely the same product class:

- local-first AI memory
- project and conversation recall
- searchable retained context
- structured taxonomy over stored memory
- MCP-facing access for agents

That overlap is not speculative. The Rust rewrite chapter explicitly says `mempal` came from a deep analysis of `MemPalace`, and that the rewrite exists because the ideas were considered worth preserving while the implementation needed to be more rigorous.

### Where `mempal` is stronger on paper

Based on the official `mempal` site and rewrite chapter, `mempal` makes several explicit design moves:

- single-binary distribution
- SQLite plus `sqlite-vec` storage
- hybrid retrieval: BM25 plus vector search fused with RRF
- simplified taxonomy centered on `Wing` and `Room`
- self-describing protocol for agents
- a smaller, more explicit MCP tool surface
- built-in provenance expectations such as `drawer_id` and `source_file`

That addresses several weaknesses we already observed in actual `MemPalace` use:

- `MemPalace` currently exposes a broader but less obviously bounded surface
- `MemPalace` uses a more complex spatial model, while parts of that hierarchy appear underused
- our own usage research showed `convos` re-ingest is path-based and not truly update-aware
- practical downstream extraction from `MemPalace` ends up depending on `chroma.sqlite3` metadata, not on a simple human-readable storage layer

### Where `MemPalace` is currently stronger in this repository

`MemPalace` is not just a theoretical baseline here. This repository already has real integration work and real usage evidence around it:

- `MemArk` can run `mempalace mine --mode convos`
- we already validated project-specific Codex session ingest
- we already validated `search`, `wake-up`, and several MCP tools against real data
- the bridge logic and dogfood workflow are already built around current `MemPalace` behavior

So even if `mempal` looks cleaner architecturally, that does not automatically make it the better immediate choice for `MemArk`. A replacement would still need to prove:

- Codex session ingest quality
- stable provenance fields
- incremental behavior on repeated ingest
- compatibility with `MemArk`'s promotion model
- operational reliability under our actual dogfood flow

### Objective judgment

`mempal` looks like a serious and well-motivated rethinking of the `MemPalace` memory layer.

But from `MemArk`'s point of view, it is still a replacement candidate, not an already-proven drop-in upgrade.

The correct statement is:

- `mempal` likely overlaps heavily with `MemPalace`
- `mempal` may become a better memory backend than `MemPalace`
- `mempal` has not yet been proven in this repository enough to justify replacing `MemPalace` immediately

## 2. `mempal` vs `graphify`

### Shared surface

There is some overlap, but it is narrower than it first appears.

Both projects talk about:

- project knowledge
- retrieval
- graph-like relationships
- agent-facing tooling

That means both can help an AI answer project questions. But they are not doing the same job.

### `mempal` is primarily a memory system

The official `mempal` page emphasizes:

- historical decision recall
- hybrid memory retrieval
- knowledge graph triples with timeline and stats
- cross-project tunnels
- agent diaries
- MCP tools for status, search, ingest, delete, taxonomy, KG, and tunnels

This is still the shape of a memory operating system for agents.

### `graphify` is primarily a corpus-to-graph compiler

`Graphify` is positioned around turning a folder of:

- code
- docs
- papers
- images
- videos
- links

into a queryable knowledge graph for coding assistants.

That is a different center of gravity:

- ingestion is corpus-oriented rather than memory-oriented
- the output is explicitly a graph artifact and report surface
- it is optimized for structural navigation, code understanding, and corpus compilation

This difference is already reflected in this repository's real experience:

- `MemPalace` is useful for recovering discussion history and session context
- `Graphify` is useful for graph/report-driven code and corpus understanding
- `MemArk` exists because those two strengths do not collapse cleanly into one layer

### Objective judgment

`mempal` does not obviously replace `graphify`.

It may reduce the need for a separate memory backend.
It does not obviously remove the need for:

- corpus graph compilation
- code-structure graphing
- mixed-corpus report generation
- graph-shaped navigation over project artifacts

If `MemArk` removed `graphify` and kept only `mempal`, the likely regression would be losing a dedicated graph compilation layer and collapsing everything back into "searchable memory."

That may be acceptable for some products. It is not obviously acceptable for `MemArk`, whose current value proposition includes preparing a graph-consumable corpus and tracking real graph ingestion proof.

## 3. Should `MemArk` use both, or pick one?

### If forced to pick only one

If the priority is:

- cross-session memory
- historical decisions
- agent recall
- wake-up context

then a memory-first system like `MemPalace` or possibly `mempal` is the better fit.

If the priority is:

- code graph
- corpus compilation
- structured project navigation
- graph artifacts and reports

then `graphify` is the better fit.

### For `MemArk`, one tool is probably not enough

`MemArk`'s current product thesis is not just "remember more" and not just "graph more."

It is:

1. ingest project-related sessions and signals
2. promote selected memory into project knowledge
3. compile that knowledge into a graph-consumable corpus
4. expose stable AI-facing consumption entrypoints

That workflow still maps more naturally to:

- one memory layer
- one graph layer
- `MemArk` as the governance and automation layer between them

So the current objective answer is:

- `mempal` and `MemPalace` are closer to substitutes
- `mempal` and `graphify` are closer to complements
- for `MemArk`, the stronger question is "should `mempal` replace `MemPalace`?" not "should `mempal` replace `graphify`?"

## 4. Practical Recommendation For This Repository

Do not rewrite the architecture around `mempal` yet.

The lower-risk path is:

1. keep `MemPalace + Graphify` as the active product model
2. run a bounded evaluation of `mempal` as a candidate memory-layer replacement
3. compare it against the already documented `MemPalace` behavior using the same inputs

That evaluation should answer:

- can `mempal` ingest the same Codex session corpus cleanly?
- does it preserve source-level provenance well enough for promotion?
- does it support stable incremental ingest semantics?
- does it reduce bridge complexity, rather than just changing it?
- does it improve retrieval quality enough to justify migration cost?

If `mempal` wins those tests, then `MemArk` can consider:

- `mempal` for memory
- `graphify` for graph compilation
- `MemArk` for promotion, orchestration, and AI-facing entrypoints

## 5. Bottom Line

The most objective current verdict is:

- `mempal` is a credible rethink of the `MemPalace` memory layer
- `mempal` is not, by default, a full replacement for `graphify`
- `graphify` still covers a different job: project corpus graph compilation and structural navigation
- for `MemArk`, using both layers still makes more sense than collapsing everything into one tool

If there is only one follow-up worth funding next, it should be:

- a real dogfood-grade `mempal` bakeoff against `MemPalace`

not:

- an architecture rewrite that assumes `graphify` is now redundant
