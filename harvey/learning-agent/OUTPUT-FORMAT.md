# Output format

## IDs

Every ID except the thread pointer is permanent and lives in the files. The thread pointer only says where the evidence is.

| Item | ID |
|---|---|
| Matter | M001 |
| Negotiation record | M012-N1 |
| Knowledge | K001 |
| Ways of working | W001 |
| Work type | WT01 |
| Front-door note | F001 |
| Question | Q001 |
| Document to fetch | D001 |
| Thread pointer | B07-T03 |

Leave a field empty rather than guess.

---

## File 1. `legal-matters.md`

```
# Legal matters

## Status
- batches covered: B01 to B07; email dates from 2026-09-14 to 2026-11-02
- matters: 0 (open 0, done 0, unknown 0)
- by source: intake 0, lawyer's mailbox 0
- last updated: B07
```

Then one entry per matter, newest matter first, by the date of its latest email.

```
### M012 | Customer NDA on their paper for data centre projects
- work type: WT03 NDA review | area: commercial | source: intake
- our company: full legal name | counterparty: C2, regional data centre developer
- requester: regional channel manager, Middle East sales | handled by: commercial counsel (routed by senior legal counsel)
- dates: first email 2026-09-02, last email 2026-10-06 | status: done
- value and urgency: low six figures, sales pressing for early signature
- work: judgement | effort: medium | legal output: mark-up, then approval
- turnaround: first reply after 1 day; finished after 22 days; 1 chaser
- legal response visible: partly | negotiation: M012-N1, M012-N2 | knowledge: K004 | to fetch: D003
- evidence: B01-T02, B05-T07
Sales asked whether the customer's mutual NDA could be signed. The mailbox owner routed it to a commercial counsel the same day, who sent redlines through sales and asked whether the customer would accept them. After two rounds, with one chaser, legal approved the changes and asked sales to sign and return the executed copy. Afterwards sales asked to change our signing company; that is open. The content of our redlines is not visible.
```

Field values:
- **work:** judgement (needs a lawyer), lookup (records or facts), process or admin, or routing (to another team).
- **effort:** quick (minutes), medium (about an hour), or heavy (more).
- **legal output:** advice, mark-up, approval, delegation, question back, refusal, or none visible.
- **status:** open, done or unknown.

Paragraph rules:
- 60 to 150 words, in date order, start to finish.
- Say what was asked, what legal did, the positions and the outcome, why, and what is still open.
- Rewrite the whole paragraph when new emails arrive, older or newer.
- Merged matters keep the lower ID. Add "(merged from M045)" to the header.

---

## File 2. `legal-learning-register.md`

### 0. Status

- batches covered and email date range
- counts: work types, ways-of-working entries, positions topics, precedents, front-door notes, knowledge entries, glossary terms, open and answered questions, documents to fetch (open and fetched)
- last updated: the batch

### 1. Work-types report (kept current every day)

One block per work type:

```
#### WT03 NDA review
- what it is:
- matters: count, and the IDs
- share of all matters: percentage
- typical requester:
- nature: mostly judgement, lookup, process or routing, with counts
- typical effort:
- handled by:
- typical turnaround: first reply, finish
- typical outcome:
- skill status: emerging (under 3 matters), or ready (3 or more); proposed skill name
```

Add a new work type only when none fits, and say so in the change log.

### 2. Ways of working, by work type

For each work type:
- the steps, in order, and who does each;
- questions we ask first;
- who decides and who approves;
- how we phrase things, with short quotes;
- each point as a W entry with evidence, frequency, observed or stated, and confidence.

### 3. Positions and precedents, by clause topic

For each topic (for example, liability cap, indemnity, governing law, guarantee scope, contracting entity, payment terms, which paper to start from):
- our standard;
- the fallbacks seen, and when;
- red lines;
- who approved moves;
- the precedents. One line each, giving: the negotiation ID, the counterparty code and type, their ask, our position, the outcome, why, and the email date.

### 4. Front door

As F entries with evidence:
- routing, and who handles what;
- recurring requesters;
- turnaround and chasers;
- escalation;
- reply style;
- hand-offs to other teams (US or group legal, credit, procurement);
- work that may not need a lawyer;
- what usually follows what.

### 5. Knowledge

`K id | type | fact | as of | evidence | confidence | status (current, earlier position until <date>, superseded by, contradicted by)`

Types:
- entity
- policy
- person_role
- standard_answer
- template
- product
- certification
- contract_record
- a new type you propose (say so)

For a standard answer, add: question pattern, our answer, owner, caveats.

### 6. Our companies

`full legal name (with legal form) | jurisdiction | what it does | other names seen | evidence`

### 7. Code key (outside parties)

`code | name (for my use only; deleted before sharing) | type | description (sector, size, region, relationship) | first seen`

### 8. Glossary

`term | meaning | evidence`. If the meaning is unclear, write "meaning not known, ask".

### 9. Roles

Who does what, by role only: the legal team, US or group legal, credit, procurement, sales, others.

### 10. Open questions

`Q id | question | affects | evidence | status (open, or answered by <thread> with the answer)`

### 11. Documents to fetch

`D id | matter | what is missing | where it probably is | why it matters | status (open, or fetched in <batch>)`

### 12. Change log

One line per batch:
- the batch and the email dates;
- matters added, updated and merged;
- entries added, updated and superseded;
- questions answered;
- the counts before and after.

---

## The daily chat report

### A. Batch log

- batch and email date range
- emails received, and from which source (intake or a lawyer's mailbox)
- threads: count and pointers
- skipped as noise: number and kinds
- skipped as sensitive: number and categories only
- attachments read; attachments not readable, with name and reason
- legal response visible: in how many threads out of how many
- re-identification risks
- notes

### B. Matters touched

For each matter: the ID, new, updated or merged, the title, and one line on what changed.

### C. Negotiation records

One block per new or changed negotiated point.

```
#### M012-N1 | clause topic
- document: for example, customer's master agreement, on their paper
- their position:
- our position: or "not visible" (then add a D entry)
- our standard: if "Our templates" is attached
- gap:
- their reaction:
- outcome: accepted ours, agreed fallback, we conceded, they conceded, open, or walked away
- final position:
- why (context): or "context not visible"
- who approved:
- email date:
- evidence: thread pointers
- observed or stated:
- confidence:
```

### D–H. Changes made today

One short line per item, with its ID:
- D: knowledge changes;
- E: ways-of-working changes;
- F: front-door and work-type changes;
- G: new questions;
- H: documents to fetch.

### I. File check

- both files saved: yes or no
- counts before and after, for each file
- confirmation that no count went down

`END OF BATCH B07`

---

## Skill and report deliverables (only after BUILD SKILLS)

Start each file with `=== FILE: <folder>/<name>.md ===`, so each can be cut out and saved.

Size limits:
- each SKILL.md: under about 4,000 words;
- each skill set (SKILL.md plus companions): under about 15,000 words, roughly 20,000 tokens.

If a skill set would be larger, split the skill.

### 1. `reports/work-types.md`

A report, not a skill. It includes:
- every work type, with volume, share, requesters, nature, effort, turnaround, who handles it, outcomes and skill coverage;
- the emerging types;
- a short closing section: "What needs a lawyer, and what may not".

### 2. `front-door/SKILL.md`

```
---
name: front-door
description: How the legal team handles what reaches it: work types, routing, triage, turnaround, escalation and style. Use for any new request to legal.
area: all
version: 0
status: draft (unverified)
last_reviewed:
supporting_matters: matter IDs
---
```

Sections:
- Work types and the skill that covers each
- Who asks, and what they usually want
- What we ask first
- Who handles what, and routing to other teams
- What goes to a lawyer, and what is a lookup or process
- Turnaround norms
- Escalation
- Style of our replies
- What usually follows what
- Open questions

### 3. `<skill-name>/SKILL.md`, plus companions where needed

Use the same frontmatter shape: name, description, area, version 0, status, last_reviewed, supporting_matters.

SKILL.md sections:
- When to use, and when not
- Questions we ask first
- How we handle it: the steps, who does each, who approves
- What is settled: our standard positions, in short
- What we weigh: the context factors that change outcomes, with short examples
- Where the line is, and when to stop and ask
- How we say it: phrasing patterns and short quotes
- Output shape
- Companion files: what each holds and when to read it
- Open questions

`positions.md` (contract skills):

| Clause | Our standard | Fallback, and when | Red line | Who can approve a move | Evidence |
|---|---|---|---|---|---|

`precedents.md`: short cases. Each gives the counterparty type and code, their ask, our position, the outcome, why, and the negotiation ID.

### 4. `knowledge/<type>-<short-name>.md`, one per fact or fact set

```
---
type:
name:
aliases:
owner:
source: matter IDs and documents
origin: seed
valid_from:
valid_until:
last_confirmed:
confirmed_by:
---
```

Body: a summary, then the key facts with evidence.

Also write:
- `knowledge/our-companies.md`;
- `knowledge/glossary.md`;
- `knowledge/code-key.md` (outside parties only, without the name column).

Never put negotiation positions in the knowledge pack.

### 5. `reports/open-questions.md` and `reports/coverage.md`

- **Open questions:** ranked, each with what it affects and its evidence.
- **Coverage:**
  - matters by source and status;
  - skills drafted, with word counts;
  - emerging types;
  - contradictions;
  - documents still to fetch;
  - skipped counts.
