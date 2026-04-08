"""Rendering helpers for Graphify-ready Markdown output."""

from __future__ import annotations

from typing import Any

from .models import RoomPackage


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return '""'
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_list(values: list[Any], indent: int = 0) -> list[str]:
    prefix = " " * indent
    lines: list[str] = []
    for value in values:
        if isinstance(value, list):
            lines.append(f"{prefix}-")
            lines.extend(_yaml_list(value, indent + 2))
        else:
            lines.append(f"{prefix}- {_yaml_scalar(value)}")
    return lines


def _frontmatter(package: RoomPackage, project: str) -> str:
    tags: list[str] = []
    for closet in package.closets:
        tags.extend(closet.tags)
    unique_tags = sorted(dict.fromkeys(tag for tag in tags if tag.strip()))

    lines = [
        "---",
        'source: "mempalace"',
        'source_kind: "promoted_room"',
        f"project: {_yaml_scalar(project)}",
        f"wing_id: {_yaml_scalar(package.wing_id)}",
        f"hall_id: {_yaml_scalar(package.hall_id)}",
        f"room_id: {_yaml_scalar(package.room_id)}",
        f"room_title: {_yaml_scalar(package.room_title)}",
    ]
    if package.participants:
        lines.append("participants:")
        lines.extend(_yaml_list(package.participants, 2))
    if unique_tags:
        lines.append("tags:")
        lines.extend(_yaml_list(unique_tags, 2))
    if package.updated_at:
        lines.append(f"updated_at: {_yaml_scalar(package.updated_at)}")
    if package.source_time_start:
        lines.append(f"source_time_start: {_yaml_scalar(package.source_time_start)}")
    if package.source_time_end:
        lines.append(f"source_time_end: {_yaml_scalar(package.source_time_end)}")
    if package.drawer_refs:
        lines.append("drawer_refs:")
        lines.extend(_yaml_list([item.drawer_id for item in package.drawer_refs], 2))
    lines.append("---")
    return "\n".join(lines)


def render_markdown(package: RoomPackage, project: str) -> str:
    sections = [_frontmatter(package, project), "", f"# {package.room_title}", ""]

    if package.room_summary:
        sections.extend(["## Room Summary", "", package.room_summary, ""])

    sections.extend(["## Closets", ""])
    for index, closet in enumerate(package.closets, start=1):
        heading = closet.closet_id or f"Closet {index}"
        sections.extend([f"### {heading}", "", closet.summary, ""])
        if closet.key_points:
            sections.extend([f"- {point}" for point in closet.key_points])
            sections.append("")

    if package.related_entities:
        sections.extend(["## Entities", ""])
        sections.extend([f"- {entity}" for entity in package.related_entities])
        sections.append("")

    if package.drawer_refs:
        sections.extend(["## Evidence", ""])
        for ref in package.drawer_refs:
            line = f"- `{ref.drawer_id}`"
            pieces = [piece for piece in [ref.timestamp, ref.speaker, ref.excerpt, ref.source_uri] if piece]
            if pieces:
                line += ": " + " | ".join(pieces)
            sections.append(line)
        sections.append("")

    return "\n".join(sections).rstrip() + "\n"
