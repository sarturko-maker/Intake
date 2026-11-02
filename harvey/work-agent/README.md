# Harvey matter work agent: how to set it up and use it

The agent takes one matter's Harvey pack and does the work the brief asks for. Every reply starts with **At a glance**: five plain bullets that assume you have read nothing about the matter. Then come a summary, an issues table, a mark-up, a draft reply and a note for the file, each opening with what to do with it.

## Set up once (about 10 minutes)

1. In Harvey's Agent Builder, create an agent called "Matter work agent".
2. Paste `AGENT-INSTRUCTIONS.md` into its instructions.
3. Let it take uploaded files as input.
4. Optional, and useful: add a knowledge source called "Our templates" with your standard NDA, MSA, guarantee and LPA forms.
5. Turn off web search, unless you want market research.

## Each matter

1. In Claude Code's task summary, click the matter's **Harvey pack** link. It opens the matter's `work-product/<reference>_harvey-pack/` folder, which is kept up to date after every run.
2. Open the agent in Harvey and drop in all the files from that folder. Keep the subfolders if Harvey allows; otherwise the file names are enough.
   - Harvey takes at most 50 files per upload. If a pack is bigger, the task summary says so: drop the main files first (brief, skill, corrections, notes, matter, the latest emails and documents).
3. Optionally type a line to narrow the task, for example "just the reply" or "focus on the liability clause". Then run it.
4. Download what comes back into the matter's `work-product/` folder, not into the pack folder. The pack is rebuilt whenever the matter changes; anything saved there is moved out, but it is cleaner to save in the right place first.
5. On the next "process the inbox" or "where are we", Claude Code records the deliverables, updates the brief, and links them in the task summary.
6. Send the reply yourself from Outlook, then drop your sent email into `inbox/`. The system notes whether it went as drafted.

## Good to know

- The pack holds only that matter, plus its subject profile, the area's intake file and the controlling skill. Nothing from other matters, and no knowledge base.
- Until skills are drafted and approved, packs have no `skill.md`. The agent then flags which positions are market practice rather than ours. That is a useful prompt for the next interview.
