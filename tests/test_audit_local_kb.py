from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_local_kb.py"
SPEC = importlib.util.spec_from_file_location("audit_local_kb", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


class LocalKnowledgeBaseAuditTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "private-wiki"
        state = project / ".llm-wiki"
        state.mkdir(parents=True)
        (state / "project.json").write_text("{}\n", encoding="utf-8")
        (state / "knowledge-health.json").write_text(
            json.dumps(
                {
                    "status": "quality_warning",
                    "generated_at": "2026-01-01T00:00:00Z",
                    "search": {"available": True, "passed": 3, "total": 4},
                }
            ),
            encoding="utf-8",
        )
        (state / "vector-index-status.json").write_text(
            json.dumps({"result": "success", "indexed_pages": 2, "indexed_chunks": 5}),
            encoding="utf-8",
        )
        (state / "codex-graph-manifest.json").write_text(
            json.dumps({"managed_pages": 2, "changed": 0, "removed": 0}),
            encoding="utf-8",
        )
        (state / "daily-sync-status.json").write_text(
            json.dumps({"result": "success", "duration_seconds": 8}),
            encoding="utf-8",
        )
        (project / "wiki").mkdir()
        (project / "wiki" / "one.md").write_text("private facts", encoding="utf-8")
        (project / "raw").mkdir()
        (project / "raw" / "source.txt").write_text("raw private text", encoding="utf-8")
        private = project / "archive" / "private-finance"
        private.mkdir(parents=True)
        (private / "record.csv").write_text("private record", encoding="utf-8")
        return project

    def test_snapshot_contains_counts_but_no_content_paths_or_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.make_project(Path(directory))

            snapshot = audit.sanitized_snapshot(project)
            serialized = json.dumps(snapshot, ensure_ascii=False)

            self.assertEqual(snapshot["counts"]["wiki_markdown_pages"], 1)
            self.assertEqual(snapshot["counts"]["raw_source_files"], 1)
            self.assertEqual(snapshot["counts"]["private_archive_files"], 1)
            self.assertFalse(snapshot["content_included"])
            self.assertFalse(snapshot["filenames_included"])
            self.assertNotIn(str(project), serialized)
            self.assertNotIn("private facts", serialized)
            self.assertNotIn("record.csv", serialized)

    def test_rejects_non_wiki_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "not an LLM Wiki"):
                audit.sanitized_snapshot(Path(directory))

    def test_output_must_stay_outside_private_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.make_project(Path(directory))
            with redirect_stderr(io.StringIO()):
                exit_code = audit.main([str(project), "--output", str(project / "public.json")])
            self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
