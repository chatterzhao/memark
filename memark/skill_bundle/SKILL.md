---
name: memark
description: Use MemArk to keep project conversations flowing into the configured memory tool and promoted project knowledge flowing toward Graphify.
---

# MemArk

Use this skill when the user is working on a software project and you need MemArk to manage project memory and knowledge compilation.

Default behavior:

- treat MemArk as the user-facing entrypoint
- use MemArk commands instead of calling `mempalace` or `graphify` directly when MemArk already covers the operation
- keep conversations isolated by directory path
- let MemArk manage the bridge into the configured memory tool and the prepared corpus for Graphify
- prefer a split consumption model:
  - use the configured memory tool for historical recall
  - use `memark query` for promoted project corpus
  - use `Graphify` for code structure and graph navigation

Important:

- MemArk runtime lives at `__MEMARK_HOME__`
- preferred CLI is `__MEMARK_BIN__`
- helper launchers live next to this skill under `bin/`
- runtime installation requires a compatible Python interpreter in the `3.10` to `3.13` range
- do not force `--python-command python3` unless that `python3` is already in the supported range
- `memark doctor` may report a missing `mempal` executable; that only blocks `mem_tool=mempal`, not the default `mempalace` flow

Use these shell defaults so the commands below are copy/pasteable and non-interactive:

```bash
export MEMARK_BIN="__MEMARK_BIN__"
export MEMARK_WORKSPACE="${MEMARK_WORKSPACE:-$PWD}"
export MEMARK_PROJECT="${MEMARK_PROJECT:-$(basename "$PWD")}"
export MEMARK_SESSIONS_ROOT="${MEMARK_SESSIONS_ROOT:-$HOME/.codex/sessions}"
```

When starting work on a new project, first check installation health:

```bash
"$MEMARK_BIN" doctor --platform auto
```

Before project setup, verify the repository root is ready:

- run `memark init` only from the main git repository root, not from a linked worktree
- the repository root must already ignore `.memark/` and `corpus/` via `.gitignore` or `.git/info/exclude`
- if the root branch is protected and `.gitignore` is missing those entries, add them on a feature branch or dedicated worktree, merge that change back into the protected root branch, then return to the main repository root and run `memark init`
- only after the main repository root has been initialized should linked worktrees use `memark worktree-attach`

For project setup, the simplest path is:

```bash
"$MEMARK_BIN" init . --auto
```

That single command creates a workspace, registers the project, installs the background scheduler, and runs one automation cycle. After that, everything runs automatically.

If you need more control:

```bash
"$MEMARK_BIN" init . --project "$MEMARK_PROJECT"
"$MEMARK_BIN" project-set --workspace . --sessions-root "$MEMARK_SESSIONS_ROOT"
"$MEMARK_BIN" service-install --workspace .
"$MEMARK_BIN" automation-run --workspace . --project "$MEMARK_PROJECT"
```

When starting a concrete task inside one project, load the prepared context first:

```bash
"$MEMARK_BIN" context --workspace "$MEMARK_WORKSPACE" --project "$MEMARK_PROJECT"
```

That command refreshes the automatic feed/process/consume cycle by default, then returns the current `ai-context`, latest summary, decision digest, risk digest, and Graphify status as one consumption surface.

For explicit promotion and graph compilation control, prefer:

```bash
"$MEMARK_BIN" palace-run --workspace "$MEMARK_WORKSPACE" --project "$MEMARK_PROJECT" --wiki
```

When the user needs promoted project knowledge, search the project corpus first:

```bash
"$MEMARK_BIN" query "<topic>" --workspace "$MEMARK_WORKSPACE" --project "$MEMARK_PROJECT"
```

Use `--scope promoted` when you specifically want promoted session knowledge, and `--json` when the result should be fed into another AI step.

When the user wants the prepared corpus graph refreshed, use MemArk directly first:

```bash
"$MEMARK_BIN" build --workspace "$MEMARK_WORKSPACE" --project "$MEMARK_PROJECT"
```

That path now writes a local mixed-corpus `graphify-out/graph.json` even when the installed `graphify` CLI does not expose a direct folder-build entrypoint.

When the user specifically wants upstream Graphify interop or platform-installed AGENTS/hooks, generate the handoff first:

```bash
"$MEMARK_BIN" graphify-handoff --workspace "$MEMARK_WORKSPACE" --project "$MEMARK_PROJECT"
```

Prefer direct MemArk CLI commands first. MemArk-owned commands are designed to support both interactive and non-interactive use, but the default execution contract is non-interactive first with automatic approval.

MemArk CLI commands now keep one official command name per capability. Do not invent abbreviations or alternate spellings for existing commands.

If the task arrives as a slash-only request or the caller explicitly requires slash syntax, use:

```bash
"$MEMARK_BIN" slash --workspace "$MEMARK_WORKSPACE" /graphify "$MEMARK_WORKSPACE" --update
"$MEMARK_BIN" slash --workspace "$MEMARK_WORKSPACE" /context "$MEMARK_WORKSPACE" --no-refresh --json
"$MEMARK_BIN" slash --workspace "$MEMARK_WORKSPACE" /milestones "$MEMARK_WORKSPACE" --json
"$MEMARK_BIN" slash --workspace "$MEMARK_WORKSPACE" /automation-status "$MEMARK_WORKSPACE" --json
"$MEMARK_BIN" slash --workspace "$MEMARK_WORKSPACE" /status "$MEMARK_WORKSPACE" --json
"$MEMARK_BIN" slash --workspace "$MEMARK_WORKSPACE" /query <terms...> --json
"$MEMARK_BIN" slash --workspace "$MEMARK_WORKSPACE" /graphify-proof "$MEMARK_WORKSPACE" --json
```

If you first need to discover which slash adapters MemArk currently supports, use:

```bash
"$MEMARK_BIN" slash --catalog --json
```

If an upstream Graphify flow really ingests that corpus separately, persist the proof back into MemArk:

```bash
"$MEMARK_BIN" graphify-proof --workspace "$MEMARK_WORKSPACE" --project "$MEMARK_PROJECT" --record-ingested --evidence-path <path-to-proof-file>
```

If either MemArk or an upstream Graphify flow writes `graphify-out/graph.json` inside `corpus/<project>` and that graph contains nodes sourced from `promoted/`, registered project documents, or `imports/`, MemArk can auto-detect the proof later via `graphify-proof` or `milestones`.

Important boundary:

- `memark context` is the preferred automatic consumption entrypoint for one project
- `memark query` searches local project corpus files directly
- current `memark build` / `automation-run` can produce a local mixed-corpus graph without requiring a slash-command client
- current `memark slash` is the slash-compatible adapter surface for slash-only workflows
- current `memark slash --catalog` is the discovery surface for supported slash adapters
- current slash catalog also declares: direct CLI is preferred, execution is non-interactive first, and approval mode is auto
- current MemArk CLI keeps one official command name per capability to avoid AI routing drift across duplicate spellings
- current slash catalog includes `/graphify`, `/context`, `/milestones`, `/automation-status`, `/status`, `/query`, and `/graphify-proof`
- `memark graphify-handoff` and `memark graphify-onboard` are optional interop paths, not prerequisites for normal MemArk automation

If the user creates a new `git worktree`, do not re-install everything manually. Prefer:

```bash
"$MEMARK_BIN" worktree-attach --source-dir <repo-dir> --target-dir <worktree-dir>
```

That command copies directory-local `.memark`, memory-tool config such as `.mempalace`, `.codex`, `.claude`, and `AGENTS.md` into the new worktree. It assumes the main repository root has already completed `memark init`.

Optional `mempal` backend:

```bash
"$MEMARK_BIN" init . --auto --mem-tool mempal
```

That path is still CLI-first and non-interactive, but MemArk will generate a workspace-local starter config at `.memark/palaces/<project>/.mempal-home-<project>/.mempal/config.toml` on first mine. The starter config defaults to `backend = "api"` with `http://localhost:11434/api/embeddings` and `nomic-embed-text` so install does not block on model downloads. If no compatible embedding API is available yet, edit that generated config before `automation-run`, `projects-run`, or `mem-tool-mine`.

If the user asks for installation or repair, use the scripts in `bin/` or the install skill from the repository root.
