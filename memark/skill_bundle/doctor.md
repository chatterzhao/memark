# MemArk Doctor

Use this helper when installation health is unclear.

Primary command:

```bash
__MEMARK_BIN__ doctor --platform auto
```

Check at least:

- MemArk runtime exists
- the selected memory tool executable exists
- `mempal` is installed when the workspace uses `mem_tool = "mempal"`
- `graphify` exists
- the MemArk skill bundle exists in the AI tool skill directory

Default install path is `mempalace`, so a missing `mempal` warning is optional unless the workspace explicitly uses `mem_tool = "mempal"`.

If you do use `mem_tool = "mempal"`, MemArk keeps it CLI-first by generating a workspace-local starter config on first mine:

```text
.memark/palaces/<project>/.mempal-home-<project>/.mempal/config.toml
```

That starter config defaults to `backend = "api"` with `http://localhost:11434/api/embeddings` and `nomic-embed-text` so install does not block on model downloads. If the embedding API is not available yet, edit that generated file before running `automation-run`, `projects-run`, or `mem-tool-mine`.
