from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict
from pathlib import Path

from .models import Closet, DrawerRef, RoomPackage
from .workspace import WorkspaceConfig, load_state, save_state


class PromotionError(RuntimeError):
    """Raised when a room package cannot be promoted."""


def load_room_package(input_path: Path) -> RoomPackage:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    closets = [
        Closet(
            closet_id=item["closet_id"],
            summary=item["summary"],
            key_points=_normalize_string_list(item.get("key_points")),
            tags=_normalize_string_list(item.get("tags")),
            evidence_refs=_normalize_string_list(item.get("evidence_refs")),
        )
        for item in raw.get("closets", [])
    ]
    drawer_refs = [
        DrawerRef(
            drawer_id=item["drawer_id"],
            timestamp=item.get("timestamp"),
            speaker=item.get("speaker"),
            excerpt=item.get("excerpt"),
            source_uri=item.get("source_uri"),
        )
        for item in raw.get("drawer_refs", [])
    ]
    package = RoomPackage(
        wing_id=raw["wing_id"],
        wing_kind=raw["wing_kind"],
        hall_id=raw["hall_id"],
        room_id=raw["room_id"],
        room_title=raw["room_title"],
        room_summary=raw.get("room_summary", ""),
        closets=closets,
        drawer_refs=drawer_refs,
        participants=_normalize_string_list(raw.get("participants")),
        related_entities=_normalize_string_list(raw.get("related_entities")),
        source_timestamps=_normalize_string_list(raw.get("source_timestamps")),
        updated_at=raw.get("updated_at"),
    )
    validate_room_package(package)
    return package


def validate_room_package(package: RoomPackage) -> None:
    required_values = {
        "wing_id": package.wing_id,
        "wing_kind": package.wing_kind,
        "hall_id": package.hall_id,
        "room_id": package.room_id,
        "room_title": package.room_title,
    }
    missing = [name for name, value in required_values.items() if not str(value).strip()]
    if missing:
        raise PromotionError(f"Missing required room package fields: {', '.join(missing)}")
    if package.wing_kind != "project":
        raise PromotionError(
            f"Room {package.room_id} is wing_kind={package.wing_kind!r}; only 'project' can be promoted"
        )
    if not package.closets and not package.room_summary:
        raise PromotionError(
            f"Room {package.room_id} has neither closets nor room_summary; nothing useful to promote"
        )


def promote_room(
    workspace: WorkspaceConfig,
    package: RoomPackage,
    *,
    source_path: Path,
    force: bool = False,
) -> Path:
    room_slug = slugify(package.room_id)
    output_path = workspace.promoted_dir / f"room-{room_slug}.md"
    state = load_state(workspace)
    promoted_rooms = state.setdefault("promoted_rooms", {})
    existing = promoted_rooms.get(package.room_id)
    if existing and not force:
        previous_updated_at = existing.get("updated_at")
        if previous_updated_at == package.updated_at:
            return output_path

    output_path.write_text(render_room_markdown(package), encoding="utf-8")
    imported_copy = workspace.imports_dir / source_path.name
    if imported_copy.resolve() != source_path.resolve():
        shutil.copy2(source_path, imported_copy)

    promoted_rooms[package.room_id] = {
        "output_path": str(output_path),
        "source_path": str(source_path.resolve()),
        "updated_at": package.updated_at,
        "hall_id": package.hall_id,
        "room_title": package.room_title,
        "wing_id": package.wing_id,
    }
    save_state(workspace, state)
    return output_path


def render_room_markdown(package: RoomPackage) -> str:
    frontmatter = {
        "source": "mempalace",
        "source_kind": "promoted_room",
        "project": package.project_slug,
        "wing_id": package.wing_id,
        "hall_id": package.hall_id,
        "room_id": package.room_id,
        "room_title": package.room_title,
        "participants": package.participants,
        "tags": _collect_tags(package),
        "updated_at": package.updated_at or "",
        "source_timestamps": package.source_timestamps,
        "drawer_refs": [item.drawer_id for item in package.drawer_refs],
    }

    lines = ["---"]
    lines.extend(_render_frontmatter(frontmatter))
    lines.append("---")
    lines.append("")
    lines.append(f"# {package.room_title}")
    lines.append("")
    lines.append("## Room Summary")
    lines.append("")
    lines.append(package.room_summary or "_No room summary provided._")
    lines.append("")

    if package.closets:
        lines.append("## Closets")
        lines.append("")
        for index, closet in enumerate(package.closets, start=1):
            lines.append(f"### Closet {index}: {closet.closet_id}")
            lines.append("")
            lines.append(closet.summary)
            lines.append("")
            if closet.key_points:
                for point in closet.key_points:
                    lines.append(f"- {point}")
                lines.append("")
            if closet.tags:
                lines.append(f"Tags: {', '.join(closet.tags)}")
                lines.append("")

    if package.related_entities:
        lines.append("## Entities")
        lines.append("")
        for entity in package.related_entities:
            lines.append(f"- {entity}")
        lines.append("")

    if package.drawer_refs:
        lines.append("## Evidence")
        lines.append("")
        for ref in package.drawer_refs:
            bits = [f"`{ref.drawer_id}`"]
            if ref.timestamp:
                bits.append(ref.timestamp)
            if ref.speaker:
                bits.append(ref.speaker)
            if ref.excerpt:
                bits.append(ref.excerpt.strip())
            if ref.source_uri:
                bits.append(ref.source_uri)
            lines.append(f"- {' | '.join(bits)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_frontmatter(data: dict) -> list[str]:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            if value:
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines[-1] += " []"
            continue
        lines.append(f"{key}: {value}")
    return lines


def _normalize_string_list(values: object) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise PromotionError("Expected a list of strings in room package input")
    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            normalized.append(text)
    return normalized


def _collect_tags(package: RoomPackage) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for closet in package.closets:
        for tag in closet.tags:
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "room"
