# Harvey learning agent: how to run it

The agent reads the legal intake emails day by day. It keeps a running register (a Harvey artifact) of how the team works, and builds draft skills and knowledge when you ask. Everything it writes is a draft. You and Claude Code check it later.

## Set up (about 15 minutes)

1. In Harvey's Agent Builder, create a new agent. Call it "Intake learning agent".
2. Paste `AGENT-INSTRUCTIONS.md` into its instructions.
   - Choose the company-name rule first. **REPLACE** gives codes such as C1 and S1, with a code key. **KEEP** writes real names.
3. Add `OUTPUT-FORMAT.md` as a knowledge source called "Output format". It holds the batch format, the register template and the skill format.
4. Optional, and useful: add a knowledge source called "Our templates" with your standard NDA, MSA, guarantee (PCG) and LPA forms. The agent can then see what changed against your standard.
5. Add no other knowledge sources and turn off web search.

## Each day

1. Attach the day's emails as `.eml` or `.msg` files (print to PDF if needed), with their attachments.
2. Send the daily message from `PROMPTS.md`. On the first day, use the START REGISTER message.
3. Check the reply ends with `END OF BATCH Bxx`. If it stops at "CONTINUED", say "continue".
4. Save the chat reply as `Bxx.md`. These are the detailed records.
5. Look at section H, "Documents to fetch". The judgement is mostly in what is missing: our replies and mark-ups.
   - Where you can, find them, often in the lawyers' sent items.
   - Give them to the agent with the "documents" message.
6. Once a week, download or copy the register and save it with a date (`register-2026-11-07.md`). This is your backup. It is also what you attach if a new conversation cannot see the register.

## After about a month

Send the BUILD SKILLS message from `PROMPTS.md`. Save each `=== FILE: ... ===` part as its own file, keeping the folders.

In the workspace, save to:
- `seeds/harvey/batches/` for the daily `Bxx.md` files;
- `seeds/harvey/register/` for the register copies;
- `seeds/harvey/build/` for the built skills and knowledge.

Claude Code then:
- checks them;
- merges threads across days;
- asks you the open questions;
- turns them into approved skills and knowledge, after your yes.

## Size of the skills

Each skill set stays under about 20,000 tokens: a SKILL.md under about 4,000 words, with detail in `positions.md` and `precedents.md`. Each one works on its own as a command in Claude Code (for example `/nda-review`), or pasted into a Harvey agent: SKILL.md as the instructions, the companions as knowledge. The register itself can grow larger; it is not loaded as a skill.

## Tips

- Prefer days with the lawyers' own replies and mark-ups in them.
- Leave obvious HR or personal emails out if you can. The agent skips them anyway.
- Before sharing anything outside Harvey, delete the name column of the code key and check the agent's re-identification flags.
