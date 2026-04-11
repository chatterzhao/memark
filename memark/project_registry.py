"""Tracked path registry and single-cycle orchestration for Codex -> MemPalace intake."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .codex import CodexSyncResult, sync_codex_sessions
from .io import dump_json_file, load_json_file
from .mempalace import MemPalaceMineResult, run_mempalace_convo_mine
from .workspace import WorkspaceConfig, slugify

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(slots=True)
class ProjectProfile:
    name: str
    path: str
    sessions_root: str = "~/.codex/sessions"
    extra_paths: list[str] | None = None
    mine_interval_seconds: int = 120
    auto_mine: bool = True
    enabled: bool = True

    def normalized_name(self) -> str:
        return slugify(self.name)

    def normalized_path(self) -> Path:
        return Path(self.path).expanduser().resolve()

    def normalized_sessions_root(self) -> Path:
        return Path(self.sessions_root).expanduser().resolve()

    def normalized_extra_paths(self) -> list[Path]:
        return [Path(value).expanduser().resolve() for value in self.extra_paths or []]

    # Compatibility aliases for older code and config naming.
    def normalized_root(self) -> Path:
        return self.normalized_path()

    def normalized_cwd_prefixes(self) -> list[Path]:
        return self.normalized_extra_paths()


@dataclass(slots=True)
class ProjectCycleState:
    pending_mine: bool = False
    last_run_at: str | None = None
    last_mined_at: str | None = None


@dataclass(slots=True)
class ProjectCycleResult:
    project: str
    sync: CodexSyncResult
    pending_mine: bool
    mined: bool
    mine_skipped_reason: str | None
    mine_command: list[str] | None = None
    mine_attempts: int | None = None
    mine_started_at: str | None = None
    mine_finished_at: str | None = None
    mine_elapsed_seconds: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "sync": self.sync.to_dict(),
            "pending_mine": self.pending_mine,
            "mined": self.mined,
            "mine_skipped_reason": self.mine_skipped_reason,
            "mine_command": self.mine_command,
            "mine_attempts": self.mine_attempts,
            "mine_started_at": self.mine_started_at,
            "mine_finished_at": self.mine_finished_at,
            "mine_elapsed_seconds": self.mine_elapsed_seconds,
        }


def _toml_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _render_projects_toml(profiles: list[ProjectProfile]) -> str:
    lines = ["version = 1", ""]
    for profile in sorted(profiles, key=lambda item: item.normalized_name()):
        extra_paths = profile.extra_paths or []
        extra_path_values = ", ".join(_toml_string(value) for value in extra_paths)
        lines.extend(
            [
                "[[projects]]",
                f"name = {_toml_string(profile.normalized_name())}",
                f"path = {_toml_string(str(profile.normalized_path()))}",
                f"sessions_root = {_toml_string(profile.sessions_root)}",
                f"extra_paths = [{extra_path_values}]",
                f"mine_interval_seconds = {max(int(profile.mine_interval_seconds), 0)}",
                f"auto_mine = {'true' if profile.auto_mine else 'false'}",
                f"enabled = {'true' if profile.enabled else 'false'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def load_project_profiles(path: Path) -> list[ProjectProfile]:
    if not path.exists():
        return []
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("projects", [])
    if not isinstance(entries, list):
        raise ValueError(f"Invalid project registry: {path}")
    profiles: list[ProjectProfile] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        tracked_path = entry.get("path", entry.get("root"))
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Invalid project registry entry without name: {path}")
        if not isinstance(tracked_path, str) or not tracked_path.strip():
            raise ValueError(f"Invalid project registry entry without path for {name}: {path}")
        extra_paths = entry.get("extra_paths", entry.get("cwd_prefixes", []))
        if extra_paths is None:
            extra_paths = []
        if not isinstance(extra_paths, list) or any(not isinstance(value, str) for value in extra_paths):
            raise ValueError(f"Invalid extra_paths for project {name}: {path}")
        sessions_root = entry.get("sessions_root", "~/.codex/sessions")
        if not isinstance(sessions_root, str) or not sessions_root.strip():
            raise ValueError(f"Invalid sessions_root for project {name}: {path}")
        mine_interval_seconds = entry.get("mine_interval_seconds", 120)
        if not isinstance(mine_interval_seconds, int):
            raise ValueError(f"Invalid mine_interval_seconds for project {name}: {path}")
        auto_mine = entry.get("auto_mine", True)
        if not isinstance(auto_mine, bool):
            raise ValueError(f"Invalid auto_mine for project {name}: {path}")
        enabled = entry.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"Invalid enabled for project {name}: {path}")
        profiles.append(
            ProjectProfile(
                name=slugify(name),
                path=tracked_path,
                sessions_root=sessions_root,
                extra_paths=extra_paths,
                mine_interval_seconds=mine_interval_seconds,
                auto_mine=auto_mine,
                enabled=enabled,
            )
        )
    return profiles


def save_project_profiles(path: Path, profiles: list[ProjectProfile]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_projects_toml(profiles), encoding="utf-8")


def upsert_project_profile(path: Path, profile: ProjectProfile) -> list[ProjectProfile]:
    profiles = load_project_profiles(path)
    next_profiles = [existing for existing in profiles if existing.normalized_name() != profile.normalized_name()]
    next_profiles.append(
        ProjectProfile(
            name=profile.normalized_name(),
            path=str(profile.normalized_path()),
            sessions_root=profile.sessions_root,
            extra_paths=[str(value) for value in profile.normalized_extra_paths()],
            mine_interval_seconds=max(int(profile.mine_interval_seconds), 0),
            auto_mine=profile.auto_mine,
            enabled=profile.enabled,
        )
    )
    save_project_profiles(path, next_profiles)
    return sorted(next_profiles, key=lambda item: item.normalized_name())


def _load_cycle_state(path: Path) -> dict[str, ProjectCycleState]:
    if not path.exists():
        return {}
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        return {}
    states: dict[str, ProjectCycleState] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        states[key] = ProjectCycleState(
            pending_mine=bool(value.get("pending_mine", False)),
            last_run_at=value.get("last_run_at") if isinstance(value.get("last_run_at"), str) else None,
            last_mined_at=value.get("last_mined_at") if isinstance(value.get("last_mined_at"), str) else None,
        )
    return states


def load_cycle_state(path: Path) -> dict[str, ProjectCycleState]:
    return _load_cycle_state(path)


def _save_cycle_state(path: Path, states: dict[str, ProjectCycleState]) -> None:
    dump_json_file(path, {key: asdict(value) for key, value in sorted(states.items())})


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None
    return datetime.fromisoformat(value)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _should_mine(state: ProjectCycleState, profile: ProjectProfile, now: datetime) -> bool:
    if not state.pending_mine or not profile.auto_mine:
        return False
    last_mined_at = _parse_timestamp(state.last_mined_at)
    if last_mined_at is None:
        return True
    interval = timedelta(seconds=max(int(profile.mine_interval_seconds), 0))
    return now >= last_mined_at + interval


def run_projects_cycle(
    config: WorkspaceConfig,
    *,
    project_filter: str | None = None,
    dry_run: bool = False,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
    progress: Callable[[str], None] | None = None,
) -> list[ProjectCycleResult]:
    profiles = load_project_profiles(config.projects_file)
    if project_filter is not None:
        target = slugify(project_filter)
        profiles = [profile for profile in profiles if profile.normalized_name() == target]
    profiles = [profile for profile in profiles if profile.enabled]
    states = _load_cycle_state(config.project_cycle_state_file)
    next_states = dict(states)
    results: list[ProjectCycleResult] = []

    now = _now_utc()
    now_iso = now.isoformat()
    for profile in profiles:
        project = profile.normalized_name()
        if progress is not None:
            progress(f"Running project: {project}")
        sync = sync_codex_sessions(
            config=config,
            project=project,
            tracked_path=profile.normalized_path(),
            sessions_root=profile.normalized_sessions_root(),
            extra_paths=profile.normalized_extra_paths(),
            dry_run=dry_run,
        )
        if progress is not None:
            progress(
                f"  Sync: copied={sync.copied} updated={sync.updated} unchanged={sync.unchanged} invalid={sync.invalid}"
            )
        state = next_states.get(project, ProjectCycleState())
        if sync.copied or sync.updated:
            state.pending_mine = True
        state.last_run_at = now_iso
        next_states[project] = state
        if not dry_run:
            _save_cycle_state(config.project_cycle_state_file, next_states)
        mined = False
        mine_skipped_reason: str | None = None
        mine_result: MemPalaceMineResult | None = None
        if state.pending_mine:
            if not profile.auto_mine:
                mine_skipped_reason = "auto_mine_disabled"
                if progress is not None:
                    progress(f"  Mine: skipped ({mine_skipped_reason})")
            elif not _should_mine(state, profile, now):
                mine_skipped_reason = "mine_interval_not_elapsed"
                if progress is not None:
                    progress(f"  Mine: skipped ({mine_skipped_reason})")
            elif dry_run:
                mined = True
                if progress is not None:
                    progress("  Mine: dry-run")
            else:
                if progress is not None:
                    progress(f"  Mine: starting {config.codex_sessions_dir(project)}")
                mine_result = run_mempalace_convo_mine(
                    mempalace_bin=config.mempalace_bin,
                    palace_dir=config.palace_dir(project),
                    staging_dir=config.codex_sessions_dir(project),
                    retry_attempts=retry_attempts,
                    retry_delay_seconds=retry_delay_seconds,
                )
                mined = True
                state.pending_mine = False
                state.last_mined_at = now_iso
                next_states[project] = state
                _save_cycle_state(config.project_cycle_state_file, next_states)
                if progress is not None:
                    progress(f"  Mine: completed attempts={mine_result.attempts}")
        else:
            mine_skipped_reason = "no_pending_changes"
            if progress is not None:
                progress(f"  Mine: skipped ({mine_skipped_reason})")
        results.append(
            ProjectCycleResult(
                project=project,
                sync=sync,
                pending_mine=state.pending_mine,
                mined=mined,
                mine_skipped_reason=None if mined else mine_skipped_reason,
                mine_command=mine_result.command if mine_result is not None else None,
                mine_attempts=mine_result.attempts if mine_result is not None else None,
                mine_started_at=mine_result.started_at if mine_result is not None else None,
                mine_finished_at=mine_result.finished_at if mine_result is not None else None,
                mine_elapsed_seconds=mine_result.elapsed_seconds if mine_result is not None else None,
            )
        )

    if not dry_run and profiles:
        _save_cycle_state(config.project_cycle_state_file, next_states)
    return results
