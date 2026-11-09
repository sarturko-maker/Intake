# Phase 2: the proper agent

Goal: legal starts every matter with a complete file. The agent handles intake end to end: it finds what it can, assumes sensible defaults, asks Sales only what is left, and hands the lawyer a ticket with the thread, the documents, the answers and a first draft. Lawyers review and decide; they stop chasing.

## Find out, assume, then ask

For each question the approved question bank lists for the matter's work type ([question-bank.md](question-bank.md)):

1. **Find out.** Look where the answer may already be: the email and the thread, the attachments (the clause), the register's earlier matters with the same customer, approved standard answers. Found: record it as a fact with its source.
2. **Assume.** Not found, and the entry has a default that is safe in this case: use it, and state it to Sales as an assumption they can correct.
3. **Ask.** Only what is left, in one email with a reason for each question and no more than the set number ([templates.md](templates.md)).

A reply is matched by its reference tag ([data-model.md](data-model.md)). The agent runs the same steps again with the new answers. No answer after the set number of working days (**To confirm:** 3) means one reminder; still none means the matter goes to the lawyer as it stands, saying what is missing. When nothing is left, the ticket goes to the lawyer and the status becomes waiting_lawyer.

## The worker

The skills run as a custom worker built on Microsoft Agent Framework in Azure AI Foundry, in the company's tenant and region. Copilot Studio calls it as an MCP tool. It prepares and drafts; it never sends.

### What it is given

- The reference.
- Read access to the matter's folder, its register row, its facts and its question log.
- Read access to the legal library: skills, playbooks, positions, the question bank.

### What it returns

| Part | Content |
|---|---|
| Facts | New fact rows to add, each with its source |
| Questions | For each bank question: found (what, and where), assumed (the default, and why it is safe here), or to ask (the wording and its reason) |
| Ticket | The lab's brief layout: requester; what they want; by when; what we still need from them; what the lawyer must decide; proposed outcome; proposed next step. Plus links to the thread, the key documents and the draft |
| First draft | A reply or note in the matter's `drafts/` folder, for the lawyer |
| Reasoning | Which skill applied, which of its considerations mattered here, the closest worked examples (alike and different), the sources used |
| Stop | When it stops instead ([CONTRACT.md](CONTRACT.md), When to stop), the reason |

The Copilot Studio flow writes the facts, register and question log from what the worker returns. The worker itself writes only to `drafts/`.

### What it is built from

- **Its instructions:** the lab's rules and its intake-reading, matter-memory and reply skills, adapted to the build ([CONTRACT.md](CONTRACT.md) wins on any conflict).
- **Its judgement:** the approved legal skills, loaded by work type. Applying a skill is reasoning, not matching: one matter in a skill is an example, never a rule.
- **Its tools:** the lab's reading helpers are plain Python with no dependencies (`unpack-email`, `redline-changes`, `area-lines`, `lint-facts`), so they can run inside the worker unchanged.
- **Identity:** a managed identity with read access to the libraries and write access to `drafts/` only.
- **Logging:** every call's reference, outputs, model and version, sources and cost, kept with the matter.

## One door

From the start of Phase 2, requests come only through the button or `legal-intake@`. A request sent straight to a lawyer is forwarded by them with the button (one click). Whether direct emails also get an automatic "please use the button" reply: **To confirm**.

## Decision: where tickets live

Decide by the end of Phase 1.5, with its measures in hand: Dataverse (a model-driven app), Jira Service Management, or ServiceNow. Compare them on:
- who else in the company already uses it, and how;
- licence cost, for legal and for requesters;
- how it connects to Copilot Studio and the flows, and what that means for the DLP policy;
- reporting for [measures.md](measures.md);
- where the data is held;
- the effort to move the register, and how requesters see their status.

## Decision: a graph store

Only if the question log earns it: when answering questions often needs facts across matters (the same customer, its group companies, earlier deals, signed contracts) that the lists and the facts table cannot give quickly. **To confirm:** more than one question in five. The facts table's design, dated rows that supersede each other, moves to a time-aware graph without rework.
