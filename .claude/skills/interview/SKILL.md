---
name: interview
description: "Talk through how the team works on one type of work, only when the lawyer asks for it. Starts from the working skill, so the lawyer reacts instead of reciting; records the answers as the lawyer's dated statements; rewrites the skill at once. Use for 'interview me about NDAs', '/interview nda-review', 'let's do the interview', 'interview me cold about <type>'."
argument-hint: "<work type or skill name>"
model: opus
---

# Interview about ways of working

Only when the lawyer asks. Skills write themselves from the matters (learn skill); an interview is the lawyer choosing to talk rather than read. Never suggest one as a step the lawyer owes.

The lawyer dictates. Recollection is valuable and fallible: people describe how they mean to work, remember the striking case, and generalise. Dictation adds errors in names and numbers. So an interview is **evidence of what the lawyer says, on one day**. For how we should work (positions, red lines, approvals), the lawyer's answer decides. For what actually happened (steps, timings, who did what), the matters do. Where the two differ, both stay visible.

Rules: RULES.md 'Skills', 'Knowledge'. Ask in plain chat, one question at a time.
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`. Today = house date.

## Before

1. Topic: the type of work from the request (its slug in learning/work-types/). None given: `bash tools/learn-index --quiet`, then the types of work on learning/index.md with their matter counts; suggest the one with the most matters.
2. Read quietly: the working skill, skills/<area>/<slug>/SKILL.md, above all its 'Not sure yet' and 'Fixed points'; the `compared` lines that start partly or missed in learning/work-types/<slug>.md; earlier interviews in seeds/interviews/. No skill yet: the evidence file itself. A Harvey draft for this type of work (seeds/harvey/*/skills.md): a lead to test, never shown before the lawyer has spoken.
3. Say how it works, in two lines: "I show you in ten lines how I think you handle this; you tell me what is wrong or missing. Then at most five questions on what I am least sure of. About ten minutes. Say 'cold' if you would rather answer open questions first, before seeing what I found."

## React, then a few questions

1. Show the skill in at most ten plain lines: when this work comes in, what we ask first, how we think about it, what is fixed (or "nothing stated as fixed yet"), how we say it. Then one question: "What is wrong, and what is missing?" Take everything the lawyer says, in their words.
2. At most five questions, one at a time, the ones whose answers would change the skill most: from 'Not sure yet', from where the agent expected the wrong thing, from sections that say "Not seen yet". For example: "In 2026-0042 we went to 150 percent; the other four matters held 100 percent. What made that one different?"
3. Follow-ups, at most one per answer:
   - **"Always", "never", "usually":** "Any exceptions? When did that last happen?"
   - **A position or a decision:** why: what you weighed, and what would have changed it. The reason is what the skill keeps.
   - **A number, percentage, amount, period, entity name or defined term:** read it back exactly ("I have: cap at 100 percent of annual fees. Right?").
4. "Skip" and "enough" are always fine. Stop when the lawyer stops.

## Cold ("interview me cold about <type>", or no skill and no evidence yet)

Ask the open question before showing any evidence, so the answer is not shaped by what the agent found. At most eight, chosen from:

1. When does this kind of request come in, from whom, and what do they really want?
2. Walk me through what you do, from the email arriving to it being done.
3. What do you always need to know before you start? What do you assume when it is missing, and when is that not safe?
4. What is our standard position on the main points? What will we move to, and when?
5. What do we never accept? Who can override that?
6. What changes the answer? For example the customer's size, leverage, deal value, a regulated customer, time pressure, or precedent.
7. Who signs off, and when does it go above you?
8. How do you phrase the reply? Give a typical line.
9. Tell me about one that went badly, and one that went well.

Then show where the answers differ from the matters, one line each, most important first, and take the lawyer's word on each: "You said we hold the cap at 100 percent. In 2 of 5 matters we went to 150 percent for strategic customers. Should the skill say 100 percent with that exception, or something else?" A difference the lawyer does not settle stays visible in the skill under 'Not sure yet'.

## Write

1. **The transcript.** seeds/interviews/<YYYY-MM-DD>_<topic>.md: the questions and the dictated answers as given. Header: topic, date, who (role), session length. Written once, never edited afterwards.
2. **The notes.** seeds/interviews/<YYYY-MM-DD>_<topic>.notes.md, one statement per line: `S01 | kind (consideration, position, red line, approval, step, timing, phrasing, question we ask, fact, example, correction) | statement with its reason | matches the matters: yes, no (with refs) or not checked`.
3. **Into the register, at once, as the lawyer's.** Every statement: `printf '%s\n' "<kind> | <statement, with its reason> | interview <today> S<nn>" | bash tools/learn-add --matter interview --origin interview --work-type <slug> --run <R>`. Kinds: position, fallback, red-line, approval, context, phrasing, did (a step), timing, we-asked (a question we put first, with what we assume when it is missing), `correction` (the lawyer said something in the skill is wrong). A firm "never", "always" or limit is a red-line or approval line: it becomes a fixed point because the lawyer said it. Company facts (entities, approval limits, who signs): `printf '%s\n' "<type> | <fact> | interview <today>" | bash tools/learn-add --matter interview --knowledge --run <R>`.
4. **The read-back, once.** At most twelve lines: "This is what I took from it", with every number and name, and anything that reads like a rule. The lawyer corrects, or says nothing. A correction is one more `correction` line. Do not wait for a yes, and do not ask for one.
5. **The skill, now.** `bash tools/learn-index`, then one learner with this type of work's `skill` line (learn skill, 'The pass', steps 4 and 5), `knowledge: yes` when facts came up. If more than one lawyer has been interviewed on the topic, the learner keeps their statements apart and shows any disagreement; it never averages them.

## After

- Tell the lawyer in three lines: the skill's link, what changed, and what is still under 'Not sure yet'.
- Interview statements are dated. When later matters go another way, the learner keeps the lawyer's line and shows the matter as an example under 'Not sure yet'; it never replaces the lawyer's word silently.
- `bash tools/budget-update --measure --run <R> --note "interview <topic>"` (the real token use from Claude Code's logs since the last measurement). It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note "interview <topic>"`, once per model used.

The orchestrator runs the interview itself; the learner writes the skill.
