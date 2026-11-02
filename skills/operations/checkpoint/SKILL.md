---
name: checkpoint
description: "Wrap up a phase of an open matter without closing it: checkpoint note, subject history and follows links, up to three why questions kept as decision facts, knowledge confirm flow. Use for 'checkpoint 2026-0042', '/checkpoint REF', for example after a signed NDA or an agreed round."
argument-hint: "<REF>"
model: opus
---

# Checkpoint

The close wrap-up without closing: status, closed date and flags stay as they are. Rules: RULES.md 'Wrap-up and learning', 'Memory files', 'Knowledge'. Ask in plain chat, one short question at a time; never assume an answer.
No subagents in this harness: do the distiller's steps yourself.
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

1. Folder: the `folder` of REF's row in INDEX.csv, or `find areas -type d -name '<REF>_*' -not -path '*/history/*'`. None: say so and stop.
2. `bash tools/budget-update --mode`: minimal or paused → stop; tell the lawyer the checkpoint waits for budget.
3. `bash tools/matter-sync <REF> --run <R>`: registers any file not yet recorded, in agent/ or human/.
4. Follows links: this matter's `follows:`, and the INDEX.csv rows whose `follows` column is REF.
5. Dispatch the distiller, call 1, with R, mode, REF, folder, the follows links and "checkpoint". It:
   a. re-reads the matter from the start: matter.md, brief.md, every facts.md line (superseded too), log.md, documents.md, corrections.md, both rosters, correspondence oldest first, the files in human/, subject.md, the controlling skill;
   b. records new files (documents.md read and summary, log line);
   c. rewrites matter.md whole by the matter-memory skill, adding `### Checkpoint <today>` under '## Closing note': the phase reached, what was decided and why, what is still open, what comes next; every claim with a pointer; earlier checkpoints condensed, never dropped;
   d. rewrites subject.md: this matter's line under Matters (status, one line); 'Standing positions agreed before' (agreed so far, with pointers); 'What usually follows what' with each follows link ("NDA 2026-0036, then MSA 2026-0042");
   e. writes at most three why questions under '## Questions for the lawyer', only where the record shows a choice without its reason: a concession, a departure from the playbook or a skill, an unexpected turn;
   f. returns the questions; company facts learned that may belong in knowledge/ (one sentence each, with source, proposed type, file and owner); any correction or re-filing of the agent's work here; last line `chars read: N, chars written: M`.
6. Ask the why questions in chat, one at a time, and wait for each answer. Then the distiller, call 2, with the answers (declined ones marked): it appends one line per answer to facts.md, `F<next> | <today> | decision | valid_from=<today> | source=lawyer in chat <today> | supersedes= | <the answer, one sentence>`, runs `bash tools/lint-facts <folder>/facts.md`, and folds the answers into matter.md. Declined: nothing recorded. No subagents: do it yourself with your edit tool.
7. Knowledge confirm flow: as the close skill, step 8. One chat sentence per fact; write only after a yes, stamped `confirmed_by` and `last_confirmed`; a standard answer names its owning department.
8. Append to log.md `<time> | checkpoint <today> | - | <R>`. The agent was corrected in this matter: append to WORKFLOW-LOG.md `<time> | <R> | corrected | <REF>: <what, one line>`.
9. `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "checkpoint <REF>"` once per model used (m: the BUDGET.md price key of that model). Then `bash tools/index-rebuild --run <R>`.
10. Tell the lawyer: what the checkpoint recorded, the follows links now in subject.md, the matter's next step, and that "close <REF>" ends it when the work is done.
