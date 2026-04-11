"""Command line interface for MemArk."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .automation import _render_context_markdown, load_automation_context, run_automation_cycle
from .corpus import search_payload, search_project_corpus
from .codex import sync_codex_sessions
from .graphify import GraphifyError, run_graphify
from .handoff import build_graphify_handoff
from .install import InstallError, install_memark, run_doctor
from .io import copy_document
from .mempalace import MemPalaceError, reset_palace_dir, run_mempalace_convo_mine
from .models import ValidationError
from .package_builder import (
    build_session_package_from_drawers,
    build_room_package_from_drawers,
    group_drawers_by_logical_session,
    group_drawers_by_room,
    package_to_dict,
    write_package_payloads,
)
from .palace import PalaceReadError, read_palace_drawers
from .project_registry import (
    ProjectProfile,
    load_cycle_state,
    load_project_profiles,
    run_projects_cycle,
    upsert_project_profile,
)
from .promote import load_room_packages, promote_file, promote_path
from .service import (
    ServiceInstallResult,
    resolve_scheduler,
    install_launchd_service,
    status_launchd_service,
    uninstall_launchd_service,
)
from .version import __version__
from .workspace import create_workspace, load_workspace, resolve_workspace, slugify


WORKTREE_ATTACH_CANDIDATES = (
    ".memark",
    ".mempalace",
    ".codex",
    ".claude",
    "AGENTS.md",
)

WORKTREE_HOOK_BEGIN = "# >>> memark worktree attach >>>"
WORKTREE_HOOK_END = "# <<< memark worktree attach <<<"
MEMARK_ATTACH_FILES = (
    "config.json",
    "projects.toml",
)


def _copy_attach_candidate(source: Path, destination: Path) -> None:
    if source.name == ".memark" and source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for name in MEMARK_ATTACH_FILES:
            child = source / name
            if child.exists():
                shutil.copy2(child, destination / name)
        return
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _attach_worktree_configs(source_dir: Path, target_dir: Path) -> dict[str, list[str]]:
    copied: list[str] = []
    skipped: list[str] = []
    for name in WORKTREE_ATTACH_CANDIDATES:
        source = source_dir / name
        destination = target_dir / name
        if not source.exists():
            skipped.append(name)
            continue
        _copy_attach_candidate(source, destination)
        copied.append(name)
    return {"copied": copied, "skipped": skipped}


def _git_common_dir(source_dir: Path) -> Path:
    completed = subprocess.run(
        ["git", "-C", str(source_dir), "rev-parse", "--git-common-dir"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git rev-parse failed"
        raise RuntimeError(detail)
    resolved = completed.stdout.strip()
    if not resolved:
        raise RuntimeError("git rev-parse --git-common-dir returned an empty path")
    common_dir = Path(resolved)
    if not common_dir.is_absolute():
        common_dir = (source_dir / common_dir).resolve()
    return common_dir


def _memark_hook_invocation() -> str:
    package_root = Path(__file__).resolve().parents[1]
    if (package_root / "pyproject.toml").exists():
        return f"PYTHONPATH={shlex.quote(str(package_root))} {shlex.quote(sys.executable)} -m memark"
    argv0 = Path(sys.argv[0]).resolve()
    if argv0.name.startswith("python"):
        return f"{shlex.quote(sys.executable)} -m memark"
    return shlex.quote(str(argv0))


def _render_worktree_hook_block(source_dir: Path) -> str:
    invocation = _memark_hook_invocation()
    source = shlex.quote(str(source_dir.resolve()))
    return (
        f"{WORKTREE_HOOK_BEGIN}\n"
        f"MEMARK_SOURCE_DIR={source}\n"
        "if [ \"$PWD\" != \"$MEMARK_SOURCE_DIR\" ]; then\n"
        f"  {invocation} worktree-attach --source-dir \"$MEMARK_SOURCE_DIR\" --target-dir \"$PWD\" >/dev/null 2>&1 || true\n"
        "fi\n"
        f"{WORKTREE_HOOK_END}\n"
    )


def _install_worktree_hook(source_dir: Path) -> Path:
    common_dir = _git_common_dir(source_dir)
    hook_path = common_dir / "hooks" / "post-checkout"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    block = _render_worktree_hook_block(source_dir)
    existing = hook_path.read_text(encoding="utf-8") if hook_path.exists() else "#!/bin/sh\n"

    if WORKTREE_HOOK_BEGIN in existing and WORKTREE_HOOK_END in existing:
        start = existing.index(WORKTREE_HOOK_BEGIN)
        end = existing.index(WORKTREE_HOOK_END) + len(WORKTREE_HOOK_END)
        prefix = existing[:start].rstrip()
        suffix = existing[end:].lstrip("\n")
        parts = [part for part in (prefix, block.rstrip(), suffix) if part]
        updated = "\n\n".join(parts).rstrip() + "\n"
    else:
        prefix = existing.rstrip()
        parts = [part for part in (prefix, block.rstrip()) if part]
        updated = "\n\n".join(parts).rstrip() + "\n"

    hook_path.write_text(updated, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | 0o111)
    return hook_path


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

    install_parser = subparsers.add_parser(
        "install",
        help="Install MemArk as a user-level runtime plus AI skill bundle",
    )
    install_parser.add_argument(
        "--platform",
        default="auto",
        help="Target AI platform: auto, codex, claude, or all",
    )
    install_parser.add_argument("--memark-home", help="Override MemArk user-level home directory")
    install_parser.add_argument("--python-command", help="Python launcher used to create the runtime venv")
    install_parser.add_argument("--source-spec", help="Package source passed to pip for MemArk itself")
    install_parser.add_argument(
        "--skip-runtime-install",
        action="store_true",
        help="Only install the skill bundle; do not recreate the runtime venv",
    )
    install_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    install_parser.set_defaults(func=cmd_install)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check user-level MemArk runtime and installed skill bundle health",
    )
    doctor_parser.add_argument(
        "--platform",
        default="auto",
        help="Target AI platform: auto, codex, claude, or all",
    )
    doctor_parser.add_argument("--memark-home", help="Override MemArk user-level home directory")
    doctor_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    doctor_parser.set_defaults(func=cmd_doctor)

    service_install_parser = subparsers.add_parser(
        "service-install",
        help="Install a user-level scheduler that repeatedly runs 'memark automation-run'",
    )
    service_install_parser.add_argument("--workspace", default=".", help="Workspace directory")
    service_install_parser.add_argument("--project", help="Only run one configured project")
    service_install_parser.add_argument(
        "--scheduler",
        default="auto",
        help="Scheduler backend: auto or launchd",
    )
    service_install_parser.add_argument(
        "--interval-seconds",
        type=int,
        default=300,
        help="Minimum repeat interval for projects-run; launchd uses a minimum of 60 seconds",
    )
    service_install_parser.add_argument("--dry-run", action="store_true", help="Render the scheduler config without installing it")
    service_install_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    service_install_parser.set_defaults(func=cmd_service_install)

    service_status_parser = subparsers.add_parser(
        "service-status",
        help="Show user-level automation-run scheduler status for a workspace",
    )
    service_status_parser.add_argument("--workspace", default=".", help="Workspace directory")
    service_status_parser.add_argument("--project", help="Only inspect the project-specific scheduler label")
    service_status_parser.add_argument(
        "--scheduler",
        default="auto",
        help="Scheduler backend: auto or launchd",
    )
    service_status_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    service_status_parser.set_defaults(func=cmd_service_status)

    service_uninstall_parser = subparsers.add_parser(
        "service-uninstall",
        help="Remove a user-level automation-run scheduler for a workspace",
    )
    service_uninstall_parser.add_argument("--workspace", default=".", help="Workspace directory")
    service_uninstall_parser.add_argument("--project", help="Only remove the project-specific scheduler label")
    service_uninstall_parser.add_argument(
        "--scheduler",
        default="auto",
        help="Scheduler backend: auto or launchd",
    )
    service_uninstall_parser.add_argument("--dry-run", action="store_true", help="Render the target scheduler label without removing it")
    service_uninstall_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    service_uninstall_parser.set_defaults(func=cmd_service_uninstall)

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

    query_parser = subparsers.add_parser(
        "query",
        help="Search promoted project corpus content without relying on Graphify",
    )
    query_parser.add_argument("query", help="Fixed-string search query")
    query_parser.add_argument("--workspace", default=".", help="Workspace directory")
    query_parser.add_argument("--project", help="Target project slug")
    query_parser.add_argument(
        "--scope",
        choices=("all", "promoted", "documents", "imports"),
        default="all",
        help="Corpus scope to search",
    )
    query_parser.add_argument("--limit", type=int, default=10, help="Maximum number of hits to return")
    query_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    query_parser.set_defaults(func=cmd_query)

    context_parser = subparsers.add_parser(
        "context",
        help="Refresh and render the current automatic consumption context for one project",
    )
    context_parser.add_argument("--workspace", default=".", help="Workspace directory")
    context_parser.add_argument("--project", help="Target project slug")
    context_parser.add_argument("--no-refresh", action="store_true", help="Read existing automation artifacts without running a fresh cycle")
    context_parser.add_argument("--retry-attempts", type=int, default=3, help="Retry mine on lock errors up to N attempts")
    context_parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=0.2,
        help="Initial retry delay for lock errors; doubles after each retry",
    )
    context_parser.add_argument("--graphify-bin", help="Override graphify executable name")
    context_parser.add_argument("--build", action="store_true", help="Attempt Graphify update during the refresh")
    context_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    context_parser.set_defaults(func=cmd_context)

    handoff_parser = subparsers.add_parser(
        "graphify-handoff",
        help="Render a Graphify skill handoff for the prepared project corpus",
    )
    handoff_parser.add_argument("--workspace", default=".", help="Workspace directory")
    handoff_parser.add_argument("--project", help="Target project slug")
    handoff_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    handoff_parser.set_defaults(func=cmd_graphify_handoff)

    build_parser = subparsers.add_parser(
        "build",
        help="Run a compatible Graphify step for a project corpus",
    )
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
        help="Scan Codex sessions, match them to one tracked directory path, and sync them into staging",
    )
    codex_parser.add_argument("--workspace", default=".", help="Workspace directory")
    codex_parser.add_argument("--project", help="Target project slug")
    codex_parser.add_argument(
        "--path",
        dest="tracked_path",
        help="Absolute or relative directory path used to match session_meta.payload.cwd",
    )
    codex_parser.add_argument(
        "--project-root",
        dest="tracked_path_compat",
        help=argparse.SUPPRESS,
    )
    codex_parser.add_argument(
        "--sessions-root",
        default="~/.codex/sessions",
        help="Root directory that contains Codex rollout JSONL files",
    )
    codex_parser.add_argument(
        "--extra-path",
        action="append",
        default=[],
        help="Additional directory paths that should map into the same tracked unit",
    )
    codex_parser.add_argument(
        "--cwd-prefix",
        dest="extra_path_compat",
        action="append",
        default=[],
        help=argparse.SUPPRESS,
    )
    codex_parser.add_argument("--dry-run", action="store_true", help="Scan and report without writing staging or ledger")
    codex_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    codex_parser.set_defaults(func=cmd_codex_sync)

    project_set_parser = subparsers.add_parser(
        "project-set",
        help="Create or update a tracked-path registry entry for single-cycle sync and mine orchestration",
    )
    project_set_parser.add_argument("--workspace", default=".", help="Workspace directory")
    project_set_parser.add_argument("--project", required=True, help="Project slug")
    project_set_parser.add_argument(
        "--path",
        dest="tracked_path",
        help="Tracked directory path used to match session_meta.payload.cwd",
    )
    project_set_parser.add_argument(
        "--root",
        dest="tracked_path_compat",
        help=argparse.SUPPRESS,
    )
    project_set_parser.add_argument(
        "--sessions-root",
        default="~/.codex/sessions",
        help="Root directory that contains Codex rollout JSONL files",
    )
    project_set_parser.add_argument(
        "--extra-path",
        action="append",
        default=[],
        help="Additional directory paths that should map into the same tracked unit",
    )
    project_set_parser.add_argument(
        "--cwd-prefix",
        dest="extra_path_compat",
        action="append",
        default=[],
        help=argparse.SUPPRESS,
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

    worktree_attach_parser = subparsers.add_parser(
        "worktree-attach",
        help="Copy MemArk, MemPalace, and Graphify-facing config files from one directory into another",
    )
    worktree_attach_parser.add_argument("--source-dir", required=True, help="Source directory to copy config from")
    worktree_attach_parser.add_argument("--target-dir", required=True, help="Target directory to receive copied config")
    worktree_attach_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    worktree_attach_parser.set_defaults(func=cmd_worktree_attach)

    worktree_hook_parser = subparsers.add_parser(
        "worktree-hook-install",
        help="Install a git post-checkout hook that auto-attaches MemArk config into new worktrees",
    )
    worktree_hook_parser.add_argument("--source-dir", required=True, help="Repository directory used as the config source")
    worktree_hook_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    worktree_hook_parser.set_defaults(func=cmd_worktree_hook_install)

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

    automation_run_parser = subparsers.add_parser(
        "automation-run",
        help="Run one automatic feed/process/consume cycle across enabled projects",
    )
    automation_run_parser.add_argument("--workspace", default=".", help="Workspace directory")
    automation_run_parser.add_argument("--project", help="Only run one configured project")
    automation_run_parser.add_argument("--retry-attempts", type=int, default=3, help="Retry mine on lock errors up to N attempts")
    automation_run_parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=0.2,
        help="Initial retry delay for lock errors; doubles after each retry",
    )
    automation_run_parser.add_argument("--graphify-bin", help="Override graphify executable name")
    automation_run_parser.add_argument("--no-build", action="store_true", help="Do not attempt Graphify update during automation")
    automation_run_parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    automation_run_parser.set_defaults(func=cmd_automation_run)

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
        "--group-by",
        choices=("room", "session"),
        default="room",
        help="Package drawers by MemPalace room or by logical source session",
    )
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
    palace_run_parser.add_argument(
        "--group-by",
        choices=("room", "session"),
        default="room",
        help="Package drawers by MemPalace room or by logical source session",
    )
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


def cmd_install(args: argparse.Namespace) -> int:
    result = install_memark(
        platform=args.platform,
        memark_home=Path(args.memark_home) if args.memark_home else None,
        python_command=args.python_command,
        source_spec=args.source_spec,
        skip_runtime_install=args.skip_runtime_install,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
        return 0

    print(f"MemArk home: {result.memark_home}")
    print(f"Runtime venv: {result.venv_dir}")
    print(f"Python: {result.python_bin}")
    print(f"MemArk: {result.memark_bin}")
    print(f"MemPalace: {result.mempalace_bin}")
    print(f"Graphify: {result.graphify_bin}")
    print(f"Source spec: {result.source_spec}")
    for target in result.targets:
        print(f"Installed skill bundle: {target.platform} -> {target.bundle_dir}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    result = run_doctor(
        platform=args.platform,
        memark_home=Path(args.memark_home) if args.memark_home else None,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
        return 0 if result.ok() else 1

    print(f"MemArk home: {result.memark_home}")
    print(f"Runtime venv: {result.venv_dir}")
    print(f"Python: {result.python_bin}")
    print(f"MemArk: {result.memark_bin}")
    print(f"MemPalace: {result.mempalace_bin}")
    print(f"Graphify: {result.graphify_bin}")
    for target in result.targets:
        print(f"Skill bundle: {target.platform} -> {target.bundle_dir}")
    if result.issues:
        print("Doctor issues:", file=sys.stderr)
        for issue in result.issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print("Doctor summary: ok")
    return 0


def _print_service_install_result(result: ServiceInstallResult) -> None:
    print(f"Scheduler: {result.scheduler}")
    print(f"Workspace: {result.workspace}")
    if result.project is not None:
        print(f"Project: {result.project}")
    print(f"Label: {result.label}")
    print(f"Interval seconds: {result.interval_seconds}")
    print(f"Plist path: {result.plist_path}")
    print(f"Stdout log: {result.stdout_path}")
    print(f"Stderr log: {result.stderr_path}")
    print("Command:", " ".join(result.command))
    if result.environment:
        print("Environment:")
        for key, value in sorted(result.environment.items()):
            print(f"  {key}={value}")
    print(f"Loaded: {result.loaded}")


def cmd_service_install(args: argparse.Namespace) -> int:
    try:
        scheduler = resolve_scheduler(args.scheduler)
        workspace = resolve_workspace(args.workspace)
        project = slugify(args.project) if args.project else None
        if scheduler != "launchd":
            raise InstallError(f"Unsupported scheduler '{scheduler}'")
        result = install_launchd_service(
            workspace,
            project=project,
            interval_seconds=max(int(args.interval_seconds), 60),
            dry_run=args.dry_run,
        )
    except InstallError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
        return 0
    _print_service_install_result(result)
    return 0


def cmd_service_status(args: argparse.Namespace) -> int:
    try:
        scheduler = resolve_scheduler(args.scheduler)
        workspace = resolve_workspace(args.workspace)
        project = slugify(args.project) if args.project else None
        if scheduler != "launchd":
            raise InstallError(f"Unsupported scheduler '{scheduler}'")
        result = status_launchd_service(workspace, project=project)
    except InstallError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
        return 0
    print(f"Scheduler: {result.scheduler}")
    print(f"Workspace: {result.workspace}")
    if result.project is not None:
        print(f"Project: {result.project}")
    print(f"Label: {result.label}")
    print(f"Installed: {result.installed}")
    print(f"Loaded: {result.loaded}")
    print(f"Plist path: {result.plist_path}")
    print("Command:", " ".join(result.command))
    return 0


def cmd_service_uninstall(args: argparse.Namespace) -> int:
    try:
        scheduler = resolve_scheduler(args.scheduler)
        workspace = resolve_workspace(args.workspace)
        project = slugify(args.project) if args.project else None
        if scheduler != "launchd":
            raise InstallError(f"Unsupported scheduler '{scheduler}'")
        result = uninstall_launchd_service(workspace, project=project, dry_run=args.dry_run)
    except InstallError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
        return 0
    print(f"Scheduler: {result.scheduler}")
    print(f"Workspace: {result.workspace}")
    if result.project is not None:
        print(f"Project: {result.project}")
    print(f"Label: {result.label}")
    print(f"Plist path: {result.plist_path}")
    print(f"Removed: {result.removed}")
    print(f"Unloaded: {result.unloaded}")
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


def _query_scopes(scope: str) -> tuple[str, ...]:
    if scope == "all":
        return ("promoted", "documents", "imports")
    return (scope,)


def cmd_query(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    scopes = _query_scopes(args.scope)
    if args.json:
        payload = search_payload(
            config,
            project=args.project,
            query=args.query,
            scopes=scopes,
            limit=max(args.limit, 1),
        )
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    hits = search_project_corpus(
        config,
        project=args.project,
        query=args.query,
        scopes=scopes,
        limit=max(args.limit, 1),
    )
    if not hits:
        print(f'No corpus hits for "{args.query}"')
        return 0

    print(f'Corpus hits for "{args.query}":')
    for index, hit in enumerate(hits, start=1):
        print(f"{index}. [{hit.scope}] {hit.title}")
        print(f"   Path: {hit.path}")
        print(f"   Line: {hit.line_number}  Occurrences: {hit.occurrences}")
        print(f"   Snippet: {hit.snippet}")
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    payload = load_automation_context(
        config,
        project=project,
        refresh=not args.no_refresh,
        retry_attempts=args.retry_attempts,
        retry_delay_seconds=args.retry_delay_seconds,
        graphify_bin=args.graphify_bin,
        build_graph=args.build,
    )
    if args.json:
        print(json.dumps(payload.to_dict(), indent=2, ensure_ascii=True))
        return 0

    print(_render_context_markdown(payload.project, payload.sections, payload.files), end="")
    return 0


def cmd_graphify_handoff(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    handoff = build_graphify_handoff(project, config.corpus_project_dir(project))

    if args.json:
        print(json.dumps(handoff.to_dict(), indent=2, ensure_ascii=True))
        return 0

    print(f"Graphify handoff target: {handoff.corpus_dir}")
    print(f"Recommended command: {handoff.recommended_command}")
    print("Corpus summary:")
    for item in handoff.inventories:
        print(f"  {item.scope}: {item.files} files, ~{item.words} words")
    print(f"  code files: {handoff.code_files}")
    print()
    print("Prompt:")
    print(handoff.prompt)
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
    print("Graphify step completed")
    print("Mode:", result.mode)
    print("Command:", " ".join(result.command))
    if result.mode == "watch-fallback":
        print(
            "Note: Graphify folder build was unavailable; MemArk used "
            "graphify.watch._rebuild_code instead. This path rebuilds code graphs "
            "only and does not prove promoted markdown entered the graph."
        )
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
    print("Graphify step completed")
    print("Mode:", result.mode)
    print("Command:", " ".join(result.command))
    if result.mode == "watch-fallback":
        print(
            "Note: Graphify folder build was unavailable; MemArk used "
            "graphify.watch._rebuild_code instead. This path rebuilds code graphs "
            "only and does not prove promoted markdown entered the graph."
        )
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return 0


def cmd_codex_sync(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    project = slugify(args.project or config.default_project)
    tracked_path = args.tracked_path or args.tracked_path_compat
    if not tracked_path:
        print("codex-sync requires --path", file=sys.stderr)
        return 2
    extra_paths = [*args.extra_path_compat, *args.extra_path]
    result = sync_codex_sessions(
        config=config,
        project=project,
        tracked_path=Path(tracked_path),
        sessions_root=Path(args.sessions_root),
        extra_paths=[Path(value) for value in extra_paths],
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
        return 0

    print(f"Project: {result.project}")
    print(f"Tracked path: {result.tracked_path}")
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
    tracked_path = args.tracked_path or args.tracked_path_compat
    if not tracked_path:
        print("project-set requires --path", file=sys.stderr)
        return 2
    extra_paths = [*args.extra_path_compat, *args.extra_path]
    profiles = upsert_project_profile(
        config.projects_file,
        ProjectProfile(
            name=args.project,
            path=tracked_path,
            sessions_root=args.sessions_root,
            extra_paths=extra_paths,
            mine_interval_seconds=max(args.mine_interval_seconds, 0),
            auto_mine=not args.no_auto_mine,
            enabled=not args.disabled,
        ),
    )
    current = next(profile for profile in profiles if profile.normalized_name() == slugify(args.project))
    payload = {
        "project": current.normalized_name(),
        "path": str(current.normalized_path()),
        "sessions_root": current.sessions_root,
        "extra_paths": [str(value) for value in current.normalized_extra_paths()],
        "mine_interval_seconds": current.mine_interval_seconds,
        "auto_mine": current.auto_mine,
        "enabled": current.enabled,
        "projects_file": str(config.projects_file),
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    print(f"Project registry updated: {payload['project']}")
    print(f"Path: {payload['path']}")
    print(f"Sessions root: {payload['sessions_root']}")
    print(f"Auto mine: {payload['auto_mine']}")
    print(f"Enabled: {payload['enabled']}")
    print(f"Projects file: {payload['projects_file']}")
    return 0


def cmd_worktree_attach(args: argparse.Namespace) -> int:
    source_dir = Path(args.source_dir).expanduser().resolve()
    target_dir = Path(args.target_dir).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Source directory does not exist: {source_dir}", file=sys.stderr)
        return 1
    target_dir.mkdir(parents=True, exist_ok=True)
    result = _attach_worktree_configs(source_dir, target_dir)
    payload = {
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "copied": result["copied"],
        "skipped": result["skipped"],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    print(f"Source dir: {payload['source_dir']}")
    print(f"Target dir: {payload['target_dir']}")
    print(f"Copied: {', '.join(payload['copied']) if payload['copied'] else '(none)'}")
    print(f"Skipped: {', '.join(payload['skipped']) if payload['skipped'] else '(none)'}")
    return 0


def cmd_worktree_hook_install(args: argparse.Namespace) -> int:
    source_dir = Path(args.source_dir).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Source directory does not exist: {source_dir}", file=sys.stderr)
        return 1
    try:
        hook_path = _install_worktree_hook(source_dir)
    except RuntimeError as exc:
        print(f"Failed to install worktree hook: {exc}", file=sys.stderr)
        return 1
    payload = {
        "source_dir": str(source_dir),
        "hook_path": str(hook_path),
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    print(f"Source dir: {payload['source_dir']}")
    print(f"Hook path: {payload['hook_path']}")
    return 0


def cmd_projects_list(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    profiles = load_project_profiles(config.projects_file)
    states = load_cycle_state(config.project_cycle_state_file)
    payload = [
        {
            "project": profile.normalized_name(),
            "path": str(profile.normalized_path()),
            "sessions_root": profile.sessions_root,
            "extra_paths": [str(value) for value in profile.normalized_extra_paths()],
            "mine_interval_seconds": profile.mine_interval_seconds,
            "auto_mine": profile.auto_mine,
            "enabled": profile.enabled,
            "pending_mine": states.get(profile.normalized_name()).pending_mine if states.get(profile.normalized_name()) else False,
            "last_run_at": states.get(profile.normalized_name()).last_run_at if states.get(profile.normalized_name()) else None,
            "last_mined_at": states.get(profile.normalized_name()).last_mined_at if states.get(profile.normalized_name()) else None,
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
        print(
            f"{item['project']}: path={item['path']} sessions_root={item['sessions_root']} "
            f"enabled={item['enabled']} pending_mine={item['pending_mine']}"
        )
        if item["last_run_at"] is not None:
            print(f"  last_run_at={item['last_run_at']}")
        if item["last_mined_at"] is not None:
            print(f"  last_mined_at={item['last_mined_at']}")
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
            if item.mine_started_at is not None:
                print(f"  Mine started at: {item.mine_started_at}")
            if item.mine_finished_at is not None:
                print(f"  Mine finished at: {item.mine_finished_at}")
            if item.mine_elapsed_seconds is not None:
                print(f"  Mine elapsed seconds: {item.mine_elapsed_seconds}")
        else:
            print(f"  Mine: skipped ({item.mine_skipped_reason})")
    return 0


def cmd_automation_run(args: argparse.Namespace) -> int:
    config = load_workspace(args.workspace)
    results = run_automation_cycle(
        config=config,
        project_filter=args.project,
        retry_attempts=args.retry_attempts,
        retry_delay_seconds=args.retry_delay_seconds,
        graphify_bin=args.graphify_bin,
        build_graph=not args.no_build,
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
        if item.intake is not None:
            print(
                "  Intake:"
                f" copied={item.intake.sync.copied}"
                f" updated={item.intake.sync.updated}"
                f" unchanged={item.intake.sync.unchanged}"
                f" mined={'yes' if item.intake.mined else 'no'}"
            )
        print(
            "  Documents:"
            f" copied={item.documents.copied}"
            f" updated={item.documents.updated}"
            f" unchanged={item.documents.unchanged}"
        )
        print(f"  Palace drawers: {item.palace_drawers}")
        print(f"  Packages: {item.packages}")
        changed = sum(1 for result in item.promoted if result.changed)
        unchanged = len(item.promoted) - changed
        print(f"  Promoted: {changed} changed, {unchanged} unchanged")
        print(f"  Graphify: {item.graphify.status}")
        for artifact in item.artifacts:
            print(f"  Artifact: {artifact}")
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
                    "started_at": result.started_at,
                    "finished_at": result.finished_at,
                    "elapsed_seconds": result.elapsed_seconds,
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
    print(f"Started at: {result.started_at}")
    print(f"Finished at: {result.finished_at}")
    print(f"Elapsed seconds: {result.elapsed_seconds}")
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
    if args.group_by == "session":
        packages = [
            build_session_package_from_drawers(
                project=project,
                wing=wing,
                room=room,
                session_key=session_key,
                session_title=session_title,
                drawers=group_drawers,
                hall_id=args.hall_id,
            )
            for (wing, room, session_key, session_title), group_drawers in sorted(group_drawers_by_logical_session(drawers).items())
        ]
    else:
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
        "group_by": args.group_by,
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
    if args.group_by == "session":
        packages = [
            build_session_package_from_drawers(
                project=project,
                wing=wing,
                room=room_name,
                session_key=session_key,
                session_title=session_title,
                drawers=group_drawers,
                hall_id=args.hall_id,
            )
            for (wing, room_name, session_key, session_title), group_drawers in sorted(group_drawers_by_logical_session(drawers).items())
        ]
    else:
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
            "group_by": args.group_by,
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
        "group_by": args.group_by,
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
    except (FileNotFoundError, ValidationError, ValueError, GraphifyError, MemPalaceError, PalaceReadError, InstallError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
