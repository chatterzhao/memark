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


def run_mempalace_convo_mine(
    *,
    mempalace_bin: str,
    palace_dir: Path,
    staging_dir: Path,
) -> MemPalaceMineResult:
    binary = shutil.which(mempalace_bin)
    if binary is None:
        raise MemPalaceError(
            f"MemPalace CLI '{mempalace_bin}' not found in PATH. Install and verify mempalace before mining."
        )
    if not staging_dir.exists():
        raise MemPalaceError(f"Codex staging directory does not exist: {staging_dir}")

    command = [binary, "--palace", str(palace_dir), "mine", str(staging_dir), "--mode", "convos"]
    completed = subprocess.run(
        command,
        cwd=staging_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise MemPalaceError(
            f"MemPalace mine failed with exit code {completed.returncode}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return MemPalaceMineResult(
        command=command,
        palace_dir=palace_dir,
        staging_dir=staging_dir,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
