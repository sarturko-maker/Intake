---
name: checkpoint
description: "Wrap up a phase of an open matter without closing it and without asking anything: checkpoint note with the reasons the record shows, subject history and follows links, and what the phase teaches recorded for the skills and the knowledge base. Use for 'checkpoint 2026-0042', '/checkpoint REF', 'checkpoint 2026-0042 and ask me why', for example after a signed NDA or an agreed round."
argument-hint: "<REF>"
model: opus
---

# Checkpoint

The close wrap-up without closing: status, closed date and flags stay as they are. It asks nothing: the distiller works the reasons out of the record and marks its own readings as assumed. Rules: RULES.md 'Wrap-up and learning', 'Memory files'.
Only if the harness has no subagents: do the distiller's steps yourself.
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

1. Folder: the `folder` of REF's row in INDEX.csv, or `find areas -type d -name '<REF>_*' -not -path '*/history/*'`. None: say so and stop.
2. `bash tools/budget-update --mode`: minimal or paused → stop; tell the lawyer the checkpoint waits for budget.
3. `bash tools/matter-sync <REF> --run <R>`: registers any file not yet recorded, in agent/ or human/.
4. What the lawyer said with the request (a reason, context): the note skill first, steps 2 and 3 (a dated "(you said)" line in agent/notes.md).
5. Follows links: this matter's `follows:`, and the INDEX.csv rows whose `follows` column is REF.
6. Dispatch the distiller, one call, with R, mode, REF, folder, the follows links and "checkpoint". It:
   a. re-reads the matter from the start;
   b. records new files, and the lawyer's reasons from notes.md as `decision` facts;
   c. rewrites matter.md whole, adding `### Checkpoint <today>` under '## Closing note': the phase reached, what was decided and why, what is still open, what comes next; earlier checkpoints condensed, never dropped; a reason the record does not give is its own reading, marked `(assumed: ...)`, with the point listed under '## Questions for the lawyer' (at most three);
   d. rewrites subject.md: this matter's line under Matters (status, one line); 'Standing positions agreed before' (agreed so far, with pointers); 'What usually follows what' with each follows link ("NDA 2026-0036, then MSA 2026-0042");
   e. records what the phase teaches with learn-add: evidence for its type of work, company facts, open points.
7. Only when the lawyer asked for it ("checkpoint 2026-0042 and ask me why"): put the distiller's open points to the lawyer, one at a time, at most three; then the distiller, call 2, with the answers. Otherwise ask nothing.
8. Append to log.md `<time> | checkpoint <today> | - | <R>`. The agent was corrected in this matter: append to WORKFLOW-LOG.md `<time> | <R> | corrected | <REF>: <what, one line>`.
9. `bash tools/budget-update --measure --run <R> --note "checkpoint <REF>"` (the real token use from Claude Code's logs since the last measurement). It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "checkpoint <REF>"`, once per model used (m: its BUDGET.md price key). Then `bash tools/index-rebuild --run <R>`.
10. Tell the lawyer in three lines: what the checkpoint recorded, with any reason it had to assume; the matter's next step; and that "close <REF>" ends it when the work is done.
