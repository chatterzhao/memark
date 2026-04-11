# MemArk Project Workflow

Use this helper when a project needs to be connected to MemArk.

Checklist:

1. choose or create a MemArk workspace
2. register the directory path with `memark project-set --path`
3. install the repeated intake cycle with `memark service-install` when the workspace should keep itself up to date
4. run `memark automation-run` once when you need an immediate automatic cycle
5. load the unified consumption surface with `memark context`
6. inspect `memark palace-status` when you need lower-level ingest status
7. search promoted project knowledge with `memark query "<topic>"`
8. if Graphify needs the full prepared corpus, generate `memark graphify-handoff`
9. only after that, use Graphify outputs for code-structure questions

Do not skip directory registration. MemArk depends on directory-bound session matching.

Consumption order:

1. `memark context` for the current automatic summary / decisions / risks / graphify status bundle
2. `MemPalace search` / `wake-up` for deeper history
3. `memark query` for promoted project knowledge
4. `Graphify` report / query for code structure
5. `memark graphify-handoff` before asking the upstream Graphify skill to semantically rebuild the prepared corpus
