---
# Only you edit this file. When the areas below describe your team, change "template" to "ready".
status: template
---
# Practice areas

The areas the legal team works in. The agent makes one folder for each area and each sub-area listed here, and files every matter under one of them. It never adds an area or a sub-area by itself. When it thinks a sub-area is missing, it suggests one in the digest, and you add it here.

The seven areas below are a starting point. Change them freely: rename, delete or add. Keep the format: a line with two hash signs and the key, then the eight lines that start with a dash.

What each line means:

- `key`: a short name in lowercase, used for the folder. Letters, numbers and hyphens only.
- `name`: the name people use.
- `code`: a short code of three capital letters.
- `unit_label`: what you call one piece of work in this area, such as matter, case or project.
- `description`: one sentence on what belongs here.
- `sub_areas`: folders inside the area, separated by commas, or "none".
- `subject_rule`: what names the folder for each party or project, with an example in brackets.
- `examples`: typical requests, separated by semicolons.

## commercial
- key: commercial
- name: Commercial
- code: COM
- unit_label: matter
- description: Customer, supplier and partner contracts and questions.
- sub_areas: customers, suppliers, partners, internal
- subject_rule: counterparty company, slug of its short name (acme-automotive)
- examples: NDA review; MSA negotiation; supplier terms; RFQ exceptions; security questionnaire

## privacy
- key: privacy
- name: Privacy
- code: PRV
- unit_label: matter
- description: Data protection programmes, data processing terms and privacy questions.
- sub_areas: gdpr, ccpa
- subject_rule: programme or vendor, slug of its short name (records-of-processing, vendor-dpas)
- examples: DPA review; sub-processor list; records of processing; data subject request; privacy notice update

## m-and-a
- key: m-and-a
- name: M&A
- code: MNA
- unit_label: project
- description: Acquisitions, disposals, investments and joint ventures.
- sub_areas: none
- subject_rule: project code name (project-falcon)
- examples: NDA with a target; due diligence request; term sheet review; disclosure letter

## disputes
- key: disputes
- name: Disputes
- code: DSP
- unit_label: case
- description: Claims and threatened claims by or against the organisation, and litigation.
- sub_areas: none
- subject_rule: counterparty company, slug of its short name (acme-automotive)
- examples: late delivery claim; letter before action; debt recovery; settlement agreement

## corporate
- key: corporate
- name: Corporate
- code: CRP
- unit_label: matter
- description: Company secretarial work, signing authority, powers of attorney and group structure.
- sub_areas: none
- subject_rule: topic, short slug (signing-authority, board-minutes)
- examples: who can sign; power of attorney; board resolution; register update; subsidiary filing

## trade-compliance
- key: trade-compliance
- name: Trade compliance
- code: TRC
- unit_label: matter
- description: Export controls, sanctions and customs.
- sub_areas: exports, sanctions, customs
- subject_rule: product or destination, slug of its short name (pump-series-x)
- examples: dual-use classification; sanctions screening question; customs tariff question; end-user certificate

## general
- key: general
- name: General
- code: GEN
- unit_label: matter
- description: Anything that fits no other area until you move it, including misdirected, out-of-area and sensitive emails.
- sub_areas: none
- subject_rule: always unfiled
- examples: misdirected invoice; request for another team; personal email for the lawyer
