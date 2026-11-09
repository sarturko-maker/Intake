# What changes in the lab

The lab is this workspace: Claude Code on the lawyer's laptop. It keeps doing what it does well (learning how legal works and turning it into approved skills and knowledge) and stops doing what the build takes over. It never sends anything, in any phase.

Items marked **code** need a small tool change in this repository. The others are documents or habits.

## Now

- RULES.md and README.md point to this folder. Nothing in the lab's sending or filing changes.
- **Guided learning** (`/guided-learning TOPIC`): the lawyer brings a topic or a document, for example levels of authority, and Claude Code questions them in layers: purpose, shape, practice, then where it meets the knowledge base, the skills and what intake has seen. It produces facts to confirm, skill changes to draft, open points and intake-question candidates for the question bank.

## Before Phase 1

1. **Knowledge types.** Add three types to knowledge/TYPES.md: `intake_question` (a question bank entry, [question-bank.md](question-bank.md)), `risk_category` ([p3-low-risk.md](p3-low-risk.md)) and `routing_rule`. Needs the lawyer's yes: the lab never adds a type on its own.
2. **Interview.** Add the question bank questions to the interview skill: "What do you always need to know before you start? What do you assume when it is missing? When must you ask?" The answers feed both the legal skill's "Questions we ask first" section and question bank entries.
3. **Learning evidence (code).** A new kind of evidence line for learn-add: a question legal had to ask the requester before it could start, why, and the answer. These lines become question bank candidates.
4. **Export log and list (code).** A dated export log in the lab, and a command that lists what is approved or changed since the last export ([export.md](export.md)).

## During Phase 1

5. **One owner for references (code).** A matter that came through the button keeps the register's reference in the lab: new-matter takes a given reference instead of counting its own. The lab's own counter stops once the register runs.
6. **The feed (code).** Replaces the daily manual drops. The lawyer's OneDrive syncs a "lab feed" folder from the matter library. A small lab tool copies each new email into `inbox/` once, recognising it by its hash. It never moves or deletes anything in the synced folder, so SharePoint is never changed from the laptop.
7. **Cost.** Copilot Credits show in the Power Platform admin centre, not in Claude Code's logs. If you want one cost line, type the monthly figure into the lab with "budget actual"; otherwise keep the build's costs separate. No code.

## From Phase 2

8. **Retire** in the lab, for matters that live in the build: filing, START-HERE pages, the index and the digest. Keep the reading tools, learning, interviews, skill drafting and the export.
9. **Keep the reading tools free of dependencies** (standard library Python only, as now), so the Phase 2 worker can run them unchanged ([p2-proper-agent.md](p2-proper-agent.md)).
