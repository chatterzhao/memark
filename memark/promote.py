"""Promotion pipeline from room packages to Graphify-ready corpus files."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import dump_json_file, load_json_file, sha256_text
from .models import RoomPackage
from .render import render_markdown
from .workspace import WorkspaceConfig, slugify


@dataclass(slots=True)
class PromoteResult:
    source: Path
    output: Path
    room_id: str
    project: str
    changed: bool
    archived_to: Path | None = None


def load_room_packages(path: Path) -> list[RoomPackage]:
    payload = load_json_file(path)
    items = payload if isinstance(payload, list) else [payload]
    return [RoomPackage.from_mapping(item) for item in items]


def _load_ledger(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def _save_ledger(path: Path, ledger: dict[str, str]) -> None:
    dump_json_file(path, ledger)


def _package_fingerprint(package: RoomPackage, project: str) -> str:
    serializable: dict[str, Any] = {
        "project": project,
        "wing_id": package.wing_id,
        "wing_kind": package.wing_kind,
        "hall_id": package.hall_id,
        "room_id": package.room_id,
        "room_title": package.room_title,
        "room_summary": package.room_summary,
        "closets": [
            {
                "closet_id": closet.closet_id,
                "summary": closet.summary,
                "key_points": closet.key_points,
                "tags": closet.tags,
                "evidence_refs": closet.evidence_refs,
            }
            for closet in package.closets
        ],
        "drawer_refs": [
            {
                "drawer_id": ref.drawer_id,
                "timestamp": ref.timestamp,
                "speaker": ref.speaker,
                "excerpt": ref.excerpt,
                "source_uri": ref.source_uri,
            }
            for ref in package.drawer_refs
        ],
        "participants": package.participants,
        "related_entities": package.related_entities,
        "source_time_start": package.source_time_start,
        "source_time_end": package.source_time_end,
        "updated_at": package.updated_at,
    }
    return sha256_text(json.dumps(serializable, sort_keys=True, ensure_ascii=True))


def promote_file(
    config: WorkspaceConfig,
    source: Path,
    project_override: str | None = None,
    allow_non_project: bool = False,
    archive: bool = False,
) -> list[PromoteResult]:
    packages = load_room_packages(source)
    results: list[PromoteResult] = []
    archived_to: Path | None = None

    for package in packages:
        package.ensure_promotable(allow_non_project=allow_non_project)
        project = slugify(project_override or package.project or config.default_project)
        config.ensure_layout(project)
        ledger_path = config.ledger_file(project)
        ledger = _load_ledger(ledger_path)
        fingerprint = _package_fingerprint(package, project)
        ledger_key = package.room_id
        output = config.promoted_dir(project) / f"room-{slugify(package.room_id)}.md"
        changed = ledger.get(ledger_key) != fingerprint or not output.exists()
        if changed:
            output.write_text(render_markdown(package, project), encoding="utf-8")
            ledger[ledger_key] = fingerprint
            _save_ledger(ledger_path, ledger)
        results.append(
            PromoteResult(
                source=source,
                output=output,
                room_id=package.room_id,
                project=project,
                changed=changed,
                archived_to=archived_to,
            )
        )

    if archive:
        archived_to = config.archive_dir / source.name
        archived_to.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != archived_to.resolve():
            shutil.move(str(source), archived_to)
        for result in results:
            result.archived_to = archived_to

    return results


def iter_input_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return [item for item in sorted(path.rglob("*.json")) if item.is_file()]


def promote_path(
    config: WorkspaceConfig,
    path: Path,
    project_override: str | None = None,
    allow_non_project: bool = False,
    archive: bool = False,
) -> list[PromoteResult]:
    results: list[PromoteResult] = []
    for file_path in iter_input_files(path):
        results.extend(
            promote_file(
                config=config,
                source=file_path,
                project_override=project_override,
                allow_non_project=allow_non_project,
                archive=archive,
            )
        )
    return results
