# Harvey learning set-up: how to run it

Goal: learn how the legal team works from a month or more of emails. The emails come mostly from the intake mailbox, plus some of your own. The output is drafts of three things: a work-types report, skills (how we work) and knowledge (facts about the company). You and Claude Code check everything later.

## What we know from the test (73 emails)

- A PST uploaded to a Vault is split into one file per email. Each attachment stays inside the email it came with, so the agent can read both together.
- The Vault's own dates are the upload date, not the sent date. The agent must read the sent date from each email's header. The instructions require this.
- The agent can open each email and read it in full. It does not have to rely on search.

## The method

The agent keeps three working files, saved as Markdown documents and updated in place:

1. **`legal-email-index.md`**: one line per email in the Vault: ID, sent date, sender's role, subject, category (work, noise or sensitive), conversation, matter, and whether it has been read. This is what makes the passes complete: every email is listed, so none is missed.
2. **`legal-matters.md`**: one paragraph per matter, with a short header (work type, who asked, who handled it, effort, outcome).
3. **`legal-learning-register.md`**: everything learned across matters:
   - the work-types report;
   - ways of working;
   - positions and precedents;
   - the front door;
   - knowledge;
   - our companies, the code key, the glossary and roles;
   - open questions and documents to fetch.

You run it in passes:

1. **Index pass.** The agent opens every email once and builds the index. It reports the totals, the date range and the count per week, which tells you how to size the next step.
2. **Reading passes, oldest first, a week at a time.** The agent reads in full every work email of that week, with its attachments. It builds and updates the matters and the register, and marks the emails as read.
3. **Building passes.** The work-types report, the front-door skill, one skill per work type, and the knowledge pack.

## Set up

1. Export the intake mailbox for the period as a PST under 500 MB. Split by month if needed. A PST of your own relevant folders can go into the same Vault.
2. Create a Vault project, for example "Legal learning: September to October", and upload the PST files.
3. In Agent Builder, create an agent called "Legal team learning agent":
   1. Paste `AGENT-INSTRUCTIONS.md` into its instructions.
   2. Add `OUTPUT-FORMAT.md` as a knowledge source called "Output format".
   3. Add the Vault project as a knowledge source.
   4. Optional: add a knowledge source called "Our templates" with your standard NDA, MSA, guarantee and LPA forms.
   5. Turn off web search.
4. Use the messages in `PROMPTS.md`, in order.

## Each pass

- Check the reply: emails in scope, emails read, anything it could not open, and confirmation that the files were saved with no count going down.
- If a week was too much, the agent says so and reads the first part. Send the rest, or halve the period next time.
- Every few passes, download the three working files and keep dated copies. They are your backup, and what you attach if a new conversation cannot see them.
- "Documents to fetch" lists what is missing, usually our replies and mark-ups from the lawyers' mailboxes. Add them to the Vault (a PST of the relevant sent items works) and use the "documents" message.

## Afterwards

- Save the three working files and everything the building passes produce into `seeds/harvey/` in the workspace.
- Claude Code checks them, asks you the open questions, and turns them into approved skills and knowledge after your yes.

## Optional: a review table as a cross-check

`REVIEW-TABLE-COLUMNS.md` defines a review table over the same Vault: one row per email, 24 columns. It is a second, independent extraction. Export it to Excel and give it to Claude Code to compare with the agent's files. It is useful once, after the first month, to see what the agent missed.

## Before sharing

- People appear by role only.
- Our own companies appear by their full legal names.
- Outside parties appear as codes (C1, S1) in everything the agent builds.
- Delete the name column of the code key before sharing outside Harvey.
- Sensitive emails are indexed without a subject and never used.
