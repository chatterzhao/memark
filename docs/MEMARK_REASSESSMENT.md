# MemArk Reassessment

Date: 2026-04-08

This reassessment is based on actual use of MemPalace and Graphify in this session. Earlier assumption-driven conclusions should be considered superseded by this document.

## Short Answer

MemArk should continue, but only as a narrow bridge and governance layer.

It should not become:

- a new memory system
- a new graph engine
- a desktop monitor app
- a fake "auto-sync everything" daemon

## What MemArk Can Genuinely Do

### 1. Define the promotion boundary

Actual usage showed:

- MemPalace stores raw drawers well
- Graphify wants a curated corpus boundary

Those are different jobs.

MemArk has real value if it defines:

- what from raw memory is project-worthy
- what stays as memory only
- what becomes promoted project corpus

### 2. Shield users from upstream rough edges

Actual upstream rough edges observed:

- MemPalace installed `init --yes` issue
- MemPalace `split` contract mismatch
- Graphify installed CLI does not expose the full pipeline cleanly
- Graphify watch/serve/svg need extra dependencies
- Graphify hooks can be fragile

A thin bridge that normalizes these rough edges is defensible.

### 3. Produce Graphify-ready markdown from memory metadata

The most useful extraction seam from MemPalace was:

- Chroma metadata
- stored drawer text
- project filters by wing and room
- `filed_at` and `source_file` as provenance

That is enough to produce promoted markdown packages for Graphify.

### 4. Separate raw memory from compiled knowledge

The main architectural value is not "combine memory and graph because 1+1".

It is:

- MemPalace keeps raw, recallable memory
- MemArk promotes and curates
- Graphify compiles and queries

That separation is clean and justified by actual tool behavior.

## What MemArk Must Not Claim

### 1. Not a direct live view over the whole palace

Actual palace storage is Chroma-backed and concurrency-sensitive.

So MemArk should not promise:

- full live mirroring
- safe direct reads of arbitrary internal storage layouts
- timestamp-sync semantics that upstream does not publicly expose

### 2. Not a replacement for using MemPalace well

If a user only needs:

- recall
- wake-up context
- memory search
- diary and fact storage

then MemPalace alone is already useful.

MemArk adds no value there.

### 3. Not a replacement for using Graphify well

If a user already has:

- a curated project corpus
- formal docs
- code graph needs

then Graphify alone can already produce useful structure.

MemArk adds value only when the missing input is raw conversational/project memory that still needs promotion.

### 4. Not a universal automatic sync daemon

There is not enough stable upstream contract yet to justify:

- background database watching
- fully automatic promotion
- guaranteed lossless incremental sync

Those should stay out of scope for now.

## When The Combination Is Worth It

The combination is worth it when all three are true:

1. the project has meaningful chat memory, decisions, or operational notes outside the codebase
2. that memory needs to become reusable project knowledge
3. the resulting promoted corpus is important enough to query as a graph

In that case:

- MemPalace preserves the raw record
- MemArk turns selected memory into stable project documents
- Graphify turns those documents plus code/docs into graph outputs

That is the actual `1 + 1 > 2` cut.

## When The Combination Is Not Worth It

Do not use MemArk just because both upstream tools exist.

It is probably not worth it when:

- there is little or no project memory outside existing docs/code
- the user only wants memory recall
- the user only wants code graph structure
- the graph is small enough that Graphify itself says a graph may not be needed

## Current Product Direction

The correct near-term shape is:

- CLI-first
- promotion-first
- install skill only for upstream tool installation
- no always-on background service
- explicit build/run commands

That aligns with the actual state of both upstream tools better than a plugin-only or desktop-first design.

## Concrete Scope For MemArk

MemArk should do:

- validate promotion input
- map promoted project memory into a stable corpus layout
- keep provenance to source drawers/files
- avoid upstream output loops
- run the compatible Graphify build path for the user's environment

MemArk should not do:

- own long-term memory storage
- own graph storage/query semantics
- claim mixed-corpus semantic Graphify build unless that exact path was actually run

## Product Statement

MemArk is a CLI-first promotion and governance layer between raw project memory and graph-compiled project knowledge.
