---
# Only you edit this file. When the areas below describe your team, change "template" to "ready".
status: ready
---
# Practice areas

The areas the legal team works in. The agent makes one folder for each area and each sub-area listed here, and files every matter under one of them. It never adds an area or a sub-area by itself. When it thinks a sub-area is missing, it suggests one in the digest, and you add it here.

These are the seven standard areas, with Kestrel's own examples. Keep the format: a line with two hash signs and the key, then the eight lines that start with a dash.

What each line means:

- `key`: a short name in lowercase, used for the folder. Letters, numbers and hyphens only.
- `name`: the name people use.
- `code`: a short code of three capital letters.
- `unit_label`: what you call one piece of work in this area, such as matter, case or project.
- `description`: one sentence on what belongs here.
- `sub_areas`: folders inside the area, separated by commas, or "none".
- `subject_rule`: what names the folder for each party or project, with an example in brackets.
- `examples`: typical requests, separated by semicolons.

Kestrel notes on names. A subject folder is the short name of the other company, without Ltd, GmbH, plc or Ltda. Several matters with the same company share one subject folder: an NDA, then a supply agreement, then a questionnaire for Acme all sit under acme-automotive. In commercial, "partners" means technology and installation partners. We have no sub-area for distributors or agents yet.

## commercial
- key: commercial
- name: Commercial
- code: COM
- unit_label: matter
- description: Customer, supplier and partner contracts and questions, from NDAs to supply agreements, tenders and security questionnaires; not invoice or payment queries, which belong to accounts payable.
- sub_areas: customers, suppliers, partners, internal
- subject_rule: counterparty company, slug of its short name without the legal form (acme-automotive, meridian-bank, volta-rail, halden-water, rio-bombas)
- examples: customer NDA before contract talks; master supply agreement and liability cap negotiation; RFQ and tender terms exceptions; customer security questionnaire; supplier terms and conditions; maintenance contract liability schedule

## privacy
- key: privacy
- name: Privacy
- code: PRV
- unit_label: matter
- description: Data protection programmes, data processing terms and privacy questions, including the data the remote condition monitoring service collects.
- sub_areas: gdpr, ccpa
- subject_rule: programme or vendor, slug of its short name (records-of-processing, vendor-dpas)
- examples: data processing agreement for the monitoring service; customer request for our sub-processor list; records of processing update; privacy notice for the website

## m-and-a
- key: m-and-a
- name: M&A
- code: MNA
- unit_label: project
- description: Acquisitions, disposals, investments and joint ventures by the Kestrel group.
- sub_areas: none
- subject_rule: project code name (project-osprey)
- examples: NDA with an acquisition target; due diligence request list; term sheet review; disclosure letter

## disputes
- key: disputes
- name: Disputes
- code: DSP
- unit_label: case
- description: Claims and threatened claims by or against Kestrel, and litigation; routine invoice queries and short payments go to accounts payable, not here.
- sub_areas: none
- subject_rule: counterparty company, slug of its short name without the legal form (volta-rail)
- examples: customer warranty claim; letter before action; debt recovery after Finance has chased twice; settlement agreement

## corporate
- key: corporate
- name: Corporate
- code: CRP
- unit_label: matter
- description: Company secretarial work for both group companies, signing authority, powers of attorney and group structure.
- sub_areas: none
- subject_rule: topic, short slug (signing-authority, board-minutes, entity-register)
- examples: who can sign for Kestrel Pumpen GmbH; power of attorney (Vollmacht) for a bank; board resolution; Companies House or Handelsregister filing

## trade-compliance
- key: trade-compliance
- name: Trade compliance
- code: TRC
- unit_label: matter
- description: Export controls, sanctions and customs for Kestrel products shipped from the UK or Germany.
- sub_areas: exports, sanctions, customs
- subject_rule: product family, slug of its name (px-400); the destination country only when no product is involved (egypt)
- examples: dual-use classification of a pump range; sanctions screening of a new customer; customs tariff code for spare parts; end-user certificate

## general
- key: general
- name: General
- code: GEN
- unit_label: matter
- description: Anything that fits no other area until you move it, including misdirected, out-of-area and sensitive emails.
- sub_areas: none
- subject_rule: always unfiled
- examples: supplier invoice sent to legal by mistake (accounts payable); request for another team; personal email for the lawyer
