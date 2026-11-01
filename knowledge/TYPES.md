# Knowledge types

The kinds of company fact the knowledge base holds, and the folder for each. The agent files every knowledge entry under one of these types. When something fits none of them, it asks you before it adds a type.

One Markdown file per thing: one policy, one company, one role, one standard answer. The files you drop in, in any format, stay as they are. The agent reads them and lists them in knowledge/INDEX.md. It writes entries from them only after you say yes.

## Default types

| Type | Folder | What it holds | Example | Also required |
|---|---|---|---|---|
| policy | knowledge/policies/ | An internal policy in force: what it requires and who owns it | Information security policy | nothing more |
| entity | knowledge/entities/ | A group company or other legal entity: legal name, number, registered office, directors, who signs for it | The German subsidiary | aliases (trading or short names) |
| person_role | knowledge/people/ | A role: who holds it and what they approve | Head of IT security | links: `held_by` |
| standard_answer | knowledge/standard-answers/ | An approved answer to a question that comes up again and again | "Do you hold ISO 27001 certification?" | owner is the owning department; body sections below |
| template | knowledge/templates/ | A house template and when to use it | Mutual NDA template | nothing more |
| position | knowledge/positions/ | A negotiating position: preferred, fallback, never, and who may approve an exception | Liability caps | links: `approved_by` |
| product | knowledge/products/ | A product or service: what it is, where it is made, its export classification | A pump range | nothing more |
| certification | knowledge/certifications/ | A certificate or accreditation: scope, issuer, expiry | ISO 27001 certificate | valid_until (the expiry date) |
| contract_record | knowledge/contract-records/ | The key terms of a signed contract | Signed framework agreement with a customer | valid_until (end of term; empty if open-ended); links: `counterparty` |

The agent creates a folder the first time it writes an entry of that type.

## Every entry

```
---
type: standard_answer
name: ISO 27001 certification
aliases: ISO27001
owner: IT security
source: knowledge/standard-answers/2025-supplier-questionnaire.docx Q12
origin: document
valid_from: 2026-01-01
valid_until:
last_confirmed: 2026-11-02
confirmed_by: you
links:
  - answered_from: knowledge/certifications/iso-27001-certificate.md
---
```

| Key | What it means |
|---|---|
| type | One of the types on this page. |
| name | What it is called. |
| aliases | Other names, separated by commas. May be empty. |
| owner | The team or role that owns it. |
| source | Where it came from: a file and the place in it, a matter reference, or "chat YYYY-MM-DD". |
| origin | document, chat, seed or matter. |
| valid_from | The date it became true, YYYY-MM-DD. |
| valid_until | The date it stopped being true. Empty while it is current. |
| last_confirmed | The date the lawyer last confirmed it. |
| confirmed_by | Who confirmed it. |
| links | One line per link, indented, in the form `- relation: target`. May be empty. |

Required in every entry: type, name, owner, source, origin, valid_from, last_confirmed, confirmed_by, plus the type's own column above. Never guess a value. If one is unknown, leave it empty: the index then lists the file under "Needs an owner or date" until someone fills it in.

The body starts with a short summary, then the key facts, each with its source. A standard_answer also has these sections: question pattern; answer; caveats; where used; owning department.

## Changing an entry

Never a silent edit. Set valid_until on the old entry, write a new entry, and link the two.

## Proposing a new type

1. Something fits none of the types above. The agent proposes a new type in one chat sentence, with an example. For instance: "The trade mark register fits no type. May I add a type trade_mark, in knowledge/trade-marks/, for registered marks and their renewal dates?"
2. Until you answer, the file is indexed with type `unknown`.
3. After your yes, the agent adds a row to the table above and creates the folder. After a no, nothing changes.

The same rule applies to sub-areas and to labels: propose with an example, add only after a yes. You add sub-areas to house/areas.md yourself.

Type names are lowercase with underscores. Folder names are lowercase, plural, with hyphens.
