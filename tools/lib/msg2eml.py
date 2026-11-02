"""msg2eml: convert Outlook .msg files to .eml beside them (or into --outdir). Keeps the .msg.

Interface: tools/msg2eml (usage text) and the build spec, D5. Methods, in order:
  1. python-oxmsg (optional import): the header block comes from PR_TRANSPORT_MESSAGE_HEADERS
     when present (MIME headers dropped), else it is rebuilt from properties; the MIME body
     and attachments are always rebuilt from properties; embedded messages become message/rfc822.
  2. msgconvert (Perl Email::Outlook::Message).
MSG2EML_METHOD=oxmsg|msgconvert forces one method (tests use it). Neither works: exit 3 with
the fallback (tools/msg2eml.ps1 on Windows with Outlook desktop, or ask for .eml).
"""

import argparse
import codecs
import hashlib
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from email import policy as _policy
from email import utils as _eutils
from email.message import EmailMessage, MIMEPart
from email.parser import BytesParser
from pathlib import Path

POLICY = _policy.default.clone(linesep="\r\n", cte_type="7bit")
METHODS = ("oxmsg", "msgconvert")
DROP_HEADERS = {"content-type", "content-transfer-encoding", "mime-version", "content-disposition",
                "content-id", "content-description", "content-length"}
# MAPI property ids (MS-OXPROPS) not named in every python-oxmsg release.
PID_SENDER_SMTP = 0x5D01
PID_SENT_REPR_SMTP = 0x5D02
PID_SENT_REPR_EMAIL = 0x0065
PID_SENT_REPR_NAME = 0x0042
PID_DELIVERY_TIME = 0x0E06
PID_CREATION_TIME = 0x3007
PID_ATTACH_HIDDEN = 0x7FFE
PID_ATTACH_FLAGS = 0x3714
EMBEDDED_STORAGE = "__substg1.0_3701000D"
EMBEDDED_HDR_OFFSET = 24
AF_BY_VALUE, AF_EMBEDDED = 1, 5

FALLBACK_TEXT = """Could not convert to .eml here. Ways forward:
  1. Windows with Outlook desktop: powershell -NoProfile -ExecutionPolicy Bypass -File tools\\msg2eml.ps1 -Path "<file.msg>"
     (it opens the .msg in Outlook and writes the .eml with its transport headers).
  2. Ask the human to open the email in new Outlook or Outlook on the web and save or download it as .eml,
     then drop the .eml into inbox/.
  3. Install a converter: bash tools/tooling-setup (python-oxmsg or msgconvert).
Record the fallback in WORKFLOW-LOG.md."""


class ConversionError(Exception):
    pass

# ---------------------------------------------------------------- oxmsg


def _safe(fn, default=None):
    try:
        v = fn()
    except Exception:
        return default
    return default if v is None else v


# Property ids and types (MS-OXPROPS) for reading text the library could not decode.
PID_BODY, PID_HTML = 0x1000, 0x1013
PTYP_STRING8, PTYP_STRING, PTYP_BINARY = 0x001E, 0x001F, 0x0102
TEXT_TYPES = (PTYP_STRING, PTYP_STRING8)


def _cp1252_for_bad_bytes(err):
    """Decode error handler: a byte that is not valid UTF-8 is read as Windows-1252, which is what
    Outlook usually meant. One curly quote no longer loses the whole body."""
    return err.object[err.start:err.end].decode("cp1252", "replace"), err.end


codecs.register_error("msg2eml-cp1252", _cp1252_for_bad_bytes)


def decode_8bit(raw, declared):
    """Text from 8-bit bytes in the declared code page, forgivingly. A .msg labelled UTF-8 often holds
    Windows-1252 bytes (smart quotes, dashes, the euro sign): those are read as Windows-1252."""
    try:
        name = codecs.lookup(declared or "cp1252").name
    except LookupError:
        name = "cp1252"
    if name == "utf-8":
        return raw.decode("utf-8", "msg2eml-cp1252")
    return raw.decode(name, "replace")


def _prop_text(props, pid, ptyps, declared):
    """The text of a variable-length property read from its raw bytes; None when absent. Used when the
    library's own strict decoding fails (python-oxmsg 0.0.2 raises on one stray byte)."""
    prop = _safe(lambda: props._get_property(pid, ptyps))
    if prop is None:
        return None
    raw = _safe(lambda: props._storage.property_stream_bytes(prop.pid, prop.ptyp))
    if raw is None:
        return None
    if prop.ptyp == PTYP_STRING:
        return raw.decode("utf-16-le", "replace")
    return decode_8bit(raw, declared)


def body_text(msg):
    """The plain-text body: the library's value, else the raw property decoded forgivingly."""
    text = _safe(lambda: msg.body)
    if not isinstance(text, str):
        props = msg.properties
        text = _prop_text(props, PID_BODY, TEXT_TYPES, _safe(lambda: props.body_encoding, ""))
    return (text or "").replace("\x00", "")


def html_text(msg):
    """The HTML body, or None: the library's value, else the raw property decoded forgivingly."""
    html = _safe(lambda: msg.html_body)
    if isinstance(html, bytes):
        html = decode_8bit(html, _safe(lambda: msg.properties.body_encoding, ""))
    if not isinstance(html, str):
        props = msg.properties
        html = _prop_text(props, PID_HTML, (PTYP_BINARY,) + TEXT_TYPES, _safe(lambda: props.body_encoding, ""))
    return html or None


def _str(props, pid):
    v = _safe(lambda: props.str_prop_value(pid))
    if not isinstance(v, str):
        v = _prop_text(props, pid, TEXT_TYPES, _safe(lambda: props._str_prop_encoding, ""))
    return v.replace("\x00", "").strip() if isinstance(v, str) else ""


def _header_blocks(text):
    """[(name, [raw lines])] from a header block; folded lines stay with their header."""
    blocks = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line == "":
            if blocks:
                break
            continue
        if line[0] in " \t":
            if blocks:
                blocks[-1][1].append(line)
            continue
        if ":" in line:
            blocks.append((line.split(":", 1)[0].strip(), [line]))
    return blocks


def _addr(name, address):
    name = (name or "").strip().strip('"').strip("'")
    address = (address or "").strip()
    if "@" not in address:
        return name
    if not name or name.lower() == address.lower():
        return address
    return _eutils.formataddr((name, address), charset="utf-8")


def _sender(msg, props):
    name = _str(props, 0x0C1A) or _str(props, PID_SENT_REPR_NAME)
    for pid in (PID_SENDER_SMTP, PID_SENT_REPR_SMTP, 0x0C1F, PID_SENT_REPR_EMAIL):
        a = _str(props, pid)
        if "@" in a:
            return _addr(name, a)
    return name


def _recipients(msg):
    out = {1: [], 2: [], 3: []}
    for r in _safe(lambda: msg.recipients, ()):
        kind = (_safe(lambda: r.properties.int_prop_value(0x0C15), 1) or 1) & 0xF
        rp = _safe(lambda: r.properties)
        addr = _safe(lambda: r.email_address, "") or (rp is not None and (_str(rp, 0x39FE) or _str(rp, 0x3003))) or ""
        name = _safe(lambda: r.name, "") or (rp is not None and _str(rp, 0x3001)) or ""
        text = _addr(name, addr)
        if text:
            out.setdefault(kind, []).append(text)
    return out


def _date(props):
    for pid in (0x0039, PID_DELIVERY_TIME, PID_CREATION_TIME):
        v = _safe(lambda: props.date_prop_value(pid))
        if hasattr(v, "tzinfo"):
            return _eutils.format_datetime(v)
    return ""


def _rebuilt_headers(msg, props, present):
    """Header lines for what the transport headers lack (all of them for sent items)."""
    rec = _recipients(msg)
    wanted = [
        ("From", _sender(msg, props)),
        ("To", ", ".join(rec.get(1, []))),
        ("Cc", ", ".join(rec.get(2, []))),
        ("Subject", _str(props, 0x0037)),
        ("Date", _date(props)),
        ("Message-ID", _str(props, 0x1035)),
        ("In-Reply-To", _str(props, 0x1042)),
        ("References", _str(props, 0x1039)),
    ]
    if not present:
        wanted.insert(3, ("Bcc", ", ".join(rec.get(3, []))))
    h = EmailMessage(policy=POLICY)
    for name, value in wanted:
        if not value or name.lower() in present:
            continue
        try:
            h[name] = value
        except Exception:
            h[name] = value.encode("ascii", "replace").decode("ascii")
    raw = h.as_bytes(policy=POLICY)
    head = raw.split(b"\r\n\r\n", 1)[0]
    return [l.decode("ascii", "replace") for l in head.split(b"\r\n") if l]


def _mime(content_type, name):
    ctype = (content_type or "").strip().lower()
    if "/" not in ctype or ctype == "application/octet-stream":
        ctype = mimetypes.guess_type(name or "")[0] or ctype or "application/octet-stream"
    main, _, sub = ctype.partition("/")
    return (main or "application"), (sub or "octet-stream")


def _embedded_message(attachment):
    """The message inside an attach-method-5 attachment, as an oxmsg Message, or None."""
    from oxmsg.message import Message
    from oxmsg.properties import Properties
    from oxmsg.util import lazyproperty

    class EmbeddedMessage(Message):
        @lazyproperty
        def _properties(self):
            return Properties(self._storage, properties_header_offset=EMBEDDED_HDR_OFFSET)

    storage = getattr(attachment, "_storage", None)
    for s in getattr(storage, "storages", ()):
        if s.name == EMBEDDED_STORAGE:
            return EmbeddedMessage(s)
    return None


def _attachments(msg, depth, seed):
    """[(name, maintype, subtype, data | EmailMessage, inline, cid)] from the .msg attachments."""
    out = []
    for n, a in enumerate(_safe(lambda: msg.attachments, ()), 1):
        ap = a.properties
        method = _safe(lambda: ap.int_prop_value(0x3705), AF_BY_VALUE)
        name = _str(ap, 0x3707) or _str(ap, 0x3704) or _str(ap, 0x3001)
        cid = _str(ap, 0x3712).strip("<>")
        hidden = bool(_safe(lambda: ap.int_prop_value(PID_ATTACH_HIDDEN), False))
        flags = _safe(lambda: ap.int_prop_value(PID_ATTACH_FLAGS), 0) or 0
        inline = hidden or bool(flags & 0x4)
        if method == AF_EMBEDDED:
            inner = _embedded_message(a)
            if inner is None or depth > 5:
                sys.stderr.write("warning: embedded message %d could not be read; left out\n" % n)
                continue
            raw = build_eml(inner, depth + 1, "%s-e%d" % (seed, n))
            out.append((name or "attachment-%d.eml" % n, "message", "rfc822",
                        BytesParser(policy=_policy.default).parsebytes(raw), inline, cid))
            continue
        data = _safe(lambda: ap.binary_prop_value(0x3701))
        if data is None:
            sys.stderr.write("warning: attachment %s is not stored inside the .msg (linked or OLE); left out\n"
                             % (name or n))
            continue
        main, sub = _mime(_str(ap, 0x370E), name)
        if main == "message":
            out.append((name or "attachment-%d.eml" % n, "message", "rfc822",
                        BytesParser(policy=_policy.default).parsebytes(data), inline, cid))
            continue
        out.append((name or "attachment-%d" % n, main, sub, data, inline, cid))
    return out


def build_eml(msg, depth=0, seed="0"):
    """RFC 5322 bytes (CRLF) for one oxmsg Message.

    seed makes the MIME boundaries deterministic, so the same .msg always gives the same bytes
    (place-email recognises an identical email by its hash).
    """
    props = msg.properties
    transport = _str(props, 0x007D)
    blocks = [b for b in _header_blocks(transport) if b[0].lower() not in DROP_HEADERS]
    present = {b[0].lower() for b in blocks}
    lines = [l for _, ls in blocks for l in ls]
    lines += _rebuilt_headers(msg, props, present)

    text = body_text(msg)
    html = html_text(msg)
    body = MIMEPart(policy=POLICY)   # MIMEPart: no MIME-Version inside sub-parts
    if html and text.strip():
        body.set_content(text)
        body.add_alternative(html, subtype="html")
    elif html:
        body.set_content(html, subtype="html")
    else:
        body.set_content(text)
    html_part = None
    if html:
        html_part = body.get_payload()[1] if body.is_multipart() else body
    for name, main, sub, data, inline, cid in _attachments(msg, depth, seed):
        if isinstance(data, EmailMessage):
            body.add_attachment(data, disposition="inline" if inline else "attachment")
            continue
        kwargs = {"filename": name, "disposition": "inline" if inline else "attachment"}
        if cid:
            kwargs["cid"] = "<%s>" % cid
        if html_part is not None and inline and cid and main == "image":
            html_part.add_related(data, maintype=main, subtype=sub, **kwargs)
        else:
            body.add_attachment(data, maintype=main, subtype=sub, **kwargs)
    for i, part in enumerate(body.walk()):
        if part.is_multipart():
            part.set_boundary("=_msg2eml_%s_%d" % (seed, i))
    raw = body.as_bytes(policy=POLICY)
    head, _, rest = raw.partition(b"\r\n\r\n")
    head_lines = [l for l in head.split(b"\r\n") if l]
    mime_lines = [l for l in head_lines if not l.lower().startswith(b"mime-version:")]
    out = [l.encode("utf-8") for l in lines] + [b"MIME-Version: 1.0"] + mime_lines
    return b"\r\n".join(out) + b"\r\n\r\n" + rest


def convert_oxmsg(src):
    try:
        from oxmsg import Message
    except ImportError:
        raise ConversionError("python-oxmsg is not installed")
    try:
        msg = Message.load(str(src))
        seed = hashlib.sha256(Path(src).read_bytes()).hexdigest()[:16]
        return build_eml(msg, 0, seed)
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError("python-oxmsg could not read it: %s" % exc)

# ---------------------------------------------------------------- msgconvert


def convert_msgconvert(src):
    exe = shutil.which("msgconvert")
    if not exe:
        raise ConversionError("msgconvert is not installed")
    tmp = tempfile.mkdtemp(prefix="msg2eml-")
    try:
        out = Path(tmp) / "out.eml"
        r = subprocess.run([exe, "--outfile", str(out), str(Path(src).resolve())], cwd=tmp,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if not out.exists():
            # older msgconvert: no --outfile; it writes <stem>.eml into the current folder
            subprocess.run([exe, str(Path(src).resolve())], cwd=tmp, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=300)
            made = [p for p in Path(tmp).iterdir() if p.suffix.lower() == ".eml"]
            out = made[0] if made else out
        if not out.exists() or out.stat().st_size == 0:
            err = r.stderr.decode("utf-8", "replace").strip().splitlines()
            raise ConversionError("msgconvert failed: %s" % (err[-1] if err else "no output"))
        return out.read_bytes()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConversionError("msgconvert failed: %s" % exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- main


def looks_like_email(data):
    try:
        msg = BytesParser(policy=_policy.default).parsebytes(data)
    except Exception:
        return False
    return len(msg.keys()) > 0


def convert(src, methods):
    errors = []
    for m in methods:
        try:
            data = convert_oxmsg(src) if m == "oxmsg" else convert_msgconvert(src)
        except ConversionError as exc:
            errors.append("%s: %s" % (m, exc))
            continue
        if not looks_like_email(data):
            errors.append("%s: output is not an email" % m)
            continue
        return data, m, errors
    return None, None, errors


def eml_body_text(data):
    """The text of an email's body (plain, else HTML), stripped; empty when there is none."""
    try:
        part = BytesParser(policy=_policy.default).parsebytes(data).get_body(preferencelist=("plain", "html"))
        return (part.get_content() or "").strip() if part is not None else ""
    except Exception:
        return ""


def refresh(targets, methods, run=None):
    """Filed emails that an older msg2eml converted without their body (a Windows-1252 byte in a .msg
    labelled UTF-8 made it give up): re-convert them from the .msg original kept beside them. The old .eml
    is kept in agent/history/; documents.md gets the new sha256 and read: pending, so the reader reads it."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import common
    root = common.find_root()
    run = run or common.run_id(root)
    if targets:
        matters = []
        for t in targets:
            m = common.find_matter(root, t) if common.REF_RE.match(t) else None
            if m is None:
                cand = Path(t) if Path(t).is_absolute() else root / t
                m = cand if common.is_matter_dir(cand) else None
            if m is None:
                sys.stderr.write("not a matter: %s\n" % t)
                return 2
            matters.append(m)
    else:
        matters = list(common.iter_matter_dirs(root))
    fixed = failed = 0
    for m in matters:
        agent = common.agent_dir(m)
        corr = agent / "correspondence"
        if not corr.is_dir():
            continue
        for src in sorted(p for p in corr.rglob("*") if p.is_file() and p.suffix.lower() == ".msg"):
            eml = src.with_suffix(".eml")
            if not eml.is_file() or eml_body_text(eml.read_bytes()):
                continue
            data, method, errors = convert(src, methods)
            if data is None:
                failed += 1
                sys.stdout.write("not re-converted: %s (%s)\n" % (common.rel(src, root), "; ".join(errors)))
                continue
            if not eml_body_text(data):
                continue                       # the .msg holds no body text either
            hist = agent / "history"
            hist.mkdir(exist_ok=True)
            kept, k = hist / (eml.stem + ".empty-body.eml"), 2
            while kept.exists():
                kept, k = hist / ("%s.empty-body-%d.eml" % (eml.stem, k)), k + 1
            shutil.move(str(eml), str(kept))
            with open(str(eml), "xb") as fh:
                fh.write(data)
            common.protect(eml)
            folder = eml.parent.relative_to(agent).as_posix()
            docs = agent / "documents.md"
            if docs.is_file():
                lines = common.read_text(docs).split("\n")
                for i, line in enumerate(lines):
                    if common.is_record_line(line):
                        f = common.split_pipe(line)
                        if len(f) > 8 and f[0] == eml.name and f[1] == folder:
                            f[7], f[8] = common.sha256_file(eml), "pending"
                            lines[i] = common.join_pipe(f)
                common.write_text_atomic(docs, "\n".join(lines))
            common.append_line(agent / "log.md", common.join_pipe(
                [common.stamp(root), "re-converted %s/%s from its .msg original (an older msg2eml lost the body); "
                 "old copy kept as history/%s" % (folder, eml.name, kept.name), "%s/%s" % (folder, src.name), run]))
            fixed += 1
            sys.stdout.write("re-converted: %s (%s)\n" % (common.rel(eml, root), method))
    sys.stdout.write("msg2eml --refresh: %d emails re-converted, %d could not be\n" % (fixed, failed))
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/msg2eml", description="Convert .msg files to .eml.")
    ap.add_argument("files", nargs="*", metavar="FILE.msg")
    ap.add_argument("--outdir", metavar="DIR")
    ap.add_argument("--refresh", action="store_true",
                    help="re-convert filed emails whose body an older version lost (arguments: matters)")
    ap.add_argument("--run")
    args = ap.parse_args(argv)
    forced = os.environ.get("MSG2EML_METHOD", "").strip().lower()
    if forced and forced not in METHODS:
        sys.stderr.write("MSG2EML_METHOD must be oxmsg or msgconvert (got '%s')\n" % forced)
        return 2
    methods = (forced,) if forced else METHODS
    if args.refresh:
        return refresh(args.files, methods, args.run)
    if not args.files:
        ap.print_usage(sys.stderr)
        sys.stderr.write("give at least one .msg file\n")
        return 2
    bad = False
    for f in args.files:
        if not f.lower().endswith(".msg"):
            sys.stderr.write("not a .msg file: %s\n" % f)
            bad = True
        elif not Path(f).is_file():
            sys.stderr.write("no file: %s\n" % f)
            bad = True
    if bad:
        return 2
    outdir = Path(args.outdir) if args.outdir else None
    if outdir is not None:
        try:
            outdir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            sys.stderr.write("cannot use --outdir %s: %s\n" % (args.outdir, exc))
            return 2
    failed = 0
    for f in args.files:
        src = Path(f)
        dest = (outdir or src.parent) / (src.stem + ".eml")
        if dest.exists():
            sys.stdout.write("exists, kept: %s\n" % dest.as_posix())
            continue
        data, method, errors = convert(src, methods)
        if data is None:
            failed += 1
            sys.stdout.write("not converted: %s (%s)\n" % (src.as_posix(), "; ".join(errors)))
            continue
        try:
            with open(str(dest), "xb") as fh:
                fh.write(data)
        except OSError as exc:
            failed += 1
            sys.stdout.write("not converted: %s (cannot write %s: %s)\n" % (src.as_posix(), dest.as_posix(), exc))
            continue
        sys.stdout.write("converted: %s -> %s (%s)\n" % (src.as_posix(), dest.as_posix(), method))
    if failed:
        sys.stderr.write(FALLBACK_TEXT + "\n")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
