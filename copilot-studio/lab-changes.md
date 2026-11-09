# What changes in the lab

The lab is this workspace: Claude Code on the lawyer's laptop. It keeps doing what it does well (learning how legal works and turning it into skills and knowledge) and stops doing what the build takes over. It never sends anything, in any phase.

Items marked **code** need a small tool change in this repository. The others are documents or habits.

## Done: the lab learns by watching

The lab no longer asks the lawyer to confirm facts, answer questions or sit interviews before anything is written. It works the way Phase 1.5 will: watch what legal does, expect, compare, correct.

- **Working first, approved later.** For each type of work the lab writes a working skill from the matters it has read, and working knowledge entries from the company facts it meets. Every line says what it rests on. The lawyer reads them when they like and says what to change; what the lawyer says or edits always wins. Approval is the lawyer's yes to a version, and is needed only for fixed points and for [export](export.md).
- **Expect, then compare.** Before legal answers a request, the lab notes what it expects legal to ask and do. When legal's email arrives, it records how that compared: match, partly, missed. The share expected right, per type of work, is the lab's own rehearsal of the Phase 1.5 question match ([measures.md](measures.md)), on the lawyer's own mail, before the build exists.
- **The questions legal asks first** are recorded from legal's own emails (`we-asked` lines, with the answer when it comes). Each skill's "Questions we ask first" section is built from them: the question, why, where the answer may already be, what legal went ahead on when it was missing. That section is the raw [question bank](question-bank.md).
- **Guided learning and interviews** stay, only when the lawyer asks for them. What the lawyer says is recorded as the lawyer's own words and goes straight into the skills and entries.
- **Ours, not theirs.** The lab learns positions only from what legal said or did, never from what the other side says was agreed. The build's agents need the same rule ([CONTRACT.md](CONTRACT.md), rule 5).

## Before Phase 1

1. **Knowledge types.** The question bank, risk categories and the routing table each need a home in the legal library ([data-model.md](data-model.md)). In the lab, question bank entries come out of the skills' "Questions we ask first" sections; add a type for them in knowledge/TYPES.local.md when the first export is prepared.
2. **Approval sitting.** Before the first export, the lawyer says "approve the knowledge entries" and "approve <skill>" for what is to go: one sitting, answered in the lawyer's own words ("all except 3 and 7"). Plain company facts can be the paralegal's to approve once they are in the tenant ([CONTRACT.md](CONTRACT.md), Who approves what).
3. **Export log and list (code).** A dated export log in the lab, and a command that lists what is approved or changed since the last export ([export.md](export.md)). Until then: "what is ready to export".

## During Phase 1

4. **One owner for references (code).** A matter that came through the button keeps the register's reference in the lab: new-matter takes a given reference instead of counting its own. The lab's own counter stops once the register runs.
5. **The feed (code).** Replaces the daily manual drops. The lawyer's OneDrive syncs a "lab feed" folder from the matter library. A small lab tool copies each new email into `inbox/` once, recognising it by its hash. It never moves or deletes anything in the synced folder, so SharePoint is never changed from the laptop.
6. **The question log feeds the lab.** The Phase 1 question log (every question legal asks, with the paralegal's grouping) is dropped into `seeds/` monthly. The lab takes it in as evidence for each type of work; it shows where the lab's own "Questions we ask first" missed.
7. **Cost.** Copilot Credits show in the Power Platform admin centre, not in Claude Code's logs. If you want one cost line, type the monthly figure into the lab with "budget actual"; otherwise keep the build's costs separate. No code.

## From Phase 2

8. **Retire** in the lab, for matters that live in the build: filing, START-HERE pages, the index and the digest. Keep the reading tools, the learning pass, skill writing and the export.
9. **Keep the reading tools free of dependencies** (standard library Python only, as now), so the Phase 2 worker can run them unchanged ([p2-proper-agent.md](p2-proper-agent.md)).
10. **The worker learns the same way.** The Phase 2 worker's "find out, assume, then ask" is the lab's own rule for the lawyer: assume the likeliest reading, say so, ask only when stuck. Its assumptions corrected by Sales are the build's version of the lab's `compared` lines.
