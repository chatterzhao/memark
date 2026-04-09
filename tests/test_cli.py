from __future__ import annotations

import json
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env["PYTHONPATH"] = str(ROOT)
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "memark", *args],
        cwd=cwd,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


class MemArkCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name) / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_init_creates_workspace_layout(self) -> None:
        result = run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.workspace / ".memark" / "config.json").exists())
        self.assertTrue((self.workspace / "inbox" / "promoted").exists())
        self.assertTrue((self.workspace / "inbox" / "documents").exists())
        self.assertTrue((self.workspace / "corpus" / "memark" / "promoted").exists())
        payload = json.loads((self.workspace / ".memark" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["mempalace_bin"], "mempalace")

    def test_validate_and_promote_room_package(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        package = {
            "wing_id": "project/memark",
            "wing_kind": "project",
            "hall_id": "discoveries",
            "room_id": "auth-migration",
            "room_title": "Authentication Migration",
            "room_summary": "Summary of migration decisions.",
            "closets": [
                {
                    "closet_id": "closet-1",
                    "summary": "We moved auth to a dedicated service.",
                    "key_points": ["Token rotation", "Audit logging"],
                    "tags": ["auth", "migration"],
                }
            ],
            "drawer_refs": [
                {
                    "drawer_id": "drawer-001",
                    "timestamp": "2026-04-08T12:00:00Z",
                    "speaker": "assistant",
                    "excerpt": "We should split auth.",
                }
            ],
            "participants": ["user", "assistant"],
            "related_entities": ["Module: auth-service", "Doc: adr-001.md"],
            "source_timestamps": {
                "start": "2026-04-01T10:00:00Z",
                "end": "2026-04-07T18:00:00Z",
            },
            "updated_at": "2026-04-08T00:00:00Z",
        }
        input_file = self.workspace / "inbox" / "promoted" / "room.json"
        input_file.write_text(json.dumps(package), encoding="utf-8")

        validate = run_cli("validate", str(input_file), cwd=ROOT)
        self.assertEqual(validate.returncode, 0, validate.stderr)

        promote = run_cli("promote", "--workspace", str(self.workspace), cwd=ROOT)
        self.assertEqual(promote.returncode, 0, promote.stderr)
        output = self.workspace / "corpus" / "memark" / "promoted" / "room-auth-migration.md"
        self.assertTrue(output.exists())
        content = output.read_text(encoding="utf-8")
        self.assertIn('room_id: "auth-migration"', content)
        self.assertIn("# Authentication Migration", content)
        self.assertIn("## Evidence", content)

    def test_promote_rejects_non_project_by_default(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        package = {
            "wing_id": "general/chat",
            "wing_kind": "general",
            "hall_id": "events",
            "room_id": "coffee",
            "room_title": "Coffee Talk",
            "closets": [{"summary": "Casual conversation."}],
        }
        input_file = self.workspace / "inbox" / "promoted" / "general.json"
        input_file.write_text(json.dumps(package), encoding="utf-8")

        promote = run_cli("promote", "--workspace", str(self.workspace), cwd=ROOT)
        self.assertNotEqual(promote.returncode, 0)
        self.assertIn("wing_kind must be 'project'", promote.stderr)

    def test_add_documents_copies_files(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        doc = self.workspace / "architecture.md"
        doc.write_text("# Architecture\n", encoding="utf-8")

        result = run_cli(
            "add-documents",
            "--workspace",
            str(self.workspace),
            str(doc),
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        copied = self.workspace / "corpus" / "memark" / "documents" / "architecture.md"
        self.assertTrue(copied.exists())

    def test_build_uses_graphify_binary(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_graphify = fake_bin_dir / "graphify"
        log_file = self.workspace / "graphify.log"
        fake_graphify.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                echo "$@" > "{log_file}"
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_graphify.chmod(fake_graphify.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli(
            "build",
            "--workspace",
            str(self.workspace),
            "--update",
            "--wiki",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(log_file.exists())
        logged = log_file.read_text(encoding="utf-8")
        self.assertIn("--update", logged)
        self.assertIn("--wiki", logged)

    def test_build_reports_graphify_cli_contract_mismatch(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_graphify = fake_bin_dir / "graphify"
        fake_graphify.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                echo "error: unknown command '$1'" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        fake_graphify.chmod(fake_graphify.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli("build", "--workspace", str(self.workspace), cwd=ROOT, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fallback to graphify.watch._rebuild_code failed", result.stderr)

    def test_build_falls_back_to_graphify_watch_module(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        promoted = self.workspace / "corpus" / "memark" / "promoted" / "room-demo.md"
        promoted.write_text("# Demo\n", encoding="utf-8")
        code_file = self.workspace / "corpus" / "memark" / "demo.py"
        code_file.write_text("def demo():\n    return 'ok'\n", encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_graphify = fake_bin_dir / "graphify"
        fake_graphify.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                echo "error: unknown command '$1'" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        fake_graphify.chmod(fake_graphify.stat().st_mode | stat.S_IEXEC)

        fake_pkg_root = self.workspace / "fake-py"
        fake_pkg = fake_pkg_root / "graphify"
        fake_pkg.mkdir(parents=True)
        (fake_pkg / "__init__.py").write_text("", encoding="utf-8")
        (fake_pkg / "watch.py").write_text(
            textwrap.dedent(
                """\
                from pathlib import Path


                def _rebuild_code(path: Path) -> bool:
                    out = path / "graphify-out"
                    out.mkdir(exist_ok=True)
                    (out / "GRAPH_REPORT.md").write_text("# Fake report\\n", encoding="utf-8")
                    (out / "graph.json").write_text('{"nodes": [], "edges": []}\\n', encoding="utf-8")
                    print("[graphify watch] Rebuilt fake graph")
                    return True
                """
            ),
            encoding="utf-8",
        )

        env = {
            "PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", ""),
            "PYTHONPATH": str(fake_pkg_root) + os.pathsep + str(ROOT),
        }

        result = run_cli("build", "--workspace", str(self.workspace), cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Graphify build completed", result.stdout)
        self.assertIn("graphify.watch", result.stdout)
        self.assertTrue((self.workspace / "corpus" / "memark" / "graphify-out" / "graph.json").exists())

    def test_build_fallback_uses_graphify_environment_python(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        code_file = self.workspace / "corpus" / "memark" / "demo.py"
        code_file.write_text("def demo():\n    return 'ok'\n", encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_graphify = fake_bin_dir / "graphify"
        fake_graphify.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                echo "error: unknown command '$1'" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        fake_graphify.chmod(fake_graphify.stat().st_mode | stat.S_IEXEC)

        fake_pkg_root = self.workspace / "graphify-env"
        fake_pkg = fake_pkg_root / "graphify"
        fake_pkg.mkdir(parents=True)
        (fake_pkg / "__init__.py").write_text("", encoding="utf-8")
        (fake_pkg / "watch.py").write_text(
            textwrap.dedent(
                """\
                from pathlib import Path


                def _rebuild_code(path: Path) -> bool:
                    out = path / "graphify-out"
                    out.mkdir(exist_ok=True)
                    (out / "graph.json").write_text('{"nodes": [], "edges": []}\\n', encoding="utf-8")
                    (out / "GRAPH_REPORT.md").write_text("# Report\\n", encoding="utf-8")
                    return True
                """
            ),
            encoding="utf-8",
        )

        fake_python = fake_bin_dir / "python"
        fake_python.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                export PYTHONPATH="{fake_pkg_root}:$PYTHONPATH"
                exec "{sys.executable}" "$@"
                """
            ),
            encoding="utf-8",
        )
        fake_python.chmod(fake_python.stat().st_mode | stat.S_IEXEC)

        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}
        result = run_cli("build", "--workspace", str(self.workspace), cwd=ROOT, env=env)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.workspace / "corpus" / "memark" / "graphify-out" / "graph.json").exists())

    def test_promote_is_idempotent_and_can_archive(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        package = {
            "wing_id": "project/memark",
            "wing_kind": "project",
            "hall_id": "events",
            "room_id": "release-cut",
            "room_title": "Release Cut",
            "closets": [{"summary": "Release process stabilized."}],
        }
        input_file = self.workspace / "inbox" / "promoted" / "release.json"
        input_file.write_text(json.dumps(package), encoding="utf-8")

        first = run_cli("promote", "--workspace", str(self.workspace), "--archive", cwd=ROOT)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("1 changed, 0 unchanged", first.stdout)
        self.assertFalse(input_file.exists())
        archived = self.workspace / ".memark" / "archive" / "release.json"
        self.assertTrue(archived.exists())

        second = run_cli(
            "promote",
            str(archived),
            "--workspace",
            str(self.workspace),
            cwd=ROOT,
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("0 changed, 1 unchanged", second.stdout)

    def test_status_reports_counts(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        (self.workspace / "inbox" / "promoted" / "queued.json").write_text("{}", encoding="utf-8")
        result = run_cli("status", "--workspace", str(self.workspace), cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Inbox files: 1", result.stdout)
        self.assertIn("Codex staged sessions: 0", result.stdout)
        self.assertIn("Inbox promoted dir:", result.stdout)

    def test_status_reports_json(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        result = run_cli("status", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["project"], "memark")
        self.assertIn("graphify", payload)
        self.assertIn("mempalace", payload)
        self.assertIn("palace_dir", payload)
        self.assertIn("inbox_promoted_dir", payload)
        self.assertIn("codex_staged_sessions", payload)

    def test_status_counts_nested_import_files(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        nested = self.workspace / "corpus" / "memark" / "imports" / "memark" / "graphify.py"
        nested.parent.mkdir(parents=True, exist_ok=True)
        nested.write_text("print('ok')\n", encoding="utf-8")

        result = run_cli("status", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["imports"], 1)

    def test_run_promotes_documents_then_builds(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        package = {
            "wing_id": "project/memark",
            "wing_kind": "project",
            "hall_id": "events",
            "room_id": "release-cut",
            "room_title": "Release Cut",
            "closets": [{"summary": "Release process stabilized."}],
        }
        input_file = self.workspace / "inbox" / "promoted" / "release.json"
        input_file.write_text(json.dumps(package), encoding="utf-8")
        doc = self.workspace / "inbox" / "documents" / "architecture.md"
        doc.write_text("# Architecture\n", encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_graphify = fake_bin_dir / "graphify"
        log_file = self.workspace / "run-graphify.log"
        fake_graphify.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                echo "$@" > "{log_file}"
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_graphify.chmod(fake_graphify.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli("run", "--workspace", str(self.workspace), "--update", cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        promoted = self.workspace / "corpus" / "memark" / "promoted" / "room-release-cut.md"
        copied = self.workspace / "corpus" / "memark" / "documents" / "architecture.md"
        self.assertTrue(promoted.exists())
        self.assertTrue(copied.exists())
        self.assertIn("--update", log_file.read_text(encoding="utf-8"))

    def test_run_infers_project_from_room_package_when_not_overridden(self) -> None:
        run_cli("init", str(self.workspace), "--project", "Demo", cwd=ROOT)
        package = {
            "wing_id": "project/memark",
            "wing_kind": "project",
            "hall_id": "discoveries",
            "room_id": "auth-migration",
            "room_title": "Authentication Migration",
            "closets": [{"summary": "Move auth into a dedicated service."}],
        }
        input_file = self.workspace / "inbox" / "promoted" / "room.json"
        input_file.write_text(json.dumps(package), encoding="utf-8")

        result = run_cli("run", "--workspace", str(self.workspace), "--no-build", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.workspace / "corpus" / "memark" / "promoted" / "room-auth-migration.md").exists())
        self.assertFalse((self.workspace / "corpus" / "demo" / "promoted" / "room-auth-migration.md").exists())

    def test_run_rejects_mixed_project_packages_without_override(self) -> None:
        run_cli("init", str(self.workspace), "--project", "Demo", cwd=ROOT)
        packages = [
            {
                "wing_id": "project/memark",
                "wing_kind": "project",
                "hall_id": "discoveries",
                "room_id": "auth-migration",
                "room_title": "Authentication Migration",
                "closets": [{"summary": "Move auth into a dedicated service."}],
            },
            {
                "wing_id": "project/freely",
                "wing_kind": "project",
                "hall_id": "discoveries",
                "room_id": "billing-migration",
                "room_title": "Billing Migration",
                "closets": [{"summary": "Move billing into a dedicated service."}],
            },
        ]
        input_file = self.workspace / "inbox" / "promoted" / "rooms.json"
        input_file.write_text(json.dumps(packages), encoding="utf-8")

        result = run_cli("run", "--workspace", str(self.workspace), "--no-build", cwd=ROOT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("multiple target projects", result.stderr)

    def test_codex_sync_stages_matching_sessions(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "codex-sessions"
        matching = sessions_root / "2026" / "04" / "08" / "rollout-a.jsonl"
        matching.parent.mkdir(parents=True, exist_ok=True)
        matching.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "session_meta",
                            "payload": {
                                "id": "sess-a",
                                "cwd": str(ROOT),
                                "timestamp": "2026-04-08T12:00:00Z",
                            },
                        }
                    ),
                    json.dumps({"type": "message", "payload": {"text": "hello"}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        non_matching = sessions_root / "2026" / "04" / "08" / "rollout-b.jsonl"
        non_matching.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "sess-b",
                        "cwd": str(self.workspace / "other-project"),
                        "timestamp": "2026-04-08T13:00:00Z",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_cli(
            "codex-sync",
            "--workspace",
            str(self.workspace),
            "--project-root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["scanned"], 2)
        self.assertEqual(payload["matched"], 1)
        self.assertEqual(payload["copied"], 1)
        staged = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "08" / "rollout-a.jsonl"
        self.assertTrue(staged.exists())
        self.assertFalse(
            (self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "08" / "rollout-b.jsonl")
            .exists()
        )

    def test_codex_sync_updates_changed_session_and_reports_unchanged(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "codex-sessions"
        session_file = sessions_root / "2026" / "04" / "08" / "rollout-a.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "sess-a",
                        "cwd": str(ROOT),
                        "timestamp": "2026-04-08T12:00:00Z",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        first = run_cli(
            "codex-sync",
            "--workspace",
            str(self.workspace),
            "--project-root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        first_payload = json.loads(first.stdout)
        self.assertEqual(first_payload["copied"], 1)

        second = run_cli(
            "codex-sync",
            "--workspace",
            str(self.workspace),
            "--project-root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        second_payload = json.loads(second.stdout)
        self.assertEqual(second_payload["unchanged"], 1)

        session_file.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "session_meta",
                            "payload": {
                                "id": "sess-a",
                                "cwd": str(ROOT),
                                "timestamp": "2026-04-08T12:00:00Z",
                            },
                        }
                    ),
                    json.dumps({"type": "message", "payload": {"text": "updated"}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        third = run_cli(
            "codex-sync",
            "--workspace",
            str(self.workspace),
            "--project-root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(third.returncode, 0, third.stderr)
        third_payload = json.loads(third.stdout)
        self.assertEqual(third_payload["updated"], 1)

    def test_codex_sync_supports_cwd_prefix(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "codex-sessions"
        worktree = self.workspace / "worktrees" / "memark-branch"
        session_file = sessions_root / "2026" / "04" / "08" / "rollout-a.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "sess-a",
                        "cwd": str(worktree),
                        "timestamp": "2026-04-08T12:00:00Z",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_cli(
            "codex-sync",
            "--workspace",
            str(self.workspace),
            "--project-root",
            str(self.workspace / "unrelated-root"),
            "--cwd-prefix",
            str(self.workspace / "worktrees"),
            "--sessions-root",
            str(sessions_root),
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["matched"], 1)

    def test_mempalace_mine_runs_against_project_staging(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        staging_file = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09" / "rollout-a.jsonl"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text('{"type":"session_meta","payload":{"cwd":"%s"}}\n' % ROOT, encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        log_file = self.workspace / "mempalace.log"
        fake_mempalace.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                echo "$@" > "{log_file}"
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli("mempalace-mine", "--workspace", str(self.workspace), cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(log_file.exists())
        logged = log_file.read_text(encoding="utf-8")
        self.assertIn("--palace", logged)
        self.assertIn("mine", logged)
        self.assertIn("--mode convos", logged)
        self.assertIn(str(self.workspace / ".memark" / "staging" / "memark" / "sessions"), logged)

    def test_mempalace_mine_dry_run_renders_json(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        result = run_cli(
            "mempalace-mine",
            "--workspace",
            str(self.workspace),
            "--dry-run",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["project"], "memark")
        self.assertIn("--mode", payload["command"])
        self.assertIn("convos", payload["command"])

    def test_mempalace_mine_reports_missing_binary(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        staging_file = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09" / "rollout-a.jsonl"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text('{"type":"session_meta","payload":{"cwd":"%s"}}\n' % ROOT, encoding="utf-8")

        result = run_cli(
            "mempalace-mine",
            "--workspace",
            str(self.workspace),
            "--mempalace-bin",
            "mempalace-does-not-exist",
            cwd=ROOT,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found in PATH", result.stderr)

    def test_palace_export_reads_convo_drawers_from_sqlite_fallback(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        db_path = palace_dir / "chroma.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE embeddings (id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL, embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE embedding_metadata (
                  id INTEGER NOT NULL,
                  key TEXT NOT NULL,
                  string_value TEXT,
                  int_value INTEGER,
                  float_value REAL,
                  bool_value INTEGER,
                  PRIMARY KEY (id, key)
                )
                """
            )
            conn.execute(
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (1, 'seg-a', 'drawer_demo', X'01')"
            )
            rows = [
                (1, "chroma:document", "Decision: adopt Clerk for auth.", None, None, None),
                (1, "wing", "codex_project", None, None, None),
                (1, "room", "decisions", None, None, None),
                (1, "source_file", "/tmp/demo/rollout-a.jsonl", None, None, None),
                (1, "filed_at", "2026-04-09T02:10:00Z", None, None, None),
                (1, "ingest_mode", "convos", None, None, None),
                (1, "extract_mode", "exchange", None, None, None),
                (1, "added_by", "mempalace", None, None, None),
                (1, "chunk_index", None, 0, None, None),
            ]
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli("palace-export", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["drawers"][0]["drawer_id"], "drawer_demo")
        self.assertEqual(payload["drawers"][0]["room"], "decisions")
        self.assertEqual(payload["drawers"][0]["ingest_mode"], "convos")

    def test_palace_export_filters_by_room(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        db_path = palace_dir / "chroma.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE embeddings (id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL, embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE embedding_metadata (
                  id INTEGER NOT NULL,
                  key TEXT NOT NULL,
                  string_value TEXT,
                  int_value INTEGER,
                  float_value REAL,
                  bool_value INTEGER,
                  PRIMARY KEY (id, key)
                )
                """
            )
            conn.executemany(
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (?, ?, ?, X'01')",
                [
                    (1, "seg-a", "drawer_a"),
                    (2, "seg-b", "drawer_b"),
                ],
            )
            metadata_rows = [
                (1, "chroma:document", "Decision drawer", None, None, None),
                (1, "room", "decisions", None, None, None),
                (1, "ingest_mode", "convos", None, None, None),
                (2, "chroma:document", "Debug drawer", None, None, None),
                (2, "room", "debugging", None, None, None),
                (2, "ingest_mode", "convos", None, None, None),
            ]
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                metadata_rows,
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli(
            "palace-export",
            "--workspace",
            str(self.workspace),
            "--room",
            "debugging",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["drawers"][0]["drawer_id"], "drawer_b")

    def test_palace_package_builds_room_package_candidates(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        db_path = palace_dir / "chroma.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE embeddings (id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL, embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE embedding_metadata (
                  id INTEGER NOT NULL,
                  key TEXT NOT NULL,
                  string_value TEXT,
                  int_value INTEGER,
                  float_value REAL,
                  bool_value INTEGER,
                  PRIMARY KEY (id, key)
                )
                """
            )
            conn.executemany(
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (?, ?, ?, X'01')",
                [
                    (1, "seg-a", "drawer_auth_1"),
                    (2, "seg-b", "drawer_auth_2"),
                ],
            )
            metadata_rows = [
                (1, "chroma:document", "Decision: adopt Clerk for auth and write an ADR.", None, None, None),
                (1, "wing", "codex_project", None, None, None),
                (1, "room", "auth_decisions", None, None, None),
                (1, "source_file", "/tmp/demo/rollout-a.jsonl", None, None, None),
                (1, "filed_at", "2026-04-09T02:10:00Z", None, None, None),
                (1, "ingest_mode", "convos", None, None, None),
                (2, "chroma:document", "Migration checklist: keep billing internal and stage rollout.", None, None, None),
                (2, "wing", "codex_project", None, None, None),
                (2, "room", "auth_decisions", None, None, None),
                (2, "source_file", "/tmp/demo/rollout-b.jsonl", None, None, None),
                (2, "filed_at", "2026-04-09T02:11:00Z", None, None, None),
                (2, "ingest_mode", "convos", None, None, None),
            ]
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                metadata_rows,
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli("palace-package", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["drawers"], 2)
        self.assertEqual(len(payload["packages"]), 1)
        package = payload["packages"][0]
        self.assertEqual(package["wing_id"], "project/memark")
        self.assertEqual(package["room_id"], "auth-decisions")
        self.assertEqual(len(package["drawer_refs"]), 2)
        self.assertEqual(package["source_timestamps"]["start"], "2026-04-09T02:10:00Z")
        self.assertEqual(package["source_timestamps"]["end"], "2026-04-09T02:11:00Z")

    def test_palace_package_can_write_into_inbox(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        db_path = palace_dir / "chroma.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE embeddings (id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL, embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE embedding_metadata (
                  id INTEGER NOT NULL,
                  key TEXT NOT NULL,
                  string_value TEXT,
                  int_value INTEGER,
                  float_value REAL,
                  bool_value INTEGER,
                  PRIMARY KEY (id, key)
                )
                """
            )
            conn.execute(
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (1, 'seg-a', 'drawer_debug', X'01')"
            )
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, "chroma:document", "Resolved flaky CI by isolating race in auth tests.", None, None, None),
                    (1, "wing", "codex_project", None, None, None),
                    (1, "room", "ci_debugging", None, None, None),
                    (1, "source_file", "/tmp/demo/rollout-c.jsonl", None, None, None),
                    (1, "filed_at", "2026-04-09T02:12:00Z", None, None, None),
                    (1, "ingest_mode", "convos", None, None, None),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli(
            "palace-package",
            "--workspace",
            str(self.workspace),
            "--write-inbox",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["written"]), 1)
        written_path = Path(payload["written"][0])
        self.assertTrue(written_path.exists())
        package = json.loads(written_path.read_text(encoding="utf-8"))
        self.assertEqual(package["room_id"], "ci-debugging")

    def test_palace_run_promotes_packages_without_build(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        db_path = palace_dir / "chroma.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE embeddings (id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL, embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE embedding_metadata (
                  id INTEGER NOT NULL,
                  key TEXT NOT NULL,
                  string_value TEXT,
                  int_value INTEGER,
                  float_value REAL,
                  bool_value INTEGER,
                  PRIMARY KEY (id, key)
                )
                """
            )
            conn.execute(
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (1, 'seg-a', 'drawer_bridge', X'01')"
            )
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, "chroma:document", "Decision: promote curated bridge notes, not the whole palace.", None, None, None),
                    (1, "wing", "codex_project", None, None, None),
                    (1, "room", "bridge_governance", None, None, None),
                    (1, "source_file", "/tmp/demo/rollout-d.jsonl", None, None, None),
                    (1, "filed_at", "2026-04-09T02:13:00Z", None, None, None),
                    (1, "ingest_mode", "convos", None, None, None),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli(
            "palace-run",
            "--workspace",
            str(self.workspace),
            "--no-build",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["drawers"], 1)
        self.assertEqual(payload["packages"], 1)
        self.assertIsNone(payload["build"])
        self.assertEqual(len(payload["written"]), 1)
        promoted = payload["promoted"][0]
        self.assertEqual(promoted["room_id"], "bridge-governance")
        self.assertTrue(promoted["changed"])
        output = self.workspace / "corpus" / "memark" / "promoted" / "room-bridge-governance.md"
        self.assertTrue(output.exists())

    def test_palace_run_dry_run_reports_targets(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        db_path = palace_dir / "chroma.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE embeddings (id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL, embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE embedding_metadata (
                  id INTEGER NOT NULL,
                  key TEXT NOT NULL,
                  string_value TEXT,
                  int_value INTEGER,
                  float_value REAL,
                  bool_value INTEGER,
                  PRIMARY KEY (id, key)
                )
                """
            )
            conn.execute(
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (1, 'seg-a', 'drawer_dry', X'01')"
            )
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, "chroma:document", "Plan: dry-run the full palace pipeline before enabling build.", None, None, None),
                    (1, "wing", "codex_project", None, None, None),
                    (1, "room", "pipeline_preview", None, None, None),
                    (1, "source_file", "/tmp/demo/rollout-e.jsonl", None, None, None),
                    (1, "filed_at", "2026-04-09T02:14:00Z", None, None, None),
                    (1, "ingest_mode", "convos", None, None, None),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli(
            "palace-run",
            "--workspace",
            str(self.workspace),
            "--dry-run",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["packages"], 1)
        self.assertEqual(len(payload["write_targets"]), 1)
        self.assertIn("graphify", " ".join(payload["build_command"]))
        self.assertFalse((self.workspace / "inbox" / "promoted" / "palace-pipeline-preview.json").exists())


if __name__ == "__main__":
    unittest.main()
