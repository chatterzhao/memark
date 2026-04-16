"""User-level intake scheduler helpers."""

from __future__ import annotations

import hashlib
import os
import plistlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

from .automation import load_automation_cycle_state
from .install import InstallError, default_memark_home
from .workspace import WorkspaceConfig, slugify


@dataclass(frozen=True)
class ServiceInstallResult:
    scheduler: str
    workspace: Path
    project: str | None
    interval_seconds: int
    label: str
    plist_path: Path
    stdout_path: Path
    stderr_path: Path
    command: list[str]
    environment: dict[str, str]
    loaded: bool
    dry_run: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "scheduler": self.scheduler,
            "workspace": str(self.workspace),
            "project": self.project,
            "interval_seconds": self.interval_seconds,
            "label": self.label,
            "plist_path": str(self.plist_path),
            "stdout_path": str(self.stdout_path),
            "stderr_path": str(self.stderr_path),
            "command": list(self.command),
            "environment": dict(self.environment),
            "loaded": self.loaded,
            "dry_run": self.dry_run,
        }


@dataclass(frozen=True)
class ServiceStatus:
    scheduler: str
    workspace: Path
    project: str | None
    label: str
    interval_seconds: int
    plist_path: Path
    stdout_path: Path
    stderr_path: Path
    command: list[str]
    environment: dict[str, str]
    installed: bool
    loaded: bool
    stdout_bytes: int
    stderr_bytes: int
    health: str
    observations: list[str]
    last_cycle: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "scheduler": self.scheduler,
            "workspace": str(self.workspace),
            "project": self.project,
            "label": self.label,
            "interval_seconds": self.interval_seconds,
            "plist_path": str(self.plist_path),
            "stdout_path": str(self.stdout_path),
            "stderr_path": str(self.stderr_path),
            "command": list(self.command),
            "environment": dict(self.environment),
            "installed": self.installed,
            "loaded": self.loaded,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
            "health": self.health,
            "observations": list(self.observations),
            "last_cycle": self.last_cycle,
        }


@dataclass(frozen=True)
class ServiceUninstallResult:
    scheduler: str
    workspace: Path
    project: str | None
    label: str
    plist_path: Path
    removed: bool
    unloaded: bool
    dry_run: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "scheduler": self.scheduler,
            "workspace": str(self.workspace),
            "project": self.project,
            "label": self.label,
            "plist_path": str(self.plist_path),
            "removed": self.removed,
            "unloaded": self.unloaded,
            "dry_run": self.dry_run,
        }


def resolve_scheduler(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "launchd":
        return "launchd"
    if normalized != "auto":
        raise InstallError(f"Unsupported scheduler '{value}'. Use auto or launchd.")
    if sys.platform == "darwin":
        return "launchd"
    raise InstallError("Automatic intake scheduler is not implemented for this platform yet. Use --scheduler launchd on macOS.")


def _launch_agents_dir() -> Path:
    return Path("~/Library/LaunchAgents").expanduser().resolve()


def _workspace_logs_dir(workspace: Path) -> Path:
    return workspace / ".memark" / "logs"


def _service_label(workspace: Path, project: str | None) -> str:
    workspace_slug = slugify(workspace.name or "workspace")
    digest = hashlib.sha1(str(workspace).encode("utf-8")).hexdigest()[:10]
    if project:
        return f"io.memark.projects-run.{workspace_slug}.{slugify(project)}.{digest}"
    return f"io.memark.projects-run.{workspace_slug}.{digest}"


def _service_invocation() -> tuple[list[str], dict[str, str]]:
    package_root = Path(__file__).resolve().parents[1]
    if (package_root / "pyproject.toml").exists():
        pythonpath_entries = [str(package_root)]
        current_pythonpath = os.environ.get("PYTHONPATH")
        if current_pythonpath:
            for entry in current_pythonpath.split(os.pathsep):
                if entry and entry not in pythonpath_entries:
                    pythonpath_entries.append(entry)
        return [sys.executable, "-m", "memark"], {"PYTHONPATH": os.pathsep.join(pythonpath_entries)}

    runtime_scripts_dir = default_memark_home() / "venv" / ("Scripts" if os.name == "nt" else "bin")
    runtime_memark = runtime_scripts_dir / ("memark.exe" if os.name == "nt" else "memark")
    if runtime_memark.exists():
        return [str(runtime_memark)], {}

    argv0 = Path(sys.argv[0]).expanduser()
    if argv0.exists() and not argv0.name.startswith("python"):
        return [str(argv0.resolve())], {}
    return [sys.executable, "-m", "memark"], {}


def _launchd_paths(workspace: Path, project: str | None) -> tuple[str, Path, Path, Path]:
    label = _service_label(workspace, project)
    plist_path = _launch_agents_dir() / f"{label}.plist"
    logs_dir = _workspace_logs_dir(workspace)
    stdout_path = logs_dir / f"{label}.out.log"
    stderr_path = logs_dir / f"{label}.err.log"
    return label, plist_path, stdout_path, stderr_path


def _load_launchd_runtime_config(
    plist_path: Path,
    *,
    fallback_command: list[str],
    fallback_environment: dict[str, str],
    fallback_interval_seconds: int,
) -> tuple[list[str], dict[str, str], int]:
    if not plist_path.exists():
        return fallback_command, fallback_environment, fallback_interval_seconds
    try:
        payload = plistlib.loads(plist_path.read_bytes())
    except (OSError, ValueError, plistlib.InvalidFileException):
        return fallback_command, fallback_environment, fallback_interval_seconds
    if not isinstance(payload, dict):
        return fallback_command, fallback_environment, fallback_interval_seconds

    command = payload.get("ProgramArguments")
    environment = payload.get("EnvironmentVariables")
    interval_seconds = payload.get("StartInterval")
    resolved_command = command if isinstance(command, list) and all(isinstance(item, str) for item in command) else fallback_command
    resolved_environment = (
        environment
        if isinstance(environment, dict) and all(isinstance(key, str) and isinstance(value, str) for key, value in environment.items())
        else fallback_environment
    )
    resolved_interval = int(interval_seconds) if isinstance(interval_seconds, int) and interval_seconds > 0 else fallback_interval_seconds
    return resolved_command, resolved_environment, resolved_interval


def _path_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _parse_iso8601(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _service_health(
    *,
    installed: bool,
    loaded: bool,
    interval_seconds: int,
    last_cycle: dict[str, object] | None,
    stdout_bytes: int,
    stderr_bytes: int,
) -> tuple[str, list[str]]:
    observations: list[str] = []
    if not installed:
        observations.append("scheduler plist is not installed")
        return "not_installed", observations
    if not loaded:
        observations.append("scheduler is installed but not loaded")
        return "not_loaded", observations
    if last_cycle is None:
        observations.append("no persisted automation cycle state found yet")
        return "no_cycle_recorded", observations

    status = str(last_cycle.get("status") or "unknown")
    if status == "failed":
        observations.append("last automation cycle failed")
        return "failing", observations
    if status == "running":
        observations.append("automation cycle is currently marked running")
        return "running", observations

    finished_at = _parse_iso8601(last_cycle.get("finished_at"))
    if finished_at is None:
        observations.append("last cycle has no parseable finished_at timestamp")
        return "unknown", observations

    age_seconds = max(0, int((datetime.now(timezone.utc) - finished_at).total_seconds()))
    observations.append(f"last completed cycle age: {age_seconds}s")
    stale_threshold = max(interval_seconds * 2, interval_seconds + 120)
    if age_seconds > stale_threshold:
        observations.append(f"last completed cycle is older than stale threshold ({stale_threshold}s)")
        return "stale", observations

    if stdout_bytes == 0 and stderr_bytes == 0:
        observations.append("stdout/stderr logs are both empty")
    return "ok", observations


def _launchd_payload(
    workspace: Path,
    *,
    project: str | None,
    interval_seconds: int,
) -> tuple[str, Path, Path, Path, list[str], dict[str, str], bytes]:
    label, plist_path, stdout_path, stderr_path = _launchd_paths(workspace, project)
    program_args, environment = _service_invocation()
    command = [*program_args, "automation-run", "--workspace", str(workspace)]
    if project:
        command.extend(["--project", project])
    payload = {
        "Label": label,
        "ProgramArguments": command,
        "RunAtLoad": True,
        "StartInterval": max(int(interval_seconds), 60),
        "StandardOutPath": str(stdout_path),
        "StandardErrorPath": str(stderr_path),
        "WorkingDirectory": str(workspace),
    }
    if environment:
        payload["EnvironmentVariables"] = environment
    return label, plist_path, stdout_path, stderr_path, command, environment, plistlib.dumps(payload)


def _launchctl_bin() -> str:
    binary = shutil.which("launchctl")
    if binary is None:
        raise InstallError("launchctl not found in PATH")
    return binary


def _launchctl_domain() -> str:
    return f"gui/{os.getuid()}"


def _run_launchctl(args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run([_launchctl_bin(), *args], text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "launchctl command failed"
        raise InstallError(f"launchctl {' '.join(args)}: {detail}")
    return completed


def install_launchd_service(
    workspace: Path,
    *,
    project: str | None = None,
    interval_seconds: int = 300,
    dry_run: bool = False,
) -> ServiceInstallResult:
    resolved_workspace = workspace.expanduser().resolve()
    label, plist_path, stdout_path, stderr_path, command, environment, payload = _launchd_payload(
        resolved_workspace,
        project=project,
        interval_seconds=interval_seconds,
    )

    if not dry_run:
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_bytes(payload)
        domain = _launchctl_domain()
        _run_launchctl(["bootout", domain, str(plist_path)], check=False)
        _run_launchctl(["bootstrap", domain, str(plist_path)], check=True)
        _run_launchctl(["enable", f"{domain}/{label}"], check=False)
        _run_launchctl(["kickstart", "-k", f"{domain}/{label}"], check=False)

    return ServiceInstallResult(
        scheduler="launchd",
        workspace=resolved_workspace,
        project=project,
        interval_seconds=max(int(interval_seconds), 60),
        label=label,
        plist_path=plist_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        command=command,
        environment=environment,
        loaded=not dry_run,
        dry_run=dry_run,
    )


def status_launchd_service(workspace: Path, *, project: str | None = None) -> ServiceStatus:
    resolved_workspace = workspace.expanduser().resolve()
    label, plist_path, stdout_path, stderr_path, command, environment, _ = _launchd_payload(
        resolved_workspace,
        project=project,
        interval_seconds=300,
    )
    installed = plist_path.exists()
    command, environment, interval_seconds = _load_launchd_runtime_config(
        plist_path,
        fallback_command=command,
        fallback_environment=environment,
        fallback_interval_seconds=300,
    )
    loaded = False
    if installed:
        domain = _launchctl_domain()
        completed = _run_launchctl(["print", f"{domain}/{label}"], check=False)
        loaded = completed.returncode == 0
    config = WorkspaceConfig(workspace=resolved_workspace, default_project=project or "default")
    last_cycle = load_automation_cycle_state(config)
    stdout_bytes = _path_size(stdout_path)
    stderr_bytes = _path_size(stderr_path)
    health, observations = _service_health(
        installed=installed,
        loaded=loaded,
        interval_seconds=interval_seconds,
        last_cycle=last_cycle,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
    )
    return ServiceStatus(
        scheduler="launchd",
        workspace=resolved_workspace,
        project=project,
        label=label,
        interval_seconds=interval_seconds,
        plist_path=plist_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        command=command,
        environment=environment,
        installed=installed,
        loaded=loaded,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        health=health,
        observations=observations,
        last_cycle=last_cycle,
    )


def uninstall_launchd_service(workspace: Path, *, project: str | None = None, dry_run: bool = False) -> ServiceUninstallResult:
    resolved_workspace = workspace.expanduser().resolve()
    label, plist_path, _, _, _, _, _ = _launchd_payload(
        resolved_workspace,
        project=project,
        interval_seconds=300,
    )
    unloaded = False
    removed = False
    if not dry_run:
        if plist_path.exists():
            domain = _launchctl_domain()
            completed = _run_launchctl(["bootout", domain, str(plist_path)], check=False)
            unloaded = completed.returncode == 0
            plist_path.unlink()
        removed = not plist_path.exists()
    return ServiceUninstallResult(
        scheduler="launchd",
        workspace=resolved_workspace,
        project=project,
        label=label,
        plist_path=plist_path,
        removed=removed,
        unloaded=unloaded,
        dry_run=dry_run,
    )
