"""Core data models for MemArk room promotion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ValidationError(ValueError):
    """Raised when a room package does not satisfy the MemArk contract."""


def _as_string_list(values: Any, field_name: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValidationError(f"{field_name} must be a list")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} entries must be strings")
        result.append(value)
    return result


def _as_mapping_list(values: Any, field_name: str) -> list[dict[str, Any]]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValidationError(f"{field_name} must be a list")
    result: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, dict):
            raise ValidationError(f"{field_name} entries must be objects")
        result.append(value)
    return result


@dataclass(slots=True)
class Closet:
    closet_id: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any], index: int) -> "Closet":
        closet_id = payload.get("closet_id") or f"closet-{index}"
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValidationError("closets[].summary must be a non-empty string")
        return cls(
            closet_id=str(closet_id),
            summary=summary.strip(),
            key_points=_as_string_list(payload.get("key_points"), "closets[].key_points"),
            tags=_as_string_list(payload.get("tags"), "closets[].tags"),
            evidence_refs=_as_string_list(payload.get("evidence_refs"), "closets[].evidence_refs"),
        )


@dataclass(slots=True)
class DrawerRef:
    drawer_id: str
    timestamp: str | None = None
    speaker: str | None = None
    excerpt: str | None = None
    source_uri: str | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any], index: int) -> "DrawerRef":
        drawer_id = payload.get("drawer_id") or f"drawer-{index}"
        return cls(
            drawer_id=str(drawer_id),
            timestamp=_optional_str(payload.get("timestamp")),
            speaker=_optional_str(payload.get("speaker")),
            excerpt=_optional_str(payload.get("excerpt")),
            source_uri=_optional_str(payload.get("source_uri")),
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError("optional string field must be a string when present")
    return value


def _normalize_string_sequence(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, list):
        result: list[str] = []
        for value in values:
            if isinstance(value, str):
                result.append(value)
            elif isinstance(value, dict):
                pieces = [str(v).strip() for v in value.values() if isinstance(v, str) and v.strip()]
                if pieces:
                    result.append(" | ".join(pieces))
            else:
                result.append(str(value))
        return result
    raise ValidationError("participants/related_entities must be a list when present")


def _derive_project_slug(wing_id: str) -> str:
    if "/" in wing_id:
        return wing_id.rsplit("/", 1)[-1].strip()
    return wing_id.strip()


@dataclass(slots=True)
class RoomPackage:
    wing_id: str
    wing_kind: str
    hall_id: str
    room_id: str
    room_title: str
    room_summary: str | None
    closets: list[Closet]
    drawer_refs: list[DrawerRef] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    source_time_start: str | None = None
    source_time_end: str | None = None
    updated_at: str | None = None
    project: str | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "RoomPackage":
        if not isinstance(payload, dict):
            raise ValidationError("room package must be an object")

        required_fields = ["wing_id", "wing_kind", "hall_id", "room_id", "room_title", "closets"]
        missing = [name for name in required_fields if name not in payload]
        if missing:
            raise ValidationError(f"room package missing required fields: {', '.join(missing)}")

        wing_id = payload["wing_id"]
        wing_kind = payload["wing_kind"]
        hall_id = payload["hall_id"]
        room_id = payload["room_id"]
        room_title = payload["room_title"]
        room_summary = payload.get("room_summary")

        for field_name, value in {
            "wing_id": wing_id,
            "wing_kind": wing_kind,
            "hall_id": hall_id,
            "room_id": room_id,
            "room_title": room_title,
        }.items():
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{field_name} must be a non-empty string")

        if room_summary is not None and not isinstance(room_summary, str):
            raise ValidationError("room_summary must be a string when present")

        closets_raw = _as_mapping_list(payload["closets"], "closets")
        if not closets_raw:
            raise ValidationError("closets must contain at least one object")
        closets = [Closet.from_mapping(item, index) for index, item in enumerate(closets_raw, start=1)]

        timestamps = payload.get("source_timestamps")
        source_time_start: str | None = None
        source_time_end: str | None = None
        if timestamps is not None:
            if not isinstance(timestamps, dict):
                raise ValidationError("source_timestamps must be an object when present")
            source_time_start = _optional_str(timestamps.get("start"))
            source_time_end = _optional_str(timestamps.get("end"))

        project = payload.get("project")
        if project is not None and not isinstance(project, str):
            raise ValidationError("project must be a string when present")

        return cls(
            wing_id=wing_id.strip(),
            wing_kind=wing_kind.strip(),
            hall_id=hall_id.strip(),
            room_id=room_id.strip(),
            room_title=room_title.strip(),
            room_summary=room_summary.strip() if isinstance(room_summary, str) and room_summary.strip() else None,
            closets=closets,
            drawer_refs=[
                DrawerRef.from_mapping(item, index)
                for index, item in enumerate(_as_mapping_list(payload.get("drawer_refs"), "drawer_refs"), start=1)
            ],
            participants=_normalize_string_sequence(payload.get("participants")),
            related_entities=_normalize_string_sequence(payload.get("related_entities")),
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            updated_at=_optional_str(payload.get("updated_at")),
            project=project.strip() if isinstance(project, str) and project.strip() else _derive_project_slug(wing_id),
        )

    def ensure_promotable(self, allow_non_project: bool = False) -> None:
        if not allow_non_project and self.wing_kind != "project":
            raise ValidationError(
                f"wing_kind must be 'project' for promotion by default, got {self.wing_kind!r}"
            )

