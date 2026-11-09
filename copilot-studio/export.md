# Export: from the lab to the approved libraries

How approved content moves from the lab (this workspace on the lawyer's laptop) into the build's two libraries. The lawyer does it, by hand, never through GitHub: skills, positions and knowledge hold house positions and company facts.

The lab writes skills and knowledge entries as its own working view, without asking. Export is where the lawyer's yes is needed: only approved versions go, and approval happens in one sitting before an export, not item by item during the week.

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

Anything marked working (a working skill, a working knowledge entry, however many matters it rests on); drafts of any kind; seeds and Harvey output; interview transcripts and notes; matter files and matter memory; the learning register; the house files themselves.

## Steps

1. **Approve what is to go.** In the lab, say "approve the knowledge entries" and "approve <skill>". The lab lists the working ones; answer in your own words ("all except 3 and 7", "5 is owned by Finance"). A skill the lab rewrote after you approved it is working again: it shows what differs from the approved version, and you approve the new one or export the old.
2. **List** what is approved or changed since the last export ("what is ready to export"): skills with `status: approved` and a new version; knowledge entries with a later `last_confirmed`; approved playbooks, question bank entries and the rest. A lab command for the list comes later ([lab-changes.md](lab-changes.md)).
3. **Check each item:** the audience from the table above; no names of clients, people or matters, except in legal-only items that need them. Worked examples describe parties by type ("a large automotive customer").
4. **Format:** strip the lab's markers first: the lines "what it rests on" stay for the legal library and come out for the Sales library, and the "Not sure yet" and "What changed" sections never go. Use what the knowledge source reads well (check in Phase 0). Word is the safe choice; keep Markdown if it indexes properly.
5. **Upload** and fill in the metadata ([data-model.md](data-model.md), Approved libraries): item type, audience, owner, approved by and on, valid from, review by, version, lab source.
6. **Replace, don't pile up.** A new version replaces the old file; library version history keeps the old one. An item the lab withdrew (`valid_until` set) is removed from the library the same day.
7. **Record** the export in the lab's export log: date, item, version, library.
8. **Retest:** after a change to the Sales library, rerun the Teams agent's test questions ([p1-agent-and-button.md](p1-agent-and-button.md)).

## Review

Every item has a review-by date (default 12 months after approval). Each month the paralegal lists what is due; the approver confirms it, changes it or withdraws it.
