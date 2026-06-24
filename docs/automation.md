# Project Directory Automation

The directory is a static GitHub Pages site, so automation stays intentionally small: regenerate `docs/projects.json`, validate it, then publish through a normal git branch/PR or an explicitly approved direct push.

## Manual sync

From the `project-directory` workspace:

```bash
scripts/update-project-directory
```

This runs the privacy-first generator and validates the JSON. If the generated manifest is unchanged, the script exits cleanly without changing `generatedAt`.

## Prepare a reviewable update branch

```bash
scripts/update-project-directory --commit --push
```

This will:

1. fetch `origin/main`
2. create or switch to `task/update-project-directory`
3. regenerate `docs/projects.json`
4. validate JSON
5. commit changed manifest output, if any
6. push the branch

Open a PR from the pushed branch when review is wanted.

## Direct publish path

If a maintainer explicitly approves a direct main update, run:

```bash
git switch main
git pull --ff-only origin main
scripts/update-project-directory
# if docs/projects.json changed:
git add docs/projects.json
git commit -m "Update project directory manifest"
git push origin main
```

## Safety rules

- The generator reads only `.project/policy.yaml` and `.project/directory.yaml` from workspaces.
- Private projects stay hidden unless their project policy is public and directory metadata explicitly opts them into a public Pages URL.
- Do not publish memory files, sessions, secrets, `.env`, local auth stores, or raw Discord transcript content.
- Durable metadata edits still require the usual `project-authz` check.
