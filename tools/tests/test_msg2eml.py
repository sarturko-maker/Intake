"""Tests for tools/msg2eml and tools/msg2eml.ps1.

The end-to-end tests use tools/fixtures/sample.msg (written by demo/build/msg) and skip cleanly
when it is absent, or when python-oxmsg or msgconvert is not installed.

Run: python3 -m unittest discover -s tools/tests -p 'test_*.py'
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOLS = ROOT / "tools"
FIXTURE = TOOLS / "fixtures" / "sample.msg"
FIXTURE_ID = "<fixture.202610010900@kestrel-eng.de>"
sys.path.insert(0, str(TOOLS / "lib"))


def tool_python_has_oxmsg():
    """Whether the Python the wrappers pick (find-python.sh) can import oxmsg."""
    res = subprocess.run(["bash", "-c", '. tools/lib/find-python.sh && $PY -c "import oxmsg"'],
                         cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0


HAVE_OXMSG_TOOL = tool_python_has_oxmsg()
HAVE_MSGCONVERT = shutil.which("msgconvert") is not None
try:
    import oxmsg  # noqa: F401
    HAVE_OXMSG_HERE = True
except ImportError:
    HAVE_OXMSG_HERE = False


def run(*args, env=None, cwd=None):
    e = dict(os.environ)
    e.pop("MSG2EML_METHOD", None)
    e.update(env or {})
    return subprocess.run(["bash", str(TOOLS / "msg2eml")] + [str(a) for a in args], cwd=str(cwd or ROOT), env=e,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8")


def parse(path):
    return BytesParser(policy=policy.default).parsebytes(Path(path).read_bytes())


class TempDirTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="msg2eml-test-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def copy_fixture(self, name="Vollmacht PoA for Kestrel Pumpen GmbH - who can sign.msg"):
        dest = self.tmp / name
        shutil.copyfile(str(FIXTURE), str(dest))
        return dest


@unittest.skipUnless(FIXTURE.is_file(), "tools/fixtures/sample.msg not present yet")
class SampleTest(TempDirTest):

    def check_eml(self, eml):
        m = parse(eml)
        self.assertEqual(str(m["Message-ID"]).strip(), FIXTURE_ID)
        self.assertEqual(m["From"].addresses[0].addr_spec, "lena.vogt@kestrel-eng.de")
        self.assertEqual(m["To"].addresses[0].addr_spec, "legal@kestrel-eng.co.uk")
        self.assertEqual(str(m["Subject"]), "Fixture: sample message")
        self.assertTrue(str(m["Date"]))
        body = m.get_body(("plain",))
        self.assertIsNotNone(body)
        self.assertIn("sample message", body.get_content())
        atts = [p for p in m.iter_attachments()]
        self.assertEqual([p.get_filename() for p in atts], ["fixture.txt"])
        self.assertEqual(atts[0].get_payload(decode=True), b"FIXTURE-ATTACHMENT")

    def convert(self, method):
        src = self.copy_fixture()
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        res = run(src, env={"MSG2EML_METHOD": method} if method else None)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        eml = src.with_suffix(".eml")
        self.assertTrue(eml.is_file())
        self.assertTrue(src.is_file())
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), before)
        self.check_eml(eml)
        return res, eml

    @unittest.skipUnless(HAVE_OXMSG_TOOL, "python-oxmsg not installed")
    def test_oxmsg_converts_the_sample(self):
        res, eml = self.convert("oxmsg")
        self.assertIn("(oxmsg)", res.stdout)
        self.assertIn(b"\r\n", eml.read_bytes())

    @unittest.skipUnless(HAVE_OXMSG_TOOL, "python-oxmsg not installed")
    def test_oxmsg_output_is_deterministic(self):
        src = self.copy_fixture("sample.msg")
        for out in ("one", "two"):
            res = run(src, "--outdir", self.tmp / out, env={"MSG2EML_METHOD": "oxmsg"})
            self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((self.tmp / "one" / "sample.eml").read_bytes(), (self.tmp / "two" / "sample.eml").read_bytes())

    @unittest.skipUnless(HAVE_MSGCONVERT, "msgconvert not installed")
    def test_msgconvert_converts_the_sample(self):
        res, eml = self.convert("msgconvert")
        self.assertIn("(msgconvert)", res.stdout)

    @unittest.skipUnless(HAVE_OXMSG_TOOL or HAVE_MSGCONVERT, "no converter installed")
    def test_default_order_and_unpack_end_to_end(self):
        res, eml = self.convert(None)
        self.assertIn("(oxmsg)" if HAVE_OXMSG_TOOL else "(msgconvert)", res.stdout)
        up = subprocess.run(["bash", str(TOOLS / "unpack-email"), "--json", "--no-signals", str(eml)],
                            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, encoding="utf-8")
        self.assertEqual(up.returncode, 0, up.stderr)
        d = json.loads(up.stdout)[0]
        self.assertEqual(d["message_id"], FIXTURE_ID.strip("<>"))
        self.assertEqual([(a["name"], a["kind"], a["sha256"]) for a in d["attachments"]],
                         [("fixture.txt", "document", hashlib.sha256(b"FIXTURE-ATTACHMENT").hexdigest())])

    @unittest.skipUnless(HAVE_OXMSG_TOOL or HAVE_MSGCONVERT, "no converter installed")
    def test_outdir_and_existing_eml_kept(self):
        src = self.copy_fixture("sample.msg")
        out = self.tmp / "out"
        res = run(src, "--outdir", out)
        self.assertEqual(res.returncode, 0, res.stderr)
        eml = out / "sample.eml"
        first = eml.read_bytes()
        self.assertFalse(src.with_suffix(".eml").exists())
        res = run(src, "--outdir", out)
        self.assertEqual(res.returncode, 0)
        self.assertIn("exists, kept", res.stdout)
        self.assertEqual(eml.read_bytes(), first)

    @unittest.skipUnless(HAVE_OXMSG_HERE, "python-oxmsg not importable by the test interpreter")
    def test_headers_rebuilt_from_properties_without_transport_headers(self):
        import msg2eml
        from oxmsg import Message
        msg = Message.load(str(FIXTURE))
        props = msg.properties
        real = props.str_prop_value
        props.str_prop_value = lambda pid: None if pid == 0x007D else real(pid)
        m = BytesParser(policy=policy.default).parsebytes(msg2eml.build_eml(msg))
        self.assertEqual(str(m["Message-ID"]).strip(), FIXTURE_ID)
        self.assertEqual(m["From"].addresses[0].addr_spec, "lena.vogt@kestrel-eng.de")
        self.assertEqual(m["To"].addresses[0].addr_spec, "legal@kestrel-eng.co.uk")
        self.assertEqual(str(m["Subject"]), "Fixture: sample message")
        self.assertIsNotNone(m["Date"].datetime)
        self.assertEqual([p.get_payload(decode=True) for p in m.iter_attachments()], [b"FIXTURE-ATTACHMENT"])


class ErrorsTest(TempDirTest):

    def test_usage_errors_exit_2(self):
        self.assertEqual(run().returncode, 2)
        txt = self.tmp / "note.txt"
        txt.write_text("x")
        self.assertEqual(run(txt).returncode, 2)
        self.assertEqual(run(self.tmp / "missing.msg").returncode, 2)
        bad = run(txt, env={"MSG2EML_METHOD": "bogus"})
        self.assertEqual(bad.returncode, 2)
        self.assertIn("MSG2EML_METHOD", bad.stderr)
        self.assertEqual(run("--help").returncode, 0)

    def test_unreadable_msg_exits_3_with_the_fallback(self):
        bad = self.tmp / "broken.msg"
        bad.write_bytes(b"this is not an Outlook file")
        res = run(bad)
        self.assertEqual(res.returncode, 3)
        self.assertIn("not converted: ", res.stdout)
        self.assertIn("msg2eml.ps1", res.stderr)
        self.assertIn(".eml", res.stderr)
        self.assertFalse((self.tmp / "broken.eml").exists())

    def test_forced_method_without_the_library_exits_3(self):
        fake = self.tmp / "fakelib" / "oxmsg"
        fake.mkdir(parents=True)
        (fake / "__init__.py").write_text("raise ImportError('hidden for the test')\n")
        msg = self.tmp / "x.msg"
        msg.write_bytes(b"\xd0\xcf\x11\xe0")
        res = run(msg, env={"MSG2EML_METHOD": "oxmsg", "PYTHONPATH": str(self.tmp / "fakelib")})
        self.assertEqual(res.returncode, 3)
        self.assertIn("python-oxmsg is not installed", res.stdout)


class PowerShellScriptTest(unittest.TestCase):

    def test_ps1_present_marked_untested_ascii_and_lf(self):
        ps1 = TOOLS / "msg2eml.ps1"
        data = ps1.read_bytes()
        text = data.decode("ascii")   # raises if not ASCII
        self.assertNotIn(b"\r", data)
        self.assertIn("UNTESTED IN THE BUILD CONTAINER", text)
        self.assertIn("OpenSharedItem", text)
        self.assertIn("PropertyAccessor", text)
        self.assertIn("http://schemas.microsoft.com/mapi/proptag/", text)
        self.assertIn("0x007D001F", text)


if __name__ == "__main__":
    unittest.main()


class ForgivingDecodeTest(unittest.TestCase):
    """A .msg labelled UTF-8 that holds a Windows-1252 byte (a curly quote): python-oxmsg raises on it,
    and msg2eml used to write the email with an empty body. Now the raw property is read and decoded."""

    def setUp(self):
        import msg2eml
        self.m = msg2eml

    def test_decode_8bit(self):
        raw = "Bitte prüfen – it".encode("utf-8") + b"\x92s urgent"
        self.assertEqual(self.m.decode_8bit(raw, "utf-8"), "Bitte prüfen – it’s urgent")
        self.assertEqual(self.m.decode_8bit(b"caf\xe9 \x80 5", "cp1252"), "caf\xe9 € 5")
        self.assertEqual(self.m.decode_8bit(b"caf\xe9", "no-such-code-page"), "caf\xe9")
        self.assertEqual(self.m.decode_8bit("ok \xfc".encode("utf-8"), "utf-8"), "ok \xfc")

    def fake(self, body_raw, html_raw=None):
        """Stands in for an oxmsg Message whose body properties are 8-bit and labelled UTF-8."""
        class Prop:
            def __init__(self, pid, ptyp):
                self.pid, self.ptyp = pid, ptyp

        class Storage:
            def property_stream_bytes(self, pid, ptyp):
                return {0x1000: body_raw, 0x1013: html_raw}[pid]

        class Props:
            body_encoding = "utf-8"
            _storage = Storage()

            def _get_property(self, pid, ptyps):
                if pid == 0x1000 and body_raw is not None and 0x001E in ptyps:
                    return Prop(pid, 0x001E)
                if pid == 0x1013 and html_raw is not None and 0x0102 in ptyps:
                    return Prop(pid, 0x0102)
                return None

        class Msg:
            properties = Props()

            @property
            def body(self):            # strict, as python-oxmsg 0.0.2 decodes: raises on a stray byte
                return body_raw.decode("utf-8") if body_raw is not None else None

            @property
            def html_body(self):
                return html_raw.decode("utf-8") if html_raw is not None else None

        return Msg()

    def test_body_is_kept_when_the_library_cannot_decode_it(self):
        msg = self.fake(b"We can\x92t accept clause 9.\r\n")
        self.assertEqual(self.m.body_text(msg), "We can’t accept clause 9.\r\n")
        self.assertIsNone(self.m.html_text(msg))
        msg = self.fake(b"plain", html_raw=b"<p>Caf\xe9 \x96 noted</p>")
        self.assertEqual(self.m.html_text(msg), "<p>Caf\xe9 – noted</p>")

    def test_no_body_stays_empty(self):
        self.assertEqual(self.m.body_text(self.fake(None)), "")

    @unittest.skipUnless(FIXTURE.is_file(), "tools/fixtures/sample.msg not present yet")
    def test_raw_reading_matches_the_library_on_a_good_file(self):
        try:
            from oxmsg import Message
        except ImportError:
            self.skipTest("python-oxmsg not installed")
        msg = Message.load(str(FIXTURE))
        want = msg.body
        self.assertTrue(want)
        self.assertEqual(self.m._prop_text(msg.properties, self.m.PID_BODY, self.m.TEXT_TYPES, ""), want)
        self.assertEqual(self.m.body_text(msg), want.replace("\x00", ""))


@unittest.skipUnless(FIXTURE.is_file() and HAVE_OXMSG_TOOL, "needs tools/fixtures/sample.msg and python-oxmsg")
class RefreshTest(unittest.TestCase):
    """msg2eml --refresh: a filed email that an older version converted without its body is re-converted
    from the .msg original kept beside it."""

    def test_refresh_restores_a_lost_body(self):
        sys.path.insert(0, str(HERE))
        from test_new_matter import Workspace
        import common
        import msg2eml
        ws = Workspace()
        self.addCleanup(ws.cleanup)
        ref, m = ws.new_matter("commercial", "kestrel", "poa", sub_area="customers")
        corr = m / "agent" / "correspondence"
        name = "2026-10-20_0900_in_lena-vogt_vollmacht"
        shutil.copy2(str(FIXTURE), str(corr / (name + ".msg")))
        empty = (b"From: Lena Vogt <lena.vogt@kestrel-eng.de>\r\nSubject: Vollmacht\r\nMessage-ID: <x@y>\r\n"
                 b"Content-Type: text/plain; charset=utf-8\r\n\r\n")
        eml = corr / (name + ".eml")
        eml.write_bytes(empty)
        os.chmod(str(eml), 0o444)              # received files are read-only on disk
        common.append_line(m / "agent" / "documents.md", common.join_pipe(
            [eml.name, "correspondence", "received", "lena.vogt@kestrel-eng.de", "2026-10-20 09:00", "", "x@y",
             common.sha256_file(eml), "yes", "empty", ""]))
        r = ws.run("msg2eml", "--refresh", "--run", "R1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1 emails re-converted", r.stdout)
        self.assertTrue(msg2eml.eml_body_text(eml.read_bytes()))
        self.assertFalse(os.stat(str(eml)).st_mode & 0o222)
        self.assertEqual((m / "agent" / "history" / (name + ".empty-body.eml")).read_bytes(), empty)
        rows = common.read_pipe_records(m / "agent" / "documents.md", common.DOCUMENTS_COLUMNS)
        self.assertEqual((rows[0]["hash"], rows[0]["read"]), (common.sha256_file(eml), "pending"))
        self.assertIn("re-converted correspondence/%s.eml" % name, (m / "agent" / "log.md").read_text())
        self.assertEqual(ws.run("lint-received").returncode, 0)
        # a good email is left alone
        self.assertIn("0 emails re-converted", ws.run("msg2eml", "--refresh", "--run", "R2").stdout)
