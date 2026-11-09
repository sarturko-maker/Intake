"""Tests for the two look-up tools: tools/area-lines (matching lines of an area's playbook, intake notes and a
subject file) and tools/redline-changes (tracked changes and comments of a .docx with clause numbers)."""

import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsfixture import Workspace  # noqa: E402

PLAYBOOK = """---
status: draft
---
# Commercial playbook

## Signing
### Who signs
Contracts above EUR 250,000 are signed by two directors.
A letter of authority (LOA) lets the country manager sign below that.
The LOA register is kept by the company secretary.

Unrelated paragraph far below.

## Liability
Our usual cap is 100% of annual fees.
"""

INTAKE = """# Commercial intake notes

## Routing
NDAs from sales go to the contracts team.
"""

SUBJECT = """---
subject: acme
name: Acme Automotive GmbH
---
# Acme Automotive

Their signatory is the Geschaeftsfuehrer (2026-0003 matter.md).
"""


class AreaLinesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = Workspace(skills=False)
        cls.ws.write("areas/commercial/playbook.md", PLAYBOOK)
        cls.ws.write("areas/commercial/intake.md", INTAKE)
        cls.ws.write("areas/commercial/customers/acme/subject.md", SUBJECT)

    @classmethod
    def tearDownClass(cls):
        cls.ws.cleanup()

    def test_matching_lines_come_with_their_headings(self):
        r = self.ws.run("area-lines", "commercial", "letter of authority|LOA")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("== areas/commercial/playbook.md", r.stdout)
        self.assertIn("[Commercial playbook > Signing > Who signs] A letter of authority (LOA)", r.stdout)
        self.assertIn("The LOA register", r.stdout)
        self.assertNotIn("Unrelated paragraph", r.stdout)
        self.assertNotIn("Our usual cap", r.stdout)
        self.assertIn("areas/commercial/intake.md: no match. Headings: Commercial intake notes; Routing", r.stdout)

    def test_a_few_lines_after_a_match_are_shown(self):
        r = self.ws.run("area-lines", "commercial", "two directors", "--after", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("signed by two directors", r.stdout)
        self.assertIn("A letter of authority", r.stdout)
        self.assertNotIn("LOA register", r.stdout)

    def test_subject_file_is_searched_on_request(self):
        r = self.ws.run("area-lines", "commercial", "signatory", "--subject", "acme")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("== areas/commercial/customers/acme/subject.md", r.stdout)
        self.assertIn("Geschaeftsfuehrer", r.stdout)

    def test_no_match_lists_headings_and_exits_1(self):
        r = self.ws.run("area-lines", "commercial", "escrow")
        self.assertEqual(r.returncode, 1)
        self.assertIn("playbook.md: no match. Headings: Commercial playbook; Signing; Who signs; Liability", r.stdout)

    def test_usage_errors(self):
        self.assertEqual(self.ws.run("area-lines", "nosuch", "x").returncode, 2)
        self.assertEqual(self.ws.run("area-lines", "commercial", "(unclosed").returncode, 2)
        self.assertEqual(self.ws.run("area-lines", "commercial", "x", "--subject", "nobody").returncode, 2)


# ---------------------------------------------------------------------------------------------- redline

NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/'
        'package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')


def run(text):
    return '<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % text


def ins(text, who="Jane Roe", date="2026-10-30T10:00:00Z"):
    return '<w:ins w:id="1" w:author="%s" w:date="%s">%s</w:ins>' % (who, date, run(text))


def dele(text, who="Jane Roe", date="2026-10-30T10:00:00Z"):
    return ('<w:del w:id="2" w:author="%s" w:date="%s"><w:r><w:delText xml:space="preserve">%s</w:delText>'
            '</w:r></w:del>' % (who, date, text))


def para(*parts, num=None, ilvl=0, style=None):
    ppr = ""
    if style or num is not None:
        ppr = "<w:pPr>%s%s</w:pPr>" % ('<w:pStyle w:val="%s"/>' % style if style else "",
                                       '<w:numPr><w:ilvl w:val="%d"/><w:numId w:val="%s"/></w:numPr>' % (ilvl, num)
                                       if num is not None else "")
    return "<w:p>%s%s</w:p>" % (ppr, "".join(parts))


NUMBERING = ('<w:numbering %s><w:abstractNum w:abstractNumId="0">'
             '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%%1."/></w:lvl>'
             '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%%1.%%2"/></w:lvl>'
             '<w:lvl w:ilvl="2"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="(%%3)"/></w:lvl>'
             '</w:abstractNum>'
             '<w:abstractNum w:abstractNumId="1">'
             '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="Heading1"/>'
             '<w:lvlText w:val="Article %%1"/></w:lvl>'
             '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="Heading2"/>'
             '<w:lvlText w:val="%%1.%%2"/></w:lvl></w:abstractNum>'
             '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
             '<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num></w:numbering>' % NS)

STYLES = ('<w:styles %s><w:style w:type="paragraph" w:styleId="Heading1"><w:pPr><w:numPr><w:numId w:val="2"/>'
          '</w:numPr></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:basedOn w:val="Heading1"/>'
          '</w:style><w:style w:type="paragraph" w:styleId="Body"/></w:styles>' % NS)


def make_docx(path, body, numbering=None, styles=None, comments=None, footnotes=None, extra=None):
    with zipfile.ZipFile(str(path), "w") as z:
        for name, data in (extra or {}).items():
            z.writestr(name, data)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8"?><w:document %s><w:body>%s'
                   '</w:body></w:document>' % (NS, body))
        if numbering:
            z.writestr("word/numbering.xml", numbering)
        if styles:
            z.writestr("word/styles.xml", styles)
        if comments:
            z.writestr("word/comments.xml", '<w:comments %s>%s</w:comments>' % (NS, comments))
        if footnotes:
            z.writestr("word/footnotes.xml", '<w:footnotes %s><w:footnote w:id="1">%s</w:footnote></w:footnotes>'
                       % (NS, footnotes))
    return path


class RedlineChangesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = Workspace(skills=False)
        d = cls.ws.path("docs")
        d.mkdir()
        comment = ('<w:comment w:id="7" w:author="John Smith" w:date="2026-10-31T09:00:00Z"><w:p>'
                   + run("Too low for us.") + '</w:p></w:comment>')
        cls.auto = make_docx(d / "auto.docx", "".join([
            para(run("Master Services Agreement"), ins(" (draft 2)")),
            para(run("Definitions"), num=1),
            para(run("Words have meanings."), num=1, ilvl=1),
            para(run("Liability"), num=1),
            para(run("The cap is "), dele("twelve (12)"), ins("six (6)"), run(" months' fees."), num=1, ilvl=1),
            para(run("Each party is liable for "), '<w:commentRangeStart w:id="7"/>', run("the cap"),
                 '<w:commentRangeEnd w:id="7"/>', '<w:r><w:commentReference w:id="7"/></w:r>', num=1, ilvl=2),
            para(run("Body text under (a) "), ins("with an addition", who="John Smith")),
            para(run("Payment"), num=1),
            para('<w:r><w:rPr><w:b/><w:rPrChange w:id="9" w:author="Jane Roe"><w:rPr/></w:rPrChange></w:rPr>'
                 '<w:t>Invoices monthly.</w:t></w:r>', num=1, ilvl=1),
        ]), NUMBERING, STYLES, comment)
        cls.typed = make_docx(d / "typed.docx", "".join([
            para(run("2.1 The Supplier shall "), dele("promptly ")),
            para(run("(a) notify the Customer"), ins(" in writing")),
            para(run("12.1 Notices go by email"), ins(" or post")),
            para(run("Schedule 2")),
            para(run("1.1 Service levels are "), ins("99.9%")),
            para(run("Moved: "), '<w:moveFrom w:id="3" w:author="Jane Roe" w:date="2026-10-30T10:00:00Z">'
                 + run("old place") + '</w:moveFrom>'),
            para('<w:moveTo w:id="4" w:author="Jane Roe" w:date="2026-10-30T10:00:00Z">' + run("new place")
                 + '</w:moveTo>'),
            para('<w:ins w:id="5" w:author="Jane Roe" w:date="2026-10-30T10:00:00Z"><w:del w:id="6" '
                 'w:author="John Smith" w:date="2026-10-31T10:00:00Z"><w:r><w:delText>added then removed'
                 '</w:delText></w:r></w:del></w:ins>'),
        ]), footnotes=para(run("See the "), ins("revised "), run("annex.")))
        cls.styled = make_docx(d / "styled.docx", "".join([
            para(run("Scope"), style="Heading1"),
            para(run("Purpose"), style="Heading1"),
            para(run("The purpose is "), ins("limited"), style="Heading2"),
        ]), NUMBERING, STYLES)
        w14 = 'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"'
        thread = "".join(
            '<w:comment w:id="%s" w:author="%s" w:date="2026-11-0%sT09:00:00Z"><w:p w14:paraId="%s" %s>%s</w:p>'
            '</w:comment>' % (cid, who, day, pid, w14, run(text)) for cid, who, day, pid, text in (
                ("1", "Jane Roe", "1", "AAAA0001", "Why six months?"),
                ("2", "John Smith", "2", "AAAA0002", "Market standard for this spend."),
                ("3", "Jane Roe", "3", "AAAA0003", "Typo fixed.")))
        ext = ('<w15:commentsEx xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">'
               '<w15:commentEx w15:paraId="AAAA0001" w15:done="0"/>'
               '<w15:commentEx w15:paraId="AAAA0002" w15:paraIdParent="AAAA0001" w15:done="0"/>'
               '<w15:commentEx w15:paraId="AAAA0003" w15:done="1"/></w15:commentsEx>')
        cls.threads = make_docx(d / "threads.docx", "".join([
            para(run("1.1 The cap is "), '<w:commentRangeStart w:id="1"/>', run("six months"),
                 '<w:commentRangeEnd w:id="1"/>', '<w:r><w:commentReference w:id="1"/></w:r>',
                 '<w:r><w:commentReference w:id="2"/></w:r>'),
            para(run("1.2 Teh parties "), '<w:commentRangeStart w:id="3"/>', run("agree"),
                 '<w:commentRangeEnd w:id="3"/>', '<w:r><w:commentReference w:id="3"/></w:r>'),
        ]), comments=thread, extra={"word/commentsExtended.xml": ext})
        cls.clean = make_docx(d / "clean.docx", para(run("Nothing changed here.")))
        (d / "notes.txt").write_text("not a word file", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.ws.cleanup()

    def redline(self, *args):
        r = self.ws.run("redline-changes", *args)
        return r.returncode, r.stdout, r.stderr

    def test_automatic_numbering_gives_clause_numbers(self):
        rc, out, err = self.redline(self.auto)
        self.assertEqual(rc, 0, err)
        self.assertIn('para 1 | inserted | Jane Roe | 2026-10-30 | "(draft 2)"', out)
        self.assertIn('clause 2.1 | deleted | Jane Roe | 2026-10-30 | "twelve (12)"', out)
        self.assertIn('clause 2.1 | inserted | Jane Roe | 2026-10-30 | "six (6)"', out)
        self.assertIn('reads: "The cap is [-twelve (12)-]{+six (6)+} months\' fees."', out)
        self.assertIn('clause 2.1(a) | comment | John Smith | 2026-10-31 | "Too low for us." on "the cap"', out)
        self.assertIn('clause 2.1(a) | inserted | John Smith | 2026-10-30 | "with an addition"', out)
        self.assertIn("-- 5 items in 4 paragraphs. Jane Roe: 2 inserted, 1 deleted. John Smith: 1 comment, "
                      "1 inserted. 1 formatting change, not listed.", out)
        self.assertNotIn("Words have meanings", out)
        self.assertNotIn("Invoices monthly", out)

    def test_typed_numbers_schedules_moves_and_footnotes(self):
        rc, out, err = self.redline(self.typed)
        self.assertEqual(rc, 0, err)
        self.assertIn('clause 2.1 | deleted | Jane Roe | 2026-10-30 | "promptly"', out)
        self.assertIn('clause 2.1(a) | inserted | Jane Roe | 2026-10-30 | "in writing"', out)
        self.assertIn('clause 12.1 | inserted', out)
        self.assertIn('schedule 2 para 1.1 | inserted | Jane Roe | 2026-10-30 | "99.9%"', out)
        self.assertIn('| moved away | Jane Roe | 2026-10-30 | "old place"', out)
        self.assertIn('| moved here | Jane Roe | 2026-10-30 | "new place"', out)
        self.assertIn('| deleted | John Smith | 2026-10-31 | "added then removed"', out)
        self.assertIn('footnote | inserted | Jane Roe | 2026-10-30 | "revised"', out)

    def test_numbering_from_heading_styles(self):
        rc, out, err = self.redline(self.styled)
        self.assertEqual(rc, 0, err)
        self.assertIn('clause 2.1 | inserted | Jane Roe | 2026-10-30 | "limited"', out)

    def test_one_clause_and_its_sub_clauses(self):
        rc, out, _ = self.redline(self.typed, "--clause", "2")
        self.assertEqual(rc, 0)
        self.assertIn("clause 2.1 |", out)
        self.assertIn("clause 2.1(a) |", out)
        self.assertNotIn("clause 12.1", out)
        self.assertNotIn("schedule 2", out)
        rc, out, _ = self.redline(self.typed, "--clause", "schedule 2")
        self.assertIn("schedule 2 para 1.1", out)
        self.assertNotIn("clause 2.1", out)
        rc, out, _ = self.redline(self.typed, "--clause", "7")
        self.assertEqual(rc, 0)
        self.assertIn("no tracked changes or comments in clause 7", out)

    def test_summary_and_no_context(self):
        rc, out, _ = self.redline(self.auto, "--summary")
        self.assertEqual(rc, 0)
        self.assertIn("clause 2.1 | 1 deleted, 1 inserted | Jane Roe", out)
        self.assertIn("clause 2.1(a) | 1 comment, 1 inserted | John Smith", out)
        self.assertNotIn("reads:", out)
        rc, out, _ = self.redline(self.auto, "--no-context")
        self.assertNotIn("reads:", out)
        self.assertIn('clause 2.1 | deleted', out)

    def test_comment_replies_and_resolved_comments(self):
        rc, out, err = self.redline(self.threads)
        self.assertEqual(rc, 0, err)
        self.assertIn('clause 1.1 | comment | Jane Roe | 2026-11-01 | "Why six months?" on "six months"', out)
        self.assertIn('clause 1.1 | reply | John Smith | 2026-11-02 | "Market standard for this spend." '
                      '(reply to Jane Roe)', out)
        self.assertIn('clause 1.2 | comment | Jane Roe | 2026-11-03 | "Typo fixed." on "agree" (resolved)', out)
        self.assertIn("Jane Roe: 2 comments. John Smith: 1 reply.", out)
        self.assertNotIn("reads:", out)

    def test_no_changes_and_unreadable_files(self):
        rc, out, _ = self.redline(self.clean)
        self.assertEqual(rc, 0)
        self.assertIn("no tracked changes or comments", out)
        rc, out, err = self.redline(self.ws.path("docs/notes.txt"))
        self.assertEqual(rc, 2)
        self.assertIn("not a readable .docx", err)
        self.assertEqual(self.ws.run("redline-changes").returncode, 2)


if __name__ == "__main__":
    unittest.main()
