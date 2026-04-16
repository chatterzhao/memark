# MemArk Project Workflow

Use this helper when a project needs to be connected to MemArk.

Default CLI-first onboarding:

```bash
__MEMARK_BIN__ init . --auto
```

That single command creates a workspace, registers the project, installs the background scheduler, and runs one automation cycle.

For step-by-step control:

```bash
__MEMARK_BIN__ init . --project <name>
__MEMARK_BIN__ project-set --workspace . --sessions-root ~/.codex/sessions
__MEMARK_BIN__ service-install --workspace .
__MEMARK_BIN__ automation-run --workspace . --project <name>
```

Checklist:

1. run `__MEMARK_BIN__ init . --auto` to set up everything at once
2. or if step-by-step: `memark init .` then `memark project-set --workspace .` then `memark service-install --workspace .`
3. check `memark automation-status` when you need to confirm the last automatic cycle finished
4. inspect `memark palace-status`
5. search promoted project knowledge with `memark query "<topic>"`
6. if Graphify needs the full prepared corpus, generate `memark graphify-handoff`

Do not skip directory registration. MemArk depends on directory-bound session matching.

Important boundary:

- `memark install` is machine-level setup, not project onboarding
- a new project does not require another install
- a new project does require either an existing workspace plus `project-set`, or a fresh `memark init . --auto` for a new workspace
