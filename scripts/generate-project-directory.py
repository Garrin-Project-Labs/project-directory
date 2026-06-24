#!/usr/bin/env python3
"""Generate docs/projects.json for the Project Directory site.

This intentionally reads only Project Factory policy.yaml files and publishes only
public projects with publicDemos/GitHub Pages enabled. It does not read memory,
sessions, secrets, or private project content.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_WORKSPACE_GLOB = "/home/garrin/.openclaw/workspace-*"


def parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0:1] in ('"', "'") and raw[-1:] == raw[0]:
        return raw[1:-1]
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "null":
        return None
    return raw


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the simple nested mapping shape emitted by the factory policy files."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        if ":" not in text:
            continue
        key, value = text.split(":", 1)
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parse_scalar(value)
    return root


def slug_to_description(project_id: str, name: str) -> str:
    if project_id == "directory":
        return "Central landing page for public Project Factory projects."
    words = re.sub(r"[-_]+", " ", project_id).strip()
    if words and words.lower() != name.lower():
        return f"Project workspace for {name}."
    return "Public Project Factory workspace."


def load_projects(workspace_glob: str) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    for policy_path in sorted(Path("/").glob(workspace_glob.lstrip("/") + "/.project/policy.yaml")):
        try:
            policy = parse_simple_yaml(policy_path)
        except Exception as exc:  # pragma: no cover - defensive generator path
            print(f"warning: skipped {policy_path}: {exc}")
            continue
        project = policy.get("project", {})
        discord = policy.get("discord", {})
        publishing = policy.get("publishing", {})
        project_id = str(project.get("id") or policy_path.parents[1].name.removeprefix("workspace-")).strip()
        name = str(project.get("name") or project_id.replace("-", " ").title()).strip()
        visibility = str(discord.get("visibility") or "private").strip().lower()
        pages_enabled = publishing.get("githubPages") is True
        public_demo = publishing.get("publicDemos") is True
        pages_url = str(publishing.get("githubPagesUrl") or "").strip()

        if visibility != "public":
            continue
        if project_id != "directory" and not (pages_enabled and public_demo and pages_url):
            # Be conservative: public-but-not-published projects can opt in later.
            continue

        repo = str(project.get("repo") or "").strip()
        entry = {
            "id": project_id,
            "title": name,
            "description": slug_to_description(project_id, name),
            "repo": f"https://github.com/{repo}" if repo else "",
            "pagesUrl": pages_url,
            "channelId": str(discord.get("channelId") or ""),
            "visibility": visibility,
            "pagesStatus": str(publishing.get("githubPagesStatus") or "unknown"),
            "sortKey": name.lower(),
        }
        projects.append(entry)
    projects.sort(key=lambda item: (item["id"] == "directory", item["sortKey"], item["id"]))
    return projects


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Project Directory manifest")
    parser.add_argument("--workspace-glob", default=DEFAULT_WORKSPACE_GLOB)
    parser.add_argument("--output", default="docs/projects.json")
    args = parser.parse_args()

    projects = load_projects(args.workspace_glob)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Project Factory policy.yaml files",
        "privacy": "Only public projects with public GitHub Pages demos are listed.",
        "projects": projects,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output} with {len(projects)} project(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
