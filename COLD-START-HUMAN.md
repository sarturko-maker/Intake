# Cold start for a person

One page. Half an hour.

## 1. Install and open

- Install Claude Code, or open Claude Cowork, on the machine with the workspace folder. Copilot or another assistant works too: point it at `RULES.md`. On Windows, also install Git for Windows so the helpers can run.
- If the folder syncs to OneDrive or SharePoint, mark it "Always keep on this device".

## 2. Fill in two files in `house/`

- `house/brief.md`: legal names and entities, the email domains that count as "us", the addresses of the legal team and the shared legal mailbox, timezone, who legal acts for, where signing authority and approval limits are written down, the tone for drafts. Prompts are in the file.
- `house/areas.md`: your practice areas. For each: key, name, what you call a unit of work there, a sentence on what belongs in it, sub-areas if any (customers, suppliers, partners), what names a subject folder (counterparty, project code name, programme), and example request types. Defaults are filled in; change them freely.
- When a file is done, change `status: template` at the top to `status: ready`. These two files are yours, and they are never sent to GitHub. Claude can help you fill them in: it shows each change and writes it only after you say yes (Claude Code also asks for permission).

## 3. Put company facts into `knowledge/`

Drop files into the subfolders, any format, untidied. The agent reads, summarises and indexes everything on the first run, and splits lists (answer sets, lists of companies or people) into one entry each. It does not ask; it says what it did. It also writes entries of its own from what it meets in matters.

- `policies/`, `entities/`, `people/`, `standard-answers/` (past questionnaires with your answers), `templates/`, `positions/`.
- `seeds/` at the top level for anything else to start from, for example an extraction Harvey produced over old emails.

Treat `standard-answers/` as the most sensitive folder and set its permissions accordingly.

## 4. Drop emails into `inbox/`

- Drag from Outlook. New Outlook and web Outlook give `.eml`, which is best. Classic Outlook gives `.msg`; the first run installs a converter if it can, otherwise it asks for `.eml`.
- Drop your sent items too: replies, interim updates and your solutions. Interim ones (thanks, chasing, asking for documents) just update the status. Substantive ones (advice, positions, approvals, mark-ups) are read and teach the skills. If the same email arrives from the intake mailbox and from your Sent Items, it is kept once and not read twice.
- The inbox is emptied on every run; dropping a same-named file later is fine.
- Keep the reference, like `[2026-0042]`, in the subject line when you reply. That is how later emails file themselves.

## 5. First run

Say "cold start". It asks once before it installs anything. From then on, "process the inbox".

You do not have to teach it anything. It learns from the emails.

## 5b. It learns by watching

For now, the system's main job is to learn how you work. It writes a skill for each type of work and writes down company facts as it meets them. It asks you nothing. Day-to-day help (briefs, replies, Harvey packs) is there when you ask for it.

- Keep dropping both incoming emails and your sent items. Your sent items teach it most: what you asked the requester first, what you did, the positions you took and why, how you phrased it.
- Before you answer a request, it notes what it expects you to ask and do. When your reply comes through, it compares the two and corrects itself. `learning/index.md` shows, per type of work, how often it expected right.
- After two matters of the same type, it writes a working skill, and rewrites it as more arrive. Company facts become working knowledge entries. "Working" means its own view, not yet approved by you.
- Read them when you like, in a few weeks if that suits you: open `learning/index.md`, which links every skill and the knowledge index.
- To change anything, tell Claude in your own words: "in the NDA skill, we never accept more than three years", "that is wrong: Finance owns credit limits". Or edit the file yourself. What you say and what you edit is kept, and is never overwritten by what it infers.
- A red line, an approval limit or who may sign is treated as fixed only when you say so.
- "approve nda-review" or "approve the knowledge entries" marks them approved. You only need that before content goes to another system, such as the Copilot Studio libraries.
- If you would rather talk than read: "interview me about NDAs" (it shows you what it thinks and you say what is wrong), or "guided learning on <topic>" with a document. Both are optional.
- "learn" runs the write-up now instead of at the end of the next inbox run.

## 6. Where to look

- `digests/LATEST.md`: what came in, what was proposed, what it assumed, and "what you should do next".
- `learning/index.md`: the skills and company facts it has written so far.
- `INDEX.md`: everything open and closed. `INDEX.csv` opens in Excel.
- `inbox/please-check/`: emails the agent was unsure about. Each has a note: why it is unsure, what it would do, what you should decide. Move the file to the right matter, or say "file the please-check email from <sender> in 2026-0042".
- `inbox/noise/`: proposed "nothing needed". Paste the line from the digest, like `confirm nothing needed: NOISE-0001, NOISE-0002`, or type `closed` in those CSV rows.
- Personal, misdirected or privileged emails are set aside for you as "Sensitive: for the lawyer". Nothing from their contents is recorded.

## 7. Matters, subjects, what follows what

A matter lives under its area, sub-area and subject: `areas/commercial/customers/acme-automotive/2026-0042_acme-automotive_msa-liability-cap/`. The subject folder holds `subject.md`, the running profile of that party or project. An NDA, then a framework agreement, then an SOW for the same customer are three matters under one subject, each noting which it follows.

## 8. Correcting the agent

- In a matter, write what is true in `corrections.md`. The agent must follow it.
- Each matter folder has three things: `START-HERE.md` (open this: status, next step and links to everything), `human/` (yours) and `agent/` (the agent's). Put anything of yours in `human/`; the next run picks it up and reads it. You may also change files in `agent/`; your change wins.
- Emails and documents that came in are read-only on disk, so nothing (Word adding a sensitivity label, for example) can change them. Open them to read. To work on a document, use Save As into the matter's `human/` folder.
- You do not need to write notes. Tell Claude what is not in the emails, such as a call, a meeting, a Teams chat or your thinking: "note 2026-0042: called Sam, they accept the cap at 150%". It adds a dated line to the matter's notes (`agent/notes.md`), reads them every run, and puts them in the Harvey pack. Where the emails do not settle a point, it takes the likeliest reading and lists it under "Assumed"; put it right in a word if it is wrong. It asks at most one question per run, and only when a matter cannot move without you. You can also type in that file yourself. Claude only adds lines at the end and never changes yours.
- Every run ends with a short summary per matter (five bold-titled bullets) and links to open the brief, the email to answer, the key document and the Harvey pack. Say "draft a reply to 2026-0042" for a reply to copy into Outlook.
- Confirm who is who in `roster.confirmed.md`.
- Move a misfiled email to the right matter and say so.
- Close a matter with `closed` in its CSV row, or "close 2026-0042". It writes the closing note from the file and asks nothing. If you want it to know why something went the way it did, say so in the same breath ("close 2026-0042: we gave way on the cap because they are strategic"), or say "close 2026-0042 and ask me why". "checkpoint 2026-0042" does the same at a phase end without closing. A closed matter reopens by itself if a new email arrives.

## 9. Harvey or another work tool

Every open matter has a ready Harvey pack, kept up to date after every run: the matter's `agent/<reference>_harvey-pack/` folder (the task summary and START-HERE.md link it). Drop its files into the Harvey work agent (see `harvey/work-agent/`). Save what comes back into the matter's `human/` folder, not into the pack. Legora or another tool works the same way.

## 10. Budget

The agent keeps `BUDGET.md`. Once a month, tell it the actual bill: "budget actual 37.20". Past 70 percent it reads less; past 90 percent it only files and briefs; at 100 percent it only files. "budget" shows where it stands.

## 11. What the system will never do

Send an email, close a matter, change your corrections, rename a file you received, or create an area or sub-area by itself. It writes skills and company facts without asking, but marks them "working" until you approve them, never treats a red line or an approval limit as fixed unless you said so, and never lets working content leave for another system.
