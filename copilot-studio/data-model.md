# Data model

Where everything is kept in the build, and how it maps onto the lab's files. Column names are suggestions; keep the meanings.

## The reference

- Format `<prefix><YYYY>-<NNNN>`, for example `2026-0042`: one counter per year, never reused, never changed.
- From Phase 1 the register is the only place that hands out references. The lab uses the register's references from then on ([lab-changes.md](lab-changes.md)).
- Every email legal or the agents send ends its subject with `[<reference>]`. A reply is matched by that tag first, then by the email's thread headers (In-Reply-To, References), then by sender and subject, and only then treated as new.

## Matter library (SharePoint document library)

One folder per matter, named by its reference:

```
2026-0042/
  correspondence/        emails as .eml, named YYYY-MM-DD_HHMM_<in|out>_<from>_<subject>.eml
  documents/received/    attachments as received, names kept
  documents/ours/        what legal sent
  drafts/                agent drafts for the lawyer (Phase 1.5 on)
```

Files are never edited: library versioning on, received files read-only by permission. A name that would make a path too long is shortened, with the original name kept in the file's metadata. These are the lab's naming rules, so the lab's reading tools work on these files unchanged.

## Register (SharePoint list; may move to the ticket system in Phase 2)

| Column | Type | Written by |
|---|---|---|
| Reference | text, unique | flow |
| Title | text, 80 characters | flow from the subject (Phase 1); agent (1.5 on); the lawyer may edit |
| Status | new, open, waiting_requester, waiting_counterparty, waiting_lawyer, closed | flow, agent, lawyer (only the lawyer sets closed; see the contract for Phase 3) |
| Source | button, mailbox, direct | flow |
| Received | date and time | flow |
| Requester, requester team | person, text | button form or mailbox |
| Counterparty | text | button form; agent (1.5 on) |
| Need | review a document, question, approval, other | button form |
| Due | date | button form; agent (1.5 on) |
| Value band | choice, optional | button form |
| Area, sub-area, work type | choices from the legal taxonomy | lawyer (Phase 1); agent, corrected by the lawyer (1.5 on) |
| Claimed by, claimed at | person, date and time | Claim card |
| Waiting on, next step | choice, text | lawyer; agent (1.5 on) |
| Proposed outcome | nothing_needed, ready_for_lawyer, needs_info_from_requester, out_of_area, in_progress | agent (1.5 on) |
| Confirmed outcome, lawyer minutes, accepted unchanged | choice, number, yes/no | lawyer only |
| Ready at, closed | date and time, date | flow; lawyer |
| Sensitive, flags | yes/no, multiple choice | flow, agent |
| Folder, five points, open questions | link, link, number | flow |

## Question log (SharePoint list)

One row per question legal asks a requester before it can start, or the agent drafts.

| Column | Meaning |
|---|---|
| Question ID | `<reference>-Q<n>` |
| Reference, work type | the matter, and its work type |
| Question | as drafted |
| Why | what the answer unblocks, in one line |
| Drafted by | lawyer or agent |
| Lawyer's verdict | match, partly, missed, unnecessary (Phase 1.5 scoring) |
| Final wording, sent on, sent by | what actually went out |
| Assumption stated | the default used instead of asking, if any (Phase 2) |
| Answer, answered on, answered by | the reply |
| Status | open, answered, assumed, withdrawn |
| Bank entry | the question bank entry it matches, once mapped |

## Facts table (Dataverse, Phase 1.5)

The lab's facts.md as a table. Rows are only ever added: a change is a new row that names the row it supersedes. Security role: create and read, never update or delete.

| Column | Meaning |
|---|---|
| Fact ID | F0001, F0002 ... within the matter |
| Reference | the matter |
| Recorded on | date |
| Type | party, term, date, decision, open_point, fact |
| Valid from | when it became true, if known |
| Source | the file and the place in it: `documents/received/MSA_v2.docx cl. 9.2` |
| Supersedes | the Fact ID it replaces, if any |
| Text | one statement |
| Recorded by | agent, lawyer, paralegal |

The live facts are the rows nothing supersedes.

## Approved libraries (SharePoint)

Two libraries, the Sales library and the legal library ([CONTRACT.md](CONTRACT.md), Audiences). Every file carries:

| Field | Meaning |
|---|---|
| Item type | standard answer, template, guide, checklist, skill, playbook, position, question bank entry, risk category, routing rule, entity, policy |
| Audience | sales or legal |
| Owner | the team or role that owns it |
| Approved by, approved on | who said yes, and when |
| Valid from, valid until | empty valid until while current |
| Review by | default 12 months after approval |
| Version | raised on every change |
| Lab source | the file in the lab it came from, and its version |

## From the lab to the build

| Lab | Build |
|---|---|
| INDEX.csv | Register |
| areas/.../<matter>/agent/correspondence, documents/ | Matter library folder |
| facts.md | Facts table |
| brief.md | The ticket body (Phase 2) |
| What we still need from them (brief.md), outcome needs_info_from_requester | Question log rows |
| knowledge/ entries, approved skills and playbooks | Approved libraries, by [export.md](export.md) |
| house/areas.md, areas/*/intake.md labels | The legal taxonomy (area, sub-area, work type) |
