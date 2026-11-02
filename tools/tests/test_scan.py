"""Tests for tools/scan-changes, including the plan's slice 1 check (a second scan after changing
one file reports exactly that file).

Run: python3 -m unittest discover -s tools/tests -p 'test_*.py'
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_new_matter import WorkspaceTest  # noqa: E402

import common  # noqa: E402

MANIFEST_HEADER = "path,size,mtime,sha256,first_seen,last_seen,last_processed"


class ScanBase(WorkspaceTest):

    def scan(self, *args):
        res = self.ws.run("scan-changes", "--json", *args)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def write(self, rel, text):
        p = self.ws.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def bump_mtime(self, rel, seconds=10):
        p = self.ws.path(rel)
        st = p.stat()
        os.utime(str(p), (st.st_atime + seconds, st.st_mtime + seconds))

    def kinds(self, report):
        return sorted((c["kind"], c["path"]) + ((c["old_path"],) if "old_path" in c else ())
                      for c in report["changes"])

    def manifest(self):
        return {r["path"]: r for r in common.read_csv(self.ws.path("MANIFEST.csv"))}


class ScanTest(ScanBase):

    def test_first_scan_reports_everything_new(self):
        self.write("inbox/a.eml", "x")
        d = self.scan("--run", "S1")
        self.assertTrue(d["first_scan"])
        self.assertEqual(d["counts"]["new"], d["files"])
        self.assertEqual(set(c["kind"] for c in d["changes"]), {"new"})
        self.assertIn("inbox/a.eml", [c["path"] for c in d["changes"]])
        self.assertIn("house/brief.md", [c["path"] for c in d["changes"]])
        report = self.ws.path("changes/S1.md").read_text(encoding="utf-8")
        self.assertTrue(report.startswith("# Changes S1\n"))
        self.assertIn("First scan", report)
        self.assertIn("- new: inbox/a.eml (1)", report)

    def test_slice_1_second_scan_after_touching_one_file_reports_exactly_that_file(self):
        self.write("knowledge/policies/infosec.md", "policy")
        self.scan("--run", "S1", "--write-manifest")
        self.bump_mtime("knowledge/policies/infosec.md")
        d = self.scan("--run", "S2")
        self.assertEqual(self.kinds(d), [("touched", "knowledge/policies/infosec.md")])
        self.assertEqual(d["counts"], {"new": 0, "modified": 0, "touched": 1, "moved": 0, "deleted": 0})

    def test_slice_1_second_scan_after_changing_one_file_reports_exactly_that_file(self):
        self.write("knowledge/policies/infosec.md", "policy")
        self.scan("--run", "S1", "--write-manifest")
        self.write("house/areas.md", self.ws.path("house/areas.md").read_text(encoding="utf-8") + "\nedited\n")
        d = self.scan("--run", "S2")
        self.assertEqual(self.kinds(d), [("modified", "house/areas.md")])
        same_size = self.ws.path("knowledge/policies/infosec.md")
        self.scan("--run", "S3", "--write-manifest")
        same_size.write_text("POLICY", encoding="utf-8")   # same size, new content
        self.bump_mtime("knowledge/policies/infosec.md")
        self.assertEqual(self.kinds(self.scan("--run", "S4")), [("modified", "knowledge/policies/infosec.md")])

    def test_no_changes(self):
        self.scan("--run", "S1", "--write-manifest")
        d = self.scan("--run", "S2")
        self.assertEqual(d["changes"], [])
        self.assertIn("No changes since the last manifest.", self.ws.path("changes/S2.md").read_text(encoding="utf-8"))

    def test_new_modified_touched_deleted_and_moved(self):
        self.write("inbox/move-me.eml", "same bytes")
        self.write("seeds/old.md", "old seed")
        self.write("knowledge/a.md", "a")
        self.write("knowledge/b.md", "b")
        self.scan("--run", "S1", "--write-manifest")
        ref, m = self.ws.new_matter("corporate", "signing-authority", "poa")
        mrel = m.relative_to(self.ws.root).as_posix()
        os.replace(str(self.ws.path("inbox/move-me.eml")), str(m / "agent" / "correspondence" / "x.eml"))
        self.ws.path("seeds/old.md").unlink()
        self.write("knowledge/a.md", "a changed")
        self.bump_mtime("knowledge/b.md")
        d = self.scan("--run", "S2")
        got = self.kinds(d)
        self.assertIn(("moved", mrel + "/agent/correspondence/x.eml", "inbox/move-me.eml"), got)
        self.assertIn(("deleted", "seeds/old.md"), got)
        self.assertIn(("modified", "knowledge/a.md"), got)
        self.assertIn(("touched", "knowledge/b.md"), got)
        self.assertIn(("new", mrel + "/agent/matter.md"), got)
        self.assertNotIn(("new", mrel + "/agent/correspondence/x.eml"), got)
        report = self.ws.path("changes/S2.md").read_text(encoding="utf-8")
        self.assertIn("## " + mrel + "\n", report)
        self.assertIn("- moved: inbox/move-me.eml -> %s/agent/correspondence/x.eml" % mrel, report)
        self.assertIn("## knowledge\n", report)
        self.assertIn("- deleted: seeds/old.md (8)", report)
        self.assertLess(report.index("## " + mrel), report.index("## knowledge"))

    def test_exclusions(self):
        self.scan("--run", "S1", "--write-manifest")
        ref, m = self.ws.new_matter("corporate", "signing-authority", "poa")
        self.scan("--run", "S2", "--write-manifest")
        for rel in (".git/config", ".claude/settings.json", "demo/README.md", "phase-2/x.html",
                    ".github/copilot-instructions.md", "changes/other.md", "digests/LATEST.md",
                    "JOURNAL.md", "INDEX.md", "WORKFLOW-LOG.md", "TOOLING.md", "BUDGET.md", "HANDOFF.md",
                    "knowledge/INDEX.md", "inbox/.DS_Store", "inbox/Thumbs.db", "house/desktop.ini",
                    "inbox/~$draft.docx", "inbox/file.tmp", "inbox/.~lock.x.docx#"):
            self.write(rel, "excluded")
        mrel = m.relative_to(self.ws.root).as_posix()
        self.write(mrel + "/history/matter.2026-10-15_090000.md", "old")
        self.write(mrel + "/work-product/bundle-2026-10-23/brief.md", "copy")
        self.write(mrel + "/work-product/memo.md", "deliverable")
        self.write("INDEX.csv", "reference\n")
        d = self.scan("--run", "S3")
        self.assertEqual(self.kinds(d), [("new", "INDEX.csv"), ("new", mrel + "/work-product/memo.md")])
        report = self.ws.path("changes/S3.md").read_text(encoding="utf-8")
        self.assertIn("## root\n- new: INDEX.csv", report)

    def test_write_manifest_columns_and_bookkeeping(self):
        self.write("inbox/new.eml", "mail")
        self.write("inbox/noise/old.eml", "noise")
        self.scan("--run", "S1", "--write-manifest")
        text = self.ws.path("MANIFEST.csv").read_text(encoding="utf-8")
        self.assertEqual(text.splitlines()[0], MANIFEST_HEADER)
        rows = self.manifest()
        self.assertNotIn("MANIFEST.csv", rows)
        r = rows["inbox/new.eml"]
        self.assertEqual((r["size"], r["first_seen"], r["last_seen"], r["last_processed"]), ("4", "S1", "S1", ""))
        self.assertEqual(r["sha256"], common.sha256_file(self.ws.path("inbox/new.eml")))
        self.assertEqual(r["mtime"], str(int(self.ws.path("inbox/new.eml").stat().st_mtime)))
        self.assertEqual(rows["inbox/noise/old.eml"]["last_processed"], "S1")
        self.assertEqual(rows["house/brief.md"]["last_processed"], "S1")
        self.write("house/areas.md", "changed")
        os.replace(str(self.ws.path("inbox/new.eml")), str(self.ws.path("inbox/please-check/new.eml")))
        self.scan("--run", "S2", "--write-manifest")
        rows = self.manifest()
        self.assertEqual((rows["house/areas.md"]["first_seen"], rows["house/areas.md"]["last_seen"]), ("S1", "S2"))
        self.assertEqual(rows["inbox/please-check/new.eml"]["first_seen"], "S1")
        self.assertEqual(rows["inbox/please-check/new.eml"]["last_processed"], "S2")
        self.assertNotIn("inbox/new.eml", rows)

    def test_plain_and_quiet_output(self):
        res = self.ws.run("scan-changes", "--run", "S1")
        self.assertEqual(res.returncode, 0)
        self.assertTrue(res.stdout.startswith("scan: first scan, new "))
        self.assertIn("report: changes/S1.md", res.stdout)
        res = self.ws.run("scan-changes", "--run", "S2", "--quiet")
        self.assertEqual(res.stdout.strip(), "changes/S2.md")

    def test_default_run_id_and_usage_errors(self):
        d = self.scan()
        self.assertRegex(d["run"], r"^\d{4}-\d{2}-\d{2}_\d{6}$")
        self.assertTrue(self.ws.path(d["report"]).is_file())
        self.assertEqual(self.ws.run("scan-changes", "--bogus").returncode, 2)
        self.assertEqual(self.ws.run("scan-changes", "--run", "../x").returncode, 2)
        help_text = self.ws.run("scan-changes", "-h")
        self.assertEqual(help_text.returncode, 0)
        self.assertIn("Usage: bash tools/scan-changes", help_text.stdout)


if __name__ == "__main__":
    unittest.main()
