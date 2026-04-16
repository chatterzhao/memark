# MemPalace Usage Research

Date: 2026-04-08

This report is based on actual command execution against `mempalace` plus direct inspection of generated palace data. It intentionally replaces earlier inference-heavy conclusions.

## Tested Surfaces

- CLI help: `init`, `mine`, `search`, `compress`, `wake-up`, `split`, `status`
- Project ingest
- Conversation ingest
- Search filters: `--wing`, `--room`
- `wake-up --wing`
- `compress --dry-run` and actual `compress`
- MCP server: `initialize`, `tools/list`, `mempalace_status`, `mempalace_search`
- MCP write tools on a copied palace: duplicate check, add drawer, delete drawer, diary, KG add/query/timeline/stats
- Palace on-disk structure via `chroma.sqlite3`

## Test Corpus

Project corpus:

- `/tmp/mempalace-usage/project-alpha/src/auth.py`
- `/tmp/mempalace-usage/project-alpha/src/billing.py`
- `/tmp/mempalace-usage/project-alpha/docs/adr-auth.md`

Conversation corpus:

- `/tmp/mempalace-usage/chats/mega.txt`

Palaces:

- `/tmp/mempalace-project-palace`
- `/tmp/mempalace-convo-palace`
- `/tmp/mempalace-convo-general-palace`
- `/tmp/mempalace-codex-palace-1`

## What Worked

### 1. Standard project flow is real

Using source checkout import path, `init` and `mine` worked for a normal project path.

Observed result:

- project mine: `3 files`, `3 drawers`
- rooms detected in practice: `src`, `documentation`
- `status` showed `project_alpha -> src: 2, documentation: 1`
- `wake-up --wing project_alpha` produced a short, useful L1 summary
- `search "Clerk" --wing project_alpha --room documentation` returned the ADR text cleanly

### 2. Conversation ingest is genuinely a different mode

`mine --mode convos` behaved differently from project ingest.

Observed result:

- exchange mode: `1 file`, `2 drawers`, room `technical`
- general extraction mode: `1 file`, `1 drawer`, room `decision`

That difference matters: MemPalace is not just storing files, it has distinct ingestion strategies for project files and chat exports.

### 2.1. Codex project sessions are the correct primary input, not `history.jsonl`

Two different Codex data surfaces were inspected:

- `~/.codex/history.jsonl`
- `~/.codex/sessions/YYYY/MM/rollout-*.jsonl`

Practical conclusion after checking both:

- `history.jsonl` is a flattened global index of user text keyed by `session_id` and timestamp
- it does not carry project path or `cwd`
- it is useful as a coarse cross-session log, but not as the primary project-memory source
- the real project-aware session store is `~/.codex/sessions/**/*.jsonl`

Actual session files contain a first-line `session_meta` record with project context, including:

- `payload.id`
- `payload.cwd`
- `payload.timestamp`

For this repository, filtering `~/.codex/sessions/**/*.jsonl` by:

- `session_meta.payload.cwd == <repo-root>`

produced `11` session files, which were copied into:

- `/tmp/mempalace-codex-memark-sessions`

and mined with:

- `mine /tmp/mempalace-codex-memark-sessions --mode convos`

Observed result:

- `11 files`, `216 drawers`
- wing: `mempalace_codex_memark_sessions`
- rooms: `technical`, `planning`
- `status` showed a single wing for only the `memark` project sessions
- `wake-up --wing mempalace_codex_memark_sessions` returned chunked text from those project-specific session files
- `source_file` metadata pointed to individual rollout files, not the global `history.jsonl`

Direct SQLite inspection of `/tmp/mempalace-codex-palace-1/chroma.sqlite3` showed:

- `ingest_mode=convos`
- `extract_mode=exchange`
- `source_file=/private/tmp/mempalace-codex-memark-sessions/rollout-...jsonl`
- `room=technical` or `planning`
- `wing=mempalace_codex_memark_sessions`
- `chroma:document` stored chunked session text, including `session_meta` records in some chunks

This is the important practical finding for Codex integration:

- Codex sessions are project-separable in practice
- the correct project-level source is `~/.codex/sessions/**/*.jsonl`
- `history.jsonl` should not be treated as the default project-ingest surface
- MemPalace still stores chunked raw conversation/session text, not curated project knowledge

### 2.2. `convos` re-ingest is path-based, not update-aware

A minimal repro was run against `mempalace 3.0.0`:

1. create one `rollout-a.jsonl`
2. run `mempalace --palace <tmp> mine <chat_dir> --mode convos`
3. append more messages to the same file path
4. run the same `mine --mode convos` command again

Observed result:

- first run: `Files processed: 1`, `Drawers filed: 1`
- second run: `Files processed: 0`, `Files skipped (already filed): 1`
- SQLite still contained only the first `source_file`

Practical conclusion:

- `MemPalace convos` currently treats `source_file` as the decisive dedupe surface
- it does not re-ingest same-path session growth the way normal project `mine` uses `source_mtime`
- any bridge that needs correct `Codex resume` handling must compensate before `MemPalace`

This is exactly why `MemArk` now writes updated sessions as immutable staging snapshots instead of rewriting the same staging path.

### 3. Compression exists, but real gains depend on corpus size

Observed dry-run results:

- project palace: `118t -> 93t`, about `1.3x`
- convo palace: `108t -> 66t`, about `1.6x`

Actual `compress` also wrote compressed drawers back into the palace metadata.

Conclusion:

- compression is real
- on small corpora it is modest
- claims of dramatic reduction should not be repeated as a default assumption

### 4. MCP surface is much broader than CLI help suggests

Actual `tools/list` exposed not only read/search tools, but also:

- taxonomy tools
- duplicate checking
- drawer add/delete
- diary write/read
- knowledge graph add/query/invalidate/timeline/stats
- room graph traversal/tunnel stats

These were not just visible in source. They were exercised on a copied palace:

- duplicate check found the ADR as a similar match with similarity `0.732`
- `mempalace_add_drawer` successfully added a `notes` drawer
- `mempalace_delete_drawer` removed it again
- `mempalace_diary_write` created a diary entry under `wing_codex/diary/research`
- `mempalace_kg_add` and `mempalace_kg_query` stored and returned `AuthService -> depends_on -> Clerk`

### 5. The palace is not an easy raw-text folder

Actual palace top level looked like this:

- `chroma.sqlite3`
- vector segment directories like `<uuid>/data_level0.bin`

The most usable top-level exposed data for downstream tooling was not a markdown file tree. It was `embedding_metadata` inside `chroma.sqlite3`.

Actual metadata fields observed:

- `chroma:document`
- `wing`
- `room`
- `source_file`
- `filed_at`
- `chunk_index`
- `ingest_mode`
- `extract_mode`
- `compression_ratio`

This is the most important bridge finding from actual use:

- for downstream extraction, the highest-value practical surface is metadata plus stored drawer text from Chroma
- not the ANN binary files
- not a top-level human-readable palace export
- in the Codex session test, that meant `ingest_mode`, `extract_mode`, `wing`, `room`, `source_file`, `filed_at`, and `chroma:document`

## What Broke Or Mismatched

### 1. Installed `init` path is buggy

Installed `mempalace 3.0.0` did not successfully complete non-interactive `init --yes`.

Workaround that did work:

- run from source with `PYTHONPATH=~/Downloads/code/my-memark/mempalace`

This means a skill or automation layer should not blindly trust installed `init` on this version.

### 2. `split` help and actual behavior mismatched

Observed:

- help advertises `mempalace split <dir>`
- actual parser rejected the positional path on the installed wrapper
- `--source` at wrapper level also did not work

This is a real contract mismatch.

### 3. MCP CLI help surface is poor

Running `python -m mempalace.mcp_server --help` did not provide a useful top-level capability summary in practice; it mostly started the server path.

### 4. Some direct import usage hit database locking

When importing MCP helpers directly against an already-used palace, some attempts failed with `sqlite3.OperationalError: database is locked`.

On a copied palace, the same write and KG operations succeeded.

Implication:

- MemPalace is operationally usable
- but bridge code should expect locking and treat the live palace as a concurrent store, not a static file dump

## Best Standard Usage After Real Testing

For project memory:

1. `init`
2. `mine <project_dir>`
3. `search` and `wake-up`
4. optional `compress`
5. MCP for AI-side read/write workflows

For chat memory:

1. normalize or split chat exports if needed
2. `mine <chat_dir> --mode convos`
3. search/wake-up over the same palace

For Codex specifically:

1. scan `~/.codex/sessions/**/*.jsonl`
2. read the first `session_meta` line and filter by `payload.cwd`
3. copy only the target project's session files into a dedicated input directory
4. run `mine <that_dir> --mode convos`
5. treat the result as raw process memory, not as already-promoted project knowledge

For AI integration:

- CLI alone is enough for a human operator
- MCP is the real leverage point if the goal is an agent that verifies memory before speaking

## What MemPalace Is Best At

- storing verbatim memory
- recovering exact text later
- giving AI a short wake-up context
- separating project ingest from conversation ingest
- attaching a protocol layer on top of storage via MCP

## What It Is Not Good At

- serving as a ready-made Graphify corpus
- exposing a stable public incremental export API like "all updates after timestamp X"
- acting like a browsable project wiki by itself

## Bridge Implication For MemArk

After actual use, the most defensible extraction point is:

1. read Chroma drawer text plus metadata
2. filter to project-relevant wings and rooms
3. promote selected drawers into Graphify-ready markdown

Do not claim:

- that MemPalace already exposes a stable `since` API
- that the palace itself is directly Graphify-ready
- that the bridge should read ANN binary files
- that `history.jsonl` is the correct project-memory source for Codex
