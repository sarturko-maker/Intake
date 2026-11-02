"""Tests for tools/hash-files and tools/history-copy (pure bash).

Run: python3 -m unittest discover -s tools/tests -p 'test_*.py'
"""

import datetime as dt
import hashlib
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

import common  # noqa: E402

FIXED_STAMP = "2026-10-31_120000"


def run(tool, *args, env=None, cwd=None):
    e = dict(os.environ)
    e.pop("HASH_FILES_METHOD", None)
    e.update(env or {})
    return subprocess.run(["bash", str(TOOLS / tool)] + [str(a) for a in args], cwd=str(cwd or ROOT), env=e,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8")


class TempDirTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="hash-history-test-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def fake_date_env(self):
        """PATH with a 'date' that always prints FIXED_STAMP, so names are predictable."""
        fakebin = self.tmp / "fakebin"
        fakebin.mkdir(exist_ok=True)
        script = fakebin / "date"
        script.write_text("#!/bin/sh\necho %s\n" % FIXED_STAMP)
        script.chmod(0o755)
        return {"PATH": str(fakebin) + os.pathsep + os.environ.get("PATH", "")}


class HashFilesTest(TempDirTest):

    def setUp(self):
        super().setUp()
        self.files = []
        for name, data in (("plain.txt", b"hello"), ("it's got spaces.docx", b"PK\x03\x04" + b"\x00" * 5000),
                           ("empty.bin", b"")):
            p = self.tmp / name
            p.write_bytes(data)
            self.files.append(p)

    def expected(self):
        return "".join("%s  %s\n" % (hashlib.sha256(p.read_bytes()).hexdigest(), p) for p in self.files)

    def test_default_method(self):
        res = run("hash-files", *self.files)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout, self.expected())

    def test_each_available_method_agrees_with_hashlib(self):
        tried = 0
        for method, exe in (("sha256sum", "sha256sum"), ("shasum", "shasum"), ("openssl", "openssl"),
                            ("python", "python3"), ("powershell", "pwsh")):
            if shutil.which(exe) is None:
                continue
            tried += 1
            res = run("hash-files", *self.files, env={"HASH_FILES_METHOD": method})
            self.assertEqual(res.returncode, 0, "%s: %s" % (method, res.stderr))
            self.assertEqual(res.stdout, self.expected(), method)
        self.assertGreater(tried, 0)

    def test_missing_file_exit_1_others_still_hashed(self):
        res = run("hash-files", self.files[0], self.tmp / "missing.pdf", self.files[1])
        self.assertEqual(res.returncode, 1)
        self.assertIn("no file: %s" % (self.tmp / "missing.pdf"), res.stderr)
        self.assertEqual(len(res.stdout.splitlines()), 2)

    def test_usage_and_method_errors(self):
        self.assertEqual(run("hash-files").returncode, 2)
        self.assertEqual(run("hash-files", self.files[0], env={"HASH_FILES_METHOD": "md5"}).returncode, 2)
        if shutil.which("pwsh") is None and shutil.which("powershell") is None:
            res = run("hash-files", self.files[0], env={"HASH_FILES_METHOD": "powershell"})
            self.assertEqual(res.returncode, 3)
            self.assertIn("Fallback:", res.stderr)
        help_text = run("hash-files", "--help")
        self.assertEqual(help_text.returncode, 0)
        self.assertIn("Usage: bash tools/hash-files FILE...", help_text.stdout)


class HistoryCopyTest(TempDirTest):

    NAMES = ("matter.md", "facts.md", "noext", ".hidden", "a.b.", "x.tar.gz")

    def make(self, folder, name, text="content"):
        folder.mkdir(parents=True, exist_ok=True)
        p = folder / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_naming_matches_common_history_copy(self):
        env = self.fake_date_env()
        bash_dir, py_dir = self.tmp / "bash", self.tmp / "py"
        when = dt.datetime.strptime(FIXED_STAMP, "%Y-%m-%d_%H%M%S")
        for name in self.NAMES:
            b = self.make(bash_dir, name)
            p = self.make(py_dir, name)
            for _ in range(3):
                res = run("history-copy", b, env=env)
                self.assertEqual(res.returncode, 0, res.stderr)
                common.history_copy(p, when=when)
        got = sorted(x.name for x in (bash_dir / "history").iterdir())
        want = sorted(x.name for x in (py_dir / "history").iterdir())
        self.assertEqual(got, want)
        self.assertIn("matter.%s.md" % FIXED_STAMP, got)
        self.assertIn("matter.%s-2.md" % FIXED_STAMP, got)
        self.assertIn("matter.%s-3.md" % FIXED_STAMP, got)
        self.assertIn("noext.%s.md" % FIXED_STAMP, got)
        self.assertIn("x.tar.%s.gz" % FIXED_STAMP, got)

    def test_prints_the_path_keeps_content_and_mtime(self):
        f = self.make(self.tmp / "m", "matter.md", "page text")
        old = 1790000000
        os.utime(str(f), (old, old))
        res = run("history-copy", f, env=self.fake_date_env())
        dest = self.tmp / "m" / "history" / ("matter.%s.md" % FIXED_STAMP)
        self.assertEqual(res.stdout, "%s\n" % dest)
        self.assertEqual(dest.read_text(encoding="utf-8"), "page text")
        self.assertEqual(int(dest.stat().st_mtime), old)

    def test_relative_path_and_real_clock(self):
        self.make(self.tmp / "m", "subject.md")
        res = run("history-copy", "subject.md", cwd=self.tmp / "m")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertRegex(res.stdout.strip(), r"^history/subject\.\d{4}-\d{2}-\d{2}_\d{6}\.md$")

    def test_missing_file_is_not_an_error(self):
        f = self.make(self.tmp / "m", "facts.md")
        res = run("history-copy", self.tmp / "m" / "missing.md", f, env=self.fake_date_env())
        self.assertEqual(res.returncode, 0)
        lines = res.stdout.splitlines()
        self.assertEqual(lines[0], "no file: %s" % (self.tmp / "m" / "missing.md"))
        self.assertTrue(lines[1].replace("\\", "/").endswith("history/facts.%s.md" % FIXED_STAMP))

    def test_windows_style_path(self):
        """C:\\...\\matter.md as Python on Windows passes it: the copy lands beside the file and its
        path comes back in the same style. INTAKE_WINPATHS=1 lets a non-Windows shell act the same."""
        f = self.make(self.tmp / "m", "matter.md", "page text")
        given = str(f).replace("/", "\\")
        env = dict(self.fake_date_env(), INTAKE_WINPATHS="1")
        res = run("history-copy", given, env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        dest = self.tmp / "m" / "history" / ("matter.%s.md" % FIXED_STAMP)
        self.assertEqual(res.stdout, "%s\n" % str(dest).replace("/", "\\"))
        self.assertEqual(dest.read_text(encoding="utf-8"), "page text")
        self.assertFalse((ROOT / "history").exists())
        missing = str(self.tmp / "m" / "missing.md").replace("/", "\\")
        self.assertEqual(run("history-copy", missing, env=env).stdout, "no file: %s\n" % missing)

    def test_usage_exit_2(self):
        self.assertEqual(run("history-copy").returncode, 2)
        self.assertEqual(run("history-copy", "-h").returncode, 0)


if __name__ == "__main__":
    unittest.main()
