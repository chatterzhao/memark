# MemArk Project Workflow

Use this helper when a project needs to be connected to MemArk.

Checklist:

1. decide whether to reuse an existing workspace or create a new one
2. if no suitable workspace exists yet, initialize one with `memark init <workspace>`
3. register the project directory with `memark project-set --workspace <workspace> --path`
4. install the repeated intake cycle with `memark service-install` when the workspace should keep itself up to date
5. run `memark automation-run` once when you need an immediate automatic cycle
6. check `memark automation-status` when you need to confirm the last automatic cycle finished
7. load the unified consumption surface with `memark context`
8. inspect `memark palace-status` when you need lower-level ingest status
9. inspect `memark milestones --workspace <workspace>` when you need the current stage, blockers, and next actions
10. search promoted project knowledge with `memark query "<topic>"`
11. inspect `memark status --workspace <workspace> --json` when you need the exact `graphify_corpus.status`
12. if that status is `graph_missing` or `code_only_graph`, run `memark build --workspace <workspace>`
13. if you need to discover which slash adapters are available first, run `memark slash --catalog --json`
14. prefer direct MemArk CLI commands first because MemArk-owned commands are designed for non-interactive automation with approval=auto
15. use only the official MemArk command name for each capability; do not create shorthand aliases for existing commands
16. if the requested action is slash-only, route it through `memark slash --workspace <workspace> /graphify <workspace-or-corpus> --update`
17. if the requested action asks for the unified project context, prefer `memark context --workspace <workspace> --project <name>`; only fall back to `memark slash --workspace <workspace> /context <workspace> --no-refresh --json` when slash syntax is required
18. if the requested action asks for rollout status or blockers, prefer `memark milestones --workspace <workspace> --json`; only fall back to `memark slash --workspace <workspace> /milestones <workspace> --json` when slash syntax is required
19. if the requested action asks for exact workspace status, prefer `memark status --workspace <workspace> --json`; only fall back to `memark slash --workspace <workspace> /status <workspace> --json` when slash syntax is required
20. if the requested action asks for local corpus search, prefer `memark query "<topic>" --workspace <workspace> --project <name>`; only fall back to `memark slash --workspace <workspace> /query <terms...> --json` when slash syntax is required
21. if the requested action asks for the latest automation cycle state, prefer `memark automation-status --workspace <workspace> --json`; only fall back to `memark slash --workspace <workspace> /automation-status <workspace> --json` when slash syntax is required
22. if the requested action asks for mixed-corpus graph proof state, prefer `memark graphify-proof --workspace <workspace> --json`; only fall back to `memark slash --workspace <workspace> /graphify-proof <workspace> --json` when slash syntax is required
23. if upstream Graphify interop is specifically needed, run `memark graphify-onboard --workspace <workspace>` and `memark graphify-handoff`
24. after either MemArk or upstream Graphify writes a real mixed-corpus `graphify-out/graph.json`, let `memark graphify-proof` or `memark milestones` auto-detect it
25. then use Graphify outputs for code-structure and corpus-navigation questions

Do not skip directory registration. MemArk depends on directory-bound session matching.

Important boundary:

- `memark install` is machine-level setup, not project onboarding
- a new project does not require another install
- a new project does require either an existing workspace plus `project-set`, or a fresh `memark init` for a new workspace

Consumption order:

1. `memark context` for the current automatic summary / decisions / risks / graphify status bundle
2. `MemPalace search` / `wake-up` for deeper history
3. `memark query` for promoted project knowledge
4. `memark build`, `memark slash`, or `automation-run` to refresh the corpus graph when needed
5. `Graphify` report / query for code structure, with `memark graphify-handoff` reserved for upstream interop
