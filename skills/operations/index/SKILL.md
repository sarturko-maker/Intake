---
name: index
description: "Build or refresh knowledge/INDEX.md, the tree index of the documents in house/, knowledge/ and seeds/, for changed files or all files; split dropped lists into working entries; list what needs an owner or date. Use for 're-index knowledge', 're-index everything', '/index', and when intake finds documents the lawyer dropped into knowledge."
argument-hint: "[all]"
---

# Index

The indexer subagent reads and writes; you dispatch. The index covers the documents the lawyer drops into house/, knowledge/ and seeds/. Knowledge entries (a .md file with a `type:` in its frontmatter, written by the learning pass or approved by the lawyer) get their index blocks from `bash tools/learn-index`, with no model cost: never dispatch the indexer for those. Rules: RULES.md 'Knowledge'.
Only if the harness has no subagents: do the indexer's steps yourself, one folder at a time.
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`.

1. Scope. `find house knowledge seeds -type f ! -name .gitkeep ! -path knowledge/INDEX.md ! -name 'TYPES*.md' ! -path '*/history/*' -print0 | xargs -0 bash tools/hash-files`. First `bash tools/learn-index --quiet`, so the entries' blocks are current and only dropped documents are left to index. Compare each hash with that file's `<!-- sha256: -->` line in knowledge/INDEX.md: new, changed, gone. Called by intake with a file list: those files. "all", or no INDEX.md yet: every file.
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
   - type: one from knowledge/TYPES.md or knowledge/TYPES.local.md, else `other`, with the kind it seems to be in the report. origin: document, chat, matter, or seed for everything in seeds/.
   - owner and valid_from: from the file only, never guessed.
   - 'Needs an owner or date': approved entries and dropped documents lacking an owner, a source or a validity date, with what is missing. Working entries are never listed: an owner is needed only when an entry is approved for export. house/ files are the lawyer's own: never listed.
3. What the indexer found, with nobody asked:
   - Split candidates (standard-answer sets, entity lists, people lists the lawyer dropped in): dispatch the indexer again with `split <file>`. It writes one working entry per item in the type's folder, frontmatter per RULES.md 'Knowledge' (`status: working`, `origin: document`, `source: <original file> <locator>`, owner and valid_from from the original or left empty). The original stays. Then `bash tools/learn-index --quiet` indexes them.
   - Material that fits no type three times over: add a row to knowledge/TYPES.local.md (type, folder, what it holds, example), create the folder, and give the indexer `type <file> = <type>`. Say so in the digest.
   - Conflicts (a seed against a position, two policies): one open point each, `bash tools/learn-add --matter chat --question`; seeds never win.
4. Shape review (duplicate subjects, unused sub-areas, clusters that want a sub-area) is phase 2. If asked, say it is not active yet.
5. `bash tools/budget-update --measure --run <R> --note index` (the real token use from Claude Code's logs since the last measurement). It finds no logs (another harness): `bash tools/budget-update --run <R> --model <m> --in-chars <n> --out-chars <n> --note index`, once per model used (m: its BUDGET.md price key).
6. Tell the lawyer in three lines: what was indexed, what was split into entries, and any type added. Nothing waits for an answer.
