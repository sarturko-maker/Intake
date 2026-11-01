# Phase 2: learning and visibility

Phase 2 is not built yet. Nothing in this folder is active. Phase 1, the working intake, does not read or write anything here.

## What phase 2 adds

- **A dashboard.** A page you open in a browser, built from INDEX.csv and BUDGET.md: what to do next, your queue, open matters by area and age, noise to confirm, the budget, and matters closed in the last 30 days. A small helper, `tools/dashboard-build`, will write it as `DASHBOARD.html`.
- **Proposals at wrap-up.** When a matter closes, the agent writes a short proposal to improve a skill, a playbook or an area's intake file: the old and new wording, the reason, the matters behind it, and an example with names removed. Proposals go into `areas/<area>/proposals/`.
- **A leak check.** Before a proposal is shown, `tools/leak-check` searches it for names, organisations, addresses and figures from the matters it came from. A hit stops it. If the check cannot run, the agent checks by hand and records that it did.
- **A monthly review.** "learn" or `/learn` reads the proposals, the workflow log, the journal and the four measures, and writes one monthly review with suggested changes. New skills are suggested only when three or more closed matters support them. You approve in chat; the agent applies the changes, raises the version numbers and updates the skills.
- **Shape review.** Suggestions about the folder structure: subjects that look like duplicates, sub-areas nobody uses, groups of matters that want a sub-area of their own. Suggestions only; you decide.
- **Type proposals** for the knowledge base during the monthly review, and seeds cited in drafts as leads.

Phase 2 is done when a month of closed matters has produced skill changes you approved.

## The dashboard sample

`DASHBOARD.sample.html` is a prototype filled with sample data, to show the idea. It is not connected to anything: it does not read INDEX.csv, and it does not update. Open it in a browser to see what phase 2 is aiming for. Do not rely on its numbers.

## Until then

Phase 1 already gives you most of this in text:

- `digests/LATEST.md` ends with what you should do next and shows the four measures.
- `INDEX.md` lists every open and closed matter.
- "close 2026-0042" and "checkpoint 2026-0042" ask you up to three short questions about why things went the way they did, and keep your answers.
- "learn" tells you it is not active yet and notes that you asked.
