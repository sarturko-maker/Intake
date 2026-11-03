---
name: draft-skill
description: "Draft a legal skill from this organisation's own knowledge, closed matters and a short interview with the lawyer, then stamp it on approval. Use for 'draft a skill for NDA review', '/draft-skill nda-review', and 'approve' after a draft skill, playbook or intake file is shown."
argument-hint: "<skill-name> [area]"
model: opus
---

# Draft a skill

Shape from the template; content from this organisation only. Never invent a position. Rules: RULES.md 'Skills', 'Knowledge'. Ask in plain chat, one or two short questions at a time; never assume an answer.
Only if the harness has no subagents: do the researcher's reading yourself.
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

1. Name: kebab-case from the request (nda-review). Area: from the request or house/areas.md; unclear → ask "Which area is this skill for?". Path: skills/<area>/<name>/SKILL.md. It exists: ask whether to redraft it.
2. `bash tools/budget-update --mode`: minimal or paused → stop; say it waits for budget.
3. Dispatch the researcher to gather sources and return candidate points, each line with its source, plus conflicts and gaps:
   - knowledge/INDEX.md first, then only the relevant files and sections (positions, templates, policies, standard answers);
   - closed matters of this kind: INDEX.csv rows with status closed and a matching label, and `grep -rl --include=matter.md 'controlling_skill: <name>' areas`; their closing notes and decision facts;
   - seeds/: leads only, never truth;
   - skills/POINTERS.md: shape and checklists only; nothing from it becomes a position without the lawyer;
   - areas/<area>/playbook.md and intake.md;
   - learning/work-types/<slug>.md: the evidence for this work type, matter by matter (start here);
   - seeds/interviews/*<topic>*.notes.md: confirmed interview statements only (interview skill);
   - our substantive emails in matters of this kind (documents.md rows with origin ours and a "[substantive]" summary): what we actually said and did; the strongest evidence after the lawyer's own answers;
   - for 'What to read': the documents and clauses those matters actually turned on, and the `wasted-effort` lines in WORKFLOW-LOG.md for them, so the skill reads only what the result needs.
4. Interview: at most eight questions, one or two at a time, only on what the interview notes and sources leave open (no notes yet: suggest "interview me about <topic>" first). Ask the open question first; then show in one line what the sources say, with the source, so the lawyer can confirm or correct it. Skip what is already answered.
   1. When does this kind of request come in, and from whom?
   2. What do you check first?
   3. What do you never accept?
   4. What do you usually concede?
   5. What facts do you ask for before acting?
   6. Who signs off?
   7. How do you phrase the reply?
   8. Tell me about one that went badly.
   A seed that contradicts knowledge or an answer: say so and ask. The lawyer's answer wins.
5. Draft from skills/operations/draft-skill/templates/skill-template.md into the path: `status: draft`, `version: 0`, description starting "DRAFT, not yet approved.". Every position line ends with its source: (interview <date>, S<nn>), (knowledge/<file>), (matter <REF>) or (seed (lead, unverified)). Where the interview and the evidence differ, the lawyer's recorded choice decides the line; the exceptions go under 'Worked examples' with their context. No source, no line.
   Write how we think, not rules: considerations, how they trade off, and worked examples (situation, what was weighed, what we did, why). One matter is an example, never a rule; a consideration rests on two matters or a confirmed interview statement. No "if X, then Y", "always" or "must" unless the lawyer said it is firm; those few go under 'Fixed points'. No party names or identifying figures: cite references.
6. Show the draft: the path and each section in brief. Ask: "Approve, or tell me what to change?" Apply changes. A line resting on a seed alone is confirmed by the lawyer or removed before approval.
7. On "approve": `status: approved`, `version: 1`, `last_reviewed: <today>`, `supporting_matters: <REF, REF>`, description without the DRAFT prefix. Add the skill to 'Which skill controls which document' in areas/<area>/playbook.md. `bash tools/skills-sync`, then `bash tools/skills-sync --check` (exit 0).
8. Answers that are company facts not yet in knowledge/ (a position, an approval limit): offer the knowledge confirm flow (close skill, step 8).
9. `bash tools/budget-update --measure --run <R> --note "draft-skill <name>"` (the real token use from Claude Code's logs since the last measurement). It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "draft-skill <name>"`, once per model used (m: its BUDGET.md price key).
10. Tell the lawyer: the skill is approved; from the next run readers set `controlling_skill: <name>` on matching matters and work in its output shape; to change it, say "redraft <name>".

## Approving an area file
"approve the <area> playbook" (or intake file), after the lawyer has read it: set `status: approved`, raise `version` by one, and in playbook.md set `last_reviewed: <today>`. Changes asked for: apply them with their sources; the file stays draft until approved. Then tell the lawyer what is next.
