---
name: learn
description: "Review what the system has learned, with the lawyer: confirm facts about the company, answer open questions, take in Harvey or other seed output, and choose the next interview or skill to draft. Use for 'learn', '/learn', 'what have you learned', 'monthly review', and whenever facts or questions are waiting."
model: opus
---

# Learn

This phase is mainly for learning. Ways of working become skills; facts about the company become knowledge. The learning register in learning/ is kept by scripts: you add lines with `bash tools/learn-add` and rebuild the page with `bash tools/learn-index`. Rules: RULES.md 'Wrap-up and learning', 'Knowledge', 'Skills'. Ask in plain chat: numbered, short, a few items at a time. Never assume an answer.

R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

1. Run `bash tools/learn-index`, then read learning/index.md.
2. **Seeds.** Some files in seeds/ may not be listed in learning/seeds-imported.md yet: Harvey batch reports, registers, built skills, extractions. For each such file:
   - read it;
   - add what it teaches with learn-add, every line marked as a lead:
     - evidence: `--matter seed --origin seed --work-type <slug>`, reusing a slug from learning/work-types/;
     - facts: `--matter seed --knowledge`, with source "seed <file>";
     - questions: `--matter seed --question`;
   - record the file name, its sha256 (from `bash tools/hash-files`) and today's date in learning/seeds-imported.md.

   Seeds are never "observed". A seed that contradicts observed evidence or knowledge becomes a question.
3. **Facts waiting.** Take the pending lines in learning/knowledge-candidates.md, at most five at a time, in one numbered message: "<fact> (source). Keep it? Who owns it?" The lawyer answers in their own words, for example "yes 1, 2, 4; no 3; 5 is owned by Finance".
   - Each yes: run the knowledge confirm flow (RULES.md 'Knowledge'). Write or update the entry in the type's folder (knowledge/TYPES.md), stamped with confirmed_by and last_confirmed, then set the candidate's status to `confirmed (knowledge/<file>)` with Edit.
   - Each no: `rejected`.
   - Each unclear one: leave it pending.
   - A changed fact supersedes the old entry: set valid_until on the old one. Never edit an entry silently.
4. **Open questions.** Ask up to three, one line each; offer more only if the lawyer wants them. For each answer:
   - `printf '%s\n' "answer | <the answer> | lawyer in chat <today>" | bash tools/learn-add --matter chat --work-type <slug> --origin lawyer`;
   - set the question's status to `answered (<today>)` with Edit.

   An answer that is a company fact also goes to step 3.
5. **Next.** Show the numbered next learning steps from learn-index (interviews due, skills ready to draft, drafts waiting for approval) and offer the first. For example: "Interview about NDA review now? About 15 minutes."
6. Run `bash tools/learn-index --quiet`.
7. Run `bash tools/budget-update --measure --run <R> --note "learn"` (the real token use from Claude Code's logs since the last measurement). It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "learn"`, once per model used.

What phase 2 adds later: a monthly review that proposes changes to approved skills from closed matters, with a leak check. Until then, an approved skill changes only through "redraft <name>".

No subagents are needed. A long seed may go to the indexer or researcher to summarise first.
