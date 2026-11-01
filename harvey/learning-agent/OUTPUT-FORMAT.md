# Output format

Use these headings and field lines exactly, one item per block, as `- field: value` lines. Leave a field empty rather than guess. IDs:
- thread: Bxx-Txx
- negotiation record: Bxx-Txx-Nn
- knowledge: Bxx-Kn
- ways of working: Bxx-Wn
- front door: Bxx-Fn
- question: Bxx-Qn

---

## Batch deliverables (every batch)

### A. Batch log

- batch: B07
- emails received:
- threads:
- skipped as noise: number and kinds (newsletter, auto-reply, invitation, marketing)
- skipped as sensitive: number and categories only
- attachments read: number; not readable: name and reason
- continues earlier threads: thread ID, subject and date of the earlier email
- notes:

### B. Thread cards: one per thread

#### B07-T03 | short title, like a lawyer's file title, no personal names

- dates: first email, last email
- request type: in your words (NDA review, supplier terms question, security questionnaire, signing authority, RFQ terms, and so on)
- area: commercial, privacy, corporate, disputes, trade compliance, employment, other
- requester: role and team
- counterparty: type and size (for example, large automotive customer), plus the name if company names are kept
- what they asked:
- what legal did: the steps, in order
- documents: what was attached and what each was
- outcome: what was agreed or sent, or "open"
- turnaround: first reply after how long; finished after how long
- who decided: role; escalations (to whom, and why)
- reply style: tone, length, structure; one short quote of our wording if useful
- knowledge used or revealed: K ids from section D
- negotiation records: N ids from section C
- shows the way of working for: request type
- notes:

### C. Negotiation records: one per negotiated point

#### B07-T03-N1 | clause topic (for example, limitation of liability)

- document: for example, customer's master agreement, on their paper
- their position: what their draft or email said (paraphrase)
- our position: our mark-up or reply (paraphrase)
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

- type: entity, policy, person_role, standard_answer, template, product, certification, contract_record, or a new type you propose (say so)
- fact: one or two sentences
- as of: date
- stated by: role, or the document
- evidence: thread IDs and document names
- observed or stated:
- confidence:

For a standard questionnaire answer, add:
- question pattern: how the question is usually asked
- our answer: the answer we gave (paraphrase, or a short quote where the wording matters)
- owner: the team that supplied or confirmed it
- caveats:

### E. Ways-of-working notes: grouped by request type

#### Request type: name

##### B07-W4 | short title

- what we do: the step, check, position or habit
- when it applies, and when it does not:
- standard position: for contracts, our usual starting point
- fallback: what we accept if pushed, and in which circumstances
- red line: what we do not accept, and who can override it
- questions we ask first:
- how we phrase it: a pattern, or a short quote
- evidence: thread IDs and N ids; frequency in this batch
- observed or stated:
- confidence:

### F. Front-door notes: how the inbox works overall

#### B07-F1 | short title

- topic: routing, triage, turnaround, escalation, who handles what, recurring requesters, style, or hand-offs to other teams
- note:
- evidence: thread IDs; frequency
- confidence:

### G. Questions for the legal team

#### B07-Q1

- question: for example, "Why was the cap raised to 150% in B07-T03 but held at 100% in B07-T05?"
- why it matters: which skill or fact it affects
- evidence: thread IDs

`END OF BATCH B07`

---

## Consolidated deliverables (only after CONSOLIDATE)

Start each file with a line `=== FILE: <name>.md ===` so each can be cut out and saved on its own.

### 1. Front-door guide: `front-door.md`

The overarching way of working for the legal inbox.

```
---
name: front-door
description: How the legal team handles its intake inbox: request types, routing, triage, turnaround, escalation and style. Use for any new request.
area: all
version: 0
status: draft (unverified)
last_reviewed:
supporting_matters: thread IDs
---
```

Sections:
- Request types we see, with counts
- Who asks, and what they usually want
- What we ask first
- Who handles what, and routing to other teams
- What goes straight to a lawyer
- Turnaround norms
- Escalation
- Style of our replies
- What usually follows what (for example, an NDA, then a framework agreement, then a statement of work)
- Open questions

### 2. Skill drafts: one file per request type seen in three or more threads

File name: the skill name, for example `nda-review.md`, `msa-liability.md`, `security-questionnaire.md`.

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

Sections:
- When to use
- Questions we ask first
- What is settled: our standard positions
- Positions table (contracts only):

  | Clause | Our standard | Fallback, and when | Red line | Who can approve a move | Evidence |
  |---|---|---|---|---|---|

- What we weigh: the context factors that changed outcomes, with examples
- How it has gone: short cases from the negotiation records. For each: their ask, our position, the outcome, and why. Names follow the company-name rule.
- Where the line is, and when to stop and ask
- How we say it: phrasing patterns and short quotes
- Output shape: what the deliverable looks like (for example, a mark-up plus a cover email of five to eight lines)
- Open questions for this skill

Request types seen in fewer than three threads are not drafted. List them under "Emerging" in the coverage report.

### 3. Knowledge pack: one file per fact or fact set

File name: the type and a short name, for example `entity-german-subsidiary.md`, `standard-answer-encryption-at-rest.md`.

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
- the key facts, each with its evidence;
- for standard answers: the question pattern, our answer, caveats, where it was used, and the owning team.

Never put negotiation positions here. They belong in skills.

### 4. Open questions: `open-questions.md`

Merged and ranked, most important first. Each question names the skill or fact it affects and cites its thread IDs.

### 5. Coverage report: `coverage.md`

- request types, with thread counts
- skills drafted
- emerging request types
- contradictions found
- batches and threads covered
- what was skipped, and why (counts only)
