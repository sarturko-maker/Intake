# Harvey learning agent: how to run it

The agent reads the legal team's emails batch by batch, mostly from the intake mailbox and some from your own. It keeps two working files up to date:

- **`legal-matters.md`**: one paragraph per matter, with a short header (work type, who asked, who handled it, effort, outcome). There is no duplication: when new or older emails arrive for a matter, it rewrites that matter's paragraph.
- **`legal-learning-register.md`**: everything learned across matters:
  - the work-types report;
  - ways of working;
  - positions and precedents;
  - the front door;
  - knowledge;
  - our companies, the glossary, roles and the code key;
  - open questions and documents to fetch;
  - a change log.

When you ask, it builds the work-types report, draft skills and the knowledge pack from those two files. Everything it writes is a draft. You and Claude Code check it later.

## Set up (about 15 minutes)

1. In Harvey's Agent Builder, create a new agent. Call it "Legal team learning agent".
2. Paste `AGENT-INSTRUCTIONS.md` into its instructions.
   - Our own companies always appear by their full legal names.
   - Outside parties get codes (C1, S1) unless you change REPLACE to KEEP.
   - People always appear by role, never by name.
3. Add `OUTPUT-FORMAT.md` as a knowledge source called "Output format".
4. Optional, and useful: add a knowledge source called "Our templates" with your standard NDA, MSA, guarantee (PCG) and LPA forms.
5. Add no other knowledge sources and turn off web search.

## Each batch

You are going backwards: the most recent emails first, then older ones.

1. Attach the batch as `.eml` or `.msg` files (print to PDF if needed), with their attachments. Mixing intake emails and your own is fine.
2. Send the message from `PROMPTS.md`. For the first batch, use the START FILES message.
3. Check the reply:
   - it ends with `END OF BATCH Bxx`;
   - its file check says both files were saved and no count went down.
   - If it stops at "CONTINUED", say "continue".
4. Section H lists documents to fetch, usually our replies and mark-ups from the lawyers' sent items. That is where the judgement is. When you find them, give them to the agent with the "documents" message.
5. Every few days, download both files and keep dated copies (`legal-matters-2026-11-07.md`). This is your backup, and what you attach if a new conversation cannot see the files.

## After about a month

Send the BUILD SKILLS message. Save each `=== FILE: ... ===` part as its own file, keeping the folders.

In the workspace, save to:
- `seeds/harvey/files/` for the two working files;
- `seeds/harvey/build/` for the reports, skills and knowledge.

Claude Code then:
- checks them;
- asks you the open questions;
- turns them into approved skills and knowledge, after your yes.

## Size

- **Skill sets:** each stays under about 20,000 tokens. A SKILL.md is under about 4,000 words, with detail in `positions.md` and `precedents.md`. Each works on its own as a command in Claude Code (for example `/nda-review`), or pasted into a Harvey agent.
- **Matters file:** about 300 paragraphs a month is fine. It is a working file, not a skill.

## Tips

- If the agent seems to lose entries when it rewrites a file, ask for the optional check. Keep your dated copies.
- Leave obvious HR or personal emails out if you can. The agent skips them anyway.
- Before sharing anything outside Harvey, delete the name column of the code key and check the agent's re-identification flags. Our own company names stay.
