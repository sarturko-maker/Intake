# Legal intake on Copilot Studio: specification

The plan for building legal intake on Microsoft Copilot Studio, phase by phase. Markdown only: no code, no company data. Every example here is invented. Real requests, answers, skills and knowledge live in the company tenant, never in this repository.

**The arc in one line:** first give Sales answers without legal, then let the agent watch how legal works, then let it do the intake, then let it finish the easy ones.

## Two halves

| | The build | The lab |
|---|---|---|
| What | Copilot Studio agents, Power Automate flows, SharePoint lists and libraries, Dataverse, later a worker in Azure AI Foundry | This workspace: Claude Code on the lawyer's laptop |
| Job | Runs intake for Sales | Learns how legal works by watching, with nobody asked, and turns it into content the lawyer approves: skills, knowledge, the question bank, the five points |
| Sends anything? | Only what [CONTRACT.md](CONTRACT.md) allows in each phase | Never |
| Data | Company tenant | The lawyer's laptop, then the tenant via export |

Content flows one way into the build: the lab writes working skills and knowledge as it reads, the lawyer approves what is to leave, then exports it ([export.md](export.md)). Nothing working is ever exported. Evidence flows the other way: the register and the question log feed the lab ([lab-changes.md](lab-changes.md)).

## Phases

| Phase | Goal | Spec |
|---|---|---|
| 0, plumbing | Nothing later waits on IT | [p0-plumbing.md](p0-plumbing.md) |
| 1, knowledge agent and button | Simple questions stop reaching legal; every request is captured properly | [p1-agent-and-button.md](p1-agent-and-button.md), [five-points.md](five-points.md) |
| 1.5, watch and draft | Prove the agent asks the right questions before it may ask them | [p1-5-watch-and-draft.md](p1-5-watch-and-draft.md) |
| 2, the proper agent | Legal starts every matter with a complete file | [p2-proper-agent.md](p2-proper-agent.md), [question-bank.md](question-bank.md) |
| 3, if the data supports it | Low-risk, repetitive work goes straight back to Sales | [p3-low-risk.md](p3-low-risk.md) |

These phase numbers belong to the build. They have nothing to do with this repository's `phase-2/` folder.

## Files

| File | What it holds |
|---|---|
| [CONTRACT.md](CONTRACT.md) | The rules every agent, flow and worker follows; what may be sent in each phase; who approves what |
| [measures.md](measures.md) | Success measures, the baseline, and the gates between phases |
| [data-model.md](data-model.md) | The reference, the matter library, the register, the question log, the facts table, the approved libraries |
| [templates.md](templates.md) | Fixed texts: receipt, acknowledgement, questions, ticket, cards |
| [five-points.md](five-points.md) | The five-point check of a deal document, as a prompt tool, with its tests |
| [question-bank.md](question-bank.md) | "Find out, assume, then ask": the questions legal needs answered, where to find them, safe defaults |
| [export.md](export.md) | How approved content moves from the lab into the build |
| [lab-changes.md](lab-changes.md) | What changes in this workspace, and when |

## Ground rules for this folder

- Plain English. Anything the lawyer must decide is marked **To confirm**.
- Nothing here is a house position. Where it proposes content (the five points, thresholds), the lawyer replaces or confirms it.
- Changes to [CONTRACT.md](CONTRACT.md) take effect only once the lawyer approves them. Keep its version line up to date.
