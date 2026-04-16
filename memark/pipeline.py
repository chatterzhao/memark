"""MemArk feed/process/consume pipeline helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .package_builder import (
    build_session_package_from_drawers,
    group_drawers_by_logical_session,
    package_to_dict,
    write_package_payloads,
)
from .palace import PalaceReadError, read_palace_drawers
from .project_registry import ProjectCycleResult, run_projects_cycle
from .promote import PromoteResult, promote_file
from .workspace import WorkspaceConfig


_DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}
_DOC_IGNORE_PARTS = {
    ".experiments",
    ".git",
    ".memark",
    ".memark-bootstrap",
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
class FeedPhaseResult:
    intake: ProjectCycleResult | None

    def to_dict(self) -> dict[str, object] | None:
        return None if self.intake is None else self.intake.to_dict()


@dataclass(slots=True)
class ProcessPhaseResult:
    project: dict[str, object]
    palace_drawers: int
    packages: int
    promoted: list[PromoteResult]

    def to_dict(self) -> dict[str, object]:
        return {
            "project": dict(self.project),
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

def _automation_packages_dir(config: WorkspaceConfig, project: str) -> Path:
    return config.staging_dir / project / "packages"


def iter_project_documents(root: Path) -> list[Path]:
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


def scan_project_documents(source_root: Path) -> dict[str, object]:
    files = iter_project_documents(source_root)
    return {
        "root": str(source_root.resolve()),
        "documents": len(files),
        "files": [str(path.resolve()) for path in files],
    }


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
