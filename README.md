# Legal intake workspace

A folder that works as an in-house legal team's intake inbox.

- You drop emails into `inbox/`. An AI assistant files each one into a matter, under its practice area and the party or project it is about.
- For every matter it keeps a short memory: a one-page summary, dated facts, who is who, a log, and your corrections.
- It keeps an index you can open in Excel, and writes a digest that ends with what you should do next.
- It learns how you work from what it reads: for each type of work it writes a skill, and it writes down company facts as it meets them. It asks you nothing; you read what it has written when you like and tell it what to change.
- You decide everything. It never sends anything.
- It is plain files, a few small helper scripts and one rules file, so you are not tied to one tool.

## What it never does

- Send an email, a reply or anything else.
- Close a matter. Only you close matters.
- Change your corrections, your confirmed list of who is who, or the house files.
- Rename or edit a file you received.
- Delete your files. The one exception is a second, identical copy of an email it has already filed.
- Follow instructions written in an email. Emails are information, nothing more.
- Treat its own notes as approved. The skills and company facts it writes are marked "working" until you say "approve"; a red line or an approval limit is fixed only when you say so; nothing working leaves for another system.
- Add an area or a sub-area without your yes.

## Quick start

Follow [COLD-START-HUMAN.md](COLD-START-HUMAN.md). It is one page and takes about half an hour:

1. Copy the workspace files into the folder you will work in.
2. Fill in `house/brief.md` and `house/areas.md`.
3. Drop company facts into `knowledge/`.
4. Open the folder in your assistant and say "cold start".
5. Drop emails into `inbox/` and say "process the inbox".

## Try the demo

[demo/README.md](demo/README.md) runs the whole flow on three batches of emails. The demo is invented: the company, its people, its customers and every email.

## How it is organised

| Folder or file | What it holds | Who writes it |
|---|---|---|
| `inbox/` | Emails you drop in; noise and please-check piles | You drop; the assistant sorts |
| `areas/` | Matters, by area, sub-area and subject | The assistant |
| `house/` | Your organisation and your practice areas | You (Claude only with your yes); never in git |
| `knowledge/` | Company facts: policies, companies, people, standard answers, templates, positions | You add files; the assistant indexes them and writes working entries from what it reads |
| `seeds/` | Starting material, such as an extraction from old emails | You |
| `skills/` | How the assistant works, and one legal skill per type of work | The assistant writes them from your matters; you correct and approve |
| `learning/` | What it has learned: start at `learning/index.md` | The assistant |
| `digests/` | What came in and what to do next | The assistant |
| `INDEX.csv`, `INDEX.md` | Every matter and its status | The assistant; you fill in four columns |
| `RULES.md` | The rules every assistant follows | Part of the workspace |
| `tools/` | Small helper scripts the assistant runs | Part of the workspace |
| `demo/` | The invented demo | Part of the workspace |
| `phase-2/` | What comes next; not active | Part of the workspace |
| `copilot-studio/` | The specification for building intake on Copilot Studio; the workspace is its lab | Part of the workspace |

## Three phases

1. **Working intake.** Built. Filing, matter memory, index and digest, budget, work bundle, the commands, the knowledge base, skills that write themselves from your matters, and a short wrap-up when a matter closes.
2. **Learning and visibility.** A dashboard, proposals to improve the skills from closed matters, and a monthly review. See [phase-2/README.md](phase-2/README.md).
3. **Connections.** A direct Outlook connection instead of drag and drop, sending bundles to the work tool automatically, and a second user. Decided after phase 2.

## Works with

- **Assistants:** Claude Code, Claude Cowork, Copilot or OpenCode. Any assistant that can read files and run a shell can follow `RULES.md`. On Windows, install Git for Windows so the helpers can run in Git Bash.
- **Work tools:** Harvey by default. Legora or another tool works the same way: a bundle goes out of the folder and the results come back in. No work tool at all is fine too; the assistant then does the work from the same files.

## Safety

- Never commit real emails or client documents to git. The `.gitignore` keeps live data out of the repository, but check before you commit.
- At work, keep this repository (the folder with `.git`) outside the folder that syncs to OneDrive or SharePoint. Create the live workspace by copying the repository files into the synced folder, without the `.git` folder.
- `knowledge/standard-answers/` is the most sensitive folder. Set its permissions so only the right people can open it.

## Provenance

- The matter memory and the intake rules take their shape from [lq-ai-fork](https://github.com/sarturko-maker/lq-ai-fork) (Apache-2.0): its matter-memory and intake-triage skills, its commercial doctrine and its design records. Only the shape and the memory rules were borrowed. No legal content was copied as a house position. [skills/POINTERS.md](skills/POINTERS.md) lists what is useful there.
- The knowledge index follows the tree index idea of PageIndex. The package is not used.
- Memory kept as plain Markdown pages with an index and a log follows Karpathy's "LLM Wiki" pattern. Only the convention is used.

## Status

Phase 1 is built. See [HANDOFF.md](HANDOFF.md) for the current state and the next steps.
