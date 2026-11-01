"""Tests for tools/place-email.

Run: python3 -m unittest discover -s tools/tests -p 'test_*.py'
"""

import hashlib
import json
import sys
import unittest
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_new_matter import WorkspaceTest  # noqa: E402
from test_unpack import ALEX, DOCX, JULIA, PNG_SMALL, TOM, make_email  # noqa: E402

import common  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PlaceBase(WorkspaceTest):

    def setUp(self):
        super().setUp()
        self.ref, self.matter = self.ws.new_matter("commercial", "acme-automotive", "msa-liability-cap",
                                                   sub_area="customers", opened="2026-10-15")
        self.mrel = self.matter.relative_to(self.ws.root).as_posix()

    def inbox(self, name):
        return self.ws.path("inbox/" + name)

    def place(self, file, *args, ok=True):
        res = self.ws.run("place-email", file, *args)
        if ok:
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return res

    def docs(self, matter=None):
        return common.read_pipe_records(Path(matter or self.matter) / "documents.md", common.DOCUMENTS_COLUMNS)

    def unpack(self, file):
        res = self.ws.run("unpack-email", "--json", "--no-signals", file)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)[0]


class IntoMatterTest(PlaceBase):

    def test_files_email_attachments_rows_log_and_journal(self):
        f = make_email(self.inbox("Acme MSA - draft.eml"), sender=JULIA, to=(TOM,),
                       subject="Acme Master Supply Agreement - draft for review",
                       date="Thu, 15 Oct 2026 08:47:00 +0200", message_id="<b1-04.202610150847@acme-automotive.de>",
                       attachments=[("Acme_MSA_v1.docx", b"PK\x03\x04 msa v1", DOCX)],
                       inline_images=[("image001.png", PNG_SMALL, "image001.png@01DB")])
        info = self.unpack(f)
        before = sha(f)
        self.place(f, "--to", self.mrel, "--run", "R1", "--reason", "new matter for the MSA", "--confidence", "0.9")
        self.assertFalse(f.exists())
        dest = self.matter / "correspondence" / info["canonical_name"]
        self.assertTrue(dest.is_file())
        self.assertEqual(sha(dest), before)
        stored = self.matter / "documents" / "received" / "Acme_MSA_v1.docx"
        self.assertEqual(stored.read_bytes(), b"PK\x03\x04 msa v1")
        self.assertFalse((self.matter / "documents" / "received" / "image001.png").exists())
        rows = self.docs()
        self.assertEqual([(r["name"], r["folder"], r["origin"], r["read"]) for r in rows], [
            (info["canonical_name"], "correspondence", "received", "pending"),
            ("image001.png", "", "received", "no: signature image"),
            ("Acme_MSA_v1.docx", "documents/received", "received", "pending")])
        for r in rows:
            self.assertEqual(r["message_id"], "b1-04.202610150847@acme-automotive.de")
            self.assertEqual(r["from"], "j.schmidt@acme-automotive.de")
            self.assertEqual(r["date"], info["date"])
        self.assertEqual(rows[0]["hash"], before)
        self.assertEqual(rows[2]["hash"], sha(stored))
        self.assertEqual(rows[2]["hash"], info["attachments"][1]["sha256"])
        log = common.read_pipe_records(self.matter / "log.md", common.LOG_COLUMNS)
        self.assertEqual(log[-1]["event"], "filed in email from j.schmidt@acme-automotive.de: "
                                           "Acme Master Supply Agreement - draft for review")
        self.assertEqual(log[-1]["source"], "correspondence/" + info["canonical_name"])
        self.assertEqual(log[-1]["run"], "R1")
        j = common.split_pipe(self.ws.journal_lines()[-1])
        self.assertEqual(j[1:], ["R1", "filed", "inbox/Acme MSA - draft.eml", self.mrel + "/correspondence/" +
                                 info["canonical_name"], "new matter for the MSA", "0.9"])

    def test_reference_accepted_for_to(self):
        f = make_email(self.inbox("a.eml"))
        self.place(f, "--to", self.ref)
        self.assertEqual(len(list((self.matter / "correspondence").iterdir())), 1)

    def test_out_email_goes_to_documents_ours(self):
        f = make_email(self.inbox("RE Acme NDA.eml"), sender=ALEX, to=(TOM,), subject="RE: Acme NDA",
                       attachments=[("Acme_NDA_v1_Kestrel.docx", b"PK our markup", DOCX)])
        self.place(f, "--to", self.mrel)
        self.assertTrue((self.matter / "documents" / "ours" / "Acme_NDA_v1_Kestrel.docx").is_file())
        rows = self.docs()
        self.assertEqual([(r["folder"], r["origin"]) for r in rows],
                         [("correspondence", "ours"), ("documents/ours", "ours")])
        self.assertIn("_out_alexmorgan_", rows[0]["name"])

    def test_duplicate_attachment_stored_once(self):
        msa = b"PK identical MSA bytes"
        a = make_email(self.inbox("a.eml"), sender=JULIA, subject="Acme MSA draft",
                       message_id="<b1-04@acme-automotive.de>", attachments=[("Acme_MSA_v1.docx", msa, DOCX)])
        b = make_email(self.inbox("b.eml"), sender=TOM, subject="FW: Acme MSA draft",
                       date="Thu, 15 Oct 2026 09:30:00 +0100", message_id="<b1-05@kestrel-eng.co.uk>",
                       attachments=[("Acme MSA v1 (copy).docx", msa, DOCX)])
        self.place(a, "--to", self.mrel, "--run", "R1")
        res = self.place(b, "--to", self.mrel, "--run", "R1")
        self.assertIn("duplicate: Acme MSA v1 (copy).docx", res.stdout)
        self.assertEqual(sorted(p.name for p in (self.matter / "documents" / "received").iterdir()),
                         ["Acme_MSA_v1.docx"])
        rows = [r for r in self.docs() if r["name"].endswith(".docx")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["duplicate_of"], "")
        self.assertEqual(rows[1]["duplicate_of"], "Acme_MSA_v1.docx")
        self.assertEqual(rows[1]["folder"], "")
        self.assertEqual(rows[1]["read"], "no: duplicate of Acme_MSA_v1.docx")
        self.assertEqual(rows[1]["message_id"], "b1-05@kestrel-eng.co.uk")
        self.assertEqual(rows[0]["hash"], rows[1]["hash"])

    def test_same_name_different_content_gets_suffix(self):
        a = make_email(self.inbox("a.eml"), subject="v1", attachments=[("MSA.docx", b"PK one", DOCX)])
        b = make_email(self.inbox("b.eml"), subject="v2", attachments=[("MSA.docx", b"PK two", DOCX)])
        self.place(a, "--to", self.mrel)
        self.place(b, "--to", self.mrel)
        received = self.matter / "documents" / "received"
        self.assertEqual((received / "MSA.docx").read_bytes(), b"PK one")
        self.assertEqual((received / "MSA-2.docx").read_bytes(), b"PK two")
        self.assertEqual([r["name"] for r in self.docs() if r["name"].startswith("MSA")], ["MSA.docx", "MSA-2.docx"])

    def test_identical_email_dropped_twice(self):
        f = make_email(self.inbox("Acme NDA.eml"), attachments=[("NDA.docx", b"PK nda", DOCX)])
        data = f.read_bytes()
        self.place(f, "--to", self.mrel, "--run", "R1")
        again = self.inbox("Acme NDA (2).eml")
        again.write_bytes(data)
        res = self.place(again, "--to", self.mrel, "--run", "R2")
        self.assertIn("duplicate-dropped", res.stdout)
        self.assertFalse(again.exists())
        self.assertEqual(len(list((self.matter / "correspondence").iterdir())), 1)
        self.assertEqual(len([r for r in self.docs() if r["folder"] == "correspondence"]), 1)
        self.assertEqual(len([r for r in self.docs() if r["name"] == "NDA.docx"]), 1)
        j = common.split_pipe(self.ws.journal_lines()[-1])
        self.assertEqual(j[1:4], ["R2", "duplicate-dropped", "inbox/Acme NDA (2).eml"])

    def test_msg_sibling_moves_with_its_eml(self):
        f = make_email(self.inbox("Vollmacht PoA.eml"), sender=("Lena Vogt", "lena.vogt@kestrel-eng.de"),
                       subject="Vollmacht / PoA for Kestrel Pumpen GmbH - who can sign?")
        msg = self.inbox("Vollmacht PoA.msg")
        msg.write_bytes(b"\xd0\xcf\x11\xe0 original outlook bytes")
        self.place(f, "--to", self.mrel)
        corr = sorted((self.matter / "correspondence").iterdir())
        self.assertEqual([p.suffix for p in corr], [".eml", ".msg"])
        self.assertEqual(corr[0].stem, corr[1].stem)
        self.assertEqual(corr[1].read_bytes(), b"\xd0\xcf\x11\xe0 original outlook bytes")
        self.assertFalse(msg.exists())
        rows = self.docs()
        self.assertEqual(rows[1]["name"], corr[1].name)
        self.assertEqual(rows[1]["read"], "no: original of %s" % corr[0].name)
        self.assertEqual(rows[1]["hash"], sha(corr[1]))

    def test_same_msg_dropped_twice_even_when_converted_eml_differs(self):
        outlook = b"\xd0\xcf\x11\xe0 the same outlook file"
        first = make_email(self.inbox("PoA.eml"), body="converted once")
        self.inbox("PoA.msg").write_bytes(outlook)
        self.place(first, "--to", self.mrel, "--run", "R1")
        second = make_email(self.inbox("PoA (2).eml"), body="converted again, other bytes")
        self.inbox("PoA (2).msg").write_bytes(outlook)
        res = self.place(second, "--to", self.mrel, "--run", "R2")
        self.assertIn("duplicate-dropped", res.stdout)
        self.assertFalse(second.exists())
        self.assertFalse(self.inbox("PoA (2).msg").exists())
        self.assertEqual(sorted(p.suffix for p in (self.matter / "correspondence").iterdir()), [".eml", ".msg"])
        j = common.split_pipe(self.ws.journal_lines()[-1])
        self.assertEqual(j[1:4], ["R2", "duplicate-dropped", "inbox/PoA (2).msg"])

    def test_canonical_name_clash_gets_suffix(self):
        a = make_email(self.inbox("a.eml"), body="First version of the text.")
        b = make_email(self.inbox("b.eml"), body="Second, different text.")
        self.place(a, "--to", self.mrel)
        self.place(b, "--to", self.mrel)
        names = sorted(p.name for p in (self.matter / "correspondence").iterdir())
        self.assertEqual(len(names), 2)
        self.assertTrue(names[1].endswith("-2.eml") or names[0].endswith("-2.eml"))
        stem = names[0][:-4] if not names[0].endswith("-2.eml") else names[1][:-4]
        self.assertIn(stem + "-2.eml", names)

    def test_calendar_part_and_attached_email(self):
        inner = EmailMessage()
        inner["From"] = "accounts@northgate-logistics.com"
        inner["Subject"] = "Invoice 4471"
        inner.set_content("Short payment.")
        f = make_email(self.inbox("a.eml"), attachments=[("invite.ics", b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n", "text/calendar")],
                       attached_emails=[inner])
        info = self.unpack(f)
        self.place(f, "--to", self.mrel)
        rows = {r["name"]: r for r in self.docs()}
        self.assertEqual(rows["invite.ics"]["read"], "no: calendar part")
        self.assertEqual(rows["invite.ics"]["folder"], "")
        stored = self.matter / "documents" / "received" / "invoice-4471.eml"
        self.assertTrue(stored.is_file())
        self.assertEqual(rows["invoice-4471.eml"]["hash"], sha(stored))
        self.assertEqual(rows["invoice-4471.eml"]["hash"], info["attachments"][1]["sha256"])

    def test_cross_ref(self):
        ref2, other = self.ws.new_matter("commercial", "acme-automotive", "security-questionnaire",
                                         sub_area="customers", opened="2026-10-19")
        f = make_email(self.inbox("a.eml"), sender=JULIA, subject="MSA and questionnaire")
        self.place(f, "--to", self.mrel, "--cross-ref", other.relative_to(self.ws.root).as_posix(), "--run", "R3")
        log = common.read_pipe_records(other / "log.md", common.LOG_COLUMNS)
        self.assertTrue(log[-1]["event"].startswith("cross-ref: email filed in %s" % self.ref))
        self.assertTrue(log[-1]["source"].startswith(self.mrel + "/correspondence/"))
        actions = [common.split_pipe(l)[2] for l in self.ws.journal_lines()]
        self.assertEqual(actions[-2:], ["filed", "cross-ref"])

    def test_json_output(self):
        f = make_email(self.inbox("a.eml"), attachments=[("NDA.docx", b"PK", DOCX)])
        res = self.place(f, "--to", self.mrel, "--json")
        d = json.loads(res.stdout)
        self.assertEqual([a["action"] for a in d["actions"]], ["filed", "stored"])
        self.assertEqual(d["matter"], self.mrel)
        self.assertTrue(d["destination"].startswith(self.mrel + "/correspondence/"))

    def test_safe_to_call_many_times_in_one_run(self):
        for i in range(5):
            f = make_email(self.inbox("m%d.eml" % i), subject="Message %d" % i, message_id="<m%d@x>" % i,
                           attachments=[("doc%d.pdf" % i, b"%%PDF %d" % i, "application/pdf")])
            self.place(f, "--to", self.mrel, "--run", "R1")
        self.assertEqual(len([r for r in self.docs() if r["folder"] == "correspondence"]), 5)
        self.assertEqual(len(list((self.matter / "documents" / "received").iterdir())), 5)
        self.assertEqual(len(self.ws.journal_lines()), 6)  # new-matter + 5 filed
        text = (self.matter / "documents.md").read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n"))


class NoiseAndCheckTest(PlaceBase):

    def test_noise_ids_allocated_in_order(self):
        names = []
        for i, (subj, hdr) in enumerate([("Autumn employment law update", {"List-Unsubscribe": "<mailto:u@brightlaw.co.uk>"}),
                                         ("Out of office: Jonas Keller until 2 November", {"Auto-Submitted": "auto-replied"}),
                                         ("New 2027 catalogue", {})]):
            f = make_email(self.inbox("n%d.eml" % i), subject=subj, headers=hdr, message_id="<n%d@x>" % i)
            args = ["--to", "noise", "--run", "R1"]
            if i == 2:
                args += ["--title", "Seal supplier catalogue", "--label", "marketing"]
            self.place(f, *args)
            names.append(f.name)
        csv_path = self.ws.path("inbox/noise/NOISE.csv")
        raw = csv_path.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbfid,file,received,from,subject,title,label,status,"
                                       b"proposed_outcome,confirmed_outcome,confirmed_by\r\n"))
        rows = common.read_csv(csv_path)
        self.assertEqual([r["id"] for r in rows], ["NOISE-0001", "NOISE-0002", "NOISE-0003"])
        self.assertEqual([r["label"] for r in rows], ["bulk", "auto-reply", "marketing"])
        self.assertEqual(rows[0]["title"], "Autumn employment law update")
        self.assertEqual(rows[2]["title"], "Seal supplier catalogue")
        self.assertEqual({r["status"] for r in rows}, {"waiting_lawyer"})
        self.assertEqual({r["proposed_outcome"] for r in rows}, {"nothing_needed"})
        for r in rows:
            self.assertTrue(self.ws.path(r["file"]).is_file())
            self.assertTrue(r["file"].startswith("inbox/noise/2026-10-12_"))
        self.assertEqual([common.split_pipe(l)[2] for l in self.ws.journal_lines()].count("noise"), 3)

    def test_noise_id_continues_after_existing_rows(self):
        common.write_csv(self.ws.path("inbox/noise/NOISE.csv"), common.NOISE_COLUMNS,
                         [{"id": "NOISE-0007", "file": "inbox/noise/confirmed/x.eml", "status": "closed"}])
        f = make_email(self.inbox("n.eml"), subject="Newsletter")
        self.place(f, "--to", "noise")
        self.assertEqual([r["id"] for r in common.read_csv(self.ws.path("inbox/noise/NOISE.csv"))],
                         ["NOISE-0007", "NOISE-0008"])

    def test_please_check_note_with_claimed_reference_and_candidates(self):
        f = make_email(self.inbox("Quick question.eml"), sender=JULIA, subject="Quick question",
                       date="Wed, 21 Oct 2026 16:05:00 +0200")
        self.place(f, "--to", "please-check", "--run", "R2", "--claimed", self.ref,
                   "--candidates", "%s, 2026-0006" % self.ref, "--confidence", "0.4",
                   "--note", "No tag and no thread. I would file it in the MSA matter. Decide which matter.")
        notes = list(self.ws.path("inbox/please-check").glob("*.note.md"))
        self.assertEqual(len(notes), 1)
        meta, body = common.read_frontmatter_file(notes[0])
        self.assertEqual(list(meta), ["file", "received", "from", "subject", "claimed_reference", "candidates", "run"])
        self.assertEqual(meta["claimed_reference"], self.ref)
        self.assertEqual(meta["candidates"], "%s, 2026-0006" % self.ref)
        self.assertEqual(meta["from"], "j.schmidt@acme-automotive.de")
        self.assertEqual(meta["subject"], "Quick question")
        self.assertEqual(meta["run"], "R2")
        self.assertTrue(self.ws.path(meta["file"]).is_file())
        self.assertEqual(notes[0].name, Path(meta["file"]).name + ".note.md")
        self.assertIn("I would file it in the MSA matter", body)
        j = common.split_pipe(self.ws.journal_lines()[-1])
        self.assertEqual(j[2], "please-check")
        self.assertEqual(j[6], "0.4")

    def test_refile_from_please_check_resolves_the_note(self):
        f = make_email(self.inbox("q.eml"), sender=JULIA, subject="Quick question")
        self.place(f, "--to", "please-check", "--note", "unsure")
        moved = [p for p in self.ws.path("inbox/please-check").glob("*.eml")][0]
        self.place(moved, "--to", self.mrel, "--reason", "lawyer: the MSA", "--run", "R3")
        self.assertEqual(list(self.ws.path("inbox/please-check").glob("*.note.md")), [])
        resolved = list(self.ws.path("inbox/please-check/resolved").glob("*.note.md"))
        self.assertEqual(len(resolved), 1)
        text = resolved[0].read_text(encoding="utf-8")
        self.assertIn("## Resolution", text)
        self.assertIn("lawyer: the MSA", text)
        self.assertIn(self.mrel + "/correspondence/", text)

    def test_please_check_needs_a_note_and_refuses_double(self):
        f = make_email(self.inbox("q.eml"))
        self.assertEqual(self.place(f, "--to", "please-check", ok=False).returncode, 2)
        self.place(f, "--to", "please-check", "--note", "unsure")
        moved = list(self.ws.path("inbox/please-check").glob("*.eml"))[0]
        self.assertEqual(self.place(moved, "--to", "please-check", "--note", "x", ok=False).returncode, 2)

    def test_loose_file_goes_to_please_check_then_into_a_matter(self):
        pdf = self.inbox("Signed NDA.pdf")
        pdf.write_bytes(b"%PDF-1.4 signed")
        self.assertEqual(self.place(pdf, "--to", self.mrel, ok=False).returncode, 2)
        self.assertEqual(self.place(pdf, "--to", "noise", ok=False).returncode, 2)
        self.place(pdf, "--to", "please-check", "--note", "A PDF on its own.", "--candidates", self.ref)
        moved = self.ws.path("inbox/please-check/Signed NDA.pdf")
        self.assertEqual(moved.read_bytes(), b"%PDF-1.4 signed")
        self.assertTrue(self.ws.path("inbox/please-check/Signed NDA.pdf.note.md").is_file())
        self.place(moved, "--to", self.mrel)
        stored = self.matter / "documents" / "received" / "Signed NDA.pdf"
        self.assertEqual(stored.read_bytes(), b"%PDF-1.4 signed")
        row = self.docs()[-1]
        self.assertEqual((row["name"], row["folder"], row["hash"]), ("Signed NDA.pdf", "documents/received", sha(stored)))
        self.assertTrue(self.ws.path("inbox/please-check/resolved/Signed NDA.pdf.note.md").is_file())


class RegisterAndRefusalTest(PlaceBase):

    def test_register_email_put_in_by_hand(self):
        corr = self.matter / "correspondence"
        f = make_email(corr / "forwarded by hand.eml", sender=JULIA, subject="Acme MSA v2",
                       attachments=[("Acme_MSA_v2.docx", b"PK v2", DOCX)], message_id="<hand.1@acme-automotive.de>")
        res = self.ws.run("place-email", "--register", f.relative_to(self.ws.root).as_posix(), "--run", "R4")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(f.is_file())
        rows = self.docs()
        self.assertEqual([(r["name"], r["folder"], r["read"]) for r in rows], [
            ("forwarded by hand.eml", "correspondence", "pending"),
            ("Acme_MSA_v2.docx", "documents/received", "pending")])
        self.assertEqual(rows[0]["message_id"], "hand.1@acme-automotive.de")
        self.assertEqual((self.matter / "documents" / "received" / "Acme_MSA_v2.docx").read_bytes(), b"PK v2")
        again = self.ws.run("place-email", "--register", str(f))
        self.assertEqual(again.returncode, 0)
        self.assertIn("already registered", again.stdout)
        self.assertEqual(len(self.docs()), 2)
        self.assertEqual(common.split_pipe(self.ws.journal_lines()[-1])[2], "filed")

    def test_register_work_product_and_reference(self):
        wp = self.matter / "work-product" / "2026-10-23_harvey-memo_liability-cap_v1.md"
        wp.write_text("memo", encoding="utf-8")
        ref = self.matter / "documents" / "reference" / "liability-caps.md"
        ref.write_text("position", encoding="utf-8")
        for p in (wp, ref):
            self.assertEqual(self.ws.run("place-email", "--register", str(p)).returncode, 0)
        rows = self.docs()
        self.assertEqual([(r["folder"], r["origin"]) for r in rows],
                         [("work-product", "work-product"), ("documents/reference", "reference")])
        self.assertEqual(rows[0]["hash"], sha(wp))

    def test_register_refusals(self):
        self.assertEqual(self.ws.run("place-email", "--register", "inbox/none.eml").returncode, 2)
        loose = self.ws.path("inbox/loose.pdf")
        loose.write_bytes(b"%PDF")
        self.assertEqual(self.ws.run("place-email", "--register", str(loose)).returncode, 2)
        self.assertEqual(self.ws.run("place-email", "--register", str(self.matter / "matter.md")).returncode, 2)

    def test_refuses_file_outside_inbox(self):
        f = make_email(self.matter / "documents" / "received" / "x.eml")
        before = sha(f)
        res = self.place(f, "--to", self.mrel, ok=False)
        self.assertEqual(res.returncode, 2)
        self.assertIn("not in inbox/", res.stderr)
        self.assertEqual(sha(f), before)

    def test_refuses_folder_without_matter_md(self):
        f = make_email(self.inbox("a.eml"))
        (self.ws.root / "areas" / "commercial" / "customers" / "acme-automotive" / "not-a-matter").mkdir()
        res = self.place(f, "--to", "areas/commercial/customers/acme-automotive/not-a-matter", ok=False)
        self.assertEqual(res.returncode, 2)
        self.assertTrue(f.exists())
        self.assertEqual(self.place(f, "--to", "2026-0999", ok=False).returncode, 2)

    def test_refuses_msg_bad_confidence_and_missing_args(self):
        msg = self.inbox("x.msg")
        msg.write_bytes(b"x")
        res = self.place(msg, "--to", self.mrel, ok=False)
        self.assertEqual(res.returncode, 2)
        self.assertIn("convert first", res.stderr)
        f = make_email(self.inbox("a.eml"))
        self.assertEqual(self.place(f, "--to", self.mrel, "--confidence", "2", ok=False).returncode, 2)
        self.assertEqual(self.place(f, "--to", "please-check", "--note", "x", "--candidates", "nope", ok=False).returncode, 2)
        self.assertEqual(self.ws.run("place-email", f).returncode, 2)
        self.assertEqual(self.ws.run("place-email").returncode, 2)
        self.assertTrue(f.exists())
        self.assertFalse(self.ws.path("inbox/noise/NOISE.csv").exists())

    def test_journal_created_with_header(self):
        self.ws.path("JOURNAL.md").unlink()
        f = make_email(self.inbox("a.eml"))
        self.place(f, "--to", "noise")
        lines = self.ws.path("JOURNAL.md").read_text(encoding="utf-8").split("\n")
        self.assertEqual(lines[0], "# time | run | action | item | destination | reason | confidence")
        self.assertEqual(common.split_pipe(lines[1])[2], "noise")


if __name__ == "__main__":
    unittest.main()
