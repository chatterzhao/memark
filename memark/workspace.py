"""Workspace configuration and filesystem helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR_NAME = ".memark"
CONFIG_FILE_NAME = "config.json"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


@dataclass(slots=True)
class WorkspaceConfig:
    workspace: Path
    default_project: str
    graphify_bin: str = "graphify"

    @property
    def config_dir(self) -> Path:
        return self.workspace / CONFIG_DIR_NAME

    @property
    def config_file(self) -> Path:
        return self.config_dir / CONFIG_FILE_NAME

    @property
    def inbox_dir(self) -> Path:
        return self.workspace / "inbox"

    @property
    def inbox_promoted_dir(self) -> Path:
        return self.inbox_dir / "promoted"

    @property
    def inbox_documents_dir(self) -> Path:
        return self.inbox_dir / "documents"

    @property
    def archive_dir(self) -> Path:
        return self.config_dir / "archive"

    @property
    def state_dir(self) -> Path:
        return self.config_dir / "state"

    def corpus_project_dir(self, project: str | None = None) -> Path:
        name = slugify(project or self.default_project)
        return self.workspace / "corpus" / name

    def promoted_dir(self, project: str | None = None) -> Path:
        return self.corpus_project_dir(project) / "promoted"

    def documents_dir(self, project: str | None = None) -> Path:
        return self.corpus_project_dir(project) / "documents"

    def imports_dir(self, project: str | None = None) -> Path:
        return self.corpus_project_dir(project) / "imports"

    def ledger_file(self, project: str | None = None) -> Path:
        return self.state_dir / f"{slugify(project or self.default_project)}-ledger.json"

    def ensure_layout(self, project: str | None = None) -> None:
        for path in [
            self.config_dir,
            self.inbox_dir,
            self.inbox_promoted_dir,
            self.inbox_documents_dir,
            self.archive_dir,
            self.state_dir,
            self.promoted_dir(project),
            self.documents_dir(project),
            self.imports_dir(project),
        ]:
            path.mkdir(parents=True, exist_ok=True)


def resolve_workspace(path: str | None) -> Path:
    if path is None:
        return Path.cwd()
    return Path(path).expanduser().resolve()


def create_workspace(workspace: Path, project: str, graphify_bin: str = "graphify") -> WorkspaceConfig:
    config = WorkspaceConfig(workspace=workspace, default_project=slugify(project), graphify_bin=graphify_bin)
    config.ensure_layout()
    config.config_file.write_text(
        json.dumps(
            {
                "default_project": config.default_project,
                "graphify_bin": graphify_bin,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return config


def load_workspace(path: str | None) -> WorkspaceConfig:
    workspace = resolve_workspace(path)
    config_file = workspace / CONFIG_DIR_NAME / CONFIG_FILE_NAME
    if not config_file.exists():
        raise FileNotFoundError(
            f"MemArk workspace not initialized at {workspace}. Run 'memark init {workspace}' first."
        )
    payload = json.loads(config_file.read_text(encoding="utf-8"))
    default_project = payload.get("default_project")
    if not isinstance(default_project, str) or not default_project.strip():
        raise ValueError(f"Invalid MemArk config: {config_file}")
    graphify_bin = payload.get("graphify_bin")
    if not isinstance(graphify_bin, str) or not graphify_bin.strip():
        graphify_bin = "graphify"
    config = WorkspaceConfig(
        workspace=workspace,
        default_project=slugify(default_project),
        graphify_bin=graphify_bin.strip(),
    )
    config.ensure_layout()
    return config
