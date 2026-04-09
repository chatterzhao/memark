"""Command line interface for MemArk."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .codex import sync_codex_sessions
from .graphify import GraphifyError, run_graphify
from .io import copy_document
from .mempalace import MemPalaceError, reset_palace_dir, run_mempalace_convo_mine
from .models import ValidationError
from .package_builder import (
    build_room_package_from_drawers,
    group_drawers_by_room,
    package_to_dict,
    write_package_payloads,
)
from .palace import PalaceReadError, read_palace_drawers
from .project_registry import ProjectProfile, load_project_profiles, run_projects_cycle, upsert_project_profile
from .promote import load_room_packages, promote_file, promote_path
from .version import __version__
from .workspace import create_workspace, load_workspace, resolve_workspace, slugify


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memark",
        description="Promote MemPalace room packages into a Graphify-ready corpus.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a MemArk workspace")
    init_parser.add_argument("workspace", nargs="?", default=".", help="Workspace directory")
    init_parser.add_argument("--project", default="default", help="Default project slug")
    init_parser.add_argument("--graphify-bin", default="graphify", help="Graphify executable name")
    init_parser.add_argument("--mempalace-bin", default="mempalace", help="MemPalace executable name")
    init_parser.set_defaults(func=cmd_init)

    validate_parser = subparsers.add_parser("validate", help="Validate a room package JSON file")
    validate_parser.add_argument("input", help="JSON file to validate")
    validate_parser.set_defaults(func=cmd_validate)

    promote_parser = subparsers.add_parser(
        "promote",
        help="Promote room package JSON into the Graphify corpus",
    )
    promote_parser.add_argument(
        "input",
        nargs="?",
        default="inbox",
        help="JSON file or directory to consume. Default resolves to inbox/promoted",
    )
    promote_parser.add_argument("--workspace", default=".", help="Workspace directory")
    promote_parser.add_argument("--project", help="Override project slug")
    promote_parser.add_argument(
        "--allow-non-project",
        action="store_true",
        help="Allow non-project wing kinds to be promoted",
    )
    promote_parser.add_argument(
        "--archive",
        action="store_true",
        help="Move consumed JSON files into .memark/archive",
    )
    promote_parser.set_defaults(func=cmd_promote)

    docs_parser = subparsers.add_parser("add-documents", help="Copy project documents into the corpus")
    docs_parser.add_argument("sources", nargs="+", help="Files to copy")
    docs_parser.add_argument("--workspace", default=".", help="Workspace directory")
    docs_parser.add_argument("--project", help="Target project slug")
    docs_parser.set_defaults(func=cmd_add_documents)

    build_parser = subparsers.add_parser("build", help="Run Graphify against a project corpus")
    build_parser.add_argument("--workspace", default=".", help="Workspace directory")
    build_parser.add_argument("--project", help="Target project slug")
    build_parser.add_argument("--graphify-bin", help="Override graphify executable name")
    build_parser.add_argument("--update", action="store_true", help="Pass --update to graphify")
    build_parser.add_argument("--wiki", action="store_true", help="Pass --wiki to graphify")
    build_parser.add_argument("--obsidian", action="store_true", help="Pass --obsidian to graphify")
    build_parser.add_argument("--mcp", action="store_true", help="Pass --mcp to graphify")
    build_parser.add_argument("--dry-run", action="store_true", help="Print the graphify command without executing it")
    build_parser.set_defaults(func=cmd_build)

    run_parser = subparsers.add_parser(
        "run",
        help="Promote inbox room packages, copy inbox documents, then optionally run Graphify",
    )
    run_parser.add_argument("--workspace", default=".", help="Workspace directory")
    run_parser.add_argument("--project", help="Target project slug")
    run_parser.add_argument(
        "--allow-non-project",
        action="store_true",
        help="Allow non-project wing kinds to be promoted",
    )
    run_parser.add_argument("--archive", action="store_true", help="Move consumed JSON files into .memark/archive")
    run_parser.add_argument("--graphify-bin", help="Override graphify executable name")
    run_parser.add_argument("--update", action="store_true", help="Pass --update to graphify")
    run_parser.add_argument("--wiki", action="store_true", help="Pass --wiki to graphify")
    run_parser.add_argument("--obsidian", action="store_true", help="Pass --obsidian to graphify")
    run_parser.add_argument("--mcp", action="store_true", help="Pass --mcp to graphify")
    run_parser.add_argument("--dry-run", action="store_true", help="Print the graphify command without executing it")
    run_parser.add_argument("--no-build", action="store_true", help="Only ingest inbox content")
    run_parser.set_defaults(func=cmd_run)

    codex_parser = subparsers.add_parser(
        "codex-sync",
        help="Scan Codex sessions, match project sessions by cwd, and sync them into staging",
    )
    codex_parser.add_argument("--workspace", default=".", help="Workspace directory")
    codex_parser.add_argument("--project", help="Target project slug")
    codex_parser.add_argument(
        "--project-root",
        required=True,
        help="Absolute or relative project root used to match session_meta.payload.cwd",
    )
    codex_parser.add_argument(
        "--sessions-root",
        default="~/.codex/sessions",
        help="Root directory that contains Codex rollout JSONL files",
    )
    codex_parser.add_argument(
        "--cwd-prefix",
        action="append",
        default=[],
        help="Additional cwd prefixes that should map into the same project",
    )
    codex_parser.add_argument("--dry-run", action="store_true", help="Scan and report without writing staging or ledger")
    codex_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    codex_parser.set_defaults(func=cmd_codex_sync)

    project_set_parser = subparsers.add_parser(
        "project-set",
        help="Create or update a project registry entry for single-cycle sync and mine orchestration",
    )
    project_set_parser.add_argument("--workspace", default=".", help="Workspace directory")
    project_set_parser.add_argument("--project", required=True, help="Project slug")
    project_set_parser.add_argument("--root", required=True, help="Project root used to match session_meta.payload.cwd")
    project_set_parser.add_argument(
        "--sessions-root",
        default="~/.codex/sessions",
        help="Root directory that contains Codex rollout JSONL files",
    )
    project_set_parser.add_argument(
        "--cwd-prefix",
        action="append",
        default=[],
        help="Additional cwd prefixes that should map into the same project",
    )
    project_set_parser.add_argument(
        "--mine-interval-seconds",
        type=int,
        default=120,
        help="Minimum interval between automatic mempalace mine runs for this project",
    )
    project_set_parser.add_argument("--no-auto-mine", action="store_true", help="Record pending changes without auto-running mine")
    project_set_parser.add_argument("--disabled", action="store_true", help="Keep the project in config but skip it during projects-run")
    project_set_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    project_set_parser.set_defaults(func=cmd_project_set)

    projects_list_parser = subparsers.add_parser("projects-list", help="List configured project registry entries")
    projects_list_parser.add_argument("--workspace", default=".", help="Workspace directory")
    projects_list_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    projects_list_parser.set_defaults(func=cmd_projects_list)

    projects_run_parser = subparsers.add_parser(
        "projects-run",
        help="Run one configured Codex sync + optional MemPalace mine cycle across enabled projects",
    )
    projects_run_parser.add_argument("--workspace", default=".", help="Workspace directory")
    projects_run_parser.add_argument("--project", help="Only run one configured project")
    projects_run_parser.add_argument("--retry-attempts", type=int, default=3, help="Retry mine on lock errors up to N attempts")
    projects_run_parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=0.2,
        help="Initial retry delay for lock errors; doubles after each retry",
    )
    projects_run_parser.add_argument("--dry-run", action="store_true", help="Render what would happen without writing state or mining")
    projects_run_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    projects_run_parser.set_defaults(func=cmd_projects_run)

    mempalace_parser = subparsers.add_parser(
        "mempalace-mine",
        help="Run 'mempalace mine --mode convos' against a project's staged Codex sessions",
    )
    mempalace_parser.add_argument("--workspace", default=".", help="Workspace directory")
    mempalace_parser.add_argument("--project", help="Target project slug")
    mempalace_parser.add_argument("--mempalace-bin", help="Override mempalace executable name")
    mempalace_parser.add_argument(
        "--palace-dir",
        help="Override palace directory. Defaults to .memark/palaces/<project>",
    )
    mempalace_parser.add_argument(
        "--staging-dir",
        help="Override staging directory. Defaults to .memark/staging/<project>/sessions",
    )
    mempalace_parser.add_argument("--retry-attempts", type=int, default=3, help="Retry mine on lock errors up to N attempts")
    mempalace_parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=0.2,
        help="Initial retry delay for lock errors; doubles after each retry",
    )
    mempalace_parser.add_argument("--dry-run", action="store_true", help="Print the MemPalace command without executing it")
    mempalace_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    mempalace_parser.set_defaults(func=cmd_mempalace_mine)

    palace_status_parser = subparsers.add_parser(
        "palace-status",
        help="Show filesystem and drawer counts for a project's palace",
    )
    palace_status_parser.add_argument("--workspace", default=".", help="Workspace directory")
    palace_status_parser.add_argument("--project", help="Target project slug")
    palace_status_parser.add_argument("--palace-dir", help="Override palace directory")
    palace_status_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    palace_status_parser.set_defaults(func=cmd_palace_status)

    palace_clean_parser = subparsers.add_parser(
        "palace-clean",
        help="Remove a project's palace contents and recreate the empty directory",
    )
    palace_clean_parser.add_argument("--workspace", default=".", help="Workspace directory")
    palace_clean_parser.add_argument("--project", help="Target project slug")
    palace_clean_parser.add_argument("--palace-dir", help="Override palace directory")
    palace_clean_parser.add_argument("--dry-run", action="store_true", help="Render the target directory without deleting it")
    palace_clean_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    palace_clean_parser.set_defaults(func=cmd_palace_clean)

    palace_rebuild_parser = subparsers.add_parser(
        "palace-rebuild",
        help="Clean a project's palace, then rerun MemPalace convo mine from staging",
    )
    palace_rebuild_parser.add_argument("--workspace", default=".", help="Workspace directory")
    palace_rebuild_parser.add_argument("--project", help="Target project slug")
    palace_rebuild_parser.add_argument("--mempalace-bin", help="Override mempalace executable name")
    palace_rebuild_parser.add_argument("--palace-dir", help="Override palace directory")
    palace_rebuild_parser.add_argument("--staging-dir", help="Override staging directory")
    palace_rebuild_parser.add_argument("--retry-attempts", type=int, default=3, help="Retry mine on lock errors up to N attempts")
    palace_rebuild_parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=0.2,
        help="Initial retry delay for lock errors; doubles after each retry",
    )
    palace_rebuild_parser.add_argument("--dry-run", action="store_true", help="Render actions without deleting or mining")
    palace_rebuild_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    palace_rebuild_parser.set_defaults(func=cmd_palace_rebuild)

    palace_retry_parser = subparsers.add_parser(
        "palace-retry",
        help="Retry MemPalace convo mine against the current project staging without cleaning",
    )
    palace_retry_parser.add_argument("--workspace", default=".", help="Workspace directory")
    palace_retry_parser.add_argument("--project", help="Target project slug")
    palace_retry_parser.add_argument("--mempalace-bin", help="Override mempalace executable name")
    palace_retry_parser.add_argument("--palace-dir", help="Override palace directory")
    palace_retry_parser.add_argument("--staging-dir", help="Override staging directory")
    palace_retry_parser.add_argument("--retry-attempts", type=int, default=3, help="Retry mine on lock errors up to N attempts")
    palace_retry_parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=0.2,
        help="Initial retry delay for lock errors; doubles after each retry",
    )
    palace_retry_parser.add_argument("--dry-run", action="store_true", help="Render the MemPalace command without executing it")
    palace_retry_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    palace_retry_parser.set_defaults(func=cmd_palace_retry)

    palace_parser = subparsers.add_parser(
        "palace-export",
        help="Read staged MemPalace drawers from a project palace using a read-only adapter",
    )
    palace_parser.add_argument("--workspace", default=".", help="Workspace directory")
    palace_parser.add_argument("--project", help="Target project slug")
    palace_parser.add_argument("--palace-dir", help="Override palace directory")
    palace_parser.add_argument("--ingest-mode", default="convos", help="Filter drawers by ingest_mode")
    palace_parser.add_argument("--wing", help="Filter drawers by wing")
    palace_parser.add_argument("--room", help="Filter drawers by room")
    palace_parser.add_argument("--limit", type=int, help="Maximum number of drawers to return")
    palace_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    palace_parser.set_defaults(func=cmd_palace_export)

    package_parser = subparsers.add_parser(
        "palace-package",
        help="Build deterministic room package candidates from palace drawers",
    )
    package_parser.add_argument("--workspace", default=".", help="Workspace directory")
    package_parser.add_argument("--project", help="Target project slug")
    package_parser.add_argument("--palace-dir", help="Override palace directory")
    package_parser.add_argument("--ingest-mode", default="convos", help="Filter drawers by ingest_mode")
    package_parser.add_argument("--wing", help="Filter drawers by wing")
    package_parser.add_argument("--room", help="Filter drawers by room")
    package_parser.add_argument("--limit", type=int, help="Maximum number of drawers to read before grouping")
    package_parser.add_argument("--hall-id", default="discoveries", help="hall_id to assign to generated packages")
    package_parser.add_argument(
        "--write-inbox",
        action="store_true",
        help="Write one JSON package per room into workspace/inbox/promoted",
    )
    package_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    package_parser.set_defaults(func=cmd_palace_package)

    palace_run_parser = subparsers.add_parser(
        "palace-run",
        help="Build room packages from palace drawers, promote them, then optionally run Graphify",
    )
    palace_run_parser.add_argument("--workspace", default=".", help="Workspace directory")
    palace_run_parser.add_argument("--project", help="Target project slug")
    palace_run_parser.add_argument("--palace-dir", help="Override palace directory")
    palace_run_parser.add_argument("--ingest-mode", default="convos", help="Filter drawers by ingest_mode")
    palace_run_parser.add_argument("--wing", help="Filter drawers by wing")
    palace_run_parser.add_argument("--room", help="Filter drawers by room")
    palace_run_parser.add_argument("--limit", type=int, help="Maximum number of drawers to read before grouping")
    palace_run_parser.add_argument("--hall-id", default="discoveries", help="hall_id to assign to generated packages")
    palace_run_parser.add_argument("--graphify-bin", help="Override graphify executable name")
    palace_run_parser.add_argument("--update", action="store_true", help="Pass --update to graphify")
    palace_run_parser.add_argument("--wiki", action="store_true", help="Pass --wiki to graphify")
    palace_run_parser.add_argument("--obsidian", action="store_true", help="Pass --obsidian to graphify")
    palace_run_parser.add_argument("--mcp", action="store_true", help="Pass --mcp to graphify")
    palace_run_parser.add_argument("--dry-run", action="store_true", help="Render intended actions without executing them")
    palace_run_parser.add_argument("--no-build", action="store_true", help="Only package and promote palace content")
    palace_run_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    palace_run_parser.set_defaults(func=cmd_palace_run)

    status_parser = subparsers.add_parser("status", help="Show workspace and project status")
    status_parser.add_argument("--workspace", default=".", help="Workspace directory")
    status_parser.add_argument("--project", help="Target project slug")
    status_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    status_parser.set_defaults(func=cmd_status)

    return parser


def _resolve_promote_input(config, raw_input: str) -> Path:
    input_path = Path(raw_input)
    if input_path.is_absolute():
        return input_path
    if input_path == Path("inbox"):
        return config.inbox_promoted_dir.resolve()
    return (config.workspace / input_path).resolve()


def _print_promote_results(results) -> None:
    changed = 0
    skipped = 0
    for result in results:
        state = "updated" if result.changed else "unchanged"
        print(f"{state}: {result.room_id} -> {result.output}")
        if result.archived_to is not None:
            print(f"archived: {result.archived_to}")
        changed += int(result.changed)
        skipped += int(not result.changed)
    print(f"Promotion summary: {changed} changed, {skipped} unchanged")


def _infer_single_project_from_results(results, fallback_project: str) -> str:
    projects = sorted({result.project for result in results})
    if not projects:
        return slugify(fallback_project)
    if len(projects) > 1:
        joined = ", ".join(projects)
        raise ValueError(
            "Inbox promotion produced multiple target projects "
            f"({joined}). Re-run with --project or separate inbox content by project."
        )
    return slugify(projects[0])


def cmd_init(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    config = create_workspace(
        workspace=workspace,
        project=args.project,
        graphify_bin=args.graphify_bin,
        mempalace_bin=args.mempalace_bin,
    )
    print(f"Initialized MemArk workspace: {config.workspace}")
    print(f"Default project: {config.default_project}")
    print(f"Inbox: {config.inbox_dir}")
    print(f"Inbox promoted: {config.inbox_promoted_dir}")
    print(f"Inbox documents: {config.inbox_documents_dir}")
    print(f"Corpus: {config.corpus_project_dir()}")
    print(f"MemPalace bin: {config.mempalace_bin}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.input).expanduser().resolve()
    packages = load_room_packages(path)
    for package in packages:
        package.ensure_promotable(allow_non_project=True)
    print(f"Validated {len(packages)} room package(s): {path}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    input_path = _resolve_promote_input(config, args.input)
    results = promote_path(
        config=config,
        path=input_path,
        project_override=args.project,
        allow_non_project=args.allow_non_project,
        archive=args.archive,
    )
    if not results:
        print(f"No JSON room packages found in {input_path}")
        return 0
    _print_promote_results(results)
    return 0


def cmd_add_documents(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    copied = 0
    for source_name in args.sources:
        source = Path(source_name).expanduser().resolve()
        destination = config.documents_dir(project) / source.name
        copy_document(source, destination)
        print(f"copied: {source} -> {destination}")
        copied += 1
    print(f"Document summary: {copied} copied")
    return 0


def _graphify_command(graphify_bin: str, project_dir: Path, args: argparse.Namespace) -> list[str]:
    command = [graphify_bin, str(project_dir)]
    if args.update:
        command.append("--update")
    if args.wiki:
        command.append("--wiki")
    if args.obsidian:
        command.append("--obsidian")
    if args.mcp:
        command.append("--mcp")
    return command


def cmd_build(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    project_dir = config.corpus_project_dir(project)
    graphify_bin = args.graphify_bin or config.graphify_bin
    command = _graphify_command(graphify_bin, project_dir, args)
    if args.dry_run:
        print(" ".join(command))
        return 0

    result = run_graphify(
        graphify_bin=graphify_bin,
        project_dir=project_dir,
        update=args.update,
        wiki=args.wiki,
        obsidian=args.obsidian,
        mcp=args.mcp,
    )
    print("Graphify build completed")
    print("Command:", " ".join(result.command))
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    explicit_project = slugify(args.project) if args.project else None

    promote_results = promote_path(
        config=config,
        path=config.inbox_promoted_dir,
        project_override=explicit_project,
        allow_non_project=args.allow_non_project,
        archive=args.archive,
    )
    _print_promote_results(promote_results)
    project = explicit_project or _infer_single_project_from_results(
        promote_results,
        fallback_project=config.default_project,
    )

    copied = 0
    for source in sorted(path for path in config.inbox_documents_dir.rglob("*") if path.is_file()):
        destination = config.documents_dir(project) / source.name
        copy_document(source, destination)
        print(f"copied: {source} -> {destination}")
        copied += 1
    print(f"Document summary: {copied} copied")

    if args.no_build:
        return 0

    graphify_bin = args.graphify_bin or config.graphify_bin
    command = _graphify_command(graphify_bin, config.corpus_project_dir(project), args)
    if args.dry_run:
        print(" ".join(command))
        return 0

    result = run_graphify(
        graphify_bin=graphify_bin,
        project_dir=config.corpus_project_dir(project),
        update=args.update,
        wiki=args.wiki,
        obsidian=args.obsidian,
        mcp=args.mcp,
    )
    print("Graphify build completed")
    print("Command:", " ".join(result.command))
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return 0


def cmd_codex_sync(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    result = sync_codex_sessions(
        config=config,
        project=project,
        project_root=Path(args.project_root),
        sessions_root=Path(args.sessions_root),
        cwd_prefixes=[Path(value) for value in args.cwd_prefix],
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {result.project}")
    print(f"Project root: {result.project_root}")
    print(f"Sessions root: {result.sessions_root}")
    print(f"Staging dir: {result.staging_dir}")
    print(f"Scanned: {result.scanned}")
    print(f"Matched: {result.matched}")
    print(f"Copied: {result.copied}")
    print(f"Updated: {result.updated}")
    print(f"Unchanged: {result.unchanged}")
    print(f"Invalid: {result.invalid}")
    return 0


def cmd_project_set(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    profiles = upsert_project_profile(
        config.projects_file,
        ProjectProfile(
            name=args.project,
            root=args.root,
            sessions_root=args.sessions_root,
            cwd_prefixes=args.cwd_prefix,
            mine_interval_seconds=max(args.mine_interval_seconds, 0),
            auto_mine=not args.no_auto_mine,
            enabled=not args.disabled,
        ),
    )
    current = next(profile for profile in profiles if profile.normalized_name() == slugify(args.project))
    payload = {
        "project": current.normalized_name(),
        "root": str(current.normalized_root()),
        "sessions_root": current.sessions_root,
        "cwd_prefixes": [str(value) for value in current.normalized_cwd_prefixes()],
        "mine_interval_seconds": current.mine_interval_seconds,
        "auto_mine": current.auto_mine,
        "enabled": current.enabled,
        "projects_file": str(config.projects_file),
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    print(f"Project registry updated: {payload['project']}")
    print(f"Root: {payload['root']}")
    print(f"Sessions root: {payload['sessions_root']}")
    print(f"Auto mine: {payload['auto_mine']}")
    print(f"Enabled: {payload['enabled']}")
    print(f"Projects file: {payload['projects_file']}")
    return 0


def cmd_projects_list(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    profiles = load_project_profiles(config.projects_file)
    payload = [
        {
            "project": profile.normalized_name(),
            "root": str(profile.normalized_root()),
            "sessions_root": profile.sessions_root,
            "cwd_prefixes": [str(value) for value in profile.normalized_cwd_prefixes()],
            "mine_interval_seconds": profile.mine_interval_seconds,
            "auto_mine": profile.auto_mine,
            "enabled": profile.enabled,
        }
        for profile in profiles
    ]
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    if not payload:
        print(f"No configured projects in {config.projects_file}")
        return 0
    for item in payload:
        print(f"{item['project']}: root={item['root']} sessions_root={item['sessions_root']} enabled={item['enabled']}")
    return 0


def cmd_projects_run(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    progress = None if args.json else print
    results = run_projects_cycle(
        config=config,
        project_filter=args.project,
        dry_run=args.dry_run,
        retry_attempts=args.retry_attempts,
        retry_delay_seconds=args.retry_delay_seconds,
        progress=progress,
    )
    payload = [item.to_dict() for item in results]
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    if not results:
        print(f"No enabled projects configured in {config.projects_file}")
        return 0
    for item in results:
        print(f"Project: {item.project}")
        print(f"  Sync copied={item.sync.copied} updated={item.sync.updated} unchanged={item.sync.unchanged}")
        print(f"  Pending mine: {item.pending_mine}")
        if item.mined:
            print("  Mine: executed")
        else:
            print(f"  Mine: skipped ({item.mine_skipped_reason})")
    return 0


def cmd_mempalace_mine(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    mempalace_bin = args.mempalace_bin or config.mempalace_bin
    palace_dir = Path(args.palace_dir).expanduser().resolve() if args.palace_dir else config.palace_dir(project)
    staging_dir = Path(args.staging_dir).expanduser().resolve() if args.staging_dir else config.codex_sessions_dir(project)

    command = [
        mempalace_bin,
        "--palace",
        str(palace_dir),
        "mine",
        str(staging_dir),
        "--mode",
        "convos",
    ]
    if args.dry_run:
        if args.json:
            print(
                json.dumps(
                    {
                        "project": project,
                        "mempalace_bin": mempalace_bin,
                        "palace_dir": str(palace_dir),
                        "staging_dir": str(staging_dir),
                        "command": command,
                        "retry_attempts": max(args.retry_attempts, 1),
                        "retry_delay_seconds": max(args.retry_delay_seconds, 0.0),
                        "dry_run": True,
                    },
                    indent=2,
                    ensure_ascii=True,
                )
            )
            return 0
        print(" ".join(command))
        return 0

    result = run_mempalace_convo_mine(
        mempalace_bin=mempalace_bin,
        palace_dir=palace_dir,
        staging_dir=staging_dir,
        retry_attempts=args.retry_attempts,
        retry_delay_seconds=args.retry_delay_seconds,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "project": project,
                    "palace_dir": str(result.palace_dir),
                    "staging_dir": str(result.staging_dir),
                    "command": result.command,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "attempts": result.attempts,
                },
                indent=2,
                ensure_ascii=True,
            )
        )
        return 0

    print(f"Project: {project}")
    print(f"Palace dir: {result.palace_dir}")
    print(f"Staging dir: {result.staging_dir}")
    print(f"Attempts: {result.attempts}")
    print("Command:", " ".join(result.command))
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return 0


def cmd_palace_status(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    palace_dir = Path(args.palace_dir).expanduser().resolve() if args.palace_dir else config.palace_dir(project)
    exists = palace_dir.exists()
    files = [item for item in palace_dir.rglob("*") if item.is_file()] if exists else []
    drawers = read_palace_drawers(palace_dir, ingest_mode=None) if exists else []
    wings = sorted({drawer.wing for drawer in drawers if drawer.wing})
    rooms = sorted({f"{drawer.wing}/{drawer.room}" for drawer in drawers if drawer.wing and drawer.room})
    payload = {
        "project": project,
        "palace_dir": str(palace_dir),
        "exists": exists,
        "files": len(files),
        "drawers": len(drawers),
        "wings": len(wings),
        "rooms": len(rooms),
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {project}")
    print(f"Palace dir: {palace_dir}")
    print(f"Exists: {'yes' if exists else 'no'}")
    print(f"Files: {len(files)}")
    print(f"Drawers: {len(drawers)}")
    print(f"Wings: {len(wings)}")
    print(f"Rooms: {len(rooms)}")
    return 0


def cmd_palace_clean(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    palace_dir = Path(args.palace_dir).expanduser().resolve() if args.palace_dir else config.palace_dir(project)
    existed = palace_dir.exists()
    if args.dry_run:
        payload = {
            "project": project,
            "palace_dir": str(palace_dir),
            "existed": existed,
            "dry_run": True,
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=True))
            return 0
        print(f"would clean: {palace_dir}")
        return 0

    cleaned_dir = reset_palace_dir(palace_dir)
    payload = {
        "project": project,
        "palace_dir": str(cleaned_dir),
        "existed": existed,
        "cleaned": True,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {project}")
    print(f"Cleaned palace: {cleaned_dir}")
    return 0


def cmd_palace_rebuild(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    mempalace_bin = args.mempalace_bin or config.mempalace_bin
    palace_dir = Path(args.palace_dir).expanduser().resolve() if args.palace_dir else config.palace_dir(project)
    staging_dir = Path(args.staging_dir).expanduser().resolve() if args.staging_dir else config.codex_sessions_dir(project)
    command = [
        mempalace_bin,
        "--palace",
        str(palace_dir),
        "mine",
        str(staging_dir),
        "--mode",
        "convos",
    ]
    if args.dry_run:
        payload = {
            "project": project,
            "palace_dir": str(palace_dir),
            "staging_dir": str(staging_dir),
            "command": command,
            "dry_run": True,
            "clean_first": True,
            "retry_attempts": max(args.retry_attempts, 1),
            "retry_delay_seconds": max(args.retry_delay_seconds, 0.0),
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=True))
            return 0
        print(f"would clean: {palace_dir}")
        print("would run:", " ".join(command))
        return 0

    reset_palace_dir(palace_dir)
    result = run_mempalace_convo_mine(
        mempalace_bin=mempalace_bin,
        palace_dir=palace_dir,
        staging_dir=staging_dir,
        retry_attempts=args.retry_attempts,
        retry_delay_seconds=args.retry_delay_seconds,
    )
    payload = {
        "project": project,
        "palace_dir": str(result.palace_dir),
        "staging_dir": str(result.staging_dir),
        "command": result.command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "attempts": result.attempts,
        "clean_first": True,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {project}")
    print(f"Rebuilt palace: {result.palace_dir}")
    print(f"Staging dir: {result.staging_dir}")
    print(f"Attempts: {result.attempts}")
    print("Command:", " ".join(result.command))
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return 0


def cmd_palace_retry(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    mempalace_bin = args.mempalace_bin or config.mempalace_bin
    palace_dir = Path(args.palace_dir).expanduser().resolve() if args.palace_dir else config.palace_dir(project)
    staging_dir = Path(args.staging_dir).expanduser().resolve() if args.staging_dir else config.codex_sessions_dir(project)
    command = [
        mempalace_bin,
        "--palace",
        str(palace_dir),
        "mine",
        str(staging_dir),
        "--mode",
        "convos",
    ]
    if args.dry_run:
        payload = {
            "project": project,
            "palace_dir": str(palace_dir),
            "staging_dir": str(staging_dir),
            "command": command,
            "dry_run": True,
            "clean_first": False,
            "retry_attempts": max(args.retry_attempts, 1),
            "retry_delay_seconds": max(args.retry_delay_seconds, 0.0),
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=True))
            return 0
        print("would run:", " ".join(command))
        return 0

    result = run_mempalace_convo_mine(
        mempalace_bin=mempalace_bin,
        palace_dir=palace_dir,
        staging_dir=staging_dir,
        retry_attempts=args.retry_attempts,
        retry_delay_seconds=args.retry_delay_seconds,
    )
    payload = {
        "project": project,
        "palace_dir": str(result.palace_dir),
        "staging_dir": str(result.staging_dir),
        "command": result.command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "attempts": result.attempts,
        "clean_first": False,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {project}")
    print(f"Retried palace mine: {result.palace_dir}")
    print(f"Staging dir: {result.staging_dir}")
    print(f"Attempts: {result.attempts}")
    print("Command:", " ".join(result.command))
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return 0


def cmd_palace_export(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    palace_dir = Path(args.palace_dir).expanduser().resolve() if args.palace_dir else config.palace_dir(project)
    limit = args.limit if args.limit and args.limit > 0 else None
    drawers = read_palace_drawers(
        palace_dir,
        ingest_mode=args.ingest_mode,
        wing=args.wing,
        room=args.room,
        limit=limit,
    )
    payload = {
        "project": project,
        "palace_dir": str(palace_dir),
        "ingest_mode": args.ingest_mode,
        "wing": args.wing,
        "room": args.room,
        "count": len(drawers),
        "drawers": [drawer.to_dict() for drawer in drawers],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {project}")
    print(f"Palace dir: {palace_dir}")
    print(f"Count: {len(drawers)}")
    for drawer in drawers:
        print(f"- {drawer.drawer_id} | wing={drawer.wing or '?'} | room={drawer.room or '?'}")
        if drawer.source_file:
            print(f"  source_file={drawer.source_file}")
        if drawer.filed_at:
            print(f"  filed_at={drawer.filed_at}")
    return 0


def cmd_palace_package(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    palace_dir = Path(args.palace_dir).expanduser().resolve() if args.palace_dir else config.palace_dir(project)
    limit = args.limit if args.limit and args.limit > 0 else None
    drawers = read_palace_drawers(
        palace_dir,
        ingest_mode=args.ingest_mode,
        wing=args.wing,
        room=args.room,
        limit=limit,
    )
    packages = [
        build_room_package_from_drawers(
            project=project,
            wing=wing,
            room=room,
            drawers=group_drawers,
            hall_id=args.hall_id,
        )
        for (wing, room), group_drawers in sorted(group_drawers_by_room(drawers).items())
    ]
    package_payloads = [package_to_dict(item) for item in packages]

    written_paths: list[Path] = []
    if args.write_inbox:
        written_paths = write_package_payloads(package_payloads, config.inbox_promoted_dir)

    payload = {
        "project": project,
        "palace_dir": str(palace_dir),
        "drawers": len(drawers),
        "packages": package_payloads,
        "written": [str(path) for path in written_paths],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {project}")
    print(f"Palace dir: {palace_dir}")
    print(f"Drawers: {len(drawers)}")
    print(f"Packages: {len(package_payloads)}")
    for package in package_payloads:
        print(f"- {package['room_id']} -> {package['room_title']}")
    for path in written_paths:
        print(f"written: {path}")
    return 0


def cmd_palace_run(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    palace_dir = Path(args.palace_dir).expanduser().resolve() if args.palace_dir else config.palace_dir(project)
    limit = args.limit if args.limit and args.limit > 0 else None
    graphify_bin = args.graphify_bin or config.graphify_bin

    drawers = read_palace_drawers(
        palace_dir,
        ingest_mode=args.ingest_mode,
        wing=args.wing,
        room=args.room,
        limit=limit,
    )
    packages = [
        build_room_package_from_drawers(
            project=project,
            wing=wing,
            room=room_name,
            drawers=group_drawers,
            hall_id=args.hall_id,
        )
        for (wing, room_name), group_drawers in sorted(group_drawers_by_room(drawers).items())
    ]
    package_payloads = [package_to_dict(item) for item in packages]
    written_paths = [config.inbox_promoted_dir / f"palace-{package['room_id']}.json" for package in package_payloads]
    command = _graphify_command(graphify_bin, config.corpus_project_dir(project), args)

    if args.dry_run:
        payload = {
            "project": project,
            "palace_dir": str(palace_dir),
            "drawers": len(drawers),
            "packages": len(package_payloads),
            "write_targets": [str(path) for path in written_paths],
            "build_command": None if args.no_build else command,
            "dry_run": True,
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=True))
            return 0
        print(f"Project: {project}")
        print(f"Palace dir: {palace_dir}")
        print(f"Drawers: {len(drawers)}")
        print(f"Packages: {len(package_payloads)}")
        for path in written_paths:
            print(f"would write: {path}")
        if not args.no_build:
            print("would build:", " ".join(command))
        return 0

    written_paths = write_package_payloads(package_payloads, config.inbox_promoted_dir)
    promote_results = []
    for path in written_paths:
        promote_results.extend(
            promote_file(
                config=config,
                source=path,
                project_override=project,
                allow_non_project=False,
                archive=False,
            )
        )

    build_payload: dict[str, object] | None = None
    if not args.no_build:
        result = run_graphify(
            graphify_bin=graphify_bin,
            project_dir=config.corpus_project_dir(project),
            update=args.update,
            wiki=args.wiki,
            obsidian=args.obsidian,
            mcp=args.mcp,
        )
        build_payload = {
            "command": result.command,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    payload = {
        "project": project,
        "palace_dir": str(palace_dir),
        "drawers": len(drawers),
        "packages": len(package_payloads),
        "written": [str(path) for path in written_paths],
        "promoted": [
            {
                "room_id": item.room_id,
                "output": str(item.output),
                "changed": item.changed,
            }
            for item in promote_results
        ],
        "build": build_payload,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {project}")
    print(f"Palace dir: {palace_dir}")
    print(f"Drawers: {len(drawers)}")
    print(f"Packages: {len(package_payloads)}")
    for path in written_paths:
        print(f"written: {path}")
    _print_promote_results(promote_results)
    if build_payload is not None:
        print("Graphify build completed")
        print("Command:", " ".join(build_payload["command"]))
        if isinstance(build_payload["stdout"], str) and build_payload["stdout"].strip():
            print(build_payload["stdout"].rstrip())
        if isinstance(build_payload["stderr"], str) and build_payload["stderr"].strip():
            print(build_payload["stderr"].rstrip(), file=sys.stderr)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    project_dir = config.corpus_project_dir(project)
    promoted_files = list(config.promoted_dir(project).glob("*.md"))
    document_files = [item for item in config.documents_dir(project).rglob("*") if item.is_file()]
    import_files = [item for item in config.imports_dir(project).rglob("*") if item.is_file()]
    inbox_files = [item for item in config.inbox_dir.rglob("*") if item.is_file()]
    staged_codex_sessions = [item for item in config.codex_sessions_dir(project).rglob("*.jsonl") if item.is_file()]
    graphify_available = shutil.which(config.graphify_bin) is not None
    mempalace_available = shutil.which(config.mempalace_bin) is not None
    payload = {
        "workspace": str(config.workspace),
        "project": project,
        "project_dir": str(project_dir),
        "inbox_promoted_dir": str(config.inbox_promoted_dir),
        "inbox_documents_dir": str(config.inbox_documents_dir),
        "palace_dir": str(config.palace_dir(project)),
        "promoted_rooms": len(promoted_files),
        "documents": len(document_files),
        "imports": len(import_files),
        "inbox_files": len(inbox_files),
        "codex_staged_sessions": len(staged_codex_sessions),
        "graphify": {
            "bin": config.graphify_bin,
            "available": graphify_available,
        },
        "mempalace": {
            "bin": config.mempalace_bin,
            "available": mempalace_available,
        },
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(f"Workspace: {payload['workspace']}")
    print(f"Project: {payload['project']}")
    print(f"Project dir: {payload['project_dir']}")
    print(f"Inbox promoted dir: {payload['inbox_promoted_dir']}")
    print(f"Inbox documents dir: {payload['inbox_documents_dir']}")
    print(f"Palace dir: {payload['palace_dir']}")
    print(f"Promoted rooms: {payload['promoted_rooms']}")
    print(f"Documents: {payload['documents']}")
    print(f"Imports: {payload['imports']}")
    print(f"Inbox files: {payload['inbox_files']}")
    print(f"Codex staged sessions: {payload['codex_staged_sessions']}")
    print(f"Graphify available: {'yes' if graphify_available else 'no'} ({config.graphify_bin})")
    print(f"MemPalace available: {'yes' if mempalace_available else 'no'} ({config.mempalace_bin})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValidationError, ValueError, GraphifyError, MemPalaceError, PalaceReadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
