"""Search helpers for project corpus content."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .pipeline import iter_project_documents
from .project_registry import load_project_profiles
from .workspace import WorkspaceConfig, slugify

_VALID_SCOPES = {"promoted", "project", "imports"}


@dataclass(slots=True)
class CorpusHit:
    scope: str
    path: Path
    title: str
    line_number: int
    snippet: str
    occurrences: int

    def to_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "path": str(self.path),
            "title": self.title,
            "line_number": self.line_number,
            "snippet": self.snippet,
            "occurrences": self.occurrences,
        }


def _iter_scope_files(config: WorkspaceConfig, project: str, scopes: tuple[str, ...]) -> list[tuple[str, Path]]:
    base = config.corpus_project_dir(project)
    files: list[tuple[str, Path]] = []
    project_root = None
    for profile in load_project_profiles(config.projects_file):
        if profile.normalized_name() == project:
            project_root = profile.normalized_path()
            break
    for scope in scopes:
        if scope == "project":
            if project_root is None:
                continue
            files.extend((scope, path) for path in iter_project_documents(project_root))
            continue
        root = base / scope
        if root.exists():
            files.extend((scope, path) for path in sorted(root.rglob("*")) if path.is_file())
    return files


def _extract_title(path: Path, text: str) -> str:
    lines = text.splitlines()
    in_frontmatter = False
    for index, raw in enumerate(lines):
        line = raw.strip()
        if index == 0 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
                continue
            if line.startswith("room_title:"):
                _, _, value = line.partition(":")
                title = value.strip().strip('"').strip("'")
                if title:
                    return title
            continue
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title
    return path.stem


def _best_match(text: str, needle: str) -> tuple[int, str]:
    best_line_number = 0
    best_snippet = ""
    for index, raw in enumerate(text.splitlines(), start=1):
        line = " ".join(raw.split())
        if not line:
            continue
        if needle in line.casefold():
            best_line_number = index
            best_snippet = line[:240]
            break
    return best_line_number, best_snippet


def search_project_corpus(
    config: WorkspaceConfig,
    *,
    project: str | None,
    query: str,
    scopes: tuple[str, ...],
    limit: int = 10,
) -> list[CorpusHit]:
    project_slug = slugify(project or config.default_project)
    needle = query.strip().casefold()
    if not needle:
        return []
    invalid = sorted(set(scopes) - _VALID_SCOPES)
    if invalid:
        joined = ", ".join(invalid)
        raise ValueError(f"Unsupported corpus scope: {joined}")

    hits: list[CorpusHit] = []
    for scope, path in _iter_scope_files(config, project_slug, scopes):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lowered = text.casefold()
        occurrences = lowered.count(needle)
        if occurrences <= 0:
            continue
        line_number, snippet = _best_match(text, needle)
        hits.append(
            CorpusHit(
                scope=scope,
                path=path,
                title=_extract_title(path, text),
                line_number=line_number,
                snippet=snippet,
                occurrences=occurrences,
            )
        )

    hits.sort(key=lambda item: (-item.occurrences, str(item.path)))
    return hits[:limit]


def search_payload(
    config: WorkspaceConfig,
    *,
    project: str | None,
    query: str,
    scopes: tuple[str, ...],
    limit: int = 10,
) -> dict[str, object]:
    project_slug = slugify(project or config.default_project)
    hits = search_project_corpus(
        config,
        project=project_slug,
        query=query,
        scopes=scopes,
        limit=limit,
    )
    return {
        "project": project_slug,
        "query": query,
        "scopes": list(scopes),
        "hits": [hit.to_dict() for hit in hits],
    }
