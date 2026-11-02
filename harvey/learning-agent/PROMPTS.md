# Messages to paste into the agent

Send these in order, one at a time. Check each reply before sending the next. Every pass updates the working files and saves them under the same names.

## 1. Build the email index

> Index pass 1. Create legal-email-index.md as a Markdown document in your workspace. Open every extracted email in the Vault (not the PST files), read its header and enough of the email to set the category and the conversation key, and add one line per email in the output format. Use the sent date from each header, never the Vault's dates. Then tell me: the total number of emails, the date range, the count per week and per category, and any file you could not open.

If the Vault is large and the reply stops, send:

> Continue the index pass from the next file not yet in the index. Save the file and report the counts.

## 2. Read in full, one period at a time, oldest first

Start with one week. If the reply says the period was too big, use half the period next time.

> Reading pass R01: emails sent from 2026-09-01 to 2026-09-07. Using legal-email-index.md, open and read in full every work email in this period not yet marked read: the message, the quoted chain and every attachment. Create or update legal-matters.md and legal-learning-register.md in the output format, mark each email read with "R01" in the index, and save all three files. Then report: emails in scope, emails read, emails you could not open, matters added and updated, and the counts before and after for each file.

Then R02 for the next week, and so on. Change the pass name and the dates every time.

## 3. Documents it asked for

> Documents for D003 and D007 are now in the Vault (our NDA mark-up and the commercial counsel's reply). Add them to the index, read them in full, update the matters and register entries they affect, and save all three files.

## 4. Build the reports, skills and knowledge

> Build reports/work-types.md and the front-door skill in the output format, from legal-matters.md and legal-learning-register.md. Save each as a Markdown document starting with an === FILE: folder/name.md === line.

Then, for each work type with three or more matters:

> Build the skill for the work type "NDA review" in the output format: SKILL.md, plus positions.md and precedents.md if needed. Use the working files, and re-open the emails of its matters wherever a point is unclear. Keep the skill set under about 15,000 words and SKILL.md under about 4,000; split it rather than drop evidence. Save each file as a Markdown document starting with an === FILE: folder/name.md === line. Mark it status: draft (unverified).

Then:

> Build the knowledge pack in the output format: one file per fact or fact set, plus knowledge/our-companies.md, knowledge/glossary.md and knowledge/code-key.md without the name column. Then build reports/open-questions.md and reports/coverage.md. Never put negotiation positions in the knowledge pack.

## Check, at any point

> Check the three working files. List emails in the index that are in a finished period but not marked read, duplicate matters, entries without evidence, reasons you inferred rather than saw, personal names or email addresses, outside parties named instead of coded, older facts shown as current, and any count that went down. Fix them and save the files.

## New conversation, or the files are not visible

Attach the latest saved copies of the three working files, then send:

> Here are the latest legal-email-index.md, legal-matters.md and legal-learning-register.md. Save them as your working files and continue from them.

## After adding another PST to the Vault

> A new PST with emails from <dates> was added to the Vault. Run an index pass for the new emails only, then tell me the new periods to read.
