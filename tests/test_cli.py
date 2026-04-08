from __future__ import annotations

import json
import os
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
        self.assertIn("does not accept direct 'graphify <folder>' builds", result.stderr)

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
        self.assertIn("Inbox promoted dir:", result.stdout)

    def test_status_reports_json(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        result = run_cli("status", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["project"], "memark")
        self.assertIn("graphify", payload)
        self.assertIn("inbox_promoted_dir", payload)

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


if __name__ == "__main__":
    unittest.main()
