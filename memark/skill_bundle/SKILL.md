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

When starting work on a new project, first check installation health:

```bash
__MEMARK_BIN__ doctor --platform auto
```

For project intake and cycle runs, prefer:

```bash
__MEMARK_BIN__ project-set --workspace <workspace> --project <name> --path <directory-path> --sessions-root ~/.codex/sessions
__MEMARK_BIN__ service-install --workspace <workspace>
__MEMARK_BIN__ automation-run --workspace <workspace>
```

When starting a concrete task inside one project, load the prepared context first:

```bash
__MEMARK_BIN__ context --workspace <workspace> --project <name>
```

That command refreshes the automatic feed/process/consume cycle by default, then returns the current `ai-context`, latest summary, decision digest, risk digest, and Graphify status as one consumption surface.

For explicit promotion and graph compilation control, prefer:

```bash
__MEMARK_BIN__ palace-run --workspace <workspace> --project <name> --wiki
```

When the user needs promoted project knowledge, search the project corpus first:

```bash
__MEMARK_BIN__ query "<topic>" --workspace <workspace> --project <name>
```

Use `--scope promoted` when you specifically want promoted session knowledge, and `--json` when the result should be fed into another AI step.

When the user wants the prepared corpus graph refreshed, use MemArk directly first:

```bash
__MEMARK_BIN__ build --workspace <workspace> --project <name>
```

That path now writes a local mixed-corpus `graphify-out/graph.json` even when the installed `graphify` CLI does not expose a direct folder-build entrypoint.

When the user specifically wants upstream Graphify interop or platform-installed AGENTS/hooks, generate the handoff first:

```bash
__MEMARK_BIN__ graphify-handoff --workspace <workspace> --project <name>
```

Prefer direct MemArk CLI commands first. MemArk-owned commands are designed to support both interactive and non-interactive use, but the default execution contract is non-interactive first with automatic approval.

MemArk CLI commands now keep one official command name per capability. Do not invent abbreviations or alternate spellings for existing commands.

If the task arrives as a slash-only request or the caller explicitly requires slash syntax, use:

```bash
__MEMARK_BIN__ slash --workspace <workspace> /graphify <workspace-or-corpus> --update
__MEMARK_BIN__ slash --workspace <workspace> /context <workspace> --no-refresh --json
__MEMARK_BIN__ slash --workspace <workspace> /milestones <workspace> --json
__MEMARK_BIN__ slash --workspace <workspace> /automation-status <workspace> --json
__MEMARK_BIN__ slash --workspace <workspace> /status <workspace> --json
__MEMARK_BIN__ slash --workspace <workspace> /query <terms...> --json
__MEMARK_BIN__ slash --workspace <workspace> /graphify-proof <workspace> --json
```

If you first need to discover which slash adapters MemArk currently supports, use:

```bash
__MEMARK_BIN__ slash --catalog --json
```

If an upstream Graphify flow really ingests that corpus separately, persist the proof back into MemArk:

```bash
__MEMARK_BIN__ graphify-proof --workspace <workspace> --project <name> --record-ingested --evidence-path <path-to-proof-file>
```

If either MemArk or an upstream Graphify flow writes `graphify-out/graph.json` inside `corpus/<project>` and that graph contains nodes sourced from `promoted/`, `documents/`, or `imports/`, MemArk can auto-detect the proof later via `graphify-proof` or `milestones`.

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
__MEMARK_BIN__ worktree-attach --source-dir <repo-dir> --target-dir <worktree-dir>
```

That command copies directory-local `.memark`, memory-tool config such as `.mempalace`, `.codex`, `.claude`, and `AGENTS.md` into the new worktree.

If the user asks for installation or repair, use the scripts in `bin/` or the install skill from the repository root.
