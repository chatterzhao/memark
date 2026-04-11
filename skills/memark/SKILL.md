---
name: memark
description: Use MemArk to keep project conversations flowing into MemPalace and promoted project knowledge flowing toward Graphify.
---

# MemArk

Use this skill when the user is working on a software project and you need MemArk to manage project memory and knowledge compilation.

Default behavior:

- treat MemArk as the user-facing entrypoint
- use MemArk commands instead of calling `mempalace` or `graphify` directly when MemArk already covers the operation
- keep conversations isolated by directory path
- let MemArk manage the bridge into MemPalace and the prepared corpus for Graphify
- prefer a split consumption model:
  - use `MemPalace` for historical recall
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
__MEMARK_BIN__ projects-run --workspace <workspace>
```

For project memory promotion and graph compilation, prefer:

```bash
__MEMARK_BIN__ palace-run --workspace <workspace> --project <name> --wiki
```

When the user needs promoted project knowledge, search the project corpus first:

```bash
__MEMARK_BIN__ query "<topic>" --workspace <workspace> --project <name>
```

Use `--scope promoted` when you specifically want promoted session knowledge, and `--json` when the result should be fed into another AI step.

When the user wants Graphify to semantically compile the full prepared corpus, generate the handoff first:

```bash
__MEMARK_BIN__ graphify-handoff --workspace <workspace> --project <name>
```

Important boundary:

- `memark query` searches local project corpus files directly
- current `memark build` / `palace-run --wiki` does not prove promoted markdown has already entered the Graphify graph
- if the task truly requires mixed-corpus Graphify semantic extraction, use the upstream Graphify skill / platform flow separately

If the user creates a new `git worktree`, do not re-install everything manually. Prefer:

```bash
__MEMARK_BIN__ worktree-attach --source-dir <repo-dir> --target-dir <worktree-dir>
```

That command copies directory-local `.memark`, `.mempalace`, `.codex`, `.claude`, and `AGENTS.md` config into the new worktree.

If the user asks for installation or repair, use the scripts in `bin/` or the install skill from the repository root.
