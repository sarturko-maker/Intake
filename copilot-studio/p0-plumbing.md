# Phase 0: plumbing

Goal: get the prerequisites out of the way so nothing later waits on IT. Accounts, permissions and billing, not design.

## How the build is made

The maker builds in their own development environment, inside **one solution**, using environment variables and connection references for everything that differs between environments. Handover to test and then production is an import of the managed solution, with new values for the variables and new connections. Nothing is hard-coded: no site address, mailbox, channel or prefix inside a flow or an agent.

**Environment variables:** legal site address; matter library; register list; question log list; Sales library; legal library; intake mailbox; legal Teams team and channel; reference prefix; house time zone; pilot group; and, from Phase 1.5, the classification threshold and the most questions per message.

**Connection references:** Outlook (the service account), SharePoint, Teams, Approvals, Office 365 Users; Dataverse from Phase 1.5.

## Checklist

| # | Item | Owner | Done when |
|---|---|---|---|
| 1 | Legal environment: a managed Power Platform environment in the company's region, restricted to a legal security group; Dataverse switched on | Power Platform admin | Makers and the service account can open it; no one else can |
| 2 | DLP policy on the legal environment: Outlook, SharePoint, Teams, Approvals, Office 365 Users, Dataverse and Copilot Studio in the business group; HTTP, custom connectors and everything else blocked | Power Platform admin, IT security | Policy applied and tested: a flow using a blocked connector fails to save |
| 3 | `legal-intake@` shared mailbox, with retention set | M365 admin | Mail arrives; legal can read it; the service account can send as it |
| 4 | Service account: licensed for Outlook and Power Automate, under the company's sign-in policy, owned by IT, used only by flows | IT | All connections in the solution use it; none use a person's account |
| 5 | Copilot Studio billing: Copilot Credits capacity (prepaid or pay-as-you-go through an Azure subscription) assigned to the legal environment; a consumption alert at 50% and 80% | Power Platform admin, finance | Credits show in the admin centre; the lawyer gets the monthly figure |
| 6 | Licences checked: makers, the service account, Sales users of the Teams agent, and lawyers who will use the Outlook Copilot pane in Phase 1.5 | IT | A short list of who needs what, with costs |
| 7 | SharePoint "Legal intake" site, legal only: matter library, register list, question log list, legal library; the Sales library readable by the pilot group. Versioning on, retention labels set, audit logging on | M365 admin, maker | Lists and libraries built to [data-model.md](data-model.md); permissions tested with a Sales account |
| 8 | Legal Teams team and a channel for Claim cards | M365 admin | The service account can post to it |
| 9 | Outlook "Send to Legal" button deployed centrally to the pilot group. The mechanism is the build team's choice; it must deliver the whole selected email with its attachments, plus the short form | M365 admin, maker | A pilot user sends a test email with two attachments and both arrive intact |
| 10 | Pilot group: named Sales users (**To confirm:** 10 to 20 across two or three teams), the lawyer, the paralegal; a feedback channel | Legal | Names agreed; a kick-off note sent |
| 11 | Success measures and baseline ([measures.md](measures.md)) | Legal | Baseline numbers written down and dated |
| 12 | Data protection screening: the build logs Sales staff's questions and timings. Where a works council or staff consultation applies, check whether it is needed before logging starts. Tell the pilot group what is logged and why | Legal, data protection | Screening filed; any consultation done; pilot note sent |
| 13 | [CONTRACT.md](CONTRACT.md) approved as version 1.0 | Lawyer | Version line updated |

Nothing in Phase 1 starts until items 1 to 9 are done.
