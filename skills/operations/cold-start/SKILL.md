---
name: cold-start
description: "First run on a machine, or when TOOLING.md is missing: check the house files, set up and verify tools, build the area skeleton, prove the protections, index what the lawyer put in, then run intake if mail is waiting. Use for 'cold start', '/cold-start', 'set up the workspace'."
---

# Cold start

Show each result; never assert it. Ask only what the set-up cannot go on without (the house files, an install). Never invent names, areas or positions.
Only if the harness has no subagents: do the indexer's and drafter's work yourself, one folder or area at a time.
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`.

## 1. House files
0. No house/brief.md or house/areas.md: `bash tools/init-workspace` copies the blank ones in.
1. Read RULES.md, HANDOFF.md if present, house/brief.md, house/areas.md, BUDGET.md if present.
2. Stop if house/brief.md or house/areas.md has `status: template`, or a brief key is empty: organisation, legal_entities, house_domains, legal_addresses, intake_mailbox, timezone, lawyer_name. Tell the lawyer exactly what to fill in: each empty key by name, the body prompts still unanswered, each area block to check (key, name, code, unit_label, description, sub_areas, subject_rule, examples), and `status: ready` in both files. reference_prefix may stay empty. Offer to help fill them in from the lawyer's answers: show each change and write it only after a yes (Claude Code also asks for permission).

## 2. Tools
3. `bash tools/tooling-setup`. Show what it found and what is missing.
4. Something missing: ask once, in chat, the question it prints ("May I install: ...?"). Yes: `bash tools/tooling-setup --install` (it stops for a terminal confirmation or a winget agreement: run it again with `--install --yes`; the lawyer's yes covers that). No: keep the fallbacks it recorded. Show the TOOLING.md lines.
5. A blocked item (for example Python by policy): keep its fallback; append to WORKFLOW-LOG.md `<time> | <R> | workaround | <item>: <fallback>`.

## 3. Skeleton
6. Per area block in house/areas.md: areas/<key>/, areas/<key>/proposals/, and areas/<key>/<sub-area>/ for each declared sub-area. Always areas/general/. Subject folders come later, with matters.
7. knowledge/TYPES.md must exist (it ships with the workspace). Missing: tell the lawyer.
8. `bash tools/budget-update --init`, then `bash tools/skills-sync`.
9. Prove the deny rules: try to create areas/_protection-test/human/corrections.md with Write (one line). Refused: verified-live (nothing was created). Allowed: delete that test folder at once: not-live. Replace the `deny rules` line in TOOLING.md with `deny rules | verified | - | - | verified-live: write to a human-only file refused <date>` or `deny rules | configured | - | RULES.md 'Protections' obligations | not-live: the write went through and was removed <date>`. house/ is not denied: it asks the lawyer before every change.
10. Prove the hooks on a real file. With your write tool, create areas/general/unfiled/subject.md from skills/operations/matter-memory/templates/subject.md (subject unfiled, name Unfiled, area general, sub_area empty, created today). Then edit it once: under '## Who they are' write "Mail that fits no area, kept here until the lawyer decides (house/areas.md)." A copy in areas/general/unfiled/history/ means verified-live. Replace the `hooks` line the same way. Not-live: RULES.md 'Protections' applies (`bash tools/history-copy` before every memory rewrite, `bash tools/lint-facts` after every facts.md append). Never delete a file to tidy up a test.
11. `bash tools/scan-changes --run <R> --write-manifest` (the first run reports everything as new).

## 4. Index
12. Dispatch the indexer on every file in house/, knowledge/ and seeds/ (method and format: index skill). It writes knowledge/INDEX.md ending with 'Needs an owner or date': dropped documents lacking owner, source or validity date. Owners are never guessed.
13. From its report, with nobody asked (index skill, step 3): standard-answer sets, entity lists and people lists are split into one working knowledge entry each; material that fits no type three times over gets a type in knowledge/TYPES.local.md. Say what was done in the report.

## 5. Area files
14. Per area without them, one drafter per area in parallel: areas/<key>/playbook.md and areas/<key>/intake.md from skills/operations/cold-start/templates/playbook.md and intake.md, `status: draft`. Fill only from the area's block in house/areas.md, house/brief.md and the knowledge files knowledge/INDEX.md points to, each point with its source. Where nothing is known, keep the prompt and write "Not known yet." Never invent a position.
15. `bash tools/budget-update --measure --run <R> --note "cold start"` (the real token use from Claude Code's logs since the last measurement). It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "cold start"`, once per model used (m: its BUDGET.md price key).
16. `bash tools/scan-changes --run <R> --write-manifest` again, so the next run sees only new changes.

## 6. Inbox
16b. `bash tools/learn-index` (creates learning/). Files in seeds/ (Harvey output): the first learning pass takes them in as leads.
17. inbox/ has files: run the intake skill. Otherwise run the status skill (the first digest, with 'Needs an owner or date').

## 7. Report
18. Five lines or fewer: tools found, installed or blocked, with fallbacks; what was created; what was indexed; what needs an owner or date; where to look (digests/LATEST.md, INDEX.md, inbox/please-check/).
19. Tell the lawyer what to do next: drop emails into inbox/, sent items included, and say "process the inbox". Skills and knowledge entries then write themselves as matters are read (learning/index.md shows them); the lawyer reads them when they like and says what to change. The draft playbook.md and intake.md per area are in use from the start; "approve the commercial playbook" stamps one when the lawyer has read it.
