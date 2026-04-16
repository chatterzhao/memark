# Graphify Usage Research

Date: 2026-04-08

This report is based on actual CLI execution, direct use of package modules, generated outputs, and real file-change tests. It intentionally distinguishes installed CLI behavior from the richer skill-described workflow.

## Tested Surfaces

- installed CLI help
- `query`
- `benchmark`
- `install --platform`
- `codex install/uninstall`
- `claude install/uninstall`
- `hook install/status/uninstall`
- actual git-hook trigger on commit
- code rebuild path via `graphify.watch._rebuild_code`
- watch loop with code change and doc change
- exports: JSON, report, HTML, Obsidian vault, canvas, GraphML, SVG, Cypher
- serve/query helper path

## Test Corpora

Small mixed corpus:

- `/private/tmp/graphify-usage/raw/code/auth.py`
- `/private/tmp/graphify-usage/raw/code/billing.py`
- `/private/tmp/graphify-usage/raw/docs/notes.md`

Larger real-project corpus:

- `/private/tmp/memark-graphify-research`

## What The Installed CLI Actually Exposes

`graphify --help` exposed a much narrower surface than the skill description suggests.

Actual CLI commands visible:

- `install`
- `query`
- `benchmark`
- `hook install|status|uninstall`
- `claude install|uninstall`
- `codex install|uninstall`
- `opencode|claw|droid|trae|trae-cn install|uninstall`

Important real conclusion:

- installed CLI is mainly integration/query oriented
- it is not a stable public "build any folder" CLI by itself

## What Worked

### 1. Code-graph rebuild is real and useful

Using `graphify.watch._rebuild_code` on the small corpus produced:

- `6 nodes`
- `6 edges`
- `3 communities`

Using the same rebuild path on a copied real project produced:

- `101 nodes`
- `172 edges`
- `8 communities`

It also wrote:

- `graphify-out/graph.json`
- `graphify-out/GRAPH_REPORT.md`

On the real project, the report surfaced usable structure:

- core abstractions
- bridge nodes
- suggested questions
- inferred edge warnings

### 2. Query is genuinely valuable after a graph exists

Actual query against the real project returned graph-centered context around:

- CLI entry points
- `WorkspaceConfig`
- `promote_file()`
- `GraphifyError`
- related tests and type helpers

This is not the same as grep. It is topology-shaped context.

### 3. Benchmark can work on a real project graph

On the real project graph:

- corpus: `5,050 words`
- graph: `101 nodes`, `172 edges`
- average query cost: `~2,810 tokens`
- reduction: `2.4x`

Per-question reductions ranged from `1.9x` to `3.3x`.

So Graphify's compression argument is real on a non-trivial project graph, but not magical.

### 4. Platform integration is a first-class feature

Actually tested:

- `graphify install --platform codex`
- `graphify codex install`
- `graphify claude install`
- `graphify claude uninstall`
- `graphify codex uninstall`

Observed outputs:

- skill installed under a home config path
- project-local `AGENTS.md`
- project-local `CLAUDE.md`
- hook registration in `.codex/hooks.json`
- Claude hook registration in `.claude/settings.json`

This is a real strength: Graphify is designed to alter how coding agents read a repo.

### 5. Watch mode works once dependencies are installed

After installing `watchdog`, actual watch behavior was:

- code file change: automatic rebuild
- doc file change: no rebuild, writes `graphify-out/needs_update` and tells the user to run `/graphify --update`

This is a very important operational finding:

- Graphify already has a governance distinction between code-only automatic refresh and semantic refresh that requires LLM work

### 6. Export surfaces are real

After installing missing extras, actual exports succeeded:

- `graph.json`
- `GRAPH_REPORT.md`
- `graph.html`
- `graph.graphml`
- `graph.svg`
- `cypher.txt`
- Obsidian vault
- canvas file

Observed on the small corpus:

- `9` Obsidian notes written
- SVG generation worked after `matplotlib` install
- Cypher export was immediately usable as import text

## What Broke Or Mismatched

### 1. The "full pipeline" is not exposed cleanly from installed CLI

The skill documentation describes commands like:

- `/graphify <path>`
- `--update`
- `--cluster-only`
- `--graphml`
- `--neo4j`
- `--watch`
- `add <url>`

But the installed CLI help did not expose those as actual top-level commands.

This is the single most important product truth about Graphify after real use:

- its public story is bigger than its installed CLI surface
- the richer path is skill-first and module-driven

### 2. Benchmark is fragile on small graphs

On the tiny corpus, `graphify benchmark` failed with:

- `No matching nodes found for sample questions. Build the graph first.`

The graph did exist. The benchmark samples just did not match well enough.

### 3. Hook automation is not fully robust

Actual commit test after `graphify hook install`:

- commit completed
- hook reported `died of signal 9`

The generated hooks also hardcoded `python3`, which is an environment mismatch risk.

### 4. Optional dependencies are not optional in practice for many claims

Real missing-package failures before installing extras:

- watch: missing `watchdog`
- serve: missing `mcp`
- SVG export: missing `matplotlib`

So any documentation claiming these modes should say "requires extra packages".

### 5. Semantic document extraction was not fully verifiable here

I attempted to exercise the skill-style semantic subagent path twice. Both attempts failed due temporary subagent high-demand errors.

That means this report can confidently validate:

- code graph build
- query
- integration
- watch
- exports

But cannot claim a full end-to-end semantic document extraction run was completed in this session.

## Best Standard Usage After Real Testing

For a codebase:

1. build or rebuild a code graph
2. read `GRAPH_REPORT.md`
3. query `graph.json`
4. optionally install agent integration
5. enable watch/hooks only after checking environment assumptions

For a mixed corpus:

- treat Graphify as a curated corpus compiler, not a magic folder you dump everything into
- expect a richer path when using the official skill than when using bare CLI

## What Graphify Is Best At

- producing structural code graphs
- giving an agent a graph-shaped query surface
- generating multiple downstream knowledge outputs from one graph
- integrating into coding assistant workflows
- highlighting bridge nodes and inference risk in a report

## What It Is Not Good At

- acting as a turnkey universal CLI corpus builder across versions
- guaranteeing robust hooks in every environment
- eliminating the need for corpus curation
- replacing raw memory storage

## Bridge Implication For MemArk

After real use, the strongest Graphify-compatible value from MemArk is not "send everything to Graphify".

It is:

1. create a stable, curated, Graphify-ready corpus boundary
2. separate raw memory from promoted project knowledge
3. avoid feeding Graphify its own outputs or noisy transient material
4. trigger the right Graphify path for the installed environment

Do not claim:

- that every Graphify install supports the same build command
- that code-only fallback equals full semantic graph compilation
