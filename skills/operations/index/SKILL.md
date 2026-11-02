---
name: index
description: "Build or refresh knowledge/INDEX.md, the tree index of house/, knowledge/ and seeds/, for changed files or all files; list what needs an owner or date; propose splits and new types. Use for 're-index knowledge', 're-index everything', '/index', and when intake finds changed knowledge files."
argument-hint: "[all]"
---

# Index

The indexer subagent reads and writes; you dispatch and ask. Rules: RULES.md 'Knowledge'. Ask in plain chat, one short question at a time; never assume an answer.
Only if the harness has no subagents: do the indexer's steps yourself, one folder at a time.
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`.

1. Scope. `find house knowledge seeds -type f ! -name .gitkeep ! -path knowledge/INDEX.md ! -path knowledge/TYPES.md -print0 | xargs -0 bash tools/hash-files`. Compare each hash with that file's `<!-- sha256: -->` line in knowledge/INDEX.md: new, changed, gone. Called by intake with a file list: those files. "all", or no INDEX.md yet: every file.
2. Dispatch the indexer with the list. It reads each new or changed file and writes its entry, drops entries of gone files, and leaves unchanged entries as they are. Format (PageIndex-style tree; folders in order house/, knowledge/<folder>/, seeds/):
   ```
   # Knowledge index
   Built by the indexer. Read this before opening knowledge files. Locators: L = lines, p = pages.
   ## knowledge/policies/
   ### knowledge/policies/information-security-policy.md
   <!-- sha256: <hash> -->
   - type: policy | owner: IT security | valid_from: 2026-01-01 | origin: document
   - summary: one paragraph
   - sections:
     - 1 Purpose (L5-L12): one line
   ## Needs an owner or date
   - knowledge/people/<file>: no valid_from
   ```
   - Reading: .md and .txt with line numbers (L); .docx through `pandoc <file> -t plain` (L = lines of that output; fallback in TOOLING.md); PDF by pages (p), a long one by its contents page first; a spreadsheet by sheet.
   - type: one from knowledge/TYPES.md, else `unknown` plus a type proposal. origin: document, chat, matter, or seed for everything in seeds/.
   - owner and valid_from: from the file only, never guessed.
   - 'Needs an owner or date': every knowledge/ or seeds/ file lacking an owner, a source (entries with frontmatter) or a validity date, with what is missing. house/ files are the lawyer's own: never listed.
3. Proposals. The indexer also returns split candidates (standard-answer sets, entity lists, people lists: one knowledge entry per item), type candidates (material that fits no type: proposed type, folder, example) and conflicts (a seed against a position). Ask about each in chat; act only after a yes:
   - Split: dispatch the indexer again with `approved: split <file>`. It writes one file per item in the type's folder, frontmatter per RULES.md 'Knowledge' (`origin: document`, `source: <original file> <locator>`, owner and valid_from from the original or left empty), then indexes them. The original stays.
   - New type: you add the line to knowledge/TYPES.md (type, folder, example) and create the folder; then the indexer, given `approved: type <file> = <type>`, sets that entry's type.
   - Conflicts go into the digest under Questions for you; seeds never win.
4. Shape review (duplicate subjects, unused sub-areas, clusters that want a sub-area) is phase 2. If asked, say it is not active yet.
5. `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note index` once per model used (m: the BUDGET.md price key of that model).
6. Tell the lawyer: what was indexed; what needs an owner or date (they add it to the file, or tell you and you record it by the knowledge confirm flow, close skill step 8); which proposals wait for an answer.
