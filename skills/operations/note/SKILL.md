---
name: note
description: "Write what the lawyer tells you in chat into a matter's notes: calls, meetings, Teams chats, decisions, context. Use for 'note 2026-0042: ...', 'add to the notes of 2026-0042', '/note REF ...', and whenever the lawyer answers a question you asked about a matter."
argument-hint: "<REF> <what to note>"
---

# Note

The lawyer talks; you write. Each matter's agent/notes.md holds only what the lawyer said, in their words, dated. It is read on every run and goes into the Harvey pack. Rules: RULES.md 'Notes and questions'.

R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

1. **Which matter.** The reference given, or the matter your question was about. If it is unclear, ask once, naming the two likeliest matters. Never guess.
2. **Write.** Add one line per point at the end of <matter>/agent/notes.md with your edit tool, never by shell:
   `- YYYY-MM-DD: (you said) <the lawyer's words, tidied for spelling only>`
   An answer to your question keeps the question, short: `- 2026-11-02: (you said, asked "Did Acme accept the cap?") Yes, 150% for strategic customers.`
   - Only what the lawyer said: nothing from emails, nothing you inferred, no summary of your own.
   - Numbers, amounts, dates and names exactly as said. Unsure of one: read it back in one line before writing.
   - Never change or remove an earlier line; the hook refuses it. To correct a note, add a line that says what changed.
3. **Log.** One log.md line: `YYYY-MM-DD HH:MM | note added (you said) | notes.md | R`.
4. **Does it change anything?** If the note settles a point, changes who we wait for, the next step or a date, or gives a position: run the reader on the matter (why: notes changed), so matter.md, brief.md and facts.md follow (facts cite `source=notes.md YYYY-MM-DD`). Otherwise stop here: the next reader run reads it.
5. **Learning.** A note that shows how we work (a position, a fallback, who approves, why): `printf '%s\n' "<kind> | <text> | notes.md <date>" | bash tools/learn-add --matter <REF> --work-type <slug> --origin lawyer --run <R>`. A company fact: `printf '%s\n' "<type> | <fact> | notes.md <date>" | bash tools/learn-add --matter <REF> --knowledge --run <R>`. Nothing is asked back: the lawyer said it, so it is recorded. A statement about how the team works in general, not about this matter: the learn skill, 'What the lawyer tells you'.
6. **Refresh (scripts, no model cost):** `bash tools/work-bundle <REF> --quiet`, then `bash tools/matter-sync <REF> --pages-only --run <R>`. After a reader run, also `bash tools/index-rebuild --run <R>`.
7. **Reply in one or two lines:** what you noted and, if it changed, the next step. No questions back unless step 1 needs one.

Several answers in one message ("1 yes, 2 skip, 3 Finance owns it"): one line each in the right matters; "skip" writes nothing. Then steps 3 to 7 once per matter.

No subagents, except the reader in step 4.
