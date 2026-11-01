"""Text of Volta_Rail_Tender_Terms.pdf (40 pages), invented for the demo.

Page 1 is the cover, page 2 the contents. Each numbered section fills one page, so section N is
on page N + 2. Two pages matter for a supplier's lawyer: page 23 (section 21, Liability:
unlimited liability including consequential loss; liquidated damages capped at 20%) and page
31 (section 29, Intellectual property and warranty: assignment of background IP; 36-month
warranty). Pages 39 and 40 are Appendices A and D.

Each entry: (number, title, part, [blocks]). A block is a paragraph string, or
("table", header, rows) for a table.
"""

ITT_REF = "VR-T-2026-117"
TITLE = "Supply of Depot Drainage, Wash-Plant and Cooling-Water Pumps"

PARTS = {
    "A": "Part A - Instructions to tenderers",
    "B": "Part B - Summary of the Requirement",
    "C": "Part C - Conditions of contract",
    "X": "Appendices",
}

SECTIONS = [
    (1, "Introduction", "A", [
        "1.1 Volta Rail Ltd (\"Volta\") invites tenders for the supply of drainage, sump, "
        "wash-plant and cooling-water pumps for its four train maintenance depots, together with "
        "spare parts and five years of maintenance support (the \"Requirement\").",
        "1.2 This document contains the instructions to tenderers (Part A), a summary of the "
        "Requirement (Part B), the conditions of contract that will apply to the successful "
        "tenderer (Part C) and the forms to be completed (Appendices A and D). The full technical "
        "specification (Appendix B) and the depot drawings (Appendix C) are issued separately "
        "through the tender portal.",
        "1.3 Tenderers should read every part of this document. By submitting a tender, a "
        "tenderer accepts these instructions.",
        "1.4 Volta is not bound to accept the lowest or any tender, and may cancel or vary this "
        "procurement at any time without liability to any tenderer.",
        "1.5 In this document, \"tenderer\" means an organisation that has received this "
        "invitation to tender, and \"Supplier\" means the successful tenderer once the Contract "
        "has been awarded.",
    ]),
    (2, "About Volta Rail", "A", [
        "2.1 Volta maintains and services electric multiple units for passenger train operators. "
        "It operates four maintenance depots, referred to in this document as Depots 1 to 4.",
        "2.2 The depots work 24 hours a day, 7 days a week. Pit drainage, the recycling of "
        "wash-plant water and the cooling of traction equipment test rigs are critical to depot "
        "operations. A pump failure can take maintenance roads out of use and delay trains "
        "entering passenger service.",
        "2.3 The existing pumps were installed between 2004 and 2011. Many are beyond their "
        "design life, spare parts are increasingly hard to obtain, and the equipment does not "
        "provide condition data to Volta's depot management system.",
        "2.4 Volta's procurement team manages this process. All communications must be made "
        "through the tender portal or by email to tenders@voltarail.co.uk. Tenderers must not "
        "contact other Volta staff about this invitation to tender.",
    ]),
    (3, "Tender timetable", "A", [
        "3.1 Volta intends to follow the timetable below. Volta may change it by notice to all "
        "tenderers through the tender portal.",
        ("table", ["Activity", "Date"], [
            ["Invitation to tender issued", "Friday 9 October 2026"],
            ["Deadline for clarification questions", "Friday 23 October 2026, 12:00"],
            ["Responses to clarification questions published", "Monday 26 October 2026"],
            ["Tender return deadline", "Friday 30 October 2026, 12:00"],
            ["Evaluation and clarification meetings", "2 to 20 November 2026"],
            ["Preferred bidder notified", "Friday 4 December 2026"],
            ["Contract award", "Friday 18 December 2026"],
            ["Commencement Date", "Monday 11 January 2027"],
        ]),
        "3.2 Tenderers must keep the evaluation period free for clarification meetings at short "
        "notice.",
    ]),
    (4, "Clarification questions", "A", [
        "4.1 Questions about this invitation to tender must be submitted through the tender "
        "portal by 12:00 on 23 October 2026.",
        "4.2 Volta will publish anonymised questions and answers to all tenderers by 26 October "
        "2026, unless a question is marked commercially sensitive and Volta agrees to answer it "
        "privately.",
        "4.3 Volta is not obliged to answer questions received after the deadline.",
        "4.4 Clarification questions may not be used to propose changes to the conditions of "
        "contract. Proposed changes must be listed in Appendix D (see section 8).",
    ]),
    (5, "Tender submission requirements", "A", [
        "5.1 Tenders must be submitted through the tender portal by 12:00 on 30 October 2026. "
        "Late tenders will not be considered.",
        "5.2 Each tender must include: (a) the Form of Tender and Pricing Schedule (Appendix A); "
        "(b) a technical response of no more than 30 pages, answering the questions in Appendix "
        "B; (c) the Compliance and Exceptions Form (Appendix D); (d) audited accounts for the last "
        "two financial years; (e) evidence of the insurances required by section 23; and (f) the "
        "completed health and safety questionnaire.",
        "5.3 Tenders must be written in English. Prices must be in pounds sterling and exclude "
        "VAT.",
        "5.4 Volta may reject a tender that is incomplete or does not follow these instructions.",
    ]),
    (6, "Evaluation methodology", "A", [
        "6.1 Tenders will be evaluated on the basis of the most advantageous tender, using the "
        "criteria and weightings below.",
        ("table", ["Criterion", "Weighting"], [
            ["Technical solution and compliance with the Specification", "30%"],
            ["Delivery programme and maintenance support", "10%"],
            ["Health, safety and environment", "5%"],
            ["Social value", "5%"],
            ["Price (whole-life cost over five years)", "40%"],
            ["Commercial compliance with Part C", "10%"],
        ]),
        "6.2 Quality criteria are scored from 0 (no response) to 5 (excellent), and the score is "
        "multiplied by the weighting. A score of 0 or 1 on any quality criterion may lead to "
        "rejection of the tender.",
        "6.3 The lowest whole-life cost receives the full price score. Other tenders are scored "
        "in proportion.",
        "6.4 The commercial compliance score is reduced for each exception listed in Appendix D, "
        "as described in section 8.",
    ]),
    (7, "Pricing schedule instructions", "A", [
        "7.1 Tenderers must state a unit price for each pump type in Appendix A, delivered DDP to "
        "the relevant depot and including installation, commissioning and training.",
        "7.2 Prices are fixed for the first two years from the Commencement Date. After that they "
        "may be indexed once a year by the Consumer Prices Index, capped at 4% a year.",
        "7.3 Maintenance support must be priced per depot per year and include two planned "
        "visits a year and an emergency call-out response within 8 hours.",
        "7.4 Volta may ask a tenderer to explain any price that appears abnormally low.",
    ]),
    (8, "Compliance with the conditions of contract", "A", [
        "8.1 Part C sets out the conditions of contract. Volta's strong preference is to contract "
        "on these conditions without amendment.",
        "8.2 Any exception must be listed in Appendix D, with the reason and the tenderer's "
        "proposed wording. Exceptions that are not listed are treated as withdrawn, and the "
        "tenderer is deemed to accept the conditions in full.",
        "8.3 Each exception reduces the commercial compliance score. An exception to section 21 "
        "(Liability) or section 29 (Intellectual property and warranty) may result in a score of "
        "zero for commercial compliance.",
        "8.4 Volta will negotiate exceptions, if at all, only with the preferred bidder.",
    ]),
    (9, "Conduct of tenderers", "A", [
        "9.1 Tenderers must not collude with other tenderers, fix or adjust prices by agreement, "
        "or canvass any Volta employee or adviser about this procurement.",
        "9.2 Tenderers must declare any actual or potential conflict of interest as soon as they "
        "become aware of it.",
        "9.3 Tenderers must not offer any gift, payment or other inducement to any person in "
        "connection with this procurement.",
        "9.4 Volta may disqualify a tenderer that breaches this section, in addition to any other "
        "remedy.",
    ]),
    (10, "Confidentiality and publicity", "A", [
        "10.1 The tender documents are confidential and may be used only to prepare a tender.",
        "10.2 Tenderers may share the tender documents with their professional advisers and "
        "proposed subcontractors, who must keep them confidential.",
        "10.3 Tenderers must not make any public statement about this procurement without "
        "Volta's prior written consent.",
    ]),
    (11, "Tender validity and costs", "A", [
        "11.1 Tenders must remain valid for 120 days from the tender return deadline.",
        "11.2 Tenderers bear their own costs of preparing and submitting a tender and of taking "
        "part in clarification meetings, whatever the outcome.",
        "11.3 Nothing in this document or in the procurement process creates a contract until "
        "the Contract is signed by both parties.",
    ]),
    (12, "Scope of supply", "B", [
        "12.1 The Requirement covers approximately 64 pumps across the four depots, as set out "
        "below. Final quantities will be confirmed at contract award.",
        ("table", ["Pump type", "Use", "Indicative quantity"], [
            ["D1 submersible drainage", "Inspection pit and track drainage", "28"],
            ["W2 wash-plant recycling", "Train wash water recovery", "12"],
            ["C3 cooling-water circulation", "Traction equipment test rigs", "16"],
            ["S4 sump", "Plant room and basement sumps", "8"],
        ]),
        "12.2 The Supplier will provide a holding of recommended spare parts at each depot.",
        "12.3 The Supplier will provide maintenance support for five years from Acceptance, "
        "including planned maintenance, emergency call-out and condition reporting.",
    ]),
    (13, "Technical specification summary", "B", [
        "13.1 The full specification is in Appendix B. The main duty points are:",
        ("table", ["Type", "Duty point", "Notes"], [
            ["D1", "30 l/s at 15 m head", "Oily water, grit; float switch control"],
            ["W2", "25 m3/h at 40 m head", "Detergent-laden water"],
            ["C3", "120 m3/h at 32 m head", "Treated closed-circuit water, up to 60 C"],
            ["S4", "5 l/s at 10 m head", "Clean drainage"],
        ]),
        "13.2 Pumps must be suitable for continuous duty and must be provided with condition "
        "monitoring (vibration, temperature, running hours) compatible with Volta's depot "
        "management system over Modbus TCP.",
        "13.3 Equipment in the fuelling area of Depot 3 must be suitable for use in a Zone 2 "
        "hazardous area.",
    ]),
    (14, "Quality management", "B", [
        "14.1 The Supplier must hold ISO 9001 certification for the design and manufacture of "
        "the Goods and maintain it throughout the Contract.",
        "14.2 Within four weeks of the Commencement Date the Supplier must submit a quality plan "
        "and an inspection and test plan for Volta's approval.",
        "14.3 All Goods must be traceable by serial number to their manufacturing and test "
        "records for the life of the Contract.",
    ]),
    (15, "Factory acceptance testing", "B", [
        "15.1 Each pump type must undergo a factory performance test to ISO 9906 Grade 2B before "
        "dispatch.",
        "15.2 Volta may witness factory tests on ten Working Days' notice. The Supplier must "
        "provide test certificates with each delivery.",
        "15.3 Goods that fail a factory test must not be dispatched until they have been "
        "remedied and re-tested.",
    ]),
    (16, "Delivery, installation and commissioning", "B", [
        "16.1 Deliveries will be scheduled depot by depot between March and September 2027, in "
        "line with the agreed delivery programme.",
        "16.2 Installation must take place within the possession windows Volta allocates, "
        "normally between 22:00 and 06:00.",
        "16.3 Commissioning includes performance verification on site, integration with the "
        "depot management system and training for depot staff.",
        "16.4 Acceptance occurs when Volta issues an acceptance certificate after successful "
        "commissioning and the delivery of all operating and maintenance manuals.",
    ]),
    (17, "Health, safety and environment", "B", [
        "17.1 The Supplier must comply with Volta's depot safety rules, including track access "
        "permits, isolation procedures and the use of personal protective equipment.",
        "17.2 All staff working on site must hold a valid rail industry safety card and complete "
        "Volta's depot induction.",
        "17.3 The Supplier must take back packaging and replaced equipment and dispose of it in "
        "line with environmental law, providing waste transfer records.",
    ]),
    (18, "Definitions and interpretation", "C", [
        "18.1 In these conditions:",
        "\"Acceptance\" means the issue by Volta of an acceptance certificate under section 16.4; "
        "\"Commencement Date\" means the date stated in the letter of award; \"Contract\" means "
        "the agreement formed under section 19; \"Contract Price\" means the total price payable "
        "under the Contract; \"Delivery Date\" means the date for delivery of Goods in the agreed "
        "delivery programme; \"Goods\" means the pumps, spare parts and associated equipment; "
        "\"Intellectual Property Rights\" means patents, rights in designs, copyright, database "
        "rights, trade marks, know-how and all similar rights anywhere in the world; "
        "\"Services\" means installation, commissioning, training and maintenance support; "
        "\"Specification\" means Appendix B; \"Working Day\" means a day other than a Saturday, "
        "Sunday or public holiday in England.",
        "18.2 Headings do not affect interpretation. \"Including\" means including without "
        "limitation.",
    ]),
    (19, "Contract formation and order of precedence", "C", [
        "19.1 The Contract is formed when both parties sign the contract agreement following "
        "Volta's letter of award.",
        "19.2 The Contract consists of these conditions, the Specification and the Supplier's "
        "tender. If they conflict, they take precedence in that order.",
        "19.3 No terms put forward by the Supplier, whether in its tender, an order acknowledgement "
        "or a delivery note, apply unless Volta agrees to them in writing.",
    ]),
    (20, "Price, invoicing and payment", "C", [
        "20.1 The Contract Price is fixed as set out in the Pricing Schedule, subject only to "
        "indexation under section 7.2 and to Variations agreed under section 27.",
        "20.2 The Supplier may invoice for Goods on Acceptance and for maintenance support "
        "quarterly in arrears.",
        "20.3 Volta will pay valid, undisputed invoices within 30 days of receipt.",
        "20.4 Volta may set off against any sum due to the Supplier any amount the Supplier owes "
        "to Volta under the Contract.",
    ]),
    (21, "Liability", "C", [
        "21.1 The Supplier's liability under or in connection with the Contract, whether in "
        "contract, tort (including negligence), breach of statutory duty or otherwise, shall not "
        "be limited, except as expressly stated in clause 21.5.",
        "21.2 Volta's total liability under or in connection with the Contract shall not exceed "
        "ten per cent (10%) of the Contract Price.",
        "21.3 The Supplier shall be liable for all indirect and consequential loss suffered by "
        "Volta, including loss of revenue, loss of use of rolling stock or depot facilities, the "
        "costs of replacement services and any compensation or penalties payable by Volta to train "
        "operators or other third parties, without limit.",
        "21.4 Nothing in the Contract limits or excludes either party's liability for death or "
        "personal injury caused by negligence, or for fraud.",
        "21.5 Liquidated damages. If the Supplier fails to deliver any Goods by the relevant "
        "Delivery Date, it shall pay Volta liquidated damages of one per cent (1%) of the price of "
        "the delayed Goods for each week or part week of delay, up to a maximum of twenty per cent "
        "(20%) of the Contract Price. Liquidated damages are without prejudice to Volta's other "
        "rights and remedies, including its right to terminate under section 34.",
        "21.6 The parties agree that the liquidated damages are proportionate to Volta's "
        "legitimate interest in the timely delivery of the Goods and are not a penalty.",
    ]),
    (22, "Indemnities", "C", [
        "22.1 The Supplier shall indemnify Volta against all claims, losses and costs arising "
        "from death or personal injury, or loss of or damage to property, caused by the "
        "Supplier's negligence or breach of the Contract.",
        "22.2 The Supplier shall indemnify Volta against any fine or penalty imposed on Volta "
        "because the Supplier has breached health and safety or environmental law.",
        "22.3 Volta shall notify the Supplier promptly of any claim covered by this section and "
        "allow the Supplier to conduct the defence, subject to Volta's reasonable requirements.",
    ]),
    (23, "Insurance", "C", [
        "23.1 The Supplier shall maintain, with reputable insurers, for the duration of the "
        "Contract and for six years after it ends: public and products liability insurance of not "
        "less than GBP 10 million for each and every claim; and employer's liability insurance as "
        "required by law.",
        "23.2 The Supplier shall provide evidence of cover on request and shall notify Volta of "
        "any cancellation or material change.",
        "23.3 The insurances do not limit the Supplier's liability under the Contract.",
    ]),
    (24, "Performance security", "C", [
        "24.1 Volta may require the Supplier to provide, within 20 Working Days of contract award, "
        "a performance bond of up to ten per cent (10%) of the Contract Price from a bank "
        "acceptable to Volta.",
        "24.2 The cost of the bond must be included in the tender price.",
        "24.3 The bond expires on the issue of the last acceptance certificate.",
    ]),
    (25, "Delivery, title and risk", "C", [
        "25.1 The Supplier shall deliver the Goods to the depot named in the delivery programme on "
        "the Delivery Date, during the depot's normal receiving hours.",
        "25.2 Title to the Goods passes to Volta on delivery or on payment, whichever is earlier. "
        "Risk passes on Acceptance.",
        "25.3 Each delivery must be accompanied by a delivery note stating the Contract number, "
        "the serial numbers of the Goods and the test certificates.",
    ]),
    (26, "Inspection, testing and rejection", "C", [
        "26.1 Volta may inspect and test the Goods at any time before Acceptance.",
        "26.2 Volta may reject any Goods that do not conform to the Contract. The Supplier shall "
        "collect rejected Goods at its own cost and replace them within ten Working Days.",
        "26.3 Inspection, testing or payment by Volta does not mean that Volta accepts that the "
        "Goods conform to the Contract.",
    ]),
    (27, "Variations", "C", [
        "27.1 Volta may instruct a change to the Goods or Services by written variation order.",
        "27.2 The Supplier shall, within ten Working Days, state the effect of the variation on "
        "the Contract Price and the delivery programme, using the rates in the Pricing Schedule "
        "where they apply.",
        "27.3 No variation is binding unless it is agreed in writing by both parties.",
    ]),
    (28, "Spare parts and obsolescence", "C", [
        "28.1 The Supplier shall make spare parts for the Goods available for at least fifteen "
        "years from Acceptance at prices no higher than its then current list prices.",
        "28.2 The Supplier shall give Volta at least twelve months' notice before any spare part "
        "becomes obsolete and offer a last-time buy or a compatible replacement.",
    ]),
    (29, "Intellectual property and warranty", "C", [
        "29.1 In this section, \"Background IP\" means Intellectual Property Rights owned by or "
        "licensed to the Supplier before the Commencement Date or developed independently of the "
        "Contract, and \"Deliverables\" means the Goods, drawings, software, manuals and other "
        "materials supplied under the Contract.",
        "29.2 The Supplier assigns to Volta, with full title guarantee and free from all "
        "third-party rights, all Intellectual Property Rights in the Deliverables, including any "
        "Background IP incorporated in or necessary for the use, maintenance, repair or "
        "modification of the Goods. The assignment takes effect on creation or, for existing "
        "rights, on the Commencement Date.",
        "29.3 The Supplier shall obtain waivers of all moral rights in the Deliverables.",
        "29.4 The Supplier shall indemnify Volta against all claims that the Deliverables infringe "
        "the Intellectual Property Rights of any third party.",
        "29.5 The Supplier warrants that the Goods will (a) conform to the Specification; (b) be "
        "free from defects in design, materials and workmanship; (c) be fit for the purposes made "
        "known in the tender documents; and (d) comply with all applicable laws and railway "
        "industry standards.",
        "29.6 The warranty in clause 29.5 applies for thirty-six (36) months from the date of "
        "Acceptance (the \"Warranty Period\").",
        "29.7 The Supplier shall remedy any defect notified during the Warranty Period within five "
        "Working Days at its own cost. The Warranty Period restarts for any repaired or replaced "
        "part. If the Supplier fails to remedy a defect, Volta may do so at the Supplier's cost.",
    ]),
    (30, "Confidentiality", "C", [
        "30.1 Each party shall keep confidential all information it receives from the other "
        "under the Contract and use it only to perform the Contract.",
        "30.2 This section does not apply to information that is public, already known to the "
        "recipient, or required to be disclosed by law.",
        "30.3 This section continues for five years after the Contract ends.",
    ]),
    (31, "Data protection and cyber security", "C", [
        "31.1 Each party shall comply with data protection law. The Contract is not expected to "
        "involve the processing of personal data on Volta's behalf; if it does, the parties will "
        "agree a data processing agreement.",
        "31.2 Equipment connected to Volta's depot management system must comply with Volta's "
        "operational technology security standard, including network segregation, unique "
        "credentials and signed firmware updates.",
        "31.3 The Supplier shall notify Volta within 24 hours of becoming aware of any security "
        "incident affecting the Goods or Volta's systems.",
    ]),
    (32, "Compliance with laws, anti-bribery and modern slavery", "C", [
        "32.1 The Supplier shall comply with all applicable laws, including the Bribery Act 2010 "
        "and the Modern Slavery Act 2015, and shall have adequate procedures to prevent bribery "
        "and slavery in its business and supply chain.",
        "32.2 The Supplier shall notify Volta promptly of any breach of this section and keep "
        "records that show its compliance.",
    ]),
    (33, "Force majeure", "C", [
        "33.1 Neither party is liable for a delay or failure caused by an event beyond its "
        "reasonable control, provided it notifies the other party promptly and takes all "
        "reasonable steps to mitigate.",
        "33.2 Shortages of labour or materials, and failures of the Supplier's subcontractors, "
        "are not force majeure events unless they are themselves caused by such an event.",
        "33.3 If a force majeure event continues for more than 60 days, either party may "
        "terminate the Contract by notice.",
    ]),
    (34, "Termination", "C", [
        "34.1 Volta may terminate the Contract for convenience on 30 days' notice. The Supplier "
        "will be paid for Goods delivered and Services performed up to termination.",
        "34.2 Either party may terminate the Contract by notice if the other commits a material "
        "breach that is not remedied within 20 Working Days of notice, or becomes insolvent.",
        "34.3 Volta may terminate the Contract by notice if the maximum liquidated damages under "
        "clause 21.5 become payable.",
        "34.4 Termination does not affect accrued rights or any provision intended to survive.",
    ]),
    (35, "Dispute resolution", "C", [
        "35.1 The parties shall first try to resolve any dispute by referring it to their "
        "contract managers and then, if not resolved within 10 Working Days, to a director of each "
        "party.",
        "35.2 If the dispute is not resolved within a further 20 Working Days, either party may "
        "propose mediation under a recognised model procedure.",
        "35.3 Nothing in this section prevents either party from applying to the courts for "
        "urgent relief.",
    ]),
    (36, "General", "C", [
        "36.1 The Supplier may not assign or subcontract the Contract without Volta's prior "
        "written consent. Volta may assign the Contract to any successor to its depot "
        "operations.",
        "36.2 The Contract is the entire agreement between the parties about its subject matter. "
        "No waiver is effective unless it is in writing.",
        "36.3 A person who is not a party has no right under the Contracts (Rights of Third "
        "Parties) Act 1999 to enforce any term of the Contract.",
        "36.4 The Contract is governed by the law of England and Wales, and the courts of England "
        "and Wales have exclusive jurisdiction.",
    ]),
]

APPENDICES = [
    ("Appendix A", "Form of Tender and Pricing Schedule", [
        "To: Volta Rail Ltd. We, the tenderer named below, offer to supply the Goods and Services "
        "described in invitation to tender " + ITT_REF + " on the conditions of contract in Part "
        "C, as qualified only by the exceptions listed in our Appendix D, for the prices below.",
        ("table", ["Item", "Description", "Qty", "Unit price (GBP)", "Total (GBP)"], [
            ["1", "Pump type D1 submersible drainage, installed", "28", "", ""],
            ["2", "Pump type W2 wash-plant recycling, installed", "12", "", ""],
            ["3", "Pump type C3 cooling-water circulation, installed", "16", "", ""],
            ["4", "Pump type S4 sump, installed", "8", "", ""],
            ["5", "Recommended spares holding, per depot", "4", "", ""],
            ["6", "Maintenance support, per depot per year (5 years)", "20", "", ""],
        ]),
        "Our tender remains valid for 120 days from the tender return deadline.",
        "Tenderer: ______________________   Signed: ______________________   Date: __________",
    ]),
    ("Appendix D", "Compliance and Exceptions Form", [
        "List every exception to the conditions of contract in Part C. Exceptions that are not "
        "listed here are treated as withdrawn (section 8.2).",
        ("table", ["No.", "Section and clause", "Exception", "Reason", "Proposed wording"], [
            ["1", "", "", "", ""],
            ["2", "", "", "", ""],
            ["3", "", "", "", ""],
            ["4", "", "", "", ""],
            ["5", "", "", "", ""],
            ["6", "", "", "", ""],
        ]),
        "We confirm that, apart from the exceptions listed above, we accept the conditions of "
        "contract in Part C in full.",
        "Tenderer: ______________________   Signed: ______________________   Date: __________",
    ]),
]
