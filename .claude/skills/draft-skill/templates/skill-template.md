---
name: {{name}}
description: "Working skill, not yet approved. Use when {{when this skill applies}}. Triggers: '{{plain phrase}}', '{{plain phrase}}'."
area: {{area}}
version: 1
status: working
written: {{YYYY-MM-DD}}
evidence_lines: {{count of evidence lines used}}
supporting_matters: {{REF, REF}}
last_reviewed:
approved_version:
---
<!-- Template for skills/<area>/<name>/SKILL.md, written by the learner (learn skill; .claude/agents/learner.md). Replace {{...}} and every "Fill" prompt; delete the comments. A section with nothing seen yet keeps its heading and one line: "Not seen yet." Never fill a gap from general legal knowledge. On approval (draft-skill skill): status approved, last_reviewed, approved_version, description without the "Working skill, not yet approved." prefix. -->
# {{Skill title}}

{{Three to five plain lines for the lawyer: what this type of work is, how we usually handle it, and how much this page rests on (how many matters, what the lawyer has said).}}

This page is the agent's working view of how we think about this work, not a set of rules. Every line says what it rests on: `(2026-0042)` one matter, `(2026-0042, 2026-0051)` several, `(you said, 2026-11-12)` or `(you edited, 2026-11-12)` the lawyer, `(interview 2026-11-20)`, `(knowledge/<file>)`, `(seed, unverified)`. Seen once is an example, not a pattern. No names of clients, people or other parties: references and types only. The lawyer decides.

How to use it: reason from the considerations and the worked examples to the matter in hand. Say which considerations apply, how the matter compares with the closest example (alike and different), and give options with a view. Never apply an example as a rule. Where the matter is outside what this page has seen, say so and give your best view, marked as outside the skill.

## When to use
<!-- Fill from the `asked` and `routing` lines: who sends this kind of request, what they really want, what this skill covers and what it does not. -->

## Questions we ask first
<!-- Fill from the `we-asked` and `answer` lines, the `expected` and `compared` lines (a question the agent missed belongs here), and the lawyer's words. One entry per question, the ones asked most first:
- **<The question, as we put it to the requester>** Why: <what the answer unblocks>. Where the answer may already be: <the draft, the earlier matter, the requester's email>. If it is missing we assume: <what we went ahead on, or "not seen yet">. Not safe to assume when: <only what the lawyer said or a matter showed>. (basis) -->

## How we think about it
<!-- Fill from the `position`, `fallback`, `context`, `approval` and `did` lines and the reasons in the matters: the considerations we weigh (what is at stake against what acting would cost, the relationship, precedent, leverage, risk) and how they pull against each other. Write them as weighing ("we weigh the cost of going further against the sum at stake; the business decides whether to absorb a loss"), never as conditions ("if the sum is low, offer two options"). A consideration rests on two matters or on the lawyer's words; with one matter it is a worked example below. Our usual starting point and where we have moved, with the reasons. -->

## Worked examples
<!-- Fill from the matters: three to six short cases, the ones that teach most. Each: the situation (by type and reference), what was weighed, what we did, why, how it turned out. Where a matter went differently from what the lawyer says we do, it stays here with its context. -->

## Fixed points
<!-- Fill only from the lawyer's own words (origin lawyer or interview, a hand edit, an approved knowledge entry): red lines, approval limits, who may sign. Each with its basis. None yet: "None stated yet."
Then, separately, what the matters show without the lawyer having said it is fixed:
Seen so far, not fixed: <what we refused or always did, with references>. -->

## Where the line is and when to stop and ask
<!-- Fill from the `approval` and `routing` lines and knowledge/ (policies, roles): who decided what in the matters seen, and what went above the lawyer. -->

## How we say it
<!-- Fill from the `phrasing` lines (our own wording, in quotes, with the reference) and the tone in house/brief.md. -->

## What to read
<!-- Fill from what the matters actually turned on and the `wasted-effort` lines for this type of work: what to read first, what can usually be skipped, when a short read is enough. This keeps runs under this skill cheap without changing the result. -->

## Output shape
<!-- Fill: what the reader or drafter produces under this skill. -->
- brief.md: the sections this skill fills, and what goes under What the lawyer must decide.
- Issues table: point | their text (file, place) | our view and the considerations behind it (basis) | options with a view.
- Drafts: <yes: what, into drafts/ | no>. A draft is never sent.

## Not sure yet
<!-- Fill: the open points for this type of work, each with the reading the agent works on until told otherwise ("Assumed: ..."); where the matters and the lawyer's words differ; where the agent expected the wrong thing (`compared` lines starting partly or missed) and what it changed. Nothing here is a question the lawyer must answer. -->

## What changed
<!-- Newest first, at most five lines: `v<N> <YYYY-MM-DD>: <what changed and why, one line>`. -->
