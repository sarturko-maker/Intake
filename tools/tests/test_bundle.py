"""Tests for tools/work-bundle (spec D14)."""

import os
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsfixture import Workspace, common, make_bin  # noqa: E402

EMAIL = "2026-10-15_0847_in_jschmidt_acme-master-supply-agreement.eml"
TOP_LEVEL = ["brief.md", "corrections.md", "correspondence", "documents", "facts-live.md", "human", "intake.md",
             "matter.md", "notes.md", "roster.confirmed.md", "roster.md", "skill.md", "subject.md"]
FACTS = [
    "F0001 | 2026-10-15 | party | valid_from= | source=correspondence/%s | supersedes= | Customer is Acme Automotive GmbH" % EMAIL,
    "F0002 | 2026-10-15 | term | valid_from=2026-10-15 | source=documents/received/Acme_MSA_v1.docx cl.12 | supersedes= | General cap 200% of annual fees",
    "F0003 | 2026-10-27 | term | valid_from=2026-10-27 | source=documents/received/Acme_MSA_v3.docx cl.12 | supersedes=F0002 | General cap 150% of annual fees",
]


class WorkBundleTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(skills=False)
        ws = self.ws
        self.m = ws.make_matter("2026-0002", "commercial", "acme-automotive", "msa-liability-cap",
                                sub_area="customers", title="Acme MSA: liability cap", controlling_skill="nda-review")
        self.mrel = ws.rel(self.m)
        with open(str(self.m / "agent" / "facts.md"), "a", encoding="utf-8") as fh:
            fh.write("".join(f + "\n" for f in FACTS))
        self.put("correspondence/" + EMAIL, b"From: j.schmidt@acme-automotive.de\n\nbody\n")
        self.put("documents/received/Acme_MSA_v1.docx", b"PK\x03\x04 received")
        self.put("documents/ours/Acme_MSA_v1_Kestrel_markup.docx", b"PK\x03\x04 ours")
        self.put("documents/reference/liability-caps.md", b"knowledge copy\n")
        self.put("drafts/reply.md", b"draft\n")
        self.put("history/matter.2026-10-15_090000.md", b"old page\n")
        self.put("correspondence/history/old.eml", b"never bundled\n")
        self.put("work-product/2026-10-23_harvey-memo_liability-cap_v1.md", b"memo\n")
        self.put("documents/received/.DS_Store", b"junk")
        ws.make_matter("2026-0006", "commercial", "acme-automotive", "security-questionnaire",
                       sub_area="customers", title="Acme questionnaire")
        ws.make_matter("2026-0007", "commercial", "halden-water", "nda", sub_area="customers", title="Halden NDA")
        ws.write("knowledge/positions/liability-caps.md", "# Liability caps\n")
        ws.write("skills/commercial/nda-review/SKILL.md", "---\nname: nda-review\n---\n# NDA review\n")
        ws.write("skills/operations/bundle/SKILL.md", "---\nname: bundle\n---\n# Bundle\n")
        ws.write("areas/commercial/intake.md", "---\nstatus: draft\n---\n# Commercial intake\n")
        ws.write("areas/commercial/playbook.md", "# Commercial playbook\n")

    def tearDown(self):
        self.ws.cleanup()

    def put(self, relp, data):
        if relp in ("corrections.md", "roster.confirmed.md"):
            relp = "human/" + relp
        elif relp.startswith("work-product/"):
            relp = "human/" + relp[len("work-product/"):]
        elif not relp.startswith(("human/", "agent/")):
            relp = "agent/" + relp
        p = self.m / relp
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def bundle(self, *args, env=None):
        return self.ws.run("work-bundle", *args, env=env)

    def files(self, b):
        return sorted(p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file())

    def bdir(self, name="bundle-2026-11-01"):
        return self.m / "agent" / name

    def test_pack_is_stable_and_replaced(self):
        import time
        r = self.bundle("2026-0002")
        self.assertEqual(r.returncode, 0, r.stderr)
        pack = self.m / "agent" / "2026-0002_harvey-pack"
        self.assertTrue((pack / "brief.md").is_file())
        self.assertTrue((pack / ".stamp").is_file())
        self.assertIn("Files: 14", r.stdout)
        # a file the lawyer saved inside the pack is moved out, never lost
        time.sleep(1.1)
        (pack / "my-memo.md").write_text("mine\n")
        r = self.bundle("2026-0002")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((pack / "my-memo.md").exists())
        self.assertTrue((self.m / "human" / "my-memo.md").is_file())
        self.assertIn("moved", r.stdout)
        self.assertEqual(len([p for p in (self.m / "agent").iterdir() if p.name.endswith("_harvey-pack")]), 1)

    def test_all_refreshes_only_changed_open_matters(self):
        import time
        r = self.bundle("--all")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("3 refreshed, 0 unchanged", r.stdout)
        r = self.bundle("--all")
        self.assertIn("0 refreshed, 3 unchanged", r.stdout)
        time.sleep(1.1)
        self.put("notes.md", b"- 2026-11-02: call with sales\n")
        r = self.bundle("--all")
        self.assertIn("1 refreshed, 2 unchanged", r.stdout)
        self.assertTrue((self.m / "agent" / "2026-0002_harvey-pack" / "notes.md").read_text().startswith("- 2026-11-02"))
        r = self.bundle("--all", "--force")
        self.assertIn("3 refreshed, 0 unchanged", r.stdout)

    def test_read_only_received_files_still_bundle_and_rebuild(self):
        doc = self.m / "agent" / "documents" / "received" / "Acme_MSA_v1.docx"
        os.chmod(str(doc), 0o444)                     # as place-email and matter-sync leave them
        for _ in range(2):
            r = self.bundle("2026-0002")
            self.assertEqual(r.returncode, 0, r.stderr)
        copy = self.m / "agent" / "2026-0002_harvey-pack" / "documents" / "received" / "Acme_MSA_v1.docx"
        self.assertTrue(os.stat(str(copy)).st_mode & 0o200, "the copy in the pack is writable")
        self.assertFalse(os.stat(str(doc)).st_mode & 0o222, "the received file stays read-only")

    def test_all_skips_closed_matters(self):
        mf = self.m / "agent" / "matter.md"
        mf.write_text(mf.read_text().replace("status: open", "status: closed"))
        r = self.bundle("--all")
        self.assertIn("2 refreshed", r.stdout)
        self.assertFalse((self.m / "agent" / "2026-0002_harvey-pack").exists())

    def test_contains_exactly_the_section_12_list(self):
        r = self.bundle("2026-0002", "--date", "2026-11-01")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        b = self.bdir()
        self.assertEqual(sorted(os.listdir(str(b))), TOP_LEVEL)
        self.assertEqual(sorted(os.listdir(str(b / "documents"))), ["ours", "received"])
        self.assertEqual(self.files(b), sorted([
            "brief.md", "corrections.md", "correspondence/" + EMAIL, "documents/ours/Acme_MSA_v1_Kestrel_markup.docx",
            "documents/received/Acme_MSA_v1.docx", "facts-live.md", "human/2026-10-23_harvey-memo_liability-cap_v1.md", "intake.md", "matter.md",
            "notes.md", "roster.confirmed.md", "roster.md", "skill.md", "subject.md"]))
        self.assertEqual((b / "matter.md").read_bytes(), (self.m / "agent" / "matter.md").read_bytes())
        self.assertEqual((b / "subject.md").read_bytes(), (self.m.parent / "subject.md").read_bytes())
        self.assertEqual((b / "skill.md").read_bytes(),
                         (self.ws.root / "skills/commercial/nda-review/SKILL.md").read_bytes())
        self.assertEqual((b / "intake.md").read_bytes(), (self.ws.root / "areas/commercial/intake.md").read_bytes())
        self.assertEqual((b / "documents/received/Acme_MSA_v1.docx").read_bytes(), b"PK\x03\x04 received")

    def test_never_history_other_subjects_or_knowledge(self):
        self.bundle("2026-0002", "--date", "2026-11-01")
        listing = "\n".join(self.files(self.bdir()))
        for word in ("history", "drafts", "reference", "questionnaire", "halden", "knowledge",
                     "liability-caps", "playbook", ".DS_Store"):
            self.assertNotIn(word, listing)

    def test_facts_live_view(self):
        self.bundle("2026-0002", "--date", "2026-11-01")
        lines = (self.bdir() / "facts-live.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], common.FENCE)
        records = [x for x in lines if common.is_record_line(x)]
        self.assertEqual(records, [FACTS[0], FACTS[2]])

    def test_facts_live_view_without_python_uses_awk(self):
        if os.name == "nt":
            self.skipTest("symlinked PATH folder")
        nopy = make_bin(self.ws.tmp / "nopy-bin", hide=("python*", "py", "pydoc*"))
        env = self.ws.env(PATH=str(nopy))
        r = self.bundle("2026-0002", "--date", "2026-11-01", env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (self.bdir() / "facts-live.md").read_text(encoding="utf-8")
        self.assertIn("awk (Python not available)", text)
        self.assertEqual([x for x in text.splitlines() if common.is_record_line(x)], [FACTS[0], FACTS[2]])

    def test_prints_path_count_and_upload_notes(self):
        r = self.bundle(self.mrel, "--date", "2026-11-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Bundle written: %s/agent/bundle-2026-11-01" % self.mrel, r.stdout)
        self.assertIn("Files: 14", r.stdout)
        self.assertIn("Harvey; Legora or another tool works the same way", r.stdout)
        self.assertIn("at most 50 files per upload, 500 MB per file", r.stdout)
        self.assertIn("Paste brief.md as the task.", r.stdout)
        self.assertIn("Put the deliverables into %s/human/" % self.mrel, r.stdout)
        self.assertNotIn("warning:", r.stdout)

    def test_second_bundle_on_the_same_date_gets_a_suffix(self):
        self.bundle("2026-0002", "--date", "2026-11-01")
        r = self.bundle("2026-0002", "--date", "2026-11-01")
        self.assertIn("bundle-2026-11-01-2", r.stdout)
        r = self.bundle("2026-0002", "--date", "2026-11-01")
        self.assertIn("bundle-2026-11-01-3", r.stdout)
        self.assertEqual(self.files(self.bdir()), self.files(self.bdir("bundle-2026-11-01-2")))

    def test_skill_flag_and_missing_skill(self):
        r = self.bundle("2026-0002", "--date", "2026-11-01", "--skill", "bundle")
        self.assertEqual(r.returncode, 0)
        self.assertIn("# Bundle", (self.bdir() / "skill.md").read_text())
        r = self.bundle("2026-0002", "--date", "2026-11-02", "--skill", "no-such-skill")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.bdir("bundle-2026-11-02").exists(), "nothing written on a usage error")
        common.update_frontmatter_file(self.m / "agent" / "matter.md", {"controlling_skill": ""}, history=False)
        r = self.bundle("2026-0002", "--date", "2026-11-03")
        self.assertEqual(r.returncode, 0)
        self.assertIn("warning: no controlling skill", r.stdout)
        self.assertNotIn("skill.md", os.listdir(str(self.bdir("bundle-2026-11-03"))))
        common.update_frontmatter_file(self.m / "agent" / "matter.md", {"controlling_skill": "retired-skill"}, history=False)
        r = self.bundle("2026-0002", "--date", "2026-11-04")
        self.assertIn("warning: controlling skill 'retired-skill' not found under skills/", r.stdout)

    def test_missing_pieces_are_left_out_with_a_warning(self):
        (self.ws.root / "areas/commercial/intake.md").unlink()
        shutil.rmtree(str(self.m / "agent" / "documents" / "ours"))
        r = self.bundle("2026-0002", "--date", "2026-11-01")
        self.assertEqual(r.returncode, 0)
        self.assertIn("warning: no intake.md for area 'commercial'", r.stdout)
        self.assertTrue((self.bdir() / "documents" / "ours").is_dir(), "the folder is there, empty")

    def test_more_than_50_files_warns(self):
        for i in range(45):
            self.put("documents/received/annex-%02d.pdf" % i, b"%PDF")
        r = self.bundle("2026-0002", "--date", "2026-11-01")
        self.assertIn("Files: 59", r.stdout)
        self.assertIn("warning: 59 files: more than 50, so upload in 2 batches of at most 50", r.stdout)

    @unittest.skipUnless(sys.platform.startswith("linux"), "sparse files keep the test small on Linux")
    def test_file_over_500_mb_warns(self):
        big = self.m / "agent" / "documents" / "received" / "scan.pdf"
        with open(str(big), "wb") as fh:
            fh.truncate(500000001)
        if os.stat(str(big)).st_blocks > 64:
            self.skipTest("no sparse files here")
        r = self.bundle("2026-0002", "--date", "2026-11-01")
        self.assertIn("warning: over 500 MB, the work tool will not take: documents/received/scan.pdf", r.stdout)

    def test_usage_errors(self):
        self.assertEqual(self.bundle().returncode, 2)
        self.assertEqual(self.bundle("2026-0999").returncode, 2)
        self.assertEqual(self.bundle("areas/commercial").returncode, 2)
        self.assertEqual(self.bundle("2026-0002", "--date", "1 Nov").returncode, 2)
        self.assertEqual(self.bundle("2026-0002", "2026-0006").returncode, 2)
        self.assertEqual(self.bundle("2026-0002", "--bogus").returncode, 2)
        self.assertEqual(self.bundle("2026-0002", "--skill", "../../etc").returncode, 2)
        self.assertFalse((self.m / "work-product").exists() and any(
            p.name.startswith("bundle-") for p in (self.m / "work-product").iterdir()))


if __name__ == "__main__":
    unittest.main()
