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
