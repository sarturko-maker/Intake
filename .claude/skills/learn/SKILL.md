---
name: learn
description: "Write up what the system has learned, without asking: working skills from the evidence, knowledge entries from the facts noted, open points settled where the evidence allows. Also takes what the lawyer says about a skill, an entry or how the team works, and applies it at once. Use for 'learn', '/learn', 'catch up', 'what have you learned', 'show me the NDA skill', and whenever the lawyer corrects or adds to a skill or a knowledge entry in their own words ('in the NDA skill, ...', 'that is wrong: ...', 'we never ...', 'Finance owns ...')."
model: opus
---

# Learn

Skills and knowledge are the agent's working view, kept the way a matter's memory is kept: written from what was read, every line with what it rests on, rewritten as more arrives, and corrected by the lawyer whenever the lawyer likes. Nothing waits for the lawyer. Rules: RULES.md 'Wrap-up and learning', 'Knowledge', 'Skills'. Never ask the lawyer to confirm a fact or answer a question so that learning can go on: write the reading you work on, and say so.

Only if the harness has no subagents: do the learner's steps yourself (.claude/agents/learner.md), one skill at a time, then knowledge, then open points.
R = the open run's id when intake calls this skill; else `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

## The pass ("learn", "catch up"; from intake when learn-index lists something as due)
1. `bash tools/budget-update --mode`. minimal or paused: stop; one line that the pass waits for budget. lean: only when the lawyer asked ("learn"); from intake the pass runs in full mode only.
2. Seeds not yet taken in. A file in seeds/ that is not listed in learning/seeds-imported.md (Harvey batch reports, registers, extractions): read it and add what it teaches as leads, then list it there with its sha256 (`bash tools/hash-files`) and today's date.
   - evidence: `bash tools/learn-add --matter seed --origin seed --work-type <slug>`, reusing a slug from learning/work-types/;
   - company facts: `--matter seed --knowledge`, source "seed <file>";
   - what it leaves open: `--matter seed --question`.
   Harvey skills scout output (seeds/harvey/<date>/): `work-types.md` gives one `asked` line per type it matches; `knowledge-needs.md` gives facts (`--knowledge`) and open points; `coverage-and-questions.md` gives open points; `skills.md` is not imported: the learner reads the draft for its type of work as a lead. Outside parties stay as Harvey's codes.
   Seeds are never "observed", and a seed never beats our own evidence or the lawyer.
3. `bash tools/learn-index`. It rebuilds learning/index.md and prints `due:` and `later:` lines. From intake: the `due:` lines only, at most six skills in one run, most evidence first; the rest wait for the next run. On "learn" or "catch up": every `due:` and `later:` line. No lines: say there is nothing new to write, link the page, stop.
4. Dispatch learners, all at once:
   - skills: three `skill` lines to a learner, each line passed exactly as printed;
   - one more learner for `knowledge: yes` (when a `knowledge` line was printed) and `points: yes`.
   Each gets R, the mode and today's date. Learners write the skills and entries, mark the fact lines and open points they dealt with, and report.
5. When they are back:
   - `bash tools/skills-sync`, then `bash tools/skills-sync --check` (exit 0): new and changed skills load from the next session;
   - `bash tools/learn-index --quiet`: the page, and the knowledge index blocks of the new entries;
   - the WORKFLOW-LOG.md lines the reports list;
   - `bash tools/budget-update --measure --run <R> --note "learn"`. It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "learn"`, once per model used.
6. Tell the lawyer, briefly: at most twelve lines in all (from intake: at most six, under 'What we learned' in the digest and the reply):
   - each skill written or rewritten, one line: its link, version, how many matters it rests on, what changed;
   - knowledge, one line: how many entries were written or updated, with a link to knowledge/INDEX.md;
   - "Least sure": at most five one-line statements from the learners' reports, as statements, not questions;
   - then one line: "Read them when you like. Tell me what is wrong in your own words, or edit the files: I keep what you say."
   End there. Never ask for a confirmation, an owner or an approval, and offer no follow-up tasks; the details are in the files.

## What the lawyer tells you (any time, in any words)
The lawyer says how the team works, states a fact about the company, or corrects a skill or an entry: "in the NDA skill, we never accept more than three years", "that is wrong: Finance owns credit limits", "delete the bit about Dutch law", "the German company's directors sign jointly". About one matter only: the note skill instead.
1. Record it first, as the lawyer's, so that no later rewrite loses it:
   - a way of working: `printf '%s\n' "<kind> | <the lawyer's point, one line> | lawyer in chat <today>" | bash tools/learn-add --matter chat --work-type <slug> --origin lawyer --run <R>`. Kinds: position, fallback, red-line, approval, context, phrasing, we-asked (a question we put first), or `correction` when it removes or contradicts something ("correction | Not our practice: <what>; removed on the lawyer's word | ...").
   - a company fact: `printf '%s\n' "<type> | <the fact> | lawyer in chat <today>" | bash tools/learn-add --matter chat --knowledge --run <R>`.
   Which skill or type of work is unclear: take the likeliest and say so in your reply. Never ask the lawyer to repeat or confirm what they just said.
2. Apply it at once, with Edit:
   - a skill: change the lines it touches, each ending `(you said, <today>)`; a removal removes the line. "Never", "always", an approval limit or who may sign goes under 'Fixed points', because the lawyer said it. Raise `version` by one, set `written: <today>`, add a line at the top of 'What changed'. If learn-index showed the skill up to date before this, also set `evidence_lines:` to the count now (`grep -cE '^[A-Za-z0-9-]+-[0-9]+ \| ' learning/work-types/<slug>.md`), so the next pass does not rewrite what the lawyer has just read.
   - an entry that exists: add the statement under 'You said' with the date; a document fact it contradicts moves to 'Differences'. Then `bash tools/learn-mark <K-id> --status "written (knowledge/<path>)"`.
   - a fact with no entry yet, more than three statements at once, or a skill that does not exist yet: run the pass for those items instead (steps 4 and 5; the learner gets `lawyer said:` with the words).
3. `bash tools/skills-sync` after a skill changed; `bash tools/learn-index --quiet`.
4. Reply in two or three lines: what you recorded and what changed, with links. No questions back.

## Showing ("what have you learned", "show me the NDA skill")
- "what have you learned": `bash tools/learn-index`, then the page in at most ten lines: the skills with their versions and how often the agent expected right, the knowledge counts, what the next pass will write. Links: learning/index.md, each skill, knowledge/INDEX.md.
- "show me <skill or entry>": the link, and its opening lines and 'Not sure yet' in chat. Offer nothing else; the lawyer says what to change.
- "what did the lawyer change", "what changed in <skill>": its 'What changed' section and the copies in its history/ folder.

## Approval
Not part of the pass. A skill or an entry is approved only when the lawyer says so ("approve nda-review", "approve the knowledge entries"): the draft-skill skill, 'Approve'. Approval is needed for fixed points and for anything exported to the Copilot Studio libraries (copilot-studio/export.md), nowhere else.
