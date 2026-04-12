"""Graphify integration helpers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


class GraphifyError(RuntimeError):
    """Raised when Graphify is unavailable or its command fails."""


@dataclass(slots=True)
class GraphifyBuildResult:
    command: list[str]
    project_dir: Path
    mode: str
    stdout: str
    stderr: str


_CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".m",
    ".mm",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
}
_TEXT_SUFFIXES = {
    ".adoc",
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".m",
    ".md",
    ".mdx",
    ".mm",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".rst",
    ".swift",
    ".ts",
    ".tsx",
    ".txt",
}
_IGNORE_PARTS = {
    ".claude",
    ".codex",
    ".git",
    ".graphify_python",
    ".mempalace",
    "__pycache__",
    "graphify-out",
}
_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "been",
    "being",
    "both",
    "build",
    "cannot",
    "could",
    "didnt",
    "does",
    "dont",
    "from",
    "graph",
    "have",
    "into",
    "itself",
    "just",
    "like",
    "make",
    "memark",
    "more",
    "must",
    "need",
    "only",
    "other",
    "project",
    "really",
    "should",
    "since",
    "still",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "todo",
    "very",
    "want",
    "were",
    "what",
    "when",
    "which",
    "with",
    "would",
}
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{3,}")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _is_candidate_file(path: Path, project_dir: Path) -> bool:
    relative = path.relative_to(project_dir)
    if any(part in _IGNORE_PARTS or part.startswith(".graphify") for part in relative.parts):
        return False
    if relative.parts and relative.parts[0] == "graphify-out":
        return False
    if path.name == "AGENTS.md":
        return False
    return path.is_file()


def _iter_corpus_files(project_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(project_dir.rglob("*"))
        if _is_candidate_file(path, project_dir)
    ]


def _scope_for(path: Path, project_dir: Path) -> str:
    relative = path.relative_to(project_dir)
    if relative.parts and relative.parts[0] in {"promoted", "documents", "imports"}:
        return relative.parts[0]
    if path.suffix.lower() in _CODE_SUFFIXES:
        return "code"
    return "other"


def _read_text(path: Path) -> str:
    if path.suffix.lower() not in _TEXT_SUFFIXES:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _file_title(path: Path, text: str) -> str:
    for match in _HEADING_RE.finditer(text):
        title = match.group(2).strip()
        if title:
            return title
    stem = path.stem.replace("-", " ").replace("_", " ").strip()
    return stem or path.name


def _file_keywords(text: str, *, limit: int = 8) -> list[str]:
    counts: Counter[str] = Counter()
    for raw in _WORD_RE.findall(text.casefold()):
        word = raw.strip("_-")
        if len(word) < 4 or word in _STOPWORDS:
            continue
        counts[word] += 1
    return [word for word, _ in counts.most_common(limit)]


def _file_summary(scope: str, title: str, relative_path: str, keywords: list[str]) -> str:
    parts = [f"{scope} file", title, relative_path]
    if keywords:
        parts.append("keywords=" + ", ".join(keywords[:4]))
    return " | ".join(parts)


def _resolve_markdown_target(source: Path, target: str, project_dir: Path) -> Path | None:
    cleaned = target.strip()
    if not cleaned or "://" in cleaned or cleaned.startswith("#"):
        return None
    cleaned = cleaned.split("#", 1)[0].split("?", 1)[0].strip()
    if not cleaned:
        return None
    candidate = (source.parent / cleaned).resolve()
    try:
        candidate.relative_to(project_dir.resolve())
    except ValueError:
        return None
    return candidate if candidate.exists() else None


def _render_autonomous_report(
    *,
    project_dir: Path,
    total_nodes: int,
    total_edges: int,
    scope_counts: dict[str, int],
    concept_count: int,
    top_files: list[tuple[str, int]],
) -> str:
    lines = [
        f"# Graph Report - {project_dir.name}",
        "",
        "## Build",
        "",
        "- builder: memark autonomous mixed-corpus",
        f"- corpus_dir: {project_dir.resolve()}",
        f"- nodes: {total_nodes}",
        f"- edges: {total_edges}",
        "",
        "## Scope Coverage",
        "",
    ]
    for scope in ("promoted", "documents", "imports", "code", "other"):
        lines.append(f"- {scope}: {scope_counts.get(scope, 0)} files")
    lines.extend(
        [
            f"- concept nodes: {concept_count}",
            "",
            "## Top Linked Files",
            "",
        ]
    )
    if top_files:
        for index, (path, degree) in enumerate(top_files, start=1):
            lines.append(f"{index}. `{path}` - {degree} links")
    else:
        lines.append("- no cross-file links detected")
    return "\n".join(lines).rstrip() + "\n"


def _run_memark_mixed_corpus_build(project_dir: Path, *, reason: str) -> GraphifyBuildResult:
    project_dir = project_dir.resolve()
    files = _iter_corpus_files(project_dir)
    graphify_out = project_dir / "graphify-out"
    graphify_out.mkdir(parents=True, exist_ok=True)

    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    file_nodes: dict[Path, str] = {}
    file_keywords: dict[Path, set[str]] = {}
    scope_counts: Counter[str] = Counter()
    concept_sources: dict[str, list[Path]] = defaultdict(list)

    for path in files:
        relative = path.relative_to(project_dir).as_posix()
        scope = _scope_for(path, project_dir)
        scope_counts[scope] += 1
        text = _read_text(path)
        keywords = _file_keywords(text) if text else []
        title = _file_title(path, text) if text else path.name
        file_id = f"file:{relative}"
        file_nodes[path.resolve()] = file_id
        file_keywords[path.resolve()] = set(keywords)
        for keyword in keywords:
            concept_sources[keyword].append(path.resolve())

        nodes.append(
            {
                "id": file_id,
                "label": title,
                "kind": "file",
                "scope": scope,
                "file_type": path.suffix.lower().lstrip(".") or "file",
                "source_file": str(path.resolve()),
                "relative_path": relative,
                "words": len(text.split()) if text else 0,
                "summary": _file_summary(scope, title, relative, keywords),
            }
        )

        headings: list[str] = []
        if text:
            for index, match in enumerate(_HEADING_RE.finditer(text), start=1):
                heading = match.group(2).strip()
                if not heading:
                    continue
                heading_id = f"{file_id}#heading:{index}"
                headings.append(heading_id)
                nodes.append(
                    {
                        "id": heading_id,
                        "label": heading,
                        "kind": "heading",
                        "scope": scope,
                        "source_file": str(path.resolve()),
                        "relative_path": relative,
                    }
                )
                edges.append(
                    {
                        "source": file_id,
                        "target": heading_id,
                        "relation": "contains",
                        "confidence": "EXTRACTED",
                    }
                )
                if len(headings) >= 12:
                    break
        if text and path.suffix.lower() in {".md", ".mdx", ".rst", ".txt", ".adoc"}:
            for raw_target in _MD_LINK_RE.findall(text):
                target = _resolve_markdown_target(path, raw_target, project_dir)
                if target is None:
                    continue
                target_id = f"file:{target.relative_to(project_dir).as_posix()}"
                edge_key = (file_id, target_id, "references")
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                edges.append(
                    {
                        "source": file_id,
                        "target": target_id,
                        "relation": "references",
                        "confidence": "EXTRACTED",
                    }
                )

    concept_count = 0
    for keyword, paths in sorted(concept_sources.items()):
        unique_paths = sorted(set(paths))
        if len(unique_paths) < 2:
            continue
        concept_id = f"concept:{keyword}"
        concept_count += 1
        nodes.append(
            {
                "id": concept_id,
                "label": keyword,
                "kind": "concept",
                "scope": "mixed",
                "source_file": "",
            }
        )
        for path in unique_paths[:10]:
            file_id = file_nodes[path]
            edge_key = (file_id, concept_id, "mentions")
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "source": file_id,
                    "target": concept_id,
                    "relation": "mentions",
                    "confidence": "INFERRED",
                    "confidence_score": 0.65,
                }
            )

    resolved_paths = sorted(file_nodes)
    for index, left in enumerate(resolved_paths):
        for right in resolved_paths[index + 1 :]:
            left_scope = _scope_for(left, project_dir)
            right_scope = _scope_for(right, project_dir)
            if left_scope == "other" and right_scope == "other":
                continue
            overlap = sorted(file_keywords[left] & file_keywords[right])
            if len(overlap) < 2:
                continue
            left_id = file_nodes[left]
            right_id = file_nodes[right]
            edge_key = (left_id, right_id, "shares_terms_with")
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "source": left_id,
                    "target": right_id,
                    "relation": "shares_terms_with",
                    "confidence": "INFERRED",
                    "confidence_score": min(0.95, 0.55 + 0.1 * min(len(overlap), 4)),
                    "shared_terms": overlap[:6],
                }
            )

    degree: Counter[str] = Counter()
    for edge in edges:
        degree[str(edge["source"])] += 1
        degree[str(edge["target"])] += 1

    top_files = []
    for path, file_id in file_nodes.items():
        top_files.append((path.relative_to(project_dir).as_posix(), degree[file_id]))
    top_files.sort(key=lambda item: (-item[1], item[0]))

    payload = {
        "builder": "memark",
        "mode": "mixed-corpus-autonomous",
        "reason": reason,
        "root": str(project_dir.resolve()),
        "nodes": nodes,
        "edges": edges,
        "links": edges,
        "summary": {
            "files": len(file_nodes),
            "concept_nodes": concept_count,
            "nodes": len(nodes),
            "edges": len(edges),
            "scopes": dict(scope_counts),
        },
    }
    (graphify_out / "graph.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (graphify_out / "manifest.json").write_text(
        json.dumps(
            {
                "builder": "memark",
                "mode": "mixed-corpus-autonomous",
                "root": str(project_dir.resolve()),
                "files": len(file_nodes),
                "nodes": len(nodes),
                "edges": len(edges),
                "reason": reason,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (graphify_out / "GRAPH_REPORT.md").write_text(
        _render_autonomous_report(
            project_dir=project_dir,
            total_nodes=len(nodes),
            total_edges=len(edges),
            scope_counts=dict(scope_counts),
            concept_count=concept_count,
            top_files=top_files[:10],
        ),
        encoding="utf-8",
    )

    return GraphifyBuildResult(
        command=["memark-autonomous-graph", str(project_dir)],
        project_dir=project_dir,
        mode="memark-mixed-corpus",
        stdout=(
            f"[memark] Built mixed-corpus graph with {len(nodes)} nodes and {len(edges)} edges "
            f"across {len(file_nodes)} files.\n"
            f"[memark] Output: {graphify_out / 'graph.json'}"
        ),
        stderr="",
    )


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
        detail = (
            "Graphify direct folder build was not available, and fallback to "
            "graphify.watch._rebuild_code failed. This fallback is code-only and "
            "depends on importing the installed graphify Python module from the "
            "Graphify environment."
        )
        if "No code files found - nothing to rebuild." in completed.stdout:
            detail += (
                " The target corpus currently has no code files, so this path cannot "
                "compile promoted markdown or other documents into the graph. Use the "
                "upstream Graphify skill or platform flow that runs `/graphify <folder> "
                "--update` for mixed-corpus semantic extraction."
            )
        raise GraphifyError(
            detail
            + "\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return GraphifyBuildResult(
        command=command,
        project_dir=project_dir,
        mode="watch-fallback",
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
    project_dir = project_dir.resolve()
    binary = shutil.which(graphify_bin)
    if binary is None:
        return _run_memark_mixed_corpus_build(
            project_dir,
            reason=f"Graphify CLI '{graphify_bin}' was not found in PATH.",
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
            return _run_memark_mixed_corpus_build(
                project_dir,
                reason="Graphify CLI does not support direct folder build in this environment.",
            )
        raise GraphifyError(
            f"Graphify build failed with exit code {completed.returncode}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return GraphifyBuildResult(
        command=command,
        project_dir=project_dir,
        mode="cli",
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
