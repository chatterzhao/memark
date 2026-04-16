"""Workspace configuration and filesystem helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR_NAME = ".memark"
CONFIG_FILE_NAME = "config.json"
PROJECTS_FILE_NAME = "projects.toml"
SUPPORTED_MEM_TOOLS = {"mempalace", "mempal"}


def _runtime_binary(name: str) -> str | None:
    try:
        from .install import default_memark_home
    except Exception:
        return None
    scripts_dir = default_memark_home() / "venv" / ("Scripts" if os.name == "nt" else "bin")
    candidates = [scripts_dir / name]
    if not name.endswith(".exe"):
        candidates.append(scripts_dir / f"{name}.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def resolve_workspace_binary(configured: str, *, default_name: str) -> str:
    value = configured.strip()
    candidate = Path(value).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    if shutil.which(value) is not None:
        return value
    if value == "mempal":
        try:
            from .install import resolve_mempal_bin
        except Exception:
            return value
        resolved = resolve_mempal_bin()
        resolved_path = Path(resolved).expanduser()
        if resolved_path.is_file():
            return str(resolved_path.resolve())
    if value == default_name:
        runtime = _runtime_binary(default_name)
        if runtime is not None:
            return runtime
    return value


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


@dataclass(slots=True)
class WorkspaceConfig:
    workspace: Path
    default_project: str
    graphify_bin: str = "graphify"
    mem_tool: str = "mempalace"
    mem_tool_bin: str = "mempalace"

    @property
    def config_dir(self) -> Path:
        return self.workspace / CONFIG_DIR_NAME

    @property
    def config_file(self) -> Path:
        return self.config_dir / CONFIG_FILE_NAME

    @property
    def corpus_root_dir(self) -> Path:
        return self.config_dir / "corpus"

    @property
    def legacy_corpus_root_dir(self) -> Path:
        return self.workspace / "corpus"

    @property
    def projects_file(self) -> Path:
        return self.config_dir / PROJECTS_FILE_NAME

    @property
    def inbox_dir(self) -> Path:
        return self.workspace / "inbox"

    @property
    def inbox_promoted_dir(self) -> Path:
        return self.inbox_dir / "promoted"

    @property
    def archive_dir(self) -> Path:
        return self.config_dir / "archive"

    @property
    def state_dir(self) -> Path:
        return self.config_dir / "state"

    @property
    def staging_dir(self) -> Path:
        return self.config_dir / "staging"

    def corpus_project_dir(self, project: str | None = None) -> Path:
        name = slugify(project or self.default_project)
        return self.corpus_root_dir / name

    def legacy_corpus_project_dir(self, project: str | None = None) -> Path:
        name = slugify(project or self.default_project)
        return self.legacy_corpus_root_dir / name

    def promoted_dir(self, project: str | None = None) -> Path:
        return self.corpus_project_dir(project) / "promoted"

    def imports_dir(self, project: str | None = None) -> Path:
        return self.corpus_project_dir(project) / "imports"

    def ledger_file(self, project: str | None = None) -> Path:
        return self.state_dir / f"{slugify(project or self.default_project)}-ledger.json"

    def codex_sessions_dir(self, project: str | None = None) -> Path:
        return self.staging_dir / slugify(project or self.default_project) / "sessions"

    def codex_ledger_file(self, project: str | None = None) -> Path:
        return self.state_dir / f"{slugify(project or self.default_project)}-codex-sessions.json"

    @property
    def project_cycle_state_file(self) -> Path:
        return self.state_dir / "projects-run.json"

    @property
    def automation_cycle_state_file(self) -> Path:
        return self.state_dir / "automation-run.json"

    def palace_dir(self, project: str | None = None) -> Path:
        return self.config_dir / "palaces" / slugify(project or self.default_project)

    @property
    def mempalace_bin(self) -> str:
        return self.mem_tool_bin

    def migrate_legacy_corpus(self) -> None:
        legacy_root = self.legacy_corpus_root_dir
        if not legacy_root.exists() or not legacy_root.is_dir():
            return
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if self.corpus_root_dir.exists():
            shutil.copytree(legacy_root, self.corpus_root_dir, dirs_exist_ok=True)
            shutil.rmtree(legacy_root)
            return
        shutil.move(str(legacy_root), str(self.corpus_root_dir))

    def ensure_layout(self, project: str | None = None) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.migrate_legacy_corpus()
        for path in [
            self.inbox_dir,
            self.inbox_promoted_dir,
            self.archive_dir,
            self.state_dir,
            self.corpus_root_dir,
            self.codex_sessions_dir(project),
            self.palace_dir(project),
            self.promoted_dir(project),
            self.imports_dir(project),
        ]:
            path.mkdir(parents=True, exist_ok=True)


def resolve_workspace(path: str | None) -> Path:
    if path is None:
        return Path.cwd()
    return Path(path).expanduser().resolve()


INIT_REQUIRED_IGNORE_PATHS = (".memark",)


def missing_init_ignore_paths(workspace: Path) -> list[str]:
    missing: list[str] = []
    for entry in INIT_REQUIRED_IGNORE_PATHS:
        probe_dir = workspace / entry
        probe_file = probe_dir / ".memark-ignore-probe"
        created_dir = False
        created_file = False
        if not probe_dir.exists():
            probe_dir.mkdir(parents=True, exist_ok=True)
            created_dir = True
        if not probe_file.exists():
            probe_file.write_text("", encoding="utf-8")
            created_file = True
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(probe_file.relative_to(workspace))],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            check=False,
        )
        if created_file:
            probe_file.unlink()
        if created_dir:
            probe_dir.rmdir()
        if result.returncode != 0:
            missing.append(entry)
    return missing


def create_workspace(
    workspace: Path,
    project: str,
    graphify_bin: str = "graphify",
    mem_tool: str = "mempalace",
    mem_tool_bin: str | None = None,
    mempalace_bin: str | None = None,
) -> WorkspaceConfig:
    normalized_mem_tool = mem_tool.strip().lower()
    if normalized_mem_tool not in SUPPORTED_MEM_TOOLS:
        raise ValueError(f"Unsupported mem_tool '{mem_tool}'. Expected one of: {', '.join(sorted(SUPPORTED_MEM_TOOLS))}")
    resolved_mem_tool_bin = (mem_tool_bin or mempalace_bin or normalized_mem_tool).strip()
    config = WorkspaceConfig(
        workspace=workspace,
        default_project=slugify(project),
        graphify_bin=graphify_bin,
        mem_tool=normalized_mem_tool,
        mem_tool_bin=resolved_mem_tool_bin,
    )
    config.ensure_layout()
    config.config_file.write_text(
        json.dumps(
            {
                "default_project": config.default_project,
                "graphify_bin": graphify_bin,
                "mem_tool": config.mem_tool,
                "mem_tool_bin": config.mem_tool_bin,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if not config.projects_file.exists():
        config.projects_file.write_text("version = 1\n", encoding="utf-8")

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
    graphify_bin = resolve_workspace_binary(graphify_bin, default_name="graphify")
    mem_tool = payload.get("mem_tool", "mempalace")
    if not isinstance(mem_tool, str) or not mem_tool.strip():
        mem_tool = "mempalace"
    mem_tool = mem_tool.strip().lower()
    if mem_tool not in SUPPORTED_MEM_TOOLS:
        raise ValueError(f"Invalid mem_tool '{mem_tool}' in {config_file}")
    mem_tool_bin = payload.get("mem_tool_bin", payload.get("mempalace_bin"))
    if not isinstance(mem_tool_bin, str) or not mem_tool_bin.strip():
        mem_tool_bin = mem_tool
    mem_tool_bin = resolve_workspace_binary(mem_tool_bin, default_name=mem_tool)
    config = WorkspaceConfig(
        workspace=workspace,
        default_project=slugify(default_project),
        graphify_bin=graphify_bin.strip(),
        mem_tool=mem_tool,
        mem_tool_bin=mem_tool_bin.strip(),
    )
    config.ensure_layout()
    return config
