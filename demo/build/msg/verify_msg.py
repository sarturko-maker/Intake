#!/usr/bin/env python3
"""Check the demo .msg files three ways against their JSON specs.

Usage (from the repository root):
  python3 demo/build/msg/verify_msg.py [SPEC.json ...]
Default: every demo/build/msg/specs/*.json. Each spec's "out" file is checked.

1. python-oxmsg reads class, subject, body, sender, recipients, ids, date, headers, attachments.
2. msgconvert converts to .eml; Python's email package checks headers, body and attachments.
3. olefile lists storages and streams, checks the root CLSID, parsing issues, every property
   entry against its stream, the header counts, and the red-black directory tree.

Exit: 0 all pass; 1 a check failed; 3 a checker is missing (nothing failed).
Needs: python-oxmsg (brings olefile), msgconvert (apt-get install libemail-outlook-message-perl).
"""

import email
import email.header
import email.policy
import email.utils
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MSG_CLSID = "00020D0B-0000-0000-C000-000000000046"
PT_UNICODE, PT_BINARY = 0x001F, 0x0102
NOSTREAM = 0xFFFFFFFF  # MS-CFB: no sibling or child
VARIABLE = (PT_UNICODE, PT_BINARY)

ROOT_STREAMS = ["001A001F", "0037001F", "0E1D001F", "1000001F", "0C1A001F", "0C1F001F",
                "0C1E001F", "5D01001F", "0042001F", "0065001F", "0064001F", "0E04001F",
                "0E03001F", "1035001F", "007D001F"]
RECIP_STREAMS = ["3001001F", "3003001F", "3002001F", "39FE001F"]
ATTACH_STREAMS = ["37010102", "3704001F", "3707001F", "3703001F", "370E001F", "3001001F"]
NAMEID_STREAMS = ["__substg1.0_00020102", "__substg1.0_00030102", "__substg1.0_00040102"]
MSG_NAME = re.compile(r"^(?:(?:__recip|__attach)_version1\.0_#[0-9A-F]{8}(?:/__properties_version1\.0"
                      r"|/__substg1\.0_[0-9A-F]{8})?|__nameid_version1\.0(?:/__substg1\.0_[0-9A-F]{8})?"
                      r"|__properties_version1\.0|__substg1\.0_[0-9A-F]{8})$")


class Report:
    def __init__(self):
        self.failed = 0
        self.skipped = []

    def check(self, label, ok, shown=""):
        shown = shown if len(shown) <= 100 else shown[:97] + "..."
        print(f"  {'PASS' if ok else 'FAIL'} {label}" + (f": {shown}" if shown else ""))
        if not ok:
            self.failed += 1

    def skip(self, what, how):
        print(f"  SKIP {what}: not installed ({how})")
        self.skipped.append(what)


def bracket(value):
    value = str(value).strip()
    return value if value.startswith("<") else f"<{value}>"


def decoded(value):
    """Header text with RFC 2047 encoded words decoded."""
    return str(email.header.make_header(email.header.decode_header(value))) if value else ""


def addr_pairs(raw):
    """[(display name, address)] from a raw address header, names decoded."""
    return [(decoded(name), addr) for name, addr in email.utils.getaddresses([raw])] if raw else []


def spec_pairs(addresses):
    return [(a.get("name") or "", a["address"]) for a in addresses]


def norm(text):
    return (text or "").replace("\r\n", "\n").rstrip("\n")


def load_spec(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    body = raw.get("body", "")
    refs = raw.get("references") or []
    refs = refs if isinstance(refs, list) else refs.split()
    return {
        "out": ROOT / raw["out"],
        "from": raw["from"],
        "to": raw["to"],
        "cc": raw.get("cc") or [],
        "subject": raw["subject"],
        "date": raw["date"],
        "message_id": bracket(raw["message_id"]),
        "in_reply_to": bracket(raw["in_reply_to"]) if raw.get("in_reply_to") else "",
        "references": " ".join(bracket(r) for r in refs),
        "body": norm("\n".join(body) if isinstance(body, list) else body),
        "attachments": [(a.get("name") or Path(a["path"]).name, a["mime"], (ROOT / a["path"]).read_bytes())
                        for a in raw.get("attachments") or []],
    }


def check_oxmsg(spec, rep):
    try:
        from oxmsg import Message
        from oxmsg.domain import constants as c
    except ImportError:
        return rep.skip("python-oxmsg", "python3 -m pip install python-oxmsg")
    m = Message.load(str(spec["out"]))
    p = m.properties
    rep.check("message class", m.message_class == "IPM.Note", m.message_class)
    rep.check("subject", m.subject == spec["subject"], repr(m.subject))
    rep.check("body", norm(m.body) == spec["body"], f"{len(m.body)} chars, starts {m.body[:40]!r}")
    rep.check("sender (From header)", addr_pairs(m.sender) == spec_pairs([spec["from"]]), m.sender)
    sender = (p.str_prop_value(c.PID_SENDER_NAME), p.str_prop_value(c.PID_SENDER_EMAIL_ADDRESS),
              p.str_prop_value(c.PID_SENDER_SMTP_ADDRESS))
    want_sender = (spec["from"].get("name") or spec["from"]["address"],) + (spec["from"]["address"],) * 2
    rep.check("sender properties", sender == want_sender, str(sender))
    got = [(r.name, r.email_address, r.properties.int_prop_value(c.PID_RECIPIENT_TYPE)) for r in m.recipients]
    # Outlook shows the address as the display name when there is no name; so does the writer.
    want = [(a.get("name") or a["address"], a["address"], kind)
            for kind, group in ((1, spec["to"]), (2, spec["cc"])) for a in group]
    rep.check("recipients (name, address, type 1=To 2=Cc)", got == want, str(got))
    mid = p.str_prop_value(c.PID_INTERNET_MESSAGE_ID)
    rep.check("PR_INTERNET_MESSAGE_ID", mid == spec["message_id"], mid)
    irt = p.str_prop_value(c.PID_IN_REPLY_TO_ID) or ""
    refs = p.str_prop_value(c.PID_INTERNET_REFERENCES) or ""
    rep.check("PR_IN_REPLY_TO_ID / PR_INTERNET_REFERENCES",
              (irt, refs) == (spec["in_reply_to"], spec["references"]), repr((irt, refs)))
    when = email.utils.parsedate_to_datetime(spec["date"])
    rep.check("sent date (PR_CLIENT_SUBMIT_TIME)", m.sent_date == when, str(m.sent_date))
    h = m.message_headers
    heads = (h.get("Message-ID"), h.get("Date"), addr_pairs(h.get("From")), addr_pairs(h.get("To")),
             addr_pairs(h.get("Cc")), decoded(h.get("Subject")))
    rep.check("transport headers Message-ID, Date, From, To, Cc, Subject",
              heads == (spec["message_id"], spec["date"], spec_pairs([spec["from"]]), spec_pairs(spec["to"]),
                        spec_pairs(spec["cc"]), spec["subject"]),
              f"{heads[0]} | {heads[1]}")
    rep.check("transport headers MIME-Version, Content-Type",
              h.get("MIME-Version") == "1.0" and bool(h.get("Content-Type")), str(h.get("Content-Type")))
    atts = [(a.file_name, a.mime_type, a.file_bytes) for a in m.attachments]
    rep.check("attachments", atts == spec["attachments"],
              str([(n, t, len(b)) for n, t, b in atts]) if atts else "none")
    counts = (m.attachment_count, m._header_prop_values[2])
    rep.check("header counts (attachments, recipients)",
              counts == (len(spec["attachments"]), len(want)), str(counts))


def check_msgconvert(spec, rep):
    exe = shutil.which("msgconvert")
    if not exe:
        return rep.skip("msgconvert", "apt-get install -y libemail-outlook-message-perl")
    with tempfile.TemporaryDirectory() as tmp:
        eml = Path(tmp) / "converted.eml"
        proc = subprocess.run([exe, "--outfile", str(eml), str(spec["out"])], capture_output=True, text=True)
        # msgconvert itself warns "Value for 'Subject' header with wide characters" for any
        # non-ASCII subject before it copies the encoded transport header; that one is expected.
        warnings = [w for w in proc.stderr.splitlines() if w.strip() and "with wide characters" not in w]
        rep.check("msgconvert exit 0, no warnings", proc.returncode == 0 and not warnings,
                  "; ".join(warnings) or proc.stderr.strip())
        if proc.returncode:
            return
        raw = eml.read_bytes()
    plain = email.message_from_bytes(raw, policy=email.policy.compat32)
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    rep.check("Message-ID", plain["Message-ID"] == spec["message_id"], plain["Message-ID"])
    rep.check("Date", plain["Date"] == spec["date"], plain["Date"])
    rep.check("From", addr_pairs(plain["From"]) == spec_pairs([spec["from"]]), plain["From"])
    rep.check("To", addr_pairs(plain["To"]) == spec_pairs(spec["to"]), " ".join(plain["To"].split()))
    rep.check("Cc", addr_pairs(plain["Cc"]) == spec_pairs(spec["cc"]), " ".join((plain["Cc"] or "none").split()))
    rep.check("Subject", msg["Subject"] == spec["subject"], msg["Subject"])
    if spec["in_reply_to"]:
        rep.check("In-Reply-To", plain["In-Reply-To"] == spec["in_reply_to"], plain["In-Reply-To"])
    if spec["references"]:
        rep.check("References", " ".join(plain["References"].split()) == spec["references"],
                  " ".join(plain["References"].split()))
    body = msg.get_body(preferencelist=("plain",))
    text = body.get_content() if body is not None else ""
    rep.check("body", norm(text) == spec["body"], f"{len(norm(text))} chars, ends {norm(text)[-30:]!r}")
    atts = [(part.get_filename(), part.get_content_type(), part.get_payload(decode=True))
            for part in msg.iter_attachments()]
    rep.check("attachments", atts == spec["attachments"],
              str([(n, t, b) for n, t, b in atts]) if atts else "none")


def check_olefile(spec, rep):
    try:
        import olefile
    except ImportError:
        return rep.skip("olefile", "python3 -m pip install olefile")
    with olefile.OleFileIO(str(spec["out"])) as ole:
        names = sorted("/".join(e) for e in ole.listdir(streams=True, storages=True))
        for name in names:
            kind = "storage" if ole.get_type(name) == olefile.STGTY_STORAGE else f"{ole.get_size(name)} bytes"
            print(f"    {name}  [{kind}]")
        rep.check("root CLSID", ole.root.clsid == MSG_CLSID, ole.root.clsid)
        rep.check("olefile parsing issues", not ole.parsing_issues,
                  str(ole.parsing_issues) if ole.parsing_issues else "none")
        recips = [n for n in names if n.startswith("__recip_version1.0_#") and "/" not in n]
        attachs = [n for n in names if n.startswith("__attach_version1.0_#") and "/" not in n]
        rep.check("recipient storages", len(recips) == len(spec["to"]) + len(spec["cc"]), ", ".join(recips))
        rep.check("attachment storages", len(attachs) == len(spec["attachments"]), ", ".join(attachs) or "none")
        want = ["__properties_version1.0"] + [f"__substg1.0_{s}" for s in ROOT_STREAMS]
        want += [f"__nameid_version1.0/{s}" for s in NAMEID_STREAMS]
        want += [f"{r}/__substg1.0_{s}" for r in recips for s in RECIP_STREAMS]
        want += [f"{a}/__substg1.0_{s}" for a in attachs for s in ATTACH_STREAMS]
        want += [f"{s}/__properties_version1.0" for s in recips + attachs]
        if spec["in_reply_to"]:
            want.append("__substg1.0_1042001F")
        if spec["references"]:
            want.append("__substg1.0_1039001F")
        missing = [w for w in want if w not in names]
        rep.check("required storages and streams", not missing, "missing " + ", ".join(missing) if missing
                  else f"{len(names)} entries")
        foreign = [n for n in names if not MSG_NAME.match(n)]
        rep.check("no entries outside MS-OXMSG names", not foreign, ", ".join(map(repr, foreign)) or "none")
        nameid = [ole.get_size(f"__nameid_version1.0/{s}") for s in NAMEID_STREAMS]
        rep.check("__nameid_version1.0 streams (may be empty)", True, f"sizes {nameid}")
        problems = []
        for storage, header in [("", 32)] + [(s, 8) for s in recips + attachs]:
            problems += property_stream_problems(ole, names, storage, header)
        head = ole.openstream("__properties_version1.0").read()[:32]
        counts = struct.unpack("<8x4I8x", head)
        want_counts = (len(recips), len(attachs), len(recips), len(attachs))
        if counts != want_counts:
            problems.append(f"root header {counts} != {want_counts}")
        rep.check("property entries match streams and sizes", not problems, "; ".join(problems) or "all match")
        tree = tree_problems(ole)
        rep.check("directory red-black trees", not tree, "; ".join(tree) or "valid")


def property_stream_problems(ole, names, storage, header):
    prefix = f"{storage}/" if storage else ""
    data = ole.openstream(f"{prefix}__properties_version1.0").read()
    problems, tagged = [], set()
    if len(data) < header or (len(data) - header) % 16:
        return [f"{prefix}__properties_version1.0 has length {len(data)}"]
    for off in range(header, len(data), 16):
        ptype, pid, flags, size, reserved = struct.unpack("<HHIII", data[off:off + 16])
        name = f"__substg1.0_{pid:04X}{ptype:04X}"
        if ptype in VARIABLE:
            tagged.add(name)
            path = prefix + name
            if path not in names:
                problems.append(f"no stream {path}")
                continue
            real = ole.get_size(path) + (2 if ptype == PT_UNICODE else 0)
            if size != real or reserved:
                problems.append(f"{path}: entry size {size}, expected {real}")
            if ptype == PT_UNICODE and ole.openstream(path).read()[-2:] == b"\0\0":
                problems.append(f"{path}: stream holds a terminator")
    for n in names:
        if n.startswith(prefix + "__substg1.0_") and "/" not in n[len(prefix):] and n[len(prefix):] not in tagged:
            if storage != "__nameid_version1.0":
                problems.append(f"stream without entry: {n}")
    return problems


def cfb_key(name):
    return (len(name), name.upper())


def tree_problems(ole):
    entries = ole.direntries
    problems = []

    def walk(sid, lo, hi):
        if sid == NOSTREAM:
            return 1
        e = entries[sid]
        if (lo and cfb_key(lo) >= cfb_key(e.name)) or (hi and cfb_key(e.name) >= cfb_key(hi)):
            problems.append(f"order at {e.name}")
        for k in (e.sid_left, e.sid_right):
            if e.color == 0 and k != NOSTREAM and entries[k].color == 0:
                problems.append(f"red-red at {e.name}")
        left, right = walk(e.sid_left, lo, e.name), walk(e.sid_right, e.name, hi)
        if left != right:
            problems.append(f"black height at {e.name}")
        return left + (1 if e.color == 1 else 0)

    for e in entries:
        if e is not None and e.entry_type in (1, 5):
            walk(e.sid_child, "", "")
    return problems



def main(argv):
    specs = argv or sorted(str(p) for p in (HERE / "specs").glob("*.json"))
    rep = Report()
    for spec_path in specs:
        spec = load_spec(spec_path)
        out = spec["out"].resolve()
        try:
            shown = out.relative_to(ROOT).as_posix()
        except ValueError:  # outside the repository
            shown = str(out)
        print(f"{shown}  (spec {Path(spec_path).name})")
        if not out.is_file():
            rep.check("file exists", False, "build it: cd demo/build/msg && node make_msg.mjs specs/*.json")
            continue
        for label, fn in (("python-oxmsg", check_oxmsg), ("msgconvert", check_msgconvert),
                          ("olefile", check_olefile)):
            print(f" [{label}]")
            fn(spec, rep)
    print(f"{'FAILED' if rep.failed else 'OK'}: {rep.failed} failed"
          + (f", skipped {', '.join(sorted(set(rep.skipped)))}" if rep.skipped else ""))
    return 1 if rep.failed else (3 if rep.skipped else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
