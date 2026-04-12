"""MemArk feed/process/consume pipeline helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .io import copy_document, dump_json_file, load_json_file, sha256_text
from .package_builder import (
    build_session_package_from_drawers,
    group_drawers_by_logical_session,
    package_to_dict,
    write_package_payloads,
)
from .palace import PalaceReadError, read_palace_drawers
from .project_registry import ProjectCycleResult, run_projects_cycle
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
class FeedPhaseResult:
    intake: ProjectCycleResult | None

    def to_dict(self) -> dict[str, object] | None:
        return None if self.intake is None else self.intake.to_dict()


@dataclass(slots=True)
class ProcessPhaseResult:
    documents: DocumentSyncResult
    palace_drawers: int
    packages: int
    promoted: list[PromoteResult]

    def to_dict(self) -> dict[str, object]:
        return {
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
        }


def _documents_ledger_path(config: WorkspaceConfig, project: str) -> Path:
    return config.state_dir / f"{slugify(project)}-documents.json"


def _automation_packages_dir(config: WorkspaceConfig, project: str) -> Path:
    return config.staging_dir / slugify(project) / "packages"


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


def build_palace_packages(config: WorkspaceConfig, *, project: str) -> tuple[int, int, list[PromoteResult]]:
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


def run_feed_phase(
    config: WorkspaceConfig,
    *,
    project_filter: str | None = None,
    dry_run: bool = False,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
    progress=None,
) -> list[ProjectCycleResult]:
    return run_projects_cycle(
        config=config,
        project_filter=project_filter,
        dry_run=dry_run,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
        progress=progress,
    )
