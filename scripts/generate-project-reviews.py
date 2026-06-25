#!/usr/bin/env python3
"""Generate docs/reviews.json for curated Project Directory reviews."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = "data/reviews/biohazardous.json"
DEFAULT_PROJECTS = "docs/projects.json"
DEFAULT_OUTPUT = "docs/reviews.json"


def clean_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_rating(value: Any, review_id: str) -> float:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"review {review_id} rating must be a number")
    if not 0 <= rating <= 5:
        raise ValueError(f"review {review_id} rating must be between 0 and 5")
    return rating


def validate_date(value: Any, review_id: str) -> str:
    text = clean_text(value)
    if not text:
        raise ValueError(f"review {review_id} reviewedAt is required")
    try:
        datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"review {review_id} reviewedAt must be YYYY-MM-DD")
    return text


def validate_review(raw: dict[str, Any], reviewer: dict[str, Any], projects: dict[str, dict[str, Any]]) -> dict[str, Any]:
    project_id = clean_text(raw.get("projectId"))
    if not project_id or project_id not in projects:
        raise ValueError(f"review has unknown projectId: {project_id!r}")
    project = projects[project_id]
    review_id = clean_text(raw.get("id")) or f"{reviewer['id']}-{project_id}"
    summary = clean_text(raw.get("summary"))
    thoughts = clean_text(raw.get("thoughts"))
    if not summary or len(summary) > 140:
        raise ValueError(f"review {review_id} summary is required and must be <= 140 chars")
    if not thoughts or len(thoughts) > 1600:
        raise ValueError(f"review {review_id} thoughts are required and must be <= 1600 chars")

    review = {
        "id": review_id,
        "projectId": project_id,
        "projectTitle": project.get("title", project_id),
        "projectUrl": project.get("pagesUrl", ""),
        "projectRepo": project.get("repo", ""),
        "projectThumbnail": project.get("thumbnail", ""),
        "reviewer": reviewer,
        "rating": validate_rating(raw.get("rating"), review_id),
        "summary": summary,
        "thoughts": thoughts,
        "reviewedAt": validate_date(raw.get("reviewedAt"), review_id),
    }
    for optional in ("favorite", "suggestion"):
        value = clean_text(raw.get(optional))
        if value:
            if len(value) > 360:
                raise ValueError(f"review {review_id} {optional} must be <= 360 chars")
            review[optional] = value
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Project Directory reviews manifest")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--projects", default=DEFAULT_PROJECTS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = load_json(Path(args.source))
    projects_payload = load_json(Path(args.projects))
    projects = {project["id"]: project for project in projects_payload.get("projects", [])}
    reviewer = source.get("reviewer") or {}
    reviewer = {
        "id": clean_text(reviewer.get("id")) or "biohazardous",
        "name": clean_text(reviewer.get("name")) or "Biohazardous",
        "displayName": clean_text(reviewer.get("displayName")) or "Biohazardous",
    }
    reviews = [validate_review(review, reviewer, projects) for review in source.get("reviews", [])]
    reviews.sort(key=lambda item: (item["reviewedAt"], item["projectTitle"].lower()), reverse=True)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": args.source,
        "scale": "0-5",
        "reviews": reviews,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output} with {len(reviews)} review(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
