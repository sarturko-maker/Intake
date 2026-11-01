# Messages to paste into the agent

Send these in order, one at a time. Wait for each reply and check it before sending the next. Each message builds on the files the earlier ones created.

## 1. Work-types report

> Pass 1. Using every row of the review table, build the work-types report as the first section of legal-learning-register.md, and create that file as a Markdown document in your workspace with the other register sections empty. Count rows by category and work type. Merge "new:" labels that mean the same thing. Tell me how many rows you used, and list the work types with their counts.

## 2. Matters, one work type at a time

Start with the biggest work type, then work down the list.

> Pass 2: matters for the work type "NDA review". Using every row with this work type, group the rows into matters by conversation key (and merge keys that are clearly the same matter). Write one entry per matter in legal-matters.md, in the output format. Create the file if it does not exist; otherwise open it, add these matters, and save it under the same name. Report the rows used and the counts before and after.

Repeat for each work type, changing the name in quotes.

## 3. The register

> Pass 3. Using legal-matters.md and the review table, fill in the rest of legal-learning-register.md:
> - ways of working by work type;
> - positions and precedents by clause topic, with the context for every move;
> - the front door;
> - knowledge;
> - our companies;
> - the code key;
> - the glossary;
> - roles;
> - open questions;
> - documents to fetch.
>
> Open the file, update it, and save it under the same name. Report the counts before and after.

If the reply stops early, say "continue". If it is too much at once, send the same message with "ways of working and positions only", then "everything else".

## 4. Skills, one work type at a time

> Build the skill for the work type "NDA review" in the output format: SKILL.md, plus positions.md and precedents.md if needed. Use legal-matters.md, legal-learning-register.md and the review table rows of this work type. Keep the skill set under about 15,000 words and SKILL.md under about 4,000; split it rather than drop evidence. Save each file as a Markdown document, starting with an === FILE: folder/name.md === line. Mark it status: draft (unverified).

Repeat for each work type with three or more matters. Then:

> Build the front-door skill and reports/work-types.md in the output format.

## 5. Knowledge pack and reports

> Build the knowledge pack in the output format: one file per fact or fact set, plus knowledge/our-companies.md, knowledge/glossary.md and knowledge/code-key.md without the name column. Then build reports/open-questions.md and reports/coverage.md. Never put negotiation positions in the knowledge pack.

## Check, at any point

> Check legal-matters.md and legal-learning-register.md. List duplicate matters, entries without evidence, reasons you inferred rather than saw, personal names or email addresses, outside parties named instead of coded, older facts shown as current, and any count that went down. Fix them and save both files.

## New conversation, or the files are not visible

Attach the latest saved copies of the working files, then send:

> Here are the latest legal-matters.md and legal-learning-register.md. Save them as your working files and continue from them.

## After adding more emails to the Vault

> New rows were added to the review table for emails from <dates>. Update legal-matters.md and legal-learning-register.md with those rows only. Newer facts replace older ones, which are kept as "earlier position". Save both files and report the counts before and after.
