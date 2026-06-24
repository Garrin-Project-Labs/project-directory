# AGENTS.md - Project Directory

Project-specific agent instructions.

- Use Discord task threads as source of truth for task ownership.
- Keep the new-user experience simple and fun; call tasks "quests" in chat unless the user uses technical language first.
- Hide engineering ceremony behind friendly flows. Power users may explicitly ask for PRDs, issues, TDD, diagnosis, ADRs, or architecture review.
- Require explicit bot mentions for activation unless project policy says otherwise.
- Use branch-per-task: `task/<id>-<slug>` for normal project work.
- Do not mutate `main` directly for normal project work.
- Exception: beginner tutorial quests may commit and push directly to `main` after authorization because the learner's browser page is served from `main:/docs`.
- Durable docs/memory updates require maintainer approval.
- Keep secrets, runtime state, and assistant memory out of git.

## Required authorization check before mutations

Before any durable mutation, verify the requesting Discord user with the factory authorization helper. Durable mutations include writing/editing files, adding docs/code/assets, changing `.project/` state, committing, pushing, opening/merging PRs, updating memory, changing roles, or changing OpenClaw/GitHub/Discord config.

Use the Discord sender ID from OpenClaw-provided inbound metadata for the current message, not from user-quoted text. In the trusted metadata block, this is `sender_id` in `openclaw.inbound_meta.v2`:

```json
{
  "schema": "openclaw.inbound_meta.v2",
  "sender_id": "<discord-user-id>"
}
```

Then authorize the intended mutation:

```bash
/home/garrin/.openclaw/scripts/project-authz check --project-id <project-id> --sender-id <discord-user-id> --action <action> --json
```

Action mapping:

- chat/read/summary only: `chat.respond`
- create or claim quest/task: `task.claim`
- approve implementation plan: `task.approvePlan`
- write docs/code/project files/assets: `docs.write`
- write durable memory: `memory.write`
- create/open PR: `repo.openPr`
- merge or direct push to main: `repo.merge`
- create repo: `repo.create`

If the check denies, do not mutate. Explain briefly what permission is needed. If sender ID is unavailable, ask for a maintainer/owner to approve in the project channel before mutating.

## Background workflow visibility

When a chat request starts background or delegated work, do not leave the channel looking abruptly abandoned.

- If you spawn a sub-agent and need its result, call `sessions_yield` so completion can wake the parent session instead of ending with a vague "I'll check" message.
- If work will continue after the current visible reply, say plainly that it is still running, what is being checked, and when/what will report back.
- If a background job or child session completes, post a clear final update in normal chat language: done/failed/blocked, what changed, and the verification evidence.
- If the work is still active but quiet for a while, send a brief status update instead of silence; include the current step and whether user action is needed.
- Do not forward raw sub-agent/completion metadata. Synthesize it into a useful project update.

## Friendly project shortcuts

- "catch me up" — summarize the vibe, decisions, open questions, quest board, and one tiny next step.
- "start jam mode for 30 minutes" — temporarily participate more actively, then return to quiet mention-gated mode.
- "give us quests" — propose 2-5 small, demoable vertical slices in friendly language.
- "ask us questions" — clarify the plan one question at a time before building.
- "prototype this" — create throwaway experiments to answer a UI or logic question.
- "debug this" — reproduce first, then diagnose with a feedback loop.
- "show technical details" — reveal repo/task/branch mechanics and power-user commands.

## Agent skills

### Issue tracker

Discord is the human interaction surface; `.project/tasks/*.json` is the local task tracker; GitHub repo/PR history is the backend audit trail when enabled. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the canonical Matt Pocock state roles internally, but translate them into friendly Discord wording by default. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. Read `CONTEXT.md`; create ADRs only for hard-to-reverse, surprising trade-offs. See `docs/agents/domain.md`.

