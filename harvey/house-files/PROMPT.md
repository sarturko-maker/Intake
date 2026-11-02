# Filling in the house files with Harvey

Attach your spreadsheets (legal entities, practice areas, the EMEA legal team). Then paste the text below.

---

I need to fill in two configuration files for our legal intake workspace: house/brief.md and house/areas.md. I have attached spreadsheets of our legal entities, our practice areas and the EMEA legal team. Use them first, then interview me for the rest.

## Step 1. Pre-fill from the spreadsheets

Fill in everything the spreadsheets show. Mark each value you took from them "(from <sheet name>)". Mark anything you inferred "(to confirm)".

## Step 2. Interview me

Ask one question at a time. I will dictate the answers. Probe as you go:
- exceptions;
- examples;
- entities or areas the spreadsheets do not cover;
- which entities matter for EMEA work;
- who in the legal team covers which areas;
- who owns the shared intake mailbox;
- which teams outside legal own what (finance, procurement, HR, IT security, others);
- where signing authority and approval limits are written down;
- the tone for drafts;
- anything the agent must always or never do.

Read back every legal name, email domain and email address exactly, so I can confirm it.

## Step 3. Write the files in exactly this structure

### File 1: house/brief.md

```
---
status: template
organisation: <short name of the organisation>
legal_entities: <full legal names with legal form, comma-separated; the entities EMEA legal works for>
house_domains: <email domains that count as colleagues, comma-separated>
legal_addresses: <email addresses of the legal team and the shared mailbox, comma-separated>
intake_mailbox: <the shared legal mailbox address>
timezone: <IANA name, for example Europe/London>
reference_prefix:
lawyer_name: <my name>
---
# House brief

## Who legal acts for
<which companies, boards and teams EMEA legal advises; anyone it must not act for>

## The legal team
<one line per person: name | role | areas or entities covered | email address; who owns the intake mailbox and how it routes work>

## Routing to other teams
<one line per team: team | what they own | how to reach them>

## Entities and what each does
<one line per entity: full legal name | country | what it does | directors or managing directors if known>

## Signing authority and approval limits
<where they are written down; who approves what, above which amounts>

## Tone for drafts
<how drafts should sound>

## Always and never
<rules the agent must always or never follow>
```

### File 2: house/areas.md

One block per practice area, in this exact form:

```
---
status: template
---
# Practice areas

## commercial
- key: commercial
- name: Commercial
- code: COM
- unit_label: matter
- description: <one or two sentences on what belongs here>
- sub_areas: <comma-separated, lowercase with hyphens, or none>
- subject_rule: <what names a subject folder: counterparty short name, project code name, programme, product or topic, with an example>
- examples: <typical requests, separated by semicolons>
```

Rules:
- Area keys and sub-area names: lowercase, hyphens, no spaces.
- Always include an area "general" (sub_areas: none; subject_rule: unfiled) for anything that fits nowhere else.
- Keep "status: template" in both files until I say "final". Then change it to "status: ready".

## Step 4. Output

When I say "final", output both files complete, as Markdown documents. Start each with a line "=== FILE: house/brief.md ===" or "=== FILE: house/areas.md ===".

---

## Afterwards

1. Copy both files into the workspace's `house/` folder, replacing the templates. This is a manual step on purpose: only you change `house/`.
2. Put the spreadsheets themselves into `knowledge/entities/` and `knowledge/people/`, as the source for the full details.
3. Say "cold start" in Claude Code. It checks the two files first and tells you if anything is missing or will not parse.
