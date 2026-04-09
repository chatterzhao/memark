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
from .mempalace import MemPalaceError, run_mempalace_convo_mine
from .models import ValidationError
from .promote import load_room_packages, promote_path
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
    mempalace_parser.add_argument("--dry-run", action="store_true", help="Print the MemPalace command without executing it")
    mempalace_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    mempalace_parser.set_defaults(func=cmd_mempalace_mine)

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
                },
                indent=2,
                ensure_ascii=True,
            )
        )
        return 0

    print(f"Project: {project}")
    print(f"Palace dir: {result.palace_dir}")
    print(f"Staging dir: {result.staging_dir}")
    print("Command:", " ".join(result.command))
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
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
    except (FileNotFoundError, ValidationError, ValueError, GraphifyError, MemPalaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
