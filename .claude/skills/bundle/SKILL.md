---
name: bundle
description: "Build a work bundle of one matter for the work tool (Harvey by default; Legora or any other tool works the same way) and explain upload and return. Use for 'bundle 2026-0042 for Harvey', 'bundle 2026-0042 for Legora', '/bundle REF'."
argument-hint: "<REF> [skill-name]"
---

# Bundle

Harvey is the default work tool. Legora or any other tool works the same way: a bundle goes out of the folder, deliverables come back in. Rules: RULES.md 'Work tool'.
R = run id, house time: `TZ=<timezone in house/brief.md> date +%Y-%m-%d_%H%M%S`.

1. Folder: the `folder` of REF's row in INDEX.csv, or `find areas -type d -name '<REF>_*' -not -path '*/history/*'`. None: say so and stop.
2. Is brief.md current? A file in correspondence/ newer than brief.md, or a file with no documents.md row, means it is not: run the status skill first. In paused mode, tell the lawyer the brief may be stale.
3. `bash tools/work-bundle <REF>`: refreshes the matter's Harvey pack, agent/<REF>_harvey-pack/ (intake and status keep every open matter's pack current anyway; this forces it now). Add `--skill <name>` only when the lawyer names a skill. A dated copy to keep: add `--date <today>`.
4. Read its output: the path, the file count, warnings (more than 50 files, a file over 500 MB, no skill.md). Pass every warning on.
5. Append to log.md with your edit tool: `<time> | Harvey pack refreshed | agent/<REF>_harvey-pack/ | <R>`.
6. Tell the lawyer, in plain words:
   - Harvey (the default; Legora or any other tool works the same way): open the Harvey work agent (harvey/work-agent/) and drop the files of the pack folder in, at most 50 per upload (more files: upload in batches), each at most 500 MB. The agent takes brief.md as the task; skill.md and intake.md tell it how this team works. Without the agent: a Vault for the matter, brief.md pasted as the task.
   - Legora or another tool: upload the folder the same way and paste brief.md as the task.
   - Save what comes back into the matter's human/ folder, not into the pack folder (it is rebuilt; anything left there is moved out). Name it like `2026-11-03_memo_liability-cap_v1.md`.
   - The next "process the inbox" or "where are we" records it: a documents.md row, a log line, refreshed matter.md and brief.md.
   - The bundle holds only this matter, its subject profile, the controlling skill and the area intake file: no other subject, no history, no knowledge base. It is confidential: upload it only to the approved work tool.
7. No work tool, or the lawyer asks you to do the work (lean or minimal mode: say what it costs and go on only after their yes; paused: it waits): the researcher finds and cites, the drafter drafts, the reviewer checks the draft against the controlling skill and the documents. They work from the pack; brief.md is the task. The result goes into drafts/ as a draft for the lawyer; the next run records it. Nothing is sent. Only if the harness has no subagents: do the three steps yourself.
8. End: tell the lawyer the next step: run the work in the tool, save the deliverable into the matter's human/ folder, then say "where are we".
