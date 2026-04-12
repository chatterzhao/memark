"""Memory tool dispatch helpers."""

from __future__ import annotations

from dataclasses import dataclass
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


def validate_mem_tool(mem_tool: str) -> str:
    normalized = mem_tool.strip().lower()
    if normalized not in SUPPORTED_MEM_TOOLS:
        raise MemToolError(f"Unsupported mem_tool '{mem_tool}'. Expected one of: {', '.join(SUPPORTED_MEM_TOOLS)}")
    return normalized


def build_mem_tool_mine_command(*, mem_tool: str, mem_tool_bin: str, palace_dir: Path, staging_dir: Path) -> list[str]:
    normalized = validate_mem_tool(mem_tool)
    if normalized == "mempalace":
        return [mem_tool_bin, "--palace", str(palace_dir), "mine", str(staging_dir), "--mode", "convos"]
    raise MemToolError(
        f"mem_tool '{normalized}' is configured for this workspace, but convo mine is not implemented yet. "
        "Use mem_tool=mempalace for now."
    )


def mem_tool_available(*, mem_tool_bin: str) -> bool:
    import shutil

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
    raise MemToolError(
        f"mem_tool '{normalized}' is configured for this workspace, but convo mine is not implemented yet. "
        "Use mem_tool=mempalace for now."
    )
