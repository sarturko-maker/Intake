@RULES.md

# Claude Code notes

Read RULES.md before acting. It is the contract; this file adds only what is specific to Claude Code.

- Commands are skills: /cold-start, /intake, /status, /close, /checkpoint, /bundle, /budget, /draft-skill, /index, /interview, /guided-learning, /reply, /learn, /note. Plain phrases map to the same skills (RULES.md, Commands).
- Ask almost nothing (RULES.md, Notes and questions): where the files do not settle a point, take the likeliest reading and say what you assumed. At most one question per run, only when a matter cannot move without it; never a question about learning (no "shall I add this fact", "who owns it", "why", "approve?"). Anything the lawyer tells you about a matter goes into its agent/notes.md (note skill).
- Skills and knowledge write themselves (RULES.md, Wrap-up and learning): readers record what each matter teaches with `bash tools/learn-add`; `bash tools/learn-index` says what is due; the learner writes the working skills and knowledge entries at the end of an intake run. Nothing waits for the lawyer, who reads learning/index.md when they like.
- When the lawyer says how the team works, states a company fact, or corrects a skill or an entry ("in the NDA skill, ...", "that is wrong: ..."): record it as the lawyer's and apply it at once (learn skill, 'What the lawyer tells you'). Never ask them to confirm what they have just said.
- .claude/skills/ is a mirror generated from skills/ by `bash tools/skills-sync`. Edit skills/ only, then run it.
- Subagents in .claude/agents/:
  - filer: one intake batch; matches and places each email through the tools.
  - reader: one matter; memory, brief and proposed outcome. After filing, after a deliverable or hand-placed file, or when corrections change.
  - indexer: knowledge/INDEX.md, at cold start, on /index, and for changed house/, knowledge/ or seeds/ files.
  - distiller: wrap-ups on /close, /checkpoint and `closed` typed in INDEX.csv. It asks nothing.
  - learner: the learning pass. It writes the working skill of a type of work and the knowledge entries, from the learning register; three types of work to a learner, in parallel.
  - researcher, drafter, reviewer: when the work is done here instead of a work tool: find and cite, draft, check the draft.
- Dispatch readers in parallel, one matter each; matters under one subject go one after another, since they share subject.md.
- Keep the main session lean: read changes/<run>.md and subagent reports, not the whole tree.
- Hooks and deny rules are in .claude/settings.json; TOOLING.md records whether they are live. When a hook refuses a write, read its message and comply. Never work around it.
- Write memory files (matter.md, brief.md, facts.md, roster.md, notes.md, log.md, documents.md, subject.md) with Write or Edit only, so the hooks run: a line added to log.md or notes.md is an Edit. Never through Bash in any form (redirection, tee, sed, cp, mv, or a Python script): the before-bash hook refuses it. This applies to every subagent.
- Write legal skills (skills/<area>/<name>/SKILL.md) and knowledge entries with Write or Edit too: the hooks keep a copy of every version in history/ and record the write, which is how the lawyer's hand edits are told apart from yours.
- Read a memory file or a template once, with one Read, just before you change it; never print templates through Bash.
- Ask the human in plain chat text, not question widgets.
- Obey the mode in BUDGET.md.
