"""The PDF attachments of the demo corpus (reportlab), invented for the demo.

Deterministic: reportlab runs in invariant mode and every PDF carries a fixed, realistic
creation date, so the bytes are the same on every run.

- Acme_Kestrel_NDA_signed.pdf   the Acme NDA as signed (Kestrel's changes accepted), with the
                                signature blocks filled in.
- PX-400_datasheet.pdf          2 pages: cast iron casing, ductile iron impeller, PN16 (16 bar),
                                90 C, no corrosion-resistant alloy options.
- Volta_Rail_Tender_Terms.pdf   40 pages; contents on page 2; page 23 Liability, page 31
                                Intellectual property and warranty (see tender_text.py).
- Northgate_Invoice_4471.pdf    freight invoice to Kestrel Pumpen GmbH, EUR 18,640.00.
- FlowTech_Catalogue_2027.pdf   4-page seal catalogue (supplier marketing).
"""

import io
import re

from reportlab.graphics.shapes import Drawing, Line, PolyLine, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

import tender_text
from legal_docs import nda_final_paragraphs

W, H = A4
SS = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=SS["Normal"], fontName="Helvetica", fontSize=9.5,
                      leading=12.5, spaceAfter=5)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, leading=10, spaceAfter=3)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=16, leading=20,
                    spaceAfter=10)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=11.5, leading=14,
                    spaceBefore=6, spaceAfter=6)
H3 = ParagraphStyle("h3", parent=BODY, fontName="Helvetica-Bold", fontSize=10, leading=13,
                    spaceBefore=4, spaceAfter=4)
CENTER = ParagraphStyle("center", parent=BODY, alignment=TA_CENTER)
RIGHT = ParagraphStyle("right", parent=BODY, alignment=TA_RIGHT)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.5, leading=10.5, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold")


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def P(text, style=BODY):
    return Paragraph(esc(text), style)


def grid(header, rows, widths, head_bg=colors.HexColor("#DDE4EE"), style_cell=CELL):
    data = [[Paragraph(esc(h), CELLB) for h in header]]
    for r in rows:
        data.append([Paragraph(esc(str(c)), style_cell) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8A94A6")),
        ("BACKGROUND", (0, 0), (-1, 0), head_bg),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _build(path, story, title, author, created, on_page=None, subject="", creator=""):
    """Build a PDF deterministically. created: 'D:YYYYMMDDHHMMSS+HH'MM'' string."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2.3 * cm, bottomMargin=2.0 * cm, title=title, author=author,
                            subject=subject, creator=creator or author, producer=creator or author,
                            invariant=1)

    def first(canv, d):
        canv.setDateFormatter(lambda *a: created)
        if on_page:
            on_page(canv, d)

    def later(canv, d):
        if on_page:
            on_page(canv, d)

    doc.build(story, onFirstPage=first, onLaterPages=later)
    data = buf.getvalue()
    with open(path, "wb") as fh:
        fh.write(data)
    return data


def page_count(data):
    return len(re.findall(rb"/Type /Page[^s]", data))


class Signature(Flowable):
    """A hand-drawn looking signature: a few bezier strokes seeded by the name."""

    def __init__(self, name, width=5.5 * cm, height=1.4 * cm):
        Flowable.__init__(self)
        self.name = name
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        seed = sum(ord(ch) * (i + 1) for i, ch in enumerate(self.name))
        c.setStrokeColor(colors.HexColor("#1B2A6B"))
        c.setLineWidth(1.1)
        x, y = 6, self.height * 0.42
        # opening loop for the initial, then a run of uneven humps, then a trailing flourish
        lift = 14 + seed % 7
        c.bezier(x, y, x - 4, y + lift, x + 10, y + lift + 4, x + 8, y - 2)
        x += 8
        n = 3 + seed % 4
        step = (self.width * (0.55 + (seed % 3) * 0.1)) / n
        for i in range(n):
            k = (seed >> (i % 9)) % 11
            c.bezier(x, y, x + step * 0.25, y + 6 + k, x + step * 0.7, y - 6 - k / 2,
                     x + step, y + (k % 4) - 1)
            x += step
        c.bezier(x, y, x + 10, y + 8, x + 18, y - 10, x + 30, y - 4)
        c.line(4, 3, x * (0.7 + (seed % 2) * 0.2), 5 + seed % 5)


# ======================================================================= signed NDA

def build_signed_nda(path):
    story = [P("MUTUAL NON-DISCLOSURE AGREEMENT", H1),
             P("Execution version", ParagraphStyle("ev", parent=BODY, fontName="Helvetica-Oblique"))]
    for kind, text in nda_final_paragraphs():
        story.append(P(text, H3 if kind == "h" else BODY))
    story.append(Spacer(1, 10))
    story.append(P("Signed by the Parties:", H3))

    def block(entity, signers):
        cells = [[P(entity, CELLB)]]
        for name, title, date in signers:
            cells.append([Signature(name)])
            cells.append([P("Name: " + name, CELL)])
            cells.append([P("Title: " + title, CELL)])
            cells.append([P("Date: " + date, CELL)])
            cells.append([Spacer(1, 6)])
        t = Table(cells, colWidths=[7.6 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        return t

    acme = block("For Acme Automotive GmbH", [
        ("Katrin Albers", "Head of Strategic Purchasing (ppa.)", "14 October 2026"),
        ("Julia Schmidt", "Strategic Purchasing (i.V.)", "14 October 2026"),
    ])
    kestrel = block("For Kestrel Engineering Ltd", [
        ("Chris Barker", "Chief Financial Officer", "13 October 2026"),
    ])
    sig = Table([[acme, kestrel]], colWidths=[8.3 * cm, 8.3 * cm])
    sig.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(KeepTogether([sig]))

    def on_page(canv, d):
        canv.saveState()
        canv.setFont("Helvetica", 7.5)
        canv.drawRightString(W - 2.2 * cm, H - 1.4 * cm,
                             "Acme Automotive GmbH | Mutual NDA | Execution version")
        canv.drawCentredString(W / 2, 1.2 * cm, "Page %d" % canv.getPageNumber())
        canv.restoreState()

    return _build(path, story, "Mutual Non-Disclosure Agreement - signed", "Acme Automotive GmbH",
                  "D:20261014104812+02'00'", on_page)


# ======================================================================= PX-400 datasheet

class Curves(Flowable):
    """Head-flow curves for three PX-400 sizes at 1450 rpm."""

    def __init__(self, width=16.5 * cm, height=7.5 * cm):
        Flowable.__init__(self)
        self.width, self.height = width, height

    def draw(self):
        d = Drawing(self.width, self.height)
        x0, y0 = 40, 30
        w, h = self.width - 60, self.height - 50
        d.add(Line(x0, y0, x0 + w, y0, strokeColor=colors.black))
        d.add(Line(x0, y0, x0, y0 + h, strokeColor=colors.black))
        for q in range(0, 401, 50):
            x = x0 + w * q / 400.0
            d.add(Line(x, y0, x, y0 + h, strokeColor=colors.HexColor("#DDDDDD"), strokeWidth=0.3))
            d.add(String(x, y0 - 12, str(q), fontSize=7, textAnchor="middle"))
        for hh in range(0, 81, 10):
            y = y0 + h * hh / 80.0
            d.add(Line(x0, y, x0 + w, y, strokeColor=colors.HexColor("#DDDDDD"), strokeWidth=0.3))
            d.add(String(x0 - 6, y - 2, str(hh), fontSize=7, textAnchor="end"))
        d.add(String(x0 + w / 2, 4, "Flow Q (m3/h)", fontSize=8, textAnchor="middle"))
        d.add(String(8, y0 + h + 6, "Head H (m)", fontSize=8))
        sizes = [("PX-400-125", 48.0, 210.0, colors.HexColor("#1F5FA8")),
                 ("PX-400-150", 64.0, 300.0, colors.HexColor("#C0392B")),
                 ("PX-400-200", 78.0, 400.0, colors.HexColor("#2E8B57"))]
        for name, h_max, q_max, col in sizes:
            pts = []
            for i in range(0, 41):
                q = q_max * i / 40.0
                head = h_max * (1 - 0.55 * (q / q_max) ** 2)
                pts += [x0 + w * q / 400.0, y0 + h * head / 80.0]
            d.add(PolyLine(pts, strokeColor=col, strokeWidth=1.4))
            d.add(String(x0 + w * q_max / 400.0 - 4, y0 + h * (h_max * 0.45) / 80.0 + 6, name,
                         fontSize=7, fillColor=col, textAnchor="end"))
        d.drawOn(self.canv, 0, 0)


def build_px400_datasheet(path):
    story = [P("Kestrel PX-400 series", H1),
             P("End-suction centrifugal pumps for clean water | Datasheet KE-DS-PX400 rev. C | "
               "October 2026", ParagraphStyle("sub", parent=BODY, fontName="Helvetica-Oblique")),
             P("The PX-400 is a horizontal, single-stage, end-suction centrifugal pump for clean "
               "or slightly contaminated water without abrasive particles. It is used in water "
               "supply and treatment, irrigation, cooling-water circuits, HVAC and general "
               "industrial service. Back pull-out design: the motor, bearing bracket and impeller "
               "can be removed without disturbing the pipework."),
             P("Key data", H2),
             grid(["Parameter", "Value"], [
                 ["Flow rate", "up to 400 m³/h"],
                 ["Head", "up to 80 m"],
                 ["Maximum working pressure", "16 bar (PN16)"],
                 ["Liquid temperature", "-10 °C to +90 °C"],
                 ["Speed", "1450 rpm or 2900 rpm (50 Hz)"],
                 ["Motor power", "7.5 kW to 75 kW, IE3, IP55"],
                 ["Flanges", "PN16, drilled to EN 1092-2"],
                 ["Shaft seal", "Single mechanical seal"],
             ], [6.0 * cm, 10.5 * cm]),
             P("Materials of construction", H2),
             grid(["Part", "Material"], [
                 ["Pump casing", "Grey cast iron EN-GJL-250"],
                 ["Impeller", "Ductile iron EN-GJS-500-7"],
                 ["Casing cover and bearing bracket", "Grey cast iron EN-GJL-250"],
                 ["Shaft", "Carbon steel C45, with replaceable bronze sleeve"],
                 ["Wear rings", "Grey cast iron"],
                 ["Mechanical seal", "Carbon / silicon carbide faces, EPDM elastomers"],
                 ["Casing gasket", "Aramid fibre"],
             ], [6.0 * cm, 10.5 * cm]),
             Spacer(1, 6),
             P("Material options: none. The PX-400 is built in cast iron only. No stainless steel, "
               "nickel alloy, titanium or other corrosion-resistant alloy versions are offered for "
               "this series, and it is not suitable for corrosive liquids, seawater, brine or "
               "chemicals.", ParagraphStyle("note", parent=BODY, fontName="Helvetica-Bold")),
             P("Applications", H2),
             P("Municipal water supply and booster stations; water treatment (clean water side); "
               "irrigation; cooling-water and condenser circuits; heating and air conditioning; "
               "fire-fighting supply (non-certified duty); general industrial transfer of clean "
               "water."),
             PageBreak(),
             P("Performance curves (1450 rpm, water at 20 °C)", H2),
             Curves(),
             P("Curves are typical and based on tests to ISO 9906 Grade 2B. Duty points must be "
               "confirmed by Kestrel's selection software for each order.", SMALL),
             P("Dimensions and weights", H2),
             grid(["Model", "Suction / discharge DN", "Max. motor (kW)", "Length (mm)",
                   "Weight, bare pump (kg)"], [
                 ["PX-400-125", "150 / 125", "30", "1,210", "185"],
                 ["PX-400-150", "200 / 150", "55", "1,420", "260"],
                 ["PX-400-200", "250 / 200", "75", "1,630", "345"],
             ], [3.2 * cm, 3.6 * cm, 2.8 * cm, 2.8 * cm, 4.1 * cm]),
             P("Standards and testing", H2),
             P("Designed to EN 733 dimensions where applicable. Hydrostatic test of casing at "
               "24 bar. Performance test to ISO 9906 Grade 2B on request. UKCA and CE marked."),
             P("Noise", H2),
             P("Sound pressure level at 1 m below 78 dB(A) at 1450 rpm, depending on motor."),
             P("Ordering", H2),
             P("State model, duty point (flow and head), liquid and temperature, motor voltage "
               "and frequency, and any accessories (baseplate, coupling guard, flange adaptors)."),
             ]

    def on_page(canv, d):
        canv.saveState()
        canv.setFillColor(colors.HexColor("#0E3B5C"))
        canv.rect(0, H - 1.2 * cm, W, 1.2 * cm, stroke=0, fill=1)
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 10)
        canv.drawString(2.2 * cm, H - 0.8 * cm, "KESTREL ENGINEERING")
        canv.setFont("Helvetica", 8)
        canv.drawRightString(W - 2.2 * cm, H - 0.8 * cm, "PX-400 datasheet")
        canv.setFillColor(colors.black)
        canv.setFont("Helvetica", 7)
        canv.drawString(2.2 * cm, 1.1 * cm, "Kestrel Engineering Ltd, Sheffield, United Kingdom | "
                        "kestrel-eng.co.uk | Data subject to change without notice")
        canv.drawRightString(W - 2.2 * cm, 1.1 * cm, "Page %d of 2" % canv.getPageNumber())
        canv.restoreState()

    data = _build(path, story, "PX-400 datasheet", "Kestrel Engineering Ltd",
                  "D:20261002113000+01'00'", on_page, subject="Datasheet KE-DS-PX400 rev. C")
    assert page_count(data) == 2, page_count(data)
    return data


# ======================================================================= Volta tender (40 pages)

def build_volta_tender(path):
    starts = {}

    class Marker(Flowable):
        def __init__(self, key):
            Flowable.__init__(self)
            self.key = key
            self.width = self.height = 0

        def draw(self):
            starts[self.key] = self.canv.getPageNumber()

    def blocks(items):
        out = []
        for b in items:
            if isinstance(b, tuple) and b[0] == "table":
                _, header, rows = b
                n = len(header)
                total = 16.6 * cm
                widths = [total / n] * n
                if n == 2:
                    widths = [10.6 * cm, 6.0 * cm]
                if n == 3:
                    widths = [5.0 * cm, 7.6 * cm, 4.0 * cm]
                if n == 5:
                    widths = [1.2 * cm, 6.4 * cm, 1.4 * cm, 3.6 * cm, 4.0 * cm]
                out.append(grid(header, rows, widths))
                out.append(Spacer(1, 6))
            else:
                out.append(P(b))
        return out

    story = [Spacer(1, 4 * cm),
             P("VOLTA RAIL LTD", ParagraphStyle("c1", parent=H1, alignment=TA_CENTER, fontSize=22)),
             Spacer(1, 1 * cm),
             P("Invitation to Tender " + tender_text.ITT_REF,
               ParagraphStyle("c2", parent=H2, alignment=TA_CENTER, fontSize=14)),
             P(tender_text.TITLE, ParagraphStyle("c3", parent=H2, alignment=TA_CENTER)),
             Spacer(1, 0.6 * cm),
             P("Conditions of Tender and Contract", CENTER),
             Spacer(1, 3 * cm),
             P("Issued: 9 October 2026", CENTER),
             P("Tender return deadline: 12:00 on Friday 30 October 2026", CENTER),
             P("Enquiries: through the tender portal or tenders@voltarail.co.uk", CENTER),
             Spacer(1, 3 * cm),
             P("This document is confidential and is issued only to organisations invited to "
               "tender.", ParagraphStyle("c4", parent=SMALL, alignment=TA_CENTER)),
             PageBreak()]

    # contents (page 2)
    rows = []
    current = None
    for no, title, part, _ in tender_text.SECTIONS:
        if part != current:
            rows.append([tender_text.PARTS[part], "", ""])
            current = part
        rows.append([str(no), title, str(no + 2)])
    rows.append([tender_text.PARTS["X"], "", ""])
    for i, (code, title, _) in enumerate(tender_text.APPENDICES):
        rows.append([code, title, str(39 + i)])
    rows.insert(0, ["Section", "Title", "Page"])
    data = []
    styles = [("FONTSIZE", (0, 0), (-1, -1), 8.5), ("LEADING", (0, 0), (-1, -1), 10.2),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2), ("TOPPADDING", (0, 0), (-1, -1), 1.2),
              ("ALIGN", (2, 0), (2, -1), "RIGHT"),
              ("FONTNAME", (0, 0), (2, 0), "Helvetica-Bold"),
              ("LINEBELOW", (0, 0), (2, 0), 0.5, colors.black)]
    for i, r in enumerate(rows):
        if i and r[1] == "" and r[2] == "":
            data.append([r[0], "", ""])
            styles.append(("SPAN", (0, i), (2, i)))
            styles.append(("FONTNAME", (0, i), (2, i), "Helvetica-Bold"))
            styles.append(("TOPPADDING", (0, i), (2, i), 5))
        else:
            data.append(r)
    toc = Table(data, colWidths=[2.2 * cm, 12.4 * cm, 2.0 * cm])
    toc.setStyle(TableStyle(styles))
    story += [P("Contents", H1), toc, Spacer(1, 6),
              P("Appendix B (technical specification) and Appendix C (depot drawings) are issued "
                "separately through the tender portal.", SMALL),
              PageBreak()]

    current = None
    for no, title, part, body in tender_text.SECTIONS:
        head = []
        if part != current:
            head.append(P(tender_text.PARTS[part], ParagraphStyle("pt", parent=SMALL,
                                                                  fontName="Helvetica-Oblique")))
            current = part
        story.append(Marker(no))
        story += head
        story.append(P("%d. %s" % (no, title), H2))
        story += blocks(body)
        story.append(PageBreak())
    for i, (code, title, body) in enumerate(tender_text.APPENDICES):
        story.append(Marker(code))
        story.append(P("%s - %s" % (code, title), H2))
        story += blocks(body)
        if i < len(tender_text.APPENDICES) - 1:
            story.append(PageBreak())

    def on_page(canv, d):
        n = canv.getPageNumber()
        canv.saveState()
        canv.setFont("Helvetica", 7.5)
        if n > 1:
            canv.drawString(2.2 * cm, H - 1.4 * cm, "Volta Rail Ltd | ITT " + tender_text.ITT_REF)
            canv.drawRightString(W - 2.2 * cm, H - 1.4 * cm, "Conditions of Tender and Contract")
            canv.line(2.2 * cm, H - 1.5 * cm, W - 2.2 * cm, H - 1.5 * cm)
        canv.drawCentredString(W / 2, 1.2 * cm, "Page %d of 40 | Commercial in confidence" % n)
        canv.restoreState()

    data = _build(path, story, "ITT " + tender_text.ITT_REF + " Conditions of Tender and Contract",
                  "Volta Rail Ltd", "D:20261009160514+01'00'", on_page,
                  subject=tender_text.TITLE)
    assert page_count(data) == 40, page_count(data)
    for no, _, _, _ in tender_text.SECTIONS:
        assert starts[no] == no + 2, (no, starts[no])
    assert starts["Appendix A"] == 39 and starts["Appendix D"] == 40, starts
    return data


# ======================================================================= Northgate invoice

def build_northgate_invoice(path):
    lines = [
        ["1", "Groupage road freight Sheffield (GB) - Dortmund (DE), consignment NL-260812-01, "
              "6 pallets, collected 12.08.2026", "4,150.00"],
        ["2", "Groupage road freight Sheffield (GB) - Dortmund (DE), consignment NL-260819-04, "
              "8 pallets, collected 19.08.2026", "5,550.00"],
        ["3", "Full load Sheffield (GB) - Dortmund (DE), consignment NL-260826-02, 13.6 ldm, "
              "collected 26.08.2026", "6,300.00"],
        ["4", "Fuel surcharge 10% on lines 1-3", "1,600.00"],
        ["5", "Export and import customs declarations, 3 consignments at 280.00", "840.00"],
        ["6", "Tail-lift delivery surcharge, 2 deliveries at 100.00", "200.00"],
    ]
    story = [P("Northgate Logistics Ltd", H1),
             P("Hull, United Kingdom | accounts@northgate-logistics.com | VAT reg. GB 000 0000 00",
               SMALL),
             Spacer(1, 10),
             P("INVOICE 4471", H2),
             grid(["Invoice number", "Invoice date", "Due date", "Customer account", "Your reference"],
                  [["4471", "31 August 2026", "30 September 2026", "KPG-0193",
                    "PO 4500-2026-0318"]],
                  [3.0 * cm, 3.0 * cm, 3.2 * cm, 3.3 * cm, 4.1 * cm]),
             Spacer(1, 8),
             P("Invoice to: Kestrel Pumpen GmbH, Accounts Payable, Dortmund, Germany"),
             Spacer(1, 6),
             grid(["Line", "Description", "Amount (EUR)"], lines,
                  [1.2 * cm, 12.4 * cm, 3.0 * cm]),
             Spacer(1, 6),
             grid(["", "EUR"], [["Net total", "18,640.00"],
                                ["VAT 0% (international freight transport)", "0.00"],
                                ["Invoice total", "18,640.00"]],
                  [13.6 * cm, 3.0 * cm]),
             Spacer(1, 12),
             P("Payment terms: 30 days net. Please quote invoice number 4471 with your payment."),
             P("Bank: account name Northgate Logistics Ltd, IBAN GB00 NGLX 0000 0000 4471 00 "
               "(illustrative), BIC NGLXGB00XXX."),
             P("All services are provided under Northgate Logistics standard trading conditions "
               "(2025 edition). Claims for loss of or damage to goods must be notified in writing "
               "within 7 days of delivery (clause 14). Charges are payable in full without set-off "
               "or deduction (clause 18). Interest on late payment is charged under clause 19.",
               SMALL),
             ]

    def on_page(canv, d):
        canv.saveState()
        canv.setFillColor(colors.HexColor("#2C4A3E"))
        canv.rect(0, H - 0.8 * cm, W, 0.8 * cm, stroke=0, fill=1)
        canv.setFont("Helvetica", 7)
        canv.setFillColor(colors.black)
        canv.drawCentredString(W / 2, 1.1 * cm, "Northgate Logistics Ltd | Registered in England "
                               "and Wales | Company no. 00000000")
        canv.restoreState()

    return _build(path, story, "Invoice 4471", "Northgate Logistics Ltd",
                  "D:20260831170204+01'00'", on_page)


# ======================================================================= FlowTech catalogue

def build_flowtech_catalogue(path):
    big = ParagraphStyle("big", parent=H1, fontSize=30, leading=36, textColor=colors.HexColor("#0B6E99"))
    story = [Spacer(1, 5 * cm), P("FlowTech Seals", big),
             P("Catalogue 2027", ParagraphStyle("big2", parent=H1, fontSize=22, leading=26)),
             P("Mechanical seals for water and wastewater pumps",
               ParagraphStyle("big3", parent=H2, fontSize=14)),
             Spacer(1, 4 * cm),
             P("New for 2027: FT-Cartridge 50 series for end-suction pumps up to 16 bar"),
             P("Next-day dispatch on more than 400 stock items from our UK warehouse"),
             PageBreak(),
             P("Product range", H1),
             grid(["Series", "Type", "Shaft size (mm)", "Max. pressure (bar)", "Temperature (°C)",
                   "Faces"], [
                 ["FT-100", "Single spring, unbalanced", "12 - 60", "10", "-20 to +100",
                  "Carbon / ceramic"],
                 ["FT-200", "Elastomer bellows", "16 - 75", "12", "-20 to +120",
                  "Carbon / silicon carbide"],
                 ["FT-300", "Multi-spring, balanced", "25 - 100", "25", "-30 to +180",
                  "SiC / SiC or TC / TC"],
                 ["FT-Cartridge 50", "Cartridge, single", "25 - 100", "16", "-20 to +120",
                  "SiC / SiC or carbon / SiC"],
                 ["FT-Cartridge 70", "Cartridge, double", "30 - 100", "25", "-30 to +150",
                  "SiC / SiC"],
             ], [3.0 * cm, 3.6 * cm, 2.4 * cm, 2.4 * cm, 2.6 * cm, 2.6 * cm]),
             Spacer(1, 10),
             P("Elastomers: NBR, EPDM (drinking-water approved grades available), FKM. Springs and "
               "metal parts in stainless steel 1.4401 as standard."),
             P("All seals are supplied with installation instructions and a declaration of "
               "conformity. Drinking-water approvals are listed by grade on our website."),
             PageBreak(),
             P("FT-Cartridge 50: fitted in minutes", H1),
             P("The FT-Cartridge 50 is a pre-assembled single cartridge seal for end-suction and "
               "inline pumps. It fits standard seal chambers without machining and is set at the "
               "factory, so it can be installed without measuring."),
             grid(["Feature", "Benefit"], [
                 ["Pre-set cartridge", "No setting errors; installation in under 15 minutes"],
                 ["Hydraulically balanced faces", "Longer life at pressures up to 16 bar"],
                 ["Flush and quench connections", "Suitable for dirty water with a clean flush"],
                 ["Interchangeable with common component seals", "One stock item covers several "
                                                                 "pump makes"],
             ], [6.0 * cm, 10.6 * cm]),
             Spacer(1, 10),
             P("Typical applications: water supply, irrigation, cooling water, district heating, "
               "light wastewater."),
             PageBreak(),
             P("Ordering and service", H1),
             P("Order by phone, by email to sales@flowtechseals.com, or through our online shop. "
               "Orders placed by 15:00 on a working day are dispatched the same day for stock items."),
             P("Introductory offer: 10% off your first order placed before 31 December 2026 with "
               "code CAT2027."),
             P("Seal repair service: send us used cartridge seals for refurbishment, typically "
               "returned within 5 working days with a new test certificate."),
             P("Prices exclude VAT and delivery. Our terms and conditions of sale apply and are "
               "available on request.", SMALL),
             ]

    def on_page(canv, d):
        n = canv.getPageNumber()
        canv.saveState()
        canv.setFillColor(colors.HexColor("#0B6E99"))
        canv.rect(0, 0, W, 1.0 * cm, stroke=0, fill=1)
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica", 8)
        canv.drawString(2.2 * cm, 0.4 * cm, "FlowTech Seals | marketing@flowtechseals.com")
        canv.drawRightString(W - 2.2 * cm, 0.4 * cm, "Catalogue 2027 | %d" % n)
        canv.restoreState()

    data = _build(path, story, "FlowTech Seals Catalogue 2027", "FlowTech Seals",
                  "D:20261020093000+01'00'", on_page)
    assert page_count(data) == 4, page_count(data)
    return data
