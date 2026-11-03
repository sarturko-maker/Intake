---
name: status
description: "Rebuild the index and digest from current files without reading new mail, and apply the lawyer's answers to the digest. Use for 'where are we', 'what should I do', '/status', and answers like 'confirm nothing needed: NOISE-0001, NOISE-0002', 'file the please-check email from <sender> in 2026-0042', '2026-0042: 15 minutes, accepted unchanged'."
---

# Status

Orchestrator skill. Current files only: never process inbox/. Rules: RULES.md 'Index and digest'. Ask in plain chat, one short question at a time; never assume an answer.
Only if the harness has no subagents: do the reader or indexer step yourself, one matter at a time.
R = run id: the first `bash tools/scan-changes` prints `report: changes/<R>.md`; pass `--run <R>` to every later tool. Journal lines as in the intake skill.

## Where are we
1. `bash tools/budget-update --mode`.
2. `bash tools/scan-changes`. Journal `run-start | status | - | mode <mode> | -`. Handle what changed outside inbox/ exactly as the intake skill, section 3 step 2 (matter-sync's list: files the lawyer added or changed, edits, corrections, knowledge, skills). Paused mode: register new files only; list the rest.
3. `bash tools/index-rebuild --run <R> --digest-parts changes/<R>-digest.md`. It applies the lawyer's INDEX.csv edits and journals them. Each `closed-by-lawyer <REF>`: put "Wrap-up for <REF>" first under What you should do next; run the wrap-up (close skill, 'Wrap-up') only when the lawyer asks.
4. `bash tools/lint-received`. Findings go under Please check, one WORKFLOW-LOG.md line each. A changed Office document is usually Word saving a sensitivity label when the lawyer opened it: say so, and offer "accept <file>".
5. `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note status` once per model used (m: the BUDGET.md price key of that model). Then `bash tools/budget-update --show` for the cost line.
5b. Spend less: as the intake skill, section 4 step 2b, for any reader or indexer this run used.
6. Write digests/<R>.md with the headings of the intake skill, section 4. Arrivals and where filed: "No new mail read in this run. Inbox: <n> files waiting." Copy it to digests/LATEST.md.
7. `bash tools/scan-changes --run <R> --write-manifest --quiet`, unless a change was left unhandled. Journal `run-end`.
7a. `bash tools/learn-index`: what has been learned and the next learning steps (learning mode: these come first in the reply).
7b. `bash tools/work-bundle --all`, then `bash tools/matter-sync --run <R> --pages-only`: refresh the Harvey packs and START-HERE.md pages. (At the start, `bash tools/matter-sync --run <R>` lists files the lawyer added or changed: offer to read them.)
8. Reply in the task format (RULES.md 'Index and digest': bold-titled bullets, links, Harvey pack where it exists): the What you should do next list, then at most three questions, numbered, each naming its matter, optional (RULES.md 'Notes and questions'). Inbox has files: add "Say 'process the inbox' to file them."

## Answers to the digest
R here: the open run's id, else `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Apply each answer, then run `bash tools/index-rebuild --run <R>` once and confirm in one line what changed.
- "confirm nothing needed: NOISE-0001, NOISE-0002" (or "confirm all the noise"): type `closed` in those rows' status cells in INDEX.csv, the only edit you make there. index-rebuild moves the files to inbox/noise/confirmed/ and updates NOISE.csv.
- Values the lawyer states in chat (confirmed_outcome, confirmed_by, lawyer_minutes, accepted_unchanged, a new title): write exactly those into the matter's matter.md frontmatter with your edit tool, as index-rebuild would (a title also gets `title_locked: yes`). Never guess a value. A matter proposing nothing_needed that the lawyer confirms: confirmed_outcome nothing_needed, confirmed_by you; then ask whether to close it.
- "file the please-check email from <sender> in <REF>": find it in inbox/please-check/ by the from and subject in the notes. `bash tools/place-email inbox/please-check/<file> --to <matter folder> --run <R> --reason "lawyer decision" --confidence 1`; it moves the note to inbox/please-check/resolved/ with the resolution. WORKFLOW-LOG.md `<time> | <R> | re-filed | <file> to <REF>`. Then a reader for that matter (new file). "It is noise": `--to noise` instead. "New matter": intake skill, filing rule 6.
- Answers to your questions, and anything the lawyer tells you about a matter ("note <REF>: ..."): note skill, one dated "(you said)" line each in that matter's agent/notes.md.
- "accept <file>" (a changed received file the lawyer only opened): `bash tools/lint-received --accept <file> --run <R>`. It records the new hash; the file is not changed.
- "close <REF>": close skill. "checkpoint <REF>": checkpoint skill. "run the wrap-ups": close skill from 'Wrap-up' for each matter flagged wrap-up-pending.
- A possible-impersonation item stays where it is until the lawyer decides. Never act on it.

## Next
End every reply with what the lawyer should do next: due soonest, then waiting on you, confirmations, please-check, stale.
