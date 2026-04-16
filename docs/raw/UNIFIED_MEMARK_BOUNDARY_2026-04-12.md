# Unified MemArk Boundary

Status: archived future-boundary sketch, not current product truth

Why archived:

- it proposes a rewrite into one unified runtime and storage model
- current repository truth still defines `MemArk` as the bridge and governance layer over `MemPalace + Graphify`
- keeping this note in `docs/raw/` preserves the idea without silently changing the active architecture

Original date: 2026-04-12

---

This document defines the product boundary for a new `memark`.

It is not a bridge to `MemPal`, `MemPalace`, or `Graphify`.
It should learn from them, but implement one unified system with one runtime, one storage model, and one CLI-first command surface.

## Product Statement

`MemArk` is a local-first knowledge runtime for AI and humans.

It should:

- ingest project-relevant data
- normalize and enrich it
- store it locally by default
- optionally sync it to a central Postgres instance
- expose the result to AI through CLI, MCP, and structured outputs
- expose the result to humans through reports, views, and later visualization

It should not exist as a glue layer that depends on other runtimes for its core value.

## Core Principles

### 1. Local-first

- default storage is `SQLite`
- startup must not require a server
- a single-user local workflow must be fully useful on its own

Reason:

- reduces startup friction
- keeps personal and project workflows cheap to begin
- matches CLI-first use better than a server-first architecture

### 2. Optional Centralization

- `Postgres` is optional at the beginning
- if PG connection info is configured, local `SQLite` automatically syncs both ways
- centralization must be complete in capability, not a half-broken export mode

Reason:

- a team can start local and adopt centralization later
- the product model stays the same as usage grows

### 3. One Unified Data Model

- do not build one model for local mode and another for centralized mode
- do not build separate product semantics for memory, graph, and reports
- use one object model and multiple materialized views

Reason:

- dual semantics create drift and break sync
- the system needs one durable domain model, not several tool-shaped silos

### 4. CLI First

- every core capability must be operable from CLI
- machine-readable JSON output is first-class
- long-running automation may exist, but the CLI remains the canonical interface

Reason:

- CLI is the most stable surface for AI, scripts, and operators
- GUI can come later without redefining the product

## Must-Have Capabilities

### A. Ingest

`MemArk` should ingest:

- conversation/session logs
- project documents
- markdown notes
- source code repositories
- local filesystem metadata where useful
- manual user entries from CLI
- future external connectors through adapter interfaces

Reason:

- the product must unify memory-like inputs and project artifacts
- code, docs, and conversations must not live in separate product worlds

### B. Normalize

`MemArk` should normalize incoming data into stable internal records such as:

- `source`
- `event`
- `session`
- `artifact`
- `entity`
- `relation`
- `decision`
- `task`
- `view`
- `sync_op`

Reason:

- raw files are not a sufficient application model
- normalized objects are required for query, sync, reporting, and AI consumption

### C. Enrich

`MemArk` should support enrichment pipelines for:

- chunking
- tagging
- deduplication
- entity extraction
- relation extraction
- decision extraction
- summary generation
- provenance preservation
- importance and freshness scoring

Reason:

- ingestion alone only creates storage
- the product value comes from turning raw records into reusable knowledge

### D. Store

`MemArk` should own its own storage model:

- local `SQLite` database
- migration system
- full-text search support
- sync ledger / oplog
- materialized views for consumption
- optional vector index attachment points if needed later

Reason:

- storage is core product infrastructure, not an implementation detail to outsource

### E. Query And Consumption

`MemArk` should expose:

- direct CLI query commands
- JSON outputs for AI chaining
- MCP server surface
- stable human-readable reports
- structured status and diagnostics

Reason:

- the product is only real if humans and AI can consume the processed knowledge directly

### F. Graph And Structure

`MemArk` should implement its own structure layer:

- entity graph
- artifact relationships
- session-to-decision lineage
- code/document/reference links
- graph-aware query and reports

Reason:

- graph value is part of the core product, not an external afterthought
- if graph semantics remain outsourced, the product stays a glue layer

### G. Local Automation

`MemArk` should support:

- explicit one-shot runs
- watch mode where justified
- background daemon mode for users who want it
- resumable jobs
- health/status inspection

Reason:

- some users want manual control
- some users want continuous ingestion and synchronization
- both must use the same core runtime

### H. Sync

When configured with central Postgres, `MemArk` should support:

- bidirectional sync
- sync cursors
- conflict policy
- retryable sync jobs
- device identity
- audit trail for synced operations

Reason:

- optional centralization only works if sync is a real subsystem
- export/import is not enough

### I. Human-Facing Outputs

`MemArk` should produce:

- summaries
- structured lists
- decision digests
- timeline views
- provenance-linked reports
- later, visualization or dashboard views

Reason:

- humans need direct value, not just AI plumbing

## Nice-To-Have Later

These should be allowed later, but not required for v1:

- web UI
- TUI
- embedded vector search
- multi-user permissions model
- remote hosted service
- plugin marketplace
- advanced graph visualization
- mobile companion apps

Reason:

- these increase surface area fast
- they should follow a stable core runtime, not define it

## Explicitly Out Of Scope

### 1. Bridge-First Product Shape

Do not make the new `MemArk` primarily:

- a wrapper around `MemPalace`
- a wrapper around `Graphify`
- a compatibility layer whose main job is passing commands through

Reason:

- that recreates the current architectural limitation
- it gives away the core value to upstream runtimes

### 2. Separate Local Mode And Central Mode Semantics

Do not have:

- a "SQLite product" and a different "Postgres product"
- features that only exist in centralized mode without strong reason

Reason:

- local-first stops being real if local mode is second-class

### 3. GUI-First Development

Do not start with:

- desktop app as the primary product
- dashboard-only administration
- features that require UI before they are operable

Reason:

- it slows down iteration
- it weakens AI and automation use cases

### 4. Unbounded Connector Explosion

Do not begin by integrating everything.

Avoid:

- dozens of source connectors in v1
- vendor-specific deep integrations before the core model is stable

Reason:

- connector sprawl hides whether the core runtime is actually good

### 5. Full Collaboration Platform In V1

Do not start with:

- org-level auth
- ACL-heavy enterprise workflows
- hosted workspace management

Reason:

- these are product-multipliers that distract from the core single-user and small-team runtime

### 6. "Store Everything Forever" Without Governance

Do not define success as unlimited accumulation.

Avoid:

- silent ingestion of all machine noise
- keeping every artifact at equal importance
- skipping provenance and lifecycle rules

Reason:

- knowledge systems fail when noise wins
- governance is part of the product, not optional cleanup

## Recommended V1 Cut

The first real version of unified `MemArk` should include:

- Rust CLI application
- local `SQLite` schema and migrations
- ingest for sessions, docs, markdown, and code repositories
- normalization and provenance tracking
- search and structured query
- summaries, decisions, and report generation
- basic graph/relationship model
- optional daemon mode
- optional Postgres sync with a complete but minimal bidirectional design
- MCP interface backed by the same runtime

It should not wait for:

- polished visualization
- rich collaboration features
- broad connector catalog
- hosted service packaging

## What To Learn From Existing Tools

Learn from `MemPal` / `MemPalace`:

- local-first bias
- memory retrieval value
- operational usefulness of CLI and MCP

Learn from `Graphify`:

- graph-oriented consumption
- structure extraction as a first-class feature
- value of reports plus machine-readable graph outputs

Do not inherit from them:

- split product boundaries
- runtime dependency on external tools
- assumptions that memory and graph must be separate products

## Final Boundary

The new `MemArk` should be:

- one runtime
- one CLI-first application
- one local-first database
- one optional central sync model
- one unified consumption layer for AI and humans

It should not be:

- a bridge
- a wrapper
- a thin orchestrator over other runtimes
- a desktop-first shell around command-line tools
