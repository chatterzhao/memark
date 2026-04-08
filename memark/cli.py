"""Command line interface for MemArk."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .graphify import GraphifyError, run_graphify
from .io import copy_document
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


def cmd_init(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    config = create_workspace(workspace=workspace, project=args.project, graphify_bin=args.graphify_bin)
    print(f"Initialized MemArk workspace: {config.workspace}")
    print(f"Default project: {config.default_project}")
    print(f"Inbox: {config.inbox_dir}")
    print(f"Inbox promoted: {config.inbox_promoted_dir}")
    print(f"Inbox documents: {config.inbox_documents_dir}")
    print(f"Corpus: {config.corpus_project_dir()}")
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
    project = slugify(args.project or config.default_project)

    promote_results = promote_path(
        config=config,
        path=config.inbox_promoted_dir,
        project_override=project,
        allow_non_project=args.allow_non_project,
        archive=args.archive,
    )
    _print_promote_results(promote_results)

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


def cmd_status(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    project_dir = config.corpus_project_dir(project)
    promoted_files = list(config.promoted_dir(project).glob("*.md"))
    document_files = [item for item in config.documents_dir(project).iterdir() if item.is_file()]
    import_files = [item for item in config.imports_dir(project).iterdir() if item.is_file()]
    inbox_files = [item for item in config.inbox_dir.rglob("*") if item.is_file()]
    graphify_available = shutil.which(config.graphify_bin) is not None
    payload = {
        "workspace": str(config.workspace),
        "project": project,
        "project_dir": str(project_dir),
        "inbox_promoted_dir": str(config.inbox_promoted_dir),
        "inbox_documents_dir": str(config.inbox_documents_dir),
        "promoted_rooms": len(promoted_files),
        "documents": len(document_files),
        "imports": len(import_files),
        "inbox_files": len(inbox_files),
        "graphify": {
            "bin": config.graphify_bin,
            "available": graphify_available,
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
    print(f"Promoted rooms: {payload['promoted_rooms']}")
    print(f"Documents: {payload['documents']}")
    print(f"Imports: {payload['imports']}")
    print(f"Inbox files: {payload['inbox_files']}")
    print(f"Graphify available: {'yes' if graphify_available else 'no'} ({config.graphify_bin})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValidationError, ValueError, GraphifyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
