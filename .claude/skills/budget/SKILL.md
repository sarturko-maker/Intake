---
name: budget
description: "Show the month's estimated spend, the cap, the mode and what the mode limits; record the actual bill; review where the same results could have cost less. Use for 'how much have we spent', 'budget', '/budget', 'budget actual 37.20', 'optimise', and 'where could we spend less'."
argument-hint: "[actual <USD>]"
---

# Budget

Rules: RULES.md 'Budget'. No subagents needed: do it yourself.

1. `bash tools/budget-update --show`. Asked for detail: also show the last ledger lines of BUDGET.md.
2. Tell the lawyer in plain words: the month; estimated spend against the cap, in USD and percent; the mode; the last actual bill and its date. Then what the mode limits (thresholds from BUDGET.md; defaults 70, 90, 100 percent):
   - full: everything.
   - lean: attachments read only as mark-ups and the pages that matter; no drafts.
   - minimal: emails are filed and briefs written; memory comes from the email text alone; the digest says "filed, not fully read".
   - paused: emails are filed only by reference tag or thread; everything else goes to please-check; nothing is read.
3. Say how the figure is made. In Claude Code, lines marked "measured" come from Claude Code's own logs on this computer: every model and subagent, priced at list prices; most of the cost is re-reading and caching the conversation at each step, not the documents. On a subscription plan this is what the same use would cost on the API. Elsewhere it is an estimate: characters read and written, divided by four, at the list prices, times the overhead factor; the actual bill corrects it. Asked for the latest figure: `bash tools/budget-update --measure` first.
4. "budget actual 37.20": `bash tools/budget-update --actual 37.20`. Add `--date YYYY-MM-DD` when the lawyer gives the bill's date. Show the new overhead factor and mode.
5. The lawyer wants another cap or new prices: they edit `cap_usd:` or `prices_usd_per_mtok:` in BUDGET.md themselves. You write BUDGET.md only through the tool. Afterwards run `bash tools/budget-update --show`.
6. End with what to do next: once a month, type the actual bill ("budget actual <amount>"); if the mode is lean or lower, say what waits until next month or a higher cap.

## Spend less ("optimise", "where could we spend less")

The question: where could we have spent fewer tokens for the same result? Rules: RULES.md 'Budget' (Spend less) and hard rule 13.

1. Run `bash tools/budget-update --measure` and read its split by step (main session, reader xN, filer ..., each with its model), then the `wasted-effort` lines in WORKFLOW-LOG.md since the last review (the date of the newest changes/optimise-*.md) and the ledger lines of BUDGET.md for the same runs. The split shows which steps used which model; a step on Opus that the default would do is a saving. Few lines yet: look at the last runs instead, in JOURNAL.md, the digests and the ledger: readers per run, characters per run, the biggest reads.
2. Group them by cause, and estimate each group's saving in characters and in USD (its share of the runs' characters times their estimated cost). Common causes:
   - a reader started for a matter that only had an interim email, or a filer for five emails or fewer;
   - a whole document read when the thread turned on one clause (contents page, then the clause); a mark-up read in full (redline-changes gives only the changes); a playbook read whole for one point (area-lines);
   - a full read where the short read would do (one email of ours, at most one attachment);
   - the same text read twice: a quoted thread, a forwarded copy, an attachment already hashed;
   - Opus used where the default model gives the same result;
   - matter.md rewritten for a one-line change (an edit to the frontmatter would do);
   - long outputs nobody reads.
3. Propose at most five changes, the biggest saving first. For each: what to change, the saving, and where it goes:
   - **a legal skill** (skills/<area>/<name>/SKILL.md): the line for its 'What to read' section. Record it as a learning line (`printf '%s\n' "note | what to read: <the line> | optimise <today>" | bash tools/learn-add --matter chat --work-type <slug>`); the next learning pass writes it into the skill. An approved skill: say the line, and apply it when the lawyer says so;
   - **a house setting or habit** (batch size, mode, which emails to drop): the lawyer decides;
   - **the workspace's own files** (RULES.md, tools/, skills/operations/, .claude/): never edit them here. Write the change into the maintainer note.
4. Write changes/optimise-<YYYY-MM-DD>.md: the groups, the savings, the proposals, and at the end a "Note for the maintainer" block that is safe to share: kinds of work and documents, references, step names and numbers only. No names of people or organisations, no quotes, no figures from matters.
5. Reply in plain words: the total that could have been saved, the top three changes in one line each, and which are the lawyer's to decide. Say the maintainer note can be pasted to whoever keeps the repository.
6. Learning comes last in the spend order, never first: do not suggest cutting the reads a skill still needs as evidence.
