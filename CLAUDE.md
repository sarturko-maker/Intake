@RULES.md

# Claude Code notes

Read RULES.md before acting. It is the contract; this file adds only what is specific to Claude Code.

- Commands are skills: /cold-start, /intake, /status, /close, /checkpoint, /bundle, /budget, /draft-skill, /index, /interview, /guided-learning, /reply, /learn, /note. Plain phrases map to the same skills (RULES.md, Commands).
- Notes: the lawyer should not have to write anything down. Ask at most three short, optional questions per run; write each answer, and anything the lawyer tells you about a matter, into its agent/notes.md with the note skill (RULES.md, Notes and questions).
- This phase is mainly for learning (house/brief.md `mode:`, default learning): readers record what each matter teaches with `bash tools/learn-add`; `bash tools/learn-index` shows what has been learned and the next steps.
- .claude/skills/ is a mirror generated from skills/ by `bash tools/skills-sync`. Edit skills/ only, then run it.
- Subagents in .claude/agents/:
  - filer: one intake batch; matches and places each email through the tools.
  - reader: one matter; memory, brief and proposed outcome. After filing, after a deliverable or hand-placed file, or when corrections change.
  - indexer: knowledge/INDEX.md, at cold start, on /index, and for changed house/, knowledge/ or seeds/ files.
  - distiller: wrap-ups on /close, /checkpoint and `closed` typed in INDEX.csv.
  - researcher, drafter, reviewer: when the work is done here instead of a work tool: find and cite, draft, check the draft.
- Dispatch readers in parallel, one matter each; matters under one subject go one after another, since they share subject.md.
- Keep the main session lean: read changes/<run>.md and subagent reports, not the whole tree.
- Hooks and deny rules are in .claude/settings.json; TOOLING.md records whether they are live. When a hook refuses a write, read its message and comply. Never work around it.
- Write memory files (matter.md, brief.md, facts.md, roster.md, notes.md, log.md, documents.md, subject.md) with Write or Edit only, so the hooks run: a line added to log.md or notes.md is an Edit. Never through Bash in any form (redirection, tee, sed, cp, mv, or a Python script): the before-bash hook refuses it. This applies to every subagent.
- Read a memory file or a template once, with one Read, just before you change it; never print templates through Bash.
- Ask the human in plain chat text, not question widgets.
- Obey the mode in BUDGET.md.
