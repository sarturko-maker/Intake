"""Tests for tools/unpack-email (and tools/lib/emailtools.py). Also holds make_email(), the email
builder shared with test_place.

Run: python3 -m unittest discover -s tools/tests -p 'test_*.py'
"""

import datetime as dt
import hashlib
import json
import os
import sys
import unittest
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_new_matter import HAVE_LONDON, WorkspaceTest  # noqa: E402

import common  # noqa: E402
import emailtools  # noqa: E402

TOM = ("Tom Hale", "tom.hale@kestrel-eng.co.uk")
LEGAL = ("Kestrel Legal", "legal@kestrel-eng.co.uk")
ALEX = ("Alex Morgan", "alex.morgan@kestrel-eng.co.uk")
JULIA = ("Julia Schmidt", "j.schmidt@acme-automotive.de")
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PNG_SMALL = b"\x89PNG\r\n\x1a\n" + b"\x00" * 3000


def make_email(path, sender=TOM, to=(LEGAL,), cc=(), subject="Acme NDA for review",
               date="Mon, 12 Oct 2026 09:12:00 +0100", message_id="<t-1.202610120912@kestrel-eng.co.uk>",
               in_reply_to=None, references=None, body="Hello,\n\nplease review the attached NDA.\n\nTom",
               html=None, attachments=(), inline_images=(), headers=None, attached_emails=()):
    """Write an .eml built with email.message.EmailMessage. Returns the path.

    attachments: (name, bytes, mime); inline_images: (name, bytes, content_id) added inline;
    attached_emails: EmailMessage objects attached as message/rfc822.
    """
    m = EmailMessage()
    m["From"] = formataddr(sender)
    if to:
        m["To"] = ", ".join(formataddr(t) for t in to)
    if cc:
        m["Cc"] = ", ".join(formataddr(c) for c in cc)
    m["Subject"] = subject
    if date:
        m["Date"] = date
    if message_id:
        m["Message-ID"] = message_id
    if in_reply_to:
        m["In-Reply-To"] = in_reply_to
    if references:
        m["References"] = references
    for k, v in (headers or {}).items():
        m[k] = v
    if body is not None:
        m.set_content(body)
        if html is not None:
            m.add_alternative(html, subtype="html")
    elif html is not None:
        m.set_content(html, subtype="html")
    for name, data, cid in inline_images:
        m.add_attachment(data, maintype="image", subtype="png", filename=name, disposition="inline",
                         cid="<%s>" % cid)
    for name, data, mime in attachments:
        main, sub = mime.split("/", 1)
        m.add_attachment(data, maintype=main, subtype=sub, filename=name)
    for inner in attached_emails:
        m.add_attachment(inner)
    path = Path(path)
    path.write_bytes(bytes(m))
    return path


class UnpackBase(WorkspaceTest):

    def unpack(self, *files, extra=()):
        res = self.ws.run("unpack-email", "--json", *list(extra) + [str(f) for f in files])
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def one(self, path, extra=()):
        return self.unpack(path, extra=extra)[0]

    def inbox(self, name):
        return self.ws.path("inbox/" + name)


class FieldsTest(UnpackBase):

    @unittest.skipUnless(HAVE_LONDON, "Europe/London time zone data not available")
    def test_fields_and_canonical_name_in_house_time(self):
        f = make_email(self.inbox("Acme MSA.eml"), sender=JULIA, to=(TOM,), cc=(LEGAL, ("Brandt, Felix", "f.brandt@acme-automotive.de")),
                       subject="Acme Master Supply Agreement - draft for review",
                       date="Thu, 15 Oct 2026 08:47:00 +0200",
                       message_id="<b1-04.202610150847@acme-automotive.de>")
        d = self.one(f)
        self.assertEqual(d["file"], "inbox/Acme MSA.eml")
        self.assertEqual(d["date"], "2026-10-15 07:47")
        self.assertEqual(d["canonical_name"], "2026-10-15_0747_in_jschmidt_acme-master-supply-agreement-draft-for.eml")
        self.assertEqual(d["direction"], "in")
        self.assertFalse(d["internal"])
        self.assertFalse(d["personal_address"])
        self.assertEqual(d["from"], {"name": "Julia Schmidt", "address": "j.schmidt@acme-automotive.de"})
        self.assertEqual(d["to"], [{"name": "Tom Hale", "address": "tom.hale@kestrel-eng.co.uk"}])
        self.assertEqual([c["address"] for c in d["cc"]], ["legal@kestrel-eng.co.uk", "f.brandt@acme-automotive.de"])
        self.assertEqual(d["cc"][1]["name"], "Brandt, Felix")
        self.assertEqual(d["message_id"], "b1-04.202610150847@acme-automotive.de")
        self.assertEqual(d["in_reply_to"], "")
        self.assertEqual(d["references"], [])
        self.assertEqual(d["sha256"], hashlib.sha256(f.read_bytes()).hexdigest())
        self.assertEqual(d["notes"], [])

    @unittest.skipUnless(HAVE_LONDON, "Europe/London time zone data not available")
    def test_house_time_across_the_clock_change(self):
        before = make_email(self.inbox("a.eml"), date="Wed, 14 Oct 2026 11:05:00 +0200", subject="Signed NDA")
        after = make_email(self.inbox("b.eml"), date="Tue, 27 Oct 2026 10:30:00 +0100", subject="RE: Acme MSA")
        utc = make_email(self.inbox("c.eml"), date="Mon, 26 Oct 2026 07:45:00 -0000", subject="x")
        d = self.unpack(before, after, utc)
        self.assertEqual([x["date"] for x in d], ["2026-10-14 10:05", "2026-10-27 09:30", "2026-10-26 07:45"])
        self.assertTrue(d[1]["canonical_name"].startswith("2026-10-27_0930_in_tomhale_re-acme-msa"))

    def test_out_direction_for_legal_addresses_and_intake_mailbox(self):
        a = make_email(self.inbox("a.eml"), sender=ALEX, to=(TOM,), subject="RE: Acme NDA")
        b = make_email(self.inbox("b.eml"), sender=LEGAL, to=(TOM,), subject="RE: Acme NDA")
        c = make_email(self.inbox("c.eml"), sender=TOM, subject="Acme NDA")
        d = self.unpack(a, b, c)
        self.assertEqual([x["direction"] for x in d], ["out", "out", "in"])
        self.assertTrue(all(x["internal"] for x in d))
        self.assertIn("_out_alexmorgan_", d[0]["canonical_name"])
        self.assertIn("_out_kestrel-eng_", d[1]["canonical_name"])

    def test_personal_address(self):
        f = make_email(self.inbox("a.eml"), sender=("Tom Hale", "tomhale.home@gmail.com"), subject="RE: Acme MSA")
        d = self.one(f)
        self.assertTrue(d["personal_address"])
        self.assertFalse(d["internal"])

    def test_missing_date_uses_file_time_with_note(self):
        f = make_email(self.inbox("nodate.eml"), date=None, subject="No date")
        when = dt.datetime(2026, 10, 20, 14, 30, tzinfo=dt.timezone.utc).timestamp()
        os.utime(str(f), (when, when))
        d = self.one(f)
        self.assertIn("date from file time", d["notes"])
        if HAVE_LONDON:
            self.assertEqual(d["date"], "2026-10-20 15:30")

    def test_unparseable_date_uses_file_time(self):
        f = make_email(self.inbox("baddate.eml"), date="sometime last week", subject="Bad date")
        self.assertIn("date from file time", self.one(f)["notes"])

    def test_missing_message_id_is_empty(self):
        f = make_email(self.inbox("a.eml"), message_id=None)
        self.assertEqual(self.one(f)["message_id"], "")

    def test_rfc2047_headers_rfc2231_filename_and_bad_charset(self):
        raw = (b"From: =?utf-8?q?J=C3=B6rg_Br=C3=BCckner?= <j.brueckner@kestrel-eng.de>\r\n"
               b"To: legal@kestrel-eng.co.uk\r\n"
               b"Subject: =?iso-8859-1?q?Vollmacht_f=FCr_Gesch=E4ftsf=FChrer?=\r\n"
               b"Date: Wed, 28 Oct 2026 09:10:00 +0100\r\n"
               b"Message-ID: <rfc.202610280910@kestrel-eng.de>\r\n"
               b"MIME-Version: 1.0\r\n"
               b"Content-Type: multipart/mixed; boundary=\"XX\"\r\n\r\n"
               b"--XX\r\nContent-Type: text/plain; charset=\"x-no-such-charset\"\r\n"
               b"Content-Transfer-Encoding: 8bit\r\n\r\nWer darf unterschreiben? \xe4\xff\r\n"
               b"--XX\r\nContent-Type: application/pdf\r\n"
               b"Content-Disposition: attachment; filename*=utf-8''Liste%20Gesch%C3%A4ftsf%C3%BChrer.pdf\r\n"
               b"Content-Transfer-Encoding: base64\r\n\r\nJVBERi0xLjQK\r\n--XX--\r\n")
        f = self.inbox("raw.eml")
        f.write_bytes(raw)
        d = self.one(f)
        self.assertEqual(d["from"]["name"], "Jörg Brückner")
        self.assertEqual(d["subject"], "Vollmacht für Geschäftsführer")
        self.assertIn("vollmacht-fuer-geschaeftsfuehrer", d["canonical_name"])
        self.assertTrue(d["body"].startswith("Wer darf unterschreiben?"))
        self.assertEqual(d["attachments"][0]["name"], "Liste Geschäftsführer.pdf")
        self.assertEqual(d["attachments"][0]["sha256"], hashlib.sha256(b"%PDF-1.4\n").hexdigest())

    def test_html_only_body(self):
        html = ("<html><head><style>p {color: red}</style></head><body><p>Dear Legal,</p>"
                "<p>please check the <b>tender</b> terms &amp; conditions.<br>Thanks</p>"
                "<blockquote><p>older message text</p></blockquote></body></html>")
        f = make_email(self.inbox("h.eml"), body=None, html=html)
        d = self.one(f)
        self.assertEqual(d["body"], "Dear Legal,\n\nplease check the tender terms & conditions.\nThanks")
        self.assertNotIn("color", d["body"])
        self.assertGreater(d["quoted_chars"], 0)

    def test_body_limit(self):
        f = make_email(self.inbox("long.eml"), body="word " * 100)
        d = self.one(f, extra=("--body-chars", "50"))
        self.assertEqual(d["body_chars_total"], 499)
        self.assertTrue(d["body"].endswith("[... 449 more characters]"))

    def test_markdown_output_and_no_signals(self):
        f = make_email(self.inbox("a.eml"), subject="Acme NDA [2026-0001]")
        res = self.ws.run("unpack-email", f)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("## inbox/a.eml", res.stdout)
        self.assertIn("- tags: 2026-0001", res.stdout)
        self.assertIn("### Body", res.stdout)
        self.assertNotIn("signals", self.one(f, extra=("--no-signals",)))

    def test_msg_missing_and_other_files_exit_2(self):
        msg = self.inbox("x.msg")
        msg.write_bytes(b"not really")
        res = self.ws.run("unpack-email", msg)
        self.assertEqual(res.returncode, 2)
        self.assertIn("convert first: bash tools/msg2eml", res.stderr)
        self.assertEqual(self.ws.run("unpack-email", "inbox/missing.eml").returncode, 2)
        pdf = self.inbox("x.pdf")
        pdf.write_bytes(b"%PDF")
        self.assertEqual(self.ws.run("unpack-email", pdf).returncode, 2)
        self.assertEqual(self.ws.run("unpack-email").returncode, 2)
        self.assertEqual(self.ws.run("unpack-email", "--body-chars", "x", "a.eml").returncode, 2)


class TagsTest(UnpackBase):

    def test_tag_in_subject_removed_from_canonical_name(self):
        d = self.one(make_email(self.inbox("a.eml"), subject="RE: Acme MSA [2026-0042]"))
        self.assertEqual(d["tags"], ["2026-0042"])
        self.assertTrue(d["canonical_name"].endswith("_re-acme-msa.eml"))

    def test_tag_in_new_body_and_prefix(self):
        d = self.one(make_email(self.inbox("a.eml"), subject="Question",
                                body="About [LM-2026-0007] and [2026-0042].\n\nTom"))
        self.assertEqual(d["tags"], ["LM-2026-0007", "2026-0042"])

    def test_tag_only_in_quoted_history_is_found_by_fallback(self):
        body = "Thanks, see below.\n\nOn Mon, 12 Oct 2026 at 09:12, Alex Morgan <alex.morgan@kestrel-eng.co.uk> wrote:\n> RE: Acme MSA [2026-0042]\n"
        d = self.one(make_email(self.inbox("a.eml"), subject="RE: Acme MSA", body=body))
        self.assertEqual(d["tags"], ["2026-0042"])
        self.assertEqual(d["body"], "Thanks, see below.")

    def test_subject_tag_wins_over_history(self):
        body = "New text.\n\n> old [2026-0001]\n"
        d = self.one(make_email(self.inbox("a.eml"), subject="RE: x [2026-0002]", body=body))
        self.assertEqual(d["tags"], ["2026-0002"])

    def test_tags_are_case_sensitive_and_exact(self):
        d = self.one(make_email(self.inbox("a.eml"), subject="re [lm-2026-0001] [2026-001] (2026-0042)"))
        self.assertEqual(d["tags"], [])


class QuotedHistoryTest(UnpackBase):

    def body_of(self, text):
        return self.one(make_email(self.inbox("q.eml"), body=text))["body"]

    def test_english_on_wrote(self):
        self.assertEqual(self.body_of("Agreed.\n\nOn Mon, 12 Oct 2026, Tom Hale <tom.hale@kestrel-eng.co.uk> wrote:\nold text\n"),
                         "Agreed.")

    def test_english_on_wrote_wrapped_over_two_lines(self):
        self.assertEqual(self.body_of("Agreed.\n\nOn Mon, 12 Oct 2026 at 09:12, Tom Hale\n<tom.hale@kestrel-eng.co.uk> wrote:\nold\n"),
                         "Agreed.")

    def test_original_message_and_from_sent_block(self):
        self.assertEqual(self.body_of("Fine.\n-----Original Message-----\nFrom: x\nold"), "Fine.")
        text = "See below.\n\n________________________________\nFrom: Tom Hale <tom.hale@kestrel-eng.co.uk>\nSent: 12 October 2026 09:12\nTo: Legal\nSubject: x\n\nold"
        self.assertEqual(self.body_of(text), "See below.")
        far_apart = "Notes\nFrom: the buyer's side\nwe heard nothing\n\n\n\n\nDate: later"
        self.assertEqual(self.body_of(far_apart), far_apart)

    def test_quoted_lines_dropped(self):
        self.assertEqual(self.body_of("Yes.\n> old line\n>> older\nAnd one more thing."),
                         "Yes.\nAnd one more thing.")

    def test_german_markers(self):
        self.assertEqual(self.body_of("Danke.\n\nAm 12.10.2026 um 09:12 schrieb Tom Hale <tom.hale@kestrel-eng.co.uk>:\nalt\n"),
                         "Danke.")
        self.assertEqual(self.body_of("Siehe unten.\n-----Ursprüngliche Nachricht-----\nVon: x\nalt"), "Siehe unten.")
        self.assertEqual(self.body_of("Bitte prüfen.\n\nVon: Northgate Accounts <accounts@northgate-logistics.com>\nGesendet: Donnerstag, 15. Oktober 2026 10:00\nAn: Lena Vogt\nBetreff: Invoice 4471\n\nalt"),
                         "Bitte prüfen.")


class NoiseHintsTest(UnpackBase):

    def hints(self, **kw):
        kw.setdefault("body", "A normal message with enough words in it to count.")
        return self.one(make_email(self.inbox("n.eml"), **kw))["noise_hints"]

    def test_auto_reply(self):
        self.assertIn("auto-reply", self.hints(headers={"Auto-Submitted": "auto-replied"}))
        self.assertIn("auto-reply", self.hints(subject="Out of office: Jonas Keller until 2 November"))
        self.assertIn("auto-reply", self.hints(subject="Automatische Antwort: Urlaub"))
        self.assertIn("auto-reply", self.hints(subject="Abwesenheitsnotiz"))
        self.assertIn("auto-reply", self.hints(subject="Automatic reply: away"))
        self.assertIn("auto-reply", self.hints(headers={"X-Autoreply": "yes"}))
        self.assertIn("auto-reply", self.hints(headers={"X-Autorespond": "yes"}))
        self.assertNotIn("auto-reply", self.hints(headers={"Auto-Submitted": "no"}))

    def test_bulk(self):
        self.assertIn("bulk", self.hints(headers={"List-Unsubscribe": "<mailto:u@brightlaw.co.uk>"}))
        self.assertIn("bulk", self.hints(headers={"Precedence": "bulk"}))
        self.assertIn("bulk", self.hints(headers={"List-Id": "<news.brightlaw.co.uk>"}))
        self.assertNotIn("bulk", self.hints(headers={"Precedence": "first-class"}))

    def test_calendar(self):
        ics = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
        self.assertIn("calendar", self.hints(attachments=[("invite.ics", ics, "text/calendar")]))
        self.assertIn("calendar", self.hints(attachments=[("invite.ics", ics, "application/octet-stream")]))
        self.assertEqual(self.hints(), [])

    def test_empty_body(self):
        self.assertEqual(self.hints(body="ok"), ["empty-body"])
        self.assertEqual(self.hints(body="", attachments=[("NDA.docx", b"PK..", DOCX)]), [])

    def test_logo_only(self):
        hints = self.hints(body="", subject="", inline_images=[("logo.png", PNG_SMALL, "logo@printhaus")])
        self.assertIn("logo-only", hints)
        self.assertIn("empty-body", hints)
        self.assertNotIn("logo-only", self.hints(inline_images=[("logo.png", PNG_SMALL, "l@x")],
                                                 attachments=[("NDA.docx", b"PK..", DOCX)]))


class AttachmentsTest(UnpackBase):

    def test_kinds_names_and_hashes(self):
        big = b"\x89PNG" + b"\x01" * (150 * 1024)
        inner = EmailMessage()
        inner["From"] = "accounts@northgate-logistics.com"
        inner["Subject"] = "Invoice 4471 short payment"
        inner.set_content("Please pay.")
        f = make_email(self.inbox("a.eml"),
                       attachments=[("Acme_NDA.docx", b"PK\x03\x04docx", DOCX), ("", b"raw bytes", "application/pdf"),
                                    ("photo.png", big, "image/png")],
                       inline_images=[("image001.png", PNG_SMALL, "image001.png@01DB")],
                       attached_emails=[inner])
        d = self.one(f)
        got = [(a["name"], a["kind"], a["inline"]) for a in d["attachments"]]
        self.assertEqual(got, [("image001.png", "signature-image", True), ("Acme_NDA.docx", "document", False),
                               ("attachment-3.pdf", "document", False), ("photo.png", "image", False),
                               ("invoice-4471-short-payment.eml", "email", False)])
        self.assertEqual(d["attachments"][1]["sha256"], hashlib.sha256(b"PK\x03\x04docx").hexdigest())
        self.assertEqual(d["attachments"][1]["size"], 8)
        self.assertEqual(d["attachments"][3]["sha256"], hashlib.sha256(big).hexdigest())
        self.assertEqual(d["attachments"][1]["content_type"], DOCX)

    def test_extract_writes_stored_kinds_with_matching_hashes(self):
        f = make_email(self.inbox("a.eml"), attachments=[("NDA.docx", b"PK-nda", DOCX)],
                       inline_images=[("image001.png", PNG_SMALL, "i1@x")])
        out = self.ws.path("tmp-extract")
        d = self.one(f, extra=("--extract", str(out)))
        stem = d["canonical_name"][:-4]
        self.assertEqual(sorted(p.name for p in (out / stem).iterdir()), ["NDA.docx"])
        self.assertEqual(hashlib.sha256((out / stem / "NDA.docx").read_bytes()).hexdigest(),
                         d["attachments"][1]["sha256"])
        self.assertEqual(d["attachments"][1]["extracted"], "tmp-extract/%s/NDA.docx" % stem)
        self.assertNotIn("extracted", d["attachments"][0])

    def test_unsafe_attachment_names_are_made_safe(self):
        f = make_email(self.inbox("a.eml"), attachments=[("..\\..\\evil:name?.pdf", b"x", "application/pdf")])
        self.assertEqual(self.one(f)["attachments"][0]["name"], "evil_name_.pdf")


class SignalsTest(UnpackBase):

    def setUp(self):
        super().setUp()
        self.ref, self.matter = self.ws.new_matter("commercial", "acme-automotive", "msa-liability-cap",
                                                   sub_area="customers")
        self.ws.add_roster(self.matter, "R01 | Julia Schmidt | Acme Automotive GmbH | counterparty | buyer | "
                                        "j.schmidt@acme-automotive.de | inferred | correspondence/x.eml")
        self.ws.add_roster(self.matter, "R02 | Tom Hale | Kestrel Engineering Ltd | ours | requester | "
                                        "tom.hale@kestrel-eng.co.uk | inferred | correspondence/x.eml")
        self.ws.add_roster(self.matter, "C01 | Dr Felix Brandt | Acme Automotive GmbH | counterparty | legal | "
                                        "F.Brandt@acme-automotive.de; felix.brandt@acme-automotive.de | confirmed | you",
                           confirmed=True)

    def check(self, sender, name="s.eml"):
        f = make_email(self.inbox(name), sender=sender, subject="RE: Acme MSA [%s]" % self.ref)
        tm = self.one(f)["signals"]["tag_matches"]
        self.assertEqual(len(tm), 1)
        self.assertTrue(tm[0]["found"])
        self.assertEqual(tm[0]["folder"], self.matter.relative_to(self.ws.root).as_posix())
        self.assertEqual(tm[0]["status"], "open")
        return tm[0]["sender_check"]

    def test_sender_checks(self):
        self.assertEqual(self.check(TOM), "internal")
        self.assertEqual(self.check(JULIA), "roster-address")
        self.assertEqual(self.check(("Felix", "f.brandt@acme-automotive.de")), "roster-address")
        self.assertEqual(self.check(("Julia Schmidt", "julia.s@gmail.com")), "roster-name-freemail")
        self.assertEqual(self.check(("schmidt, julia", "julia.schmidt@web.de")), "roster-name-freemail")
        self.assertEqual(self.check(("Dr Felix Brandt", "f.brandt@acme-automotlve.de")), "roster-name-other-domain")
        self.assertEqual(self.check(("Felix Brandt", "f.brandt@acme-automotlve.de")), "roster-name-other-domain")
        self.assertEqual(self.check(("Carlos Mendes", "carlos.mendes@riobombas.com.br")), "not-on-roster")

    def test_unknown_reference(self):
        f = make_email(self.inbox("a.eml"), sender=JULIA, subject="RE: x [2026-0999]")
        tm = self.one(f)["signals"]["tag_matches"]
        self.assertEqual(tm, [{"tag": "2026-0999", "found": False, "folder": "", "status": "",
                               "sender_check": "not-on-roster"}])

    def test_thread_matches_by_in_reply_to_and_references(self):
        self.ws.add_document_row(self.matter, "2026-10-16_1040_out_alexmorgan_x.eml", "b1-12.202610161040@kestrel-eng.co.uk")
        self.ws.set_status(self.matter, "waiting_counterparty")
        a = make_email(self.inbox("a.eml"), sender=JULIA, in_reply_to="<b1-12.202610161040@kestrel-eng.co.uk>")
        b = make_email(self.inbox("b.eml"), sender=JULIA, references="<other@x> <b1-12.202610161040@kestrel-eng.co.uk>")
        c = make_email(self.inbox("c.eml"), sender=JULIA, in_reply_to="<priya-clarification.202610190955@kestrel-eng.co.uk>")
        da, db, dc = self.unpack(a, b, c)
        for d in (da, db):
            tm = d["signals"]["thread_matches"]
            self.assertEqual(len(tm), 1)
            self.assertEqual(tm[0]["reference"], self.ref)
            self.assertEqual(tm[0]["status"], "waiting_counterparty")
            self.assertEqual(tm[0]["matched_ids"], ["b1-12.202610161040@kestrel-eng.co.uk"])
        self.assertEqual(dc["signals"]["thread_matches"], [])
        self.assertEqual(da["in_reply_to"], "b1-12.202610161040@kestrel-eng.co.uk")
        self.assertEqual(db["references"], ["other@x", "b1-12.202610161040@kestrel-eng.co.uk"])

    def test_already_filed_by_message_id(self):
        self.ws.add_document_row(self.matter, "x.eml", "dup.1@acme-automotive.de")
        d = self.one(make_email(self.inbox("a.eml"), message_id="<dup.1@acme-automotive.de>"))
        self.assertEqual([x["reference"] for x in d["signals"]["already_filed"]], [self.ref])


class EmailToolsUnitTest(unittest.TestCase):

    def test_strip_quoted_returns_counts(self):
        new, quoted = emailtools.strip_quoted("New\n> old\nmore\n\nOn Mon, X wrote:\nhistory here")
        self.assertEqual(new, "New\nmore")
        self.assertGreater(quoted, 10)

    def test_norm_name(self):
        self.assertEqual(emailtools.norm_name("Dr. Felix  Brandt"), "felix brandt")
        self.assertEqual(emailtools.norm_name("Schmidt, Julia"), "julia schmidt")
        self.assertEqual(emailtools.norm_name('"Tom Hale"'), "tom hale")

    def test_decode_text_fallbacks(self):
        self.assertEqual(emailtools.decode_text("Grüße".encode("utf-8"), "us-ascii"), "Grüße")
        self.assertEqual(emailtools.decode_text(b"Gr\xfc\xdfe", "utf-8"), "Grüße")
        self.assertEqual(emailtools.decode_text(b"abc", "x-unknown-thing"), "abc")
        self.assertIn("�", emailtools.decode_text(b"\xff\xfe\xfa", "iso-2022-jp"))

    def test_canonical_name_slugs(self):
        when = dt.datetime(2026, 10, 30, 6, 0)
        self.assertEqual(emailtools.canonical_name(when, "in", "noreply@printhaus.de", ""),
                         "2026-10-30_0600_in_printhaus_none.eml")
        self.assertEqual(common.from_slug("j.schmidt@acme-automotive.de"), "jschmidt")


if __name__ == "__main__":
    unittest.main()
