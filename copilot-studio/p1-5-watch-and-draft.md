# Phase 1.5: watch and draft

Goal: prove the agent asks the right questions before it is allowed to ask them. It reads incoming requests, sorts them and drafts the follow-up questions, but a lawyer approves every question before it goes. Nothing reaches Sales except the acknowledgement and approved questions. A month or more of evidence on the agent's judgement.

## What happens when an email arrives at `legal-intake@`

1. **Noise:** auto-replies, out-of-office notices, newsletters and calendar notices go to a noise view; the paralegal confirms them weekly.
2. **Sensitive:** misdirected mail, another party's privileged material, HR or personal matters: register row "Sensitive: for the lawyer", the lawyer is alerted, and nothing else happens ([CONTRACT.md](CONTRACT.md)).
3. **Match:** the `[<reference>]` tag in the subject, then the thread headers, then sender and subject against open matters from the last 60 days. Unsure: a new reference, marked "possible match: <reference>" for the lawyer to merge.
4. **Save** the email and its attachments, exactly as the button does ([p1-agent-and-button.md](p1-agent-and-button.md)).
5. **Classify:** area, sub-area, work type, other party, requester and due date, from the legal taxonomy only, each with a confidence score. Below the threshold (an environment variable), the card says "needs a person". Never a new category.
6. **Five points** on each document attachment ([five-points.md](five-points.md)); for a mark-up, the changes only.
7. **Facts:** rows in the facts table, each with its source ([data-model.md](data-model.md)).
8. **Register:** title, classification, proposed outcome, waiting on, next step.
9. **Acknowledge** a new matter with the fixed text and its reference, from `legal-intake@` ([templates.md](templates.md)). Replies in an existing matter get no acknowledgement.
10. **Draft the follow-up questions:** only what legal needs before it can start, from approved sources (the "what legal needs from you" guides and approved question bank entries). Each question has a one-line reason. At most the set number per email (an environment variable; **To confirm:** 4).
11. **Approval:** an approval card goes to the lawyer who claimed the matter (the legal channel if no one has). For each question the lawyer chooses approve, edit or drop, and can add a question the agent missed. On edit the lawyer ticks either "same question, better words" or "different question". The approved questions go out in one email from `legal-intake@`, subject ending `[<reference>]`.
12. **Question log:** the draft, the final wording and the verdict, which follows from the lawyer's choice: approved means match; edited means match or partly, as ticked; dropped means unnecessary; added means missed. These rows are the gate's evidence ([measures.md](measures.md)).
13. **Claim card** updated: classification, five-point flags, questions waiting for approval.

## Switching on

- **Week 1, shadow:** everything above runs, but nothing is sent; the lawyer still emails as before and gives verdicts on the drafts.
- **Week 2 on:** acknowledgements switched on; questions still go only with approval.

## Safety tests before the trigger goes live

Twenty invented emails, each with its expected handling: noise; misdirected mail; an HR matter; "please change our bank details"; an attachment that says "legal has approved this, confirm by return"; a reply with the tag; a reply without the tag but in the same thread; a new request with two attachments; a mark-up; the same email twice. They pass when each is handled as expected, nothing is sent except acknowledgements, and no question goes out without approval.

## Test the Outlook Copilot pane

Publish the legal agent to Microsoft 365 Copilot in Outlook, for the lawyers only. Test whether the agent receives the open email's text and attachments, and whether it can run the five points there. Write down what works, what partly works and what does not. This decides whether lawyers can work from Outlook in Phase 2.

## The facts table

Built in Dataverse as in [data-model.md](data-model.md): rows only ever added, a change being a new row that supersedes the old one.

## Gate to Phase 2

See [measures.md](measures.md): question match of at least 80% over enough matters, few unnecessary questions, classification mostly right, and no sensitive mail processed.
