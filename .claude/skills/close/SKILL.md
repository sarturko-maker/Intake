---
name: close
description: "Close a matter on the lawyer's word and run its wrap-up: closing note, subject profile, up to three why questions kept as decision facts, knowledge confirm flow. Use for 'close 2026-0042', '/close REF', and for each closed-by-lawyer line from index-rebuild (already closed in INDEX.csv, wrap-up-pending)."
argument-hint: "<REF>"
---

# Close

Closing is the lawyer's decision and only a status: nothing moves or is deleted, and new mail reopens the matter by itself. Rules: RULES.md 'Wrap-up and learning', 'Memory files', 'Knowledge'. Ask in plain chat, one short question at a time; never assume an answer.
No subagents in this harness: do the distiller's steps yourself.
R = the open run's id when intake or status calls this skill; else `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

## Close
1. Folder: the `folder` of REF's row in INDEX.csv, or `find areas -type d -name '<REF>_*' -not -path '*/history/*'`. None: say so and stop.
2. Already `status: closed` (the lawyer typed it in INDEX.csv and index-rebuild set it): go to Wrap-up.
3. Else edit matter.md frontmatter with your edit tool (hooks copy history; hooks not live: `bash tools/history-copy <folder>/matter.md` first): `status: closed`, `closed: <today>`, add `wrap-up-pending` to flags. Append to log.md `<time> | closed by the lawyer in chat | - | <R>`. Journal `closed-by-lawyer | <REF> | <folder> | lawyer in chat | -`.
4. `bash tools/budget-update --mode`: minimal or paused → stop here. Tell the lawyer the wrap-up waits for budget; wrap-up-pending stays.

## Wrap-up
5. Files with no documents.md row in correspondence/, documents/ or work-product/ (not bundle-*): `bash tools/place-email --register <path> --run <R>` each.
6. Dispatch the distiller, call 1, with R, mode, REF, folder and "close". It:
   a. re-reads the matter from the start: matter.md, brief.md, every facts.md line (superseded too), log.md, documents.md, corrections.md, both rosters, correspondence oldest first, work-product/, subject.md, the controlling skill;
   b. records new files (documents.md read and summary, log line);
   c. rewrites matter.md whole by the matter-memory skill, with '## Closing note': the outcome, what was decided and why, what we conceded, what to remember next time; every claim with a pointer;
   d. rewrites subject.md: this matter's line under Matters (closed, one line); 'Standing positions agreed before' (agreed here, with pointers); 'What usually follows what' from follows links ("NDA 2026-0036, then MSA 2026-0042");
   e. writes at most three why questions under '## Questions for the lawyer', only where the record shows a choice without its reason: a concession, a departure from the playbook or a skill, an unexpected outcome;
   f. returns the questions; company facts learned that may belong in knowledge/ (one sentence each, with source, proposed type, file and owner); any correction or re-filing of the agent's work here; last line `chars read: N, chars written: M`.
7. Ask the why questions in chat, one at a time, and wait for each answer. Then the distiller, call 2, with the answers (declined ones marked): it appends one line per answer to facts.md, `F<next> | <today> | decision | valid_from=<today> | source=lawyer in chat <today> | supersedes= | <the answer, one sentence>`, runs `bash tools/lint-facts <folder>/facts.md`, and folds the answers into matter.md. Declined: nothing recorded. No subagents: do it yourself with your edit tool.
8. Knowledge confirm flow, per candidate fact: one chat sentence with fact, source and owner, for example "Shall I add to knowledge: '<fact>' (from <REF>)? Which department owns it?". Write only after a yes: one file in the type's folder under knowledge/, frontmatter per RULES.md 'Knowledge', `origin: matter`, `source: <REF> <file>`, `confirmed_by: <lawyer_name in house/brief.md>`, `last_confirmed: <today>`; a standard answer also names its owning department. If it changes an existing entry, set `valid_until: <today>` on the old entry and write a new one; never edit silently. Then index the new file (index skill, those files only).
9. Edit matter.md frontmatter: remove `wrap-up-pending`. Log `wrap-up done`. Unanswered questions stay in matter.md.
10. The agent was corrected in this matter (corrections.md lines, re-filed emails): append to WORKFLOW-LOG.md `<time> | <R> | corrected | <REF>: <what, one line>`.
11. `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "wrap-up <REF>"` once per model used (m: the BUDGET.md price key of that model). Then `bash tools/index-rebuild --run <R>`.

## Next
12. Tell the lawyer: closed and wrapped up, and what was recorded. If confirmed_outcome, lawyer_minutes or accepted_unchanged are empty, ask them to fill those in INDEX.csv or say them in a sentence. New mail on this matter reopens it by itself.
