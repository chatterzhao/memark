"""MemPalace integration helpers."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class MemPalaceError(RuntimeError):
    """Raised when MemPalace is unavailable or its command fails."""


@dataclass(slots=True)
class MemPalaceMineResult:
    command: list[str]
    palace_dir: Path
    staging_dir: Path
    stdout: str
    stderr: str
    attempts: int
    started_at: str
    finished_at: str
    elapsed_seconds: float


def _resolve_mempalace_binary(mempalace_bin: str) -> str:
    binary = shutil.which(mempalace_bin)
    if binary is None:
        raise MemPalaceError(
            f"MemPalace CLI '{mempalace_bin}' not found in PATH. Install and verify mempalace before mining."
        )
    return binary


def _is_lock_error(stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}".lower()
    return "database is locked" in combined or "sqlite" in combined and "locked" in combined


def _run_mempalace_command(
    command: list[str],
    *,
    cwd: Path,
    action: str,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
) -> tuple[str, str, int]:
    attempts = max(retry_attempts, 1)
    delay = max(retry_delay_seconds, 0.0)
    last_completed: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, attempts + 1):
        completed = subprocess.run(
            command,
            cwd=cwd,
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
    raise MemPalaceError(
        f"MemPalace {action} failed with exit code {last_completed.returncode} after {attempts} attempt(s)\n"
        f"STDOUT:\n{last_completed.stdout}\nSTDERR:\n{last_completed.stderr}"
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_palace_dir(palace_dir: Path) -> Path:
    normalized = palace_dir.expanduser().resolve()
    if normalized.exists():
        shutil.rmtree(normalized)
    normalized.mkdir(parents=True, exist_ok=True)
    return normalized


def run_mempalace_convo_mine(
    *,
    mempalace_bin: str,
    palace_dir: Path,
    staging_dir: Path,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
) -> MemPalaceMineResult:
    binary = _resolve_mempalace_binary(mempalace_bin)
    if not staging_dir.exists():
        raise MemPalaceError(f"Codex staging directory does not exist: {staging_dir}")

    command = [binary, "--palace", str(palace_dir), "mine", str(staging_dir), "--mode", "convos"]
    started_at = _utc_now_iso()
    started_perf = time.perf_counter()
    stdout, stderr, attempts = _run_mempalace_command(
        command,
        cwd=staging_dir,
        action="mine",
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    finished_at = _utc_now_iso()
    elapsed_seconds = round(time.perf_counter() - started_perf, 3)
    return MemPalaceMineResult(
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
