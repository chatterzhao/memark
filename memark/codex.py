"""Codex session discovery, project matching, and staging helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .io import copy_document, dump_json_file, load_json_file, sha256_text
from .workspace import WorkspaceConfig, slugify


@dataclass(slots=True)
class CodexSessionRecord:
    source_path: str
    staged_path: str
    staged_relative_path: str
    size: int
    mtime_ns: int
    sha256: str
    session_id: str | None
    cwd: str
    timestamp: str | None


@dataclass(slots=True)
class CodexSyncResult:
    project: str
    project_root: str
    sessions_root: str
    staging_dir: str
    scanned: int = 0
    matched: int = 0
    copied: int = 0
    updated: int = 0
    unchanged: int = 0
    invalid: int = 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _load_ledger(path: Path) -> dict[str, CodexSessionRecord]:
    if not path.exists():
        return {}
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        return {}
    ledger: dict[str, CodexSessionRecord] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        cwd = value.get("cwd")
        staged_path = value.get("staged_path")
        sha256 = value.get("sha256")
        if not isinstance(cwd, str) or not isinstance(staged_path, str) or not isinstance(sha256, str):
            continue
        ledger[key] = CodexSessionRecord(
            source_path=str(value.get("source_path", key)),
            staged_path=staged_path,
            staged_relative_path=(
                str(value.get("staged_relative_path"))
                if isinstance(value.get("staged_relative_path"), str)
                else Path(staged_path).name
            ),
            size=int(value.get("size", 0)),
            mtime_ns=int(value.get("mtime_ns", 0)),
            sha256=sha256,
            session_id=value.get("session_id") if isinstance(value.get("session_id"), str) else None,
            cwd=cwd,
            timestamp=value.get("timestamp") if isinstance(value.get("timestamp"), str) else None,
        )
    return ledger


def _save_ledger(path: Path, ledger: dict[str, CodexSessionRecord]) -> None:
    payload = {key: asdict(value) for key, value in sorted(ledger.items())}
    dump_json_file(path, payload)


def _parse_session_meta(path: Path) -> tuple[str, str | None, str | None]:
    with path.open("r", encoding="utf-8") as handle:
        first_line = handle.readline()
    if not first_line.strip():
        raise ValueError(f"{path} is empty")
    try:
        payload = json.loads(first_line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} does not start with valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} session_meta line must be an object")
    if payload.get("type") != "session_meta":
        raise ValueError(f"{path} first JSONL record is not session_meta")
    meta = payload.get("payload")
    if not isinstance(meta, dict):
        raise ValueError(f"{path} session_meta.payload must be an object")
    cwd = meta.get("cwd")
    if not isinstance(cwd, str) or not cwd.strip():
        raise ValueError(f"{path} session_meta.payload.cwd is missing")
    session_id = meta.get("id") if isinstance(meta.get("id"), str) and meta.get("id").strip() else None
    timestamp = meta.get("timestamp") if isinstance(meta.get("timestamp"), str) and meta.get("timestamp").strip() else None
    return str(Path(cwd).expanduser()), session_id, timestamp


def _matches_project(cwd: str, project_root: Path, cwd_prefixes: list[Path]) -> bool:
    cwd_path = Path(cwd).expanduser().resolve()
    candidates = [project_root, *cwd_prefixes]
    for candidate in candidates:
        try:
            if cwd_path == candidate or cwd_path.is_relative_to(candidate):
                return True
        except ValueError:
            continue
    return False


def _fingerprint_session(path: Path) -> tuple[int, int, str]:
    stat_result = path.stat()
    text = path.read_text(encoding="utf-8")
    return stat_result.st_size, stat_result.st_mtime_ns, sha256_text(text)


def _snapshot_relative_path(relative_path: Path, *, mtime_ns: int, digest: str) -> Path:
    suffix = relative_path.suffix
    stem = relative_path.name[: -len(suffix)] if suffix else relative_path.name
    snapshot_name = f"{stem}--{mtime_ns}-{digest[:12]}{suffix}"
    return relative_path.with_name(snapshot_name)


def sync_codex_sessions(
    config: WorkspaceConfig,
    *,
    project: str,
    project_root: Path,
    sessions_root: Path,
    cwd_prefixes: list[Path] | None = None,
    dry_run: bool = False,
) -> CodexSyncResult:
    normalized_project = slugify(project)
    normalized_project_root = project_root.expanduser().resolve()
    normalized_sessions_root = sessions_root.expanduser().resolve()
    prefixes = [path.expanduser().resolve() for path in (cwd_prefixes or [])]
    config.ensure_layout(normalized_project)
    staging_dir = config.codex_sessions_dir(normalized_project)
    ledger_path = config.codex_ledger_file(normalized_project)
    ledger = _load_ledger(ledger_path)
    next_ledger = dict(ledger)

    result = CodexSyncResult(
        project=normalized_project,
        project_root=str(normalized_project_root),
        sessions_root=str(normalized_sessions_root),
        staging_dir=str(staging_dir),
    )

    for source in sorted(path for path in normalized_sessions_root.rglob("*.jsonl") if path.is_file()):
        result.scanned += 1
        try:
            cwd, session_id, timestamp = _parse_session_meta(source)
        except ValueError:
            result.invalid += 1
            continue
        if not _matches_project(cwd, normalized_project_root, prefixes):
            continue

        result.matched += 1
        size, mtime_ns, digest = _fingerprint_session(source)
        relative_path = source.relative_to(normalized_sessions_root)
        staged_relative_path = _snapshot_relative_path(relative_path, mtime_ns=mtime_ns, digest=digest)
        destination = staging_dir / staged_relative_path
        source_key = str(source)
        existing = ledger.get(source_key)
        changed = (
            existing is None
            or existing.size != size
            or existing.mtime_ns != mtime_ns
            or existing.sha256 != digest
            or existing.cwd != cwd
        )
        if changed:
            if not dry_run:
                copy_document(source, destination)
            if existing is None:
                result.copied += 1
            else:
                result.updated += 1
        else:
            result.unchanged += 1

        next_ledger[source_key] = CodexSessionRecord(
            source_path=source_key,
            staged_path=str(destination),
            staged_relative_path=str(staged_relative_path),
            size=size,
            mtime_ns=mtime_ns,
            sha256=digest,
            session_id=session_id,
            cwd=cwd,
            timestamp=timestamp,
        )

    if not dry_run:
        _save_ledger(ledger_path, next_ledger)
    return result
