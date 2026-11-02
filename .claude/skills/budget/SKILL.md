---
name: budget
description: "Show the month's estimated spend, the cap, the mode and what the mode limits; record the actual bill. Use for 'how much have we spent', 'budget', '/budget', and 'budget actual 37.20'."
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
3. Say how the estimate works: characters read and written, divided by four, at the list prices in BUDGET.md, times the overhead factor. It is an estimate; the actual bill corrects it.
4. "budget actual 37.20": `bash tools/budget-update --actual 37.20`. Add `--date YYYY-MM-DD` when the lawyer gives the bill's date. Show the new overhead factor and mode.
5. The lawyer wants another cap or new prices: they edit `cap_usd:` or `prices_usd_per_mtok:` in BUDGET.md themselves. You write BUDGET.md only through the tool. Afterwards run `bash tools/budget-update --show`.
6. End with what to do next: once a month, type the actual bill ("budget actual <amount>"); if the mode is lean or lower, say what waits until next month or a higher cap.
