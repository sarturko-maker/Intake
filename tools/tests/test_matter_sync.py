"""Tests for tools/matter-sync and tools/matter-migrate (agent/ and human/ layout)."""

import os
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lib"))
from test_new_matter import WorkspaceTest  # noqa: E402
import common  # noqa: E402


class MatterSyncTest(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.ref, self.m = self.ws.new_matter("commercial", "acme-automotive", "nda", sub_area="customers",
                                              opened="2026-10-12")

    def sync(self, *args):
        return self.ws.run("matter-sync", "--run", "R1", *args)

    def docs(self):
        return common.read_pipe_records(self.m / "agent" / "documents.md", common.DOCUMENTS_COLUMNS)

    def test_layout_from_new_matter(self):
        self.assertTrue((self.m / "agent" / "matter.md").is_file())
        self.assertTrue((self.m / "human" / "notes.md").is_file())
        self.assertTrue((self.m / "human" / "corrections.md").is_file())
        self.assertFalse((self.m / "matter.md").exists())

    def test_registers_human_files_and_writes_start_here(self):
        (self.m / "human" / "call note 2 Nov.docx").write_bytes(b"PK call")
        r = self.sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = self.docs()
        self.assertEqual([(x["name"], x["folder"], x["origin"], x["read"]) for x in rows],
                         [("call note 2 Nov.docx", "human", "human", "pending")])
        page = (self.m / "START-HERE.md").read_text(encoding="utf-8")
        self.assertIn("# %s" % self.ref, page)
        self.assertIn("[Brief](agent/brief.md)", page)
        self.assertIn("(human/call%20note%202%20Nov.docx)", page)
        self.assertIn("New or changed since the last run", page)
        self.assertIn("to read: human/call note 2 Nov.docx", r.stdout)
        self.assertTrue(list((self.ws.root / "changes").glob("R1-matters.md")))
        # notes.md is read directly, never registered as a document
        self.assertNotIn("notes.md", [x["name"] for x in rows])

    def test_changed_human_file_goes_back_to_pending(self):
        f = self.m / "human" / "memo.md"
        f.write_text("v1\n")
        self.sync()
        docs = self.m / "agent" / "documents.md"
        docs.write_text(docs.read_text().replace("| pending |", "| yes |"))
        self.assertNotIn("to read", self.sync().stdout)
        f.write_text("v2, changed by the lawyer\n")
        r = self.sync()
        self.assertIn("changed by you: human/memo.md", r.stdout)
        self.assertEqual(self.docs()[0]["read"], "pending")
        self.assertIn("lawyer changed human/memo.md", (self.m / "agent" / "log.md").read_text())

    def test_hand_placed_document_in_agent_folder_is_registered(self):
        (self.m / "agent" / "documents" / "received" / "signed.pdf").write_bytes(b"%PDF signed")
        r = self.sync()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([(x["name"], x["folder"]) for x in self.docs()], [("signed.pdf", "documents/received")])

    def test_lawyer_edits_found_against_the_manifest(self):
        self.ws.run("scan-changes", "--run", "R0", "--write-manifest")
        brief = self.m / "agent" / "brief.md"
        brief.write_text(brief.read_text() + "\nThe lawyer added this.\n")
        notes = self.m / "human" / "notes.md"
        notes.write_text(notes.read_text() + "\n- 2026-11-02: call with sales\n")
        r = self.sync()
        self.assertIn("edited by you: human/notes.md, agent/brief.md", r.stdout)
        # at the end of a run (pages only) the agent's own writes are not reported as the lawyer's
        r = self.sync("--pages-only")
        self.assertNotIn("edited by you", r.stdout)

    def test_pages_only_writes_nothing_else(self):
        (self.m / "human" / "x.txt").write_text("x")
        self.sync("--pages-only")
        self.assertEqual(self.docs(), [])
        self.assertTrue((self.m / "START-HERE.md").is_file())


class MatterMigrateTest(WorkspaceTest):
    def test_old_layout_is_moved(self):
        ref, m = self.ws.new_matter("commercial", "acme-automotive", "nda", sub_area="customers")
        # rebuild the old one-folder layout from the new one
        import shutil
        for p in list((m / "agent").iterdir()):
            shutil.move(str(p), str(m / p.name))
        for p in list((m / "human").iterdir()):
            shutil.move(str(p), str(m / p.name))
        (m / "agent").rmdir()
        (m / "human").rmdir()
        (m / "work-product").mkdir()
        (m / "work-product" / "2026-10-23_harvey-memo.md").write_text("memo\n")
        (m / "work-product" / "bundle-2026-10-20").mkdir()
        (m / "correspondence" / "a.eml").write_bytes(b"From: x\n\nbody\n")
        common.append_line(m / "documents.md", common.join_pipe(
            ["2026-10-23_harvey-memo.md", "work-product", "work-product", "", "2026-10-23 10:00", "", "", "0" * 64,
             "yes", "", ""]))
        self.assertTrue(common.is_legacy_matter_dir(m))
        r = self.ws.run("matter-migrate", "--dry-run")
        self.assertIn("would migrate", r.stdout)
        self.assertTrue((m / "matter.md").is_file())
        r = self.ws.run("matter-migrate", "--run", "R1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(common.is_matter_dir(m))
        self.assertTrue((m / "agent" / "correspondence" / "a.eml").is_file())
        self.assertTrue((m / "human" / "corrections.md").is_file())
        self.assertTrue((m / "human" / "2026-10-23_harvey-memo.md").is_file())
        self.assertFalse((m / "work-product").exists())
        rows = common.read_pipe_records(m / "agent" / "documents.md", common.DOCUMENTS_COLUMNS)
        self.assertEqual((rows[0]["folder"], rows[0]["origin"]), ("human", "human"))
        self.assertIn("nothing to do", self.ws.run("matter-migrate").stdout)


if __name__ == "__main__":
    unittest.main()
