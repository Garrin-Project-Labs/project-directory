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
from urllib.parse import urlparse

DEFAULT_WORKSPACE_GLOB = "/home/garrin/.openclaw/workspace-*"


def parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0:1] in ('"', "'") and raw[-1:] == raw[0]:
        return raw[1:-1]
    if raw.startswith("[") and raw.endswith("]"):
        items = raw[1:-1].strip()
        if not items:
            return []
        return [parse_scalar(item.strip()) for item in items.split(",")]
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


def clean_text(value: Any, fallback: str = "") -> str:
    return str(value if value is not None else fallback).strip()


def validate_description(description: str, project_id: str) -> str:
    description = " ".join(description.split())
    if len(description) > 180:
        raise ValueError(f"directory description for {project_id} is too long ({len(description)} > 180 chars)")
    return description


def validate_tags(tags: Any, project_id: str) -> list[str]:
    if tags in (None, ""):
        return []
    if not isinstance(tags, list):
        raise ValueError(f"directory tags for {project_id} must be a YAML inline list")
    cleaned: list[str] = []
    for tag in tags:
        text = clean_text(tag).lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,30}", text):
            raise ValueError(f"invalid directory tag for {project_id}: {tag!r}")
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def validate_thumbnail(thumbnail: str, project_id: str) -> str:
    if not thumbnail:
        return ""
    parsed = urlparse(thumbnail)
    if parsed.scheme:
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"directory thumbnail for {project_id} must be a local path or https URL")
        return thumbnail
    if thumbnail.startswith(("/", "../")) or "/../" in thumbnail or thumbnail == "..":
        raise ValueError(f"directory thumbnail for {project_id} must stay inside the project site")
    if not thumbnail.startswith(("docs/", "assets/")):
        raise ValueError(f"directory thumbnail for {project_id} must be under docs/ or assets/")
    return thumbnail


def validate_public_url(url: str, project_id: str, field: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"directory {field} for {project_id} must be an https URL")
    return url


def load_directory_override(workspace_path: Path, project_id: str) -> dict[str, Any]:
    override_path = workspace_path / ".project" / "directory.yaml"
    if not override_path.exists():
        return {}
    data = parse_simple_yaml(override_path)
    directory = data.get("directory", {})
    if not isinstance(directory, dict):
        raise ValueError(f"directory override for {project_id} must contain a directory mapping")
    return directory


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
        project_id = clean_text(project.get("id") or policy_path.parents[1].name.removeprefix("workspace-"))
        name = clean_text(project.get("name") or project_id.replace("-", " ").title())
        visibility = clean_text(discord.get("visibility") or "private").lower()
        pages_enabled = publishing.get("githubPages") is True
        public_demo = publishing.get("publicDemos") is True

        try:
            override = load_directory_override(policy_path.parents[1], project_id)
        except Exception as exc:
            print(f"warning: skipped {policy_path.parents[1]} directory override: {exc}")
            continue

        pages_url = validate_public_url(
            clean_text(override.get("pagesUrl"), clean_text(publishing.get("githubPagesUrl"))),
            project_id,
            "pagesUrl",
        )
        override_pages_opt_in = bool(override.get("listed") is True and pages_url)

        if override.get("listed") is False:
            continue
        if visibility != "public":
            continue
        if project_id != "directory" and not ((pages_enabled and public_demo and pages_url) or override_pages_opt_in):
            # Be conservative: require policy publishing fields or an explicit directory opt-in with a Pages URL.
            continue

        title = clean_text(override.get("title"), name)
        description = validate_description(
            clean_text(override.get("description"), slug_to_description(project_id, title)),
            project_id,
        )
        thumbnail = validate_thumbnail(clean_text(override.get("thumbnail")), project_id)
        tags = validate_tags(override.get("tags"), project_id)
        status = clean_text(override.get("status"), "live" if pages_url else "pending").lower()
        sort_order = override.get("sortOrder", 1000)
        try:
            sort_order = int(sort_order)
        except (TypeError, ValueError):
            raise ValueError(f"directory sortOrder for {project_id} must be an integer")

        repo = clean_text(project.get("repo"))
        entry = {
            "id": project_id,
            "title": title,
            "description": description,
            "repo": f"https://github.com/{repo}" if repo else "",
            "pagesUrl": pages_url,
            "channelId": clean_text(discord.get("channelId")),
            "visibility": visibility,
            "pagesStatus": clean_text(publishing.get("githubPagesStatus"), "live" if override_pages_opt_in else "unknown"),
            "status": status,
            "thumbnail": thumbnail,
            "tags": tags,
            "sortOrder": sort_order,
            "sortKey": title.lower(),
        }
        projects.append(entry)
    projects.sort(key=lambda item: (item["sortOrder"], item["id"] == "directory", item["sortKey"], item["id"]))
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
