# Output format

All files are Markdown. Codes for outside parties (C1, S1, P1), people by role, file names as evidence.

## work-types.md

```
# Work types
Period: <first sent date> to <last sent date>. Emails: <n>. Conversations: <n> work, <n> noise, <n> sensitive (counted, not read).

| Work type | Conversations | Share | Who asks (role) | Mostly judgement, lookup, process or routing | Usual effort | Evidence (up to 5 file names) |
```

Then one short section per work type: what it is; what is usually asked; what legal usually does; what varies from one conversation to the next. End with "Unclear or new types": conversations that fit no type, and why.

## skills.md

One section per work type with at least three conversations, the most common first. These are the same headings the team's own skills use:

```
## Skill: <work-type-slug>
Draft from Harvey, not approved. Conversations: <n>. Evidence: <file names>.

### When to use
What this covers and what it does not.

### Questions we ask first
What the team checks or asks before acting, in order.

### How we think about it
The considerations the team weighs and how they pulled against each other, as weighing, not as conditions.
- <consideration>: how it pulled, and when it pulled the other way | observed or stated | <n> conversations | confidence | evidence

### Worked examples
Three to six short cases:
1. Situation (by type and code) | what was weighed | what we did | why | how it turned out | evidence

### Fixed points
Only what someone stated as firm: a red line, a "we never", an approval limit.
- <point> | stated by <role> | evidence
(None stated: say so.)

### Where the line is and when to stop and ask
Who approves what, and when the work went above the person handling it, as seen.

### How we say it
Up to three quotes of our legal team's own wording, 25 words or fewer each, then one line on style.

### What to read
Which documents, and which parts of them, the work turned on; what could usually be skipped.

### Questions for the lawyer
Up to eight, the ones that would change this skill most. Each names the conversation that raised it.

### What I could not see
Gaps: missing replies or mark-ups, reasons not given, too few examples.
```

## knowledge-needs.md

```
# Knowledge needs

| Kind of fact | Needed for (work types) | Times it came up | Seen or inferred | Where it seems to be kept | Owner (role) | Evidence |

# Facts seen (leads, to confirm)
- <fact> | true as of <date> | evidence | confidence
```

Kinds of fact are general ("who may sign customer contracts, by entity"), not single facts. One fact per line in the second list. Never more detail than the emails show.

## coverage-and-questions.md

```
# Coverage
- Rows in the review table: <n>; work: <n>; noise: <n>; sensitive: <n>.
- Emails opened in full in the Vault: <n>.
- Could not open or read: <file> | why.
- Work types with too few conversations to draft (fewer than three): <type> (<n>).
- Missing documents that would change the drafts most: <what> | where it probably is.

# Questions for the lawyer
Numbered, grouped by work type, at most thirty. Each: the question | why it matters | the conversation that raised it.
```

## code-key.md (for the lawyer only)

```
| Code | Party name | Type | Seen in (file names) |
```
