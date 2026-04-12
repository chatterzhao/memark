"""Persistent AI auto-consumption proof helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .io import dump_json_file, load_json_file
from .workspace import WorkspaceConfig, slugify


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _consumption_proof_path(config: WorkspaceConfig, project: str) -> Path:
    return config.state_dir / f"{slugify(project)}-consumption-proof.json"


@dataclass(slots=True)
class ConsumptionProof:
    project: str
    status: str
    recorded_at: str
    command: str | None
    evidence_paths: list[str]
    notes: str | None
    outcomes: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "status": self.status,
            "recorded_at": self.recorded_at,
            "command": self.command,
            "evidence_paths": list(self.evidence_paths),
            "notes": self.notes,
            "outcomes": list(self.outcomes),
        }


def load_consumption_proof(config: WorkspaceConfig, project: str) -> dict[str, object] | None:
    path = _consumption_proof_path(config, project)
    if not path.exists():
        return None
    payload = load_json_file(path)
    return payload if isinstance(payload, dict) else None


def record_consumption_proof(
    config: WorkspaceConfig,
    *,
    project: str,
    command: str | None,
    evidence_paths: list[str],
    notes: str | None,
    outcomes: list[str],
) -> dict[str, object]:
    project_slug = slugify(project)
    normalized_outcomes = [item.strip() for item in outcomes if isinstance(item, str) and item.strip()]
    payload = ConsumptionProof(
        project=project_slug,
        status="verified",
        recorded_at=_now_utc_iso(),
        command=command.strip() if isinstance(command, str) and command.strip() else None,
        evidence_paths=[str(Path(item).expanduser().resolve()) for item in evidence_paths],
        notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
        outcomes=normalized_outcomes,
    )
    dump_json_file(_consumption_proof_path(config, project_slug), payload.to_dict())
    return payload.to_dict()
