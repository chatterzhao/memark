"""Static milestone catalog for MemArk rollout tracking."""

from __future__ import annotations

from datetime import datetime, timezone


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _check(status_id: str, label: str, passed: bool, detail: str) -> dict[str, str | bool]:
    return {
        "id": status_id,
        "label": label,
        "passed": passed,
        "status": "passed" if passed else "blocked",
        "detail": detail,
    }


def milestone_catalog() -> dict[str, object]:
    milestones = [
        {
            "id": "M0",
            "name": "Beta",
            "status": "achieved",
            "summary": "Controlled macOS beta dogfood on this repo is operational.",
            "focus": [
                "user-level install and runtime verification",
                "workspace/project onboarding",
                "single-cycle intake -> process -> consume automation",
                "launchd-backed scheduler install/status/uninstall",
                "local corpus consumption through context and query",
            ],
            "features": [
                {"name": "Install Runtime", "commands": ["memark install", "memark doctor"]},
                {"name": "Workspace Onboarding", "commands": ["memark init", "memark project-set", "memark projects-list"]},
                {"name": "Automation Cycle", "commands": ["memark codex-sync", "memark projects-run", "memark automation-run"]},
                {
                    "name": "Palace Ops",
                    "commands": [
                        "memark mempalace-mine",
                        "memark palace-status",
                        "memark palace-clean",
                        "memark palace-rebuild",
                        "memark palace-retry",
                        "memark palace-export",
                        "memark palace-package",
                        "memark palace-run",
                    ],
                },
                {"name": "Corpus Promotion", "commands": ["memark promote", "memark add-documents"]},
                {"name": "Consumption Surface", "commands": ["memark query", "memark context"]},
                {
                    "name": "Scheduler and Status",
                    "commands": ["memark service-install", "memark service-status", "memark service-uninstall", "memark automation-status"],
                },
                {"name": "Worktree Support", "commands": ["memark worktree-attach", "memark worktree-hook-install"]},
                {"name": "Graphify Bridge", "commands": ["memark graphify-handoff"]},
                {"name": "Slash Adapter", "commands": ["memark slash"]},
            ],
        },
        {
            "id": "M1",
            "name": "Beta+1",
            "status": "in_progress",
            "summary": "Reliable unattended dogfood plus one autonomous mixed-corpus graph proof on the project corpus.",
            "focus": [
                "multi-day scheduler reliability evidence",
                "service-status health and stale/failing observation",
                "autonomous mixed-corpus graph closure on the prepared corpus",
                "AI auto-consumption that measurably reduces repeated context gathering",
            ],
            "features": [
                {"name": "Background Reliability", "commands": ["memark service-status", "memark automation-status"]},
                {"name": "Dogfood Operations", "commands": ["memark service-install", "memark service-uninstall", "memark context"]},
                {"name": "Autonomous Graph Build", "commands": ["memark build", "memark run", "memark automation-run"]},
                {"name": "Slash-compatible Execution", "commands": ["memark slash", "memark status"]},
                {"name": "Graph Proof Surface", "commands": ["memark graphify-proof", "memark milestones"]},
                {"name": "Graphify Interop", "commands": ["memark graphify-handoff", "memark graphify-onboard"]},
            ],
        },
        {
            "id": "M2",
            "name": "Cross-platform Preview",
            "status": "planned",
            "summary": "Verify scheduler and install paths on macOS plus at least one non-macOS platform.",
            "focus": [
                "linux scheduler support",
                "windows scheduler support",
                "cross-platform install/status UX",
            ],
            "features": [],
        },
    ]
    return {
        "current": "M1",
        "achieved": "M0",
        "milestones": milestones,
    }


def assess_current_milestone(payload: dict[str, object]) -> dict[str, object]:
    current_id = payload["current"]
    current = next(item for item in payload["milestones"] if item["id"] == current_id)
    snapshot = payload.get("workspace_snapshot")
    assessment: dict[str, object] = {
        "id": current["id"],
        "name": current["name"],
        "summary": current["summary"],
        "status": "needs_workspace",
        "checks": [],
        "blockers": [],
        "next_actions": [],
    }
    if not isinstance(snapshot, dict):
        assessment["next_actions"] = [
            "Run 'memark milestones --workspace <dir>' to attach live workspace evidence."
        ]
        return assessment

    service = snapshot.get("service") if isinstance(snapshot.get("service"), dict) else {}
    automation = snapshot.get("automation") if isinstance(snapshot.get("automation"), dict) else {}
    results = automation.get("results") if isinstance(automation.get("results"), list) else []

    service_ok = (
        service.get("installed") is True
        and service.get("loaded") is True
        and service.get("health") == "ok"
    )
    service_detail = (
        f"service health={service.get('health')}, installed={service.get('installed')}, loaded={service.get('loaded')}"
        if service
        else str(snapshot.get("service_error") or "service evidence unavailable")
    )

    finished_at = _parse_timestamp(automation.get("finished_at"))
    automation_ok = automation.get("status") == "completed" and finished_at is not None
    automation_detail = (
        f"last automation status={automation.get('status')}, finished_at={automation.get('finished_at')}"
        if automation
        else "automation evidence unavailable"
    )

    corpus_ok = all(snapshot.get(name, 0) > 0 for name in ("promoted_rooms", "documents", "imports"))
    corpus_detail = (
        f"promoted={snapshot.get('promoted_rooms', 0)}, documents={snapshot.get('documents', 0)}, imports={snapshot.get('imports', 0)}"
    )

    auto_consumption_ok = any(isinstance(item, dict) and item.get("artifacts") for item in results)
    auto_consumption_detail = (
        "automation artifacts were generated in the latest cycle"
        if auto_consumption_ok
        else "latest cycle does not show generated automation artifacts"
    )

    graphify_proof = snapshot.get("graphify_proof") if isinstance(snapshot.get("graphify_proof"), dict) else {}
    graphify_corpus = snapshot.get("graphify_corpus") if isinstance(snapshot.get("graphify_corpus"), dict) else {}
    graphify_onboarding = graphify_corpus.get("onboarding") if isinstance(graphify_corpus.get("onboarding"), dict) else {}
    graphify_diagnostics = (
        snapshot.get("graphify_proof_diagnostics")
        if isinstance(snapshot.get("graphify_proof_diagnostics"), dict)
        else {}
    )
    graphify_ok = graphify_proof.get("status") == "ingested"
    graphify_statuses = [
        item.get("graphify_status")
        for item in results
        if isinstance(item, dict)
    ]
    graphify_detail = (
        f"proof recorded_at={graphify_proof.get('recorded_at')}, latest graphify statuses={graphify_statuses}"
        if graphify_proof
        else (
            "no ingestion proof recorded; "
            f"corpus_status={graphify_corpus.get('status')}; "
            f"onboarding={graphify_onboarding.get('status')}; "
            f"diagnostics={graphify_diagnostics.get('status')}; "
            f"latest graphify statuses={graphify_statuses}"
            if graphify_statuses
            else (
                "no graphify result was recorded in the latest cycle; "
                f"corpus_status={graphify_corpus.get('status')}; "
                f"onboarding={graphify_onboarding.get('status')}; "
                f"diagnostics={graphify_diagnostics.get('status')}"
            )
        )
    )

    checks = [
        _check("background_scheduler", "Background scheduler is healthy", service_ok, service_detail),
        _check("automation_cycle", "Automation completed recently", automation_ok, automation_detail),
        _check("project_corpus", "Workspace has a real mixed local corpus", corpus_ok, corpus_detail),
        _check("auto_consumption", "Automation produced consumption artifacts", auto_consumption_ok, auto_consumption_detail),
        _check("graphify_closure", "Mixed-corpus graph closure is proven", graphify_ok, graphify_detail),
    ]
    blockers = [item["label"] for item in checks if not item["passed"]]
    next_actions: list[str] = []
    if not service_ok:
        next_actions.append("Keep the launchd job installed and restore service health to 'ok'.")
    if not automation_ok:
        next_actions.append("Run and observe another completed automation cycle.")
    if not auto_consumption_ok:
        next_actions.append("Verify automation keeps writing summary/digest artifacts into imports/automation.")
    if not graphify_ok:
        corpus_status = graphify_corpus.get("status")
        diagnostics_status = graphify_diagnostics.get("status")
        graph_path = graphify_diagnostics.get("graph_path")
        recommended_command = graphify_onboarding.get("recommended_command")
        if corpus_status == "graph_missing":
            next_actions.append(
                f"Run 'memark build --workspace <dir>' so the prepared corpus writes {graph_path} with mixed-corpus nodes."
            )
            if isinstance(recommended_command, str) and recommended_command:
                next_actions.append(f"Optional upstream interop command: {recommended_command}")
        elif diagnostics_status == "graph_missing":
            next_actions.append(
                f"Run 'memark build --workspace <dir>' or 'memark automation-run --workspace <dir>' so {graph_path} is created."
            )
            if isinstance(recommended_command, str) and recommended_command:
                next_actions.append(f"Optional upstream interop command: {recommended_command}")
        elif diagnostics_status == "code_only_graph":
            next_actions.append(
                "Rebuild the corpus graph with MemArk's mixed-corpus path; the current graph only contains code nodes."
            )
            if isinstance(recommended_command, str) and recommended_command:
                next_actions.append(f"Optional upstream interop command: {recommended_command}")
        else:
            next_actions.append("Record or auto-detect one mixed-corpus graph proof beyond 'pending_update' or 'not_requested'.")

    assessment["checks"] = checks
    assessment["blockers"] = blockers
    assessment["next_actions"] = next_actions
    assessment["status"] = "ready" if not blockers else "blocked"
    return assessment
