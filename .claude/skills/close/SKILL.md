---
name: close
description: "Close a matter on the lawyer's word and run its wrap-up without asking anything: closing note with the reasons the record shows, subject profile, and what the matter teaches recorded for the skills and the knowledge base. Use for 'close 2026-0042', '/close REF', 'close 2026-0042: <why>', 'close 2026-0042 and ask me why', and for each closed-by-lawyer line from index-rebuild (already closed in INDEX.csv, wrap-up-pending)."
argument-hint: "<REF>"
model: opus
---

# Close

Closing is the lawyer's decision and only a status: nothing moves or is deleted, and new mail reopens the matter by itself. The wrap-up asks nothing: the distiller works the reasons out of the record and marks its own readings as assumed. Rules: RULES.md 'Wrap-up and learning', 'Memory files'.
Only if the harness has no subagents: do the distiller's steps yourself.
R = the open run's id when intake or status calls this skill; else `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

## Close
1. Folder: the `folder` of REF's row in INDEX.csv, or `find areas -type d -name '<REF>_*' -not -path '*/history/*'`. None: say so and stop.
2. Already `status: closed` (the lawyer typed it in INDEX.csv and index-rebuild set it): go to Wrap-up.
3. Else edit matter.md frontmatter with your edit tool (hooks copy history; hooks not live: `bash tools/history-copy <folder>/matter.md` first): `status: closed`, `closed: <today>`, add `wrap-up-pending` to flags. Append to log.md `<time> | closed by the lawyer in chat | - | <R>`. Journal `closed-by-lawyer | <REF> | <folder> | lawyer in chat | -`.
4. `bash tools/budget-update --mode`: minimal or paused → stop here. Tell the lawyer the wrap-up waits for budget; wrap-up-pending stays.

## Wrap-up
5. `bash tools/matter-sync <REF> --run <R>`: registers any file not yet recorded, in agent/ or human/.
6. What the lawyer said with the close ("close 2026-0042: we gave way on the cap because they are a strategic customer", an outcome, minutes): write it down first. Reasons and context: the note skill, steps 2 and 3 (a dated "(you said)" line in agent/notes.md). confirmed_outcome, lawyer_minutes, accepted_unchanged: into matter.md frontmatter as the status skill does. Never ask for any of them.
7. Dispatch the distiller, one call, with R, mode, REF, folder and "close". It:
   a. re-reads the matter from the start;
   b. records new files, and the lawyer's reasons from notes.md as `decision` facts;
   c. rewrites matter.md whole with '## Closing note': the outcome, what was decided and why, what we conceded, what to remember next time; a reason the record does not give is its own reading, marked `(assumed: ...)`, with the point listed under '## Questions for the lawyer' (at most three);
   d. rewrites subject.md: this matter's line under Matters (closed, one line); 'Standing positions agreed before'; 'What usually follows what' from follows links;
   e. records what the matter teaches with learn-add: evidence for its type of work, company facts, open points. The learning pass turns these into the working skill and knowledge entries; nobody confirms them one by one.
8. Only when the lawyer asked for it ("close 2026-0042 and ask me why", "ask me why"): put the distiller's open points to the lawyer, one at a time, at most three; then the distiller, call 2, with the answers (declined ones marked). It records each as a `decision` fact (`source=lawyer in chat <today>`) and a learning line with origin lawyer, and folds them into matter.md. Otherwise ask nothing: the points stay in matter.md with the readings taken, and the lawyer can settle one at any time ("note <REF>: ...").
9. Edit matter.md frontmatter: remove `wrap-up-pending`. Log `wrap-up done`.
10. The agent was corrected in this matter (corrections.md lines, re-filed emails): append to WORKFLOW-LOG.md `<time> | <R> | corrected | <REF>: <what, one line>`.
11. `bash tools/budget-update --measure --run <R> --note "wrap-up <REF>"` (the real token use from Claude Code's logs since the last measurement). It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "wrap-up <REF>"`, once per model used (m: its BUDGET.md price key). Then `bash tools/index-rebuild --run <R>`.

## Next
12. Tell the lawyer in three lines: closed and wrapped up; the closing note in one line, with any reason it had to assume; and that a reason or a correction can be added at any time ("note <REF>: ..."). New mail on this matter reopens it by itself. Do not ask for an outcome, minutes or anything else.
