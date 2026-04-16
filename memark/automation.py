"""Automated MemArk feed/process/consume cycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .graphify import GraphifyError, GraphifyBuildResult, run_graphify
from .graphify_proof import graphify_corpus_status
from .handoff import GraphifyHandoff, build_graphify_handoff
from .io import dump_json_file, load_json_file
from .pipeline import (
    FeedPhaseResult,
    ProcessPhaseResult,
    build_palace_packages,
    run_feed_phase,
    iter_project_documents,
    scan_project_documents,
)
from .project_registry import (
    ProjectCycleResult,
    load_project_profiles,
)
from .workspace import WorkspaceConfig, slugify
_DECISION_MARKERS = ("decision", "decide", "adr", "chosen", "adopt")
_RISK_MARKERS = ("risk", "blocker", "issue", "failed", "failure", "todo", "follow-up", "followup")


@dataclass(slots=True)
class GraphifyAutomationResult:
    status: str
    attempted: bool
    mode: str | None
    command: list[str] | None
    error: str | None
    recommended_command: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "attempted": self.attempted,
            "mode": self.mode,
            "command": list(self.command) if self.command is not None else None,
            "error": self.error,
            "recommended_command": self.recommended_command,
        }


@dataclass(slots=True)
class AutomationProjectResult:
    project: str
    feed: FeedPhaseResult
    process: ProcessPhaseResult
    consume: "ConsumePhaseResult"

    @property
    def intake(self) -> ProjectCycleResult | None:
        return self.feed.intake

    @property
    def project_documents(self) -> dict[str, object]:
        return self.process.project

    @property
    def palace_drawers(self) -> int:
        return self.process.palace_drawers

    @property
    def packages(self) -> int:
        return self.process.packages

    @property
    def promoted(self):
        return self.process.promoted

    @property
    def artifacts(self) -> list[str]:
        return self.consume.artifacts

    @property
    def graphify(self) -> GraphifyAutomationResult:
        return self.consume.graphify

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "feed": self.feed.to_dict(),
            "process": self.process.to_dict(),
            "consume": self.consume.to_dict(),
            "intake": self.intake.to_dict() if self.intake is not None else None,
            "project_documents": dict(self.project_documents),
            "palace_drawers": self.palace_drawers,
            "packages": self.packages,
            "promoted": self.process.to_dict()["promoted"],
            "artifacts": list(self.artifacts),
            "graphify": self.graphify.to_dict(),
        }


@dataclass(slots=True)
class ConsumePhaseResult:
    artifacts: list[str]
    graphify: GraphifyAutomationResult

    def to_dict(self) -> dict[str, object]:
        return {
            "artifacts": list(self.artifacts),
            "graphify": self.graphify.to_dict(),
        }


@dataclass(slots=True)
class AutomationContextResult:
    project: str
    refreshed: bool
    files: dict[str, str]
    sections: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "refreshed": self.refreshed,
            "files": dict(self.files),
            "sections": dict(self.sections),
        }


@dataclass(slots=True)
class AutomationCycleState:
    status: str
    started_at: str
    finished_at: str | None
    project_filter: str | None
    build_graph: bool
    project_count: int
    results: list[dict[str, object]]
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "project_filter": self.project_filter,
            "build_graph": self.build_graph,
            "project_count": self.project_count,
            "results": list(self.results),
            "error": self.error,
        }


def _automation_imports_dir(config: WorkspaceConfig, project: str) -> Path:
    return config.imports_dir(project) / "automation"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _automation_summary(result: AutomationProjectResult) -> dict[str, object]:
    return {
        "project": result.project,
        "feed": None
        if result.intake is None
        else {
            "copied": result.intake.sync.copied,
            "updated": result.intake.sync.updated,
            "unchanged": result.intake.sync.unchanged,
            "invalid": result.intake.sync.invalid,
            "pending_mine": result.intake.pending_mine,
            "mined": result.intake.mined,
            "mine_skipped_reason": result.intake.mine_skipped_reason,
        },
        "process": {
            "project": dict(result.project_documents),
            "palace_drawers": result.palace_drawers,
            "packages": result.packages,
            "promoted_changed": sum(1 for item in result.promoted if item.changed),
            "promoted_unchanged": sum(1 for item in result.promoted if not item.changed),
        },
        "consume": {
            "graphify_status": result.graphify.status,
            "artifacts": list(result.artifacts),
        },
        "project_documents": dict(result.project_documents),
        "palace_drawers": result.palace_drawers,
        "packages": result.packages,
        "promoted_changed": sum(1 for item in result.promoted if item.changed),
        "promoted_unchanged": sum(1 for item in result.promoted if not item.changed),
        "graphify_status": result.graphify.status,
        "artifacts": list(result.artifacts),
        "intake": None
        if result.intake is None
        else {
            "copied": result.intake.sync.copied,
            "updated": result.intake.sync.updated,
            "unchanged": result.intake.sync.unchanged,
            "invalid": result.intake.sync.invalid,
            "pending_mine": result.intake.pending_mine,
            "mined": result.intake.mined,
            "mine_skipped_reason": result.intake.mine_skipped_reason,
        },
    }


def _save_automation_cycle_state(
    config: WorkspaceConfig,
    *,
    status: str,
    started_at: str,
    project_filter: str | None,
    build_graph: bool,
    results: list[AutomationProjectResult] | None = None,
    error: str | None = None,
) -> None:
    finished_at = None if status == "running" else _now_utc_iso()
    summaries = [_automation_summary(item) for item in results or []]
    payload = AutomationCycleState(
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        project_filter=project_filter,
        build_graph=build_graph,
        project_count=len(summaries),
        results=summaries,
        error=error,
    )
    dump_json_file(config.automation_cycle_state_file, payload.to_dict())


def load_automation_cycle_state(config: WorkspaceConfig) -> dict[str, object] | None:
    path = config.automation_cycle_state_file
    if not path.exists():
        return None
    payload = load_json_file(path)
    return payload if isinstance(payload, dict) else None


def _extract_titles(paths: list[Path], *, limit: int) -> list[str]:
    results: list[str] = []
    for path in paths[:limit]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("#"):
                results.append(line.lstrip("#").strip())
                break
        else:
            results.append(path.stem)
    return results


def _extract_matching_lines(paths: list[Path], markers: tuple[str, ...], *, limit: int) -> list[str]:
    matches: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for raw in text.splitlines():
            line = " ".join(raw.split())
            if not line:
                continue
            lowered = line.casefold()
            if any(marker in lowered for marker in markers):
                matches.append(f"{path.name}: {line[:220]}")
                if len(matches) >= limit:
                    return matches
    return matches


def _write_artifact(path: Path, lines: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return str(path)


def _render_graphify_status(
    handoff: GraphifyHandoff,
    graphify: GraphifyAutomationResult,
    *,
    graphify_corpus: dict[str, object],
) -> list[str]:
    onboarding = graphify_corpus.get("onboarding") if isinstance(graphify_corpus.get("onboarding"), dict) else {}
    diagnostics = graphify_corpus.get("diagnostics") if isinstance(graphify_corpus.get("diagnostics"), dict) else {}
    lines = [
        "# Graphify Status",
        "",
        f"- status: {graphify.status}",
        f"- corpus_status: {graphify_corpus.get('status')}",
        f"- attempted: {str(graphify.attempted).lower()}",
        f"- recommended_command: `{handoff.recommended_command}`",
    ]
    if onboarding:
        lines.append(f"- onboarding_status: {onboarding.get('status')}")
        lines.append(f"- agents_installed: {str(onboarding.get('agents_installed')).lower()}")
        lines.append(f"- codex_hooks_installed: {str(onboarding.get('codex_hooks_installed')).lower()}")
    if diagnostics:
        lines.append(f"- proof_diagnostics: {diagnostics.get('status')}")
        lines.append(f"- graph_path: {diagnostics.get('graph_path')}")
    if graphify.mode:
        lines.append(f"- mode: {graphify.mode}")
    if graphify.command:
        lines.append(f"- command: `{' '.join(graphify.command)}`")
    if graphify.error:
        lines.extend(["", "## Error", "", graphify.error])
    lines.extend(["", "## Corpus Summary", ""])
    for item in handoff.inventories:
        lines.append(f"- {item.scope}: {item.files} files, ~{item.words} words")
    lines.append(f"- code files: {handoff.code_files}")
    return lines


def generate_consumption_artifacts(
    config: WorkspaceConfig,
    *,
    project: str,
    handoff: GraphifyHandoff,
    graphify: GraphifyAutomationResult,
) -> list[str]:
    project_slug = slugify(project)
    graphify_corpus = graphify_corpus_status(config, project_slug)
    onboarding = graphify_corpus.get("onboarding") if isinstance(graphify_corpus.get("onboarding"), dict) else {}
    diagnostics = graphify_corpus.get("diagnostics") if isinstance(graphify_corpus.get("diagnostics"), dict) else {}
    imports_dir = _automation_imports_dir(config, project_slug)
    promoted = sorted(
        config.promoted_dir(project_slug).glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    project_root = None
    for profile in load_project_profiles(config.projects_file):
        if profile.normalized_name() == project_slug:
            project_root = profile.normalized_path()
            break
    project_documents = (
        sorted(iter_project_documents(project_root), key=lambda path: path.stat().st_mtime, reverse=True)
        if project_root is not None
        else []
    )
    recent_titles = _extract_titles(promoted, limit=5)
    decision_lines = _extract_matching_lines([*promoted, *project_documents], _DECISION_MARKERS, limit=10)
    risk_lines = _extract_matching_lines([*promoted, *project_documents], _RISK_MARKERS, limit=10)

    written: list[str] = []
    recent_lines = [f"- {title}" for title in recent_titles] or ["- No promoted knowledge yet."]
    decision_digest = [f"- {line}" for line in decision_lines] or ["- No decision-like lines detected yet."]
    risk_digest = [f"- {line}" for line in risk_lines] or ["- No risk-like lines detected yet."]

    written.append(
        _write_artifact(
            imports_dir / "latest-summary.md",
            [
                "# Latest Summary",
                "",
                f"- project: {project_slug}",
                f"- promoted_files: {len(promoted)}",
                f"- project_documents: {len(project_documents)}",
                f"- graphify_status: {graphify.status}",
                f"- graphify_corpus_status: {graphify_corpus.get('status')}",
                "",
                "## Recent Promoted Knowledge",
                "",
                *recent_lines,
            ],
        )
    )
    written.append(
        _write_artifact(
            imports_dir / "decisions-digest.md",
            [
                "# Decisions Digest",
                "",
                *decision_digest,
            ],
        )
    )
    written.append(
        _write_artifact(
            imports_dir / "risks-digest.md",
            [
                "# Risks Digest",
                "",
                *risk_digest,
            ],
        )
    )
    written.append(
        _write_artifact(
            imports_dir / "ai-context.md",
            [
                "# AI Context",
                "",
                f"- project: {project_slug}",
                f"- graphify_status: {graphify.status}",
                f"- graphify_corpus_status: {graphify_corpus.get('status')}",
                f"- graphify_onboarding_status: {onboarding.get('status')}",
                f"- graphify_proof_diagnostics: {diagnostics.get('status')}",
                f"- recommended_graphify_command: `{handoff.recommended_command}`",
                "",
                "## Start Here",
                "",
                "- Read latest-summary.md for the newest promoted changes.",
                "- Read decisions-digest.md before making project-level changes.",
                "- Read risks-digest.md before changing architecture or rollout logic.",
                "- If graphify_corpus_status is not `ingested`, read graphify-status.md before depending on Graphify outputs.",
                "",
                "## Recent Promoted Knowledge",
                "",
                *recent_lines,
            ],
        )
    )
    written.append(
        _write_artifact(
            imports_dir / "graphify-status.md",
            _render_graphify_status(handoff, graphify, graphify_corpus=graphify_corpus),
        )
    )
    return written


def _graphify_automation_result(
    *,
    handoff: GraphifyHandoff,
    result: GraphifyBuildResult | None = None,
    error: str | None = None,
    attempted: bool,
) -> GraphifyAutomationResult:
    if result is not None:
        return GraphifyAutomationResult(
            status="updated",
            attempted=attempted,
            mode=result.mode,
            command=result.command,
            error=None,
            recommended_command=handoff.recommended_command,
        )
    status = "pending_update" if error else "not_requested"
    return GraphifyAutomationResult(
        status=status,
        attempted=attempted,
        mode=None,
        command=None,
        error=error,
        recommended_command=handoff.recommended_command,
    )


def _load_text_if_exists(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _render_context_markdown(project: str, sections: dict[str, str], files: dict[str, str]) -> str:
    lines = [
        f"# MemArk Context: {project}",
        "",
        "## Files",
        "",
    ]
    for name, path in files.items():
        lines.append(f"- {name}: {path}")
    for name, content in sections.items():
        lines.extend(["", f"## {name.replace('-', ' ').title()}", ""])
        if content:
            lines.append(content)
        else:
            lines.append("_missing_")
    return "\n".join(lines).rstrip() + "\n"


def load_automation_context(
    config: WorkspaceConfig,
    *,
    project: str,
    refresh: bool = True,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
    graphify_bin: str | None = None,
    build_graph: bool = False,
) -> AutomationContextResult:
    project_slug = slugify(project)
    refreshed = False
    if refresh:
        run_automation_cycle(
            config,
            project_filter=project_slug,
            retry_attempts=retry_attempts,
            retry_delay_seconds=retry_delay_seconds,
            graphify_bin=graphify_bin,
            build_graph=build_graph,
        )
        refreshed = True

    imports_dir = _automation_imports_dir(config, project_slug)
    file_map = {
        "ai-context": str(imports_dir / "ai-context.md"),
        "latest-summary": str(imports_dir / "latest-summary.md"),
        "decisions-digest": str(imports_dir / "decisions-digest.md"),
        "risks-digest": str(imports_dir / "risks-digest.md"),
        "graphify-status": str(imports_dir / "graphify-status.md"),
    }
    sections = {
        name: _load_text_if_exists(Path(path))
        for name, path in file_map.items()
    }
    return AutomationContextResult(
        project=project_slug,
        refreshed=refreshed,
        files=file_map,
        sections=sections,
    )


def run_automation_cycle(
    config: WorkspaceConfig,
    *,
    project_filter: str | None = None,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
    graphify_bin: str | None = None,
    build_graph: bool = True,
) -> list[AutomationProjectResult]:
    intake_results = run_feed_phase(
        config=config,
        project_filter=project_filter,
        dry_run=False,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
        progress=None,
    )
    intake_by_project = {item.project: item for item in intake_results}
    profiles = load_project_profiles(config.projects_file)
    if project_filter is not None:
        target = slugify(project_filter)
        profiles = [profile for profile in profiles if profile.normalized_name() == target]
    profiles = [profile for profile in profiles if profile.enabled]

    started_at = _now_utc_iso()
    _save_automation_cycle_state(
        config,
        status="running",
        started_at=started_at,
        project_filter=slugify(project_filter) if project_filter is not None else None,
        build_graph=build_graph,
    )

    results: list[AutomationProjectResult] = []
    try:
        for profile in profiles:
            project = profile.normalized_name()
            project_snapshot = scan_project_documents(profile.normalized_path())
            palace_drawers, packages, promoted = build_palace_packages(config, project=project)
            handoff = build_graphify_handoff(
                project,
                config.corpus_project_dir(project),
                project_root=profile.normalized_path(),
            )

            graphify_result: GraphifyBuildResult | None = None
            graphify_error: str | None = None
            attempted = False
            if build_graph:
                attempted = True
                try:
                    graphify_result = run_graphify(
                        graphify_bin=graphify_bin or config.graphify_bin,
                        project_dir=config.corpus_project_dir(project),
                        update=True,
                    )
                except GraphifyError as exc:
                    graphify_error = str(exc)
            graphify = _graphify_automation_result(
                handoff=handoff,
                result=graphify_result,
                error=graphify_error,
                attempted=attempted,
            )
            artifacts = generate_consumption_artifacts(
                config,
                project=project,
                handoff=handoff,
                graphify=graphify,
            )
            results.append(
                AutomationProjectResult(
                    project=project,
                    feed=FeedPhaseResult(intake=intake_by_project.get(project)),
                    process=ProcessPhaseResult(
                        project=project_snapshot,
                        palace_drawers=palace_drawers,
                        packages=packages,
                        promoted=promoted,
                    ),
                    consume=ConsumePhaseResult(
                        artifacts=artifacts,
                        graphify=graphify,
                    ),
                )
            )
    except Exception as exc:
        _save_automation_cycle_state(
            config,
            status="failed",
            started_at=started_at,
            project_filter=slugify(project_filter) if project_filter is not None else None,
            build_graph=build_graph,
            results=results,
            error=str(exc),
        )
        raise
    _save_automation_cycle_state(
        config,
        status="completed",
        started_at=started_at,
        project_filter=slugify(project_filter) if project_filter is not None else None,
        build_graph=build_graph,
        results=results,
    )
    return results
