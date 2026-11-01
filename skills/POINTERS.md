# Pointers

Reference material for the shape of skills and for checklists. Nothing here is a house position, and nothing here becomes one without the lawyer. A position enters a skill, a playbook or the knowledge base only through /draft-skill or the knowledge confirm flow, after the lawyer says yes.

Every entry below is labelled: reference, not house position. Use it for structure, order and coverage, never for the answer. The fork's legal skills assume US law unless they say otherwise; this organisation's law, positions and tone come from house/, knowledge/, closed matters and the lawyer.

## The fork: lq-ai-fork (Apache-2.0)

Pinned at commit 82904157a155ad2926e4ba64447087f7ef1cdb45:
https://github.com/sarturko-maker/lq-ai-fork/tree/82904157a155ad2926e4ba64447087f7ef1cdb45

Paths below are relative to that commit. Shape and memory rules were borrowed from it; no legal content was copied as a house position.

### Skills

- `skills/nda-review/` (SKILL.md, reference/issue_checklist.md, red_flags.md, severity_rubric.md, perspective_lens.md). Reference, not house position. Useful for: the checklist of NDA protections and one-sided terms, asking which side we are on before starting, and a findings report with a severity per issue and a clause citation for each.
- `skills/nda-snapshot/`. Reference, not house position. Useful for: the grid shape for comparing several NDAs side by side (definition of confidential information, permitted recipients, return or destruction, remedies), with a citation in every cell.
- `skills/msa-review-saas/` (SKILL.md and reference/). Reference, not house position. Useful for: the issue list for software subscription agreements (liability, indemnity, IP, data protection, warranties, term, payment), seen from the vendor or the customer side, with redline wording for material gaps.
- `skills/msa-review-commercial-purchase/` (SKILL.md and reference/). Reference, not house position. Useful for: the issue list for supply and purchase agreements for goods and services (price and payment, delivery and acceptance, warranties, liability, supply continuity, force majeure), seen from the buyer or the supplier side.
- `skills/msa-snapshot/`. Reference, not house position. Useful for: the grid shape for comparing several master agreements on term and renewal, payment, liability cap and indemnity.
- `skills/dpa-checklist-review/` (SKILL.md, reference/gdpr_requirements.md and the other regimes). Reference, not house position. Useful for: a present, partial, missing or unclear checklist for data processing terms by regime, and asking which regime applies before starting.
- `skills/contract-qa/` (SKILL.md, reference/question_classification.md, citation_format.md). Reference, not house position. Useful for: answering one targeted question about a contract: classify the question, give a verdict (standard, unusual, aggressive or favourable) and quote the clause.
- `skills/negotiation-review/`. Reference, not house position. Useful for: answering the other side's mark-up with one decision for every change and every comment (accept, reject, counter, leave open, escalate), counters that change only the operative words, and escalating demands below the floor instead of conceding them.
- `skills/surgical-redline/`. Reference, not house position. Useful for: smallest-change redlining: quote the existing clause, change only the words that matter, give the reason, preview before applying.
- `skills/deal-review/`. Reference, not house position. Useful for: the fan-out then reconcile method for deals with several documents: one drafter per head, a review for over-reach, gaps and inconsistency, then one reconciled position before any work product.
- `skills/playbooks/<name>/playbook.yaml` (nda, nda-unilateral, msa-saas, msa-commercial-purchase, dpa-gdpr). Reference, not house position. Useful for: the shape of a position file: issue, standard language, fallback tiers, redline strategy, severity if missing, detection keywords. The fork itself marks them as unvetted starting points.
- `skills/intake-triage/`. Reference, not house position. Useful for: reading an intake email: decide what it is first, check sender authenticity, classify misdirected, privileged or HR-personal mail without recording its contents, write a file title of at most 80 characters and a summary of at most five bullets, send nothing. Shapes skills/operations/intake-reading/.
- `skills/matter-memory/`. Reference, not house position. Useful for: the memory craft: a living one-page summary rewritten whole, dated facts with their sources, supersede and never overwrite, corrections win, consolidate when the memory drifts, memory describes and never authorises. Shapes skills/operations/matter-memory/.

### Doctrine

- `profiles/commercial/doctrine.md`. Reference, not house position. Useful for: the playbook shape: who the agent is, standing disciplines (ground and cite, clarify before guessing, draft for a human, separate the legal line from the business decision), triage of effort, controlling skills, surgical redlining, playbooks as tiered defaults, negotiation, and when to escalate. The shape behind areas/<area>/playbook.md.

### Design records: memory and intake rules

- `docs/adr/F042-unit-of-work-memory-auto-write.md`. Reference, not house position. Useful for: auto-write then correct; the fence on memory of unverified origin; corrections that win and that the agent cannot write; supersede, never overwrite; memory describes, controls authorise.
- `docs/adr/F043-matter-memory-consolidation-egress.md`. Reference, not house position. Useful for: consolidation that only supersedes, applies all or nothing, and never touches a correction.
- `docs/adr/F044-matter-memory-read-and-revert.md`. Reference, not house position. Useful for: "what did we believe on that date" views of the facts, and a copy of the old page before every overwrite, so a human can always go back.
- `docs/adr/F086-email-intake-architecture.md`. Reference, not house position. Useful for: one reading pass per email thread; nothing sent automatically, not even an acknowledgement; free-form labels for display only; intake behaviour kept in a readable skill, not in configuration.
- `docs/adr/F088-matter-reference-and-email-stamping.md`. Reference, not house position. Useful for: references that never change once issued, and the inbound trust ladder: weak signals never file on their own; a subject tag files only when the sender is on that matter's roster; otherwise the claimed reference is recorded for the lawyer.
- `docs/adr/F048-matter-participant-roster.md`. Reference, not house position. Useful for: the roster of who is who on a matter, the side deciding how a person's changes are treated, a human-confirmed side never overridden, and asking about unknown authors.
- `docs/adr/F082-workspace-awareness-document-summaries.md`. Reference, not house position. Useful for: duplicates found from file hashes only, never from what a document claims, and a one-line summary per document.
- `docs/fork/research/matter-memory-patterns.md`. Reference, not house position. Useful for: the survey of agent memory systems behind auto-write then correct.

## Outside the fork

- PageIndex by VectifyAI, https://github.com/VectifyAI/PageIndex (MIT). Reference, not house position. Useful for: the tree index idea: a contents tree with a summary and a page or line locator per section, read before opening documents. knowledge/INDEX.md follows the idea in plain Markdown. The package is not used.
- The "LLM Wiki" pattern published by Karpathy as a gist. Reference, not house position. Useful for: an agent that keeps a folder of Markdown pages with an index and a log, and checks them for contradictions and stale entries. The matter memory and the knowledge base follow the convention only. Nothing was copied: the gist has no licence.
