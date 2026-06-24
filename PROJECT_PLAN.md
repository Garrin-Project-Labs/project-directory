# Project Directory Plan

## Purpose

Project Directory is the central public landing page for Project Factory projects. It should help people quickly discover public projects, open their live GitHub Pages demos, and find the backing GitHub repositories when they want technical details.

This project intentionally publishes only safe public metadata. Private projects, non-public demos, secrets, memory files, runtime state, and Discord-only discussion content must not be listed publicly unless a maintainer explicitly opts that project in.

## Current first version

The first implementation is a static GitHub Pages site served from `docs/`:

- `docs/index.html` renders a searchable card directory.
- `docs/projects.json` is the generated manifest consumed by the page.
- `scripts/generate-project-directory.py` regenerates the manifest from Project Factory workspace policy files.

The current generator is conservative: it lists only projects whose `.project/policy.yaml` says:

- `discord.visibility: public`
- `publishing.githubPages: true`
- `publishing.publicDemos: true`
- `publishing.githubPagesUrl` is non-empty

The directory project itself may be listed as the central hub.

## Desired end state

A Project Factory-managed public directory that stays current as projects are created, renamed, published, or updated, while still allowing owners/maintainers to customize how their project appears.

The directory should show, at minimum:

- project title
- short description
- GitHub Pages URL when available
- GitHub repo URL when public
- optional thumbnail/image
- optional tags/category
- status such as live, pending, archived, hidden

## Operating principles

1. **Privacy first**
   - Never list private projects by default.
   - Never read or publish memory, sessions, secrets, `.env`, local auth stores, or raw Discord transcript content.
   - Only publish metadata from explicit project policy/manifest files or maintainer-approved overrides.

2. **Generated, not hand-maintained**
   - `docs/projects.json` should be reproducible from source metadata.
   - Manual edits should go into project-owned metadata/override files, not directly into generated output.

3. **Owner-friendly customization**
   - Project owners/maintainers should be able to ask the bot to update title, description, thumbnail, tags, sort order, and hidden/listed status.
   - The bot should perform the normal `project-authz` check before any durable change.

4. **Small static surface**
   - Prefer static JSON + static HTML on GitHub Pages.
   - Avoid a server unless we discover a real need for dynamic behavior.

## Near-term implementation plan

### Phase 1 — First useful directory

- Keep `docs/index.html` lightweight and searchable.
- Keep `docs/projects.json` generated and committed.
- Keep generator input limited to public `.project/policy.yaml` files.
- Add this `PROJECT_PLAN.md` so the project agent has enough context to continue without relying on chat history.

Verification:

```bash
scripts/generate-project-directory.py
python3 -m json.tool docs/projects.json >/dev/null
```

### Phase 2 — Metadata overrides

Add a durable metadata source for each listed project. Recommended shape:

```yaml
# .project/directory.yaml in each project workspace/repo
directory:
  listed: true
  title: "Friendly display title"
  description: "Short public description."
  thumbnail: "docs/assets/thumbnail.png"
  tags: [game, demo]
  sortOrder: 100
```

Rules:

- If no override exists, derive safe defaults from `.project/policy.yaml`.
- `listed: false` hides a project even if it is public.
- Only authorized maintainers/owners may edit overrides.
- The generator should validate descriptions are short and thumbnails are local/approved URLs.

### Phase 3 — Automation hook

Regenerate and publish the directory when:

- a new public project is created
- a project enables GitHub Pages
- a project changes visibility
- a maintainer updates directory metadata
- a scheduled sync runs as a safety net

Likely implementation options:

- Project Factory command/script: `scripts/update-project-directory`
- Cron/scheduled TaskFlow job that runs the generator and opens/updates a PR
- GitHub Action in `project-directory` if it can safely access only approved public metadata

Recommendation: start with a factory script that opens a PR, then add scheduling once the data shape is stable.

### Phase 4 — Better UI

Once the manifest is stable:

- add tags/filter chips
- add project thumbnails
- group by project type/status
- show live/pending/archived indicators
- improve empty/error states
- keep the page dependency-free unless the UI grows enough to justify a build step

## Open questions

- Should `project-directory` list public projects that do not yet have Pages, or only projects with live demos?
- Should descriptions live in each project repo, factory state, or both?
- Should hidden/listed be owner-controlled per project, or global-owner only?
- Should the directory auto-merge generated updates, or always open PRs for review?

## Useful references

- Source task in Project Factory: `.project/tasks/025-project-landing-page-directory.json`
- Directory workspace: `/home/garrin/.openclaw/workspace-directory`
- Directory repo: `Garrin-Project-Labs/project-directory`
- Directory Pages URL: `https://garrin-project-labs.github.io/project-directory/`
- Factory auth helper: `/home/garrin/.openclaw/scripts/project-authz`
