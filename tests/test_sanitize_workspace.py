from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "sanitize_workspace.py"
SPEC = importlib.util.spec_from_file_location("sanitize_workspace", SCRIPT)
assert SPEC and SPEC.loader
sanitize = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sanitize
SPEC.loader.exec_module(sanitize)


class SanitizerTests(unittest.TestCase):
    def test_redacts_supported_categories_without_echoing_values(self) -> None:
        email = "owner" + "@" + "example.test"
        phone = "138" + "0013" + "8000"
        credential = "value_" + "only_for_test"
        home_path = "/".join(("", "Users", "demo", "private"))
        source = f"email={email}\nphone={phone}\napi_key={credential}\n{home_path}"

        output, counts = sanitize.redact_text(source)

        self.assertNotIn(email, output)
        self.assertNotIn(phone, output)
        self.assertNotIn(credential, output)
        self.assertNotIn("/".join(("", "Users", "demo")), output)
        self.assertIn("<REDACTED:EMAIL>", output)
        self.assertIn("${HOME}/private", output)
        self.assertEqual(counts["email"], 1)
        self.assertEqual(counts["cn-phone"], 1)

    def test_export_writes_new_text_only_copy_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            output = base / "sanitized"
            source.mkdir()
            email = "reader" + "@" + "example.test"
            (source / "notes.md").write_text(f"contact: {email}\n", encoding="utf-8")
            (source / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

            manifest = sanitize.export_workspace(source, output, "placeholder", set())

            self.assertTrue((output / "notes.md").exists())
            self.assertFalse((output / "photo.png").exists())
            self.assertNotIn(email, (output / "notes.md").read_text(encoding="utf-8"))
            self.assertTrue((output / ".redaction-manifest.json").exists())
            self.assertEqual(manifest["binary_policy"], "skipped")

    def test_refuses_output_inside_source_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            with self.assertRaisesRegex(ValueError, "outside"):
                sanitize.validate_roots(source, source / "public")

    def test_scan_report_contains_no_sensitive_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            secret_value = "credential_" + "only_for_test"
            (source / "config.txt").write_text(f"password={secret_value}\n", encoding="utf-8")

            findings, stats = sanitize.scan_workspace(source)

            self.assertEqual(stats["scanned_files"], 1)
            serialized = repr(findings)
            self.assertNotIn(secret_value, serialized)
            self.assertTrue(any(item.rule == "credential-assignment" for item in findings))


if __name__ == "__main__":
    unittest.main()
