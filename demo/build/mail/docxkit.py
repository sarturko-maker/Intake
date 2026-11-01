"""Helpers on top of python-docx 1.2 for the demo attachments.

What python-docx does not do on its own, and the demo needs:
- byte-identical output on every run (fixed core properties, fixed zip entry times);
- real tracked changes: w:ins and w:del with w:author and w:date;
- Word comments anchored around those changes (the comment part itself comes from
  python-docx 1.2; its date is overwritten so it is fixed too).

Dev tool. Python 3.8+, python-docx 1.2.
"""

import datetime as dt
import io
import re
import zipfile

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ZIP_TIME = (2026, 10, 1, 0, 0, 0)


class Ins:
    """Inserted text (a tracked insertion)."""

    def __init__(self, text):
        self.text = text


class Del:
    """Deleted text (a tracked deletion)."""

    def __init__(self, text):
        self.text = text


class B:
    """Bold text."""

    def __init__(self, text):
        self.text = text


class I:  # noqa: E742 - short on purpose, used inline in content tables
    """Italic text."""

    def __init__(self, text):
        self.text = text


def _iso(when):
    return when.strftime("%Y-%m-%dT%H:%M:00Z")


class Doc:
    """A Word document with fixed metadata and optional tracked changes.

    author/created/modified describe the file; change_author/change_date are used
    for every tracked change and comment unless given per call.
    """

    def __init__(self, title, author, created, modified, header=None, footer=None,
                 change_author=None, change_date=None, font="Calibri", size=10.5,
                 revision=1, company=""):
        self.d = Document()
        self.title_text = title
        self.author = author
        self.created = created
        self.modified = modified
        self.revision = revision
        self.company = company
        self.change_author = change_author or author
        self.change_date = change_date or modified
        self._rev_id = 900
        normal = self.d.styles["Normal"]
        normal.font.name = font
        normal.font.size = Pt(size)
        normal.paragraph_format.space_after = Pt(6)
        for sec in self.d.sections:
            sec.page_height = Cm(29.7)
            sec.page_width = Cm(21.0)
            sec.left_margin = sec.right_margin = Cm(2.3)
            sec.top_margin = Cm(2.2)
            sec.bottom_margin = Cm(2.0)
            if header:
                hp = sec.header.paragraphs[0]
                hp.text = header
                hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                for r in hp.runs:
                    r.font.size = Pt(8)
            if footer:
                fp = sec.footer.paragraphs[0]
                fp.text = footer
                fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in fp.runs:
                    r.font.size = Pt(8)

    # ------------------------------------------------------------ blocks

    def title(self, text, sub=None):
        p = self.d.add_paragraph(style="Title")
        p.add_run(text)
        if sub:
            s = self.d.add_paragraph(style="Subtitle")
            s.add_run(sub)
        return p

    def heading(self, text, level=1, inserted=False):
        p = self.d.add_paragraph(style="Heading %d" % level)
        if inserted:
            self._fill(p, [Ins(text)])
            self._mark_paragraph(p, "w:ins")
        else:
            p.add_run(text)
        return p

    def para(self, *segments, style=None, align=None, inserted=False, comment=None,
             comment_author=None, comment_initials=None, comment_date=None, indent=None,
             keep=False, size=None):
        """Add a paragraph from segments: str, Ins, Del, B, I.

        inserted=True records the whole paragraph (and its paragraph mark) as inserted.
        comment="text" anchors a Word comment from the first to the last tracked change in
        the paragraph, or around the whole paragraph when it has none.
        """
        p = self.d.add_paragraph(style=style)
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "right":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif align == "justify":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if indent is not None:
            p.paragraph_format.left_indent = Cm(indent)
        if keep:
            p.paragraph_format.keep_with_next = True
        segs = list(segments)
        if inserted:
            segs = [s if isinstance(s, (Ins, Del)) else Ins(s.text if hasattr(s, "text") else s)
                    for s in segs]
        self._fill(p, segs, size=size)
        if inserted:
            self._mark_paragraph(p, "w:ins")
        if comment:
            self.add_comment(p, comment, author=comment_author, initials=comment_initials,
                             date=comment_date)
        return p

    def bullet(self, *segments, **kw):
        return self.para(*segments, style="List Bullet", **kw)

    def spacer(self):
        return self.d.add_paragraph()

    def table(self, header, rows, widths=None, style="Table Grid", font_size=9,
              header_bold=True):
        t = self.d.add_table(rows=1, cols=len(header))
        t.style = self.d.styles[style]
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(header):
            cell = t.rows[0].cells[i]
            cell.text = ""
            r = cell.paragraphs[0].add_run(h)
            r.bold = header_bold
            r.font.size = Pt(font_size)
        self._repeat_header(t.rows[0])
        for row in rows:
            cells = t.add_row().cells
            for i, val in enumerate(row):
                cells[i].text = ""
                parts = str(val).split("\n")
                for j, part in enumerate(parts):
                    para = cells[i].paragraphs[0] if j == 0 else cells[i].add_paragraph()
                    run = para.add_run(part)
                    run.font.size = Pt(font_size)
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        return t

    def page_break(self):
        self.d.add_page_break()

    def signature_block(self, lines_left, lines_right):
        t = self.d.add_table(rows=len(lines_left), cols=2)
        for i in range(len(lines_left)):
            t.rows[i].cells[0].text = lines_left[i]
            t.rows[i].cells[1].text = lines_right[i] if i < len(lines_right) else ""
        return t

    # ------------------------------------------------------------ tracked changes

    def _next_id(self):
        self._rev_id += 1
        return self._rev_id

    def _change(self, tag, text, author=None, date=None, size=None):
        el = OxmlElement(tag)
        el.set(qn("w:id"), str(self._next_id()))
        el.set(qn("w:author"), author or self.change_author)
        el.set(qn("w:date"), _iso(date or self.change_date))
        el.append(self._run(text, deleted=(tag == "w:del"), size=size))
        return el

    def _run(self, text, deleted=False, bold=False, italic=False, size=None):
        r = OxmlElement("w:r")
        if bold or italic or size:
            rpr = OxmlElement("w:rPr")
            if bold:
                rpr.append(OxmlElement("w:b"))
            if italic:
                rpr.append(OxmlElement("w:i"))
            if size:
                sz = OxmlElement("w:sz")
                sz.set(qn("w:val"), str(int(size * 2)))
                rpr.append(sz)
            r.append(rpr)
        t = OxmlElement("w:delText" if deleted else "w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = text
        r.append(t)
        return r

    def _fill(self, p, segments, size=None):
        for s in segments:
            if isinstance(s, Ins):
                p._p.append(self._change("w:ins", s.text, size=size))
            elif isinstance(s, Del):
                p._p.append(self._change("w:del", s.text, size=size))
            elif isinstance(s, B):
                p._p.append(self._run(s.text, bold=True, size=size))
            elif isinstance(s, I):
                p._p.append(self._run(s.text, italic=True, size=size))
            else:
                p._p.append(self._run(str(s), size=size))

    def _mark_paragraph(self, p, tag):
        """Record the paragraph mark itself as inserted or deleted."""
        ppr = p._p.get_or_add_pPr()
        rpr = ppr.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            ppr.append(rpr)
        mark = OxmlElement(tag)
        mark.set(qn("w:id"), str(self._next_id()))
        mark.set(qn("w:author"), self.change_author)
        mark.set(qn("w:date"), _iso(self.change_date))
        rpr.append(mark)

    # ------------------------------------------------------------ comments

    def add_comment(self, p, text, author=None, initials=None, date=None):
        """A Word comment over the tracked changes in paragraph p (or the whole paragraph)."""
        author = author or self.change_author
        if initials is None:
            initials = "".join(w[0] for w in author.replace("Dr ", "").split() if w[:1].isalpha())
        c = self.d.comments.add_comment(text=text, author=author, initials=initials)
        c._comment_elm.date = (date or self.change_date).replace(tzinfo=dt.timezone.utc) \
            if (date or self.change_date).tzinfo is None else (date or self.change_date)
        cid = str(c.comment_id)
        changes = [el for el in p._p if el.tag in (qn("w:ins"), qn("w:del"))]
        content = [el for el in p._p if el.tag in (qn("w:ins"), qn("w:del"), qn("w:r"))]
        first, last = (changes[0], changes[-1]) if changes else (content[0], content[-1])
        start = OxmlElement("w:commentRangeStart")
        start.set(qn("w:id"), cid)
        end = OxmlElement("w:commentRangeEnd")
        end.set(qn("w:id"), cid)
        first.addprevious(start)
        last.addnext(end)
        ref = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        rstyle = OxmlElement("w:rStyle")
        rstyle.set(qn("w:val"), "CommentReference")
        rpr.append(rstyle)
        ref.append(rpr)
        cref = OxmlElement("w:commentReference")
        cref.set(qn("w:id"), cid)
        ref.append(cref)
        end.addnext(ref)
        return c

    # ------------------------------------------------------------ output

    @staticmethod
    def _repeat_header(row):
        trpr = row._tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        trpr.append(el)

    def save(self, path=None):
        cp = self.d.core_properties
        cp.title = self.title_text
        cp.author = self.author
        cp.last_modified_by = self.change_author
        cp.created = self.created.replace(tzinfo=None)
        cp.modified = self.modified.replace(tzinfo=None)
        cp.revision = self.revision
        cp.comments = ""
        cp.subject = ""
        cp.keywords = ""
        cp.category = ""
        buf = io.BytesIO()
        self.d.save(buf)
        data = normalise_zip(buf.getvalue(), company=self.company)
        if path:
            with open(path, "wb") as fh:
                fh.write(data)
        return data


def normalise_zip(data, company=""):
    """Rewrite a .docx so the bytes depend only on its content: fixed entry times and
    attributes, and no word-processor product name in docProps/app.xml."""
    zin = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            blob = zin.read(info.filename)
            if info.filename == "docProps/app.xml":
                text = blob.decode("utf-8")
                text = re.sub(r"<Application>[^<]*</Application>", "<Application/>", text)
                text = re.sub(r"<Company\s*/>|<Company>[^<]*</Company>",
                              "<Company>%s</Company>" % company if company else "<Company/>", text)
                blob = text.encode("utf-8")
            zi = zipfile.ZipInfo(info.filename, ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 0
            zi.external_attr = 0
            zout.writestr(zi, blob)
    return out.getvalue()
