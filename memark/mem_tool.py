"""Memory tool dispatch helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .mempalace import MemPalaceMineResult, run_mempalace_convo_mine


SUPPORTED_MEM_TOOLS = ("mempalace", "mempal")


class MemToolError(RuntimeError):
    """Raised when a selected memory tool cannot fulfill a requested operation."""


@dataclass(slots=True)
class MemToolMineResult:
    tool: str
    bin_name: str
    command: list[str]
    palace_dir: Path
    staging_dir: Path
    stdout: str
    stderr: str
    attempts: int
    started_at: str
    finished_at: str
    elapsed_seconds: float

    @classmethod
    def from_mempalace(cls, result: MemPalaceMineResult, *, bin_name: str) -> "MemToolMineResult":
        return cls(
            tool="mempalace",
            bin_name=bin_name,
            command=result.command,
            palace_dir=result.palace_dir,
            staging_dir=result.staging_dir,
            stdout=result.stdout,
            stderr=result.stderr,
            attempts=result.attempts,
            started_at=result.started_at,
            finished_at=result.finished_at,
            elapsed_seconds=result.elapsed_seconds,
        )


def _resolve_binary(binary_name: str, *, tool_label: str) -> str:
    binary = shutil.which(binary_name)
    if binary is None:
        raise MemToolError(f"{tool_label} CLI '{binary_name}' not found in PATH.")
    return binary


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_lock_error(stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}".lower()
    return "database is locked" in combined or ("sqlite" in combined and "locked" in combined)


def _run_mem_tool_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    action: str,
    tool_label: str,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
) -> tuple[str, str, int]:
    attempts = max(retry_attempts, 1)
    delay = max(retry_delay_seconds, 0.0)
    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    last_completed: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, attempts + 1):
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=base_env,
            text=True,
            capture_output=True,
            check=False,
        )
        last_completed = completed
        if completed.returncode == 0:
            return completed.stdout, completed.stderr, attempt
        if attempt >= attempts or not _is_lock_error(completed.stdout, completed.stderr):
            break
        time.sleep(delay)
        delay *= 2
    assert last_completed is not None
    raise MemToolError(
        f"{tool_label} {action} failed with exit code {last_completed.returncode} after {attempts} attempt(s)\n"
        f"STDOUT:\n{last_completed.stdout}\nSTDERR:\n{last_completed.stderr}"
    )


def _mempal_runtime_home(*, palace_dir: Path) -> Path:
    return palace_dir.parent / f".mempal-home-{palace_dir.name}"


def _mempal_db_path(*, palace_dir: Path) -> Path:
    return palace_dir / "palace.db"


def _ensure_mempal_runtime_config(*, palace_dir: Path) -> Path:
    runtime_home = _mempal_runtime_home(palace_dir=palace_dir)
    config_dir = runtime_home / ".mempal"
    config_dir.mkdir(parents=True, exist_ok=True)
    db_path = _mempal_db_path(palace_dir=palace_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"
    config_path.write_text(
        'db_path = "{}"\n'.format(str(db_path).replace("\\", "\\\\")),
        encoding="utf-8",
    )
    return runtime_home


def _mempal_wing_from_palace_dir(*, palace_dir: Path) -> str:
    return palace_dir.name


def _run_mempal_convo_mine(
    *,
    mempal_bin: str,
    palace_dir: Path,
    staging_dir: Path,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
) -> MemToolMineResult:
    binary = _resolve_binary(mempal_bin, tool_label="MemPal")
    if not staging_dir.exists():
        raise MemToolError(f"Codex staging directory does not exist: {staging_dir}")

    runtime_home = _ensure_mempal_runtime_config(palace_dir=palace_dir)
    command = [
        binary,
        "ingest",
        str(staging_dir),
        "--wing",
        _mempal_wing_from_palace_dir(palace_dir=palace_dir),
        "--format",
        "convos",
    ]
    started_at = _utc_now_iso()
    started_perf = time.perf_counter()
    stdout, stderr, attempts = _run_mem_tool_command(
        command,
        cwd=staging_dir,
        env={"HOME": str(runtime_home)},
        action="ingest",
        tool_label="MemPal",
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    finished_at = _utc_now_iso()
    elapsed_seconds = round(time.perf_counter() - started_perf, 3)
    return MemToolMineResult(
        tool="mempal",
        bin_name=mempal_bin,
        command=command,
        palace_dir=palace_dir,
        staging_dir=staging_dir,
        stdout=stdout,
        stderr=stderr,
        attempts=attempts,
        started_at=started_at,
        finished_at=finished_at,
        elapsed_seconds=elapsed_seconds,
    )


def validate_mem_tool(mem_tool: str) -> str:
    normalized = mem_tool.strip().lower()
    if normalized not in SUPPORTED_MEM_TOOLS:
        raise MemToolError(f"Unsupported mem_tool '{mem_tool}'. Expected one of: {', '.join(SUPPORTED_MEM_TOOLS)}")
    return normalized


def build_mem_tool_mine_command(*, mem_tool: str, mem_tool_bin: str, palace_dir: Path, staging_dir: Path) -> list[str]:
    normalized = validate_mem_tool(mem_tool)
    if normalized == "mempalace":
        return [mem_tool_bin, "--palace", str(palace_dir), "mine", str(staging_dir), "--mode", "convos"]
    return [mem_tool_bin, "ingest", str(staging_dir), "--wing", _mempal_wing_from_palace_dir(palace_dir=palace_dir), "--format", "convos"]


def mem_tool_available(*, mem_tool_bin: str) -> bool:
    return shutil.which(mem_tool_bin) is not None


def run_mem_tool_convo_mine(
    *,
    mem_tool: str,
    mem_tool_bin: str,
    palace_dir: Path,
    staging_dir: Path,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
) -> MemToolMineResult:
    normalized = validate_mem_tool(mem_tool)
    if normalized == "mempalace":
        result = run_mempalace_convo_mine(
            mempalace_bin=mem_tool_bin,
            palace_dir=palace_dir,
            staging_dir=staging_dir,
            retry_attempts=retry_attempts,
            retry_delay_seconds=retry_delay_seconds,
        )
        return MemToolMineResult.from_mempalace(result, bin_name=mem_tool_bin)
    return _run_mempal_convo_mine(
        mempal_bin=mem_tool_bin,
        palace_dir=palace_dir,
        staging_dir=staging_dir,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
