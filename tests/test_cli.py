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
from unittest import mock

from memark import install as install_mod
from memark import workspace as workspace_mod

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
        self.assertTrue((self.workspace / ".memark" / "projects.toml").exists())
        self.assertTrue((self.workspace / "inbox" / "promoted").exists())
        self.assertTrue((self.workspace / "inbox" / "documents").exists())
        self.assertTrue((self.workspace / "corpus" / "memark" / "promoted").exists())
        payload = json.loads((self.workspace / ".memark" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(Path(payload["mempalace_bin"]).name, "mempalace")
        self.assertEqual(Path(payload["graphify_bin"]).name, "graphify")

    def test_load_workspace_prefers_user_runtime_binaries(self) -> None:
        with (
            mock.patch("memark.workspace.shutil.which", return_value=None),
            mock.patch.object(workspace_mod, "_runtime_binary", side_effect=lambda name: f"/tmp/runtime/{name}"),
        ):
            config = workspace_mod.create_workspace(self.workspace, "MemArk")
            self.assertEqual(config.mempalace_bin, "mempalace")
            self.assertEqual(config.graphify_bin, "graphify")

            loaded = workspace_mod.load_workspace(str(self.workspace))
            self.assertEqual(loaded.mempalace_bin, "/tmp/runtime/mempalace")
            self.assertEqual(loaded.graphify_bin, "/tmp/runtime/graphify")

    def test_install_bundle_writes_user_skill_dir(self) -> None:
        fake_home = Path(self.tmpdir.name) / "home"
        memark_home = fake_home / ".memark-test"
        env = {
            "HOME": str(fake_home),
            "MEMARK_HOME": str(memark_home),
        }

        result = run_cli(
            "install",
            "--platform",
            "codex",
            "--skip-runtime-install",
            "--json",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        bundle_dir = (fake_home / ".agents" / "skills" / "memark").resolve()
        self.assertEqual(payload["targets"][0]["bundle_dir"], str(bundle_dir))
        self.assertTrue((bundle_dir / "SKILL.md").exists())
        self.assertTrue((bundle_dir / "project.md").exists())
        self.assertTrue((bundle_dir / "doctor.md").exists())
        self.assertTrue((bundle_dir / "bin" / "memark").exists())
        self.assertTrue(os.access(bundle_dir / "bin" / "memark", os.X_OK))
        self.assertTrue((bundle_dir / "manifest.json").exists())

    def test_doctor_reports_missing_runtime(self) -> None:
        fake_home = Path(self.tmpdir.name) / "home"
        env = {
            "HOME": str(fake_home),
            "MEMARK_HOME": str(fake_home / ".memark-test"),
        }

        result = run_cli("doctor", "--platform", "codex", cwd=ROOT, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing runtime environment", result.stderr)

    def test_doctor_succeeds_with_fake_runtime_and_bundle(self) -> None:
        fake_home = Path(self.tmpdir.name) / "home"
        memark_home = fake_home / ".memark-test"
        scripts_dir = memark_home / "venv" / "bin"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        python_bin = scripts_dir / "python"
        python_bin.write_text(
            "#!/bin/sh\nif [ \"$1\" = \"-c\" ]; then\n  printf '3.13\\n'\nfi\nexit 0\n",
            encoding="utf-8",
        )
        python_bin.chmod(python_bin.stat().st_mode | stat.S_IEXEC)
        for name in ("memark", "mempalace", "graphify"):
            path = scripts_dir / name
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        env = {
            "HOME": str(fake_home),
            "MEMARK_HOME": str(memark_home),
        }
        install = run_cli(
            "install",
            "--platform",
            "codex",
            "--skip-runtime-install",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(install.returncode, 0, install.stderr)

        doctor = run_cli("doctor", "--platform", "codex", cwd=ROOT, env=env)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIn("Doctor summary: ok", doctor.stdout)

    def test_default_python_command_prefers_supported_interpreter(self) -> None:
        with mock.patch.object(
            install_mod,
            "_python_version",
            side_effect=lambda command: {
                "python3.13": (3, 13),
                "python3.12": (3, 12),
                "python3.11": (3, 11),
                "python3.10": (3, 10),
                "python3": (3, 14),
                "python": (3, 14),
            }.get(command),
        ):
            selected = install_mod._resolve_python_command("python3", "python3.13", "python3.12")
        self.assertEqual(selected, "python3.13")

    def test_doctor_rejects_unsupported_runtime_python(self) -> None:
        fake_home = Path(self.tmpdir.name) / "home"
        memark_home = fake_home / ".memark-test"
        scripts_dir = memark_home / "venv" / "bin"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        python_bin = scripts_dir / "python"
        python_bin.write_text("#!/bin/sh\nprintf '3.14\\n'\n", encoding="utf-8")
        python_bin.chmod(python_bin.stat().st_mode | stat.S_IEXEC)
        for name in ("memark", "mempalace", "graphify"):
            path = scripts_dir / name
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        env = {
            "HOME": str(fake_home),
            "MEMARK_HOME": str(memark_home),
        }
        install = run_cli(
            "install",
            "--platform",
            "codex",
            "--skip-runtime-install",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(install.returncode, 0, install.stderr)

        doctor = run_cli("doctor", "--platform", "codex", cwd=ROOT, env=env)
        self.assertNotEqual(doctor.returncode, 0)
        self.assertIn("unsupported runtime python version", doctor.stderr)

    def test_service_install_status_and_uninstall_manage_launchd_scheduler(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        fake_home = Path(self.tmpdir.name) / "home"
        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        launchctl_log = self.workspace / "launchctl.log"
        state_dir = self.workspace / "launchctl-state"
        state_dir.mkdir(parents=True, exist_ok=True)
        fake_launchctl = fake_bin_dir / "launchctl"
        fake_launchctl.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                LOG_FILE="{launchctl_log}"
                STATE_DIR="{state_dir}"
                cmd="$1"
                shift
                case "$cmd" in
                  bootstrap)
                    plist="$2"
                    touch "$STATE_DIR/$(basename "$plist").loaded"
                    echo "bootstrap $plist" >> "$LOG_FILE"
                    exit 0
                    ;;
                  bootout)
                    target="$2"
                    base=$(basename "$target")
                    rm -f "$STATE_DIR/$base.loaded"
                    echo "bootout $target" >> "$LOG_FILE"
                    exit 0
                    ;;
                  enable)
                    echo "enable $1" >> "$LOG_FILE"
                    exit 0
                    ;;
                  kickstart)
                    echo "kickstart $2" >> "$LOG_FILE"
                    exit 0
                    ;;
                  print)
                    label="${{1##*/}}"
                    if [ -f "$STATE_DIR/$label.plist.loaded" ]; then
                      echo "service = $label"
                      exit 0
                    fi
                    echo "could not find service" >&2
                    exit 113
                    ;;
                esac
                echo "unexpected $cmd" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        fake_launchctl.chmod(fake_launchctl.stat().st_mode | stat.S_IEXEC)
        env = {
            "HOME": str(fake_home),
            "PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", ""),
        }

        install = run_cli(
            "service-install",
            "--workspace",
            str(self.workspace),
            "--scheduler",
            "launchd",
            "--interval-seconds",
            "120",
            "--json",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(install.returncode, 0, install.stderr)
        install_payload = json.loads(install.stdout)
        plist_path = Path(install_payload["plist_path"])
        self.assertTrue(plist_path.exists())
        self.assertEqual(install_payload["scheduler"], "launchd")
        self.assertEqual(install_payload["interval_seconds"], 120)
        self.assertTrue(install_payload["loaded"])
        self.assertIn("automation-run", install_payload["command"])

        status = run_cli(
            "service-status",
            "--workspace",
            str(self.workspace),
            "--scheduler",
            "launchd",
            "--json",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        status_payload = json.loads(status.stdout)
        self.assertTrue(status_payload["installed"])
        self.assertTrue(status_payload["loaded"])
        self.assertEqual(status_payload["plist_path"], str(plist_path))

        uninstall = run_cli(
            "service-uninstall",
            "--workspace",
            str(self.workspace),
            "--scheduler",
            "launchd",
            "--json",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        uninstall_payload = json.loads(uninstall.stdout)
        self.assertTrue(uninstall_payload["removed"])
        self.assertTrue(uninstall_payload["unloaded"])
        self.assertFalse(plist_path.exists())

    def test_service_install_dry_run_does_not_write_plist(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        fake_home = Path(self.tmpdir.name) / "home"
        env = {"HOME": str(fake_home)}

        result = run_cli(
            "service-install",
            "--workspace",
            str(self.workspace),
            "--scheduler",
            "launchd",
            "--dry-run",
            "--json",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(Path(payload["plist_path"]).exists())
        self.assertFalse(payload["loaded"])

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

    def test_query_searches_promoted_and_documents(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        promoted = self.workspace / "corpus" / "memark" / "promoted" / "room-bridge.md"
        promoted.write_text(
            textwrap.dedent(
                """\
                ---
                room_title: "Bridge Governance"
                ---

                # Bridge Governance

                Graphify fallback is code-only today.
                """
            ),
            encoding="utf-8",
        )
        document = self.workspace / "corpus" / "memark" / "documents" / "notes.md"
        document.write_text("# Notes\n\nGraphify fallback is code-only today.\n", encoding="utf-8")

        result = run_cli("query", "graphify fallback", "--workspace", str(self.workspace), cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('[promoted] Bridge Governance', result.stdout)
        self.assertIn('[documents] Notes', result.stdout)

    def test_query_can_filter_scope_and_render_json(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        promoted = self.workspace / "corpus" / "memark" / "promoted" / "room-bridge.md"
        promoted.write_text("# Bridge Governance\n\nSession knowledge lives here.\n", encoding="utf-8")
        imports = self.workspace / "corpus" / "memark" / "imports" / "repo.md"
        imports.parent.mkdir(parents=True, exist_ok=True)
        imports.write_text("# Repo Import\n\nSession knowledge should not show up in promoted-only scope.\n", encoding="utf-8")

        result = run_cli(
            "query",
            "session knowledge",
            "--workspace",
            str(self.workspace),
            "--scope",
            "promoted",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["scopes"], ["promoted"])
        self.assertEqual(len(payload["hits"]), 1)
        self.assertEqual(payload["hits"][0]["scope"], "promoted")
        self.assertEqual(payload["hits"][0]["title"], "Bridge Governance")

    def test_graphify_handoff_renders_prompt_and_command(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        promoted = self.workspace / "corpus" / "memark" / "promoted" / "room-bridge.md"
        promoted.write_text("# Bridge Governance\n\nSession-derived project knowledge.\n", encoding="utf-8")
        document = self.workspace / "corpus" / "memark" / "documents" / "notes.md"
        document.write_text("# Notes\n\nProject notes live here.\n", encoding="utf-8")
        imports = self.workspace / "corpus" / "memark" / "imports" / "paper.md"
        imports.parent.mkdir(parents=True, exist_ok=True)
        imports.write_text("# Imported\n\nExternal material.\n", encoding="utf-8")

        result = run_cli("graphify-handoff", "--workspace", str(self.workspace), cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        corpus_dir = (self.workspace / "corpus" / "memark").resolve()
        self.assertIn(f"Graphify handoff target: {corpus_dir}", result.stdout)
        self.assertIn(f"Recommended command: /graphify {corpus_dir} --update", result.stdout)
        self.assertIn("promoted: 1 files", result.stdout)
        self.assertIn("documents: 1 files", result.stdout)
        self.assertIn("imports: 1 files", result.stdout)
        self.assertIn("Use the Graphify skill, not bare memark build", result.stdout)

    def test_graphify_handoff_can_render_json(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        promoted = self.workspace / "corpus" / "memark" / "promoted" / "room-bridge.md"
        promoted.write_text("# Bridge Governance\n\nSession-derived project knowledge.\n", encoding="utf-8")

        result = run_cli("graphify-handoff", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["project"], "memark")
        self.assertTrue(payload["recommended_command"].endswith(" --update"))
        self.assertIn("Use the Graphify skill", payload["prompt"])
        self.assertEqual(payload["inventories"][0]["scope"], "promoted")

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
        self.assertIn("Graphify step completed", result.stdout)
        self.assertIn("Mode: watch-fallback", result.stdout)
        self.assertIn("graphify.watch", result.stdout)
        self.assertIn("does not prove promoted markdown entered the graph", result.stdout)
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
        staged_dir = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "08"
        staged_matches = sorted(staged_dir.glob("rollout-a--*.md"))
        self.assertEqual(len(staged_matches), 1)
        self.assertFalse(list(staged_dir.glob("rollout-b--*.md")))
        content = staged_matches[0].read_text(encoding="utf-8")
        self.assertIn("Workspace Path:", content)

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
        staged_dir = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "08"
        self.assertEqual(len(list(staged_dir.glob("rollout-a--*.md"))), 2)

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

    def test_project_set_writes_project_registry_entry(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)

        result = run_cli(
            "project-set",
            "--workspace",
            str(self.workspace),
            "--project",
            "MemArk",
            "--path",
            str(ROOT),
            "--sessions-root",
            str(self.workspace / "codex-sessions"),
            "--extra-path",
            str(self.workspace / "worktrees"),
            "--mine-interval-seconds",
            "180",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["project"], "memark")
        self.assertEqual(payload["path"], str(ROOT))
        self.assertEqual(payload["mine_interval_seconds"], 180)
        registry = (self.workspace / ".memark" / "projects.toml").read_text(encoding="utf-8")
        self.assertIn('name = "memark"', registry)
        self.assertIn(f'path = "{ROOT}"', registry)

    def test_worktree_attach_copies_hidden_tool_config(self) -> None:
        source_dir = self.workspace / "repo"
        target_dir = self.workspace / "worktree"
        (source_dir / ".memark").mkdir(parents=True)
        (source_dir / ".codex").mkdir(parents=True)
        (source_dir / ".claude").mkdir(parents=True)
        (source_dir / ".mempalace").mkdir(parents=True)
        (source_dir / ".memark" / "state").mkdir(parents=True)
        (source_dir / ".memark" / "state" / "ledger.json").write_text('{"old":true}\n', encoding="utf-8")
        (source_dir / ".memark" / "config.json").write_text('{"ok":true}\n', encoding="utf-8")
        (source_dir / ".memark" / "projects.toml").write_text("version = 1\n", encoding="utf-8")
        (source_dir / ".codex" / "config.toml").write_text("model = 'gpt-5.4'\n", encoding="utf-8")
        (source_dir / ".claude" / "settings.json").write_text('{"hooks":[]}\n', encoding="utf-8")
        (source_dir / ".mempalace" / "config.toml").write_text("mode = 'convos'\n", encoding="utf-8")
        (source_dir / "AGENTS.md").write_text("# Graphify\n", encoding="utf-8")

        result = run_cli(
            "worktree-attach",
            "--source-dir",
            str(source_dir),
            "--target-dir",
            str(target_dir),
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn(".memark", payload["copied"])
        self.assertIn(".codex", payload["copied"])
        self.assertIn(".claude", payload["copied"])
        self.assertIn(".mempalace", payload["copied"])
        self.assertIn("AGENTS.md", payload["copied"])
        self.assertEqual((target_dir / ".memark" / "config.json").read_text(encoding="utf-8"), '{"ok":true}\n')
        self.assertEqual((target_dir / ".memark" / "projects.toml").read_text(encoding="utf-8"), "version = 1\n")
        self.assertFalse((target_dir / ".memark" / "state").exists())
        self.assertEqual((target_dir / ".codex" / "config.toml").read_text(encoding="utf-8"), "model = 'gpt-5.4'\n")
        self.assertEqual((target_dir / ".claude" / "settings.json").read_text(encoding="utf-8"), '{"hooks":[]}\n')
        self.assertEqual((target_dir / ".mempalace" / "config.toml").read_text(encoding="utf-8"), "mode = 'convos'\n")
        self.assertEqual((target_dir / "AGENTS.md").read_text(encoding="utf-8"), "# Graphify\n")

    def test_worktree_hook_install_auto_attaches_hidden_config_on_git_worktree_add(self) -> None:
        repo_dir = self.workspace / "repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=repo_dir, check=True, text=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "MemArk Test"], cwd=repo_dir, check=True, text=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "memark@example.com"],
            cwd=repo_dir,
            check=True,
            text=True,
            capture_output=True,
        )
        (repo_dir / ".gitignore").write_text(".memark/\n", encoding="utf-8")
        (repo_dir / ".codex").mkdir(parents=True)
        (repo_dir / ".codex" / "config.toml").write_text("model = 'gpt-5.4'\n", encoding="utf-8")
        (repo_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore", ".codex/config.toml", "README.md"], cwd=repo_dir, check=True, text=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, text=True, capture_output=True)
        (repo_dir / ".memark").mkdir(parents=True)
        (repo_dir / ".memark" / "config.json").write_text('{"ok":true}\n', encoding="utf-8")
        (repo_dir / ".memark" / "state").mkdir(parents=True)
        (repo_dir / ".memark" / "state" / "ledger.json").write_text('{"stale":true}\n', encoding="utf-8")

        install = run_cli(
            "worktree-hook-install",
            "--source-dir",
            str(repo_dir),
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(install.returncode, 0, install.stderr)
        payload = json.loads(install.stdout)
        hook_path = Path(payload["hook_path"])
        self.assertTrue(hook_path.exists())

        worktree_dir = self.workspace / "repo-worktree"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), "-b", "test/worktree-auto-attach"],
            cwd=repo_dir,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertTrue((worktree_dir / ".memark" / "config.json").exists())
        self.assertEqual((worktree_dir / ".memark" / "config.json").read_text(encoding="utf-8"), '{"ok":true}\n')
        self.assertFalse((worktree_dir / ".memark" / "state").exists())

    def test_projects_run_syncs_and_mines_configured_project(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "codex-sessions"
        session_file = sessions_root / "2026" / "04" / "09" / "rollout-a.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "session_meta",
                            "payload": {
                                "id": "sess-a",
                                "cwd": str(ROOT),
                                "timestamp": "2026-04-09T12:00:00Z",
                            },
                        }
                    ),
                    json.dumps({"type": "message", "payload": {"text": "hello"}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        run_cli(
            "project-set",
            "--workspace",
            str(self.workspace),
            "--project",
            "MemArk",
            "--root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            cwd=ROOT,
        )

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        counter_file = self.workspace / "mine-count.txt"
        fake_mempalace.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                COUNT_FILE="{counter_file}"
                count=0
                if [ -f "$COUNT_FILE" ]; then
                  count=$(cat "$COUNT_FILE")
                fi
                count=$((count + 1))
                printf '%s' "$count" > "$COUNT_FILE"
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli("projects-run", "--workspace", str(self.workspace), "--json", cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["sync"]["copied"], 1)
        self.assertTrue(payload[0]["mined"])
        self.assertIsInstance(payload[0]["mine_started_at"], str)
        self.assertIsInstance(payload[0]["mine_finished_at"], str)
        self.assertGreaterEqual(payload[0]["mine_elapsed_seconds"], 0)
        self.assertEqual(counter_file.read_text(encoding="utf-8"), "1")
        staged_dir = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09"
        self.assertEqual(len(list(staged_dir.glob("rollout-a--*.md"))), 1)

        second = run_cli("projects-run", "--workspace", str(self.workspace), "--json", cwd=ROOT, env=env)
        self.assertEqual(second.returncode, 0, second.stderr)
        second_payload = json.loads(second.stdout)
        self.assertFalse(second_payload[0]["mined"])
        self.assertEqual(second_payload[0]["mine_skipped_reason"], "no_pending_changes")
        self.assertEqual(counter_file.read_text(encoding="utf-8"), "1")

    def test_projects_run_defers_mine_until_interval_elapses(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "codex-sessions"
        session_file = sessions_root / "2026" / "04" / "09" / "rollout-a.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "sess-a",
                        "cwd": str(ROOT),
                        "timestamp": "2026-04-09T12:00:00Z",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_cli(
            "project-set",
            "--workspace",
            str(self.workspace),
            "--project",
            "MemArk",
            "--root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            "--mine-interval-seconds",
            "3600",
            cwd=ROOT,
        )

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        counter_file = self.workspace / "mine-count.txt"
        fake_mempalace.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                COUNT_FILE="{counter_file}"
                count=0
                if [ -f "$COUNT_FILE" ]; then
                  count=$(cat "$COUNT_FILE")
                fi
                count=$((count + 1))
                printf '%s' "$count" > "$COUNT_FILE"
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        first = run_cli("projects-run", "--workspace", str(self.workspace), "--json", cwd=ROOT, env=env)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(counter_file.read_text(encoding="utf-8"), "1")

        session_file.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "session_meta",
                            "payload": {
                                "id": "sess-a",
                                "cwd": str(ROOT),
                                "timestamp": "2026-04-09T12:00:00Z",
                            },
                        }
                    ),
                    json.dumps({"type": "message", "payload": {"text": "updated"}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        second = run_cli("projects-run", "--workspace", str(self.workspace), "--json", cwd=ROOT, env=env)
        self.assertEqual(second.returncode, 0, second.stderr)
        second_payload = json.loads(second.stdout)
        self.assertFalse(second_payload[0]["mined"])
        self.assertEqual(second_payload[0]["mine_skipped_reason"], "mine_interval_not_elapsed")
        self.assertTrue(second_payload[0]["pending_mine"])
        self.assertEqual(counter_file.read_text(encoding="utf-8"), "1")

    def test_projects_run_persists_pending_state_before_failed_mine(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "codex-sessions"
        session_file = sessions_root / "2026" / "04" / "09" / "rollout-a.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "sess-a",
                        "cwd": str(ROOT),
                        "timestamp": "2026-04-09T12:00:00Z",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_cli(
            "project-set",
            "--workspace",
            str(self.workspace),
            "--project",
            "MemArk",
            "--root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            cwd=ROOT,
        )

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        fake_mempalace.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                echo "simulated mine failure" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli("projects-run", "--workspace", str(self.workspace), cwd=ROOT, env=env)
        self.assertNotEqual(result.returncode, 0)
        state = json.loads((self.workspace / ".memark" / "state" / "projects-run.json").read_text(encoding="utf-8"))
        self.assertTrue(state["memark"]["pending_mine"])
        self.assertIsNone(state["memark"]["last_mined_at"])
        self.assertIsInstance(state["memark"]["last_run_at"], str)

    def test_projects_list_includes_runtime_state(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "codex-sessions"
        session_file = sessions_root / "2026" / "04" / "09" / "rollout-a.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "sess-a",
                        "cwd": str(ROOT),
                        "timestamp": "2026-04-09T12:00:00Z",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_cli(
            "project-set",
            "--workspace",
            str(self.workspace),
            "--project",
            "MemArk",
            "--root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            cwd=ROOT,
        )

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        fake_mempalace.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        run_cli("projects-run", "--workspace", str(self.workspace), cwd=ROOT, env=env)
        json_result = run_cli("projects-list", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertEqual(len(payload), 1)
        self.assertFalse(payload[0]["pending_mine"])
        self.assertIsInstance(payload[0]["last_run_at"], str)
        self.assertIsInstance(payload[0]["last_mined_at"], str)

        text_result = run_cli("projects-list", "--workspace", str(self.workspace), cwd=ROOT)
        self.assertEqual(text_result.returncode, 0, text_result.stderr)
        self.assertIn("pending_mine=False", text_result.stdout)
        self.assertIn("last_run_at=", text_result.stdout)
        self.assertIn("last_mined_at=", text_result.stdout)

    def test_projects_run_non_json_reports_phase_progress(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "codex-sessions"
        session_file = sessions_root / "2026" / "04" / "09" / "rollout-a.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "sess-a",
                        "cwd": str(ROOT),
                        "timestamp": "2026-04-09T12:00:00Z",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_cli(
            "project-set",
            "--workspace",
            str(self.workspace),
            "--project",
            "MemArk",
            "--root",
            str(ROOT),
            "--sessions-root",
            str(sessions_root),
            cwd=ROOT,
        )

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        fake_mempalace.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli("projects-run", "--workspace", str(self.workspace), cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Running project: memark", result.stdout)
        self.assertIn("Mine: starting", result.stdout)
        self.assertIn("Mine: completed attempts=1", result.stdout)
        self.assertIn("Mine started at:", result.stdout)
        self.assertIn("Mine elapsed seconds:", result.stdout)

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

    def test_mempalace_mine_retries_on_lock_error(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        staging_file = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09" / "rollout-a.jsonl"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text('{"type":"session_meta","payload":{"cwd":"%s"}}\n' % ROOT, encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        counter_file = self.workspace / "retry-count.txt"
        fake_mempalace.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                COUNT_FILE="{counter_file}"
                count=0
                if [ -f "$COUNT_FILE" ]; then
                  count=$(cat "$COUNT_FILE")
                fi
                count=$((count + 1))
                printf '%s' "$count" > "$COUNT_FILE"
                if [ "$count" -eq 1 ]; then
                  echo "sqlite3.OperationalError: database is locked" >&2
                  exit 1
                fi
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli(
            "mempalace-mine",
            "--workspace",
            str(self.workspace),
            "--retry-delay-seconds",
            "0",
            "--json",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["attempts"], 2)
        self.assertIsInstance(payload["started_at"], str)
        self.assertIsInstance(payload["finished_at"], str)
        self.assertGreaterEqual(payload["elapsed_seconds"], 0)
        self.assertEqual(counter_file.read_text(encoding="utf-8"), "2")

    def test_mempalace_mine_text_output_includes_timing(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        staging_file = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09" / "rollout-a.jsonl"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text('{"type":"session_meta","payload":{"cwd":"%s"}}\n' % ROOT, encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        fake_mempalace.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli("mempalace-mine", "--workspace", str(self.workspace), cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Started at:", result.stdout)
        self.assertIn("Finished at:", result.stdout)
        self.assertIn("Elapsed seconds:", result.stdout)

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

    def test_palace_status_reports_files_and_drawers(self) -> None:
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
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (1, 'seg-a', 'drawer_status', X'01')"
            )
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, "chroma:document", "Status: palace has one tracked drawer.", None, None, None),
                    (1, "wing", "codex_project", None, None, None),
                    (1, "room", "status_room", None, None, None),
                    (1, "ingest_mode", "convos", None, None, None),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli("palace-status", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["exists"])
        self.assertEqual(payload["files"], 1)
        self.assertEqual(payload["drawers"], 1)
        self.assertEqual(payload["wings"], 1)
        self.assertEqual(payload["rooms"], 1)

    def test_palace_clean_resets_directory(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        nested = palace_dir / "subdir" / "note.txt"
        nested.parent.mkdir(parents=True, exist_ok=True)
        nested.write_text("stale\n", encoding="utf-8")

        result = run_cli("palace-clean", "--workspace", str(self.workspace), "--json", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["cleaned"])
        self.assertTrue(palace_dir.exists())
        self.assertEqual(list(palace_dir.iterdir()), [])

    def test_palace_rebuild_cleans_then_mines(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        staging_file = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09" / "rollout-a.jsonl"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text('{"type":"session_meta","payload":{"cwd":"%s"}}\n' % ROOT, encoding="utf-8")

        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        stale = palace_dir / "old.txt"
        stale.write_text("old\n", encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        log_file = self.workspace / "palace-rebuild.log"
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

        result = run_cli("palace-rebuild", "--workspace", str(self.workspace), "--json", cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["clean_first"])
        self.assertFalse(stale.exists())
        self.assertIn("--mode", log_file.read_text(encoding="utf-8"))

    def test_palace_retry_reports_attempts_after_lock_retry(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        staging_file = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09" / "rollout-a.jsonl"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text('{"type":"session_meta","payload":{"cwd":"%s"}}\n' % ROOT, encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        counter_file = self.workspace / "palace-retry-count.txt"
        fake_mempalace.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                COUNT_FILE="{counter_file}"
                count=0
                if [ -f "$COUNT_FILE" ]; then
                  count=$(cat "$COUNT_FILE")
                fi
                count=$((count + 1))
                printf '%s' "$count" > "$COUNT_FILE"
                if [ "$count" -eq 1 ]; then
                  echo "database is locked" >&2
                  exit 1
                fi
                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli(
            "palace-retry",
            "--workspace",
            str(self.workspace),
            "--retry-delay-seconds",
            "0",
            "--json",
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["attempts"], 2)
        self.assertEqual(counter_file.read_text(encoding="utf-8"), "2")

    def test_palace_retry_runs_without_cleaning(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        staging_file = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09" / "rollout-a.jsonl"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text('{"type":"session_meta","payload":{"cwd":"%s"}}\n' % ROOT, encoding="utf-8")

        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        keep_file = palace_dir / "keep.txt"
        keep_file.write_text("keep\n", encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        log_file = self.workspace / "palace-retry.log"
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

        result = run_cli("palace-retry", "--workspace", str(self.workspace), "--json", cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["clean_first"])
        self.assertTrue(keep_file.exists())
        self.assertIn(str(palace_dir), log_file.read_text(encoding="utf-8"))

    def test_mempalace_mine_reports_rebuild_hint_for_incompatible_palace(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        staging_file = self.workspace / ".memark" / "staging" / "memark" / "sessions" / "2026" / "04" / "09" / "rollout-a.md"
        staging_file.parent.mkdir(parents=True, exist_ok=True)
        staging_file.write_text("Source Path: /tmp/example.jsonl\nWorkspace Path: /tmp/project\n", encoding="utf-8")

        fake_bin_dir = self.workspace / "bin"
        fake_bin_dir.mkdir()
        fake_mempalace = fake_bin_dir / "mempalace"
        fake_mempalace.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                echo "KeyError: '_type'" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        fake_mempalace.chmod(fake_mempalace.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", "")}

        result = run_cli("mempalace-mine", "--workspace", str(self.workspace), cwd=ROOT, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale or incompatible palace directory", result.stderr)
        self.assertIn("memark palace-rebuild", result.stderr)

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
                    (3, "seg-c", "drawer_auth_3"),
                ],
            )
            metadata_rows = [
                (1, "chroma:document", "Decision: adopt Clerk for auth and write an ADR.", None, None, None),
                (1, "wing", "codex_project", None, None, None),
                (1, "room", "auth_decisions", None, None, None),
                (1, "source_file", "/tmp/demo/rollout-a--111-aaaaaaaaaaaa.jsonl", None, None, None),
                (1, "filed_at", "2026-04-09T02:10:00Z", None, None, None),
                (1, "ingest_mode", "convos", None, None, None),
                (2, "chroma:document", "Decision update: use Clerk plus staged fallback migration.", None, None, None),
                (2, "wing", "codex_project", None, None, None),
                (2, "room", "auth_decisions", None, None, None),
                (2, "source_file", "/tmp/demo/rollout-a--222-bbbbbbbbbbbb.jsonl", None, None, None),
                (2, "filed_at", "2026-04-09T02:11:00Z", None, None, None),
                (2, "ingest_mode", "convos", None, None, None),
                (3, "chroma:document", "Migration checklist: keep billing internal and stage rollout.", None, None, None),
                (3, "wing", "codex_project", None, None, None),
                (3, "room", "auth_decisions", None, None, None),
                (3, "source_file", "/tmp/demo/rollout-b--333-cccccccccccc.jsonl", None, None, None),
                (3, "filed_at", "2026-04-09T02:12:00Z", None, None, None),
                (3, "ingest_mode", "convos", None, None, None),
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
        self.assertEqual(payload["drawers"], 3)
        self.assertEqual(len(payload["packages"]), 1)
        package = payload["packages"][0]
        self.assertEqual(package["wing_id"], "project/memark")
        self.assertEqual(package["room_id"], "auth-decisions")
        self.assertEqual(len(package["drawer_refs"]), 2)
        self.assertEqual(package["drawer_refs"][0]["source_uri"], "/tmp/demo/rollout-a.jsonl")
        self.assertEqual(package["drawer_refs"][1]["source_uri"], "/tmp/demo/rollout-b.jsonl")
        self.assertEqual(package["source_timestamps"]["start"], "2026-04-09T02:11:00Z")
        self.assertEqual(package["source_timestamps"]["end"], "2026-04-09T02:12:00Z")

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

    def test_palace_package_can_group_by_session(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        palace_dir = self.workspace / ".memark" / "palaces" / "memark"
        snapshot_dir = self.workspace / ".memark" / "staging" / "memark" / "sessions"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "rollout-alpha--111-aaaaaaaaaaaa.md").write_text(
            "Source Path: /tmp/demo/rollout-alpha.jsonl\n"
            f"Workspace Path: {self.workspace}\n"
            "Session ID: alpha\n"
            "Session Timestamp: 2026-04-09T02:10:00Z\n\n"
            "> Continue\n\n"
            "> Design the MemArk install flow for production skill bundles.\n",
            encoding="utf-8",
        )
        (snapshot_dir / "rollout-alpha--222-bbbbbbbbbbbb.md").write_text(
            "Source Path: /tmp/demo/rollout-alpha.jsonl\n"
            f"Workspace Path: {self.workspace}\n"
            "Session ID: alpha\n"
            "Session Timestamp: 2026-04-09T02:11:00Z\n\n"
            "> Continue\n\n"
            "> Design the MemArk install flow for production skill bundles.\n",
            encoding="utf-8",
        )
        (snapshot_dir / "rollout-beta--333-cccccccccccc.md").write_text(
            "Source Path: /tmp/demo/rollout-beta.jsonl\n"
            f"Workspace Path: {self.workspace}\n"
            "Session ID: beta\n"
            "Session Timestamp: 2026-04-09T02:12:00Z\n\n"
            "> Compare MemPalace search and Graphify query for project AI consumption.\n",
            encoding="utf-8",
        )
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
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (?, ?, ?, ?)",
                [
                    (1, "seg-a", "drawer_a", b"\x01"),
                    (2, "seg-b", "drawer_b", b"\x02"),
                    (3, "seg-c", "drawer_c", b"\x03"),
                ],
            )
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, "chroma:document", "Session A first decision.", None, None, None),
                    (1, "wing", "sessions", None, None, None),
                    (1, "room", "technical", None, None, None),
                    (1, "source_file", str(snapshot_dir / "rollout-alpha--111-aaaaaaaaaaaa.md"), None, None, None),
                    (1, "filed_at", "2026-04-09T02:10:00Z", None, None, None),
                    (1, "ingest_mode", "convos", None, None, None),
                    (2, "chroma:document", "Session A follow-up.", None, None, None),
                    (2, "wing", "sessions", None, None, None),
                    (2, "room", "technical", None, None, None),
                    (2, "source_file", str(snapshot_dir / "rollout-alpha--222-bbbbbbbbbbbb.md"), None, None, None),
                    (2, "filed_at", "2026-04-09T02:11:00Z", None, None, None),
                    (2, "ingest_mode", "convos", None, None, None),
                    (3, "chroma:document", "Session B decision.", None, None, None),
                    (3, "wing", "sessions", None, None, None),
                    (3, "room", "technical", None, None, None),
                    (3, "source_file", str(snapshot_dir / "rollout-beta--333-cccccccccccc.md"), None, None, None),
                    (3, "filed_at", "2026-04-09T02:12:00Z", None, None, None),
                    (3, "ingest_mode", "convos", None, None, None),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli(
            "palace-package",
            "--workspace",
            str(self.workspace),
            "--group-by",
            "session",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["group_by"], "session")
        self.assertEqual(len(payload["packages"]), 2)
        room_ids = {item["room_id"] for item in payload["packages"]}
        self.assertEqual(room_ids, {"technical-rollout-alpha", "technical-rollout-beta"})
        titles = {item["room_id"]: item["room_title"] for item in payload["packages"]}
        self.assertEqual(titles["technical-rollout-alpha"], "Design the MemArk install flow for production skill bundles.")
        self.assertEqual(
            titles["technical-rollout-beta"],
            "Compare MemPalace search and Graphify query for project AI consumption.",
        )

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

    def test_automation_run_closes_feed_process_consume_loop_without_build(self) -> None:
        run_cli("init", str(self.workspace), "--project", "MemArk", cwd=ROOT)
        sessions_root = self.workspace / "sessions"
        sessions_root.mkdir(parents=True, exist_ok=True)
        project_docs = self.workspace / "docs"
        project_docs.mkdir(parents=True, exist_ok=True)
        (project_docs / "plan.md").write_text("# Plan\n\nDecision: automate the full memark cycle.\n", encoding="utf-8")
        raw_docs = project_docs / "raw"
        raw_docs.mkdir(parents=True, exist_ok=True)
        (raw_docs / "draft.md").write_text("# Draft\n\nRisk: stale archive should not feed automation.\n", encoding="utf-8")
        build_docs = self.workspace / "build"
        build_docs.mkdir(parents=True, exist_ok=True)
        (build_docs / "generated.md").write_text("# Generated\n\nDecision: generated output should stay out.\n", encoding="utf-8")
        experiments_docs = self.workspace / ".experiments"
        experiments_docs.mkdir(parents=True, exist_ok=True)
        (experiments_docs / "scratch.md").write_text("# Scratch\n\nRisk: experiments should stay out.\n", encoding="utf-8")
        pytest_docs = self.workspace / ".pytest_cache"
        pytest_docs.mkdir(parents=True, exist_ok=True)
        (pytest_docs / "README.md").write_text("# Cache\n\nRisk: cache docs should stay out.\n", encoding="utf-8")
        egg_info = self.workspace / "memark.egg-info"
        egg_info.mkdir(parents=True, exist_ok=True)
        (egg_info / "PKG-INFO").write_text("Metadata-Version: 2.1\n", encoding="utf-8")
        run_cli(
            "project-set",
            "--workspace",
            str(self.workspace),
            "--project",
            "MemArk",
            "--path",
            str(self.workspace),
            "--sessions-root",
            str(sessions_root),
            "--json",
            cwd=ROOT,
        )

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
                "INSERT INTO embeddings (id, segment_id, embedding_id, seq_id) VALUES (1, 'seg-a', 'drawer_auto', X'01')"
            )
            conn.executemany(
                """
                INSERT INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, "chroma:document", "Decision: installation should finish the setup. Risk: manual follow-up breaks adoption.", None, None, None),
                    (1, "wing", "codex_project", None, None, None),
                    (1, "room", "automation_loop", None, None, None),
                    (1, "source_file", str(self.workspace / ".memark" / "staging" / "memark" / "sessions" / "rollout-auto.md"), None, None, None),
                    (1, "filed_at", "2026-04-10T03:00:00Z", None, None, None),
                    (1, "ingest_mode", "convos", None, None, None),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        result = run_cli(
            "automation-run",
            "--workspace",
            str(self.workspace),
            "--no-build",
            "--json",
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload), 1)
        project = payload[0]
        self.assertEqual(project["project"], "memark")
        self.assertEqual(project["documents"]["copied"], 1)
        self.assertEqual(project["packages"], 1)
        self.assertEqual(project["graphify"]["status"], "not_requested")
        self.assertEqual(len(project["artifacts"]), 5)

        promoted = self.workspace / "corpus" / "memark" / "promoted" / "room-automation-loop-rollout-auto.md"
        self.assertTrue(promoted.exists())
        copied_doc = self.workspace / "corpus" / "memark" / "documents" / "docs" / "plan.md"
        self.assertTrue(copied_doc.exists())
        self.assertFalse((self.workspace / "corpus" / "memark" / "documents" / "docs" / "raw" / "draft.md").exists())
        self.assertFalse((self.workspace / "corpus" / "memark" / "documents" / "build" / "generated.md").exists())
        self.assertFalse((self.workspace / "corpus" / "memark" / "documents" / ".experiments" / "scratch.md").exists())
        self.assertFalse((self.workspace / "corpus" / "memark" / "documents" / ".pytest_cache" / "README.md").exists())
        self.assertFalse((self.workspace / "corpus" / "memark" / "documents" / "memark.egg-info" / "PKG-INFO").exists())
        imports_dir = self.workspace / "corpus" / "memark" / "imports" / "automation"
        self.assertTrue((imports_dir / "latest-summary.md").exists())
        self.assertTrue((imports_dir / "decisions-digest.md").exists())
        self.assertTrue((imports_dir / "risks-digest.md").exists())
        self.assertTrue((imports_dir / "ai-context.md").exists())
        self.assertTrue((imports_dir / "graphify-status.md").exists())


if __name__ == "__main__":
    unittest.main()
