# Output format

Use these headings and field lines exactly, one item per block, as `- field: value` lines. Leave a field empty rather than guess.

IDs:
- thread: Bxx-Txx
- negotiation record: Bxx-Txx-Nn
- knowledge: Bxx-Kn
- ways of working: Bxx-Wn
- front door: Bxx-Fn
- question: Bxx-Qn
- document to fetch: Bxx-Dn
- request type: RTnn

The ID keeps the batch where the item first appeared.

---

## Part 1. Daily batch deliverables (in chat)

### A. Batch log

- batch: B07, date 2026-11-03
- emails received:
- threads: new (IDs); continued from earlier batches (IDs)
- skipped as noise: number and kinds
- skipped as sensitive: number and categories only
- attachments read: number; not readable: name and reason
- legal response visible: in how many threads out of how many
- re-identification risks: combinations that could still identify a party
- notes:

### B. Thread cards: one per new thread, and one per continued thread (marked "continued")

#### B07-T03 | short title, like a lawyer's file title, no personal names

- dates: first and last email (batch date and day numbers)
- request type: RT id and name, from the catalogue
- area: commercial, privacy, corporate, disputes, trade compliance, employment, credit, procurement, other
- requester: role and team
- our company: full legal name of our company involved
- counterparty: code and description (type, sector, size, relationship)
- value and urgency: deal or order value band (low, medium, high, with the figure if given), and any deadline
- what they asked:
- what legal did: the steps, in order, and who did each (role)
- legal response visible: yes, partly or no
- type of legal output: advice, mark-up, approval, delegation, question back, refusal, or none visible
- nature of the work: judgement (needs a lawyer), record lookup, process or admin, or routing to another team
- effort: quick (minutes), medium (an hour or so), or heavy (more), as it appears
- documents: what was attached and what each was; our templates used
- outcome: what was agreed or sent, or "open"
- turnaround: first legal reply after how long; finished after how long; chasers
- who decided: role; escalations (to whom, and why)
- reply style: tone, length, structure; one short quote of our wording if useful
- knowledge used or revealed: K ids
- negotiation records: N ids
- notes:

### C. Negotiation records: one per negotiated point

#### B07-T03-N1 | clause topic (for example, limitation of liability)

- document: for example, customer's master agreement, on their paper; or our PCG form
- their position: what their draft or email said (paraphrase)
- our position: our mark-up or reply (paraphrase), or "not visible" (then add an H item)
- our standard: what our template says, if "Our templates" is attached
- gap:
- their reaction:
- outcome: accepted ours, agreed fallback, we conceded, they conceded, open, or walked away
- final position: paraphrase of what was agreed
- why (context): leverage, size, strategic value, regulated customer, deal value, time pressure, relationship, precedent, insurance; or "context not visible"
- who approved:
- observed or stated:
- confidence:

### D. Knowledge candidates: facts only

#### B07-K2 | fact title

- type: entity, policy, person_role, standard_answer, template, product, certification, contract_record, glossary, or a new type you propose (say so)
- fact: one or two sentences
- as of: date
- stated by: role, or the document
- evidence: thread IDs and document names
- observed or stated:
- confidence:
- register status: new, adds evidence to (register ID), or contradicts (register ID)

For a standard questionnaire answer, add:
- question pattern: how the question is usually asked
- our answer: the answer we gave (paraphrase, or a short quote where the wording matters)
- owner: the team that supplied or confirmed it
- caveats:

### E. Ways-of-working notes: grouped by request type

#### RT03 NDA review

##### B07-W4 | short title

- what we do: the step, check, position or habit
- when it applies, and when it does not:
- standard position:
- fallback: what we accept if pushed, and in which circumstances
- red line: what we do not accept, and who can override it
- questions we ask first:
- who does it and who approves:
- how we phrase it: a pattern, or a short quote
- evidence: thread IDs and N ids; frequency today and in total
- observed or stated:
- confidence:

### F. Front-door notes: how the inbox works overall

#### B07-F1 | short title

- topic: routing, triage, turnaround, escalation, who handles what, recurring requesters, style, hand-offs to other teams, or work that may not need a lawyer
- note:
- evidence: thread IDs; frequency
- confidence:

### G. Questions for the legal team

#### B07-Q1

- question:
- why it matters: which skill or fact it affects
- evidence: thread IDs

### H. Documents to fetch: what I should find and give you

#### B07-D1

- thread: thread ID and subject
- what is missing: for example, legal's reply sent from a personal mailbox, our mark-up of the NDA, the customer's second-round response
- where it probably is: for example, the sent items of the commercial counsel, around day 9
- why it matters: which negotiation record or skill it would complete

### I. Register changes

- added: new entries, by ID
- updated: entries with new evidence, by ID
- superseded: old entry, and the entry that replaces it
- questions answered: question ID and the thread that answers it
- codes added to the key:
- request types added to the catalogue:

`END OF BATCH B07`

---

## Part 2. The learning register (the artifact): template

Title: **Intake learning register**. Keep these sections in this order. Use compact lines; the register may grow large.

### 0. Status

- batches covered: B01 to B07 (first and last date)
- emails: n; threads: n; open threads: n
- legal response visible: n of n threads
- last updated: batch and date

### 1. Code key

**Our own companies**, by real name, with no codes:

`full legal name (with legal form) | jurisdiction | what it does | other names seen | first seen`

**Outside parties:** customers (C...), suppliers (S...) and others.

`code | name (for my use only; delete before sharing) | type | description (sector, size, region, relationship) | first seen`

### 2. Request-type catalogue

`RT id | name | what it is | threads (count and IDs) | typical requester | status (emerging under 3 threads, ready at 3 or more) | proposed skill name`

### 3. Thread register

`thread ID | short title | RT id | counterparty code | status (open, done, unknown) | last seen batch | legal response visible | documents to fetch (D ids)`

### 4. Ways of working, by request type

For each RT, merged from all batches:
- steps, in order, and who does each;
- questions we ask first;
- who decides and who approves;
- how we phrase things, with short quotes;
- evidence for each point.

### 5. Positions and precedents, by clause topic

For each clause topic (for example, liability cap, indemnity, governing law, guarantee scope, contracting entity, payment terms):
- our standard;
- fallbacks seen, and when;
- red lines;
- who approved the moves;
- the precedents: one line each with counterparty code, their ask, our position, the outcome, why, and the N id.

### 6. Front door

- request volumes by type;
- routing and who handles what;
- recurring requesters;
- turnaround: typical first reply, typical finish, chasers;
- escalation;
- reply style;
- work that may not need a lawyer;
- what usually follows what.

### 7. Knowledge register

`K id | type | fact | as of | evidence | confidence | status (current, superseded by, contradicted by)`

### 8. Glossary

`term | meaning | evidence`. Use "meaning not known, ask" when unclear (for example OTP, PA, LPA, PCG, credit prefix).

### 9. Roles

Who does what, by role only: the legal team, US or group legal, credit, procurement, sales and others.

### 10. Open questions

`Q id | question | affects | status (open, or answered by thread ID with the answer)`

### 11. Documents to fetch

`D id | thread | what | where | status (open, fetched in Bxx)`

### 12. Change log

One line per batch: the date, what was added, what was updated, what was superseded.

---

## Part 3. Skill deliverables (only after BUILD SKILLS)

Start each file with a line `=== FILE: <folder>/<name>.md ===`, so each file can be cut out and saved on its own.

Size limits:
- each SKILL.md: under about 4,000 words;
- each skill set (SKILL.md plus companions): under about 15,000 words, which is roughly 20,000 tokens.

If a skill set would be larger, split the skill.

### 1. Front-door skill: `front-door/SKILL.md`

```
---
name: front-door
description: How the legal team handles its intake inbox: request types, routing, triage, turnaround, escalation and style. Use for any new request to legal.
area: all
version: 0
status: draft (unverified)
last_reviewed:
supporting_matters: thread IDs
---
```

Sections:
- Request types we see, with counts and the skill that covers each
- Who asks, and what they usually want
- What we ask first
- Who handles what, and routing to other teams
- What goes to a lawyer, and what is a lookup or process
- Turnaround norms
- Escalation
- Style of our replies
- What usually follows what
- Open questions

### 2. Request-type skills: `<skill-name>/SKILL.md`, plus companions where needed

```
---
name: nda-review
description: When to use this skill, in one or two sentences.
area: commercial
version: 0
status: draft (unverified)
last_reviewed:
supporting_matters: thread IDs
---
```

SKILL.md sections:
- When to use, and when not
- Questions we ask first
- How we handle it: the steps, who does each, who approves
- What is settled: our standard positions, in short (the full table goes in positions.md)
- What we weigh: the context factors that change outcomes, with short examples
- Where the line is, and when to stop and ask
- How we say it: phrasing patterns and short quotes
- Output shape: what the deliverable looks like
- Companion files: what positions.md and precedents.md hold, and when to read them
- Open questions for this skill

`<skill-name>/positions.md` (contract skills only), the positions table:

| Clause | Our standard | Fallback, and when | Red line | Who can approve a move | Evidence |
|---|---|---|---|---|---|

`<skill-name>/precedents.md`: short cases from the negotiation records. Each gives:
- the counterparty type and code;
- their ask;
- our position;
- the outcome;
- why, with the context;
- the N id.

### 3. Knowledge pack: `knowledge/<type>-<short-name>.md`, one file per fact or fact set

```
---
type:
name:
aliases:
owner:
source: thread IDs and document names
origin: seed
valid_from: the "as of" date
valid_until:
last_confirmed:
confirmed_by:
---
```

Body:
- a summary;
- the key facts, each with evidence;
- for standard answers: the question pattern, our answer, caveats, where it was used, and the owning team.

Also write `knowledge/glossary.md`, `knowledge/our-companies.md` (our companies by real name) and `knowledge/code-key.md` (outside parties only, without the name column).

Never put negotiation positions in the knowledge pack.

### 4. `open-questions.md`

Merged and ranked, most important first. Each question names the skill or fact it affects and cites its thread IDs.

### 5. `coverage.md`

- request types, with thread counts
- skills drafted, with word counts
- emerging request types
- contradictions found
- documents still to fetch
- what was skipped, and why (counts only)
