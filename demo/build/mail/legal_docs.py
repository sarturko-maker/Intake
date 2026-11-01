"""The .docx attachments of the demo corpus (python-docx 1.2, via docxkit).

Everything here is invented: Kestrel Engineering Ltd, Kestrel Pumpen GmbH, Acme Automotive
GmbH, Halden Water Ltd, Meridian Bank plc, Rio Bombas Distribuicao Ltda and every person.
Numbers follow the demo storyline (BUILD-SPEC section G):

- Acme NDA v1 (Acme paper): 5-year term, German law. Kestrel mark-up: 3 years (5 for trade
  secrets), English law; tracked changes and comments by Alex Morgan.
- Acme MSA clause 12:
    v1      general cap 200% of Annual Fees; data breach unlimited; liable for indirect loss.
    markup  (Kestrel on v1) cap 100%; data breach super-cap 2x Annual Fees; mutual exclusion
            of indirect loss; a comment with the reason on each change.
    v2      cap 150%; data breach unlimited; indirect loss excluded but production stoppage
            from defective Products recoverable within the cap.
    v3      cap 150%; data breach unlimited only for gross negligence or wilful misconduct,
            otherwise within the 150% cap.
- Halden Water NDA: one-way in Halden's favour, 5-year term, clause 9 two-year non-compete
  in Halden's region.
- Meridian Bank Schedule 7: data breach cap 3x Annual Charges; regulatory fines caused by
  the supplier's default uncapped.
- Rio Bombas draft: exclusive for Brazil, minimum purchase targets, Brazilian law.
"""

import datetime as dt

from docxkit import B, Del, Doc, I, Ins

UTC = dt.timezone.utc


def _t(y, mo, d, h=9, mi=0):
    return dt.datetime(y, mo, d, h, mi, tzinfo=UTC)


def chg(old, new, mode):
    """A changed passage: original text, tracked change, or the accepted text."""
    if mode == "orig":
        return [old] if old else []
    if mode == "final":
        return [new] if new else []
    out = []
    if old:
        out.append(Del(old))
    if new:
        out.append(Ins(new))
    return out


def flat(segments):
    """Plain text of a segment list (deleted text dropped)."""
    out = []
    for s in segments:
        if isinstance(s, Del):
            continue
        out.append(s.text if hasattr(s, "text") else str(s))
    return "".join(out)


# ======================================================================= Acme NDA

def nda_content(mode):
    """Acme's mutual NDA. mode: orig (Acme v1), markup (Kestrel's tracked changes), final
    (as signed). Returns a list of (kind, segments, comment)."""
    c = []

    def h(text):
        c.append(("h", [text], None))

    def p(segs, comment=None):
        c.append(("p", segs if isinstance(segs, list) else [segs], comment))

    p("This Mutual Non-Disclosure Agreement (the \"Agreement\") is made between:")
    p([B("Acme Automotive GmbH"), ", Stuttgart, Germany (\"Acme\"); and"])
    p([B("Kestrel Engineering Ltd"), ", Sheffield, United Kingdom (\"Kestrel\"),"])
    p("each a \"Party\" and together the \"Parties\".")
    h("Background")
    p("(A) The Parties wish to discuss a possible supply relationship for process and "
      "cooling-water pumps, spare parts and a remote condition monitoring service for Acme's "
      "production sites (the \"Purpose\").")
    p("(B) In the course of these discussions each Party may disclose Confidential Information "
      "to the other. The Parties therefore agree as follows.")
    h("1. Definitions")
    p("1.1 \"Confidential Information\" means all information, in any form, that a Party (the "
      "\"Disclosing Party\") discloses to the other Party (the \"Receiving Party\") in connection "
      "with the Purpose, including technical data, drawings, specifications, prices, volumes, "
      "plant layouts and business plans, which is marked as confidential or which a reasonable "
      "person would understand to be confidential.")
    p("1.2 \"Affiliate\" means any company that controls, is controlled by or is under common "
      "control with a Party, where control means holding more than 50% of the voting rights.")
    p("1.3 \"Effective Date\" means the date of the last signature below.")
    h("2. Obligations of confidentiality")
    p("2.1 The Receiving Party shall (a) keep the Confidential Information strictly "
      "confidential; (b) use it only for the Purpose; and (c) protect it with at least the same "
      "degree of care it uses for its own confidential information, and in any case with "
      "reasonable care.")
    p("2.2 The Receiving Party may disclose Confidential Information only to its and its "
      "Affiliates' employees, officers and professional advisers who need to know it for the "
      "Purpose and who are bound by obligations of confidentiality no less strict than those in "
      "this Agreement. The Receiving Party is responsible for any breach by those persons.")
    h("3. Exceptions")
    p("3.1 Clause 2 does not apply to information which the Receiving Party can show (a) is or "
      "becomes public other than through a breach of this Agreement; (b) was lawfully in its "
      "possession before disclosure; (c) is lawfully received from a third party without an "
      "obligation of confidentiality; or (d) is developed independently without use of the "
      "Confidential Information.")
    p("3.2 The Receiving Party may disclose Confidential Information if required by law, a "
      "court or a competent authority, provided that, where lawful, it gives the Disclosing "
      "Party prompt notice and limits the disclosure to what is required.")
    h("4. Return and destruction")
    p("4.1 On the Disclosing Party's written request, the Receiving Party shall promptly return "
      "or destroy all Confidential Information and confirm in writing that it has done so. The "
      "Receiving Party may keep copies required by law or held in routine electronic back-ups, "
      "which remain subject to this Agreement.")
    h("5. No licence and no warranty")
    p("5.1 All Confidential Information remains the property of the Disclosing Party. No licence "
      "under any patent, copyright or other intellectual property right is granted by this "
      "Agreement.")
    p("5.2 Confidential Information is provided \"as is\". The Disclosing Party gives no "
      "warranty as to its accuracy or completeness.")
    h("6. No obligation to proceed")
    p("6.1 This Agreement does not oblige either Party to enter into any further agreement or to "
      "continue discussions. Any supply relationship will be governed by a separate written "
      "agreement.")
    h("7. Data protection")
    p("7.1 If personal data is exchanged under this Agreement, each Party shall comply with "
      "applicable data protection law, including the General Data Protection Regulation (EU) "
      "2016/679 and the UK GDPR.")
    h("8. Term")
    p(["8.1 This Agreement and the obligations of confidentiality under it shall continue for "]
      + chg("five (5)", "three (3)", mode)
      + [" years from the Effective Date"]
      + chg("", ", save that the obligations in respect of any Confidential Information that "
                "constitutes a trade secret shall continue for five (5) years from the Effective "
                "Date", mode)
      + ["."],
      comment="Kestrel's standard term for mutual NDAs is three years, with five years for "
              "trade secrets. Five years for all information is longer than these discussions "
              "need.")
    p("8.2 Either Party may end the discussions at any time by written notice. The obligations in "
      "this Agreement continue for the period in clause 8.1 for Confidential Information "
      "disclosed before that notice.")
    h("9. Remedies")
    p("9.1 Each Party acknowledges that damages alone may not be an adequate remedy for a breach "
      "of this Agreement and that the Disclosing Party may seek injunctive relief in addition to "
      "any other remedy.")
    h("10. Assignment")
    p("10.1 Neither Party may assign this Agreement without the prior written consent of the "
      "other Party.")
    h("11. Entire agreement and amendments")
    p("11.1 This Agreement is the entire agreement between the Parties about its subject matter. "
      "Any amendment must be in writing and signed by both Parties.")
    h("12. Governing law and jurisdiction")
    p(["12.1 This Agreement shall be governed by the laws of "]
      + chg("the Federal Republic of Germany, excluding the UN Convention on Contracts for the "
            "International Sale of Goods", "England and Wales", mode)
      + ["."],
      comment="Kestrel's NDAs are governed by English law. As this Agreement is short and mutual, "
              "we propose English law and the English courts.")
    p(["12.2 The courts of "]
      + chg("Stuttgart, Germany", "England and Wales", mode)
      + [" shall have exclusive jurisdiction over any dispute arising out of or in connection "
         "with this Agreement."],
      comment="Follows the change to clause 12.1.")
    return c


def _nda_doc(mode, path):
    if mode == "orig":
        doc = Doc("Mutual Non-Disclosure Agreement", "Felix Brandt", _t(2026, 10, 8, 14, 20),
                  _t(2026, 10, 9, 7, 55), header="Acme Automotive GmbH | Mutual NDA | Draft 09.10.2026",
                  footer="Acme Automotive GmbH - Confidential", revision=4)
    else:
        doc = Doc("Mutual Non-Disclosure Agreement", "Felix Brandt", _t(2026, 10, 8, 14, 20),
                  _t(2026, 10, 12, 14, 31), header="Acme Automotive GmbH | Mutual NDA | Draft 09.10.2026"
                  " | Kestrel comments 12.10.2026",
                  footer="Acme Automotive GmbH - Confidential", change_author="Alex Morgan",
                  change_date=_t(2026, 10, 12, 14, 5), revision=6)
    doc.title("MUTUAL NON-DISCLOSURE AGREEMENT")
    for kind, segs, comment in nda_content(mode):
        if kind == "h":
            doc.heading(segs[0], 2)
        else:
            doc.para(*segs, comment=comment if mode == "markup" else None,
                     comment_initials="AM")
    doc.spacer()
    doc.para(B("Signed by the Parties:"))
    doc.signature_block(
        ["For Acme Automotive GmbH", "Name:", "Title:", "Date:", "Signature:"],
        ["For Kestrel Engineering Ltd", "Name:", "Title:", "Date:", "Signature:"])
    return doc.save(path)


def build_acme_nda_v1(path):
    return _nda_doc("orig", path)


def build_acme_nda_kestrel(path):
    return _nda_doc("markup", path)


def nda_final_paragraphs():
    """[(kind, text)] of the NDA as signed (Kestrel's changes accepted), for the signed PDF."""
    return [(kind, flat(segs)) for kind, segs, _ in nda_content("final")]


# ======================================================================= Acme MSA

MSA_HEADER = {
    "v1": "Acme Automotive GmbH | Master Supply Agreement | Draft v1 | 15.10.2026",
    "markup": "Acme Automotive GmbH | Master Supply Agreement | Draft v1 | 15.10.2026 | "
              "Kestrel comments on clause 12, 16.10.2026",
    "v2": "Acme Automotive GmbH | Master Supply Agreement | Draft v2 | 19.10.2026",
    "v3": "Acme Automotive GmbH | Master Supply Agreement | Draft v3 | 27.10.2026",
}


def msa_clause12(version):
    """Clause 12 for v1, markup (Kestrel's tracked changes on v1), v2 and v3.
    Returns [(segments, comment)]."""
    mode = "markup" if version == "markup" else "orig"
    rows = []
    rows.append((["12.1 Supplier is liable for breach of its obligations in accordance with the "
                  "statutory provisions, except as set out in this clause 12."], None))
    if version in ("v1", "markup"):
        cap = chg("two hundred per cent (200%)", "one hundred per cent (100%)", mode)
    else:
        cap = ["one hundred and fifty per cent (150%)"]
    rows.append((["12.2 Supplier's aggregate liability under or in connection with this "
                  "Agreement in any Contract Year is limited to "] + cap + [" of the Annual Fees."],
                 "Kestrel's general cap is 100% of the Annual Fees. This reflects the value of the "
                 "supply and is in line with market practice for process equipment of this kind."))
    rows.append((["12.3 The limitation in clause 12.2 does not apply to liability (a) for injury "
                  "to life, body or health; (b) for intent or gross negligence; (c) under the German "
                  "Product Liability Act (Produkthaftungsgesetz); or (d) under any guarantee given "
                  "by Supplier."], None))
    lead = "12.4 Supplier's liability for any Data Breach, and for any breach of clause 10 " \
           "(Data Protection and Information Security), "
    if version in ("v1", "markup", "v2"):
        tail = chg("is unlimited and does not count towards the limit in clause 12.2",
                   "is limited in aggregate to two (2) times the Annual Fees. This limit is "
                   "separate from, and in addition to, the limit in clause 12.2", mode)
        rows.append(([lead] + tail + ["."],
                     "Kestrel cannot accept unlimited liability for data breach. It is not "
                     "insurable and could exceed the value of this Agreement many times over. We "
                     "propose a separate cap of two times the Annual Fees for data breach, in "
                     "addition to the general cap."))
    else:
        rows.append(([lead + "is unlimited where the Data Breach or breach was caused by "
                      "Supplier's gross negligence or wilful misconduct. In all other cases it is "
                      "subject to the limit in clause 12.2."], None))
    if version in ("v1", "markup"):
        rows.append((["12.5 "] + chg("Supplier is liable for", "Neither party is liable to the "
                                     "other for any", mode)
                     + [" indirect and consequential loss, including loss of production, costs of "
                        "production stoppage and loss of profit"]
                     + chg("", ", except where clause 12.3 applies", mode) + ["."],
                     "We have replaced liability for indirect loss with a mutual exclusion. Loss of "
                     "production at Acme's plants could far exceed the contract value and cannot be "
                     "insured by an equipment supplier at a reasonable cost. The carve-outs in "
                     "clause 12.3 still apply."))
    else:
        rows.append((["12.5 Neither party is liable to the other for indirect or consequential "
                      "loss, including loss of profit, except where clause 12.3 applies. Costs of "
                      "production stoppage caused by defective Products are direct loss and are "
                      "recoverable within the limit in clause 12.2."], None))
    rows.append((["12.6 Customer's liability is governed by the statutory provisions."], None))
    rows.append((["12.7 The limitation period for claims under this clause 12 is the statutory "
                  "period, save as set out in clause 7.2."], None))
    return rows


def msa_sections(version):
    """The MSA as [(heading, [paragraph or ('c12', ...)])]."""
    s = []
    s.append(("1. Definitions", [
        "1.1 \"Agreement\" means this Master Supply Agreement including its Annexes.",
        "1.2 \"Annual Fees\" means the total fees paid or payable by Customer to Supplier under "
        "this Agreement in the twelve (12) months before the event giving rise to the claim.",
        "1.3 \"Contract Year\" means each period of twelve (12) months starting on the Effective "
        "Date or on an anniversary of it.",
        "1.4 \"Customer Data\" means all data, including personal data and production data, that "
        "Supplier or the Monitoring Service receives from or processes on behalf of Customer.",
        "1.5 \"Data Breach\" means any accidental or unlawful destruction, loss, alteration or "
        "unauthorised disclosure of, or access to, Customer Data, and any unauthorised access to "
        "Customer's networks or systems, in each case caused by Supplier, its subcontractors or "
        "the Monitoring Service.",
        "1.6 \"Monitoring Service\" means Supplier's remote condition monitoring service "
        "described in Annex 3, including the gateways installed at Customer's sites.",
        "1.7 \"Order\" means a purchase order issued by Customer under this Agreement.",
        "1.8 \"Products\" means the pumps, spare parts and accessories described in Annex 1.",
    ]))
    s.append(("2. Scope", [
        "2.1 This Agreement sets out the terms on which Supplier supplies Products and the "
        "Monitoring Service to Customer and its Affiliates. It does not oblige Customer to "
        "purchase any minimum quantity.",
        "2.2 Supplier's general terms and conditions do not apply, even if referred to in an "
        "order confirmation or delivery note.",
    ]))
    s.append(("3. Orders and forecasts", [
        "3.1 Customer places Orders through its purchasing system. An Order is binding unless "
        "Supplier rejects it in writing within three (3) working days of receipt.",
        "3.2 Customer will provide a non-binding rolling twelve-month forecast each quarter.",
    ]))
    s.append(("4. Prices and payment", [
        "4.1 Prices are set out in Annex 2 and are fixed until 31 December 2027. Prices are DAP "
        "Customer's site (Incoterms 2020).",
        "4.2 Supplier shall invoice on delivery. Customer shall pay within sixty (60) days of "
        "receipt of a correct invoice.",
        "4.3 Supplier grants Customer an annual volume rebate as set out in Annex 2, settled by "
        "credit note within thirty (30) days of the end of each Contract Year.",
    ]))
    s.append(("5. Delivery", [
        "5.1 Delivery dates in Orders are binding. Supplier shall inform Customer immediately of "
        "any expected delay.",
        "5.2 For each full week of delay Customer may claim liquidated damages of 0.5% of the "
        "value of the delayed delivery, up to a maximum of 5%. Customer's right to claim further "
        "damages is not affected; liquidated damages paid are credited against them.",
    ]))
    s.append(("6. Quality and inspection", [
        "6.1 Supplier shall maintain a quality management system certified to ISO 9001.",
        "6.2 Customer's duty to inspect and to give notice of defects under section 377 of the "
        "German Commercial Code (HGB) is limited to defects that are apparent on a visual check of "
        "the delivery documents and packaging. Other defects may be notified within ten (10) "
        "working days of discovery.",
    ]))
    s.append(("7. Warranty", [
        "7.1 Supplier warrants that the Products are free from defects in design, material and "
        "workmanship, conform to the specifications in Annex 1 and are fit for the intended use at "
        "Customer's sites.",
        "7.2 The warranty period is thirty-six (36) months from commissioning, but not more than "
        "forty-two (42) months from delivery.",
        "7.3 Supplier shall remedy defects by repair or replacement within five (5) working days. "
        "In urgent cases Customer may remedy defects itself at Supplier's cost.",
    ]))
    s.append(("8. Intellectual property", [
        "8.1 Supplier retains all intellectual property rights in the Products and the "
        "Monitoring Service. Customer receives a non-exclusive, royalty-free right to use the "
        "Products and the Monitoring Service for its business.",
        "8.2 Supplier shall indemnify Customer against claims of third parties that the Products "
        "or the Monitoring Service infringe their intellectual property rights.",
    ]))
    s.append(("9. Confidentiality", [
        "9.1 The mutual non-disclosure agreement between the parties dated 14 October 2026 "
        "continues to apply and forms part of this Agreement.",
    ]))
    s.append(("10. Data protection and information security", [
        "10.1 Supplier shall process personal data only on Customer's documented instructions "
        "and in accordance with the data processing agreement in Annex 4.",
        "10.2 Supplier shall maintain information security measures at least equal to ISO/IEC "
        "27001 and Customer's supplier security requirements, and shall complete Customer's "
        "supplier information security questionnaire before the Monitoring Service is connected "
        "to Customer's networks.",
        "10.3 Supplier shall notify Customer of any Data Breach without undue delay and in any "
        "case within twenty-four (24) hours of becoming aware of it.",
        "10.4 Customer may audit Supplier's compliance with this clause 10 once a year on thirty "
        "(30) days' notice.",
    ]))
    s.append(("11. Insurance", [
        "11.1 Supplier shall maintain, with reputable insurers, product liability insurance of at "
        "least EUR 10 million per claim and cyber insurance of at least EUR 5 million per claim, "
        "and shall provide certificates on request.",
    ]))
    s.append(("12. Liability", ["c12"]))
    s.append(("13. Term and termination", [
        "13.1 This Agreement starts on the date of the last signature (the \"Effective Date\") and "
        "continues for three (3) years. It then renews for successive periods of one (1) year "
        "unless either party gives six (6) months' notice before the end of the current period.",
        "13.2 Either party may terminate this Agreement for good cause (aus wichtigem Grund) with "
        "immediate effect.",
        "13.3 Customer may terminate this Agreement for convenience on six (6) months' notice.",
    ]))
    s.append(("14. Force majeure", [
        "14.1 Neither party is liable for a failure to perform caused by events beyond its "
        "reasonable control, such as natural disasters, war, epidemics or government action, "
        "provided that it notifies the other party promptly and uses reasonable efforts to "
        "mitigate the effects. Strikes at Supplier's own premises are not force majeure.",
    ]))
    s.append(("15. General", [
        "15.1 Amendments must be in writing. This also applies to any waiver of this "
        "written-form requirement.",
        "15.2 If any provision is invalid, the remaining provisions remain in force.",
        "15.3 Supplier may not assign this Agreement or subcontract its obligations without "
        "Customer's prior written consent.",
    ]))
    s.append(("16. Governing law and jurisdiction", [
        "16.1 This Agreement is governed by the laws of the Federal Republic of Germany, excluding "
        "the UN Convention on Contracts for the International Sale of Goods (CISG).",
        "16.2 The courts of Stuttgart, Germany, have exclusive jurisdiction.",
    ]))
    return s


def build_msa(version, path):
    """version: v1 | markup | v2 | v3."""
    dates = {
        "v1": (_t(2026, 10, 14, 13, 10), _t(2026, 10, 15, 6, 30), 7),
        "markup": (_t(2026, 10, 14, 13, 10), _t(2026, 10, 16, 9, 22), 9),
        "v2": (_t(2026, 10, 14, 13, 10), _t(2026, 10, 19, 6, 48), 12),
        "v3": (_t(2026, 10, 14, 13, 10), _t(2026, 10, 27, 9, 14), 15),
    }
    created, modified, rev = dates[version]
    doc = Doc("Master Supply Agreement", "Felix Brandt", created, modified,
              header=MSA_HEADER[version], footer="Acme Automotive GmbH - Confidential",
              change_author="Alex Morgan" if version == "markup" else "Felix Brandt",
              change_date=_t(2026, 10, 16, 9, 10) if version == "markup" else modified,
              revision=rev)
    doc.title("MASTER SUPPLY AGREEMENT")
    doc.para("between", align="center")
    doc.para(B("Acme Automotive GmbH"), ", Stuttgart, Germany (\"Customer\")", align="center")
    doc.para("and", align="center")
    doc.para(B("Kestrel Engineering Ltd"), ", Sheffield, United Kingdom (\"Supplier\")",
             align="center")
    label = {"v1": "Draft v1 of 15 October 2026 - for discussion",
             "markup": "Draft v1 of 15 October 2026 - with Kestrel's comments on clause 12 "
                       "(16 October 2026)",
             "v2": "Draft v2 of 19 October 2026 - Acme's response to Kestrel's comments of "
                   "16 October 2026",
             "v3": "Draft v3 of 27 October 2026 - revised clause 12"}[version]
    doc.para(I(label), align="center")
    for heading, paras in msa_sections(version):
        doc.heading(heading, 2)
        for para in paras:
            if para == "c12":
                for segs, comment in msa_clause12(version):
                    doc.para(*segs, comment=comment if (version == "markup" and comment) else None,
                             comment_initials="AM")
            else:
                doc.para(para)
    doc.heading("Annexes", 2)
    for a in ("Annex 1 - Products and specifications", "Annex 2 - Prices and volume rebate",
              "Annex 3 - Monitoring Service description", "Annex 4 - Data processing agreement"):
        doc.bullet(a)
    doc.para(I("The Annexes will be provided with the next draft."))
    doc.spacer()
    doc.signature_block(
        ["For Acme Automotive GmbH", "Name:", "Title:", "Date:", "Signature:"],
        ["For Kestrel Engineering Ltd", "Name:", "Title:", "Date:", "Signature:"])
    return doc.save(path)


def msa_clause12_text(version):
    """Clause 12 as plain text with changes applied (for tests and email summaries)."""
    rows = msa_clause12("v1" if version == "markup" else version)
    if version == "markup":
        rows = [(segs, c) for segs, c in msa_clause12("markup")]
    return "\n".join(flat(segs) for segs, _ in rows)


# ======================================================================= Halden Water NDA

def build_halden_nda(path):
    doc = Doc("Confidentiality Agreement - Thornbury Pumping Station", "Mark Ostrow",
              _t(2026, 3, 2, 10, 0), _t(2026, 10, 20, 13, 30),
              header="Halden Water Ltd | Confidentiality Agreement | Template CA-07 rev 3",
              footer="Halden Water Ltd - Commercial in confidence", revision=11)
    doc.title("CONFIDENTIALITY AGREEMENT",
              "Thornbury Pumping Station Upgrade - Early Supplier Engagement")
    doc.para("This Agreement is dated ______________________ 2026.")
    doc.heading("Parties", 2)
    doc.para("(1) ", B("Halden Water Ltd"), ", a company registered in England and Wales (the "
             "\"Company\"); and")
    doc.para("(2) ", B("Kestrel Engineering Ltd"), ", a company registered in England and Wales "
             "(the \"Recipient\").")
    doc.heading("Background", 2)
    doc.para("(A) The Company is planning the upgrade of its Thornbury pumping station (the "
             "\"Project\") and intends to engage potential suppliers of pumping equipment before "
             "the formal tender.")
    doc.para("(B) The Company is willing to disclose Confidential Information to the Recipient for "
             "the Purpose on the terms of this Agreement. The Recipient is not disclosing any "
             "information under this Agreement.")
    doc.heading("1. Definitions", 2)
    doc.para("1.1 In this Agreement:")
    doc.para("\"Confidential Information\" means all information relating to the Project or to "
             "the Company's business, assets, network or customers that the Company or its "
             "advisers disclose to the Recipient, before or after the date of this Agreement and "
             "in any form, including hydraulic models, site surveys, asset data, drawings, "
             "security arrangements and commercial information;", indent=0.8)
    doc.para("\"Purpose\" means the Recipient's evaluation of, and participation in, the early "
             "supplier engagement for the Project;", indent=0.8)
    doc.para("\"Region\" means the area in which the Company provides water or wastewater "
             "services from time to time, as described in the Schedule;", indent=0.8)
    doc.para("\"Representatives\" means the Recipient's employees, officers and professional "
             "advisers.", indent=0.8)
    doc.heading("2. Confidentiality undertakings", 2)
    doc.para("2.1 The Recipient shall keep the Confidential Information secret and confidential, "
             "use it only for the Purpose, and not disclose it to any person except those of its "
             "Representatives who need to know it for the Purpose.")
    doc.para("2.2 The Recipient shall ensure that its Representatives comply with this Agreement "
             "and is liable for their acts and omissions as if they were its own.")
    doc.para("2.3 The Recipient shall protect the Confidential Information with security measures "
             "no less strict than the Company's Security Requirements for Suppliers, as notified "
             "to the Recipient from time to time.")
    doc.heading("3. Exceptions", 2)
    doc.para("3.1 Clause 2 does not apply to information that (a) is or becomes generally "
             "available to the public other than through a breach of this Agreement; (b) the "
             "Recipient can show was lawfully in its possession before the Company disclosed it; "
             "or (c) the Recipient is required to disclose by law or by a court or regulator, "
             "provided it first notifies the Company where lawful.")
    doc.heading("4. Return and destruction", 2)
    doc.para("4.1 Within ten (10) days of the Company's request, the Recipient shall return or "
             "destroy all Confidential Information and certify in writing that it has done so.")
    doc.heading("5. No licence, warranty or obligation", 2)
    doc.para("5.1 No licence or other right is granted in the Confidential Information. The "
             "Company makes no warranty as to its accuracy or completeness. Neither party is "
             "obliged to enter into any further agreement.")
    doc.heading("6. Announcements", 2)
    doc.para("6.1 The Recipient shall not make any announcement about the Project or its "
             "involvement in it without the Company's prior written consent.")
    doc.heading("7. Duration", 2)
    doc.para("7.1 This Agreement and the obligations in it continue for five (5) years from the "
             "date of this Agreement.")
    doc.heading("8. Indemnity and remedies", 2)
    doc.para("8.1 The Recipient shall indemnify the Company against all losses, costs and "
             "expenses (including legal fees) arising from any breach of this Agreement by the "
             "Recipient or its Representatives.")
    doc.para("8.2 Damages alone may not be an adequate remedy and the Company may seek an "
             "injunction or other equitable relief.")
    doc.heading("9. Non-competition", 2)
    doc.para("9.1 In consideration of the Company disclosing the Confidential Information, the "
             "Recipient shall not, for a period of two (2) years from the date of this Agreement, "
             "either alone or jointly with others, and whether directly or indirectly, within the "
             "Region:")
    doc.para("(a) bid or tender for, or supply pumping equipment or related services to, any "
             "person other than the Company in connection with any water or wastewater project; "
             "or", indent=0.8)
    doc.para("(b) assist any other water or wastewater undertaker, developer or contractor to "
             "prepare a proposal for any project that competes with the Project.", indent=0.8)
    doc.para("9.2 The Recipient agrees that the restrictions in clause 9.1 are reasonable and "
             "necessary to protect the Company's legitimate interests in the Confidential "
             "Information.")
    doc.heading("10. General", 2)
    doc.para("10.1 The Recipient may not assign this Agreement. The Company may assign it to any "
             "member of its group or to a successor undertaker.")
    doc.para("10.2 This Agreement is the entire agreement between the parties about its subject "
             "matter. A person who is not a party has no right under the Contracts (Rights of "
             "Third Parties) Act 1999 to enforce any of its terms.")
    doc.heading("11. Governing law and jurisdiction", 2)
    doc.para("11.1 This Agreement and any dispute arising out of or in connection with it are "
             "governed by the law of England and Wales, and the courts of England and Wales have "
             "exclusive jurisdiction.")
    doc.heading("Schedule - The Region", 2)
    doc.para("The administrative areas in which the Company is appointed as water undertaker or "
             "sewerage undertaker, as shown on the plan of its area of appointment available from "
             "the Company on request.")
    doc.spacer()
    doc.signature_block(
        ["Signed for and on behalf of Halden Water Ltd", "Name:", "Title:", "Date:"],
        ["Signed for and on behalf of Kestrel Engineering Ltd", "Name:", "Title:", "Date:"])
    return doc.save(path)


# ======================================================================= Meridian Bank schedule

def build_meridian_schedule(path):
    doc = Doc("Schedule 7 - Limitation of Liability", "Olivia Grant", _t(2026, 9, 28, 9, 0),
              _t(2026, 10, 21, 8, 5),
              header="Meridian Bank plc | Maintenance of Pumping and Cooling Plant | Schedule 7",
              footer="Meridian Bank plc - Restricted - Draft for supplier comment", revision=5)
    doc.title("SCHEDULE 7 - LIMITATION OF LIABILITY",
              "Agreement for the maintenance of pumping and cooling plant at the Customer's data "
              "centres")
    doc.para(I("Customer: Meridian Bank plc. Supplier: Kestrel Engineering Ltd. Draft for supplier "
               "comment, 21 October 2026."))
    doc.heading("1. Definitions", 2)
    doc.para("1.1 In this Schedule:")
    doc.para("\"Annual Charges\" means the total Charges paid or payable by the Customer in the "
             "Contract Year in which the event giving rise to the claim occurred (or, in the first "
             "Contract Year, the Charges that would have been payable had the Agreement been in "
             "force for the whole of that year);", indent=0.8)
    doc.para("\"Data Breach\" means any breach of clause 21 (Data Protection), clause 22 "
             "(Information Security) or clause 23 (Confidentiality), and any Personal Data Breach "
             "as defined in the UK GDPR, caused by the Supplier or its Sub-contractors;", indent=0.8)
    doc.para("\"Default\" means any breach of the Agreement, negligence or breach of statutory "
             "duty of the Supplier or its Sub-contractors;", indent=0.8)
    doc.para("\"Regulatory Fine\" means any fine, penalty or redress imposed on the Customer by "
             "the PRA, the FCA, the Information Commissioner or any other Regulator.", indent=0.8)
    doc.heading("2. Unlimited liability", 2)
    doc.para("2.1 Neither party limits or excludes its liability for death or personal injury "
             "caused by its negligence, for fraud or fraudulent misrepresentation, or for any "
             "other liability that cannot be limited or excluded by law.")
    doc.heading("3. Supplier's liability", 2)
    doc.para("3.1 Subject to paragraphs 2, 3.2 and 3.3, the Supplier's total aggregate liability "
             "in each Contract Year shall not exceed one hundred per cent (100%) of the Annual "
             "Charges.")
    doc.para("3.2 The Supplier's total aggregate liability for Data Breaches shall not exceed "
             "three hundred per cent (300%) of the Annual Charges. This limit is separate from, "
             "and in addition to, the limit in paragraph 3.1.")
    doc.para("3.3 The Supplier's liability for any Regulatory Fine imposed on the Customer to the "
             "extent caused by a Default of the Supplier shall be unlimited, and shall not count "
             "towards the limits in paragraphs 3.1 and 3.2.")
    doc.heading("4. Customer's liability", 2)
    doc.para("4.1 The Customer's total aggregate liability in each Contract Year, other than for "
             "payment of the Charges, shall not exceed one hundred per cent (100%) of the Annual "
             "Charges.")
    doc.heading("5. Excluded losses", 2)
    doc.para("5.1 Neither party shall be liable for any indirect or consequential loss, or for "
             "loss of profit, revenue or goodwill.")
    doc.para("5.2 Despite paragraph 5.1, the following are recoverable by the Customer as direct "
             "losses: (a) the costs of investigating and remedying a Data Breach, including "
             "notifying affected individuals and Regulators; (b) the costs of procuring "
             "replacement services; (c) additional operational and administrative costs, "
             "including the costs of emergency cooling; and (d) Regulatory Fines, subject to "
             "paragraph 3.3.")
    doc.heading("6. Regulatory context", 2)
    doc.para("6.1 The Supplier acknowledges that the Customer is authorised by the Prudential "
             "Regulation Authority and regulated by the Financial Conduct Authority and the "
             "Prudential Regulation Authority, and that the Services support the Customer's "
             "important business services. The Customer must manage its outsourcing and "
             "third-party arrangements in line with its regulators' expectations, including PRA "
             "Supervisory Statement SS2/21, and the limits in this Schedule reflect that "
             "requirement.")
    doc.heading("7. Insurance", 2)
    doc.para("7.1 The Supplier shall maintain public and product liability insurance of not less "
             "than GBP 10 million and cyber insurance of not less than GBP 5 million, in each case "
             "for each and every claim, and shall provide evidence of cover on request.")
    doc.heading("8. Summary of limits (for information only)", 2)
    doc.table(["Head of liability", "Supplier limit", "Paragraph"], [
        ["Death or personal injury, fraud", "Unlimited", "2.1"],
        ["General (all other claims)", "100% of Annual Charges per Contract Year", "3.1"],
        ["Data Breach", "300% of Annual Charges, in addition to the general cap", "3.2"],
        ["Regulatory Fines caused by the Supplier's Default", "Unlimited", "3.3"],
        ["Indirect and consequential loss", "Excluded (except paragraph 5.2)", "5"],
    ], widths=[6.0, 7.0, 2.5])
    return doc.save(path)


# ======================================================================= Rio Bombas draft

def build_riobombas(path):
    doc = Doc("Exclusive Distribution Agreement - Brazil", "Carlos Mendes", _t(2026, 10, 22, 14, 0),
              _t(2026, 10, 27, 19, 40), header="Rio Bombas Distribuição Ltda | Draft 27.10.2026",
              footer="Draft for discussion - subject to contract", revision=3)
    doc.title("EXCLUSIVE DISTRIBUTION AGREEMENT", "Draft prepared by Rio Bombas - 27 October 2026")
    doc.heading("Parties", 2)
    doc.para(B("KESTREL ENGINEERING LTD"), ", a company incorporated in England and Wales, with "
             "its registered office in Sheffield, United Kingdom (\"Supplier\"); and")
    doc.para(B("RIO BOMBAS DISTRIBUIÇÃO LTDA"), ", a limited liability company (sociedade "
             "limitada) incorporated in Brazil, enrolled with the CNPJ under no. "
             "00.000.000/0001-00, with its head office in São Paulo, SP, Brazil (\"Distributor\").")
    doc.heading("Recitals", 2)
    doc.para("(A) Supplier designs and manufactures industrial pumps and spare parts.")
    doc.para("(B) Distributor has an established sales and service network for pumps and fluid "
             "handling equipment in Brazil and wishes to distribute Supplier's products on an "
             "exclusive basis.")
    doc.heading("1. Appointment and exclusivity", 2)
    doc.para("1.1 Supplier appoints Distributor as its exclusive distributor of the Products in "
             "the Federative Republic of Brazil (the \"Territory\"), and Distributor accepts the "
             "appointment.")
    doc.para("1.2 During the term of this Agreement Supplier shall not (a) appoint any other "
             "distributor, agent or reseller in the Territory; or (b) sell the Products, directly "
             "or indirectly, to any customer in the Territory, including original equipment "
             "manufacturers, EPC contractors, water and sanitation companies and other public "
             "utilities.")
    doc.para("1.3 Supplier shall refer to Distributor all enquiries and orders for the Products "
             "received from the Territory. Distributor is entitled to the margin it would have "
             "earned on any sale made in the Territory in breach of clause 1.2.")
    doc.heading("2. Products", 2)
    doc.para("2.1 \"Products\" means all pumps, spare parts and accessories manufactured or sold by "
             "Supplier from time to time, including new products launched during the term.")
    doc.heading("3. Minimum purchase targets", 2)
    doc.para("3.1 Distributor shall use its best efforts to purchase Products with an aggregate "
             "net invoice value of at least:")
    doc.table(["Contract Year", "Minimum purchase target (net invoice value)"], [
        ["Year 1", "EUR 400,000"],
        ["Year 2", "EUR 650,000"],
        ["Year 3", "EUR 900,000"],
        ["Years 4 and 5", "As agreed in writing, not more than the Year 3 target"],
    ], widths=[4.0, 10.0])
    doc.para("3.2 Failure to reach a minimum purchase target is not a breach of this Agreement "
             "and does not entitle Supplier to terminate this Agreement or to reduce the "
             "exclusivity in clause 1. The Parties shall meet to discuss in good faith the reasons "
             "for any shortfall.")
    doc.para("3.3 The minimum purchase target for any Contract Year is reduced in proportion to "
             "any period in which Supplier does not deliver Products within the agreed lead "
             "times.")
    doc.heading("4. Prices and payment", 2)
    doc.para("4.1 Supplier shall sell the Products to Distributor at Supplier's export list price "
             "less a discount of thirty-five per cent (35%). Prices are fixed for each Contract "
             "Year.")
    doc.para("4.2 Deliveries are made CIF Santos (Incoterms 2020).")
    doc.para("4.3 Distributor shall pay each invoice in euros within ninety (90) days of the date "
             "of the bill of lading.")
    doc.heading("5. Marketing and product registration", 2)
    doc.para("5.1 Distributor shall promote the Products in the Territory at its own cost and in "
             "accordance with its own commercial policy and resale prices.")
    doc.para("5.2 Supplier shall bear the costs of any certification, registration or approval "
             "needed to sell the Products in the Territory and shall train Distributor's staff "
             "free of charge.")
    doc.heading("6. Trademarks", 2)
    doc.para("6.1 Distributor may use Supplier's trademarks in the Territory to promote the "
             "Products. To protect the trademarks in the Territory, Distributor may register them "
             "with the Brazilian National Institute of Industrial Property (INPI) in its own name, "
             "and shall assign them to Supplier when this Agreement ends, subject to payment of the "
             "compensation in clause 9.3.")
    doc.heading("7. Warranty", 2)
    doc.para("7.1 Supplier warrants the Products for twenty-four (24) months from delivery to the "
             "end customer and shall reimburse Distributor for all costs of warranty work, "
             "including labour and travel.")
    doc.heading("8. Term", 2)
    doc.para("8.1 This Agreement starts on the date of signature and continues for an initial term "
             "of five (5) years. It renews automatically for further periods of five (5) years "
             "unless either Party gives notice of non-renewal at least twelve (12) months before "
             "the end of the current term.")
    doc.heading("9. Termination", 2)
    doc.para("9.1 Either Party may terminate this Agreement by written notice if the other Party "
             "commits a material breach and does not remedy it within ninety (90) days of notice.")
    doc.para("9.2 Supplier may not terminate this Agreement for convenience.")
    doc.para("9.3 If this Agreement ends for any reason other than termination by Supplier under "
             "clause 9.1, including non-renewal, Supplier shall pay Distributor compensation equal "
             "to Distributor's average annual gross margin on the Products over the last three (3) "
             "Contract Years multiplied by the number of years this Agreement has been in force, "
             "and shall buy back Distributor's stock of Products at the price Distributor paid.")
    doc.heading("10. Governing law and jurisdiction", 2)
    doc.para("10.1 This Agreement is governed by the laws of the Federative Republic of Brazil.")
    doc.para("10.2 The courts of the City of São Paulo, State of São Paulo, have exclusive "
             "jurisdiction, to the exclusion of any other court, however privileged.")
    doc.heading("11. Language", 2)
    doc.para("11.1 This Agreement is signed in English and Portuguese. If the versions differ, "
             "the Portuguese version prevails.")
    doc.heading("12. General", 2)
    doc.para("12.1 Neither Party may assign this Agreement without the other Party's prior written "
             "consent. This Agreement is the entire agreement between the Parties about its "
             "subject matter.")
    doc.spacer()
    doc.signature_block(
        ["KESTREL ENGINEERING LTD", "Name:", "Title:", "Date:"],
        ["RIO BOMBAS DISTRIBUIÇÃO LTDA", "Name:", "Title:", "Date:"])
    return doc.save(path)


# ======================================================================= questionnaires

def build_acme_questionnaire(path, questions):
    """Acme's blank questionnaire: 40 rows of No., Question, Answer, Evidence."""
    assert len(questions) == 40
    doc = Doc("Supplier Information Security Questionnaire", "Acme Supplier Security",
              _t(2026, 6, 1, 8, 0), _t(2026, 10, 19, 9, 10),
              header="Acme Automotive GmbH | Information Security Office | Form ISO-SQ v3.2",
              footer="Acme Automotive GmbH - Confidential when completed", revision=21)
    doc.title("SUPPLIER INFORMATION SECURITY QUESTIONNAIRE")
    doc.table(["Item", "Details"], [
        ["Supplier", "Kestrel Engineering Ltd"],
        ["Service in scope", "Process and cooling-water pumps with remote condition monitoring "
                             "connected to Acme production networks"],
        ["Acme contact", "Supplier Security, vendor-security@acme-automotive.de"],
        ["Issued", "19 October 2026"],
        ["Return by", "30 October 2026"],
    ], widths=[4.0, 11.5])
    doc.heading("Instructions", 2)
    doc.bullet("Answer every question. Where a question does not apply, write \"not applicable\" "
               "and say why.")
    doc.bullet("In the Evidence column, name the policy, certificate or report that supports your "
               "answer. Acme may ask for copies.")
    doc.bullet("Answers must describe controls that are in place today, not planned controls.")
    doc.bullet("The questionnaire must be signed off by a person responsible for information "
               "security at the supplier.")
    doc.heading("Questions", 2)
    doc.table(["No.", "Question", "Answer", "Evidence"],
              [[str(i + 1), q, "", ""] for i, q in enumerate(questions)],
              widths=[1.0, 7.5, 4.5, 3.0], font_size=8.5)
    doc.heading("Sign-off", 2)
    doc.para("Completed by (name and role): ____________________________")
    doc.para("Date: ______________    Signature: ______________________")
    return doc.save(path)


def build_past_questionnaire(path, rows):
    """Kestrel's own answers to a customer security questionnaire, September 2025."""
    assert len(rows) == 40
    doc = Doc("Supplier security questionnaire - Kestrel responses (September 2025)",
              "Raj Mehta", _t(2025, 9, 8, 9, 0), _t(2025, 9, 22, 15, 40),
              header="Kestrel Engineering Ltd | IT Security | Standard answers",
              footer="Kestrel Engineering Ltd - Confidential - Owner: IT Security", revision=8,
              company="Kestrel Engineering Ltd")
    doc.title("SUPPLIER SECURITY QUESTIONNAIRE", "Kestrel Engineering Ltd - responses")
    doc.table(["Item", "Details"], [
        ["Document owner", "IT Security (Head of IT Security)"],
        ["Date of responses", "22 September 2025"],
        ["Prepared for", "A customer's supplier due diligence (water sector), September 2025"],
        ["Covers", "Kestrel Engineering Ltd, Sheffield, including corporate IT and the remote "
                   "condition monitoring platform"],
        ["Reuse", "May be reused as standard answers. Check with IT Security before reusing an "
                  "answer that is more than 12 months old."],
    ], widths=[4.0, 11.5])
    doc.heading("Responses", 2)
    doc.table(["No.", "Question", "Kestrel answer", "Evidence"],
              [[str(i + 1), q, a, e] for i, (q, a, e) in enumerate(rows)],
              widths=[1.0, 4.5, 7.5, 3.0], font_size=8.5)
    doc.heading("Approval", 2)
    doc.para("Answers reviewed and approved by the Head of IT Security on 22 September 2025.")
    return doc.save(path)


# ======================================================================= fixtures

def build_fixture_docx(path):
    """tools/fixtures/sample.docx: one tracked insertion containing FIXTURE-INSERTED-TEXT."""
    doc = Doc("Fixture document", "Tooling Fixture", _t(2026, 10, 1, 8, 0), _t(2026, 10, 1, 8, 0),
              change_author="Tooling Fixture", change_date=_t(2026, 10, 1, 8, 0))
    doc.para("Fixture document for bash tools/tooling-setup. The next sentence is a tracked "
             "insertion: ", Ins("FIXTURE-INSERTED-TEXT"), ".")
    doc.para("pandoc --track-changes=all must show the inserted text above.")
    return doc.save(path)


def build_fixture_attachment(path):
    """fixture.docx: the small attachment of tools/fixtures/sample.eml."""
    doc = Doc("Fixture attachment", "Tom Hale", _t(2026, 10, 1, 7, 45), _t(2026, 10, 1, 7, 45))
    doc.para("Fixture attachment for tools/tooling-setup.")
    doc.para("If you can read this, the attachment was extracted from sample.eml.")
    return doc.save(path)
