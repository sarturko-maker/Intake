# Tools

CLI reference for the helpers in `tools/`. Agent-facing. RULES.md (Tools) says when to run each one; this file gives the flags, what each reads and writes, exit codes and fallbacks.

## Conventions

- Run from the workspace root: `bash tools/<name> ...`. Works on Linux, macOS and Windows Git Bash.
- Each tool is a bash file (no extension, executable, LF). Where Python is needed it runs `tools/lib/<name_with_underscores>.py`: Python 3.8+, standard library only (optional imports: `oxmsg` in msg2eml, `docx` as a fallback reader). `tools/lib/find-python.sh` picks `python3`, `python` or `py -3`.
- `-h` / `--help`: the usage block at the top of the file, ending with the fallback.
- Exit codes: `0` ok, `1` findings or check failed, `2` usage error, `3` dependency missing (fallback printed).
- Workspace root: `INTAKE_ROOT` if set (tests), else the folder above `tools/`.
- Output: short plain lines. JSON only with `--json`.
- Paths workspace-relative with forward slashes. Dates `YYYY-MM-DD`; date-times `YYYY-MM-DD HH:MM`, house time; RUN `YYYY-MM-DD_HHMMSS`, house time. Pass `--run RUN` to every tool in a run: every tool accepts it (the read-only ones ignore it).
- Windows long paths: files are opened with the `\\?\` prefix when a path is long (common.os_path), so they can be read even where Windows long paths are off; place-email stores an attachment whose path would pass 240 characters under a shortened name (`<start>~<6 characters><ext>`, the original name first in its documents.md summary). `INTAKE_MAX_PATH` overrides the limit (tests).
- A tool fails or is missing: use its fallback, say so in the digest, log `workaround` or `tool-failure` in WORKFLOW-LOG.md.

| Tool | Does | Runs on | Fallback |
|---|---|---|---|
| tooling-setup | detect, install, verify, TOOLING.md | bash | check by hand, write TOOLING.md |
| scan-changes | tree against MANIFEST.csv | Python | find -newer, hash-files, report by hand |
| unpack-email | parse .eml, filing signals | Python | read the .eml; munpack or ripmime |
| place-email | rename, move, extract, record | Python | the same steps by hand |
| new-matter | reference and matter skeleton | Python | next reference by hand, copy templates |
| msg2eml | .msg to .eml | Python, msgconvert | msg2eml.ps1; ask for .eml |
| hash-files | sha256 of files | bash | certutil; log not hashed |
| history-copy | dated copy into history/ | bash | cp by hand |
| lint-facts | check facts.md; live and as-of views | Python | by eye |
| lint-received | re-hash received files | Python | hash-files, compare |
| index-rebuild | INDEX.csv, INDEX.md, digest parts | Python | rows by hand |
| budget-update | BUDGET.md ledger and mode | Python | edit BUDGET.md by hand |
| skills-sync | mirror skills/ to .claude/skills/ | bash | copy folders |
| work-bundle | work tool bundle | bash (+ Python or awk) | copy the list by hand |
| matter-sync | register new and changed files in matters, find the lawyer's edits, START-HERE.md | Python | open the folders by hand |
| matter-migrate | old one-folder matters to agent/ + human/ | Python | move the files by hand |
| learn-add, learn-index | learning lines; learning/index.md and next steps | Python | append and count by hand |
| init-workspace | blank house files from templates/house/ | bash | copy by hand |
| area-lines | matching lines of an area's playbook.md, intake.md, a subject.md, with headings | Python | grep -n -i -A2 |
| redline-changes | tracked changes and comments of a .docx, with clause numbers | Python | pandoc --track-changes=all |

## tooling-setup

`bash tools/tooling-setup [--install] [--yes] [--verify-only]` (pure bash)

- Detects: bash; a SHA-256 tool (sha256sum, `shasum -a 256`, `openssl dgst -sha256`, Python hashlib, PowerShell Get-FileHash); python3 (`py -3`, `python`); python-oxmsg, python-docx; msgconvert, pandoc, munpack, ripmime, git; pip, brew, apt-get (root, or sudo without a password), winget, npm; PowerShell; Outlook desktop (Windows); hooks (`PreToolUse`, `PostToolUse`) and deny rules (corrections.md, roster.confirmed.md, house/) in `.claude/settings.json`.
- No option: writes TOOLING.md, prints missing items, the exact install commands, then `Ask the human once: May I install: X, Y (using pip/apt)?` and `If yes: run bash tools/tooling-setup --install`.
- `--install`: `python3 -m pip install --user python-oxmsg` (again with `--break-system-packages` on an externally-managed error); `[sudo] apt-get install -y libemail-outlook-message-perl pandoc mpack` (`apt-get update` once on "Unable to locate package"); `brew install pandoc mpack`; `winget install --id JohnMacFarlane.Pandoc -e`. Only missing items. A failure is `blocked`, with its fallback. On a terminal it asks once unless `--yes`.
- `--yes`: with `--install` only: no terminal prompt; winget agreements accepted.
- `--verify-only`: detect and verify, write TOOLING.md, no install advice.
- `TOOLING_DRY_RUN=1` (environment): print the install commands instead of running them; TOOLING.md notes `dry run: would run: ...`.
- Verifies on `tools/fixtures/` (values from `EXPECTED.txt`): sha256 of `sample.eml`; `bash tools/unpack-email tools/fixtures/sample.eml` reports its Message-ID; `bash tools/msg2eml tools/fixtures/sample.msg --outdir <tmp>` gives an .eml with the expected Message-ID; `pandoc --track-changes=all tools/fixtures/sample.docx -t plain` shows the inserted text; munpack or ripmime extracts the attachment. A missing fixture: `not verified: fixture missing`.
- Reads: `.claude/settings.json`, `house/brief.md` (timezone), `tools/fixtures/`. Writes: `TOOLING.md`.
- TOOLING.md: header (date, OS, package managers, PowerShell), then `item | status | version | fallback in use | note` for shell, sha256, python3, msg converter, pandoc, munpack/ripmime, python-docx, git, hooks, deny rules. Status: found, installed, missing, blocked, configured, verified. hooks and deny rules: `configured | - | - | prove at cold start (RULES.md obligations if the harness ignores them)`.
- Exit: 0 done (missing items are recorded, not errors); 1 a present tool failed verification; 2 usage error.
- Fallback: `command -v NAME`, `NAME --version` for each item; write TOOLING.md in the same line format by hand.

## scan-changes

`bash tools/scan-changes [--run RUN] [--write-manifest] [--json] [--quiet]`

- Compares the tree with MANIFEST.csv by size and mtime; hashes candidates only. Kinds: new, modified (hash differs), touched (mtime only), deleted, moved (a deleted path's hash at a new path). No manifest: everything is new.
- Skips `.git/ .claude/ tools/ demo/ phase-2/ .github/ changes/ digests/`, every `history/`, `**/work-product/bundle-*/`, MANIFEST.csv, JOURNAL.md, INDEX.md, WORKFLOW-LOG.md, TOOLING.md, BUDGET.md, HANDOFF.md, OS junk (`.DS_Store Thumbs.db desktop.ini ~$* *.tmp .~lock*`). INDEX.csv is scanned (the lawyer edits it).
- Report `changes/<RUN>.md`: counts in the header; sections by matter folder, else first path part (inbox, knowledge, house, seeds, skills, areas), else root; lines `- new: <path> (<size>)`, `- moved: <old> -> <new>`.
- `--write-manifest`: rewrite MANIFEST.csv (`path,size,mtime,sha256,first_seen,last_seen,last_processed`, mtime integer seconds): first_seen kept, last_seen = RUN, last_processed = RUN for every file not directly in `inbox/`. Also empties `changes/agent-writes.csv` (the after-write hook's record of the agent's own writes; the manifest now holds them).
- `--quiet`: only the report path. `--json`: counts and changes.
- Reads: the tree, MANIFEST.csv. Writes: `changes/<RUN>.md`; MANIFEST.csv with `--write-manifest`.
- Exit: 0, 2 usage, 3 Python missing.
- Fallback: `find . -newer MANIFEST.csv -type f`, hash with hash-files, write `changes/<run>.md` by hand.

## unpack-email

`bash tools/unpack-email [--json] [--body-chars N] [--extract DIR] [--no-signals] [--with-quoted [--quoted-inline] | --no-quoted] FILE...`

- `.eml` only; a `.msg` exits 2: `convert first: bash tools/msg2eml FILE`.
- Per file (full list in `--help`): file, canonical_name (`YYYY-MM-DD_HHMM_<in|out>_<from-slug>_<subject-slug>.eml`, house time, subject slug max 40 without the tag), direction (`out` when From is in legal_addresses or is intake_mailbox), internal (From domain in house_domains), personal_address (free-mail domain), date, from {name, address}, to, cc, subject, message_id, in_reply_to, references (no angle brackets), tags (subject and new body first, else full body), noise_hints (auto-reply, bulk, calendar, empty-body, logo-only), body (new text only, quoted history stripped, default 4000 characters then `[... N more characters]`), body_chars_total, attachments {name, content_type, size, sha256, kind, inline}; kind document, image, signature-image, calendar, email.
- Quoted history (`--with-quoted`): the oldest quoted message, where the request usually is, as `quoted`; every quoted message, without disclaimers, written once to `changes/quoted/<canonical stem>.txt` (`quoted_file`, `quoted_messages`, `quoted_chars_total`). Read that file once, only when the oldest message does not give the request. `--quoted-inline` prints the whole history instead. `--no-quoted` skips it (no quoted_first_date): the fast pass for putting a batch in order.
- signals (not with `--no-signals`): thread_matches (matters whose documents.md holds an In-Reply-To/References id, with status), tag_matches (folder, status, sender_check: internal, roster-address, roster-name-freemail, roster-name-other-domain, not-on-roster).
- Reads: the .eml files, house/brief.md, matters' documents.md, roster.md, roster.confirmed.md. Writes: nothing, except attachments with `--extract DIR`.
- Exit: 0, 2 usage (also a .msg), 3 Python missing.
- Fallback: read the .eml as text (headers on top); save attachments with munpack or ripmime; hash with hash-files.

## place-email

`bash tools/place-email FILE --to <MATTER_FOLDER|REF|noise|please-check> [--run RUN] [--reason TEXT] [--confidence 0-1] [--note TEXT] [--title TEXT] [--label TEXT] [--claimed REF] [--candidates "REF,REF"] [--cross-ref MATTER_FOLDER] [--json]`
`bash tools/place-email --register PATH_INSIDE_MATTER [--run RUN] [--json]`

- Into a matter: FILE to `<matter>/correspondence/<canonical_name>` (different content with the same name: `-2`, `-3`); a same-stem `.msg` moves with it as `<canonical-stem>.msg`; attachments of kind document, image, email to `documents/received/` (`documents/ours/` when direction is out), names kept (`<stem>-2<ext>` for a different file with the same name); a sha256 already in the matter's documents.md is not stored again (row `duplicate_of=<earlier name>`); a sha256 already read (`read=yes`, with a summary) in another matter of the same subject folder, except general/unfiled, is stored but not read again: its row gets `read=no: read in <REF> <path>, same file` and that summary, and its card (`agent/summaries/<name>.md`) is copied, headed "Copied from <REF>"; signature images and calendar parts are not stored (`read=no: signature image`, `read=no: calendar part`). documents.md rows for the email and each attachment (`read=pending`), a log.md line, a JOURNAL.md `filed` line (reason, confidence). `--cross-ref F`: a line in F's log.md and the journal.
- A name that would make the stored path too long for Windows (over 240 characters) is shortened to `<start>~<6 characters><ext>`; its documents.md summary starts `original name: <name>`, and a warning names any path still too long (move the workspace to a shorter folder). `--register` opens long paths with the Windows long-path prefix.
- Identical email already in the matter: the inbox copy is deleted, journal `duplicate-dropped`. The only deletion any tool makes.
- `noise`: to `inbox/noise/<canonical_name>`; next `NOISE-NNNN` row in inbox/noise/NOISE.csv (status waiting_lawyer, proposed nothing_needed, `--title` default the subject, `--label`); journal `noise`; attachments not extracted.
- `please-check`: to `inbox/please-check/<canonical_name>` plus `<canonical_name>.note.md` (frontmatter file, received, from, subject, claimed_reference, candidates, run; body from `--note`); journal `please-check`. Re-filing from please-check resolves the note into `resolved/`.
- `--register`: documents.md rows (and an email's attachments) for a file a human put into a matter; the file is not moved.
- Refuses (exit 2, nothing changed): FILE not under `inbox/` (or `inbox/please-check/` for re-filing); a matter folder without matter.md.
- Reads: FILE, house/brief.md, the matter's documents.md (and, for an attachment, the documents.md of the other matters in the same subject folder), NOISE.csv. Writes: the moved files, documents.md, log.md, JOURNAL.md, NOISE.csv, please-check notes.
- Exit: 0, 1 a move or write failed part-way, 2 usage or refusal, 3 Python missing.
- Fallback: move and rename by hand (unpack-email rules), save attachments, hash them, append the documents.md, log.md and JOURNAL.md lines yourself.

## new-matter

`bash tools/new-matter --area A [--sub-area S] --subject SUBJ --topic TOPIC [--subject-name "Display Name"] [--title TEXT] [--follows REF] [--opened YYYY-MM-DD] [--run RUN]`
`bash tools/new-matter --next-ref [--year YYYY]`

- Area must be in house/areas.md (`general` always allowed). An undeclared `--sub-area` exits 2: "sub-area '<S>' is not declared for <A>. File under areas/<A>/<subject>/ and propose the sub-area in the digest." No `--sub-area`: the matter sits under the area.
- Slugs `[a-z0-9-]+`; folder name at most 70 characters (topic shortened). Reference from the opened date's year: highest in INDEX.csv and folder names, plus one.
- Creates the subject folder and subject.md if missing; the matter folder, its subfolders and the eight memory files from `skills/operations/matter-memory/templates/`; log.md `opened matter`; journal `new-matter`. Prints `REF<TAB>FOLDER`. `--next-ref` prints the next reference only.
- Reads: house/areas.md, house/brief.md (prefix, timezone), INDEX.csv, folder names, templates. Writes: the new folders and files, log.md, JOURNAL.md.
- Exit: 0, 1 could not write, 2 usage (unknown area, undeclared sub-area, bad slug), 3 Python missing.
- Fallback: next reference by hand, create the folders, copy the templates and fill the `{{...}}` fields.

## msg2eml

`bash tools/msg2eml FILE.msg... [--outdir DIR]`

- Writes `<stem>.eml` beside each .msg (or in DIR); keeps the .msg. Methods in order: python-oxmsg (headers from PR_TRANSPORT_MESSAGE_HEADERS, else rebuilt from properties), then msgconvert (Perl Email::Outlook::Message).
- Neither works: prints how to use `tools/msg2eml.ps1` (Windows with Outlook desktop) or to ask the human to save as .eml from new or web Outlook; exit 3. The caller writes the JOURNAL `converted` line.
- Text in a .msg labelled UTF-8 that holds Windows-1252 bytes (curly quotes, dashes, the euro sign) is read as Windows-1252; the body is never dropped for it.
- `--refresh [MATTER_FOLDER|REF ...] [--run RUN]`: filed emails whose body an older version lost (empty body, .msg original with text beside it) are re-converted; the old .eml goes to `agent/history/<stem>.empty-body.eml`, documents.md gets the new sha256 and `read: pending`, log.md a line.
- Reads: the .msg files. Writes: the .eml files.
- Exit: 0, 1 a --refresh conversion failed, 2 usage, 3 no converter or Python missing.
- Fallback: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\msg2eml.ps1 -Path FILE.msg` on Windows with Outlook desktop (untested in the build container); else ask for .eml.

## hash-files

`bash tools/hash-files FILE...` (pure bash)

- Prints `<sha256>  <path>` per file, path as given. Methods in order: sha256sum, `shasum -a 256`, `openssl dgst -sha256`, Python hashlib, PowerShell Get-FileHash (`HASH_FILES_METHOD` forces one). A missing file prints `no file: <path>` on stderr; the others are still hashed.
- Writes nothing. Exit: 0, 1 a file missing or unreadable, 2 usage, 3 no SHA-256 method.
- Fallback: `certutil -hashfile FILE SHA256` on Windows; else log the file as not hashed.

## history-copy

`bash tools/history-copy FILE...` (pure bash)

- Copies each existing file to `<dir>/history/<stem>.<YYYY-MM-DD_HHMMSS>.md` (`-2`, `-3` on a clash; same naming as `common.history_copy`). Prints each copy's path. A missing file prints `no file: <path>` and exits 0.
- Windows (Git Bash, MSYS, Cygwin): `C:\x\y` paths work as well as `/c/x/y`; the copy's path is printed in the style given. `INTAKE_WINPATHS=1` makes any shell treat backslashes this way (tests).
- Writes: `history/` copies. Exit: 0, 1 a copy failed, 2 usage.
- Fallback: copy by hand to `history/<stem>.<YYYY-MM-DD_HHMMSS>.md`.

## lint-facts

`bash tools/lint-facts FILE [--previous OLDFILE] [--live] [--as-of YYYY-MM-DD]`

- Checks every record of facts.md: 7 fields (`id | recorded | type | valid_from= | source= | supersedes= | text`); id `F` plus 4 or more digits, unique, ascending; type party, term, date, decision, open_point, fact; recorded and valid_from are dates (`valid_from=` may be empty); `source=` non-empty; text non-empty; every `supersedes=` target (comma-separated allowed) exists and comes earlier.
- `--previous OLDFILE`: OLDFILE's records appear unchanged and in order as a prefix of FILE's records (append-only). A missing OLDFILE skips this check with a note on stderr.
- `--live`: only live records (no later line supersedes them). `--as-of D`: records held on D (recorded on or before D) and in force on D (valid_from, or recorded when empty, on or before D), not superseded by such a record: what we believed at D.
- Output: one line per error, `FILE:LINE: ID: message`, on stdout; clean: `ok: FILE: N records, M live`. With a view, the record lines go to stdout and errors to stderr.
- Called by the PostToolUse hook after each write to facts.md (exit 1: the hook restores the file). Reads FILE (and OLDFILE). Writes nothing.
- Exit: 0 clean, 1 errors, 2 usage, 3 Python missing.
- Fallback: check by eye: 7 fields, ids unique and ascending, supersedes targets earlier, no earlier line changed or removed.

## lint-received

`bash tools/lint-received [MATTER_FOLDER|REF ...]` (default: every matter)

- For every documents.md row whose folder is `correspondence` or `documents/received`: recompute sha256 and compare. Lines: `changed: <path>`, `missing: <path>`, `no hash: <path>`, `no row: <path>` (file in those folders without a row). Rows with `duplicate_of`, `read=no: signature image` or `read=no: calendar part` have no stored file by design; a `.msg` beside its `.eml` needs no row of its own. OS junk ignored.
- Summary: `lint-received: N files checked in M matters, K findings`.
- Reads: documents.md and the files. Writes nothing. Never repair: list findings under Please check.
- `--accept FILE... [--reason TEXT] [--run RUN]`: only after the lawyer confirms the change is not to the content (typically Word saving a sensitivity label into an opened file): records the new sha256 in documents.md, logs the old one in log.md, makes the file read-only. The file is not changed.
- Exit: 0 clean, 1 findings, 2 usage (not a matter folder, unknown reference), 3 Python missing.
- Fallback: hash-files on each file, compare with the hash column by eye.

## index-rebuild

`bash tools/index-rebuild [--today YYYY-MM-DD] [--run RUN] [--digest-parts FILE] [--no-apply] [--confirm-noise IDS] [--json]`

1. Human edits: INDEX.csv against `changes/INDEX.generated.csv`, cell by cell, rows matched by reference. Excel saves are tolerated: BOM or not, UTF-8 or cp1252, `,` or `;`, dates and decimals reformatted.
   - Human columns (confirmed_outcome, confirmed_by, lawyer_minutes, accepted_unchanged) of a matter row go into matter.md frontmatter (history copy first); outcomes and yes/no normalised.
   - `closed` typed in status of an open matter: `status: closed`, `closed: <today>`, flag `wrap-up-pending`; prints `closed-by-lawyer REF: run the wrap-up`; journal `closed-by-lawyer`, log.md line.
   - title edited: title set, `title_locked: yes`.
   - Noise row with status `closed` or a confirmed_outcome: file to `inbox/noise/confirmed/`, NOISE.csv row closed (confirmed_outcome default nothing_needed, confirmed_by default `you`), BOM and line endings kept.
   - Any other edited cell: ignored, `warning: REF: column X is kept by the agent; say it in chat instead`. Deleted or added rows: warning.
   - No generated copy (first run): no edits detected; an existing INDEX.csv is kept as `changes/INDEX.before-<RUN>.csv`.
   - Applied edits: JOURNAL.md `human-edit-applied` lines.
2. `--confirm-noise IDS`: the chat line `confirm nothing needed: NOISE-0001, NOISE-0002` (the ids are picked out of the text): the same as typing closed in those rows.
3. Rows: every matter.md under areas/ (outside history/ and work-product/) and every NOISE.csv row. days_open = (closed date, or last_activity when closed without one, or today) - opened. hours_to_ready = ready_at - arrived, 0.1 hours, empty if either is missing. folder = workspace path. Noise: kind noise, proposed nothing_needed, opened and last_activity = received date, waiting_on `you` and next_step `Confirm as nothing needed` while open, folder = file path.
4. Sort: open matters by due ascending (blank last), then days_open descending; closed by last_activity descending; noise, open first.
5. Writes: INDEX.csv (columns as INDEX.sample.csv, UTF-8 BOM, CRLF); locked (Excel): `INDEX.new.csv` and a warning, and the generated copy is left as it was so edits are still found next time. `changes/INDEX.generated.csv`: byte copy of INDEX.csv. `INDEX.md`: open matters by area (house/areas.md order), oldest first; noise awaiting confirmation with the paste line; closed in the last 30 days; the four measures.
6. Measures: lawyer minutes per matter (mean over closed matters with a value); share of deliverables accepted unchanged (yes / (yes + no)); agreement between proposed and confirmed outcome (rows with a confirmed outcome); hours from arrival to ready (median). `n/a` without data.
7. `--digest-parts FILE`: `## Nothing needed (confirm)` (open noise, the line `confirm nothing needed: NOISE-...`, and matters proposing nothing_needed), `## Please check` (each `inbox/please-check/*.note.md` with a one-line reason), `## Quiet for ten days or more`, `## Measures`, `## What you should do next` (numbered: due soonest, waiting on you oldest first, confirmations, please-check, stale; one line each: reference, title, next step).
8. Integrity: duplicate references, missing reference, area, subject, title, status or opened, folder name not starting with its reference. Lines `integrity: ...`; the index is still written.

- `--no-apply`: report detected edits (`would ...`) and write nothing: no INDEX.csv, INDEX.md, matter.md or NOISE.csv change (`--digest-parts` is still written).
- `--today`: date for days, closing, quiet and recent lists (default today, house time). `--json`: the report as JSON (applied, closed_by_lawyer, noise_confirmed, warnings, integrity, counts, measures).
- Reads: matter.md files, NOISE.csv, INDEX.csv, `changes/INDEX.generated.csv`, please-check notes, house/areas.md. Writes: INDEX.csv, `changes/INDEX.generated.csv`, INDEX.md, the digest parts file, matter.md frontmatter, log.md, NOISE.csv, `inbox/noise/confirmed/`, JOURNAL.md.
- Exit: 0, 1 integrity problems, 2 usage, 3 Python missing.
- Fallback: copy the lawyer's edits into matter.md first, then write INDEX.csv by hand from the frontmatter and NOISE.csv; copy it to `changes/INDEX.generated.csv`.

## budget-update

`bash tools/budget-update --init [--month YYYY-MM]`
`bash tools/budget-update --run RUN --model opus|sonnet|haiku --in-chars N --out-chars M [--note T]`
`bash tools/budget-update --measure [--run RUN] [--note T] [--transcripts DIR]`
`bash tools/budget-update --actual USD [--date YYYY-MM-DD] [--month YYYY-MM]`
`bash tools/budget-update --show` | `--mode`

- `--measure` (Claude Code): reads the real token use since `measured_until` from Claude Code's own session and subagent logs on this computer (`$CLAUDE_CONFIG_DIR` or `~/.claude`, `projects/<workspace path, non-alphanumerics as ->/`), each response once, and prices it: fresh input and output at list prices, cache writes at 1.25x (5-minute) or 2x (1-hour) the input price, cache reads at their own price (prices line `family=in/out/cache read`), fast mode at 2x. One ledger line per model, note `measured: ...` with its split by step; stdout also lists each step (main session, and each subagent type from the `agent-<id>.meta.json` beside its log, with how many ran) and its cost by model. The first measurement counts from the start of the month and sets that month's estimated lines to 0 (kept, marked). Only numbers are read; nothing leaves the machine. No logs found: exit 1.

- `--init`: create BUDGET.md if absent (cap 100, overhead_factor 1.25, thresholds `lean=70 minimal=90 paused=100`, prices `opus=4/20 sonnet=2/10 haiku=0.10/0.50` USD per million tokens as of 2026-10-06, with a note to check them).
- `--run`: one ledger line per model per run, `run | date | model | in_chars | out_chars | est_usd | note`; est_usd = `(in_chars/4 * price_in + out_chars/4 * price_out) / 1e6 * overhead_factor`, prices and factor from BUDGET.md; the model must have a price there. Recomputes estimated_spend_usd, percent_of_cap, mode; prints `mode changed: X -> Y` when it moves. Creates BUDGET.md if absent.
- Modes by percent of cap: full below lean; lean from lean; minimal from minimal; paused from paused.
- `--actual USD`: `overhead_factor = old * actual / estimated`, limited to 1.0-5.0; sets last_actual_usd and last_actual_date. Billed month: `--month`; else BUDGET.md's month if it has ended; else last month if `digests/budget-<last month>.md` has no actual yet (recorded there); else this month (spend to date).
- `--show`: summary and this month's ledger. `--mode`: the mode word only; a month that has ended counts as reset (full); no BUDGET.md prints `full`.
- On any write, a BUDGET.md month that is not the current month moves its ledger to `digests/budget-<month>.md` and the estimate resets.
- `--today D`: stand-in for today (tests, catching up).
- Reads and writes: BUDGET.md, `digests/budget-<month>.md`. Human lines in BUDGET.md's header are kept.
- Exit: 0, 1 no BUDGET.md for `--show` or no estimate for the named month, 2 usage, 3 Python missing.
- Fallback: append the ledger line by hand, add up est_usd, set percent_of_cap and mode from the thresholds.

## skills-sync

`bash tools/skills-sync [--check]` (pure bash)

- Mirrors every `skills/<group>/<name>/` holding SKILL.md (group: operations or an area key; other groups mirrored with a warning) to `.claude/skills/<name>/`, replacing it whole; removes mirror folders with no canonical skill; writes `.claude/skills/.generated`: "Generated by tools/skills-sync from skills/. Do not edit."
- `--check`: compare only, write nothing; lines `missing:`, `differs:`, `extra:`, `marker:`; exit 1 on any difference (slice 4 check).
- Name clash between groups: nothing written, exit 2.
- Reads: skills/, house/areas.md. Writes: `.claude/skills/`.
- Exit: 0, 1 differences (`--check`) or no skills/, 2 usage or name clash.
- Fallback: copy each skill folder to `.claude/skills/<name>/` by hand, delete stale mirror folders, write the marker.

## work-bundle

`bash tools/work-bundle <REF|MATTER_FOLDER> [--date YYYY-MM-DD] [--skill NAME]` (bash; Python only for the live facts view, awk without Python)

- Creates `<matter>/work-product/bundle-<date>/` (`-2`, `-3` for another bundle that day) holding exactly: brief.md, matter.md, facts-live.md (`bash tools/lint-facts facts.md --live`, fence and header first), subject.md, roster.md, roster.confirmed.md, corrections.md, correspondence/, documents/received/, documents/ours/, skill.md (SKILL.md of `controlling_skill` in matter.md, or `--skill`; looked up in the area's group, then operations, then any group), intake.md (`areas/<area>/intake.md`).
- Never other subjects, history/, drafts/, documents/reference/, the knowledge base or OS junk. A missing piece is left out with a warning; an unknown `--skill` is a usage error and nothing is written.
- Prints the path, `Files: N` and the upload notes: Harvey (Legora or another tool works the same way): a Vault, at most 50 files per upload, 500 MB per file; paste brief.md as the task; deliverables back into `<matter>/work-product/`. Warns over 50 files (number of uploads) and for any file over 500 MB.
- The change scan skips bundle folders. Reads: the matter, its subject.md, the skill, the area intake.md, house/brief.md (timezone). Writes: the bundle folder.
- Exit: 0, 2 usage (no or unknown matter, bad date, unknown skill, two folders with one reference).
- Fallback: create the folder by hand and copy the list; facts-live.md = the facts.md lines no later line supersedes.

## area-lines

`bash tools/area-lines AREA PATTERN [--subject SLUG] [--after N]`

- Prints the lines of `areas/AREA/playbook.md` and `areas/AREA/intake.md` (and, with `--subject`, that subject's subject.md) that match PATTERN (a regular expression, case-insensitive), each as `<line> [<heading > subheading>] <text>`, followed by up to N more lines of the same paragraph (default 2). A file with no match prints its headings, so a better pattern can be chosen.
- For one point (a signatory, a letter of authority, an approval limit) instead of reading the whole playbook.
- Reads only. Exit: 0 a match, 1 no match, 2 usage (unknown area or subject, bad pattern), 3 Python missing.
- Fallback: `grep -n -i -A2 -E "PATTERN" areas/AREA/playbook.md areas/AREA/intake.md`.

## redline-changes

`bash tools/redline-changes FILE.docx [--clause N] [--summary] [--no-context]`

- Prints only the tracked changes (inserted, deleted, moved away, moved here) and comments of a Word mark-up, one per line: `<where> | <kind> | <author> | <date> | "<text>"`, a comment followed by `on "<the text it is anchored to>"`; under each changed paragraph `reads: "..."`, the paragraph with `[-deleted-]` and `{+inserted+}` text (long unchanged stretches shortened). Last line: the count by author; formatting changes are counted, not listed.
- Where: `clause 12.2`, `clause 12.2(a)` from Word's automatic numbering (numbering.xml and heading styles) or a number typed at the start of the paragraph; an unnumbered paragraph takes the clause above it; `schedule 2 para 1.1` after a schedule or annex heading; `para N` before the first number; `footnote`, `header`, `footer`.
- `--clause N`: only clause N and its sub-clauses (12 gives 12, 12.1, 12.2(a); not 2 or 112); also `--clause "schedule 2"`. `--summary`: one line per changed clause with the kinds of change and who made them, a first look at a heavy mark-up. `--no-context`: no `reads:` lines.
- Reads only; standard library (zip and XML). Exit: 0 (also when there are no changes), 2 not a readable .docx (a .doc or PDF: pandoc, or ask for the .docx), 3 Python missing.
- Fallback: `pandoc --track-changes=all FILE.docx -t plain`.

## Tests

`bash tools/tests/run-tests [-v]`

- Runs `python3 -m unittest discover -s tools/tests -p 'test_*.py'` (python or `py -3` when python3 is missing), then `bash tools/tests/test_shell.sh`. Exit 1 if either fails or Python is missing.
- Unit tests build temporary workspaces (copy of tools/, skills/, house files; `INTAKE_ROOT`); the real workspace is not touched. Shared fixture: `tools/tests/wsfixture.py`.
- `test_shell.sh`: every wrapper's `--help` (exit 0, mentions Usage and Fallback), executable bit, LF only, a FALLBACK= line; hash-files output format; history-copy naming; skills-sync `--check`, also on this workspace once its mirror exists.
