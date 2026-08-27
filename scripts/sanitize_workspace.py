#!/usr/bin/env python3
"""Scan a workspace and export a conservative, text-only sanitized copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Match, Pattern


MAX_TEXT_BYTES = 2 * 1024 * 1024
TEXT_EXTENSIONS = {
    ".c", ".cc", ".conf", ".cpp", ".css", ".csv", ".env.example", ".go",
    ".h", ".hpp", ".html", ".ini", ".java", ".js", ".json", ".jsx",
    ".kt", ".kts", ".md", ".mdx", ".mjs", ".php", ".properties", ".py",
    ".rb", ".rs", ".scss", ".sh", ".sql", ".swift", ".toml", ".ts",
    ".tsx", ".txt", ".xml", ".yaml", ".yml", ".zsh",
}
TEXT_FILENAMES = {"Dockerfile", "LICENSE", "Makefile", "Procfile"}
DEFAULT_IGNORES = {
    ".git", ".hg", ".idea", ".svn", ".venv", ".vscode", "__pycache__",
    "backups", "build", "coverage", "dist", "node_modules", "raw", "tmp",
    "workspace-sanitized",
}
SEVERITY_RANK = {"none": 99, "medium": 1, "high": 2, "critical": 3}


@dataclass(frozen=True)
class Rule:
    name: str
    severity: str
    pattern: Pattern[str]
    placeholder: str
    replacement: Callable[[Match[str], str], str] | None = None


@dataclass(frozen=True)
class Finding:
    file: str
    rule: str
    severity: str
    count: int
    location: str = "content"


def _credential_replacement(match: Match[str], mode: str) -> str:
    key = match.group(1)
    value = match.group(2)
    return f"{key}=<{token_for('CREDENTIAL', value, mode)}>"


def _home_replacement(match: Match[str], mode: str) -> str:
    del match, mode
    return "${HOME}"


def _windows_home_replacement(match: Match[str], mode: str) -> str:
    del match, mode
    return "%USERPROFILE%"


PRIVATE_KEY_MARKER = "-----BEGIN" + " PRIVATE KEY-----"
RULES = (
    Rule("private-key", "critical", re.compile(re.escape(PRIVATE_KEY_MARKER)), "PRIVATE_KEY"),
    Rule("github-token", "critical", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,255}\b"), "GITHUB_TOKEN"),
    Rule("openai-key", "critical", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"), "OPENAI_KEY"),
    Rule("aws-access-key", "critical", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "AWS_ACCESS_KEY"),
    Rule("bearer-token", "critical", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}"), "BEARER_TOKEN"),
    Rule(
        "credential-assignment",
        "critical",
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)"
            r"\s*[:=]\s*[\"']?([^\s,\"';}{]{6,})[\"']?"
        ),
        "CREDENTIAL",
        _credential_replacement,
    ),
    Rule("email", "high", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "EMAIL"),
    Rule("cn-phone", "high", re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)"), "PHONE"),
    Rule(
        "macos-home-path",
        "high",
        re.compile(r"/Users/[A-Za-z0-9._-]+(?=/|\b)"),
        "HOME_PATH",
        _home_replacement,
    ),
    Rule(
        "windows-home-path",
        "high",
        re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+(?=\\|\b)", re.I),
        "HOME_PATH",
        _windows_home_replacement,
    ),
)


def token_for(label: str, value: str, mode: str) -> str:
    if mode == "hash":
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
        return f"REDACTED:{label}:{digest}"
    return f"REDACTED:{label}"


def replacement_for(rule: Rule, match: Match[str], mode: str) -> str:
    if rule.replacement:
        return rule.replacement(match, mode)
    return f"<{token_for(rule.placeholder, match.group(0), mode)}>"


def redact_text(text: str, mode: str = "placeholder") -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    output = text
    for rule in RULES:
        output, count = rule.pattern.subn(lambda match: replacement_for(rule, match, mode), output)
        if count:
            counts[rule.name] = count
    return output, counts


def is_text_file(path: Path) -> bool:
    if path.name in TEXT_FILENAMES:
        return True
    if path.name.endswith(".env.example"):
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def should_ignore(relative: Path, extra_ignores: set[str]) -> bool:
    ignored = DEFAULT_IGNORES | extra_ignores
    return any(part in ignored for part in relative.parts)


def iter_text_files(root: Path, extra_ignores: set[str]) -> Iterable[tuple[Path, Path]]:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if should_ignore(relative, extra_ignores):
            continue
        if path.is_symlink() or not path.is_file() or not is_text_file(path):
            continue
        try:
            if path.stat().st_size > MAX_TEXT_BYTES:
                continue
        except OSError:
            continue
        yield path, relative


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def scan_workspace(root: Path, extra_ignores: set[str] | None = None) -> tuple[list[Finding], dict[str, int]]:
    extra_ignores = extra_ignores or set()
    findings: list[Finding] = []
    scanned_files = 0
    skipped_unreadable = 0
    for path, relative in iter_text_files(root, extra_ignores):
        text = read_text(path)
        if text is None:
            skipped_unreadable += 1
            continue
        scanned_files += 1
        for rule in RULES:
            count = sum(1 for _ in rule.pattern.finditer(text))
            if count:
                findings.append(Finding(relative.as_posix(), rule.name, rule.severity, count))

        relative_text = relative.as_posix()
        for rule in RULES:
            if rule.name not in {"email", "cn-phone", "macos-home-path", "windows-home-path"}:
                continue
            count = sum(1 for _ in rule.pattern.finditer(relative_text))
            if count:
                findings.append(Finding(relative_text, rule.name, rule.severity, count, "path"))
    return findings, {"scanned_files": scanned_files, "skipped_unreadable": skipped_unreadable}


def validate_roots(root: Path, output: Path | None = None) -> tuple[Path, Path | None]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"workspace is not a directory: {root}")
    if output is None:
        return root, None
    output = output.expanduser().resolve()
    if output == root or root in output.parents:
        raise ValueError("output must be outside the source workspace")
    if output.exists() and any(output.iterdir()):
        raise ValueError("output directory must not exist or must be empty")
    return root, output


def export_workspace(root: Path, output: Path, mode: str, extra_ignores: set[str]) -> dict[str, object]:
    root, resolved_output = validate_roots(root, output)
    assert resolved_output is not None
    resolved_output.mkdir(parents=True, exist_ok=True)
    files_written = 0
    replacements: dict[str, int] = {}
    skipped_unreadable = 0

    for path, relative in iter_text_files(root, extra_ignores):
        text = read_text(path)
        if text is None:
            skipped_unreadable += 1
            continue
        redacted, counts = redact_text(text, mode)
        destination = resolved_output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(redacted, encoding="utf-8")
        files_written += 1
        for name, count in counts.items():
            replacements[name] = replacements.get(name, 0) + count

    manifest = {
        "schema_version": 1,
        "source_included": False,
        "mode": mode,
        "files_written": files_written,
        "skipped_unreadable": skipped_unreadable,
        "binary_policy": "skipped",
        "symlink_policy": "skipped",
        "replacement_counts": replacements,
        "claim_boundary": "Counts cover configured rules and readable text files only.",
    }
    (resolved_output / ".redaction-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def should_fail(findings: list[Finding], threshold: str) -> bool:
    if threshold == "none":
        return False
    minimum = SEVERITY_RANK[threshold]
    return any(SEVERITY_RANK[item.severity] >= minimum for item in findings)


def print_scan(findings: list[Finding], stats: dict[str, int], json_output: bool) -> None:
    summary = {
        **stats,
        "finding_groups": len(findings),
        "finding_count": sum(item.count for item in findings),
        "findings": [asdict(item) for item in findings],
        "snippets_included": False,
        "claim_boundary": "No match means no configured rule matched; it is not proof of zero risk.",
    }
    if json_output:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print(f"Scanned files: {summary['scanned_files']}")
    print(f"Findings: {summary['finding_count']} across {summary['finding_groups']} file/rule groups")
    for finding in findings:
        print(f"- [{finding.severity}] {finding.file} :: {finding.rule} x{finding.count} ({finding.location})")
    print("Boundary: no match is not proof of zero risk; review semantics and binary metadata manually.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="scan readable text without modifying files")
    scan.add_argument("workspace", type=Path)
    scan.add_argument("--ignore", action="append", default=[], help="additional path component to ignore")
    scan.add_argument("--fail-on", choices=SEVERITY_RANK, default="none")
    scan.add_argument("--json", action="store_true", dest="json_output")

    export = subparsers.add_parser("export", help="write a sanitized text-only copy to a new directory")
    export.add_argument("workspace", type=Path)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--ignore", action="append", default=[], help="additional path component to ignore")
    export.add_argument("--mode", choices=("placeholder", "hash"), default="placeholder")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "scan":
            root, _ = validate_roots(args.workspace)
            findings, stats = scan_workspace(root, set(args.ignore))
            print_scan(findings, stats, args.json_output)
            return 2 if should_fail(findings, args.fail_on) else 0

        manifest = export_workspace(args.workspace, args.output, args.mode, set(args.ignore))
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
