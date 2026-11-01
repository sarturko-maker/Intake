#!/usr/bin/env python3
"""Build the binary knowledge files of the demo world (Kestrel Engineering, all invented).

Outputs, committed to the repository:
  demo/knowledge/policies/delegation-of-authority.docx      who approves, who signs, limits
  demo/knowledge/templates/kestrel-mutual-nda-template.docx Kestrel's mutual NDA template
  demo/knowledge/entities/insurance-schedule-2026.pdf       broker's schedule; no owner line

The Markdown knowledge files (policies, entities, people, positions) are written by hand.
demo/knowledge/standard-answers/ belongs to the demo-mail generator, not to this one.

Every company, person, address, register number and policy number here is invented.
Numbers that would identify a real company are zero-filled on purpose (company number
00000000, HRB 00000). Email addresses outside the demo domains use .invalid.

Deterministic: fixed core properties and fixed zip entry times for the .docx files;
reportlab invariant mode and a fixed creation date for the PDF. Two runs give the same bytes.

Usage:
  python3 demo/build/world/make_world.py            build into demo/knowledge/
  python3 demo/build/world/make_world.py --check    build into a temp folder, compare with
                                                    the committed files, exit 1 on a difference
  python3 demo/build/world/make_world.py --out DIR  build into DIR/<same relative paths>

Dev tool: Python 3.8+, python-docx 1.2, reportlab. Not used by the workspace at run time.
"""

import argparse
import datetime as dt
import filecmp
import io
import sys
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPO = Path(__file__).resolve().parents[3]
KNOWLEDGE = REPO / "demo" / "knowledge"
ZIP_TIME = (2026, 10, 1, 0, 0, 0)

OUTPUTS = {
    "doa": "policies/delegation-of-authority.docx",
    "nda": "templates/kestrel-mutual-nda-template.docx",
    "insurance": "entities/insurance-schedule-2026.pdf",
}

UTC = dt.timezone.utc


def _t(y, mo, d, h=9, mi=0):
    return dt.datetime(y, mo, d, h, mi, tzinfo=UTC)


# ======================================================================= docx helpers

def _normalise_zip(data):
    """Rewrite a .docx with fixed entry times and attributes, so the bytes never change."""
    zin = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zi = zipfile.ZipInfo(info.filename, ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 0
            zi.external_attr = 0
            zout.writestr(zi, zin.read(info.filename))
    return out.getvalue()


def _shade(cell, fill="DDE4EE"):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


class WordDoc:
    """A plain Word document: headings, numbered paragraphs typed as text, simple tables."""

    def __init__(self, title, author, created, modified, revision, header, footer,
                 subject="", keywords="", company="Kestrel Engineering Ltd"):
        self.d = Document()
        self.meta = dict(title=title, author=author, created=created, modified=modified,
                         revision=revision, subject=subject, keywords=keywords)
        normal = self.d.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(10.5)
        normal.paragraph_format.space_after = Pt(5)
        for name, size in (("Heading 1", 13), ("Heading 2", 11.5)):
            st = self.d.styles[name]
            st.font.name = "Calibri"
            st.font.size = Pt(size)
            st.font.color.rgb = RGBColor(0x0E, 0x3B, 0x5C)
        sec = self.d.sections[0]
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        for side in ("left_margin", "right_margin"):
            setattr(sec, side, Cm(2.2))
        sec.top_margin, sec.bottom_margin = Cm(2.3), Cm(2.0)
        hp = sec.header.paragraphs[0]
        hp.text = header
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for r in hp.runs:
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        fp = sec.footer.paragraphs[0]
        fp.text = footer
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in fp.runs:
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        self.company = company

    def title(self, text, sub=None):
        # A plain bold paragraph, not Word's Title style: pandoc turns the Title style into
        # metadata and drops it from `pandoc FILE -t plain`, which is how the indexer reads.
        p = self.d.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(18)
        r.font.color.rgb = RGBColor(0x0E, 0x3B, 0x5C)
        if sub:
            p = self.d.add_paragraph()
            r = p.add_run(sub)
            r.italic = True
            r.font.size = Pt(11)

    def h1(self, text):
        self.d.add_heading(text, level=1)

    def h2(self, text):
        self.d.add_heading(text, level=2)

    def para(self, *parts, indent=0.0, italic=False, size=None, align=None):
        """parts: plain strings, or ("b", text) for bold, ("i", text) for italic."""
        p = self.d.add_paragraph()
        if indent:
            p.paragraph_format.left_indent = Cm(indent)
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for part in parts:
            if isinstance(part, tuple):
                kind, text = part
                r = p.add_run(text)
                r.bold = kind == "b"
                r.italic = kind == "i" or italic
            else:
                r = p.add_run(part)
                r.italic = italic
            if size:
                r.font.size = Pt(size)
        return p

    def bullet(self, text, indent=0.6):
        p = self.d.add_paragraph()
        p.paragraph_format.left_indent = Cm(indent + 0.4)
        p.paragraph_format.first_line_indent = Cm(-0.4)
        p.add_run("•  " + text)
        return p

    def table(self, header, rows, widths, size=9.0):
        t = self.d.add_table(rows=1 + len(rows), cols=len(header))
        t.style = self.d.styles["Table Grid"]
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, text in enumerate(header):
            cell = t.rows[0].cells[i]
            cell.text = ""
            r = cell.paragraphs[0].add_run(text)
            r.bold = True
            r.font.size = Pt(size)
            _shade(cell)
        for ri, row in enumerate(rows, start=1):
            for ci, text in enumerate(row):
                cell = t.rows[ri].cells[ci]
                cell.text = ""
                r = cell.paragraphs[0].add_run(text)
                r.font.size = Pt(size)
        for ci, w in enumerate(widths):
            for row in t.rows:
                row.cells[ci].width = Cm(w)
        self.d.add_paragraph()
        return t

    def signature_block(self, left, right):
        t = self.d.add_table(rows=len(left), cols=2)
        for i, (a, b) in enumerate(zip(left, right)):
            t.rows[i].cells[0].text = a
            t.rows[i].cells[1].text = b
        return t

    def save(self, path):
        cp = self.d.core_properties
        cp.title = self.meta["title"]
        cp.author = self.meta["author"]
        cp.last_modified_by = self.meta["author"]
        cp.subject = self.meta["subject"]
        cp.keywords = self.meta["keywords"]
        cp.comments = ""
        cp.category = ""
        cp.created = self.meta["created"].replace(tzinfo=None)
        cp.modified = self.meta["modified"].replace(tzinfo=None)
        cp.last_printed = self.meta["modified"].replace(tzinfo=None)
        cp.revision = self.meta["revision"]
        buf = io.BytesIO()
        self.d.save(buf)
        data = _normalise_zip(buf.getvalue())
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(data)
        return data


# ======================================================================= delegation of authority

def build_doa(path):
    doc = WordDoc(
        "Delegation of Authority and Signing Policy", "Chris Barker",
        _t(2025, 11, 18, 10, 0), _t(2026, 1, 26, 15, 30), revision=14,
        header="Kestrel Engineering Ltd | FIN-POL-02 Delegation of Authority and Signing Policy | "
               "Version 3.0",
        footer="Internal | Owner: Chief Financial Officer | In force from 1 February 2026",
        subject="Approval limits and signing authority for the Kestrel group",
        keywords="delegation of authority; signing; approval limits; liability caps; Vollmacht")
    doc.title("DELEGATION OF AUTHORITY AND SIGNING POLICY",
              "Kestrel Engineering Ltd and Kestrel Pumpen GmbH")
    doc.table(["Item", "Details"], [
        ["Document", "FIN-POL-02 Delegation of Authority and Signing Policy"],
        ["Version", "3.0 (replaces version 2.1 of March 2024)"],
        ["Owner", "Chief Financial Officer (Finance)"],
        ["Approved by", "Board of Kestrel Engineering Ltd on 20 January 2026; adopted by the "
                        "Geschäftsführer of Kestrel Pumpen GmbH on 26 January 2026"],
        ["In force from", "1 February 2026"],
        ["Next review", "January 2027"],
        ["Applies to", "Kestrel Engineering Ltd (KEL) and Kestrel Pumpen GmbH (KPG)"],
    ], widths=[4.0, 12.6])

    doc.h1("1. Purpose and scope")
    doc.para("1.1 This policy says who may approve commitments on behalf of the Kestrel group, and "
             "who may sign documents for each group company. It applies to Kestrel Engineering Ltd "
             "(\"KEL\") and Kestrel Pumpen GmbH (\"KPG\") and to everyone who works for them.")
    doc.para("1.2 Approval and signature are separate steps. A commitment must be approved at the "
             "right level before anyone signs it. Signing a document does not by itself approve "
             "it.")
    doc.para("1.3 Nobody may approve a commitment in which they have a personal interest, or "
             "approve their own expenses.")
    doc.para("1.4 A commitment must not be split into smaller parts to keep it below a limit.")

    doc.h1("2. Definitions")
    doc.para(("b", "Annual contract value"), " means the expected revenue or spend in any 12-month "
             "period under a contract, including options that are likely to be exercised. For a "
             "one-off sale or purchase it means the total price.")
    doc.para(("b", "Annual fees"), ", for liability caps, means the fees paid or payable under the "
             "contract in the 12 months before the event that gives rise to the claim, as set out "
             "in the Legal position paper on liability in customer contracts (LP-03).")
    doc.para(("b", "Director"), " means a director of KEL registered at Companies House. ",
             ("b", "Geschäftsführer"), " means a managing director of KPG entered in the "
             "Handelsregister. ", ("b", "Legal"), " means the Senior Legal Counsel.")

    doc.h1("3. General rules")
    doc.para("3.1 Legal must review a document before it is signed if it is: a contract that is not "
             "on a Kestrel standard template, or a template that has been changed; an NDA on the "
             "other party's paper; governed by a law other than that of England and Wales or "
             "Germany; a power of attorney; or a guarantee, bond or letter of credit.")
    doc.para("3.2 Approvals are given in writing (an email is enough) and kept with the contract "
             "record.")
    doc.para("3.3 The limits in this policy are in pounds sterling. For KPG the same limits apply in "
             "euros at the budget rate set by Finance each year (2026: GBP 1 = EUR 1.15).")

    doc.h1("4. Approval limits for commitments")
    doc.para("4.1 A commitment is approved at the level shown for its annual contract value. Each "
             "level may also approve everything below it.")
    doc.table(["Commitment", "Up to GBP 100,000", "Up to GBP 500,000", "Up to GBP 2,000,000",
               "Above GBP 2,000,000"], [
        ["Customer contracts and bids (annual contract value)", "Sales Director",
         "Chief Executive Officer", "Chief Executive Officer and Chief Financial Officer together",
         "Board"],
        ["Supplier contracts and purchase orders (annual contract value)", "Procurement Lead",
         "Operations Director", "Chief Executive Officer and Chief Financial Officer together",
         "Board"],
        ["Capital expenditure (total cost)", "Operations Director", "Chief Executive Officer",
         "Chief Executive Officer and Chief Financial Officer together", "Board"],
    ], widths=[4.6, 2.6, 2.8, 3.8, 2.8])
    doc.para("4.2 Settlements of claims, credit notes and write-offs: the Chief Financial Officer up "
             "to GBP 25,000; the Chief Executive Officer and the Chief Financial Officer together up "
             "to GBP 250,000; the Board above that.")
    doc.para("4.3 A bid or tender is approved at the level of the contract that would result from "
             "it, including the list of exceptions to the customer's terms.")

    doc.h1("5. Contract terms that need specific approval")
    doc.para("5.1 The terms below need the approval shown, whatever the value of the contract, in "
             "addition to the approval under section 4. Legal's positions on these terms are in the "
             "Legal position papers (LP-01 NDAs, LP-03 liability in customer contracts).")
    doc.table(["Term", "Approval needed"], [
        ["General liability cap up to 1x the annual fees",
         "Covered by the approval under section 4, after Legal review"],
        ["General liability cap above 1x the annual fees",
         "Chief Financial Officer, after Legal review"],
        ["Separate cap for data breach (super-cap) up to 2x the annual fees",
         "Senior Legal Counsel"],
        ["Cap for data breach above 2x and up to 3x the annual fees, only for customers regulated by "
         "the PRA or the FCA where their outsourcing rules apply to the contract",
         "Chief Financial Officer, on Legal's advice"],
        ["Unlimited liability, other than for death or personal injury caused by negligence, for "
         "fraud, and for liability that cannot be limited by law",
         "Not permitted. Only the Board may make an exception"],
        ["Indemnities other than the standard intellectual property indemnity",
         "Senior Legal Counsel. Uncapped indemnities are not permitted"],
        ["Liquidated damages above 10% of the contract price", "Chief Financial Officer"],
        ["Exclusivity, non-compete, most-favoured-customer or minimum purchase commitments given "
         "by Kestrel", "Chief Executive Officer, on Legal's advice. Never in an NDA"],
        ["Parent company guarantees, bonds and letters of credit",
         "Chief Financial Officer up to GBP 1,000,000; Board above"],
        ["Contracts governed by a law other than that of England and Wales or Germany",
         "Senior Legal Counsel"],
        ["Payment terms longer than 90 days, or advance payments by Kestrel above GBP 50,000",
         "Chief Financial Officer"],
    ], widths=[10.0, 6.6])

    doc.h1("6. Who signs")
    doc.h2("6.1 Kestrel Engineering Ltd")
    doc.para("(a) Once a commitment is approved under sections 4 and 5, the contract is signed for "
             "KEL by one director.", indent=0.6)
    doc.para("(b) The authorised signatories in Schedule 1 may also sign within their limits.",
             indent=0.6)
    doc.para("(c) A deed is executed by two directors, or by one director in the presence of a "
             "witness who attests the signature (Companies Act 2006, sections 44 and 46).",
             indent=0.6)
    doc.para("(d) Key account managers, bid managers and other staff may not sign contracts for KEL. "
             "They may send a document once an authorised person has signed it.", indent=0.6)
    doc.para("(e) Customer contracts for the United Kingdom and the rest of the world are made by "
             "KEL. Customer contracts for Germany, Austria and Switzerland are usually made by KPG, "
             "unless the customer buys centrally from KEL. The remote condition monitoring service "
             "is always provided by KEL.", indent=0.6)
    doc.h2("6.2 NDAs")
    doc.para("NDAs on the Kestrel template, or cleared by Legal, may be signed for KEL by any "
             "director or by the Senior Legal Counsel, and for KPG by its two Geschäftsführer "
             "jointly. Nobody may sign an NDA that contains a non-compete, a non-solicitation of "
             "customers or an indemnity.")
    doc.h2("6.3 Kestrel Pumpen GmbH")
    doc.para("(a) KPG is represented by its two Geschäftsführer acting jointly (Gesamtvertretung), "
             "as entered in the commercial register of the Amtsgericht Dortmund (HRB 00000). One "
             "Geschäftsführer alone cannot bind KPG, on any document, including bank forms. No "
             "Prokura is registered.", indent=0.6)
    doc.para("(b) Officers of KEL who are not Geschäftsführer of KPG, including the group Chief "
             "Financial Officer, may sign for KPG only under a written power of attorney "
             "(Vollmacht) signed by both Geschäftsführer.", indent=0.6)
    doc.para("(c) The approval limits in sections 4 and 5 also apply to commitments of KPG. A "
             "commitment approved under those sections is then signed by both Geschäftsführer.",
             indent=0.6)
    doc.h2("6.4 Bank accounts and payments")
    doc.para("(a) Opening or closing a bank account, and any bank mandate or account power of "
             "attorney (Kontovollmacht), needs the approval of the Chief Financial Officer. It is "
             "signed for KEL by two directors and for KPG by both Geschäftsführer.", indent=0.6)
    doc.para("(b) Every payment above GBP 10,000 (for KPG: EUR 10,000) is released in online "
             "banking by two authorised persons acting jointly. One authorised person may release "
             "a payment up to that amount, within a daily limit agreed with the bank.", indent=0.6)
    doc.para("(c) No one may change the bank details of a supplier or customer on the strength of "
             "an email or letter alone. The change is checked by a telephone call to a number "
             "already on file, and approved by a second person in Finance.", indent=0.6)

    doc.h1("7. Powers of attorney")
    doc.para("7.1 A power of attorney for KEL is granted by deed, signed by two directors. A power "
             "of attorney (Vollmacht) for KPG is signed by both Geschäftsführer.")
    doc.para("7.2 Every power of attorney is limited in scope and in time (at most two years), is "
             "reviewed by Legal before signature, and is recorded in the register of powers of "
             "attorney kept by Legal.")
    doc.para("7.3 A notary (notarielle Beglaubigung) is needed only where the law requires it, for "
             "example for filings with the Handelsregister, transfers of GmbH shares or land, or "
             "where the other party insists. Legal arranges it.")
    doc.para("7.4 Prokura for KPG is granted by both Geschäftsführer with the approval of the Board "
             "of KEL, and entered in the Handelsregister through a notary.")

    doc.h1("8. Records")
    doc.para("8.1 Signed originals, or the signed PDF, go to Legal for the contract register within "
             "five working days.")
    doc.para("8.2 Finance keeps the bank mandate list and the list of authorised signatories, and "
             "updates both when a role holder changes.")

    doc.h1("9. Breaches")
    doc.para("9.1 A commitment made without the required approval may not bind the company, or may "
             "need to be ratified. Breaches are reported to the Chief Financial Officer and may lead "
             "to disciplinary action.")

    doc.h1("Schedule 1: Authorised signatories (as at 1 February 2026)")
    doc.table(["Name", "Role", "May sign for"], [
        ["Helen Ashworth", "Chief Executive Officer and director of KEL; Geschäftsführerin of KPG",
         "KEL: all approved commitments. KPG: jointly with Jens Hartmann"],
        ["Chris Barker", "Chief Financial Officer and director of KEL",
         "KEL: all approved commitments. KPG: only under a Vollmacht signed by both "
         "Geschäftsführer"],
        ["David Lund", "Operations Director and director of KEL", "KEL: all approved commitments"],
        ["Jens Hartmann", "Geschäftsführer of KPG", "KPG: jointly with Helen Ashworth"],
        ["Owen Pryce", "Sales Director, KEL", "Customer contracts up to GBP 100,000 annual "
                                               "contract value"],
        ["Hannah Cole", "Procurement Lead, KEL", "Purchase orders and supplier contracts up to "
                                                  "GBP 100,000"],
        ["Alex Morgan", "Senior Legal Counsel, KEL", "NDAs; data processing agreements; settlement "
                                                      "agreements up to GBP 25,000 approved by the "
                                                      "Chief Financial Officer"],
    ], widths=[3.2, 6.0, 7.4])
    return doc.save(path)


# ======================================================================= mutual NDA template

def build_nda_template(path):
    doc = WordDoc(
        "Mutual Non-Disclosure Agreement - Kestrel template", "Alex Morgan",
        _t(2023, 4, 3, 9, 0), _t(2026, 2, 24, 16, 10), revision=23,
        header="Kestrel Engineering Ltd | Mutual NDA template NDA-M | Version 4.0",
        footer="Template owner: Legal | Valid from 1 March 2026 | Remove the template notes before "
               "sending",
        subject="Kestrel standard mutual NDA",
        keywords="NDA; confidentiality; template; LP-01")
    doc.title("MUTUAL NON-DISCLOSURE AGREEMENT", "Kestrel template NDA-M, version 4.0")

    doc.h2("Template notes (delete before sending)")
    doc.table(["Item", "Note"], [
        ["Owner", "Legal (Senior Legal Counsel). Version 4.0, valid from 1 March 2026; replaces "
                  "version 3.2."],
        ["When to use", "Customers, suppliers, partners and bidders where both sides will share "
                        "information: prices, drawings, designs, monitoring data or plans."],
        ["Kestrel party", "Kestrel Engineering Ltd for the United Kingdom and the rest of the world. "
                          "Kestrel Pumpen GmbH for Germany, Austria and Switzerland: replace party "
                          "(1) with \"KESTREL PUMPEN GMBH, registered in the commercial register of "
                          "the Amtsgericht Dortmund under HRB 00000, Turmfalkenstraße 7, 44000 "
                          "Dortmund, Germany\", and ask Legal for the German-law version of "
                          "clause 14."],
        ["Fill in", "Everything in square brackets. Describe the Purpose in one sentence."],
        ["Do not change", "Clauses 2, 5, 7, 10 and 14 without Legal. Never add a non-compete, a "
                          "non-solicitation of customers, an indemnity, a penalty or a residuals "
                          "clause (Legal position paper LP-01)."],
        ["Signing", "Unchanged template: any director of Kestrel Engineering Ltd or the Senior "
                    "Legal Counsel; for Kestrel Pumpen GmbH, both Geschäftsführer jointly "
                    "(delegation of authority policy, section 6.2)."],
    ], widths=[3.4, 13.2])

    doc.para(("b", "THIS AGREEMENT"), " is dated [date].")
    doc.h2("Parties")
    doc.para("(1) ", ("b", "KESTREL ENGINEERING LTD"), ", a company incorporated in England and "
             "Wales with company number 00000000, whose registered office is at Kestrel House, "
             "1 Hawkstone Way, Sheffield S0 1KE, United Kingdom (\"Kestrel\"); and")
    doc.para("(2) ", ("b", "[COUNTERPARTY LEGAL NAME]"), ", a company incorporated in [country] "
             "with company number [number], whose registered office is at [address] (the "
             "\"Counterparty\"),")
    doc.para("each a \"Party\" and together the \"Parties\".")
    doc.h2("Background")
    doc.para("(A) The Parties wish to discuss [describe the project or business relationship] (the "
             "\"Purpose\").")
    doc.para("(B) Each Party expects to disclose Confidential Information to the other for the "
             "Purpose and agrees to protect it on the terms of this Agreement.")
    doc.h2("Agreed terms")

    clauses = [
        ("1. Definitions", [
            "1.1 \"Affiliate\" means any entity that controls, is controlled by, or is under common "
            "control with a Party, where control means direct or indirect ownership of more than "
            "50% of the voting rights.",
            "1.2 \"Confidential Information\" means all information of whatever nature and in "
            "whatever form, including technical data, drawings, designs, specifications, software, "
            "prices, costs, volumes, customer information and data from monitoring systems, that is "
            "disclosed by or for a Party (the \"Discloser\") to the other Party (the \"Recipient\") "
            "in connection with the Purpose, before or after the date of this Agreement, and that is "
            "marked or described as confidential or that a reasonable person would consider "
            "confidential.",
            "1.3 \"Representatives\" means a Party's and its Affiliates' directors, officers, "
            "employees, contractors and professional advisers.",
            "1.4 \"Trade Secret\" means Confidential Information that is a trade secret under "
            "applicable law.",
        ]),
        ("2. Confidentiality", [
            "2.1 The Recipient shall: (a) keep the Discloser's Confidential Information "
            "confidential; (b) use it only for the Purpose; (c) not disclose it to anyone except as "
            "clause 3 permits; and (d) protect it with at least the care it uses for its own "
            "confidential information of a similar kind, and in any case with reasonable care.",
        ]),
        ("3. Permitted disclosure", [
            "3.1 The Recipient may disclose Confidential Information to those of its Representatives "
            "who need to know it for the Purpose, if they are bound by obligations of "
            "confidentiality no less protective than this Agreement. The Recipient is responsible "
            "for any breach by its Representatives.",
            "3.2 The Recipient may disclose Confidential Information to the extent required by law, "
            "by a court or by a governmental or regulatory authority, if, where lawful, it gives "
            "the Discloser prompt notice and takes reasonable steps to limit the disclosure.",
        ]),
        ("4. Exceptions", [
            "4.1 Clauses 2 and 3 do not apply to information that the Recipient can show: (a) is or "
            "becomes public other than through a breach of this Agreement; (b) was lawfully in its "
            "possession, free of any obligation of confidence, before it was disclosed; (c) is "
            "lawfully received from a third party free of any obligation of confidence; or (d) is "
            "developed independently without use of the Discloser's Confidential Information.",
        ]),
        ("5. Return and destruction", [
            "5.1 On the Discloser's written request, the Recipient shall promptly return or destroy "
            "the Discloser's Confidential Information and, if asked, confirm in writing that it has "
            "done so. The Recipient may keep copies (a) that it must keep by law or regulation, and "
            "(b) held in routine electronic back-ups that are not readily accessible, which remain "
            "subject to this Agreement.",
        ]),
        ("6. No licence and no warranty", [
            "6.1 All Confidential Information remains the property of the Discloser. This Agreement "
            "grants no licence or other right in any intellectual property of either Party, except "
            "the right to use Confidential Information for the Purpose.",
            "6.2 Confidential Information is provided \"as is\". The Discloser gives no warranty as "
            "to its accuracy or completeness.",
        ]),
        ("7. Duration", [
            "7.1 This Agreement starts on the date of the last signature. Either Party may end the "
            "discussions on the Purpose at any time by written notice.",
            "7.2 The obligations in this Agreement continue for three (3) years from the date of "
            "this Agreement, except that the obligations in respect of Trade Secrets continue for "
            "five (5) years from that date.",
        ]),
        ("8. No obligation", [
            "8.1 Neither Party is obliged to disclose any particular information or to enter into "
            "any further agreement. Any further relationship will be governed by a separate written "
            "contract.",
        ]),
        ("9. Data protection", [
            "9.1 The Parties do not intend to share personal data under this Agreement. If they do, "
            "each Party shall comply with the data protection law that applies to it, including the "
            "UK GDPR and the EU GDPR.",
        ]),
        ("10. Remedies", [
            "10.1 Each Party agrees that damages alone may not be an adequate remedy for a breach of "
            "this Agreement, and that the Discloser may seek an injunction or specific performance "
            "in addition to any other remedy.",
        ]),
        ("11. Assignment", [
            "11.1 Neither Party may assign or transfer this Agreement without the prior written "
            "consent of the other, except to an Affiliate that takes over the business to which the "
            "Purpose relates.",
        ]),
        ("12. General", [
            "12.1 This Agreement is the entire agreement between the Parties about its subject "
            "matter. Any amendment must be in writing and signed by both Parties.",
            "12.2 A person who is not a Party has no right under the Contracts (Rights of Third "
            "Parties) Act 1999 to enforce any term of this Agreement.",
            "12.3 This Agreement may be signed in counterparts and by electronic signature. Each "
            "counterpart is an original, and together they form one agreement.",
        ]),
        ("13. Notices", [
            "13.1 Notices under this Agreement are given in writing to the addresses above, or by "
            "email: for Kestrel to legal@kestrel-eng.co.uk, for the Counterparty to [email].",
        ]),
        ("14. Governing law and jurisdiction", [
            "14.1 This Agreement and any dispute or claim, including a non-contractual dispute or "
            "claim, arising out of or in connection with it are governed by the law of England and "
            "Wales.",
            "14.2 The courts of England and Wales have exclusive jurisdiction to settle any such "
            "dispute or claim.",
        ]),
    ]
    for heading, paras in clauses:
        doc.h2(heading)
        for text in paras:
            doc.para(text)

    doc.para(("b", "Signed by the Parties on the dates below."))
    doc.signature_block(
        ["Signed for and on behalf of KESTREL ENGINEERING LTD", "Name:", "Title:", "Date:",
         "Signature:"],
        ["Signed for and on behalf of [COUNTERPARTY LEGAL NAME]", "Name:", "Title:", "Date:",
         "Signature:"])
    return doc.save(path)


# ======================================================================= insurance schedule (PDF)

def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_insurance_pdf(path):
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.2,
                          leading=12, spaceAfter=5, alignment=TA_LEFT)
    small = ParagraphStyle("small", parent=body, fontSize=7.8, leading=9.8, spaceAfter=3)
    h1 = ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=16, leading=20,
                        spaceAfter=8, textColor=colors.HexColor("#1F3A2E"))
    h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=14,
                        spaceBefore=6, spaceAfter=5, textColor=colors.HexColor("#1F3A2E"),
                        keepWithNext=1)
    cell = ParagraphStyle("cell", parent=body, fontSize=8, leading=10, spaceAfter=0)
    cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")

    def P(text, style=body):
        return Paragraph(_esc(text), style)

    def grid(header, rows, widths):
        data = [[Paragraph(_esc(h), cellb) for h in header]]
        data += [[Paragraph(_esc(c), cell) for c in r] for r in rows]
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8A9A90")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE8E0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    story = [
        P("Schedule of Insurance 2026/27", h1),
        P("Kestrel Engineering group", h2),
        grid(["Item", "Details"], [
            ["Client", "Kestrel Engineering Ltd and its subsidiary companies, including Kestrel "
                       "Pumpen GmbH"],
            ["Period of insurance", "1 April 2026 to 31 March 2027, both days inclusive"],
            ["Issued", "24 March 2026"],
            ["Our reference", "MT/KEL/2026-27/SCH"],
            ["Broker", "Marrick & Thorne Insurance Brokers Ltd"],
        ], [4.2 * cm, 12.4 * cm]),
        Spacer(1, 8),
        P("This schedule summarises the insurance we have arranged for the Kestrel group for the "
          "period above. It is a summary only. The policy wordings, schedules and endorsements "
          "issued by insurers set out the full cover, conditions and exclusions, and they prevail "
          "over this summary."),
        P("Summary of cover", h2),
        grid(["Class of cover", "Insurer and policy", "Limit of indemnity", "Excess",
              "Territory"], [
            ["Products liability", "Eastmarch Insurance plc, EMI/LIA/26/000000",
             "GBP 10,000,000 any one occurrence and in the aggregate in respect of all products "
             "claims in the period", "GBP 10,000 each claim (property damage only)",
             "Worldwide, excluding USA and Canada"],
            ["Public liability", "Eastmarch Insurance plc, EMI/LIA/26/000000",
             "GBP 10,000,000 any one occurrence", "GBP 1,000 each claim (property damage only)",
             "Worldwide, excluding USA and Canada"],
            ["Employers' liability", "Eastmarch Insurance plc, EMI/EL/26/000000",
             "GBP 10,000,000 any one occurrence, including costs", "Nil",
             "Great Britain, Northern Ireland, Isle of Man, Channel Islands; employees temporarily "
             "abroad"],
            ["Cyber and data", "Quillon Specialty Insurance Ltd, QSI/CYB/26/000000",
             "GBP 5,000,000 any one claim and in the aggregate for the period, including defence "
             "and incident response costs",
             "GBP 25,000 each claim; 8-hour waiting period for business interruption",
             "Worldwide"],
            ["Professional indemnity", "Quillon Specialty Insurance Ltd, QSI/PI/26/000000",
             "GBP 2,000,000 any one claim and in the aggregate", "GBP 15,000 each claim",
             "Worldwide, excluding USA and Canada"],
            ["Property damage and business interruption",
             "Eastmarch Insurance plc, EMI/PRO/26/000000",
             "Buildings, plant and stock at Sheffield and Dortmund: GBP 46,500,000 (declared "
             "values). Business interruption: gross profit GBP 21,000,000, 24-month indemnity "
             "period", "GBP 10,000 each loss", "United Kingdom and Germany"],
            ["Goods in transit and marine cargo", "Eastmarch Insurance plc, EMI/MAR/26/000000",
             "GBP 750,000 any one conveyance", "GBP 2,500 each claim", "Worldwide"],
            ["Directors' and officers' liability", "Quillon Specialty Insurance Ltd, "
                                                   "QSI/DO/26/000000",
             "GBP 5,000,000 in the aggregate", "Nil for individuals", "Worldwide"],
            ["Local liability policy, Kestrel Pumpen GmbH",
             "Issued in Germany by Eastmarch Insurance plc, Niederlassung Deutschland, "
             "EMD/HPF/26/000000",
             "EUR 5,000,000 any one occurrence (general and products liability), with the group "
             "policy above it for broader conditions and higher limits", "EUR 2,500 each claim",
             "Germany, Austria and Switzerland"],
        ], [3.0 * cm, 3.6 * cm, 4.6 * cm, 2.8 * cm, 2.6 * cm]),
        Spacer(1, 8),
        P("Points to note when you agree contracts", h2),
        P("1. Liability accepted under contract. The liability policies cover the liability Kestrel "
          "would have had in law without the contract. Liability you accept under a contract "
          "beyond that, for example an indemnity, a waiver of a limitation or liquidated damages, "
          "is not covered unless insurers agree in advance. Please send us any contract that asks "
          "for unlimited liability or an indemnity before it is signed."),
        P("2. Aggregate limits. The products liability limit and the cyber limit are aggregate "
          "limits: GBP 10,000,000 and GBP 5,000,000 are the most insurers will pay for all claims "
          "of that kind in the period, across all customers. Where a customer asks for cover \"for "
          "each and every claim\", please check with us before you confirm it."),
        P("3. Cyber. Fines and penalties are covered only where they are insurable by law. "
          "Contractual penalties and service credits are excluded."),
        P("4. Professional indemnity covers design and advice, including advice given through the "
          "remote condition monitoring service."),
        P("5. Certificates. We can issue certificates of insurance for customers on request; please "
          "allow two working days."),
        P("6. Changes. Please tell us before you start new activities that may change the risk, for "
          "example sales to the USA or Canada, acquisitions, or new services."),
        Spacer(1, 6),
        P("Account executive: Fiona Marr, Marrick & Thorne Insurance Brokers Ltd, Leeds. "
          "T +44 113 496 0755. kestrel.team@marrickthorne.invalid", small),
        P("Marrick & Thorne Insurance Brokers Ltd is authorised and regulated by the Financial "
          "Conduct Authority. Firm reference number 000000. Registered in England and Wales, "
          "company number 00000000.", small),
    ]

    def on_page(canv, d):
        canv.saveState()
        w, h = A4
        canv.setFillColor(colors.HexColor("#1F3A2E"))
        canv.rect(0, h - 1.1 * cm, w, 1.1 * cm, stroke=0, fill=1)
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 9.5)
        canv.drawString(2.2 * cm, h - 0.72 * cm, "MARRICK & THORNE INSURANCE BROKERS")
        canv.setFont("Helvetica", 8)
        canv.drawRightString(w - 2.2 * cm, h - 0.72 * cm, "Schedule of Insurance 2026/27")
        canv.setFillColor(colors.black)
        canv.setFont("Helvetica", 7)
        canv.drawString(2.2 * cm, 1.1 * cm, "Kestrel Engineering group | Period 1 April 2026 to "
                                            "31 March 2027 | Summary only: the policy wordings "
                                            "prevail")
        canv.drawRightString(w - 2.2 * cm, 1.1 * cm, "Page %d" % canv.getPageNumber())
        canv.restoreState()

    created = "D:20260324104500+00'00'"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="Schedule of Insurance 2026/27 - Kestrel Engineering group",
                            author="Marrick & Thorne Insurance Brokers Ltd",
                            subject="Summary of insurance cover, period 2026/27",
                            creator="Marrick & Thorne Insurance Brokers Ltd",
                            producer="Marrick & Thorne Insurance Brokers Ltd", invariant=1)

    def first(canv, d):
        canv.setDateFormatter(lambda *a: created)
        on_page(canv, d)

    doc.build(story, onFirstPage=first, onLaterPages=on_page)
    data = buf.getvalue()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(data)
    return data


# ======================================================================= main

BUILDERS = {"doa": build_doa, "nda": build_nda_template, "insurance": build_insurance_pdf}


def build_all(root):
    root = Path(root)
    written = []
    for key, rel in OUTPUTS.items():
        dest = root / rel
        BUILDERS[key](dest)
        written.append(dest)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the demo world's .docx and .pdf knowledge files.")
    ap.add_argument("--out", help="build into this folder instead of demo/knowledge/")
    ap.add_argument("--check", action="store_true",
                    help="build into a temp folder and compare with the committed files")
    args = ap.parse_args(argv)
    if args.check:
        with tempfile.TemporaryDirectory(prefix="make-world-") as tmp:
            build_all(tmp)
            bad = []
            for rel in OUTPUTS.values():
                a, b = Path(tmp) / rel, KNOWLEDGE / rel
                if not b.exists() or not filecmp.cmp(str(a), str(b), shallow=False):
                    bad.append(rel)
            for rel in OUTPUTS.values():
                print(("DIFF " if rel in bad else "same ") + "demo/knowledge/" + rel)
            return 1 if bad else 0
    root = Path(args.out) if args.out else KNOWLEDGE
    for p in build_all(root):
        print("wrote", p.relative_to(REPO) if REPO in p.resolve().parents else p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
