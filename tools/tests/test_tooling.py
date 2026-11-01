"""Tests for tools/tooling-setup (spec D12). Nothing is installed: TOOLING_DRY_RUN=1, or fake managers."""

import hashlib
import os
import shutil
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsfixture import ROOT, Workspace, make_bin  # noqa: E402

ITEMS = ["shell", "sha256", "python3", "msg converter", "pandoc", "munpack/ripmime", "python-docx", "git",
         "hooks", "deny rules"]
STATUSES = {"found", "installed", "missing", "blocked", "configured", "verified"}
CONFIGURED = "configured | - | - | prove at cold start (RULES.md obligations if the harness ignores them)"
SETTINGS = """{
  "permissions": {
    "deny": [
      "Edit(**/corrections.md)", "Write(**/corrections.md)",
      "Edit(**/roster.confirmed.md)", "Write(**/roster.confirmed.md)",
      "Edit(house/**)", "Write(house/**)"
    ]
  },
  "hooks": {
    "PreToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "bash .claude/hooks/before-write"}]}],
    "PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "bash .claude/hooks/after-write"}]}]
  }
}
"""
REAL_PY = shutil.which("python3") or sys.executable
HIDE = ("pandoc", "munpack", "ripmime", "msgconvert", "apt-get", "sudo", "brew", "winget")
FAKE_APT_OK = "#!/bin/sh\necho \"apt-get $*\" >> \"$FAKE_LOG\"\nexit 0\n"
FAKE_APT_FAIL = "#!/bin/sh\necho \"apt-get $*\" >> \"$FAKE_LOG\"\n[ \"$1\" = update ] && exit 0\necho 'E: Unable to locate package pandoc' >&2\nexit 100\n"
FAKE_SUDO = "#!/bin/sh\nexec \"$@\"\n"
FAKE_PY_PEP668 = ("#!/bin/sh\nif [ \"$1\" = -m ] && [ \"$2\" = pip ] && [ \"$3\" = install ]; then\n"
                  "  echo \"pip $*\" >> \"$FAKE_LOG\"\n"
                  "  echo 'error: externally-managed-environment' >&2\n  exit 1\nfi\nexec %s \"$@\"\n" % REAL_PY)


def pip_available():
    return subprocess.call([REAL_PY, "-m", "pip", "--version"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0


def minimal_docx(path, inserted):
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/'
          'package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
          'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/'
          'document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.'
            'openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.'
           'openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t xml:space="preserve">Cap: </w:t>'
           '</w:r><w:ins w:id="1" w:author="Reviewer" w:date="2026-10-16T10:40:00Z"><w:r><w:t>%s</w:t></w:r></w:ins>'
           '</w:p></w:body></w:document>' % inserted)
    with zipfile.ZipFile(str(path), "w") as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)


SAMPLE_EML = (b"From: Lena Vogt <lena.vogt@kestrel-eng.de>\r\n"
              b"To: legal@kestrel-eng.co.uk\r\n"
              b"Subject: Fixture: sample email\r\n"
              b"Date: Thu, 01 Oct 2026 09:00:00 +0200\r\n"
              b"Message-ID: <testfixture.202610010900@kestrel-eng.de>\r\n"
              b"MIME-Version: 1.0\r\n"
              b"Content-Type: multipart/mixed; boundary=\"b1\"\r\n\r\n"
              b"--b1\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nPlease see the attached note.\r\n"
              b"--b1\r\nContent-Type: text/plain; name=\"fixture-note.txt\"\r\n"
              b"Content-Disposition: attachment; filename=\"fixture-note.txt\"\r\n\r\nFIXTURE-ATTACHMENT\r\n"
              b"--b1--\r\n")


@unittest.skipIf(os.name == "nt", "uses a symlinked PATH folder")
class ToolingSetupTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(skills=False)
        self.ws.write(".claude/settings.json", SETTINGS)
        self.fix = self.ws.root / "tools" / "fixtures"
        self.log = self.ws.tmp / "fake.log"

    def tearDown(self):
        self.ws.cleanup()

    def setup_tool(self, *args, path=None, **env):
        e = self.ws.env(FAKE_LOG=str(self.log), **env)
        if path is not None:
            e["PATH"] = str(path)
        return self.ws.run("tooling-setup", *args, env=e)

    def table(self):
        lines = self.ws.read("TOOLING.md").splitlines()
        self.assertEqual(lines[0], "# Tooling")
        self.assertIn("Written by tools/tooling-setup on", lines[1])
        self.assertIn("OS:", lines[1])
        start = lines.index("item | status | version | fallback in use | note")
        rows = [line.split(" | ") for line in lines[start + 1:] if line.strip()]
        self.assertEqual([r[0] for r in rows], ITEMS)
        for r in rows:
            self.assertEqual(len(r), 5, r)
            self.assertIn(r[1], STATUSES, r)
        return {r[0]: r for r in rows}

    def hidden_bin(self, extra=None, hide=HIDE, name="bin"):
        scripts = {"apt-get": FAKE_APT_OK, "sudo": FAKE_SUDO}
        scripts.update(extra or {})
        return make_bin(self.ws.tmp / name, hide=hide, extra=scripts)

    def fake_modules(self):
        d = self.ws.tmp / "fakemods"
        d.mkdir(exist_ok=True)
        for name in ("oxmsg", "docx"):
            (d / (name + ".py")).write_text("raise ImportError('hidden for a test')\n")
        return str(d)

    # ------------------------------------------------------------ TOOLING.md

    def test_writes_the_ten_item_lines(self):
        shutil.rmtree(str(self.fix), ignore_errors=True)
        r = self.setup_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("TOOLING.md written:", r.stdout)
        rows = self.table()
        self.assertEqual(rows["shell"][1], "found")
        self.assertTrue(rows["shell"][2].startswith("bash "))
        self.assertEqual(" | ".join(rows["hooks"][1:]), CONFIGURED)
        self.assertEqual(" | ".join(rows["deny rules"][1:]), CONFIGURED)
        self.assertIn("not verified: fixture missing", rows["sha256"][4])

    def test_hooks_and_deny_rules_missing(self):
        (self.ws.root / ".claude" / "settings.json").unlink()
        self.setup_tool("--verify-only")
        rows = self.table()
        self.assertEqual(rows["hooks"][1], "missing")
        self.assertEqual(rows["deny rules"][1], "missing")
        self.assertIn(".claude/settings.json not found", rows["hooks"][4])
        self.ws.write(".claude/settings.json", SETTINGS.replace('"Edit(house/**)", "Write(house/**)"', '"Read(x)"'))
        self.setup_tool("--verify-only")
        rows = self.table()
        self.assertEqual(rows["deny rules"][1], "missing")
        self.assertIn("lack: house/", rows["deny rules"][4])
        self.assertEqual(rows["hooks"][1], "configured")

    # ------------------------------------------------------------ missing items, the question, installs

    def test_missing_items_print_commands_and_one_question(self):
        r = self.setup_tool(path=self.hidden_bin(), PYTHONPATH=self.fake_modules())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = self.table()
        for item in ("msg converter", "pandoc", "munpack/ripmime", "python-docx"):
            self.assertEqual(rows[item][1], "missing", rows[item])
        self.assertIn("unzip the .docx and strip tags", rows["pandoc"][3])
        self.assertIn("ask the human to save the email as .eml", rows["msg converter"][3])
        self.assertIn("Install commands:", r.stdout)
        if pip_available():
            self.assertIn("  python3 -m pip install --user python-oxmsg", r.stdout)
            self.assertIn("Ask the human once: May I install: python-oxmsg, pandoc, mpack (using pip/apt)?", r.stdout)
        else:
            self.assertIn("libemail-outlook-message-perl", r.stdout)
        self.assertRegex(r.stdout, r"\n  (sudo )?apt-get install -y (libemail-outlook-message-perl )?pandoc mpack\n")
        self.assertIn("If yes: run bash tools/tooling-setup --install", r.stdout)
        self.assertIn("install with:", rows["pandoc"][4])
        self.assertFalse(self.log.exists(), "nothing was run")

    def test_dry_run_install_prints_what_it_would_run(self):
        r = self.setup_tool("--install", path=self.hidden_bin(), PYTHONPATH=self.fake_modules(), TOOLING_DRY_RUN="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        if pip_available():
            self.assertIn("+ python3 -m pip install --user python-oxmsg", r.stdout)
        self.assertRegex(r.stdout, r"\+ env DEBIAN_FRONTEND=noninteractive (sudo )?apt-get install -y "
                                   r"(libemail-outlook-message-perl )?pandoc mpack")
        self.assertNotIn("May I install", r.stdout)
        rows = self.table()
        for item in ("msg converter", "pandoc", "munpack/ripmime"):
            self.assertEqual(rows[item][1], "missing")
            self.assertIn("dry run: would run:", rows[item][4])
        self.assertFalse(self.log.exists(), "the dry run ran nothing")

    def test_blocked_installs_are_recorded_with_the_fallback(self):
        path = self.hidden_bin(extra={"apt-get": FAKE_APT_FAIL, "python3": FAKE_PY_PEP668},
                               hide=HIDE + ("python3",))
        r = self.setup_tool("--install", "--yes", path=path, PYTHONPATH=self.fake_modules())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = self.log.read_text()
        if pip_available():
            self.assertIn("+ python3 -m pip install --user python-oxmsg", r.stdout)
            self.assertIn("+ python3 -m pip install --user --break-system-packages python-oxmsg", r.stdout,
                          "PEP 668: retried with --break-system-packages")
            self.assertEqual(log.count("pip -m pip install"), 2)
        self.assertIn("apt-get update", log, "package lists refreshed once after 'Unable to locate package'")
        self.assertEqual(log.count("install -y"), 2)
        rows = self.table()
        for item in ("msg converter", "pandoc", "munpack/ripmime"):
            self.assertEqual(rows[item][1], "blocked", rows[item])
            self.assertIn("install failed", rows[item][4])
            self.assertNotEqual(rows[item][3], "-", "a blocked item names its fallback")

    def test_successful_install_is_recorded_as_installed(self):
        apt = ("#!/bin/sh\n"
               "echo \"apt-get $*\" >> \"$FAKE_LOG\"\n"
               "d=\"$(dirname \"$0\")\"\n"
               "printf '#!/bin/sh\\necho \"pandoc 9.9\"\\n' > \"$d/pandoc\"\n"
               "printf '#!/bin/sh\\nexit 0\\n' > \"$d/munpack\"\n"
               "chmod +x \"$d/pandoc\" \"$d/munpack\"\n"
               "exit 0\n")
        path = self.hidden_bin(extra={"apt-get": apt})
        shutil.rmtree(str(self.fix), ignore_errors=True)
        r = self.setup_tool("--install", "--yes", path=path)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = self.table()
        self.assertEqual(rows["pandoc"][1], "installed", rows["pandoc"])
        self.assertEqual(rows["pandoc"][2], "9.9")
        self.assertIn("installed now with:", rows["pandoc"][4])
        self.assertEqual(rows["munpack/ripmime"][1], "installed")

    def test_verify_only_gives_no_install_advice(self):
        r = self.setup_tool("--verify-only", path=self.hidden_bin(), PYTHONPATH=self.fake_modules())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("May I install", r.stdout)
        self.assertNotIn("Install commands", r.stdout)
        self.assertTrue((self.ws.root / "TOOLING.md").exists())

    def test_python_fallbacks(self):
        path = self.hidden_bin(extra={"python": "#!/bin/sh\nexec %s \"$@\"\n" % REAL_PY}, hide=HIDE + ("python3*",))
        self.setup_tool("--verify-only", path=path)
        self.assertEqual(self.table()["python3"][3], "python")
        nopy = self.hidden_bin(hide=HIDE + ("python*", "py", "pydoc*"), name="nopy-bin")
        self.setup_tool("--verify-only", path=nopy)
        rows = self.table()
        self.assertEqual(rows["python3"][1], "missing")
        self.assertIn("shell plus munpack", rows["python3"][3])
        self.assertEqual(rows["msg converter"][1], "missing")
        self.assertIn(rows["sha256"][1], ("found", "verified"))

    # ------------------------------------------------------------ verification on fixtures

    def write_fixtures(self, eml=SAMPLE_EML, expected_hash=None):
        shutil.rmtree(str(self.fix), ignore_errors=True)
        self.fix.mkdir(parents=True)
        (self.fix / "sample.eml").write_bytes(eml)
        minimal_docx(self.fix / "sample.docx", "INSERTED-MARKER")
        if (ROOT / "tools" / "fixtures" / "sample.msg").exists():
            shutil.copy2(str(ROOT / "tools" / "fixtures" / "sample.msg"), str(self.fix / "sample.msg"))
        (self.fix / "EXPECTED.txt").write_text(
            "# Expected values for tools/tooling-setup\n"
            "sample.eml sha256: %s\n"
            "sample.eml message-id: <testfixture.202610010900@kestrel-eng.de>\n"
            "sample.eml attachment: fixture-note.txt\n"
            "sample.docx inserted: INSERTED-MARKER\n"
            "sample.msg message-id: <fixture.202610010900@kestrel-eng.de>\n"
            % (expected_hash or hashlib.sha256(SAMPLE_EML).hexdigest()))

    @unittest.skipUnless(shutil.which("pandoc"), "pandoc not installed here")
    def test_verification_on_fixtures(self):
        self.write_fixtures()
        r = self.setup_tool("--verify-only")
        rows = self.table()
        self.assertEqual(rows["sha256"][1], "verified", rows["sha256"])
        self.assertEqual(rows["pandoc"][1], "verified", rows["pandoc"])
        if (ROOT / "tools" / "unpack-email").exists():
            self.assertEqual(rows["python3"][1], "verified", rows["python3"])
        if (self.fix / "sample.msg").exists() and rows["msg converter"][2] != "-":
            self.assertEqual(rows["msg converter"][1], "verified", rows["msg converter"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_failed_verification_exits_1(self):
        self.write_fixtures(expected_hash="0" * 64)
        r = self.setup_tool("--verify-only")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("check failed: sha256: verification failed", r.stdout)
        self.assertEqual(self.table()["sha256"][1], "found")

    @unittest.skipUnless((ROOT / "tools" / "fixtures" / "EXPECTED.txt").exists(), "repository fixtures not written yet")
    def test_repository_fixtures_verify(self):
        r = self.setup_tool("--verify-only")
        rows = self.table()
        self.assertEqual(rows["sha256"][1], "verified", rows["sha256"])
        self.assertNotIn("verification failed", r.stdout)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_usage_errors(self):
        self.assertEqual(self.setup_tool("--bogus").returncode, 2)
        self.assertEqual(self.setup_tool("--install", "--verify-only").returncode, 2)
        self.assertEqual(self.setup_tool("--yes").returncode, 2)


if __name__ == "__main__":
    unittest.main()
