"""Persistent mixed-corpus Graphify proof helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .handoff import build_graphify_handoff
from .io import dump_json_file, load_json_file
from .workspace import WorkspaceConfig, slugify


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _graphify_proof_path(config: WorkspaceConfig, project: str) -> Path:
    return config.state_dir / f"{slugify(project)}-graphify-proof.json"


@dataclass(slots=True)
class GraphifyProof:
    project: str
    status: str
    recorded_at: str
    corpus_dir: str
    recommended_command: str
    command: str | None
    evidence_paths: list[str]
    notes: str | None
    inventories: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "status": self.status,
            "recorded_at": self.recorded_at,
            "corpus_dir": self.corpus_dir,
            "recommended_command": self.recommended_command,
            "command": self.command,
            "evidence_paths": list(self.evidence_paths),
            "notes": self.notes,
            "inventories": list(self.inventories),
        }


def _graphify_out_dir(config: WorkspaceConfig, project: str) -> Path:
    return config.corpus_project_dir(project) / "graphify-out"


def _graph_node_counts(graph_path: Path, corpus_dir: Path) -> tuple[int, int] | None:
    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return None
    scope_markers = (
        str((corpus_dir / "promoted").resolve()) + "/",
        str((corpus_dir / "documents").resolve()) + "/",
        str((corpus_dir / "imports").resolve()) + "/",
    )
    mixed_corpus_nodes = 0
    for item in nodes:
        if not isinstance(item, dict):
            continue
        source_file = item.get("source_file")
        if not isinstance(source_file, str):
            continue
        normalized = source_file.replace("\\", "/")
        if any(marker.replace("\\", "/") in normalized for marker in scope_markers):
            mixed_corpus_nodes += 1
    return (len(nodes), mixed_corpus_nodes)


def graphify_proof_diagnostics(config: WorkspaceConfig, project: str) -> dict[str, object]:
    project_slug = slugify(project)
    corpus_dir = config.corpus_project_dir(project_slug).resolve()
    graphify_out = _graphify_out_dir(config, project_slug)
    graph_path = graphify_out / "graph.json"
    report_path = graphify_out / "GRAPH_REPORT.md"
    diagnostics: dict[str, object] = {
        "graph_path": str(graph_path.resolve()),
        "report_path": str(report_path.resolve()),
        "status": "graph_missing",
        "total_nodes": 0,
        "mixed_corpus_nodes": 0,
    }
    workspace_graph_path = (config.workspace / "graphify-out" / "graph.json").resolve()
    if workspace_graph_path != graph_path.resolve():
        workspace_counts = _graph_node_counts(workspace_graph_path, corpus_dir) if workspace_graph_path.exists() else None
        diagnostics["workspace_graph_path"] = str(workspace_graph_path)
        diagnostics["workspace_graph_status"] = (
            "graph_missing"
            if workspace_counts is None and not workspace_graph_path.exists()
            else "graph_unreadable"
            if workspace_counts is None
            else "mixed_corpus_detected"
            if workspace_counts[1] > 0
            else "code_only_graph"
        )
        diagnostics["workspace_total_nodes"] = 0 if workspace_counts is None else workspace_counts[0]
        diagnostics["workspace_mixed_corpus_nodes"] = 0 if workspace_counts is None else workspace_counts[1]
    if not graph_path.exists():
        return diagnostics
    counts = _graph_node_counts(graph_path, corpus_dir)
    if counts is None:
        diagnostics["status"] = "graph_unreadable"
        return diagnostics
    total_nodes, mixed_corpus_nodes = counts
    diagnostics["total_nodes"] = total_nodes
    diagnostics["mixed_corpus_nodes"] = mixed_corpus_nodes
    diagnostics["status"] = "mixed_corpus_detected" if mixed_corpus_nodes > 0 else "code_only_graph"
    return diagnostics


def graphify_onboarding_status(config: WorkspaceConfig, project: str) -> dict[str, object]:
    project_slug = slugify(project)
    corpus_dir = config.corpus_project_dir(project_slug).resolve()
    agents_path = corpus_dir / "AGENTS.md"
    codex_hooks_path = corpus_dir / ".codex" / "hooks.json"
    installed_files = []
    if agents_path.exists():
        installed_files.append(str(agents_path))
    if codex_hooks_path.exists():
        installed_files.append(str(codex_hooks_path))
    if agents_path.exists() and codex_hooks_path.exists():
        status = "onboarded"
    elif agents_path.exists() or codex_hooks_path.exists():
        status = "partial"
    else:
        status = "missing"
    return {
        "status": status,
        "corpus_dir": str(corpus_dir),
        "agents_path": str(agents_path),
        "agents_installed": agents_path.exists(),
        "codex_hooks_path": str(codex_hooks_path),
        "codex_hooks_installed": codex_hooks_path.exists(),
        "installed_files": installed_files,
        "recommended_command": f"/graphify {corpus_dir} --update",
    }


def graphify_corpus_status(config: WorkspaceConfig, project: str) -> dict[str, object]:
    onboarding = graphify_onboarding_status(config, project)
    diagnostics = graphify_proof_diagnostics(config, project)
    proof = load_graphify_proof(config, project)

    status = "graph_missing"
    if isinstance(proof, dict) and proof.get("status") == "ingested":
        status = "ingested"
    elif diagnostics.get("status") == "graph_missing":
        if onboarding["status"] == "onboarded":
            status = "onboarded_graph_missing"
        elif onboarding["status"] == "partial":
            status = "partial_onboarding"
        else:
            status = "graph_missing"
    elif diagnostics.get("status") == "code_only_graph":
        status = "onboarded_code_only_graph" if onboarding["status"] == "onboarded" else "code_only_graph"
    elif diagnostics.get("status") == "graph_unreadable":
        status = "onboarded_graph_unreadable" if onboarding["status"] == "onboarded" else "graph_unreadable"
    else:
        status = "onboarded_pending_verification" if onboarding["status"] == "onboarded" else "pending_verification"

    return {
        "status": status,
        "onboarding": onboarding,
        "proof": proof,
        "diagnostics": diagnostics,
    }


def detect_graphify_proof(config: WorkspaceConfig, project: str) -> dict[str, object] | None:
    project_slug = slugify(project)
    corpus_dir = config.corpus_project_dir(project_slug).resolve()
    graphify_out = _graphify_out_dir(config, project_slug)
    graph_path = graphify_out / "graph.json"
    report_path = graphify_out / "GRAPH_REPORT.md"
    if not graph_path.exists():
        return None
    counts = _graph_node_counts(graph_path, corpus_dir)
    if counts is None:
        return None
    _, mixed_corpus_nodes = counts
    if mixed_corpus_nodes <= 0:
        return None
    handoff = build_graphify_handoff(project_slug, corpus_dir)
    evidence_paths = [str(graph_path.resolve())]
    if report_path.exists():
        evidence_paths.append(str(report_path.resolve()))
    return GraphifyProof(
        project=project_slug,
        status="ingested",
        recorded_at=datetime.fromtimestamp(graph_path.stat().st_mtime, tz=timezone.utc).isoformat(),
        corpus_dir=str(handoff.corpus_dir),
        recommended_command=handoff.recommended_command,
        command=None,
        evidence_paths=evidence_paths,
        notes="auto-detected from graphify-out/graph.json nodes sourced from promoted/documents/imports",
        inventories=[item.to_dict() for item in handoff.inventories],
    ).to_dict()


def load_graphify_proof(config: WorkspaceConfig, project: str) -> dict[str, object] | None:
    path = _graphify_proof_path(config, project)
    if not path.exists():
        return detect_graphify_proof(config, project)
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        return detect_graphify_proof(config, project)
    return payload


def record_graphify_proof(
    config: WorkspaceConfig,
    *,
    project: str,
    command: str | None,
    evidence_paths: list[str],
    notes: str | None,
) -> dict[str, object]:
    project_slug = slugify(project)
    handoff = build_graphify_handoff(project_slug, config.corpus_project_dir(project_slug))
    resolved_evidence = [str(Path(item).expanduser().resolve()) for item in evidence_paths]
    payload = GraphifyProof(
        project=project_slug,
        status="ingested",
        recorded_at=_now_utc_iso(),
        corpus_dir=str(handoff.corpus_dir),
        recommended_command=handoff.recommended_command,
        command=command.strip() if isinstance(command, str) and command.strip() else None,
        evidence_paths=resolved_evidence,
        notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
        inventories=[item.to_dict() for item in handoff.inventories],
    )
    dump_json_file(_graphify_proof_path(config, project_slug), payload.to_dict())
    return payload.to_dict()
