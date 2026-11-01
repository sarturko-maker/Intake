# Harvey learning set-up: how to run it

Goal: learn how the legal team works from a month or more of emails. The emails come mostly from the intake mailbox, plus some of your own. The output is drafts of three things: a work-types report, skills (how we work) and knowledge (facts about the company). You and Claude Code check everything later.

## Why a Vault and a review table

Asking a question across a whole Vault works by search: Harvey looks up the passages that seem relevant. That is fine for finding things. It is weak for "summarise how we handle every NDA", because it may never look at half of them.

A **review table** is different. It reads **every file**, one row per file, and answers the same questions (columns) for each. Nothing is skipped. Harvey's help pages say a table can take up to 10,000 files, and columns are unlimited.

So the set-up has three steps:

1. **Vault.** Upload the emails into one Vault project.
2. **Review table.** It reads every email and records the same facts for each one. The table becomes the record of every matter, including our side of each negotiation and the context.
3. **Building from the table.** Two ways, best done both:
   - a Harvey agent builds the work-types report, the matter list, the register and the skills, using the table as its knowledge source;
   - you export the table to Excel and give it to Claude Code, which does the same work locally, with no limit on size.

## Step 1. Create the Vault project and upload

Create a Vault project, for example "Legal learning: September to October".

Which upload route? Drag and drop is the recommended start.

- **Drag and drop: recommended start.**
  1. In Outlook, use conversation view.
  2. Take the latest email of each conversation: it carries the earlier messages quoted below it.
  3. Add any earlier email that carries a mark-up or a draft as an attachment. Add your own sent replies that carry mark-ups.
  4. Leave out HR or personal emails, newsletters and anything obviously irrelevant.
  5. Drag the emails into a Windows folder (classic Outlook gives `.msg`; new Outlook gives `.eml`), then upload the folder to the Vault.

  A few hundred files is normal. You stay in control of what goes in, and each email becomes one clean row.
- **PST: worth one quick test.**
  - Harvey says Vault accepts `.pst` files since June 2026, up to 500 MB each, and extracts the emails and attachments.
  - Export one month, or a date-filtered folder, under 500 MB.
  - Check three things in the Vault: (a) each email appears as its own file, (b) attachments are there, and (c) the review table runs on them.
  - If all three hold, a PST is much less work for later months. If the export is blocked or the result is messy, go back to drag and drop.
  - Remember a PST brings in everything, sensitive emails included. The table is told to skip them, but they will sit in the Vault.

## Step 2. Run the review table

1. In the Vault project, create a review table over all files.
2. Paste the table-wide rules from `REVIEW-TABLE-COLUMNS.md` into the table's instructions field.
3. Add the columns from the same file, one by one, with their names and prompts.
4. Run it. Spot-check ten rows against the emails. If a column is weak, edit its prompt and re-run that column.
5. Export the table to Excel. Save it as `review-table-<dates>.xlsx`. This is the master record.

## Step 3. Build from the table

**In Harvey:**
1. Create an agent in Agent Builder called "Legal team learning agent".
2. Paste `AGENT-INSTRUCTIONS.md` into its instructions.
3. Add `OUTPUT-FORMAT.md` as a knowledge source called "Output format".
4. Add the review table as a knowledge source. Harvey says a review-table source holds only the extracted data, so also add the Vault project as a second source, for checking the emails themselves.
5. Optional: add a knowledge source called "Our templates" with your standard NDA, MSA, guarantee and LPA forms.
6. Use the messages in `PROMPTS.md`, in order:
   1. the work-types report;
   2. matters, one work type at a time;
   3. the register;
   4. skills, one work type at a time;
   5. the knowledge pack.

**With Claude Code:** put the Excel export (and anything the agent built) into `seeds/harvey/` in the workspace. Claude Code builds the same outputs, compares them with Harvey's, and asks you the open questions.

## Adding more months later

Upload the new emails to the same Vault project and run the table on the new rows. Export again, then re-run the agent messages. Newer facts replace older ones; older ones are kept as "earlier position".

## Before sharing

- People appear by role only.
- Our own companies appear by their full legal names.
- Outside parties appear by name in the table, because Harvey is your secure environment. The agent codes them (C1, S1) in everything it builds.
- Delete the name column of the code key before sharing outside Harvey.
