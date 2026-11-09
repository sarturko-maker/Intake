# Export: from the lab to the approved libraries

How approved content moves from the lab (this workspace on the lawyer's laptop) into the build's two libraries. The lawyer does it, by hand, never through GitHub: skills, positions and knowledge hold house positions and company facts.

## What may go, and where

| From the lab | Library | Condition |
|---|---|---|
| Standard answers (knowledge/standard-answers/) | Sales | Confirmed, current, owner named; the owner approved the wording |
| Templates | Sales, if the lawyer marks it for Sales use; else legal | Current version |
| Policies | Sales if it applies to all staff; else legal | Current |
| Entities: our companies' legal names, numbers and addresses | Sales | Confirmed; who signs for each, legal only unless the lawyer marks it for Sales |
| Products, certifications | Sales | Current; certifications within their expiry |
| People and roles, approval limits | Legal | Confirmed |
| Positions: preferred, fallback, never | Legal | Never in the Sales library |
| Signed-contract records | Legal | Current |
| Legal skills (skills/<area>/<name>/) | Legal | status: approved |
| Area playbooks and intake files | Legal | status: approved |
| The legal taxonomy: areas, sub-areas, work types (house/areas.md, areas/*/intake.md labels) | Legal | Current; one file |
| Sales guides: "when to send to legal", "what legal needs from you" | Sales | Written for Sales and approved by the lawyer |
| The five points | Sales | Approved version ([five-points.md](five-points.md)) |
| Question bank entries, risk categories, the routing table | Legal | Approved by the lawyer |

## What never goes

Drafts of any kind; seeds and Harvey output; interview transcripts and notes; matter files and matter memory; the learning register; the house files themselves; anything not yet confirmed or approved.

## Steps

1. **List** what is approved or changed since the last export: skills with `status: approved` and a new version; knowledge entries with a later `last_confirmed`; approved playbooks, question bank entries and the rest. By hand for now; later a lab command ([lab-changes.md](lab-changes.md)).
2. **Check each item:** the audience from the table above; no names of clients, people or matters, except in legal-only items that need them. Worked examples describe parties by type ("a large automotive customer").
3. **Format:** use what the knowledge source reads well (check in Phase 0). Word is the safe choice; keep Markdown if it indexes properly.
4. **Upload** and fill in the metadata ([data-model.md](data-model.md), Approved libraries): item type, audience, owner, approved by and on, valid from, review by, version, lab source.
5. **Replace, don't pile up.** A new version replaces the old file; library version history keeps the old one. An item the lab withdrew (`valid_until` set) is removed from the library the same day.
6. **Record** the export in the lab's export log: date, item, version, library.
7. **Retest:** after a change to the Sales library, rerun the Teams agent's test questions ([p1-agent-and-button.md](p1-agent-and-button.md)).

## Review

Every item has a review-by date (default 12 months after approval). Each month the paralegal lists what is due; the approver confirms it, changes it or withdraws it.
