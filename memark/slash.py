"""Slash-command adapter registry for MemArk."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class SlashError(ValueError):
    """Raised when a slash command cannot be parsed or mapped."""


class _SlashArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SlashError(message)


@dataclass(frozen=True, slots=True)
class SlashContext:
    workspace_dir: Path
    project: str
    corpus_dir: Path


@dataclass(frozen=True, slots=True)
class SlashTarget:
    mode: str
    input: str | None
    path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "input": self.input,
            "path": self.path,
        }


@dataclass(frozen=True, slots=True)
class SlashDispatch:
    adapter: str
    slash_command: str
    memark_command: str
    raw_args: tuple[str, ...]
    mapped_args: dict[str, object]
    memark_argv: tuple[str, ...]
    target: SlashTarget | None

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter": self.adapter,
            "slash_command": self.slash_command,
            "memark_command": self.memark_command,
            "raw_args": list(self.raw_args),
            "mapped_args": self.mapped_args,
            "memark_argv": list(self.memark_argv),
            "target": self.target.to_dict() if self.target is not None else None,
        }


@dataclass(frozen=True, slots=True)
class SlashOption:
    flags: tuple[str, ...]
    dest: str
    memark_flag: str
    help: str
    action: str = "store_true"
    default: object = False
    value_type: Callable[[str], object] | None = None
    choices: tuple[str, ...] | None = None
    metavar: str | None = None
    nargs: str | int | None = None


@dataclass(frozen=True, slots=True)
class SlashPositional:
    name: str
    help: str
    nargs: str | int | None = None
    join_with: str | None = None


@dataclass(frozen=True, slots=True)
class SlashAdapterSpec:
    name: str
    aliases: tuple[str, ...]
    memark_command: str
    options: tuple[SlashOption, ...]
    resolve_target: Callable[[str | None, SlashContext], SlashTarget] | None = None
    positionals: tuple[SlashPositional, ...] = ()
    target_help: str = "Optional target path"
    preferred_invocation: str = "cli"
    interaction_mode: str = "non_interactive_first"
    approval_mode: str = "auto"
    usage_policy: str = (
        "Prefer the direct MemArk CLI command. Use the slash adapter only when the caller requires slash syntax or the upstream workflow is slash-only."
    )

    def to_catalog_entry(self) -> dict[str, object]:
        return {
            "name": self.name,
            "slash_command": f"/{self.name}",
            "aliases": [f"/{alias}" for alias in self.aliases],
            "memark_command": self.memark_command,
            "preferred_invocation": self.preferred_invocation,
            "interaction_mode": self.interaction_mode,
            "approval_mode": self.approval_mode,
            "usage_policy": self.usage_policy,
            "target_help": self.target_help if self.resolve_target is not None else None,
            "positionals": [
                {
                    "name": positional.name,
                    "help": positional.help,
                    "nargs": positional.nargs,
                }
                for positional in self.positionals
            ],
            "options": [
                {
                    "flags": list(option.flags),
                    "dest": option.dest,
                    "memark_flag": option.memark_flag,
                    "help": option.help,
                    "action": option.action,
                    "default": option.default,
                    "choices": list(option.choices) if option.choices is not None else None,
                    "metavar": option.metavar,
                    "nargs": option.nargs,
                }
                for option in self.options
            ],
        }


def _normalize_slash_command(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise SlashError("slash command cannot be empty")
    if cleaned.startswith("/"):
        cleaned = cleaned[1:]
    if not cleaned:
        raise SlashError("slash command cannot be empty")
    return cleaned.casefold()


def _resolve_graphify_target(raw_target: str | None, context: SlashContext) -> SlashTarget:
    workspace_dir = context.workspace_dir.resolve()
    corpus_dir = context.corpus_dir.resolve()
    if not raw_target:
        return SlashTarget(mode="default-corpus", input=None, path=str(corpus_dir))

    candidate = Path(raw_target).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate == corpus_dir:
        return SlashTarget(mode="explicit-corpus", input=raw_target, path=str(corpus_dir))
    if candidate == workspace_dir:
        return SlashTarget(mode="workspace-root", input=raw_target, path=str(corpus_dir))

    raise SlashError(
        "slash target must be the workspace root or the managed corpus directory: "
        f"{workspace_dir} or {corpus_dir}"
    )


def _resolve_workspace_target(raw_target: str | None, context: SlashContext) -> SlashTarget:
    workspace_dir = context.workspace_dir.resolve()
    if not raw_target:
        return SlashTarget(mode="default-workspace", input=None, path=str(workspace_dir))

    candidate = Path(raw_target).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate == workspace_dir:
        return SlashTarget(mode="workspace-root", input=raw_target, path=str(workspace_dir))

    raise SlashError(
        "slash target must be the managed workspace root: "
        f"{workspace_dir}"
    )


def _parser_for(adapter: SlashAdapterSpec) -> argparse.ArgumentParser:
    parser = _SlashArgumentParser(prog=f"/{adapter.name}", add_help=False)
    if adapter.resolve_target is not None:
        parser.add_argument("target", nargs="?", help=adapter.target_help)
    for positional in adapter.positionals:
        kwargs: dict[str, object] = {"help": positional.help}
        if positional.nargs is not None:
            kwargs["nargs"] = positional.nargs
        parser.add_argument(positional.name, **kwargs)
    for option in adapter.options:
        kwargs = {
            "dest": option.dest,
            "action": option.action,
            "help": option.help,
            "default": option.default,
        }
        if option.value_type is not None:
            kwargs["type"] = option.value_type
        if option.choices is not None:
            kwargs["choices"] = option.choices
        if option.metavar is not None:
            kwargs["metavar"] = option.metavar
        if option.nargs is not None:
            kwargs["nargs"] = option.nargs
        parser.add_argument(*option.flags, **kwargs)
    return parser


def _build_dispatch(
    adapter: SlashAdapterSpec,
    parsed: argparse.Namespace,
    slash_command: str,
    raw_args: tuple[str, ...],
    *,
    context: SlashContext,
) -> SlashDispatch:
    target = None
    if adapter.resolve_target is not None:
        target = adapter.resolve_target(getattr(parsed, "target", None), context)
    mapped_args: dict[str, object] = {}
    positional_values: list[str] = []
    for positional in adapter.positionals:
        value = getattr(parsed, positional.name)
        if isinstance(value, list) and positional.join_with is not None:
            value = positional.join_with.join(value)
        mapped_args[positional.name] = value
        positional_values.append(str(value))
    for option in adapter.options:
        mapped_args[option.dest] = getattr(parsed, option.dest, option.default)
    memark_argv = [adapter.memark_command]
    memark_argv.extend(positional_values)
    for option in adapter.options:
        value = mapped_args[option.dest]
        if option.action == "store_true":
            if value:
                memark_argv.append(option.memark_flag)
            continue
        if value != option.default:
            if isinstance(value, list):
                for item in value:
                    memark_argv.append(option.memark_flag)
                    memark_argv.append(str(item))
            else:
                memark_argv.append(option.memark_flag)
                memark_argv.append(str(value))
    return SlashDispatch(
        adapter=adapter.name,
        slash_command=slash_command,
        memark_command=adapter.memark_command,
        raw_args=raw_args,
        mapped_args=mapped_args,
        memark_argv=tuple(memark_argv),
        target=target,
    )


_ADAPTERS = (
    SlashAdapterSpec(
        name="context",
        aliases=("context",),
        memark_command="context",
        options=(
            SlashOption(flags=("--no-refresh",), dest="no_refresh", memark_flag="--no-refresh", help="Read existing context only"),
            SlashOption(flags=("--build",), dest="build", memark_flag="--build", help="Build graph during refresh"),
            SlashOption(flags=("--json",), dest="json", memark_flag="--json", help="Render machine-readable context"),
        ),
        resolve_target=_resolve_workspace_target,
        target_help="Optional managed workspace root",
    ),
    SlashAdapterSpec(
        name="milestones",
        aliases=("milestones",),
        memark_command="milestones",
        options=(
            SlashOption(flags=("--json",), dest="json", memark_flag="--json", help="Render machine-readable milestones"),
        ),
        resolve_target=_resolve_workspace_target,
        target_help="Optional managed workspace root",
    ),
    SlashAdapterSpec(
        name="automation-status",
        aliases=("automation-status",),
        memark_command="automation-status",
        options=(
            SlashOption(flags=("--json",), dest="json", memark_flag="--json", help="Render machine-readable automation state"),
        ),
        resolve_target=_resolve_workspace_target,
        target_help="Optional managed workspace root",
    ),
    SlashAdapterSpec(
        name="status",
        aliases=("status",),
        memark_command="status",
        options=(
            SlashOption(flags=("--json",), dest="json", memark_flag="--json", help="Render machine-readable status"),
        ),
        resolve_target=_resolve_workspace_target,
        target_help="Optional managed workspace root",
    ),
    SlashAdapterSpec(
        name="query",
        aliases=("query",),
        memark_command="query",
        options=(
            SlashOption(
                flags=("--scope",),
                dest="scope",
                memark_flag="--scope",
                help="Corpus scope to search",
                action="store",
                default="all",
                choices=("all", "promoted", "project", "imports"),
                metavar="SCOPE",
            ),
            SlashOption(
                flags=("--limit",),
                dest="limit",
                memark_flag="--limit",
                help="Maximum number of hits to return",
                action="store",
                default=10,
                value_type=int,
                metavar="N",
            ),
            SlashOption(flags=("--json",), dest="json", memark_flag="--json", help="Render machine-readable JSON"),
        ),
        positionals=(
            SlashPositional(name="query", help="Search text", nargs="+", join_with=" "),
        ),
    ),
    SlashAdapterSpec(
        name="graphify-proof",
        aliases=("graphify-proof",),
        memark_command="graphify-proof",
        options=(
            SlashOption(flags=("--record-ingested",), dest="record_ingested", memark_flag="--record-ingested", help="Persist proof that the prepared corpus was ingested"),
            SlashOption(flags=("--command",), dest="command", memark_flag="--command", help="Recorded upstream command or slash action", action="store", default=None, metavar="COMMAND"),
            SlashOption(flags=("--evidence-path",), dest="evidence_path", memark_flag="--evidence-path", help="Evidence file path; repeat for multiple paths", action="append", default=[], metavar="PATH"),
            SlashOption(flags=("--notes",), dest="notes", memark_flag="--notes", help="Short verification notes", action="store", default=None, metavar="TEXT"),
            SlashOption(flags=("--json",), dest="json", memark_flag="--json", help="Render machine-readable proof state"),
        ),
        resolve_target=_resolve_workspace_target,
        target_help="Optional managed workspace root",
    ),
    SlashAdapterSpec(
        name="consumption-proof",
        aliases=("consumption-proof",),
        memark_command="consumption-proof",
        options=(
            SlashOption(flags=("--record-verified",), dest="record_verified", memark_flag="--record-verified", help="Persist proof that AI continuity measurably improved"),
            SlashOption(flags=("--command",), dest="command", memark_flag="--command", help="Recorded verification command or workflow", action="store", default=None, metavar="COMMAND"),
            SlashOption(flags=("--evidence-path",), dest="evidence_path", memark_flag="--evidence-path", help="Evidence file path; repeat for multiple paths", action="append", default=[], metavar="PATH"),
            SlashOption(flags=("--outcome",), dest="outcome", memark_flag="--outcome", help="Observed improvement outcome; repeat for multiple outcomes", action="append", default=[], metavar="TEXT"),
            SlashOption(flags=("--notes",), dest="notes", memark_flag="--notes", help="Short verification notes", action="store", default=None, metavar="TEXT"),
            SlashOption(flags=("--json",), dest="json", memark_flag="--json", help="Render machine-readable proof state"),
        ),
        resolve_target=_resolve_workspace_target,
        target_help="Optional managed workspace root",
    ),
    SlashAdapterSpec(
        name="graphify",
        aliases=("graphify",),
        memark_command="build",
        options=(
            SlashOption(flags=("--update",), dest="update", memark_flag="--update", help="Refresh the graph output"),
            SlashOption(flags=("--wiki",), dest="wiki", memark_flag="--wiki", help="Request wiki mode"),
            SlashOption(flags=("--obsidian",), dest="obsidian", memark_flag="--obsidian", help="Request obsidian mode"),
            SlashOption(flags=("--mcp",), dest="mcp", memark_flag="--mcp", help="Request MCP output"),
        ),
        resolve_target=_resolve_graphify_target,
        target_help="Optional workspace root or managed corpus directory",
    ),
)

_ADAPTER_BY_ALIAS = {
    alias: adapter
    for adapter in _ADAPTERS
    for alias in adapter.aliases
}


def available_slash_commands() -> list[str]:
    return [f"/{adapter.name}" for adapter in _ADAPTERS]


def slash_catalog() -> list[dict[str, object]]:
    return [adapter.to_catalog_entry() for adapter in _ADAPTERS]


def dispatch_slash_command(
    slash_command: str,
    slash_args: list[str],
    *,
    context: SlashContext,
) -> SlashDispatch:
    normalized = _normalize_slash_command(slash_command)
    adapter = _ADAPTER_BY_ALIAS.get(normalized)
    if adapter is None:
        raise SlashError(
            f"unsupported slash command '/{normalized}'. Available adapters: {', '.join(available_slash_commands())}"
        )

    parser = _parser_for(adapter)
    parsed = parser.parse_args(slash_args)
    return _build_dispatch(adapter, parsed, f"/{adapter.name}", tuple(slash_args), context=context)
