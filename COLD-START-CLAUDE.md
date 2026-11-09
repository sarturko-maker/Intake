# Cold start for the agent (`/cold-start`)

Run on first open on a machine, and whenever `TOOLING.md` is missing. Show each result; do not assert it. Procedure in detail: `skills/operations/cold-start/SKILL.md`.

## Before anything

1. Read `RULES.md`, then `HANDOFF.md` if present, then `house/brief.md`, `house/areas.md`, `BUDGET.md` if present.
2. If `house/brief.md` or `house/areas.md` still says `status: template`, or a brief line is empty (organisation, legal_entities, house_domains, legal_addresses, intake_mailbox, timezone, lawyer_name), stop. Tell the human what to fill in, and to change both files to `status: ready`. Do not invent names or areas.

## Step 1. Tools: detect, install, verify, record

Run `bash tools/tooling-setup`. It detects each tool, verifies it on a sample file in `tools/fixtures/`, writes `TOOLING.md` (one line per item: `item | status | version | fallback in use | note`) and prints what is missing with one question, "May I install: ...?". Ask the human that question once, in chat. On yes, run `bash tools/tooling-setup --install`: it installs through the available package manager, verifies again and rewrites `TOOLING.md`. On no, keep the fallbacks it recorded.

| Tool | Why | If it cannot be installed |
|---|---|---|
| shell | everything | ask which shell exists |
| SHA-256 | duplicates, integrity, change scan | built in everywhere |
| `python3` | `.eml` parsing, CSV generation | shell plus `munpack`; write CSV directly |
| `.msg` converter (`python-oxmsg` with `tools/msg2eml`, or `msgconvert`) | `.msg` to `.eml` | PowerShell with Outlook desktop (`tools/msg2eml.ps1`); else ask for `.eml` |
| `pandoc` | `.docx`, `.html` to text | `python-docx`; else unzip and strip tags |
| `munpack` or `ripmime` | attachments without Python | human saves attachments into the matter |
| `git` | diffs, second history | `history/` and SharePoint versions |
| hooks and deny rules active? | RULES.md, Protections | follow the Protections obligations by hand: history copies, the 16,000 cap, lint-facts after facts |

If Python is blocked by policy, record it and move on. Record every workaround in `WORKFLOW-LOG.md`.

## Step 2. Skeleton

1. Create `areas/<key>/` per `house/areas.md` with `playbook.md`, `intake.md`, `proposals/`, and declared sub-area folders. Always `areas/general/`. Subject folders are created only when a matter needs them.
2. Missing playbook or intake file: draft it from the area description and the templates in `skills/operations/cold-start/templates/`, `status: draft`.
3. `knowledge/TYPES.md` ships with the defaults; if it is missing, tell the human. Create `BUDGET.md` for this month with `bash tools/budget-update --init`.
4. Run `bash tools/skills-sync`. Run `bash tools/scan-changes --run RUN --write-manifest` to create `MANIFEST.csv`.
5. Prove the protections. Deny rules: try to create `areas/_protection-test/human/corrections.md` and report the refusal; if it goes through, delete the test folder at once. (house/ is not denied: Claude Code asks the lawyer before each change there.) Hooks: write a test `matter.md` and check that a history copy appears; then remove the test folder. Record both lines in `TOOLING.md`: verified, or not live with the RULES.md obligations as the fallback.

## Step 3. Read and index what the human put in

1. Read every file in `house/`, `knowledge/`, `seeds/`. For each, a one-paragraph summary and the section tree with locators.
2. Write `knowledge/INDEX.md` as a tree: folder, file, summary, sections. Seeds marked `origin: seed`.
3. Dropped documents lacking owner, source or validity date: list in the first digest under "Needs an owner or date". Do not guess owners.
4. Standard answer sets, entity lists, people lists: split them into one working knowledge entry each (RULES.md, Knowledge). Nobody is asked; say what was done.
5. Material fitting no type in `knowledge/TYPES.md` three times over: add a type to `knowledge/TYPES.local.md`, and say so.

## Step 4. Inbox

If `inbox/` has files, run `/intake` (RULES.md, Intake); otherwise run `/status`. Either way `bash tools/index-rebuild --run RUN` rebuilds `INDEX.csv` and `INDEX.md`, the cost goes into `BUDGET.md`, and the first digest ends with "What you should do next".

- Unsure filings go to `inbox/please-check/`, each with a note: why you are unsure, what you would do, what the lawyer should decide.
- Noise goes to `inbox/noise/`. The digest gives one line the lawyer can paste back: `confirm nothing needed: NOISE-0001, NOISE-0002`.
- Misdirected, another party's privileged or HR-personal mail becomes a `needs_lawyer` matter under `general/unfiled`, titled "Sensitive: for the lawyer", with nothing recorded from its contents.

## Step 5. Report

Five lines or fewer: tools found, installed or blocked with fallbacks; what was created; what was indexed; what needs an owner or date; where to look (`digests/LATEST.md`, `INDEX.md`, `inbox/please-check/`).

## Every later session

Read `RULES.md`, `TOOLING.md`, `BUDGET.md`, `HANDOFF.md` if present, the latest scan report in `changes/`, open rows of `INDEX.csv`, last twenty lines of `WORKFLOW-LOG.md`. Obey the mode in `BUDGET.md`. Then do what was asked.

| Command | Plain phrase | Does |
|---|---|---|
| `/intake` | "process the inbox", "scan" | RULES.md, Intake, end to end; inbox empty afterwards |
| `/status` | "where are we", "what should I do" | rebuild index, `INDEX.md`, digest; no new reading |
| `/status` | "confirm nothing needed: NOISE-0001, NOISE-0002" | those noise items closed; files move to `inbox/noise/confirmed/` |
| `/status` | "file the please-check email from <sender> in 2026-0042" | filed there; its note moves to `inbox/please-check/resolved/` |
| `/close REF` | "close 2026-0042" | status closed, then the wrap-up; asks nothing |
| `/checkpoint REF` | "checkpoint 2026-0042" | wrap-up without closing |
| `/bundle REF` | "bundle 2026-0042 for Harvey" | work bundle; Legora or another tool works the same way |
| `/draft-skill NAME` | "draft a skill for NDA review", "approve nda-review", "approve the knowledge entries" | write one working skill now; stamp approval |
| `/index` | "re-index knowledge" | knowledge index |
| `/budget` | "how much have we spent", "budget actual 37.20" | ledger and mode; records the actual bill |
| `/learn` | "learn", "catch up", "what have you learned", "in the NDA skill, ..." | write the working skills and knowledge entries now; apply what the lawyer says; asks nothing |
| `/interview TOPIC` | "interview me about NDAs" | only when the lawyer asks: reacts to the working skill, then a few questions |
| `/guided-learning TOPIC` | "guided learning on LOAs", "interrogate me about <topic>" | questions in layers about a topic or a document you bring: purpose, shape, practice, then where it meets what is already known |
| `/reply REF` | "draft a reply to 2026-0042" | draft a reply to send yourself |

If a helper fails on this machine, use its fallback, say so in the digest, add a line to `WORKFLOW-LOG.md`.
