#!/usr/bin/env python3
"""Create a content-free public snapshot of a local LLM Wiki project."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ZONE_POLICY = (
    {
        "zone": "source",
        "label": "原始资料层",
        "examples": ["raw/sources/", "raw/assets/"],
        "decision": "local_only",
        "reason": "保留来源证据，不作为公开产物。",
    },
    {
        "zone": "private_archive",
        "label": "私密档案层",
        "examples": ["archive/private-*/"],
        "decision": "never_publish",
        "reason": "财务、健康、客户与身份原始记录不进入公开集。",
    },
    {
        "zone": "runtime_state",
        "label": "运行状态层",
        "examples": [".llm-wiki/chats/", ".llm-wiki/lancedb/", ".llm-wiki/*queue*"],
        "decision": "never_publish",
        "reason": "对话、向量、队列、索引与本机状态可包含隐式私密。",
    },
    {
        "zone": "generated_wiki",
        "label": "Wiki 生成层",
        "examples": ["wiki/sources/", "wiki/synthesis/", "wiki/concepts/"],
        "decision": "review_and_abstract",
        "reason": "可以提炼方法，但不默认公开来源、专有事实与业务细节。",
    },
    {
        "zone": "workflow",
        "label": "方法与工具层",
        "examples": ["tools/", "schema.md", "purpose.md"],
        "decision": "public_candidate",
        "reason": "仅在去除账号、绝对路径、凭据与私有规则后公开。",
    },
)


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def count_files(root: Path, suffix: str | None = None) -> int:
    if not root.is_dir():
        return 0
    return sum(
        1
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and (suffix is None or path.name.endswith(suffix))
    )


def compact_search(health: dict[str, Any]) -> dict[str, Any]:
    search = health.get("search")
    if not isinstance(search, dict):
        return {"available": False, "passed": None, "total": None}
    return {
        "available": search.get("available") is True,
        "passed": search.get("passed") if type(search.get("passed")) is int else None,
        "total": search.get("total") if type(search.get("total")) is int else None,
    }


def sanitized_snapshot(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    state = project / ".llm-wiki"
    if not project.is_dir() or not (state / "project.json").is_file():
        raise ValueError("the selected directory is not an LLM Wiki project")

    health = read_object(state / "knowledge-health.json")
    vector = read_object(state / "vector-index-status.json")
    graph = read_object(state / "codex-graph-manifest.json")
    daily = read_object(state / "daily-sync-status.json")
    private_roots = tuple((project / "archive").glob("private-*"))

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_type": "local-llm-wiki",
        "content_included": False,
        "source_paths_included": False,
        "filenames_included": False,
        "counts": {
            "wiki_markdown_pages": count_files(project / "wiki", ".md"),
            "raw_source_files": count_files(project / "raw"),
            "private_archive_files": sum(count_files(root) for root in private_roots),
        },
        "health": {
            "status": health.get("status"),
            "observed_at": health.get("generated_at"),
            "search": compact_search(health),
        },
        "vector": {
            "result": vector.get("result"),
            "observed_at": vector.get("updated_at"),
            "indexed_pages": vector.get("indexed_pages")
            if type(vector.get("indexed_pages")) is int
            else None,
            "indexed_chunks": vector.get("indexed_chunks")
            if type(vector.get("indexed_chunks")) is int
            else None,
        },
        "graph": {
            "observed_at": graph.get("generated_at"),
            "managed_pages": graph.get("managed_pages")
            if type(graph.get("managed_pages")) is int
            else None,
            "changed": graph.get("changed") if type(graph.get("changed")) is int else None,
            "removed": graph.get("removed") if type(graph.get("removed")) is int else None,
        },
        "daily_sync": {
            "result": daily.get("result"),
            "finished_at": daily.get("finished_at"),
            "duration_seconds": daily.get("duration_seconds")
            if type(daily.get("duration_seconds")) is int
            else None,
            "health_status": daily.get("health_status"),
        },
        "zones": list(ZONE_POLICY),
        "claim_boundary": (
            "This snapshot contains aggregate counts and selected status fields only. "
            "It does not prove that any Wiki page is safe to publish."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="local LLM Wiki project directory")
    parser.add_argument("--output", type=Path, help="optional JSON output outside the Wiki project")
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        project = args.project.expanduser().resolve()
        snapshot = sanitized_snapshot(project)
        serialized = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            print(serialized, end="")
            return 0

        output = args.output.expanduser().resolve()
        if output == project or project in output.parents:
            raise ValueError("public snapshot output must be outside the private Wiki project")
        if output.exists() and not args.force:
            raise ValueError("output already exists; pass --force to replace this generated snapshot")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
        print(f"wrote content-free snapshot: {output}")
        return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
