"""Automated intake, processing, and consumption cycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .graphify import GraphifyError, GraphifyBuildResult, run_graphify
from .handoff import GraphifyHandoff, build_graphify_handoff
from .io import copy_document, dump_json_file, load_json_file, sha256_text
from .package_builder import (
    build_session_package_from_drawers,
    group_drawers_by_logical_session,
    package_to_dict,
    write_package_payloads,
)
from .palace import PalaceReadError, read_palace_drawers
from .project_registry import (
    ProjectCycleResult,
    load_project_profiles,
    run_projects_cycle,
)
from .promote import PromoteResult, promote_file
from .workspace import WorkspaceConfig, slugify


_DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}
_DOC_IGNORE_PARTS = {
    ".experiments",
    ".git",
    ".memark",
    ".mempalace",
    ".pytest_cache",
    "corpus",
    "build",
    "dist",
    "graphify-out",
    "inbox",
    "node_modules",
    "raw",
    ".venv",
    ".venv-dev",
    ".venv-skill-check",
    "__pycache__",
}
_DECISION_MARKERS = ("decision", "decide", "adr", "chosen", "adopt")
_RISK_MARKERS = ("risk", "blocker", "issue", "failed", "failure", "todo", "follow-up", "followup")


@dataclass(slots=True)
class DocumentSyncResult:
    copied: int
    updated: int
    unchanged: int
    files: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "copied": self.copied,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "files": list(self.files),
        }


@dataclass(slots=True)
class GraphifyAutomationResult:
    status: str
    attempted: bool
    mode: str | None
    command: list[str] | None
    error: str | None
    recommended_command: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "attempted": self.attempted,
            "mode": self.mode,
            "command": list(self.command) if self.command is not None else None,
            "error": self.error,
            "recommended_command": self.recommended_command,
        }


@dataclass(slots=True)
class AutomationProjectResult:
    project: str
    intake: ProjectCycleResult | None
    documents: DocumentSyncResult
    palace_drawers: int
    packages: int
    promoted: list[PromoteResult]
    artifacts: list[str]
    graphify: GraphifyAutomationResult

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "intake": self.intake.to_dict() if self.intake is not None else None,
            "documents": self.documents.to_dict(),
            "palace_drawers": self.palace_drawers,
            "packages": self.packages,
            "promoted": [
                {
                    "room_id": item.room_id,
                    "output": str(item.output),
                    "changed": item.changed,
                }
                for item in self.promoted
            ],
            "artifacts": list(self.artifacts),
            "graphify": self.graphify.to_dict(),
        }


def _documents_ledger_path(config: WorkspaceConfig, project: str) -> Path:
    return config.state_dir / f"{slugify(project)}-documents.json"


def _automation_packages_dir(config: WorkspaceConfig, project: str) -> Path:
    return config.staging_dir / slugify(project) / "packages"


def _automation_imports_dir(config: WorkspaceConfig, project: str) -> Path:
    return config.imports_dir(project) / "automation"


def _load_documents_ledger(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def _save_documents_ledger(path: Path, payload: dict[str, str]) -> None:
    dump_json_file(path, payload)


def _iter_project_documents(root: Path) -> list[Path]:
    if not root.exists():
        return []
    results: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _DOC_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part in _DOC_IGNORE_PARTS or part.endswith(".egg-info") for part in relative.parts):
            continue
        results.append(path)
    return results


def sync_project_documents(config: WorkspaceConfig, *, project: str, source_root: Path) -> DocumentSyncResult:
    project_slug = slugify(project)
    destination_root = config.documents_dir(project_slug)
    ledger_path = _documents_ledger_path(config, project_slug)
    ledger = _load_documents_ledger(ledger_path)
    next_ledger = dict(ledger)
    copied = 0
    updated = 0
    unchanged = 0
    files: list[str] = []

    sources = _iter_project_documents(source_root)
    for source in sources:
        relative = source.relative_to(source_root)
        destination = destination_root / relative
        fingerprint = sha256_text(source.read_text(encoding="utf-8", errors="ignore"))
        key = str(relative)
        existing = ledger.get(key)
        if existing == fingerprint and destination.exists():
            unchanged += 1
            next_ledger[key] = fingerprint
            files.append(str(destination))
            continue
        existed_before = destination.exists()
        copy_document(source, destination)
        if existing is None or not existed_before:
            copied += 1
        else:
            updated += 1
        next_ledger[key] = fingerprint
        files.append(str(destination))

    stale_keys = sorted(set(next_ledger) - {str(path.relative_to(source_root)) for path in sources})
    for key in stale_keys:
        next_ledger.pop(key, None)
        destination = destination_root / key
        if destination.exists():
            destination.unlink()
            parent = destination.parent
            while parent != destination_root and parent.exists():
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent

    _save_documents_ledger(ledger_path, next_ledger)
    return DocumentSyncResult(copied=copied, updated=updated, unchanged=unchanged, files=files)


def _build_palace_packages(config: WorkspaceConfig, *, project: str) -> tuple[int, int, list[PromoteResult]]:
    palace_dir = config.palace_dir(project)
    try:
        drawers = read_palace_drawers(palace_dir, ingest_mode="convos")
    except PalaceReadError:
        return 0, 0, []
    grouped = group_drawers_by_logical_session(drawers)
    packages = [
        build_session_package_from_drawers(
            project=project,
            wing=wing,
            room=room,
            session_key=session_key,
            session_title=session_title,
            drawers=group_drawers,
            hall_id="discoveries",
        )
        for (wing, room, session_key, session_title), group_drawers in sorted(grouped.items())
    ]
    package_payloads = [package_to_dict(item) for item in packages]
    package_dir = _automation_packages_dir(config, project)
    written_paths = write_package_payloads(package_payloads, package_dir)
    promote_results: list[PromoteResult] = []
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
    return len(drawers), len(package_payloads), promote_results


def _extract_titles(paths: list[Path], *, limit: int) -> list[str]:
    results: list[str] = []
    for path in paths[:limit]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("#"):
                results.append(line.lstrip("#").strip())
                break
        else:
            results.append(path.stem)
    return results


def _extract_matching_lines(paths: list[Path], markers: tuple[str, ...], *, limit: int) -> list[str]:
    matches: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for raw in text.splitlines():
            line = " ".join(raw.split())
            if not line:
                continue
            lowered = line.casefold()
            if any(marker in lowered for marker in markers):
                matches.append(f"{path.name}: {line[:220]}")
                if len(matches) >= limit:
                    return matches
    return matches


def _write_artifact(path: Path, lines: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return str(path)


def _render_graphify_status(handoff: GraphifyHandoff, graphify: GraphifyAutomationResult) -> list[str]:
    lines = [
        "# Graphify Status",
        "",
        f"- status: {graphify.status}",
        f"- attempted: {str(graphify.attempted).lower()}",
        f"- recommended_command: `{handoff.recommended_command}`",
    ]
    if graphify.mode:
        lines.append(f"- mode: {graphify.mode}")
    if graphify.command:
        lines.append(f"- command: `{' '.join(graphify.command)}`")
    if graphify.error:
        lines.extend(["", "## Error", "", graphify.error])
    lines.extend(["", "## Corpus Summary", ""])
    for item in handoff.inventories:
        lines.append(f"- {item.scope}: {item.files} files, ~{item.words} words")
    lines.append(f"- code files: {handoff.code_files}")
    return lines


def generate_consumption_artifacts(
    config: WorkspaceConfig,
    *,
    project: str,
    handoff: GraphifyHandoff,
    graphify: GraphifyAutomationResult,
) -> list[str]:
    project_slug = slugify(project)
    imports_dir = _automation_imports_dir(config, project_slug)
    promoted = sorted(
        config.promoted_dir(project_slug).glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    documents = sorted(
        (path for path in config.documents_dir(project_slug).rglob("*") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    recent_titles = _extract_titles(promoted, limit=5)
    decision_lines = _extract_matching_lines([*promoted, *documents], _DECISION_MARKERS, limit=10)
    risk_lines = _extract_matching_lines([*promoted, *documents], _RISK_MARKERS, limit=10)

    written: list[str] = []
    recent_lines = [f"- {title}" for title in recent_titles] or ["- No promoted knowledge yet."]
    decision_digest = [f"- {line}" for line in decision_lines] or ["- No decision-like lines detected yet."]
    risk_digest = [f"- {line}" for line in risk_lines] or ["- No risk-like lines detected yet."]

    written.append(
        _write_artifact(
            imports_dir / "latest-summary.md",
            [
                "# Latest Summary",
                "",
                f"- project: {project_slug}",
                f"- promoted_files: {len(promoted)}",
                f"- document_files: {len(documents)}",
                f"- graphify_status: {graphify.status}",
                "",
                "## Recent Promoted Knowledge",
                "",
                *recent_lines,
            ],
        )
    )
    written.append(
        _write_artifact(
            imports_dir / "decisions-digest.md",
            [
                "# Decisions Digest",
                "",
                *decision_digest,
            ],
        )
    )
    written.append(
        _write_artifact(
            imports_dir / "risks-digest.md",
            [
                "# Risks Digest",
                "",
                *risk_digest,
            ],
        )
    )
    written.append(
        _write_artifact(
            imports_dir / "ai-context.md",
            [
                "# AI Context",
                "",
                f"- project: {project_slug}",
                f"- graphify_status: {graphify.status}",
                f"- recommended_graphify_command: `{handoff.recommended_command}`",
                "",
                "## Start Here",
                "",
                "- Read latest-summary.md for the newest promoted changes.",
                "- Read decisions-digest.md before making project-level changes.",
                "- Read risks-digest.md before changing architecture or rollout logic.",
                "",
                "## Recent Promoted Knowledge",
                "",
                *recent_lines,
            ],
        )
    )
    written.append(_write_artifact(imports_dir / "graphify-status.md", _render_graphify_status(handoff, graphify)))
    return written


def _graphify_automation_result(
    *,
    handoff: GraphifyHandoff,
    result: GraphifyBuildResult | None = None,
    error: str | None = None,
    attempted: bool,
) -> GraphifyAutomationResult:
    if result is not None:
        return GraphifyAutomationResult(
            status="updated",
            attempted=attempted,
            mode=result.mode,
            command=result.command,
            error=None,
            recommended_command=handoff.recommended_command,
        )
    status = "pending_update" if error else "not_requested"
    return GraphifyAutomationResult(
        status=status,
        attempted=attempted,
        mode=None,
        command=None,
        error=error,
        recommended_command=handoff.recommended_command,
    )


def run_automation_cycle(
    config: WorkspaceConfig,
    *,
    project_filter: str | None = None,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
    graphify_bin: str | None = None,
    build_graph: bool = True,
) -> list[AutomationProjectResult]:
    intake_results = run_projects_cycle(
        config=config,
        project_filter=project_filter,
        dry_run=False,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
        progress=None,
    )
    intake_by_project = {item.project: item for item in intake_results}
    profiles = load_project_profiles(config.projects_file)
    if project_filter is not None:
        target = slugify(project_filter)
        profiles = [profile for profile in profiles if profile.normalized_name() == target]
    profiles = [profile for profile in profiles if profile.enabled]

    results: list[AutomationProjectResult] = []
    for profile in profiles:
        project = profile.normalized_name()
        documents = sync_project_documents(
            config,
            project=project,
            source_root=profile.normalized_path(),
        )
        palace_drawers, packages, promoted = _build_palace_packages(config, project=project)
        handoff = build_graphify_handoff(project, config.corpus_project_dir(project))

        graphify_result: GraphifyBuildResult | None = None
        graphify_error: str | None = None
        attempted = False
        if build_graph:
            attempted = True
            try:
                graphify_result = run_graphify(
                    graphify_bin=graphify_bin or config.graphify_bin,
                    project_dir=config.corpus_project_dir(project),
                    update=True,
                )
            except GraphifyError as exc:
                graphify_error = str(exc)
        graphify = _graphify_automation_result(
            handoff=handoff,
            result=graphify_result,
            error=graphify_error,
            attempted=attempted,
        )
        artifacts = generate_consumption_artifacts(
            config,
            project=project,
            handoff=handoff,
            graphify=graphify,
        )
        results.append(
            AutomationProjectResult(
                project=project,
                intake=intake_by_project.get(project),
                documents=documents,
                palace_drawers=palace_drawers,
                packages=packages,
                promoted=promoted,
                artifacts=artifacts,
                graphify=graphify,
            )
        )
    return results
