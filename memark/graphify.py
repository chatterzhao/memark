"""Graphify integration helpers."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class GraphifyError(RuntimeError):
    """Raised when Graphify is unavailable or its command fails."""


@dataclass(slots=True)
class GraphifyBuildResult:
    command: list[str]
    project_dir: Path
    stdout: str
    stderr: str


def _resolve_graphify_python(binary: Path) -> str:
    candidates = [
        binary.with_name("python"),
        binary.with_name("python3"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _run_graphify_watch_fallback(binary: Path, project_dir: Path) -> GraphifyBuildResult:
    python_bin = _resolve_graphify_python(binary)
    command = [
        python_bin,
        "-c",
        (
            "from pathlib import Path; "
            "from graphify.watch import _rebuild_code; "
            f"raise SystemExit(0 if _rebuild_code(Path({str(project_dir)!r})) else 1)"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=project_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise GraphifyError(
            "Graphify direct folder build was not available, and fallback to "
            "graphify.watch._rebuild_code failed. This fallback is code-only and "
            "depends on importing the installed graphify Python module from the "
            "Graphify environment.\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return GraphifyBuildResult(
        command=command,
        project_dir=project_dir,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_graphify(
    graphify_bin: str,
    project_dir: Path,
    update: bool = False,
    wiki: bool = False,
    obsidian: bool = False,
    mcp: bool = False,
) -> GraphifyBuildResult:
    binary = shutil.which(graphify_bin)
    if binary is None:
        raise GraphifyError(
            f"Graphify CLI '{graphify_bin}' not found in PATH. Install and verify graphify before build."
        )

    command = [binary, str(project_dir)]
    if update:
        command.append("--update")
    if wiki:
        command.append("--wiki")
    if obsidian:
        command.append("--obsidian")
    if mcp:
        command.append("--mcp")

    completed = subprocess.run(
        command,
        cwd=project_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        combined = "\n".join(part for part in [stdout, stderr] if part)
        if "unknown command" in combined.lower():
            return _run_graphify_watch_fallback(Path(binary), project_dir)
        raise GraphifyError(
            f"Graphify build failed with exit code {completed.returncode}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return GraphifyBuildResult(
        command=command,
        project_dir=project_dir,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
