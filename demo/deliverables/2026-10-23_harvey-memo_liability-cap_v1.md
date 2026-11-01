# Memo: Acme MSA, clause 12 (liability): options after Acme's draft v2

> **Work product of a work tool. Draft v1, not reviewed.** Prepared by Harvey from the work bundle uploaded for this matter. It is not legal advice until the Senior Legal Counsel has reviewed it. Privileged and confidential: prepared for the purpose of legal advice to Kestrel Engineering Ltd.

| | |
|---|---|
| To | Alex Morgan, Senior Legal Counsel |
| From | Harvey (work tool), from the work bundle |
| Date | 23 October 2026 |
| Matter | Acme Automotive GmbH: Master Supply Agreement, clause 12 (liability) |
| Task | brief.md from the bundle, pasted as the task, with your note that you speak to Dr Felix Brandt (Acme legal) today: options on clause 12 after Acme's v2, with a recommendation |

## 1. Short answer

- Do not accept v2. Unlimited liability for data breach is outside Kestrel's position as stated in brief.md, and is not insurable.
- Recommended target (option C): accept the 150% general cap and put data breach inside it, with data breach unlimited only for intent or gross negligence. Clause 12.3(b) already leaves intent and gross negligence uncapped, so this adds no new exposure, and it gives Acme a way to say data breach is "unlimited where it matters".
- Fallback (option B): 150% general cap plus our separate data breach cap of 2x the Annual Fees.
- Both options need the CFO's approval for a general cap above 100% (brief.md, "What the lawyer must decide"). Get it before you commit on the call.

## 2. Where the drafts stand

| Point | Acme v1, 15 Oct | Kestrel mark-up, 16 Oct | Acme v2, 19 Oct | Kestrel position (brief.md) |
|---|---|---|---|---|
| General cap (cl. 12.2) | 200% of Annual Fees | 100% | 150% | 100%; above 100% needs the CFO |
| Data breach and breaches of cl. 10 (cl. 12.4) | Unlimited, outside the cap | Separate cap of 2x Annual Fees, on top of the general cap | Unlimited: Acme's "group policy" for suppliers with network access | Separate cap up to 2x with Legal approval; never unlimited |
| Indirect loss (cl. 12.5) | Kestrel liable, including loss of production | Mutual exclusion | Mutual exclusion, but production stoppage costs caused by defective Products are direct loss, recoverable within the cap | Mutual exclusion; stoppage costs inside the cap can be accepted |
| Unlimited carve-outs (cl. 12.3) | Life, body or health; intent or gross negligence; Product Liability Act; guarantees | Unchanged | Unchanged | Death or personal injury and fraud, plus what the law will not let us limit |

Sources: Acme_MSA_v1.docx and Acme_MSA_v2.docx, clause 12 (documents/received/); Acme_MSA_v1_Kestrel_markup.docx (documents/ours/); Dr Felix Brandt's email of 19 October 2026 (correspondence/).

## 3. Analysis

**Governing law.** The MSA is governed by German law with the Stuttgart courts (cl. 16). Under German law, liability for intent and gross negligence, and for injury to life, body or health, cannot be excluded or limited in standard business terms (s 309 no 7 BGB, applied between businesses through s 307 BGB), and liability for intent can never be excluded in advance (s 276(3) BGB). Clause 12.3(a) and (b) reflect that. Practical point: every data breach caused by Kestrel's intent or gross negligence is already uncapped under clause 12.3(b). The real question is data breach caused by ordinary negligence.

**Data breach.** The definition is wide (cl. 1.5): it covers any unauthorised access to Acme's networks or systems caused by Kestrel, its subcontractors or the Monitoring Service. A compromised monitoring gateway used as a way into a plant network would be a "Data Breach", and the loss could include stopped production lines. That exposure has no natural ceiling, which is why Kestrel's position never allows it to be unlimited. Tom Hale's email of 15 October makes the same point commercially: "I do not want to promise anything we cannot insure."

**Insurance.** Clause 11.1 requires cyber insurance of at least EUR 5 million "per claim" and product liability of at least EUR 10 million per claim. Kestrel's insurance schedule is not in the bundle. Please check (a) that the cyber limit meets EUR 5 million for each claim, not only in the aggregate, and (b) how much of any aggregate limit is shared with other customers. A 2x data breach cap only makes sense if it fits inside that cover at the expected Annual Fees.

**General cap.** Acme moved from 200% to 150%. The bundle does not give the expected Annual Fees; ask Tom Hale for the forecast. Note that "Annual Fees" means the fees in the 12 months before the event (cl. 1.2), so the cap is lower in the first contract year. That favours Kestrel; do not offer a floor unless Acme asks.

**Production stoppage (cl. 12.5).** Acceptable as drafted, because the costs stay inside the cap. If you want to tighten it, add "reasonable and documented" before "costs".

## 4. Options

Exposure is for ordinary negligence, in multiples of the Annual Fees (AF). Intent, gross negligence and personal injury stay uncapped in every option under clause 12.3.

| Option | General cap | Data breach | Highest exposure | Approval needed | Likely Acme reaction | View |
|---|---|---|---|---|---|---|
| A. Hold the mark-up | 100% | Separate 2x cap | 1.0 AF + 2.0 AF | Legal (2x cap) | Already rejected in v2 | Not as the end position |
| B. Move on the cap | 150% | Separate 2x cap | 1.5 AF + 2.0 AF | CFO (150%); Legal (2x) | A visible move on both points; Acme still cites its group policy | Fallback |
| C. One shared cap | 150% | Inside the 150% cap; unlimited only for intent or gross negligence | 1.5 AF in total | CFO (150%) | Close to Acme's policy wording; lets Acme report "unlimited for gross negligence" | Recommended |
| D. Accept v2 | 150% | Unlimited | No limit | Outside Kestrel's position | n/a | Do not accept |

Option C is better for Kestrel on paper than option B (one cap of 1.5 AF instead of 3.5 AF in total), and it costs nothing that clause 12.3(b) does not already give away.

## 5. Suggested wording (option C), clause 12.4

> 12.4 Supplier's liability for any Data Breach, and for any breach of clause 10 (Data Protection and Information Security), is subject to the limit in clause 12.2, except where the Data Breach or breach was caused by Supplier's intent or gross negligence, in which case clause 12.3(b) applies.

If Acme proposes "wilful misconduct" instead of "intent", ask them to use "intent", the term in clause 12.3(b). Two different terms for the same idea invite an argument about whether they mean different things.

## 6. Points outside clause 12, noticed but not analysed

- Cl. 5.2: liquidated damages for delay are not the sole remedy for delay.
- Cl. 7.3: repair within five working days, and Acme may remedy defects itself at Kestrel's cost.
- Cl. 8.2: the IP indemnity should be confirmed as subject to the cap in clause 12.2, not a "guarantee" under clause 12.3(d).
- Cl. 15.3: no subcontracting without Acme's consent. The Monitoring Service relies on hosting and monitoring subcontractors, who should be approved in the MSA.
- Annexes 1 to 4 (including the data processing agreement) are not yet provided.

## 7. Next steps

1. Ask the CFO to approve a general cap of 150% (needed for options B and C).
2. Ask Tom Hale for the expected Annual Fees, and Finance for the cyber limit and how much of it is used.
3. On today's call, offer option C; keep option B in reserve. Do not agree to unlimited data breach liability.
4. After the call, send the clause 12.4 wording above to Dr Brandt with the reference in the subject line.

## 8. What this memo is based on, and its limits

Read: brief.md, matter.md, facts-live.md, subject.md and intake.md from the bundle; the emails of 15, 16 and 19 October 2026; Acme_MSA_v1.docx, Acme_MSA_v1_Kestrel_markup.docx and Acme_MSA_v2.docx; your note with the task. Not seen: Kestrel's insurance policies, the knowledge base, the MSA annexes. The German law points are general; confirm them with German counsel if the contract value justifies it.
