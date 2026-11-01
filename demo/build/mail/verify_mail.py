#!/usr/bin/env python3
"""Checks for the demo mail corpus and the demo scripts. Dev tool.

    python3 demo/build/mail/verify_mail.py corpus     parse every email (one line each), check
                                                      expected.csv, attachments, fixtures and
                                                      the standard answers
    python3 demo/build/mail/verify_mail.py scripts [--tmp DIR]
                                                      setup -> fake G02 matter -> drop-batch 2
                                                      -> hand-placed emails -> check-filing, in a
                                                      temporary folder that is deleted afterwards
    python3 demo/build/mail/verify_mail.py            both

Exit 0 when every check passes, 1 otherwise. Uses pandoc and pdftotext when present.
"""

import argparse
import csv
import hashlib
import io
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

PROBLEMS = []

# In-Reply-To and References of every email (spec G table), as email ids.
THREADS = {
    "b1-02": (["b1-01"], ["b1-01"]),
    "b1-05": ([], ["b1-04"]),
    "b1-07": (["b1-06"], ["b1-06"]),
    "b1-12": (["b1-04"], ["b1-04"]),
    "b2-01": (["b1-12"], ["b1-04", "b1-12"]),
    "b2-03": (["b1-07"], ["b1-06", "b1-07"]),
    "b2-07": (["priya-clarification"], ["priya-clarification"]),
    "b2-09": (["b1-08"], ["b1-08"]),
    "b3-02": (["b2-01"], ["b1-04", "b1-12", "b2-01"]),
    "b3-06": (["b3-05"], ["b3-05"]),
}
PLACEHOLDERS = {"b2-01": "G02", "b2-03": "G03", "b2-09": "G04", "b3-01": "G02", "b3-02": "G02",
                "b3-03": "G02"}
ACME_LOGO = ("b1-04", "b2-01", "b3-02")


def check(cond, msg):
    if not cond:
        PROBLEMS.append(msg)
    return cond


def squash(text):
    return re.sub(r"\s+", " ", text or "")


def have(cmd):
    return shutil.which(cmd) is not None

# ======================================================================= corpus


def load_emails():
    parser = BytesParser(policy=policy.default)
    out = {}
    for batch in (1, 2, 3):
        for p in sorted((ROOT / "demo" / "batches" / str(batch)).glob("*.eml")):
            data = p.read_bytes()
            msg = parser.parsebytes(data)
            mid = str(msg["Message-ID"]).strip("<>")
            out[mid.split(".", 1)[0]] = (p, data, msg)
    return out


def all_ids(raw):
    return re.findall(r"<([^<>]+)>", raw or "")


def corpus():
    emails = load_emails()
    check(len(emails) == 28, "expected 28 .eml files, found %d" % len(emails))
    by_mid = {}
    print("Emails (%d):" % len(emails))
    for eid in sorted(emails):
        p, data, msg = emails[eid]
        date = msg["Date"].datetime
        atts = []
        for part in msg.walk():
            fn = part.get_filename()
            if fn:
                atts.append(fn + (" (inline)" if part.get_content_disposition() == "inline" else ""))
        print("%s  %s  %-48s  %-62s  [%s]" % (
            eid, date.strftime("%a %d %b %H:%M %z"), str(msg["From"])[:48],
            '"%s"' % str(msg["Subject"] or "")[:60], ", ".join(atts)))
        # Message-ID rule: <id.YYYYMMDDHHMM local@sender domain>
        frm = msg["From"].addresses[0].addr_spec.lower()
        want = "%s.%s@%s" % (eid, date.strftime("%Y%m%d%H%M"), frm.split("@", 1)[1])
        check(str(msg["Message-ID"]) == "<%s>" % want, "%s Message-ID %s != <%s>" % (
            eid, msg["Message-ID"], want))
        by_mid[want] = eid
        for h in ("Date", "From", "To", "Message-ID", "MIME-Version"):
            check(msg[h] is not None, "%s lacks %s" % (eid, h))
        check("Subject" in msg, "%s lacks a Subject header" % eid)
        check(b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b""), "%s: not CRLF" % eid)
        # placeholders
        ph = re.findall(rb"\{\{REF:(G\d\d)\}\}", data)
        if eid in PLACEHOLDERS:
            check("[{{REF:%s}}]" % PLACEHOLDERS[eid] in str(msg["Subject"]),
                  "%s subject lacks [{{REF:%s}}]" % (eid, PLACEHOLDERS[eid]))
            check(data.isascii(), "%s carries a placeholder but is not ASCII" % eid)
            for part in msg.walk():
                if part.get_content_maintype() == "text":
                    check(part["Content-Transfer-Encoding"] in (None, "7bit"),
                          "%s: text part not 7bit" % eid)
        else:
            check(not ph, "%s has an unexpected placeholder" % eid)
        check(int(eid[1]) >= 2 or not ph, "%s: placeholder in batch 1" % eid)
    # threads
    for eid, (irt, refs) in THREADS.items():
        if eid not in emails:
            continue
        msg = emails[eid][2]
        got_irt = [x.split(".", 1)[0] for x in all_ids(str(msg.get("In-Reply-To", "")))]
        got_refs = [x.split(".", 1)[0] for x in all_ids(str(msg.get("References", "")))]
        check(got_irt == irt, "%s In-Reply-To %s != %s" % (eid, got_irt, irt))
        check(got_refs == refs, "%s References %s != %s" % (eid, got_refs, refs))
    for eid in emails:
        if eid not in THREADS:
            msg = emails[eid][2]
            check(msg.get("In-Reply-To") is None and msg.get("References") is None,
                  "%s should have no thread headers" % eid)
    check("priya-clarification.202610190955@kestrel-eng.co.uk"
          in str(emails["b2-07"][2]["In-Reply-To"]), "b2-07 In-Reply-To")
    # special emails
    m = emails["b1-10"][2]
    check(m["List-Unsubscribe"] is not None and str(m["Precedence"]) == "bulk", "b1-10 bulk headers")
    check(str(emails["b2-07"][2]["Auto-Submitted"]) == "auto-replied", "b2-07 Auto-Submitted")
    types = [part.get_content_type() for part in emails["b1-11"][2].walk()]
    names = [part.get_filename() for part in emails["b1-11"][2].walk()]
    check("text/calendar" in types and "invite.ics" in names, "b1-11 calendar parts")
    for eid in ACME_LOGO:
        logos = [part for part in emails[eid][2].walk() if part.get_filename() == "image001.png"]
        check(len(logos) == 1, "%s: one image001.png" % eid)
        if logos:
            lp = logos[0]
            check(lp["Content-ID"] is not None and lp.get_content_disposition() == "inline"
                  and len(lp.get_payload(decode=True)) < 10 * 1024, "%s logo inline, cid, <10KB" % eid)
    m = emails["b3-08"][2]
    plain = m.get_body(("plain",)).get_content().strip()
    others = [part for part in m.walk() if part.get_filename()]
    check(str(m["Subject"]) == "" and len(plain) < 20 and len(others) == 1
          and others[0].get_content_disposition() == "inline", "b3-08 logo only, empty subject")
    m = emails["b1-09"][2]
    body = m.get_body(("plain",)).get_content()
    check(str(m["Subject"]).startswith("WG: ") and "-----Ursprüngliche Nachricht-----" in body
          and "Von: Northgate Logistics Accounts" in body and "EUR 2,800.00" in body, "b1-09 forward")
    for eid, marker in (("b1-02", "wrote:"), ("b1-07", "wrote:"), ("b1-12", "wrote:"),
                        ("b2-03", "wrote:"), ("b2-09", "wrote:"), ("b3-06", "wrote:"),
                        ("b2-01", "schrieb"), ("b3-02", "schrieb")):
        body = emails[eid][2].get_body(("plain",)).get_content()
        check(marker in body, "%s lacks quote marker %r" % (eid, marker))
    check("Sent: 15 October 2026 07:47" in emails["b1-05"][2].get_body(("plain",)).get_content(),
          "b1-05 Outlook forward block")
    m = emails["b3-03"][2]
    check(str(m["From"]) == "Dr Felix Brandt <f.brandt@acme-automotlve.de>"
          and "IBAN" in m.get_body(("plain",)).get_content(), "b3-03 impersonation")
    check(emails["b3-01"][2]["From"].addresses[0].addr_spec == "tomhale.home@gmail.com"
          and emails["b3-01"][2]["From"].addresses[0].display_name == "Tom Hale", "b3-01 sender")

    def att(eid, name):
        for part in emails[eid][2].walk():
            if part.get_filename() == name:
                return part.get_payload(decode=True)
        return None
    msa_a, msa_b = att("b1-04", "Acme_MSA_v1.docx"), att("b1-05", "Acme_MSA_v1.docx")
    check(msa_a is not None and msa_a == msa_b, "b1-04 and b1-05 Acme_MSA_v1.docx differ")
    # HR content exists in b3-07 only
    hr_terms = ["Garside", "grievance", "return-to-work", "signed off sick"]
    for p in list((ROOT / "demo").rglob("*")):
        if not p.is_file() or "node_modules" in p.parts:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.endswith("Personal - advice please.eml") or rel.startswith("demo/build/mail/"):
            continue
        try:
            text = p.read_bytes().decode("utf-8", "ignore")
        except OSError:
            continue
        for t in hr_terms:
            check(t not in text, "HR term %r found outside b3-07: %s" % (t, rel))
    expected_csv(emails, by_mid)
    with tempfile.TemporaryDirectory() as td:
        out = extract_attachments(emails, Path(td))
        attachments(out)
        questionnaires(out)
    fixtures()


def expected_csv(emails, by_mid):
    path = ROOT / "demo" / "expected.csv"
    text = path.read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    header = text.split("\n", 1)[0]
    check(header == "id,batch,file,message_id,kind,group,area,sub_area,subject,proposed_outcome,"
                    "flags,tests", "expected.csv header: " + header)
    check(len(rows) == 29, "expected.csv has %d rows" % len(rows))
    ids = [r["message_id"] for r in rows]
    check(len(set(ids)) == 29, "expected.csv message_ids not unique")
    for r in rows:
        if r["id"] == "b3-05":
            msg_file = ROOT / "demo" / "batches" / "3" / r["file"]
            check(r["file"] == "Vollmacht PoA for Kestrel Pumpen GmbH - who can sign.msg",
                  "b3-05 file name")
            check(r["message_id"] == "b3-05.202610280910@kestrel-eng.de", "b3-05 message_id")
            check(msg_file.exists(), "b3-05 .msg missing (msg-writer builder)")
            continue
        check(r["message_id"] in by_mid and by_mid[r["message_id"]] == r["id"],
              "%s message_id %s matches no email" % (r["id"], r["message_id"]))
        p = ROOT / "demo" / "batches" / r["batch"] / r["file"]
        check(p.exists(), "%s file missing: %s" % (r["id"], p))
        check(r["kind"] in ("matter", "noise", "please-check", "please-check|matter"),
              "%s kind %s" % (r["id"], r["kind"]))
        check(r["tests"] != "", "%s has no tests text" % r["id"])
    print("expected.csv: %d rows, %d unique message ids, all match a generated email (b3-05: "
          "name and id)" % (len(rows), len(set(ids))))


def docx_xml(path, member):
    with zipfile.ZipFile(path) as z:
        return z.read(member).decode("utf-8") if member in z.namelist() else ""


def pandoc_plain(path):
    if not have("pandoc"):
        return None
    return subprocess.run(["pandoc", "--track-changes=all", "-t", "plain", str(path)],
                          capture_output=True, text=True, check=True).stdout


def extract_attachments(emails, dest):
    """Every named attachment, as carried by the committed emails (first copy of each name)."""
    for eid in sorted(emails):
        for part in emails[eid][2].walk():
            name = part.get_filename()
            if name and not (dest / name).exists():
                (dest / name).write_bytes(part.get_payload(decode=True))
    return dest


def attachments(out):
    markups = {
        "Acme_Mutual_NDA_v1_Kestrel.docx": (["three (3)", "England and Wales"],
                                            ["five (5)", "Federal Republic of Germany"],
                                            ["standard term for mutual NDAs", "English law"]),
        "Acme_MSA_v1_Kestrel_markup.docx": (["one hundred per cent (100%)", "two (2) times the "
                                             "Annual Fees", "Neither party is liable"],
                                            ["two hundred per cent (200%)", "is unlimited and does "
                                             "not count"],
                                            ["general cap is 100%", "cannot accept unlimited",
                                             "mutual exclusion"]),
    }
    for name, (ins, dels, comments) in markups.items():
        doc = docx_xml(out / name, "word/document.xml")
        com = docx_xml(out / name, "word/comments.xml")
        check(re.search(r'<w:ins [^>]*w:author="Alex Morgan" w:date="2026-10-1\dT', doc) is not None,
              name + ": no w:ins by Alex Morgan with a date")
        check(re.search(r'<w:del [^>]*w:author="Alex Morgan" w:date="2026-10-1\dT', doc) is not None,
              name + ": no w:del by Alex Morgan with a date")
        check(com.count("<w:comment ") >= 3 and 'w:author="Alex Morgan"' in com,
              name + ": fewer than 3 comments by Alex Morgan")
        plain = pandoc_plain(out / name)
        if plain is not None:
            flat = squash(plain)
            for s in ins + dels + comments:
                check(s in flat, "%s: pandoc --track-changes=all -t plain lacks %r" % (name, s))
            print("pandoc %s: %d insertions, %d deletions, %d comments shown" % (
                name, len(ins), len(dels), len(comments)))
    for v, must in (("v1", ["two hundred per cent (200%)", "is unlimited and does not count",
                            "Supplier is liable for indirect"]),
                    ("v2", ["one hundred and fifty per cent (150%)", "is unlimited and does not "
                            "count", "Costs of production stoppage"]),
                    ("v3", ["one hundred and fifty per cent (150%)", "gross negligence or wilful "
                            "misconduct. In all other cases it is subject to the limit in clause "
                            "12.2"])):
        plain = pandoc_plain(out / ("Acme_MSA_%s.docx" % v))
        if plain is not None:
            for s in must:
                check(s in squash(plain), "Acme_MSA_%s.docx lacks %r" % (v, s))
    plain = pandoc_plain(out / "Halden_Water_NDA.docx")
    if plain is not None:
        flat = squash(plain)
        check("9. Non-competition" in flat and "two (2) years" in flat and "within the Region" in flat
              and "five (5) years" in flat, "Halden NDA clause 9 / term")
    plain = pandoc_plain(out / "Meridian_Liability_Schedule.docx")
    if plain is not None:
        flat = squash(plain)
        check("three hundred per cent (300%)" in flat and "shall be unlimited" in flat,
              "Meridian schedule 3x / uncapped fines")
    plain = pandoc_plain(out / "RioBombas_Distribution_Agreement_Draft.docx")
    if plain is not None:
        flat = squash(plain)
        check("exclusive distributor" in flat and "EUR 400,000" in flat
              and "laws of the Federative Republic of Brazil" in flat, "Rio Bombas draft")
    pages = {"Acme_Kestrel_NDA_signed.pdf": None, "PX-400_datasheet.pdf": 2,
             "Volta_Rail_Tender_Terms.pdf": 40, "Northgate_Invoice_4471.pdf": 1,
             "FlowTech_Catalogue_2027.pdf": 4}
    for name, n in pages.items():
        data = (out / name).read_bytes()
        count = len(re.findall(rb"/Type /Page[^s]", data))
        if n:
            check(count == n, "%s has %d pages, expected %d" % (name, count, n))
    if have("pdftotext"):
        def page(name, n, layout=False):
            cmd = ["pdftotext", "-f", str(n), "-l", str(n)] + (["-layout"] if layout else [])
            return subprocess.run(cmd + [str(out / name), "-"],
                                  capture_output=True, text=True, check=True).stdout
        p2 = squash(page("Volta_Rail_Tender_Terms.pdf", 2, layout=True))
        p23, p31 = (squash(page("Volta_Rail_Tender_Terms.pdf", n)) for n in (23, 31))
        check("Contents" in p2 and "21 Liability 23" in p2
              and "29 Intellectual property and warranty 31" in p2, "Volta contents page")
        check("21. Liability" in p23 and "indirect and consequential loss" in p23
              and "twenty per cent (20%)" in p23, "Volta page 23")
        check("29. Intellectual property and warranty" in p31 and "Background IP" in p31
              and "thirty-six (36) months" in p31, "Volta page 31")
        ds = squash(page("PX-400_datasheet.pdf", 1))
        check("Grey cast iron" in ds and "Ductile iron" in ds and "16 bar" in ds and "+90" in ds
              and "No stainless steel, nickel alloy, titanium" in ds, "PX-400 datasheet facts")
        nda = squash(page("Acme_Kestrel_NDA_signed.pdf", 2))
        check("Name: Chris Barker" in nda and "Name: Katrin Albers" in nda and "England and Wales"
              in nda, "signed NDA signature blocks")
        print("pdftotext: Volta contents on p.2, Liability on p.23, IP and warranty on p.31; "
              "datasheet and signature blocks checked")


def fixtures():
    fx = ROOT / "tools" / "fixtures"
    kv = dict(line.split("=", 1) for line in (fx / "EXPECTED.txt").read_text().splitlines() if line)
    check(set(kv) == {"sample_eml_sha256", "sample_eml_message_id", "sample_eml_attachment",
                      "sample_msg_message_id", "sample_docx_marker"}, "EXPECTED.txt keys")
    data = (fx / "sample.eml").read_bytes()
    check(hashlib.sha256(data).hexdigest() == kv["sample_eml_sha256"], "sample.eml sha256")
    msg = BytesParser(policy=policy.default).parsebytes(data)
    check(str(msg["Message-ID"]) == "<%s>" % kv["sample_eml_message_id"], "sample.eml id")
    check(msg["From"].addresses[0].addr_spec == "tom.hale@kestrel-eng.co.uk"
          and str(msg["To"]) == "legal@kestrel-eng.co.uk", "sample.eml from/to")
    check([p.get_filename() for p in msg.iter_attachments()] == ["fixture.docx"],
          "sample.eml attachment")
    check(kv["sample_msg_message_id"] == "fixture.202610010900@kestrel-eng.de", "msg id")
    plain = pandoc_plain(fx / "sample.docx")
    if plain is not None:
        check("FIXTURE-INSERTED-TEXT" in plain, "sample.docx marker not shown by pandoc")
    doc = docx_xml(fx / "sample.docx", "word/document.xml")
    check(re.search(r"<w:ins [^>]*>.*?FIXTURE-INSERTED-TEXT", doc) is not None,
          "sample.docx: marker not inside w:ins")
    print("fixtures: EXPECTED.txt keys, sample.eml sha256/id/attachment, sample.docx tracked "
          "insertion checked")


def questionnaires(out):
    import make_mail
    make_mail.check_questionnaire_map()
    from docx import Document
    acme = Document(str(out / "Acme_Supplier_Security_Questionnaire.docx"))
    t = acme.tables[-1]
    check([c.text for c in t.rows[0].cells] == ["No.", "Question", "Answer", "Evidence"],
          "Acme questionnaire header")
    check(len(t.rows) == 41, "Acme questionnaire has %d data rows" % (len(t.rows) - 1))
    past = Document(str(ROOT / "demo/knowledge/standard-answers" / make_mail.STANDARD_ANSWERS_FILE))
    pt = past.tables[-1]
    check(len(pt.rows) == 41 and all(r.cells[2].text.strip() for r in pt.rows[1:]),
          "past questionnaire: 40 answered rows")
    acme_q = [r.cells[1].text for r in t.rows[1:]]
    past_q = [r.cells[1].text for r in pt.rows[1:]]
    check(acme_q == make_mail.ACME_QUESTIONS, "Acme docx questions differ from make_mail")
    check(past_q == [q for q, _, _ in make_mail.PAST_QUESTIONNAIRE], "past docx differs")
    meta = past.core_properties
    check(meta.modified.year == 2025 and meta.modified.month == 9, "past questionnaire date")
    covered = sum(1 for v in make_mail.QUESTIONNAIRE_MAP.values() if v)
    print("questionnaires: Acme 40 questions, past 40 answers (Sept 2025, owner IT Security); "
          "%d of 40 covered, not covered: Acme 39 (SOC 2 Type II), 40 (penetration test)" % covered)

# ======================================================================= scripts


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def scripts(tmp_root):
    tmp = Path(tempfile.mkdtemp(prefix="demo-scripts-", dir=tmp_root))
    try:
        ws = tmp / "ws"
        rc, out = run(["bash", str(ROOT / "demo/scripts/setup"), str(ws)])
        print("$ bash demo/scripts/setup %s -> exit %d" % (ws, rc))
        print("\n".join("  " + line for line in out.strip().splitlines()))
        check(rc == 0, "setup failed")
        check((ws / "demo/.demo-workspace").exists() and (ws / "RULES.md").exists()
              and (ws / "tools/unpack-email").exists() and not (ws / ".git").exists()
              and not list(ws.rglob("node_modules")), "setup copied the wrong files")
        for sub in ("knowledge/standard-answers", "knowledge/policies", "seeds", "inbox"):
            check((ws / sub / ".gitkeep").exists() or sub == "knowledge/standard-answers",
                  "setup lost %s/.gitkeep" % sub)
        check((ws / "knowledge/standard-answers" / "Kestrel_Security_Questionnaire_Responses_"
               "2025-09.docx").exists(), "standard answers not installed")
        rc2, out2 = run(["bash", str(ROOT / "demo/scripts/setup"), str(ws)])
        print("$ bash demo/scripts/setup %s (again) -> exit %d: %s" % (ws, rc2, out2.strip()))
        check(rc2 == 1, "setup should refuse a non-empty target")

        # a G02 matter folder made by hand, holding b1-04 in correspondence/
        g02 = ws / "areas/commercial/customers/acme-automotive/2026-0002_acme-automotive_msa-terms"
        (g02 / "correspondence").mkdir(parents=True)
        (g02 / "matter.md").write_text("---\nreference: 2026-0002\nkind: matter\narea: commercial\n"
                                       "sub_area: customers\nsubject: acme-automotive\ntitle: Acme "
                                       "MSA\nstatus: open\nproposed_outcome: in_progress\nfollows: "
                                       "2026-0001\nflags:\n---\n", encoding="utf-8")
        b104 = ROOT / "demo/batches/1/Acme Master Supply Agreement - draft for review.eml"
        shutil.copy2(str(b104), str(g02 / "correspondence/2026-10-15_0747_in_jschmidt_acme-master"
                                           "-supply-agreement-draft.eml"))
        rc, out = run(["bash", str(ws / "demo/scripts/drop-batch"), "2"])
        print("$ bash demo/scripts/drop-batch 2 (from inside the workspace) -> exit %d" % rc)
        print("\n".join("  " + line for line in out.strip().splitlines()))
        check(rc == 1, "drop-batch should exit 1 with unresolved placeholders")
        check("resolved {{REF:G02}} -> 2026-0002 (b1-04" in out, "G02 not resolved")
        check("unresolved {{REF:G03}}" in out and "unresolved {{REF:G04}}" in out,
              "G03/G04 not reported unresolved")
        inbox = ws / "inbox"
        src = (ROOT / "demo/batches/2/RE Acme MSA - Kestrel comments on clause 12 (liability).eml"
               ).read_bytes()
        got = (inbox / "RE Acme MSA - Kestrel comments on clause 12 (liability).eml").read_bytes()
        check(got == src.replace(b"{{REF:G02}}", b"2026-0002"), "G02 replacement not exact")
        msg = BytesParser(policy=policy.default).parsebytes(got)
        check(str(msg["Subject"]).endswith("[2026-0002]"), "b2-01 subject not resolved")
        check(b"{{REF:G03}}" in (inbox / "RE Export query PX-400 pumps to Egypt - dual use.eml"
                                 ).read_bytes(), "G03 placeholder should stay")
        check(len([p for p in inbox.iterdir() if p.is_file() and p.name != ".gitkeep"]) == 9,
              "drop-batch 2 should copy 9 files")
        rc, out = run(["bash", str(ROOT / "demo/scripts/drop-batch"), "2", "--workspace", str(ws)])
        print("$ bash demo/scripts/drop-batch 2 --workspace ... (inbox full) -> exit %d: %s" % (
            rc, out.strip()))
        check(rc == 1 and "not empty" in out, "drop-batch should refuse a full inbox")

        # place a few emails by hand
        (inbox / "noise").mkdir(exist_ok=True)
        (inbox / "please-check").mkdir(exist_ok=True)
        shutil.move(str(inbox / "RE Acme MSA - Kestrel comments on clause 12 (liability).eml"),
                    str(g02 / "correspondence/2026-10-19_0805_in_fbrandt_re-acme-msa.eml"))
        shutil.move(str(inbox / "Out of office Jonas Keller until 2 November.eml"),
                    str(inbox / "noise/2026-10-19_1002_in_jkeller_out-of-office.eml"))
        shutil.move(str(inbox / "Quick question.eml"),
                    str(inbox / "please-check/2026-10-21_1505_in_jschmidt_quick-question.eml"))
        (inbox / "please-check/2026-10-21_1505_in_jschmidt_quick-question.eml.note.md").write_text(
            "---\nfile: 2026-10-21_1505_in_jschmidt_quick-question.eml\nclaimed_reference:\n"
            "candidates: 2026-0002, 2026-0006\n---\nTwo open Acme matters could fit.\n",
            encoding="utf-8")
        shutil.move(str(inbox / "Halden Water - NDA for Thornbury pumping station project.eml"),
                    str(g02 / "correspondence/2026-10-20_1445_in_mostrow_halden-water-nda.eml"))
        rc, out = run(["bash", str(ROOT / "demo/scripts/check-filing"), "--workspace", str(ws),
                       "--batch", "2"])
        print("$ bash demo/scripts/check-filing --workspace ... --batch 2 -> exit %d" % rc)
        print("\n".join("  " + line for line in out.strip().splitlines()))
        check(rc == 1, "check-filing should exit 1 when rows fail")
        lines = out.splitlines()
        row = {line.split()[0]: line for line in lines if re.match(r"^b\d-\d\d ", line)}
        check(" PASS " in row.get("b1-04", ""), "b1-04 should PASS")
        check(" PASS " in row.get("b2-01", ""), "b2-01 should PASS")
        check(" PASS " in row.get("b2-06", ""), "b2-06 should PASS in please-check")
        check(" PASS " in row.get("b2-07", ""), "b2-07 should PASS as noise")
        check(" FAIL " in row.get("b2-04", ""), "b2-04 should FAIL (wrong folder)")
        check(" FAIL " in row.get("b2-03", ""), "b2-03 should FAIL (still in inbox)")
        check(" FAIL " in row.get("b1-01", ""), "b1-01 should FAIL (not found)")
        check("outcome in_progress ok" in out, "G02 outcome check missing")
        rc, out = run(["bash", str(ROOT / "demo/scripts/check-filing"), "--workspace", str(ws),
                       "--batch", "2", "--json"])
        check(rc == 1 and '"rows"' in out, "check-filing --json")
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    check(not tmp.exists(), "scratch folder not deleted")
    print("scratch folder %s deleted" % tmp)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", nargs="?", choices=("corpus", "scripts", "all"), default="all")
    ap.add_argument("--tmp", help="parent folder for the scripts test (default: system temp)")
    args = ap.parse_args(argv)
    if args.what in ("corpus", "all"):
        corpus()
    if args.what in ("scripts", "all"):
        scripts(args.tmp)
    if PROBLEMS:
        print("\n%d problem(s):" % len(PROBLEMS))
        for p in PROBLEMS:
            print("- " + p)
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
