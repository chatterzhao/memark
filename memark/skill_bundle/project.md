# MemArk Project Workflow

Use this helper when a project needs to be connected to MemArk.

Checklist:

1. choose or create a MemArk workspace
2. register the directory path with `memark project-set --path`
3. run `memark projects-run`
4. inspect `memark palace-status`
5. package and promote project knowledge with `memark palace-run`
6. search promoted project knowledge with `memark query "<topic>"`
7. if Graphify needs the full prepared corpus, generate `memark graphify-handoff`
8. only after that, use Graphify outputs for code-structure questions

Do not skip directory registration. MemArk depends on directory-bound session matching.

Consumption order:

1. `MemPalace search` / `wake-up` for history
2. `memark query` for promoted project knowledge
3. `Graphify` report / query for code structure
4. `memark graphify-handoff` before asking the upstream Graphify skill to semantically rebuild the prepared corpus
