"""Build deterministic room package candidates from palace drawers."""

from __future__ import annotations

import json
import re
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


def _session_title_from_text(text: str, limit: int = 72) -> str | None:
    compact = " ".join(text.split())
    if not compact:
        return None
    if compact.startswith("> "):
        compact = compact[2:].strip()
    if compact.startswith(">"):
        compact = compact[1:].strip()
    if not compact:
        return None
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


_SNAPSHOT_NAME_RE = re.compile(r"^(?P<stem>.+)--(?P<mtime>\d+)-(?P<sha>[0-9a-f]{12})(?P<suffix>\.[^.]+)?$")


def _logical_source_uri(source_uri: str | None) -> str | None:
    if not source_uri:
        return None
    path = Path(source_uri)
    match = _SNAPSHOT_NAME_RE.match(path.name)
    if match is None:
        return source_uri
    suffix = match.group("suffix") or ""
    return str(path.with_name(f"{match.group('stem')}{suffix}"))


def _logical_source_key(source_uri: str | None) -> str | None:
    logical = _logical_source_uri(source_uri)
    if logical is None:
        return None
    path = Path(logical)
    if path.suffix:
        return path.stem
    return path.name or logical


def _logical_source_title(source_uri: str | None) -> str | None:
    key = _logical_source_key(source_uri)
    if not key:
        return None
    value = key
    if value.startswith("rollout-"):
        value = value[len("rollout-") :]
    return _titleize(value)


_GENERIC_SESSION_LINES = {
    "continue",
    "hi",
    "ok",
    "继续",
    "推进",
    "提交",
    "由您决定",
    "卡住了吗？继续",
    "卡住了吗?继续",
    "。继续",
}


def _snapshot_session_title(source_uri: str | None) -> str | None:
    logical_source = _logical_source_uri(source_uri)
    if not logical_source:
        return None
    candidates: list[Path] = []
    path = Path(logical_source)
    candidates.append(path)
    if path.suffix:
        candidates.extend(sorted(path.parent.glob(f"{path.stem}--*{path.suffix}")))
    for candidate in candidates:
        try:
            lines = candidate.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        title = _snapshot_title_from_lines(lines)
        if title:
            return title
    return None


def _snapshot_title_from_lines(lines: list[str]) -> str | None:
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith(("Source Path:", "Workspace Path:", "Session ID:", "Session Timestamp:")):
            continue
        if line.startswith(">"):
            line = line[1:].strip()
        if not line or len(line) < 6:
            continue
        if line.lower() in _GENERIC_SESSION_LINES:
            continue
        return _session_title_from_text(line)
    return None


def _latest_drawers_by_logical_source(drawers: list[PalaceDrawer]) -> list[PalaceDrawer]:
    latest: dict[str, PalaceDrawer] = {}
    passthrough: list[PalaceDrawer] = []
    for drawer in drawers:
        logical_source = _logical_source_uri(drawer.source_file)
        if logical_source is None:
            passthrough.append(drawer)
            continue
        current = latest.get(logical_source)
        if current is None or _sort_timestamp(drawer.filed_at) >= _sort_timestamp(current.filed_at):
            latest[logical_source] = drawer
    return [*passthrough, *latest.values()]


def _drawer_ref(drawer: PalaceDrawer) -> DrawerRef:
    return DrawerRef(
        drawer_id=drawer.drawer_id,
        timestamp=drawer.filed_at,
        excerpt=_excerpt(drawer.document),
        source_uri=_logical_source_uri(drawer.source_file),
    )


def _memory_tool_tag(drawers: list[PalaceDrawer], default_mem_tool: str | None = None) -> str:
    for drawer in drawers:
        if drawer.added_by and drawer.added_by.strip():
            return slugify(drawer.added_by).replace("-", "_")
    if default_mem_tool and default_mem_tool.strip():
        return slugify(default_mem_tool).replace("-", "_")
    return "mempalace"


def build_room_package_from_drawers(
    *,
    project: str,
    wing: str,
    room: str,
    drawers: list[PalaceDrawer],
    hall_id: str = "discoveries",
    default_mem_tool: str | None = None,
) -> RoomPackage:
    ordered = sorted(_latest_drawers_by_logical_source(drawers), key=lambda item: _sort_timestamp(item.filed_at))
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
                _memory_tool_tag(ordered, default_mem_tool),
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
                if _logical_source_uri(item.source_file) and Path(_logical_source_uri(item.source_file) or "").name
            }
        ),
        source_time_start=min(timestamps) if timestamps else None,
        source_time_end=max(timestamps) if timestamps else None,
        updated_at=max(timestamps) if timestamps else None,
        project=slugify(project),
    )
    return package


def build_session_package_from_drawers(
    *,
    project: str,
    wing: str,
    room: str,
    session_key: str,
    session_title: str | None,
    drawers: list[PalaceDrawer],
    hall_id: str = "discoveries",
    default_mem_tool: str | None = None,
) -> RoomPackage:
    room_id = slugify(f"{room}-{session_key}")
    ordered = sorted(_latest_drawers_by_logical_source(drawers), key=lambda item: _sort_timestamp(item.filed_at))
    inferred_title = None
    for item in ordered:
        candidate = _session_title_from_text(item.document)
        if candidate:
            inferred_title = candidate
            break
    room_title = session_title or inferred_title or _titleize(session_key)
    excerpts = [_excerpt(item.document) for item in ordered[:5]]
    summary = (
        f"Collected {len(ordered)} memory drawer(s) from logical session '{session_key}' "
        f"in room '{room}' and wing '{wing}'."
    )
    closet = Closet(
        closet_id="closet-1",
        summary=summary,
        key_points=excerpts,
        tags=sorted(
            {
                slugify(room).replace("-", "_"),
                slugify(wing).replace("-", "_"),
                slugify(session_key).replace("-", "_"),
                _memory_tool_tag(ordered, default_mem_tool),
                "codex_session",
            }
        ),
        evidence_refs=[item.drawer_id for item in ordered[:10]],
    )
    timestamps = [item.filed_at for item in ordered if item.filed_at]
    related_entities = sorted(
        {
            f"File: {Path(source_uri).name}"
            for item in ordered
            for source_uri in [_logical_source_uri(item.source_file)]
            if source_uri
        }
    )
    return RoomPackage(
        wing_id=f"project/{slugify(project)}",
        wing_kind="project",
        hall_id=slugify(hall_id),
        room_id=room_id,
        room_title=room_title,
        room_summary=summary,
        closets=[closet],
        drawer_refs=[_drawer_ref(item) for item in ordered[:20]],
        participants=[],
        related_entities=related_entities,
        source_time_start=min(timestamps) if timestamps else None,
        source_time_end=max(timestamps) if timestamps else None,
        updated_at=max(timestamps) if timestamps else None,
        project=slugify(project),
    )


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


def group_drawers_by_room(drawers: list[PalaceDrawer]) -> dict[tuple[str, str], list[PalaceDrawer]]:
    grouped: dict[tuple[str, str], list[PalaceDrawer]] = {}
    for drawer in drawers:
        wing = drawer.wing or "unknown"
        room = drawer.room or "general"
        grouped.setdefault((wing, room), []).append(drawer)
    return grouped


def group_drawers_by_logical_session(
    drawers: list[PalaceDrawer],
) -> dict[tuple[str, str, str, str], list[PalaceDrawer]]:
    grouped: dict[tuple[str, str, str, str], list[PalaceDrawer]] = {}
    for drawer in drawers:
        wing = drawer.wing or "unknown"
        room = drawer.room or "general"
        session_key = _logical_source_key(drawer.source_file) or f"drawer-{drawer.drawer_id}"
        session_title = (
            _snapshot_session_title(drawer.source_file)
            or _logical_source_title(drawer.source_file)
            or _titleize(session_key)
        )
        grouped.setdefault((wing, room, session_key, session_title), []).append(drawer)
    return grouped


def write_package_payloads(package_payloads: list[dict[str, object]], destination_dir: Path) -> list[Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for package in package_payloads:
        room_id = str(package["room_id"])
        destination = destination_dir / f"palace-{room_id}.json"
        destination.write_text(json.dumps(package, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        written.append(destination)
    return written
