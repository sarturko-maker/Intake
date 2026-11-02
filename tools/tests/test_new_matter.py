"""Tests for tools/new-matter. Also holds the shared temporary-workspace scaffolding used by
test_scan, test_unpack and test_place (class Workspace).

Run: python3 -m unittest discover -s tools/tests -p 'test_*.py'
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS / "lib"))
sys.path.insert(0, str(HERE))

import common  # noqa: E402

HOUSE_BRIEF = """---
status: ready
organisation: Kestrel Engineering
legal_entities: Kestrel Engineering Ltd, Kestrel Pumpen GmbH
house_domains: kestrel-eng.co.uk, kestrel-eng.de
legal_addresses: alex.morgan@kestrel-eng.co.uk, legal@kestrel-eng.co.uk
intake_mailbox: legal@kestrel-eng.co.uk
timezone: Europe/London
reference_prefix: {prefix}
lawyer_name: Alex Morgan
---
Test house brief.
"""

HOUSE_AREAS = """---
status: ready
---
## commercial
- key: commercial
- name: Commercial
- code: COM
- unit_label: matter
- description: Customer, supplier and partner contracts and questions.
- sub_areas: customers, suppliers, partners, internal
- subject_rule: counterparty company, slug of its short name (acme-automotive)
- examples: NDA review; MSA negotiation

## corporate
- key: corporate
- name: Corporate
- code: COR
- unit_label: matter
- description: Entities and signing authority.
- sub_areas: none
- subject_rule: topic
- examples: signing authority

## trade-compliance
- key: trade-compliance
- name: Trade compliance
- code: TRD
- unit_label: matter
- description: Export control, sanctions and customs.
- sub_areas: exports, sanctions, customs
- subject_rule: product or destination
- examples: dual-use query
"""


def london_available():
    try:
        from zoneinfo import ZoneInfo  # noqa: F401  # novm (guarded: Python 3.8 has no zoneinfo)
        ZoneInfo("Europe/London")
        return True
    except Exception:
        return False


HAVE_LONDON = london_available()


class Workspace:
    """A throwaway workspace: RULES.md, tools/ (link or copy), templates, house files, inbox."""

    def __init__(self, prefix=""):
        self._tmp = tempfile.TemporaryDirectory(prefix="intake-test-")
        self.root = Path(self._tmp.name).resolve()
        r = self.root
        (r / "RULES.md").write_text("# Rules (test workspace)\n", encoding="utf-8")
        try:
            os.symlink(str(TOOLS), str(r / "tools"), target_is_directory=True)
        except (OSError, NotImplementedError):
            shutil.copytree(str(TOOLS), str(r / "tools"),
                            ignore=shutil.ignore_patterns("tests", "__pycache__"))
        tdst = r / "skills" / "operations" / "matter-memory" / "templates"
        shutil.copytree(str(ROOT / "skills" / "operations" / "matter-memory" / "templates"), str(tdst))
        (r / "house").mkdir()
        (r / "house" / "brief.md").write_text(HOUSE_BRIEF.format(prefix=prefix), encoding="utf-8")
        (r / "house" / "areas.md").write_text(HOUSE_AREAS, encoding="utf-8")
        for d in ("inbox/noise/confirmed", "inbox/please-check", "areas", "changes", "digests"):
            (r / d).mkdir(parents=True, exist_ok=True)

    def cleanup(self):
        self._tmp.cleanup()

    def path(self, rel):
        return self.root / rel

    def run(self, tool, *args, env=None, cwd=None):
        e = dict(os.environ)
        e["INTAKE_ROOT"] = str(self.root)
        e.update(env or {})
        return subprocess.run(["bash", "tools/" + tool] + [str(a) for a in args],
                              cwd=str(cwd or self.root), env=e, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8")

    def new_matter(self, area, subject, topic, sub_area=None, opened="2026-10-12", **extra):
        args = ["--area", area, "--subject", subject, "--topic", topic, "--opened", opened]
        if sub_area:
            args += ["--sub-area", sub_area]
        for k, v in extra.items():
            args += ["--" + k.replace("_", "-"), v]
        res = self.run("new-matter", *args)
        if res.returncode != 0:
            raise AssertionError("new-matter failed: %s %s" % (res.stdout, res.stderr))
        ref, folder = res.stdout.strip().split("\t")
        return ref, self.root / folder

    def add_roster(self, matter, line, confirmed=False):
        name = "roster.confirmed.md" if confirmed else "roster.md"
        common.append_line(common.mpath(matter, name), line)

    def add_document_row(self, matter, name, message_id, sha="0" * 64, folder="correspondence"):
        common.append_line(common.mpath(matter, "documents.md"), common.join_pipe(
            [name, folder, "received", "someone@example.com", "2026-10-12 09:12", "", message_id, sha,
             "pending", "", ""]))

    def set_status(self, matter, status):
        common.update_frontmatter_file(common.mpath(matter, "matter.md"), {"status": status}, history=False)

    def journal_lines(self):
        p = self.root / "JOURNAL.md"
        if not p.exists():
            return []
        return [l for l in common.read_text(p).split("\n") if l.strip() and not l.startswith("#")]


class WorkspaceTest(unittest.TestCase):
    prefix = ""

    def setUp(self):
        self.ws = Workspace(prefix=self.prefix)
        self.addCleanup(self.ws.cleanup)


class NewMatterTest(WorkspaceTest):

    def test_creates_folders_files_and_fills_placeholders(self):
        res = self.ws.run("new-matter", "--area", "commercial", "--sub-area", "customers",
                          "--subject", "acme-automotive", "--topic", "msa-liability-cap",
                          "--subject-name", "Acme Automotive GmbH", "--title", 'Acme MSA: "cap" for data breach',
                          "--opened", "2026-10-15", "--run", "2026-10-15_090000")
        self.assertEqual(res.returncode, 0, res.stderr)
        ref, folder = res.stdout.strip().split("\t")
        self.assertEqual(ref, "2026-0001")
        self.assertEqual(folder, "areas/commercial/customers/acme-automotive/"
                                 "2026-0001_acme-automotive_msa-liability-cap")
        m = self.ws.path(folder)
        for d in common.MATTER_DIRS:
            self.assertTrue((m / "agent" / d).is_dir(), d)
        self.assertTrue((m / "human").is_dir())
        for f in common.MATTER_FILES:
            text = common.mpath(m, f).read_text(encoding="utf-8")
            self.assertNotIn("{{", text, f)
        meta, body = common.read_frontmatter_file(m / "agent" / "matter.md")
        self.assertEqual(meta["reference"], "2026-0001")
        self.assertEqual(meta["area"], "commercial")
        self.assertEqual(meta["sub_area"], "customers")
        self.assertEqual(meta["subject"], "acme-automotive")
        self.assertEqual(meta["title"], 'Acme MSA: "cap" for data breach')
        self.assertEqual(meta["opened"], "2026-10-15")
        self.assertEqual(meta["status"], "open")
        self.assertEqual(meta["follows"], "")
        self.assertEqual(body.split("\n")[0], common.FENCE)
        self.assertIn("# Brief 2026-0001: Acme MSA", (m / "agent" / "brief.md").read_text(encoding="utf-8"))
        smeta, sbody = common.read_frontmatter_file(m.parent / "subject.md")
        self.assertEqual(smeta["name"], "Acme Automotive GmbH")
        self.assertEqual(smeta["subject"], "acme-automotive")
        self.assertEqual(smeta["created"], "2026-10-15")
        self.assertEqual(sbody.split("\n")[0], common.FENCE)
        log = common.read_pipe_records(m / "agent" / "log.md", common.LOG_COLUMNS)
        self.assertEqual([(r["event"], r["run"]) for r in log], [("opened matter", "2026-10-15_090000")])
        journal = self.ws.path("JOURNAL.md").read_text(encoding="utf-8").split("\n")
        self.assertEqual(journal[0], "# time | run | action | item | destination | reason | confidence")
        rec = common.split_pipe(journal[1])
        self.assertEqual(rec[1:5], ["2026-10-15_090000", "new-matter", "2026-0001", folder])
        self.assertEqual(rec[5], "new subject")

    def test_no_trailing_spaces_and_empty_sub_area(self):
        ref, m = self.ws.new_matter("corporate", "signing-authority", "poa-germany")
        text = (m / "agent" / "matter.md").read_text(encoding="utf-8")
        self.assertIn("\nsub_area:\n", text)
        self.assertFalse(any(line != line.rstrip() for line in text.split("\n")))
        self.assertEqual(m.relative_to(self.ws.root).as_posix(),
                         "areas/corporate/signing-authority/2026-0001_signing-authority_poa-germany")

    def test_subject_md_written_only_for_a_new_subject(self):
        ref1, m1 = self.ws.new_matter("commercial", "acme-automotive", "nda", sub_area="customers")
        subject_md = m1.parent / "subject.md"
        subject_md.write_text(subject_md.read_text(encoding="utf-8") + "\nedited by the reader\n", encoding="utf-8")
        ref2, m2 = self.ws.new_matter("commercial", "acme-automotive", "msa", sub_area="customers",
                                      follows=ref1)
        self.assertIn("edited by the reader", subject_md.read_text(encoding="utf-8"))
        self.assertEqual(common.read_frontmatter_file(m2 / "agent" / "matter.md")[0]["follows"], ref1)
        reasons = [common.split_pipe(l)[5] for l in self.ws.journal_lines()]
        self.assertEqual(reasons, ["new subject", "existing subject; follows 2026-0001"])

    def test_references_within_a_year(self):
        refs = [self.ws.new_matter("corporate", "topic-%d" % i, "x", opened="2026-03-0%d" % (i + 1))[0]
                for i in range(3)]
        self.assertEqual(refs, ["2026-0001", "2026-0002", "2026-0003"])
        res = self.ws.run("new-matter", "--next-ref", "--year", "2026")
        self.assertEqual(res.stdout.strip(), "2026-0004")

    def test_reference_counter_includes_index_csv(self):
        common.write_csv(self.ws.path("INDEX.csv"), common.INDEX_COLUMNS,
                         [{"reference": "2026-0041", "kind": "matter"}, {"reference": "NOISE-0003"}])
        ref, m = self.ws.new_matter("corporate", "signing-authority", "poa")
        self.assertEqual(ref, "2026-0042")

    def test_reference_across_a_year_change(self):
        a, _ = self.ws.new_matter("corporate", "year-end", "board-minutes", opened="2026-12-31")
        b, _ = self.ws.new_matter("corporate", "new-year", "board-minutes", opened="2027-01-02")
        c, _ = self.ws.new_matter("corporate", "late-2026", "filing", opened="2026-12-30")
        self.assertEqual((a, b, c), ("2026-0001", "2027-0001", "2026-0002"))
        self.assertEqual(self.ws.run("new-matter", "--next-ref", "--year", "2027").stdout.strip(), "2027-0002")

    def test_folder_name_capped_at_70_by_shortening_the_topic(self):
        ref, m = self.ws.new_matter("commercial", "rio-bombas-distribuicao",
                                    "exclusive-distribution-agreement-for-brazil-and-latin-america")
        self.assertLessEqual(len(m.name), 70)
        self.assertTrue(m.name.startswith("2026-0001_rio-bombas-distribuicao_exclusive-distribution"))
        self.assertFalse(m.name.endswith("-"))
        topic = m.name.split("_", 2)[2]
        self.assertTrue("exclusive-distribution-agreement-for-brazil-and-latin-america".startswith(topic))
        rest = "exclusive-distribution-agreement-for-brazil-and-latin-america"[len(topic):]
        self.assertTrue(rest == "" or rest.startswith("-"), "cut inside a word: %s" % topic)

    def test_area_with_sub_areas_allowed_without_one(self):
        ref, m = self.ws.new_matter("commercial", "rio-bombas", "distribution-brazil")
        self.assertEqual(m.relative_to(self.ws.root).as_posix(),
                         "areas/commercial/rio-bombas/2026-0001_rio-bombas_distribution-brazil")
        self.assertEqual(common.read_frontmatter_file(m / "agent" / "matter.md")[0]["sub_area"], "")

    def test_sub_area_not_declared_exits_2(self):
        res = self.ws.run("new-matter", "--area", "commercial", "--sub-area", "distributors",
                          "--subject", "rio-bombas", "--topic", "distribution")
        self.assertEqual(res.returncode, 2)
        self.assertEqual(res.stderr.strip(),
                         "sub-area 'distributors' is not declared for commercial. File under "
                         "areas/commercial/<subject>/ and propose the sub-area in the digest.")
        self.assertFalse(self.ws.path("areas/commercial").exists())
        res = self.ws.run("new-matter", "--area", "corporate", "--sub-area", "x", "--subject", "s", "--topic", "t")
        self.assertEqual(res.returncode, 2)
        self.assertIn("sub-area 'x' is not declared for corporate", res.stderr)

    def test_unknown_area_exits_2_in_plain_english(self):
        res = self.ws.run("new-matter", "--area", "legal-ops", "--subject", "x", "--topic", "y")
        self.assertEqual(res.returncode, 2)
        self.assertIn("area 'legal-ops' is not in house/areas.md", res.stderr)
        self.assertIn("general", res.stderr)

    def test_general_is_always_allowed(self):
        ref, m = self.ws.new_matter("general", "unfiled", "invoice-dispute")
        self.assertEqual(m.relative_to(self.ws.root).as_posix(),
                         "areas/general/unfiled/2026-0001_unfiled_invoice-dispute")

    def test_bad_slugs_and_values_exit_2(self):
        for args in (["--subject", "Acme Automotive", "--topic", "nda"],
                     ["--subject", "acme", "--topic", "NDA review"],
                     ["--subject", "acme", "--topic", "nda", "--opened", "15/10/2026"],
                     ["--subject", "acme", "--topic", "nda", "--follows", "42"]):
            res = self.ws.run("new-matter", "--area", "corporate", *args)
            self.assertEqual(res.returncode, 2, args)
        self.assertFalse(self.ws.path("areas/corporate").exists())

    def test_long_title_is_shortened(self):
        ref, m = self.ws.new_matter("corporate", "board", "minutes", title="word " * 30)
        self.assertLessEqual(len(common.read_frontmatter_file(m / "agent" / "matter.md")[0]["title"]), 80)

    def test_usage_error_exits_2(self):
        self.assertEqual(self.ws.run("new-matter").returncode, 2)
        self.assertEqual(self.ws.run("new-matter", "--area", "corporate").returncode, 2)
        self.assertEqual(self.ws.run("new-matter", "--bogus").returncode, 2)
        help_text = self.ws.run("new-matter", "--help")
        self.assertEqual(help_text.returncode, 0)
        self.assertIn("Usage: bash tools/new-matter", help_text.stdout)


class NewMatterPrefixTest(WorkspaceTest):
    prefix = "LM-"

    def test_reference_with_prefix(self):
        ref, m = self.ws.new_matter("corporate", "signing-authority", "poa")
        self.assertEqual(ref, "LM-2026-0001")
        self.assertTrue(m.name.startswith("LM-2026-0001_signing-authority_poa"))
        self.assertEqual(self.ws.run("new-matter", "--next-ref", "--year", "2026").stdout.strip(),
                         "LM-2026-0002")
        self.assertTrue(re.match(r"^LM-2026-0001$", common.read_frontmatter_file(m / "agent" / "matter.md")[0]["reference"]))


if __name__ == "__main__":
    unittest.main()
