# Measures and gates

What we count, where it comes from, and what must be true before the next phase starts. Thresholds other than the 80% question match are proposals: **To confirm** with the lawyer in Phase 0.

## Baseline (record in Phase 0)

The lab already counts four measures (INDEX.md in the workspace). Take the last full month as the pre-pilot baseline:

| Measure | Meaning |
|---|---|
| Lawyer minutes per matter | Time the lawyer spent, as the lawyer recorded it |
| Share accepted unchanged | Drafts or proposals the lawyer accepted without change |
| Outcome agreement | Proposed outcome matched the lawyer's confirmed outcome |
| Hours to ready | From the request arriving to the matter being ready for the lawyer |

Add two counts from the legal mailbox and the lawyers' inboxes for the same month: requests received, and follow-up emails legal sent before work could start.

## Phase 1

| Measure | Source |
|---|---|
| Requests through the button, as a share of all requests | Register (source column) against the baseline count |
| Sales questions the agent answered without legal | Agent analytics: answered, rated helpful, no button press on the same topic within a week |
| Five-point checks run | Agent analytics |
| Follow-up questions legal had to ask, per request | Question log |
| Hours from request to claim; hours to ready | Register |
| Gaps: questions the library could not answer | Agent analytics, worked by the paralegal |

## Phase 1.5

| Measure | Source |
|---|---|
| **Question match:** the agent's drafted questions against the lawyer's final questions | Question log, lawyer's verdict per question |
| Unnecessary questions: drafted, and rejected by the lawyer as not needed | Question log |
| Classification accuracy: area and work type, against the lawyer's correction | Register |
| Acknowledgement time | Flow run history |

How question match is scored: for each matter, the lawyer marks each question: **match** (the same information sought, whatever the wording), **partly**, **missed** (the lawyer needed it, the agent did not ask), or **unnecessary**. Match rate = (matches + half the partlies) ÷ the lawyer's questions. Count unnecessary ones separately: a high match rate with many unnecessary questions still annoys Sales.

## Phase 2

| Measure | Source |
|---|---|
| Complete files: matters reaching the lawyer with nothing left to ask | Ticket, lawyer's tick |
| Questions sent to Sales per matter; assumptions made per matter; assumptions corrected by Sales | Question log |
| Days from request to complete file | Register |
| Lawyer minutes per matter; share of first drafts accepted unchanged | Register |

## Phase 3

| Measure | Source |
|---|---|
| Matters closed in low-risk categories, as a share of all matters | Register |
| Errors found in the weekly sample | Sample review log |
| Lawyer hours saved: minutes per matter before, times the volume handled | Register and baseline |
| Hours from request to answer, for Sales | Register |

## Gates

| From → to | Must be true |
|---|---|
| 0 → 1 | Everything in [p0-plumbing.md](p0-plumbing.md) done; baseline recorded |
| 1 → 1.5 | Pilot run for 6 to 8 weeks; most requests come through the button (**To confirm:** 70%); no data-handling incident; question log kept for every matter |
| 1.5 → 2 | **Question match at least 80%** over at least 40 matters (**To confirm**) covering the most common work types; unnecessary questions under 10% (**To confirm**); classification right in at least 90% (**To confirm**); no sensitive mail processed |
| 2 → 3, per category | At least 30 matters in the category (**To confirm**); at least 90% of first drafts accepted unchanged (**To confirm**); no material error in the last 30; the lawyer confirms the category as a fixed point |

A gate missed means the phase continues; it does not mean failure. Write down why it was missed and what changes.
