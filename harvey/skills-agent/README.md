# Harvey skills scout: how to run it

A quick first draft from a batch of emails in a Harvey Vault:

1. the types of work legal does, with how often each comes up;
2. a draft skill for each common type, written as how we think, not as rules;
3. a map of the facts each type of work needs (the knowledge needs), with any facts seen as leads.

Harvey's drafts are leads, not answers. Claude Code checks each line against what it has learned from your daily drops, interviews you, and only then turns it into an approved skill or knowledge entry. Your daily drops into Claude Code carry on as before. This just speeds things up.

The week-by-week `harvey/learning-agent/` is the thorough version of the same idea. Use one or the other.

## Why a review table first

A Harvey agent finds emails in a Vault by search, so on a large Vault it can miss some. A review table reads every email, one at a time, and gives one row per email. The agent then works from the table, which is complete, and opens single emails only for detail. That gives a better spread than search alone.

## Steps

1. **Vault.** Create a Vault project, for example "Legal skills scout: September to October". Upload the emails: .msg or .eml files, or a PST under 500 MB per file. Attachments stay inside their emails.
2. **Review table.** In the Vault, create a review table over all the files with the columns in `REVIEW-TABLE.md`: paste the table-wide instructions, then add each column with its prompt. Run it, check a few rows, and export it to Excel as `email-review.xlsx`.
3. **Agent.** In Agent Builder, create an agent called "Legal skills scout":
   1. Paste `AGENT-INSTRUCTIONS.md` into its instructions.
   2. Add `OUTPUT-FORMAT.md` as a knowledge source called "Output format".
   3. Add the exported `email-review.xlsx` as a knowledge source called "Email review table".
   4. Add the Vault project as a knowledge source.
   5. Optional: a knowledge source called "Our templates" with your standard forms.
   6. Turn off web search.
4. **Run.** Send the messages in `PROMPTS.md`, in order. Each builds or updates one file in the agent's workspace.
5. **Download** the files: `work-types.md`, `skills.md` (or `skills-1.md`, `skills-2.md`), `knowledge-needs.md`, `coverage-and-questions.md`, and `code-key.md`.

## Before you hand it to Claude Code

- Keep `code-key.md` yourself. It is the only file that names outside parties; never put it in the workspace or share it.
- Check the other files: outside parties appear only as codes (C1, S1, P1), people only by role, no personal data.
- Put the other files into the workspace under `seeds/harvey/<YYYY-MM-DD>/`.

## Then, in Claude Code

1. **"learn"**: imports the leads. Each work type is matched to the learning register, each knowledge need becomes a question ("where is it kept, who owns it?"), facts seen become facts to confirm, and Harvey's questions join the open questions. The skill drafts wait for the interview.
2. **"interview me about <work type>"**: Claude asks its open questions first, so Harvey's draft does not steer your answers. Then it shows, line by line, where your answers, its own evidence and Harvey's draft agree or differ, and you settle each one.
3. **"draft a skill for <work type>"**: Claude writes the skill. A line from Harvey goes in only if you confirmed it or Claude's own evidence supports it. Claude adds what its own evidence shows and Harvey missed.

Do one work type at a time, the most common first.
