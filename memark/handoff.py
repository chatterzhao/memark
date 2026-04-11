"""Graphify handoff helpers for mixed-corpus skill execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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


@dataclass(frozen=True)
class CorpusInventory:
    scope: str
    files: int
    words: int

    def to_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "files": self.files,
            "words": self.words,
        }


@dataclass(frozen=True)
class GraphifyHandoff:
    project: str
    corpus_dir: Path
    inventories: tuple[CorpusInventory, ...]
    code_files: int
    recommended_command: str
    prompt: str

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "corpus_dir": str(self.corpus_dir),
            "inventories": [item.to_dict() for item in self.inventories],
            "code_files": self.code_files,
            "recommended_command": self.recommended_command,
            "prompt": self.prompt,
        }


def _count_words(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return len(text.split())


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _scope_inventory(scope: str, root: Path) -> CorpusInventory:
    files = _iter_files(root)
    return CorpusInventory(
        scope=scope,
        files=len(files),
        words=sum(_count_words(path) for path in files),
    )


def _count_code_files(root: Path) -> int:
    return sum(1 for path in _iter_files(root) if path.suffix.lower() in _CODE_SUFFIXES)


def _render_prompt(project: str, corpus_dir: Path, recommended_command: str, inventories: tuple[CorpusInventory, ...], code_files: int) -> str:
    lines = [
        f"Use the Graphify skill, not bare memark build, on the MemArk-prepared corpus at {corpus_dir}.",
        f"Project: {project}",
        f"Recommended command: {recommended_command}",
        "Corpus summary:",
    ]
    for item in inventories:
        lines.append(f"- {item.scope}: {item.files} files, ~{item.words} words")
    lines.append(f"- code files anywhere under corpus: {code_files}")
    lines.extend(
        [
            "Execution notes:",
            "- promoted/ contains session-derived project knowledge promoted out of MemPalace.",
            "- documents/ contains project documents copied into the corpus.",
            "- imports/ contains imported external material.",
            "- MemArk can prepare this corpus, but mixed-corpus semantic extraction still needs the upstream Graphify skill path.",
            "- Use --update because promoted markdown and documents are non-code inputs that Graphify watch mode does not semantically rebuild by itself.",
        ]
    )
    return "\n".join(lines)


def build_graphify_handoff(project: str, corpus_dir: Path) -> GraphifyHandoff:
    resolved = corpus_dir.resolve()
    inventories = (
        _scope_inventory("promoted", resolved / "promoted"),
        _scope_inventory("documents", resolved / "documents"),
        _scope_inventory("imports", resolved / "imports"),
    )
    code_files = _count_code_files(resolved)
    recommended_command = f"/graphify {resolved} --update"
    prompt = _render_prompt(project, resolved, recommended_command, inventories, code_files)
    return GraphifyHandoff(
        project=project,
        corpus_dir=resolved,
        inventories=inventories,
        code_files=code_files,
        recommended_command=recommended_command,
        prompt=prompt,
    )
