"""User-level MemArk installation and skill-bundle helpers."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    from importlib.resources import as_file, files
except ImportError:  # pragma: no cover
    from importlib_resources import as_file, files  # type: ignore


class InstallError(RuntimeError):
    """Raised when MemArk installation fails."""


MIN_RUNTIME_PYTHON = (3, 10)
MAX_RUNTIME_PYTHON = (3, 13)


@dataclass(frozen=True)
class InstallTarget:
    platform: str
    skill_root: Path
    bundle_dir: Path


@dataclass(frozen=True)
class InstallResult:
    memark_home: Path
    venv_dir: Path
    python_bin: Path
    memark_bin: Path
    mempalace_bin: Path
    mempal_bin: str
    graphify_bin: Path
    source_spec: str
    targets: list[InstallTarget]
    manifest_files: list[Path]
    symlinked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "memark_home": str(self.memark_home),
            "venv_dir": str(self.venv_dir),
            "python_bin": str(self.python_bin),
            "memark_bin": str(self.memark_bin),
            "mempalace_bin": str(self.mempalace_bin),
            "mempal_bin": self.mempal_bin,
            "graphify_bin": str(self.graphify_bin),
            "source_spec": self.source_spec,
            "targets": [
                {
                    "platform": target.platform,
                    "skill_root": str(target.skill_root),
                    "bundle_dir": str(target.bundle_dir),
                }
                for target in self.targets
            ],
            "manifest_files": [str(path) for path in self.manifest_files],
            "symlinked": list(self.symlinked),
        }


@dataclass(frozen=True)
class DoctorResult:
    memark_home: Path
    venv_dir: Path
    python_bin: Path
    memark_bin: Path
    mempalace_bin: Path
    mempal_bin: str
    graphify_bin: Path
    targets: list[InstallTarget]
    issues: list[str]
    warnings: list[str]

    def ok(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok(),
            "memark_home": str(self.memark_home),
            "venv_dir": str(self.venv_dir),
            "python_bin": str(self.python_bin),
            "memark_bin": str(self.memark_bin),
            "mempalace_bin": str(self.mempalace_bin),
            "mempal_bin": self.mempal_bin,
            "graphify_bin": str(self.graphify_bin),
            "targets": [
                {
                    "platform": target.platform,
                    "skill_root": str(target.skill_root),
                    "bundle_dir": str(target.bundle_dir),
                }
                for target in self.targets
            ],
            "issues": list(self.issues),
            "warnings": list(self.warnings),
        }


def default_memark_home() -> Path:
    override = os.environ.get("MEMARK_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path("~/.memark").expanduser().resolve()


def default_python_command() -> str:
    explicit = os.environ.get("MEMARK_PYTHON")
    if explicit:
        return _resolve_python_command(explicit)

    candidates: list[str] = []
    if os.name == "nt":
        candidates.extend(["python3.12", "python3.11", "python3.10", "python3.13", "python", "py"])
    else:
        # Prefer the most broadly compatible supported Python first.
        candidates.extend(["python3.12", "python3.11", "python3.10", "python3.13"])
        if sys.executable:
            candidates.append(sys.executable)
        candidates.extend(["python3", "python"])
    return _resolve_python_command(*candidates)


def _python_version(command: str) -> tuple[int, int] | None:
    argv = shlex.split(command)
    if not argv:
        return None
    try:
        completed = subprocess.run(
            [*argv, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    if "." not in text:
        return None
    major, minor = text.split(".", 1)
    if not major.isdigit() or not minor.isdigit():
        return None
    return int(major), int(minor)


def _python_version_supported(version: tuple[int, int]) -> bool:
    return MIN_RUNTIME_PYTHON <= version <= MAX_RUNTIME_PYTHON


def _resolve_python_command(*candidates: str) -> str:
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        version = _python_version(normalized)
        if version and _python_version_supported(version):
            return normalized
    tried = ", ".join(seen) if seen else "<none>"
    raise InstallError(
        "No compatible Python interpreter found for MemArk runtime. "
        f"Need Python {MIN_RUNTIME_PYTHON[0]}.{MIN_RUNTIME_PYTHON[1]}-"
        f"{MAX_RUNTIME_PYTHON[0]}.{MAX_RUNTIME_PYTHON[1]}. Tried: {tried}"
    )


def bundle_template_dir() -> Path:
    resource = files("memark").joinpath("skill_bundle")
    with as_file(resource) as resolved:
        return resolved


def detect_source_spec() -> str:
    package_root = Path(__file__).resolve().parents[1]
    if (package_root / "pyproject.toml").exists():
        return str(package_root)
    return "memark"


def resolve_platforms(platform: str) -> list[str]:
    normalized = platform.strip().lower()
    if normalized in {"codex", "claude"}:
        return [normalized]
    if normalized == "all":
        return ["codex", "claude"]
    if normalized != "auto":
        raise InstallError(f"Unsupported platform '{platform}'. Use auto, codex, claude, or all.")

    codex_root = skill_root_for("codex")
    claude_root = skill_root_for("claude")
    if codex_root.parent.exists() or Path("~/.codex").expanduser().exists():
        return ["codex"]
    if claude_root.parent.exists():
        return ["claude"]
    return ["codex"]


def skill_root_for(platform: str) -> Path:
    normalized = platform.strip().lower()
    if normalized == "codex":
        return Path("~/.agents/skills").expanduser().resolve()
    if normalized == "claude":
        return Path("~/.claude/skills").expanduser().resolve()
    raise InstallError(f"Unsupported platform '{platform}'")


def bundle_targets(platform: str, bundle_name: str = "memark") -> list[InstallTarget]:
    return [
        InstallTarget(
            platform=item,
            skill_root=skill_root_for(item),
            bundle_dir=skill_root_for(item) / bundle_name,
        )
        for item in resolve_platforms(platform)
    ]


def _venv_paths(memark_home: Path) -> tuple[Path, Path, Path, Path, Path]:
    venv_dir = memark_home / "venv"
    scripts_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    python_bin = scripts_dir / ("python.exe" if os.name == "nt" else "python")
    memark_bin = scripts_dir / ("memark.exe" if os.name == "nt" else "memark")
    mempalace_bin = scripts_dir / ("mempalace.exe" if os.name == "nt" else "mempalace")
    graphify_bin = scripts_dir / ("graphify.exe" if os.name == "nt" else "graphify")
    return venv_dir, python_bin, memark_bin, mempalace_bin, graphify_bin


def resolve_mempal_bin() -> str:
    return shutil.which("mempal") or "mempal"


def _run_command(command: list[str], *, cwd: Path | None = None) -> None:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode == 0:
        return
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    detail = stderr or stdout or "command failed"
    raise InstallError(f"{' '.join(command)}: {detail}")


def create_runtime_environment(
    *,
    memark_home: Path,
    python_command: str,
    source_spec: str,
    upgrade: bool = True,
) -> tuple[Path, Path, Path, Path, Path]:
    memark_home.mkdir(parents=True, exist_ok=True)
    venv_dir, python_bin, memark_bin, mempalace_bin, graphify_bin = _venv_paths(memark_home)
    if venv_dir.exists():
        shutil.rmtree(venv_dir)
    python_argv = shlex.split(python_command)
    if not python_argv:
        raise InstallError("Python command is empty.")
    _run_command([*python_argv, "-m", "venv", str(venv_dir)])
    _run_command([str(python_bin), "-m", "pip", "install", "--upgrade", "pip"])
    install_command = [str(python_bin), "-m", "pip", "install"]
    if upgrade:
        install_command.append("--upgrade")
    install_command.extend([source_spec, "mempalace", "graphifyy"])
    _run_command(install_command)
    return venv_dir, python_bin, memark_bin, mempalace_bin, graphify_bin


def _render_text(text: str, *, memark_home: Path, memark_bin: Path, python_bin: Path) -> str:
    return (
        text.replace("__MEMARK_HOME__", str(memark_home))
        .replace("__MEMARK_BIN__", str(memark_bin))
        .replace("__PYTHON_BIN__", str(python_bin))
    )


def install_skill_bundle(
    *,
    memark_home: Path,
    memark_bin: Path,
    python_bin: Path,
    platform: str,
) -> tuple[list[InstallTarget], list[Path]]:
    source_root = bundle_template_dir()
    targets = bundle_targets(platform)
    manifest_files: list[Path] = []
    for target in targets:
        target.skill_root.mkdir(parents=True, exist_ok=True)
        if target.bundle_dir.exists():
            shutil.rmtree(target.bundle_dir)
        shutil.copytree(source_root, target.bundle_dir)
        for file_path in target.bundle_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in {".md", ".sh", ".cmd", ".json"} and file_path.name != "memark":
                continue
            text = file_path.read_text(encoding="utf-8")
            file_path.write_text(
                _render_text(text, memark_home=memark_home, memark_bin=memark_bin, python_bin=python_bin),
                encoding="utf-8",
            )
            if file_path.suffix.lower() == ".sh" or file_path.name == "memark":
                file_path.chmod(file_path.stat().st_mode | 0o111)
        manifest_path = target.bundle_dir / "manifest.json"
        manifest_payload = {
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "platform": target.platform,
            "memark_home": str(memark_home),
            "memark_bin": str(memark_bin),
            "python_bin": str(python_bin),
        }
        manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=True), encoding="utf-8")
        manifest_files.append(manifest_path)
    return targets, manifest_files


def _ensure_user_local_bin() -> Path:
    """Return ~/.local/bin, creating it if needed."""
    local_bin = Path("~/.local/bin").expanduser().resolve()
    local_bin.mkdir(parents=True, exist_ok=True)
    return local_bin


def _symlink_to_user_local_bin(venv_bin: Path, local_bin: Path) -> list[str]:
    """Symlink memark, mempalace, graphify from venv into ~/.local/bin/.

    Returns list of symlinked command names.
    """
    commands = ["memark", "mempalace", "graphify"]
    symlinked: list[str] = []
    for name in commands:
        source = venv_bin / name
        target = local_bin / name
        if not source.exists():
            continue
        # Remove stale symlink or file
        if target.is_symlink() or target.exists():
            target.unlink()
        target.symlink_to(source)
        symlinked.append(name)
    return symlinked


def install_memark(
    *,
    platform: str,
    memark_home: Path | None = None,
    python_command: str | None = None,
    source_spec: str | None = None,
    skip_runtime_install: bool = False,
) -> InstallResult:
    resolved_home = (memark_home or default_memark_home()).expanduser().resolve()
    resolved_python = _resolve_python_command(python_command) if python_command else default_python_command()
    resolved_source = source_spec or detect_source_spec()
    venv_dir, python_bin, memark_bin, mempalace_bin, graphify_bin = _venv_paths(resolved_home)

    if not skip_runtime_install:
        venv_dir, python_bin, memark_bin, mempalace_bin, graphify_bin = create_runtime_environment(
            memark_home=resolved_home,
            python_command=resolved_python,
            source_spec=resolved_source,
        )
    else:
        resolved_home.mkdir(parents=True, exist_ok=True)

    targets, manifest_files = install_skill_bundle(
        memark_home=resolved_home,
        memark_bin=memark_bin,
        python_bin=python_bin,
        platform=platform,
    )

    # Symlink commands into ~/.local/bin so they are on PATH
    local_bin = _ensure_user_local_bin()
    venv_bin = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    symlinked = _symlink_to_user_local_bin(venv_bin, local_bin)

    return InstallResult(
        memark_home=resolved_home,
        venv_dir=venv_dir,
        python_bin=python_bin,
        memark_bin=memark_bin,
        mempalace_bin=mempalace_bin,
        mempal_bin=resolve_mempal_bin(),
        graphify_bin=graphify_bin,
        source_spec=resolved_source,
        targets=targets,
        manifest_files=manifest_files,
        symlinked=symlinked,
    )


def run_doctor(*, platform: str, memark_home: Path | None = None) -> DoctorResult:
    resolved_home = (memark_home or default_memark_home()).expanduser().resolve()
    venv_dir, python_bin, memark_bin, mempalace_bin, graphify_bin = _venv_paths(resolved_home)
    targets = bundle_targets(platform)
    issues: list[str] = []
    warnings: list[str] = []

    if not venv_dir.exists():
        issues.append(f"missing runtime environment: {venv_dir}")
    if not python_bin.exists():
        issues.append(f"missing python executable: {python_bin}")
    else:
        version = _python_version(str(python_bin))
        if version is None:
            issues.append(f"unable to determine runtime python version: {python_bin}")
        elif not _python_version_supported(version):
            issues.append(
                "unsupported runtime python version: "
                f"{version[0]}.{version[1]} (need "
                f"{MIN_RUNTIME_PYTHON[0]}.{MIN_RUNTIME_PYTHON[1]}-"
                f"{MAX_RUNTIME_PYTHON[0]}.{MAX_RUNTIME_PYTHON[1]})"
            )
    if not memark_bin.exists():
        issues.append(f"missing memark executable: {memark_bin}")
    if not mempalace_bin.exists():
        issues.append(f"missing mempalace executable: {mempalace_bin}")
    mempal_bin = resolve_mempal_bin()
    if shutil.which(mempal_bin) is None:
        warnings.append(
            "missing mempal executable in PATH. This does not block the default mempalace flow. "
            "Install it separately with 'cargo install mempal' only if you want to use mem_tool=mempal. "
            "MemArk will then generate a workspace-local .mempal/config.toml starter file on first mine."
        )
    if not graphify_bin.exists():
        issues.append(f"missing graphify executable: {graphify_bin}")

    for target in targets:
        if not target.bundle_dir.exists():
            issues.append(f"missing skill bundle: {target.bundle_dir}")
            continue
        manifest_path = target.bundle_dir / "manifest.json"
        if not manifest_path.exists():
            issues.append(f"missing manifest: {manifest_path}")
        skill_entry = target.bundle_dir / "SKILL.md"
        if not skill_entry.exists():
            issues.append(f"missing runtime skill: {skill_entry}")
        launcher_sh = target.bundle_dir / "bin" / "memark"
        launcher_cmd = target.bundle_dir / "bin" / "memark.cmd"
        if not launcher_sh.exists() and not launcher_cmd.exists():
            issues.append(f"missing launcher script in bundle: {target.bundle_dir / 'bin'}")

    return DoctorResult(
        memark_home=resolved_home,
        venv_dir=venv_dir,
        python_bin=python_bin,
        memark_bin=memark_bin,
        mempalace_bin=mempalace_bin,
        mempal_bin=mempal_bin,
        graphify_bin=graphify_bin,
        targets=targets,
        issues=issues,
        warnings=warnings,
    )
