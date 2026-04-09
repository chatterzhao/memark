"""Build deterministic room package candidates from palace drawers."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import Closet, DrawerRef, RoomPackage
from .palace import PalaceDrawer
from .workspace import slugify


def _titleize(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("_", " ").replace("-", " ").split())


def _excerpt(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _sort_timestamp(value: str | None) -> tuple[int, str]:
    if not value:
        return (1, "")
    try:
        normalized = value.replace("Z", "+00:00")
        return (0, datetime.fromisoformat(normalized).isoformat())
    except ValueError:
        return (0, value)


def _drawer_ref(drawer: PalaceDrawer) -> DrawerRef:
    return DrawerRef(
        drawer_id=drawer.drawer_id,
        timestamp=drawer.filed_at,
        excerpt=_excerpt(drawer.document),
        source_uri=drawer.source_file,
    )


def build_room_package_from_drawers(
    *,
    project: str,
    wing: str,
    room: str,
    drawers: list[PalaceDrawer],
    hall_id: str = "discoveries",
) -> RoomPackage:
    ordered = sorted(drawers, key=lambda item: _sort_timestamp(item.filed_at))
    excerpts = [_excerpt(item.document) for item in ordered[:5]]
    summary = f"Collected {len(ordered)} memory drawer(s) from room '{room}' in wing '{wing}'."
    closet = Closet(
        closet_id="closet-1",
        summary=summary,
        key_points=excerpts,
        tags=sorted(
            {
                slugify(room).replace("-", "_"),
                slugify(wing).replace("-", "_"),
                "mempalace",
                "codex_session",
            }
        ),
        evidence_refs=[item.drawer_id for item in ordered[:10]],
    )

    timestamps = [item.filed_at for item in ordered if item.filed_at]
    package = RoomPackage(
        wing_id=f"project/{slugify(project)}",
        wing_kind="project",
        hall_id=slugify(hall_id),
        room_id=slugify(room),
        room_title=_titleize(room),
        room_summary=summary,
        closets=[closet],
        drawer_refs=[_drawer_ref(item) for item in ordered[:20]],
        participants=[],
        related_entities=sorted(
            {
                f"File: {Path(item.source_file).name}"
                for item in ordered
                if item.source_file and Path(item.source_file).name
            }
        ),
        source_time_start=min(timestamps) if timestamps else None,
        source_time_end=max(timestamps) if timestamps else None,
        updated_at=max(timestamps) if timestamps else None,
        project=slugify(project),
    )
    return package


def package_to_dict(package: RoomPackage) -> dict[str, object]:
    return {
        "wing_id": package.wing_id,
        "wing_kind": package.wing_kind,
        "hall_id": package.hall_id,
        "room_id": package.room_id,
        "room_title": package.room_title,
        "room_summary": package.room_summary,
        "closets": [asdict(closet) for closet in package.closets],
        "drawer_refs": [asdict(ref) for ref in package.drawer_refs],
        "participants": package.participants,
        "related_entities": package.related_entities,
        "source_timestamps": {
            "start": package.source_time_start,
            "end": package.source_time_end,
        },
        "updated_at": package.updated_at,
        "project": package.project,
    }
