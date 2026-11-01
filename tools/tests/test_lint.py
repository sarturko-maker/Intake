"""Tests for tools/lint-facts and tools/lint-received (spec D8, D9)."""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsfixture import TEMPLATES, Workspace, common  # noqa: E402

FACTS_TEMPLATE = (TEMPLATES / "facts.md").read_text(encoding="utf-8")


def fact(fid, recorded="2026-10-15", ftype="term", valid_from="valid_from=",
         source="source=correspondence/a.eml", supersedes="supersedes=", text="A fact"):
    return " | ".join([fid, recorded, ftype, valid_from, source, supersedes, text])


GOOD = [
    fact("F0001", ftype="party", text="Customer is Acme Automotive GmbH"),
    fact("F0002", valid_from="valid_from=2026-10-15", source="source=documents/received/Acme_MSA_v1.docx cl.12",
         text="General cap 200% of annual fees"),
    fact("F0003", recorded="2026-10-27", valid_from="valid_from=2026-10-27",
         source="source=documents/received/Acme_MSA_v3.docx cl.12", supersedes="supersedes=F0002",
         text="General cap 150% of annual fees"),
]


class LintFactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = Workspace(skills=False, house=False)
        cls.n = 0

    @classmethod
    def tearDownClass(cls):
        cls.ws.cleanup()

    def facts(self, lines, header=True, eol="\n"):
        LintFactsTest.n += 1
        text = (FACTS_TEMPLATE if header else "") + "".join(line + "\n" for line in lines)
        p = self.ws.root / ("facts-%d.md" % self.n)
        p.write_bytes(text.replace("\n", eol).encode("utf-8"))
        return p

    def lint(self, *args):
        return self.ws.run("lint-facts", *args)

    def error_lines(self, r):
        return [x for x in r.stdout.splitlines() if x.strip()]

    # ------------------------------------------------------------ clean files

    def test_clean_file(self):
        r = self.lint(self.facts(GOOD))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("3 records, 2 live", r.stdout)

    def test_template_alone_is_clean(self):
        r = self.lint(self.facts([]))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 records", r.stdout)

    def test_crlf_file_is_clean(self):
        r = self.lint(self.facts(GOOD, eol="\r\n"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_several_supersedes_targets(self):
        lines = GOOD + [fact("F0004", supersedes="supersedes=F0001,F0003", text="Replaces two")]
        r = self.lint(self.facts(lines), "--live")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x.split(" | ")[0] for x in r.stdout.splitlines()], ["F0004"])

    # ------------------------------------------------------------ each check

    def test_field_count(self):
        r = self.lint(self.facts(GOOD + ["F0004 | 2026-10-15 | fact | valid_from= | source=x"]))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(self.error_lines(r)), 1, r.stdout)
        self.assertIn(":8: F0004: 5 fields, expected 7", r.stdout)

    def test_extra_separator_in_text_is_an_error(self):
        r = self.lint(self.facts([fact("F0001", text="cap | 150%")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("8 fields, expected 7", r.stdout)

    def test_bad_id(self):
        r = self.lint(self.facts([fact("F01")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("bad id 'F01'", r.stdout)

    def test_duplicate_id(self):
        r = self.lint(self.facts([fact("F0001"), fact("F0001", text="again")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("F0001: duplicate id (first on line 5)", r.stdout)
        self.assertEqual(len(self.error_lines(r)), 1, r.stdout)

    def test_ids_ascend(self):
        r = self.lint(self.facts([fact("F0002"), fact("F0001")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("F0001: id is not above the previous id F0002", r.stdout)

    def test_type(self):
        r = self.lint(self.facts([fact("F0001", ftype="clause")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("type 'clause' is not one of party, term, date, decision, open_point, fact", r.stdout)

    def test_dates(self):
        r = self.lint(self.facts([fact("F0001", recorded="2026-13-01"),
                                  fact("F0002", valid_from="valid_from=31/10/2026")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("recorded '2026-13-01' is not a date", r.stdout)
        self.assertIn("valid_from '31/10/2026' is not a date", r.stdout)

    def test_valid_from_may_be_empty_but_needs_its_key(self):
        self.assertEqual(self.lint(self.facts([fact("F0001", valid_from="valid_from=")])).returncode, 0)
        r = self.lint(self.facts([fact("F0001", valid_from="2026-10-01")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("field 4 must be valid_from=", r.stdout)

    def test_source_required(self):
        r = self.lint(self.facts([fact("F0001", source="source=")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("source= is empty", r.stdout)
        r = self.lint(self.facts([fact("F0001", source="documents/received/x.pdf")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("field 5 must be source=", r.stdout)

    def test_supersedes_target_must_exist_and_come_earlier(self):
        r = self.lint(self.facts([fact("F0001", supersedes="supersedes=F0009"),
                                  fact("F0002", supersedes="supersedes=F0003"),
                                  fact("F0003"),
                                  fact("F0004", supersedes="supersedes=F0004")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("F0001: supersedes F0009, which does not exist", r.stdout)
        self.assertIn("F0002: supersedes F0003, which comes later", r.stdout)
        self.assertIn("F0004: supersedes itself", r.stdout)
        self.assertEqual(len(self.error_lines(r)), 3, r.stdout)

    def test_empty_text(self):
        r = self.lint(self.facts([fact("F0001", text="")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("text is empty", r.stdout)

    def test_one_line_per_error_with_file_and_line(self):
        path = self.facts([fact("F0001", ftype="x", source="source=")])
        r = self.lint(path)
        lines = self.error_lines(r)
        self.assertEqual(len(lines), 2, r.stdout)
        for line in lines:
            self.assertTrue(line.startswith("%s:5: F0001: " % path), line)

    # ------------------------------------------------------------ append-only

    def test_previous_prefix_ok(self):
        old = self.facts(GOOD)
        new = self.facts(GOOD + [fact("F0004", ftype="decision", text="Lawyer accepts 150%")])
        r = self.lint(new, "--previous", old)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_previous_changed_line(self):
        old = self.facts(GOOD)
        changed = list(GOOD)
        changed[1] = changed[1].replace("200%", "250%")
        r = self.lint(self.facts(changed), "--previous", old)
        self.assertEqual(r.returncode, 1)
        self.assertIn("F0002: changed: facts.md is append-only; add a new line with supersedes=F0002 instead", r.stdout)

    def test_previous_removed_line(self):
        old = self.facts(GOOD)
        r = self.lint(self.facts([GOOD[0]]), "--previous", old)
        self.assertEqual(r.returncode, 1)
        self.assertIn("F0002: removed", r.stdout)
        self.assertIn("F0003: removed", r.stdout)

    def test_previous_inserted_before(self):
        old = self.facts(GOOD[1:])
        r = self.lint(self.facts(GOOD), "--previous", old)
        self.assertEqual(r.returncode, 1)
        self.assertIn("F0001: inserted before F0002: add new lines at the end", r.stdout)

    def test_previous_missing_file_skips_the_check(self):
        r = self.lint(self.facts(GOOD), "--previous", self.ws.root / "no-such-file.md")
        self.assertEqual(r.returncode, 0)
        self.assertIn("append-only check skipped", r.stderr)

    # ------------------------------------------------------------ views

    def test_live_view(self):
        r = self.lint(self.facts(GOOD), "--live")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), [GOOD[0], GOOD[2]])

    def test_live_view_with_errors_prints_view_and_errors_on_stderr(self):
        r = self.lint(self.facts(GOOD + [fact("F0004", ftype="bogus")]), "--live")
        self.assertEqual(r.returncode, 1)
        self.assertIn("type 'bogus'", r.stderr)
        self.assertEqual(len(r.stdout.splitlines()), 3)

    def test_as_of_view(self):
        lines = [
            fact("F0001", recorded="2026-10-15", valid_from="valid_from=2026-10-15", text="cap 200%"),
            fact("F0002", recorded="2026-10-27", valid_from="valid_from=2026-10-27", supersedes="supersedes=F0001",
                 text="cap 150%"),
            fact("F0003", recorded="2026-10-20", text="no valid_from: in force from recorded"),
            fact("F0004", recorded="2026-10-28", valid_from="valid_from=2027-01-01", supersedes="supersedes=F0003",
                 text="future change"),
        ]
        path = self.facts(lines)

        def ids(day):
            r = self.lint(path, "--as-of", day)
            self.assertEqual(r.returncode, 0, r.stderr)
            return [x.split(" | ")[0] for x in r.stdout.splitlines()]

        self.assertEqual(ids("2026-10-14"), [])
        self.assertEqual(ids("2026-10-16"), ["F0001"])
        self.assertEqual(ids("2026-10-21"), ["F0001", "F0003"])
        self.assertEqual(ids("2026-10-30"), ["F0002", "F0003"])
        self.assertEqual(ids("2027-01-02"), ["F0002", "F0004"])

    # ------------------------------------------------------------ usage and speed

    def test_usage_errors(self):
        self.assertEqual(self.lint().returncode, 2)
        self.assertEqual(self.lint(self.ws.root / "missing.md").returncode, 2)
        path = self.facts(GOOD)
        self.assertEqual(self.lint(path, "--as-of", "2026-1").returncode, 2)
        self.assertEqual(self.lint(path, "--live", "--as-of", "2026-10-01").returncode, 2)
        self.assertEqual(self.lint(path, "--bogus").returncode, 2)

    def test_help(self):
        r = self.lint("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Usage", r.stdout)
        self.assertIn("Fallback", r.stdout)

    def test_fast_on_a_large_file(self):
        lines = [fact("F%04d" % i, text="fact %d" % i,
                      supersedes=("supersedes=F%04d" % (i - 1)) if i % 3 == 0 else "supersedes=")
                 for i in range(1, 3001)]
        path = self.facts(lines)
        start = time.time()
        r = self.lint(path)
        self.assertEqual(r.returncode, 0, r.stdout[:500])
        self.assertLess(time.time() - start, 10)


class LintReceivedTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(skills=False)
        ws = self.ws
        self.m = ws.make_matter("2026-0002", "commercial", "acme-automotive", "msa-liability-cap",
                                sub_area="customers", title="Acme MSA")
        self.other = ws.make_matter("2026-0003", "commercial", "acme-automotive", "security-questionnaire",
                                    sub_area="customers", title="Acme questionnaire")
        self.eml = self.put("correspondence/2026-10-15_0847_in_jschmidt_acme-msa.eml", b"From: j\n\nbody\n")
        self.doc = self.put("documents/received/Acme_MSA_v1.docx", b"PK\x03\x04 version one")
        self.msg = self.put("correspondence/2026-10-15_0847_in_jschmidt_acme-msa.msg", b"\xd0\xcf\x11\xe0 msg")
        self.ours = self.put("documents/ours/Acme_MSA_v1_Kestrel.docx", b"PK\x03\x04 ours")
        rows = [
            self.row("2026-10-15_0847_in_jschmidt_acme-msa.eml", "correspondence", self.eml),
            self.row("2026-10-15_0847_in_jschmidt_acme-msa.msg", "correspondence", self.msg,
                     read="no: original of 2026-10-15_0847_in_jschmidt_acme-msa.eml"),
            self.row("Acme_MSA_v1.docx", "documents/received", self.doc),
            self.row("image001.png", "documents/received", None, read="no: signature image"),
            self.row("invite.ics", "documents/received", None, read="no: calendar part"),
            self.row("Acme_MSA_v1 (1).docx", "documents/received", self.doc, dup="Acme_MSA_v1.docx"),
        ]
        for r in rows:
            common.append_line(self.m / "documents.md", r)

    def tearDown(self):
        self.ws.cleanup()

    def put(self, relp, data, matter=None):
        p = (matter or self.m) / relp
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def row(self, name, folder, path, read="pending", dup=""):
        h = common.sha256_file(path) if path is not None else ""
        return common.join_pipe([name, folder, "received", "j.schmidt@acme-automotive.de", "2026-10-15 08:47",
                                 "", "b1-04.202610150847@acme-automotive.de", h, read, "", dup])

    def lint(self, *args):
        return self.ws.run("lint-received", *args)

    def test_clean(self):
        r = self.lint()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 findings", r.stdout)
        self.assertIn("in 2 matters", r.stdout)

    def test_changed_file(self):
        self.doc.write_bytes(b"PK\x03\x04 edited")
        r = self.lint()
        self.assertEqual(r.returncode, 1)
        self.assertIn("changed: %s/documents/received/Acme_MSA_v1.docx" % self.ws.rel(self.m), r.stdout)

    def test_changed_msg_original(self):
        self.msg.write_bytes(b"\xd0\xcf\x11\xe0 resaved")
        r = self.lint()
        self.assertEqual(r.returncode, 1)
        self.assertIn("changed:", r.stdout)
        self.assertIn(".msg", r.stdout)

    def test_missing_file(self):
        self.eml.unlink()
        r = self.lint()
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing: %s/correspondence/2026-10-15_0847_in_jschmidt_acme-msa.eml" % self.ws.rel(self.m),
                      r.stdout)

    def test_file_without_row(self):
        self.put("documents/received/dropped-by-hand.pdf", b"%PDF-1.4")
        r = self.lint()
        self.assertEqual(r.returncode, 1)
        self.assertIn("no row: %s/documents/received/dropped-by-hand.pdf" % self.ws.rel(self.m), r.stdout)

    def test_row_without_hash(self):
        p = self.put("documents/received/nohash.pdf", b"%PDF")
        common.append_line(self.m / "documents.md", common.join_pipe(
            ["nohash.pdf", "documents/received", "received", "x", "2026-10-15 08:47", "", "", "", "pending", "", ""]))
        r = self.lint()
        self.assertEqual(r.returncode, 1)
        self.assertIn("no hash: %s" % self.ws.rel(p), r.stdout)

    def test_ours_and_junk_are_not_checked(self):
        self.put("documents/ours/no-row.docx", b"ours")
        self.put("correspondence/.DS_Store", b"junk")
        self.put("documents/received/~$Acme_MSA_v1.docx", b"lock")
        r = self.lint()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_msg_without_row_beside_its_eml_is_the_original(self):
        lines = [x for x in (self.m / "documents.md").read_text().splitlines() if ".msg |" not in x]
        (self.m / "documents.md").write_text("\n".join(lines) + "\n")
        r = self.lint()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_select_matters(self):
        self.put("documents/received/stray.pdf", b"x", matter=self.other)
        r = self.lint("2026-0002")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("in 1 matters", r.stdout)
        r = self.lint(self.ws.rel(self.other))
        self.assertEqual(r.returncode, 1)
        self.assertIn("no row:", r.stdout)

    def test_usage_errors(self):
        self.assertEqual(self.lint("areas/commercial").returncode, 2)
        self.assertEqual(self.lint("2026-0999").returncode, 2)
        self.assertEqual(self.lint("--bogus").returncode, 2)


if __name__ == "__main__":
    unittest.main()
