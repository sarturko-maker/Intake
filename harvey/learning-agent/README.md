# Harvey learning agent: how to run it

The agent reads past intake emails in batches and drafts the first knowledge (facts about the company) and skills (how the team works). Everything it writes is a draft. You and Claude Code check it later.

## Set up (about 10 minutes)

1. In Harvey's Agent Builder, create a new agent. Call it "Intake learning agent".
2. Paste `AGENT-INSTRUCTIONS.md` into its instructions.
   - Choose the company-name rule first. **KEEP** means names stay in the output; you anonymise before sharing. **REPLACE** means Harvey uses Customer A, Supplier B and so on.
3. Add `OUTPUT-FORMAT.md` as a knowledge source called "Output format". If the instructions field is big enough, you can paste it below the instructions instead.
4. Add no other knowledge sources and turn off web search. The agent must work only from your emails.

## Each batch

1. Attach about ten emails as `.eml` or `.msg` files. If Harvey cannot read those, print them to PDF.
   - Include the attachments. Mark-ups matter most: they show both sides' positions.
2. Send the batch message from `PROMPTS.md`, with a new batch number each time.
3. Check the reply ends with `END OF BATCH Bxx`. If it stops at "CONTINUED", say "continue".
4. Copy the whole reply into a file named after the batch (`B01.md`, `B02.md` and so on) in one folder.
5. When replies slow down or get worse, start a new conversation. Nothing needs to carry over, because each batch stands on its own.

## Consolidation (optional tonight)

- Upload your batch files and send the consolidation message from `PROMPTS.md`. Save each `=== FILE: ... ===` part as its own `.md` file.
- Claude Code will also consolidate from your batch files. Comparing the two shows how good Harvey's merge is.

## Tips

- Work oldest first, by period. Mixed topics in a batch are fine.
- Prefer threads that include the lawyers' own replies and mark-ups. They carry the judgement.
- Leave obvious HR or personal emails out before uploading if you can. The agent is told to skip them anyway.
- Anonymise before sharing outside Harvey, as planned.
- In the workspace, save results to `seeds/harvey/batches/` and `seeds/harvey/consolidated/`.

## For scale, if available: a review table

If your Agent Builder has a review table step, you can do the first pass over many emails at once:
- Put the emails in a Vault, one row per email.
- Add one column per thread-card field.
- Export the table.

Then run the batch agent only on the threads with negotiations or mark-ups, to get the negotiation records.
