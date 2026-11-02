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
        self.assertTrue((self.m / "agent" / "notes.md").is_file())
        self.assertFalse((self.m / "human" / "notes.md").exists())
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
        notes = self.m / "agent" / "notes.md"
        notes.write_text(notes.read_text() + "\n- 2026-11-02: call with sales\n")
        r = self.sync()
        self.assertIn("edited by you: agent/brief.md, agent/notes.md", r.stdout)
        # at the end of a run (pages only) the agent's own writes are not reported as the lawyer's
        r = self.sync("--pages-only")
        self.assertNotIn("edited by you", r.stdout)

    def test_the_agents_own_writes_are_not_the_lawyers(self):
        """The after-write hook records what the agent wrote in changes/agent-writes.csv."""
        self.ws.run("scan-changes", "--run", "R0", "--write-manifest")
        notes = self.m / "agent" / "notes.md"
        notes.write_text(notes.read_text() + "- 2026-11-02: (you said) They accept the cap.\n")
        ledger = self.ws.root / "changes" / "agent-writes.csv"
        ledger.write_text('path,sha256\n"%s",%s\n' % (common.rel(notes, self.ws.root).upper(), common.sha256_file(notes)))
        r = self.sync()
        self.assertNotIn("edited by you", r.stdout)
        # the lawyer then types in the same file: that is reported
        notes.write_text(notes.read_text() + "- my own line\n")
        self.assertIn("edited by you: agent/notes.md", self.sync().stdout)
        # writing the manifest at the end of a run empties the record
        self.ws.run("scan-changes", "--run", "R2", "--write-manifest")
        self.assertFalse(ledger.exists())

    def test_received_files_are_made_read_only(self):
        f = self.m / "agent" / "documents" / "received" / "MSA.docx"
        f.write_bytes(b"PK received")
        os.chmod(str(f), 0o644)
        r = self.sync()
        self.assertIn("1 received files set to read-only", r.stdout)
        self.assertFalse(os.stat(str(f)).st_mode & 0o222)
        self.assertNotIn("read-only", self.sync().stdout)

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

    def make_pack(self, m, ref):
        """A Harvey pack as work-bundle leaves it: copies at the top, including matter.md, and a .stamp."""
        pack = m / "agent" / ("%s_harvey-pack" % ref)
        (pack / "correspondence").mkdir(parents=True)
        for name in ("matter.md", "brief.md", "notes.md", "corrections.md", "subject.md"):
            (pack / name).write_text("copy of %s\n" % name, encoding="utf-8")
        (pack / "correspondence" / "a.eml").write_bytes(b"From: x\n\nbody\n")
        (pack / ".stamp").write_text("")
        old = time.time() - 3600
        for f in pack.rglob("*"):
            os.utime(str(f), (old, old))
        os.utime(str(pack / ".stamp"), (old + 60, old + 60))
        return pack

    def test_a_harvey_pack_is_never_taken_for_an_old_matter(self):
        ref, m = self.ws.new_matter("commercial", "acme-automotive", "nda", sub_area="customers")
        pack = self.make_pack(m, ref)
        self.assertFalse(common.is_legacy_matter_dir(pack))
        self.assertFalse(common.is_matter_dir(pack))
        self.assertEqual(list(common.iter_legacy_matter_dirs(self.ws.root)), [])
        self.assertNotIn("old layout", self.ws.run("matter-sync", "--run", "R1").stdout)
        self.assertIn("nothing to do", self.ws.run("matter-migrate", "--run", "R1").stdout)
        self.assertTrue((pack / "matter.md").is_file())
        self.assertFalse((pack / "agent").exists())

    def test_a_split_pack_is_repaired(self):
        """What the earlier mistake left: the pack split into agent/ and human/, and work-bundle then moving
        the split's log.md into the matter's human/ folder, where matter-sync registered it."""
        ref, m = self.ws.new_matter("commercial", "acme-automotive", "nda", sub_area="customers")
        pack = self.make_pack(m, ref)
        (pack / "agent").mkdir()
        (pack / "matter.md").rename(pack / "agent" / "matter.md")
        (pack / "human").mkdir()
        (pack / "corrections.md").rename(pack / "human" / "corrections.md")
        (pack / "agent" / "log.md").write_text("2026-11-02 10:00 | moved to the agent/ and human/ layout | - | R0\n")
        (pack / "my-memo.md").write_text("saved in the pack by the lawyer\n")   # newer than the stamp
        (m / "human" / "log.md").write_text("2026-11-02 10:00 | moved to the agent/ and human/ layout | - | R0\n")
        (m / "human" / "call.md").write_text("the lawyer's own file\n")
        self.ws.run("matter-sync", "--run", "R0")
        names = [x["name"] for x in common.read_pipe_records(m / "agent" / "documents.md", common.DOCUMENTS_COLUMNS)]
        self.assertIn("log.md", names)
        self.assertIn("would have removed", self.ws.run("matter-migrate", "--dry-run").stdout)
        self.assertTrue(pack.exists())
        r = self.ws.run("matter-migrate", "--run", "R1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("repaired 1 matters", r.stdout)
        self.assertFalse(pack.exists())
        self.assertEqual((m / "human" / "my-memo.md").read_text(), "saved in the pack by the lawyer\n")
        self.assertFalse((m / "human" / "log.md").exists())
        self.assertTrue(list((m / "agent" / "history").glob("log.split-pack.R1.md")))
        self.assertTrue((m / "human" / "call.md").is_file())
        names = [x["name"] for x in common.read_pipe_records(m / "agent" / "documents.md", common.DOCUMENTS_COLUMNS)]
        self.assertNotIn("log.md", names)
        self.assertIn("call.md", names)
        self.assertIn("repaired: removed the split Harvey pack", (m / "agent" / "log.md").read_text())
        self.assertIn("nothing to do", self.ws.run("matter-migrate", "--run", "R2").stdout)
        # the next work-bundle run rebuilds the pack, whole
        r = self.ws.run("work-bundle", "--all")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((pack / "matter.md").is_file())
        self.assertFalse((pack / "agent").exists())

    def test_notes_move_to_agent_and_missing_files_are_added(self):
        ref, m = self.ws.new_matter("commercial", "acme-automotive", "nda", sub_area="customers")
        # the layout before notes moved: notes.md in human/, with the lawyer's lines
        (m / "agent" / "notes.md").rename(m / "human" / "notes.md")
        with open(str(m / "human" / "notes.md"), "a", encoding="utf-8") as fh:
            fh.write("- 2026-11-01: call with sales\n")
        (m / "agent" / "roster.md").unlink()
        r = self.ws.run("matter-migrate", "--run", "R1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("tidied 1 matters", r.stdout)
        self.assertIn("call with sales", (m / "agent" / "notes.md").read_text(encoding="utf-8"))
        self.assertFalse((m / "human" / "notes.md").exists())
        self.assertTrue((m / "agent" / "roster.md").is_file())
        self.assertIn("moved human/notes.md to agent/notes.md", (m / "agent" / "log.md").read_text())
        self.assertIn("nothing to do", self.ws.run("matter-migrate").stdout)

    def test_a_matter_without_notes_gets_the_blank_file(self):
        ref, m = self.ws.new_matter("commercial", "acme-automotive", "nda", sub_area="customers")
        (m / "agent" / "notes.md").unlink()
        self.ws.run("matter-migrate", "--run", "R1")
        self.assertTrue((m / "agent" / "notes.md").is_file())

    def test_blank_agent_notes_give_way_to_the_lawyers_notes(self):
        ref, m = self.ws.new_matter("commercial", "acme-automotive", "nda", sub_area="customers")
        (m / "human" / "notes.md").write_text("# Notes\n\n- 2026-11-01: mine\n", encoding="utf-8")
        r = self.ws.run("matter-migrate", "--run", "R1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("mine", (m / "agent" / "notes.md").read_text(encoding="utf-8"))
        self.assertTrue(list((m / "agent" / "history").glob("notes.*.md")))
        # both with notes: nothing moves, a warning says what to do
        (m / "human" / "notes.md").write_text("- 2026-11-03: other\n", encoding="utf-8")
        r = self.ws.run("matter-migrate", "--run", "R2")
        self.assertIn("both hold notes", r.stdout)
        self.assertTrue((m / "human" / "notes.md").is_file())


if __name__ == "__main__":
    unittest.main()
