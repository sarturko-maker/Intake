---
name: draft-skill
description: "Write or rewrite one working skill now from this organisation's own evidence, and stamp a skill, an area file or knowledge entries approved on the lawyer's word. Use for 'draft a skill for NDA review', 'write the NDA skill now', '/draft-skill nda-review', 'redraft nda-review', 'approve nda-review', 'approve the commercial playbook', 'approve the knowledge entries', and 'what is ready to export'."
argument-hint: "<skill-name> [area]"
model: opus
---

# Draft a skill, and approve

Working skills write themselves in the learning pass (learn skill). This skill is for the two moments when the lawyer steps in: "write that one now", and "approve". Content comes from this organisation only; never invent a position. Rules: RULES.md 'Skills', 'Knowledge'. Ask nothing unless the request cannot be carried out without it.
Only if the harness has no subagents: do the learner's steps yourself (.claude/agents/learner.md).
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

## Draft ("draft a skill for <type of work>", "write the <name> skill now", "redraft <name>")
1. Name: kebab-case from the request (nda-review); it is the work type's slug in learning/work-types/. Area: from the request, the work-type file's `area:`, or the matters behind it. No work-type file with that slug: look for the closest (`ls learning/work-types/`) and use it; say which you took.
2. `bash tools/budget-update --mode`: minimal or paused → stop; say it waits for budget.
3. `bash tools/learn-index`, and take this skill's line (`due:` or `later:`). No line because it is up to date: say so and show its link. No line because the evidence is thin (one matter, or none of our own work yet): write it anyway, since the lawyer asked; the line for the learner is `skill <slug> | area <area> | asked for by the lawyer | evidence_lines <count> | <path or "no skill yet">`, the count from `grep -cE '^[A-Za-z0-9-]+-[0-9]+ \| ' learning/work-types/<slug>.md`. No evidence at all: say so in one line, and that telling you how the team handles it, or "interview me about <type>", gives the skill something to stand on.
4. Dispatch one learner with R, the mode, today's date and that line. It writes skills/<area>/<name>/SKILL.md by the template (skills/operations/draft-skill/templates/skill-template.md): `status: working`, every line with what it rests on, gaps written "Not seen yet".
5. `bash tools/skills-sync`, `bash tools/skills-sync --check` (exit 0), `bash tools/learn-index --quiet`.
6. Show the lawyer: the link, the opening lines, how many matters it rests on, and its 'Not sure yet'. Then: "Read it when you like. Tell me what to change in your own words; say 'approve <name>' when it is right." What the lawyer then says is applied by the learn skill ('What the lawyer tells you').
7. `bash tools/budget-update --measure --run <R> --note "draft-skill <name>"`. It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "draft-skill <name>"`, once per model used (m: its BUDGET.md price key).

## Approve
Approval is the lawyer's yes to a version. It is needed for two things only: a fixed point (a red line, an approval limit, who may sign), and anything that leaves for the Copilot Studio libraries (copilot-studio/export.md). Never suggest it as a step the lawyer owes.

- **A skill** ("approve nda-review"): Edit its frontmatter: `status: approved`, `last_reviewed: <today>`, `approved_version: <its version>`, description without the "Working skill, not yet approved." prefix. A line resting only on a seed is removed first, or kept if the lawyer says so. Nothing else changes. `bash tools/skills-sync`, then `--check`. A later learning pass that changes it makes it working again, says what differs from the approved version, and keeps the approved copy in its history/ folder.
- **An area file** ("approve the commercial playbook", or its intake file), after the lawyer has read it: `status: approved`, `version` one higher, and in playbook.md `last_reviewed: <today>`. Changes asked for first: apply them with their sources.
- **Knowledge entries** ("approve the knowledge entries", "approve the entities"): list the working entries (`grep -rl --include='*.md' '^status: working' knowledge | grep -v '/history/'`), numbered, at most thirty to a message: name, type, one line, link. The lawyer answers in their own words ("all", "all except 3 and 7", "5 is owned by Finance"). For each yes, Edit the frontmatter: `status: approved`, `confirmed_by: <lawyer_name in house/brief.md>`, `last_confirmed: <today>`, and `owner:` when the lawyer named one. A no: nothing changes, unless the lawyer says it is wrong, which is a correction (learn skill). Then `bash tools/learn-index --quiet`.
- **Fixed points** ("that is a fixed point", "the cap is a red line"): the learn skill, 'What the lawyer tells you'. The lawyer's saying it is the approval.

## What is ready to export ("what is ready to export", "export list")
By copilot-studio/export.md: approved skills and their versions; approved entries by type and library (Sales or legal); what changed since it was approved (a skill with `approved_version` below its `version`). List only; the lawyer uploads. Nothing working is ever exported.
