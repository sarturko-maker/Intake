---
name: interview
description: "Interview the lawyer about how the team works on one type of work, from dictated answers, and record them with caution as dated statements for the skills. Use for 'interview me about NDAs', '/interview nda-review', 'let's do the interview', and after cold start when there are no approved skills."
argument-hint: "<work type or skill name>"
model: opus
---

# Interview about ways of working

The lawyer dictates. Recollection is valuable and fallible: people describe how they mean to work, remember the striking case, and generalise. Dictation adds errors in names and numbers. So an interview is **evidence of what the lawyer says, on one day**. It is not a record of what happened, and nothing from it becomes a skill without the read-back and approval.

Rules: RULES.md 'Skills', 'Knowledge'. Ask in plain chat, one question at a time. Never assume an answer.

R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

## Before

1. Topic: the work type or skill name from the request. If there is none, show the work types from the work-types report (seeds/harvey/ or areas/*/intake.md) with their counts, and ask which to start with. Suggest the most frequent one.
2. Read quietly, and do not show yet (learning/work-types/<slug>.md first: the evidence matter by matter):
   - the evidence for this topic: knowledge/INDEX.md and the relevant files, closed matters of this kind, seeds/ (Harvey output: leads only), any existing skill, earlier interviews in seeds/interviews/, and our substantive sent emails in matters of this kind (documents.md origin ours, "[substantive]");
   - from these, note the points to test later: what the evidence shows we do, the positions seen with their context, and the gaps.
3. Say how it works, in two lines: about eight questions, about 15 minutes; numbers and names are read back; nothing changes a skill until the lawyer approves the read-back.

## Ask: open questions first, evidence after

Ask the open question before showing any evidence, so the answer is not shaped by what the agent found. At most eight questions in a session, chosen from:

1. When does this kind of request come in, from whom, and what do they really want?
2. Walk me through what you do, step by step, from the email arriving to it being done.
3. What do you check first, and what do you ask the requester before acting?
4. What is our standard position on the main points? What will we move to, and when?
5. What do we never accept? Who can override that?
6. What changes the answer? For example the customer's size, leverage, deal value, a regulated customer, time pressure, or precedent.
7. Who signs off, and when does it go above you?
8. How do you phrase the reply? Give a typical line.
9. Tell me about one that went badly, and one that went well.

Follow-ups, at most one per answer:
- **"Always", "never", "usually":** ask "Any exceptions? When did that last happen?"
- **A position:** ask for an example matter or a period, so it can be checked.
- **A number, percentage, amount, period, entity name or defined term:** read it back exactly ("I have: cap at 100 percent of annual fees. Right?").

## Then compare with the evidence

After the open answers, show the differences with the evidence, one line each, and ask the lawyer to settle each one. Example: "You said we hold the cap at 100 percent. In 2 of 5 matters we went to 150 percent for strategic customers (M012, M031). Should the skill say 100 percent with an exception for strategic customers, or something else?"

Record the lawyer's choice, and keep the difference visible:
- **For how we should work** (positions, red lines, approvals): the lawyer's confirmed answer is what the skill will say. The past exceptions are kept as precedents with their context.
- **For what actually happens** (steps, timings, who does what, volumes): evidence beats recollection. If they differ, record both, and ask once which to write. Never overwrite evidence with memory silently.

## Write

1. **The transcript.** seeds/interviews/<YYYY-MM-DD>_<topic>.md: the questions and the dictated answers as given, with dictation slips marked [sic] only where read back and corrected. Header: topic, date, who (role), session length. Written once, never edited afterwards.
2. **The notes.** seeds/interviews/<YYYY-MM-DD>_<topic>.notes.md: one statement per line:

   `S01 | kind (position, red line, approval, step, timing, phrasing, fact, example) | statement | confirmed in read-back: yes or no | matches evidence: yes, no (with refs) or not checked | lawyer's choice where they differ`

3. **The read-back.** In chat, a plain-English summary of at most 15 lines: the positions, red lines, approvals and steps as the skill would say them, plus the differences and the choices made. Ask: "Is this right? Correct anything." Mark the confirmed lines yes in the notes.
4. **Company facts** that came up (entities, approval limits, who signs): offer the knowledge confirm flow, one sentence each. Write only after a yes.

## After

- Interview notes are a source for the draft-skill skill: (interview <date>, S03). A skill line resting only on an unconfirmed statement is not used.
- Interview statements are dated. When later matters contradict one, the reader or the wrap-up raises it as a question. It is not silently replaced.
- If more than one lawyer is interviewed on the same topic, keep their statements apart and show any disagreement. Never average them.
- Tell the lawyer what is next: "draft a skill for <topic>" builds the draft from the interview, the evidence and the seeds; or "interview me about <next topic>".
- `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "interview <topic>"`, where m is the BUDGET.md price key of the model.

No subagents are needed: the orchestrator runs the interview itself.
