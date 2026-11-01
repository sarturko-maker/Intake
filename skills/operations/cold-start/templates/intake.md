---
area: {{area}}
status: draft
version: 0
---
<!-- Template for areas/<key>/intake.md (cold-start skill). In the area file: replace {{...}}; replace each "Fill" prompt with content, each point with its source; where nothing is known keep the prompt and write "Not known yet."; delete this comment. -->
# {{area_name}} intake

How requests arrive in this area and what the agent does with them. Legal content comes from this organisation only: house/, knowledge/, approved skills and the lawyer's answers. Draft until the lawyer approves it in chat.

## Request kinds
<!-- Fill from the examples line for this area in house/areas.md: one line per kind, with a typical subject line and the title the matter gets. -->

## What the internal client usually wants
<!-- Fill: per request kind, what the requester is really after, for example a signed document by a date, a yes or no, a marked-up draft. -->

## Questions legal asks first
<!-- Fill: per request kind, the facts legal needs before acting, for example which entity contracts, the value, the deadline, who the other party is. -->

## What the agent may do unasked
<!-- Fill: additions for this area that the lawyer approves. -->
- File, read, record the matter memory, write brief.md, propose an outcome and a next step.
- Draft only when the controlling skill says so and the budget mode allows. Never send.

## What always goes to the lawyer
<!-- Fill from house/brief.md and knowledge/policies/: additions for this area. -->
- Every decision, every outcome, every reply.
- Sensitive mail (misdirected, another party's privileged material, HR-personal), possible impersonation, and any signing, payment or bank-detail request.

## Title and five-bullet rules
<!-- Fill: a title pattern per request kind, for example "<Party> <document>: <open point>". -->
- Title: at most 80 characters, one line, a lawyer's file title. No RE:, FW:, addresses, dates or reference. A title the lawyer changed stands.
- Summary: at most five bullets. Each has a title of at most 40 characters and one line of text of at most 300 characters.

## Labels
<!-- Fill from the request kinds: the short labels used here, a few words each, for example NDA review, questionnaire. A new recurring label is proposed in the digest and added after a yes. -->

## Outcome vocabulary
<!-- Fill: what each outcome usually means for this area's request kinds. -->
- nothing_needed: no legal work; the lawyer confirms.
- ready_for_lawyer: read and prepared; the lawyer decides or acts.
- needs_info_from_requester: legal needs facts from the requester first.
- out_of_area: belongs to another team; the brief names the suggested home.
- in_progress: work under way; nobody is waiting on the lawyer yet.
- needs_lawyer: sensitive mail only; contents not recorded.
