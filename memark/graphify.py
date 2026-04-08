"""Graphify integration helpers."""

from __future__ import annotations

import shutil
import subprocess
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
        hint = ""
        combined = "\n".join(part for part in [stdout, stderr] if part)
        if "unknown command" in combined.lower():
            hint = (
                "\nDetected a Graphify CLI that does not accept direct 'graphify <folder>' builds. "
                "The installed package may expose only helper/query commands at the top level. "
                "Use a compatible wrapper via --graphify-bin or install a Graphify interface "
                "that supports corpus builds."
            )
        raise GraphifyError(
            f"Graphify build failed with exit code {completed.returncode}{hint}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return GraphifyBuildResult(
        command=command,
        project_dir=project_dir,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
