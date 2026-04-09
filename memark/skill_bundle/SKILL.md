---
name: memark
description: Use MemArk to keep project conversations flowing into MemPalace and promoted project knowledge flowing toward Graphify.
---

# MemArk

Use this skill when the user is working on a software project and you need MemArk to manage project memory and knowledge compilation.

Default behavior:

- treat MemArk as the user-facing entrypoint
- use MemArk commands instead of calling `mempalace` or `graphify` directly when MemArk already covers the operation
- keep project conversations isolated by project root
- let MemArk manage the bridge into MemPalace and the prepared corpus for Graphify

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
__MEMARK_BIN__ project-set --workspace <workspace> --project <name> --root <project-root> --sessions-root ~/.codex/sessions
__MEMARK_BIN__ projects-run --workspace <workspace>
```

For project memory promotion and graph compilation, prefer:

```bash
__MEMARK_BIN__ palace-run --workspace <workspace> --project <name> --wiki
```

If the user asks for installation or repair, use the scripts in `bin/` or the install skill from the repository root.
