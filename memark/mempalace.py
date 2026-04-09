"""MemPalace integration helpers."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
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


def _resolve_mempalace_binary(mempalace_bin: str) -> str:
    binary = shutil.which(mempalace_bin)
    if binary is None:
        raise MemPalaceError(
            f"MemPalace CLI '{mempalace_bin}' not found in PATH. Install and verify mempalace before mining."
        )
    return binary


def _run_mempalace_command(command: list[str], *, cwd: Path, action: str) -> tuple[str, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise MemPalaceError(
            f"MemPalace {action} failed with exit code {completed.returncode}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed.stdout, completed.stderr


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
) -> MemPalaceMineResult:
    binary = _resolve_mempalace_binary(mempalace_bin)
    if not staging_dir.exists():
        raise MemPalaceError(f"Codex staging directory does not exist: {staging_dir}")

    command = [binary, "--palace", str(palace_dir), "mine", str(staging_dir), "--mode", "convos"]
    stdout, stderr = _run_mempalace_command(command, cwd=staging_dir, action="mine")
    return MemPalaceMineResult(
        command=command,
        palace_dir=palace_dir,
        staging_dir=staging_dir,
        stdout=stdout,
        stderr=stderr,
    )
