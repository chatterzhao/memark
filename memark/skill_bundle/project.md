# MemArk Project Workflow

Use this helper when a project needs to be connected to MemArk.

Copy/paste defaults:

```bash
export MEMARK_BIN="__MEMARK_BIN__"
export MEMARK_WORKSPACE="${MEMARK_WORKSPACE:-$PWD}"
export MEMARK_PROJECT="${MEMARK_PROJECT:-$(basename "$PWD")}"
export MEMARK_SESSIONS_ROOT="${MEMARK_SESSIONS_ROOT:-$HOME/.codex/sessions}"
```

Before onboarding a project:

- run `memark init` only from the main git repository root, not from a linked worktree
- ensure the repository root already ignores `.memark/` in `.gitignore` or `.git/info/exclude`
- if the root branch is protected and that ignore entry is missing, add it on a feature branch or dedicated worktree, merge that change back into the protected root branch, then return to the main repository root and run `memark init`
- after the main repository root has been initialized, attach linked worktrees with `memark worktree-attach --source-dir <main-repo> --target-dir <worktree-dir>`

Default CLI-first onboarding:

```bash
"$MEMARK_BIN" init . --auto
```

That single command creates a workspace, registers the project, installs the background scheduler, and runs one automation cycle.

For step-by-step control:

```bash
"$MEMARK_BIN" init . --project "$MEMARK_PROJECT"
"$MEMARK_BIN" project-set --workspace . --sessions-root "$MEMARK_SESSIONS_ROOT"
"$MEMARK_BIN" service-install --workspace .
"$MEMARK_BIN" automation-run --workspace . --project "$MEMARK_PROJECT"
```

Checklist:

1. run `memark init . --auto` to set up everything at once
2. or if step-by-step: `memark init .` then `memark project-set --workspace .` then `memark service-install --workspace .`
3. check `memark automation-status` when you need to confirm the last automatic cycle finished
4. load the unified consumption surface with `memark context`
5. inspect `memark palace-status` when you need lower-level ingest status
6. inspect `memark milestones --workspace <workspace>` when you need the current stage, blockers, and next actions
7. search promoted project knowledge with `memark query "<topic>"`
8. inspect `memark status --workspace <workspace> --json` when you need the exact `graphify_corpus.status`
9. if that status is `graph_missing` or `code_only_graph`, run `memark build --workspace <workspace>`
10. if you need to discover which slash adapters are available first, run `memark slash --catalog --json`
11. prefer direct MemArk CLI commands first because MemArk-owned commands are designed for non-interactive automation with approval=auto
12. use only the official MemArk command name for each capability; do not create shorthand aliases for existing commands
13. if the requested action is slash-only, route it through `memark slash --workspace <workspace> /graphify <workspace-or-corpus> --update`
14. if the requested action asks for the unified project context, prefer `memark context --workspace <workspace> --project <name>`; only fall back to `memark slash --workspace <workspace> /context <workspace> --no-refresh --json` when slash syntax is required
15. if the requested action asks for rollout status or blockers, prefer `memark milestones --workspace <workspace> --json`; only fall back to `memark slash --workspace <workspace> /milestones <workspace> --json` when slash syntax is required
16. if the requested action asks for exact workspace status, prefer `memark status --workspace <workspace> --json`; only fall back to `memark slash --workspace <workspace> /status <workspace> --json` when slash syntax is required
17. if the requested action asks for local corpus search, prefer `memark query "<topic>" --workspace <workspace> --project <name>`; only fall back to `memark slash --workspace <workspace> /query <terms...> --json` when slash syntax is required
18. if the requested action asks for the latest automation cycle state, prefer `memark automation-status --workspace <workspace> --json`; only fall back to `memark slash --workspace <workspace> /automation-status <workspace> --json` when slash syntax is required
19. if the requested action asks for mixed-corpus graph proof state, prefer `memark graphify-proof --workspace <workspace> --json`; only fall back to `memark slash --workspace <workspace> /graphify-proof <workspace> --json` when slash syntax is required
20. if upstream Graphify interop is specifically needed, run `memark graphify-onboard --workspace <workspace>` and `memark graphify-handoff`
21. after either MemArk or upstream Graphify writes a real mixed-corpus `graphify-out/graph.json`, let `memark graphify-proof` or `memark milestones` auto-detect it
22. then use Graphify outputs for code-structure and corpus-navigation questions

Do not skip directory registration. MemArk depends on directory-bound session matching.

Important boundary:

- `memark install` is machine-level setup, not project onboarding
- a new project does not require another install
- a new project does require either an existing workspace plus `project-set`, or a fresh `memark init` for a new workspace

Consumption order:

1. `memark context` for the current automatic summary / decisions / risks / graphify status bundle
2. the configured memory tool for deeper history, for example `MemPalace search` / `wake-up`
3. `memark query` for promoted project knowledge
4. `memark build`, `memark slash`, or `automation-run` to refresh the corpus graph when needed
5. `Graphify` report / query for code structure, with `memark graphify-handoff` reserved for upstream interop

Optional `mempal` onboarding:

```bash
"$MEMARK_BIN" init . --auto --mem-tool mempal
```

That still runs non-interactively. On the first mine, MemArk writes `.memark/palaces/<project>/.mempal-home-<project>/.mempal/config.toml`. The starter backend is `api` with `http://localhost:11434/api/embeddings` and `nomic-embed-text`; if no compatible embedding API is available yet, edit that generated config before running `automation-run`, `projects-run`, or `mem-tool-mine`.
