"""Email parsing shared by unpack-email and place-email. Python 3.8+, standard library only.

Both tools call parse_email(), so canonical names, hashes, attachment lists and
kinds always agree. An attachment's sha256 is taken over exactly the bytes
place-email stores (its decoded payload; an attached email is re-serialised
from its parsed form with the source folding and line endings kept).

Formats: RULES.md (Intake) and the build spec, D2 and D3.
"""

import codecs
import datetime as _dt
import hashlib
import io
import mimetypes
import os
import re
from email import policy as _policy
from email import utils as _eutils
from email.generator import BytesGenerator
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path

import common

BODY_CHARS = 4000
SIGNATURE_IMAGE_MAX = 100 * 1024          # bytes; smaller inline/Content-ID images are signatures
EMPTY_BODY_CHARS = 20
LOGO_ONLY_BODY_CHARS = 40
MAX_NAME = 150                            # longest attachment file name kept

KINDS = ("document", "image", "signature-image", "calendar", "email")
STORED_KINDS = ("document", "image", "email")   # what place-email writes to documents/
NOISE_HINTS = ("auto-reply", "bulk", "calendar", "empty-body", "logo-only")
AUTO_REPLY_SUBJECTS = ("out of office", "automatic reply", "automatische antwort",
                       "abwesenheitsnotiz")
BULK_PRECEDENCE = ("bulk", "list", "junk")
CALENDAR_TYPES = ("text/calendar", "application/ics")
EMAIL_TYPES = ("message/rfc822", "message/global")
# Security envelope parts of signed mail: not attachments, never listed.
SIGNATURE_PART_TYPES = ("application/pkcs7-signature", "application/x-pkcs7-signature",
                        "application/pgp-signature")
NOTE_DATE_FROM_FILE = "date from file time"

_EXT = {
    "text/plain": ".txt", "text/html": ".html", "text/calendar": ".ics",
    "application/ics": ".ics", "message/rfc822": ".eml", "message/global": ".eml",
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/bmp": ".bmp",
    "image/tiff": ".tif", "image/webp": ".webp", "application/pdf": ".pdf",
    "application/msword": ".doc", "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/zip": ".zip", "application/octet-stream": ".bin",
    "application/vnd.ms-outlook": ".msg",
}
_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {"COM%d" % i for i in range(1, 10)} \
    | {"LPT%d" % i for i in range(1, 10)}
_BAD_NAME_CHARS = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]')
_ID_RE = re.compile(r"<([^<>\s]+)>")
_HONORIFICS = {"dr", "prof", "mr", "mrs", "ms", "miss", "mx", "sir", "dame", "herr", "frau"}

# ---------------------------------------------------------------- context


class Context:
    """Workspace settings read once per tool run."""

    def __init__(self, root):
        self.root = Path(root)
        self.cfg = common.house_config(self.root)
        self.tz = common.house_tz(self.root)

    def to_house(self, dt):
        """Aware datetime in house time (machine local time when tzdata is missing)."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt.astimezone(self.tz) if self.tz else dt.astimezone()

    def now(self):
        return _dt.datetime.now(self.tz) if self.tz else _dt.datetime.now()

    def stamp(self):
        return self.now().strftime("%Y-%m-%d %H:%M")

    def run_id(self):
        return self.now().strftime("%Y-%m-%d_%H%M%S")

    def rel(self, path):
        return common.rel(path, self.root)

# ---------------------------------------------------------------- journal

JOURNAL_HEADER = "# time | run | action | item | destination | reason | confidence"


def append_journal(root, stamp, run, action, item, destination, reason="", confidence=""):
    """One JOURNAL.md line; creates the file with its header line when absent."""
    path = Path(root) / "JOURNAL.md"
    if not path.exists():
        common.append_line(path, JOURNAL_HEADER)
    common.append_line(path, common.join_pipe([stamp, run, action, item, destination, reason, confidence]))

# ---------------------------------------------------------------- text helpers


def _has_surrogates(s):
    return any("\ud800" <= c <= "\udfff" for c in s)


def repair(s):
    """Undo surrogate escapes left by raw 8-bit header bytes (UTF-8, else cp1252)."""
    if s is None:
        return ""
    s = str(s)
    if not _has_surrogates(s):
        return s
    try:
        b = s.encode("utf-8", "surrogateescape")
    except UnicodeEncodeError:
        return s.encode("utf-8", "replace").decode("utf-8", "replace")
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252", "replace")


def clean(s):
    """One-line header text: repaired, whitespace collapsed."""
    return " ".join(repair(s).split())


def decode_text(data, charset):
    """Bytes to text in the declared charset. Unknown charsets read as UTF-8; bad bytes replaced."""
    cs = (charset or "").strip().strip('"').lower()
    if cs in ("", "ascii", "us-ascii", "unknown-8bit", "x-unknown", "default", "8bit"):
        cs = "utf-8"
    try:
        codecs.lookup(cs)
    except LookupError:
        cs = "utf-8"
    try:
        return data.decode(cs)
    except UnicodeDecodeError:
        pass
    if codecs.lookup(cs).name == "utf-8":
        try:
            return data.decode("cp1252")
        except UnicodeDecodeError:
            pass
    return data.decode(cs, errors="replace")


def strip_brackets(value):
    return clean(value).strip().strip("<>").strip()


def message_ids(value):
    """Ids from a Message-ID, In-Reply-To or References value, without angle brackets."""
    value = clean(value)
    if not value:
        return []
    found = _ID_RE.findall(value)
    if not found:
        found = [v.strip("<>,;") for v in value.split()]
    out = []
    for f in found:
        if f and f not in out:
            out.append(f)
    return out

# ---------------------------------------------------------------- html to text


class _HTMLText(HTMLParser):
    BLOCK = {"p", "div", "li", "tr", "table", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
             "pre", "section", "article", "header", "footer", "address", "dd", "dt", "dl",
             "center", "form", "fieldset", "caption", "thead", "tbody", "tfoot"}
    SKIP = {"script", "style", "head", "title", "noscript", "template"}

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.pre = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "blockquote":
            self.out.append("\n\x00Q+\n")
        elif tag in ("br", "hr"):
            self.out.append("\n")
        elif tag in self.BLOCK:
            if tag == "pre":
                self.pre += 1
            self.out.append("\n")
        elif tag in ("td", "th"):
            self.out.append(" ")

    def handle_startendtag(self, tag, attrs):
        if tag in ("br", "hr"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag == "blockquote":
            self.out.append("\n\x00Q-\n")
        elif tag in self.BLOCK:
            if tag == "pre":
                self.pre = max(0, self.pre - 1)
            self.out.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        if not self.pre:
            data = re.sub(r"\s+", " ", data)
        self.out.append(data)


def html_to_text(markup):
    """Readable text from HTML. Blockquoted lines come back prefixed with '> '."""
    parser = _HTMLText()
    try:
        parser.feed(markup or "")
        parser.close()
    except Exception:  # malformed markup: keep what was collected
        pass
    lines = []
    depth = 0
    for line in "".join(parser.out).replace("\xa0", " ").split("\n"):
        if line == "\x00Q+":
            depth += 1
            continue
        if line == "\x00Q-":
            depth = max(0, depth - 1)
            continue
        line = re.sub(r"[ \t]+", " ", line).strip()
        if depth and line:
            line = "> " * depth + line
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# ---------------------------------------------------------------- quoted history

_ON_WROTE = re.compile(r"^On\s.*\swrote:$")
_ON_START = re.compile(r"^On\s.+")
_WROTE_END = re.compile(r".*\bwrote:$")
_AM_SCHRIEB = re.compile(r"^Am\s.*\sschrieb\s.*:$")
_AM_START = re.compile(r"^Am\s.+\sschrieb\b.*")
_ORIGINAL = re.compile(r"^-{2,}\s*(Original Message|Ursprüngliche Nachricht|Ursprungliche Nachricht)\s*-{2,}$",
                       re.IGNORECASE)
_FROM_LINE = re.compile(r"^\*?(From|Von)\s*:\*?(\s|$)")
_SENT_LINE = re.compile(r"^\*?(Sent|Date|Gesendet|Datum)\s*:\*?(\s|$)")
_SEPARATOR = re.compile(r"^[\s_\-=*~]*$")


def _history_starts(lines, i):
    s = lines[i].strip()
    if _ON_WROTE.match(s) or _AM_SCHRIEB.match(s) or _ORIGINAL.match(s):
        return True
    nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
    if _ON_START.match(s) and not s.endswith("wrote:") and _WROTE_END.match(nxt):
        return True  # "On <date>, <name>" wrapped onto two lines
    if _AM_START.match(s) and not s.endswith(":") and nxt.endswith(":"):
        return True
    if _FROM_LINE.match(s):
        for j in range(i + 1, min(i + 5, len(lines))):
            if _SENT_LINE.match(lines[j].strip()):
                return True
    return False


def strip_quoted(text):
    """(new_text, quoted_chars). Drops '>' lines and everything from a history marker on."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    kept = []
    for i, line in enumerate(lines):
        if _history_starts(lines, i):
            break
        if line.lstrip().startswith(">"):
            continue
        kept.append(line)
    while kept and _SEPARATOR.match(kept[-1]):
        kept.pop()
    while kept and not kept[0].strip():
        kept.pop(0)
    new = "\n".join(line.rstrip() for line in kept)
    return new, max(0, len(text.strip()) - len(new))

# ---------------------------------------------------------------- names


def safe_name(name, fallback):
    """A file name safe on Windows, macOS and Linux, as close to the original as possible."""
    name = clean(name).replace("\\", "/").split("/")[-1]
    name = _BAD_NAME_CHARS.sub("_", name).strip().rstrip(". ")
    if not name or set(name) <= {".", "_"}:
        return fallback
    stem, ext = os.path.splitext(name)
    if stem.upper() in _WIN_RESERVED:
        name = "_" + name
        stem = "_" + stem
    if len(name) > MAX_NAME:
        ext = ext if len(ext) <= 10 else ""
        name = stem[:MAX_NAME - len(ext)].rstrip(". ") + ext
    return name


def ext_for(content_type):
    return _EXT.get(content_type) or mimetypes.guess_extension(content_type or "") or ".bin"


def canonical_name(when, direction, address, subject):
    """YYYY-MM-DD_HHMM_<in|out>_<from-slug>_<subject-slug>.eml (when is in house time)."""
    subj = common.TAG_RE.sub(" ", subject or "")
    return "%s_%s_%s_%s.eml" % (when.strftime("%Y-%m-%d_%H%M"), direction,
                                common.from_slug(address), common.slugify(subj, 40))


def unique_path(folder, name):
    """folder/name, or folder/<stem>-2<ext>, -3 ... if taken."""
    folder = Path(folder)
    dest = folder / name
    stem, ext = os.path.splitext(name)
    n = 2
    while dest.exists():
        dest = folder / ("%s-%d%s" % (stem, n, ext))
        n += 1
    return dest


def candidate_paths(folder, name):
    """folder/name and its -2, -3 ... variants that exist (for identical-bytes checks)."""
    folder = Path(folder)
    stem, ext = os.path.splitext(name)
    out = []
    if (folder / name).exists():
        out.append(folder / name)
    pat = re.compile(r"^" + re.escape(stem) + r"-(\d+)" + re.escape(ext) + r"$")
    if folder.is_dir():
        for p in sorted(folder.iterdir()):
            if pat.match(p.name):
                out.append(p)
    return out

# ---------------------------------------------------------------- addresses and names


def _addresses(msg, header):
    """[{'name', 'address'}] for an address header; tolerant of malformed values."""
    raw = msg.get(header)
    if raw is None:
        return []
    out = []
    try:
        for a in raw.addresses:
            out.append({"name": clean(a.display_name), "address": clean(a.addr_spec).lower()})
    except Exception:
        out = []
    if not out:
        for name, addr in _eutils.getaddresses([clean(str(raw))]):
            if name or addr:
                out.append({"name": clean(name), "address": clean(addr).lower()})
    return [a for a in out if a["address"] or a["name"]]


def norm_name(name):
    """Comparable full name: case-folded, 'Last, First' turned round, titles such as Dr dropped."""
    n = clean(name).strip().strip("\"'")
    if n.count(",") == 1:
        last, first = [x.strip() for x in n.split(",")]
        if last and first:
            n = first + " " + last
    words = re.sub(r"[.\s]+", " ", n).strip().lower().split()
    while words and words[0] in _HONORIFICS:
        words = words[1:]
    return " ".join(words)

# ---------------------------------------------------------------- attachments


class Attachment:
    """One attachment as listed by unpack-email and stored by place-email."""

    def __init__(self, name, content_type, data, kind, inline, content_id=""):
        self.name = name
        self.content_type = content_type
        self.data = data
        self.size = len(data)
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.kind = kind
        self.inline = inline
        self.content_id = content_id

    def public(self):
        return {"name": self.name, "content_type": self.content_type, "size": self.size,
                "sha256": self.sha256, "kind": self.kind, "inline": self.inline}


def _leaves(part):
    """Leaf parts in order. An attached email is one leaf; its own parts are not walked."""
    if part.get_content_type() in EMAIL_TYPES:
        yield part
        return
    if part.is_multipart():
        for sub in part.iter_parts():
            for leaf in _leaves(sub):
                yield leaf
    elif part.get_content_maintype() != "message":   # delivery reports and the like
        yield part


def _email_bytes(part, linesep):
    sub = part.get_payload()
    if isinstance(sub, list):
        sub = sub[0] if sub else None
    if sub is None:
        return b""
    if isinstance(sub, (bytes, str)):
        return sub if isinstance(sub, bytes) else sub.encode("utf-8", "surrogateescape")
    buf = io.BytesIO()
    pol = _policy.default.clone(linesep=linesep, refold_source="none")
    BytesGenerator(buf, mangle_from_=False, policy=pol).flatten(sub)
    return buf.getvalue()


def _filename(part):
    try:
        return part.get_filename() or ""
    except Exception:
        return ""


def _attachments(msg, skip_ids, linesep):
    out = []
    for part in _leaves(msg):
        if id(part) in skip_ids:
            continue
        ctype = part.get_content_type()
        if ctype in SIGNATURE_PART_TYPES:
            continue
        disp = part.get_content_disposition()
        fname = _filename(part)
        if ctype in ("text/plain", "text/html") and not fname and disp != "attachment":
            continue  # a further inline piece of the body, not an attachment
        n = len(out) + 1
        inline = disp == "inline"
        cid = clean(part.get("Content-ID", ""))
        if ctype in EMAIL_TYPES:
            data = _email_bytes(part, linesep)
            inner = part.get_payload()
            inner = inner[0] if isinstance(inner, list) and inner else None
            subj = clean(inner.get("Subject", "")) if inner is not None and hasattr(inner, "get") else ""
            name = common.slugify(subj, 40) + ".eml" if subj.strip() else "attachment-%d.eml" % n
            out.append(Attachment(name, "message/rfc822", data, "email", inline, cid))
            continue
        data = part.get_payload(decode=True) or b""
        name = safe_name(fname, "attachment-%d%s" % (n, ext_for(ctype)))
        guessed = mimetypes.guess_type(name)[0] or ""
        if ctype in CALENDAR_TYPES or name.lower().endswith((".ics", ".vcs")):
            kind = "calendar"
        elif ctype.startswith("image/") or (ctype == "application/octet-stream"
                                            and guessed.startswith("image/")):
            kind = "signature-image" if (inline or cid) and len(data) < SIGNATURE_IMAGE_MAX else "image"
        else:
            kind = "document"
        out.append(Attachment(name, ctype, data, kind, inline, cid))
    return out

# ---------------------------------------------------------------- parsing


class ParsedEmail:
    """Everything the intake tools need from one .eml file."""

    def __init__(self):
        self.path = None
        self.info = {}
        self.attachments = []
        self.new_body = ""
        self.full_body = ""
        self.date = None
        self.sha256 = ""
        self.size = 0
        self.from_name = ""
        self.from_addr = ""
        self.direction = "in"
        self.internal = False
        self.subject = ""
        self.message_id = ""
        self.thread_ids = []
        self.canonical_name = ""
        self.notes = []


def _body_text(part):
    if part is None:
        return ""
    data = part.get_payload(decode=True) or b""
    text = decode_text(data, part.get_content_charset())
    if part.get_content_subtype() == "html":
        text = html_to_text(text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _get_body(msg, pref):
    try:
        return msg.get_body(preferencelist=pref)
    except Exception:
        return None


def is_email_file(path):
    return str(path).lower().endswith(".eml")


def is_msg_file(path):
    return str(path).lower().endswith(".msg")


def parse_email(path, ctx, body_chars=BODY_CHARS):
    """Parse one .eml file. Raises OSError when it cannot be read."""
    path = Path(path)
    raw = path.read_bytes()
    msg = BytesParser(policy=_policy.default).parsebytes(raw)
    p = ParsedEmail()
    p.path = path
    p.sha256 = hashlib.sha256(raw).hexdigest()
    p.size = len(raw)
    cfg = ctx.cfg

    senders = _addresses(msg, "From") or _addresses(msg, "Sender")
    sender = senders[0] if senders else {"name": "", "address": ""}
    p.from_name, p.from_addr = sender["name"], sender["address"]
    p.subject = clean(msg.get("Subject", ""))
    domain = common.email_domain(p.from_addr)
    p.direction = "out" if p.from_addr and (p.from_addr in cfg["legal_addresses"]
                                            or p.from_addr == cfg["intake_mailbox"]) else "in"
    p.internal = bool(domain) and common.domain_matches(domain, cfg["house_domains"])
    personal = domain in common.FREEMAIL_DOMAINS

    when = None
    raw_date = msg.get("Date")
    if raw_date is not None and clean(str(raw_date)):
        try:
            when = _eutils.parsedate_to_datetime(clean(str(raw_date)))
        except Exception:
            when = None
    if when is None:
        when = _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc)
        p.notes.append(NOTE_DATE_FROM_FILE)
    p.date = ctx.to_house(when)

    ids = message_ids(msg.get("Message-ID", ""))
    p.message_id = ids[0] if ids else ""
    irt = message_ids(msg.get("In-Reply-To", ""))
    refs = message_ids(msg.get("References", ""))
    p.thread_ids = [i for i in irt + refs if i != p.message_id]
    p.thread_ids = list(dict.fromkeys(p.thread_ids))

    plain = _get_body(msg, ("plain",))
    html_part = _get_body(msg, ("html",))
    text = _body_text(plain)
    if not text.strip() and html_part is not None:
        text = _body_text(html_part)
    p.full_body = text.strip("\n")
    p.new_body, quoted = strip_quoted(p.full_body)

    skip = {id(x) for x in (plain, html_part) if x is not None}
    linesep = "\r\n" if b"\r\n" in raw else "\n"
    p.attachments = _attachments(msg, skip, linesep)

    found = common.TAG_RE.findall(p.subject + "\n" + p.new_body) \
        or common.TAG_RE.findall(p.full_body)
    tags = list(dict.fromkeys(found))

    hints = []
    auto = clean(msg.get("Auto-Submitted", "")).lower()
    if (auto and auto != "no") or msg.get("X-Autoreply") is not None \
            or msg.get("X-Autorespond") is not None \
            or p.subject.lower().startswith(AUTO_REPLY_SUBJECTS):
        hints.append("auto-reply")
    if clean(msg.get("Precedence", "")).lower() in BULK_PRECEDENCE \
            or msg.get("List-Unsubscribe") is not None or msg.get("List-Id") is not None:
        hints.append("bulk")
    if any(a.kind == "calendar" for a in p.attachments):
        hints.append("calendar")
    body_len = len(p.new_body.strip())
    if body_len < EMPTY_BODY_CHARS and not any(a.kind in ("document", "email") for a in p.attachments):
        hints.append("empty-body")
    if p.attachments and all(a.kind in ("image", "signature-image") for a in p.attachments) \
            and body_len < LOGO_ONLY_BODY_CHARS:
        hints.append("logo-only")

    p.canonical_name = canonical_name(p.date, p.direction, p.from_addr, p.subject)
    total = len(p.new_body)
    if body_chars is not None and total > body_chars:
        body = p.new_body[:max(0, body_chars)].rstrip() + "\n[... %d more characters]" % (total - max(0, body_chars))
    else:
        body = p.new_body

    p.info = {
        "file": ctx.rel(path),
        "canonical_name": p.canonical_name,
        "direction": p.direction,
        "internal": p.internal,
        "personal_address": personal,
        "date": p.date.strftime("%Y-%m-%d %H:%M"),
        "from": {"name": p.from_name, "address": p.from_addr},
        "to": _addresses(msg, "To"),
        "cc": _addresses(msg, "Cc"),
        "subject": p.subject,
        "message_id": p.message_id,
        "in_reply_to": irt[0] if irt else "",
        "references": refs,
        "tags": tags,
        "noise_hints": hints,
        "notes": list(p.notes),
        "sha256": p.sha256,
        "size": p.size,
        "attachments": [a.public() for a in p.attachments],
        "body_chars_total": total,
        "quoted_chars": quoted,
        "body": body,
    }
    return p

# ---------------------------------------------------------------- signals


def _matter_meta(d):
    try:
        meta, _ = common.read_frontmatter_file(d / "matter.md")
    except OSError:
        meta = {}
    return meta


def _matter_ref(d):
    m = common.MATTER_DIR_RE.match(d.name)
    return m.group(1) if m else ""


def _in_skipped_dir(root, d):
    parts = Path(common.rel(d, root)).parts
    return "history" in parts or "work-product" in parts


def message_id_index(root):
    """{message_id: [matter folder, ...]} from the message_id column of every areas/**/documents.md."""
    idx = {}
    areas = Path(root) / "areas"
    if not areas.is_dir():
        return idx
    for doc in sorted(areas.rglob("documents.md")):
        d = doc.parent
        if _in_skipped_dir(root, d) or not (d / "matter.md").exists():
            continue
        for rec in common.read_pipe_records(doc, common.DOCUMENTS_COLUMNS):
            mid = strip_brackets(rec.get("message_id", ""))
            if mid:
                folders = idx.setdefault(mid, [])
                if d not in folders:
                    folders.append(d)
    return idx


def roster_people(matter_dir):
    """[(normalised name, {aliases})] from roster.confirmed.md and roster.md."""
    people = []
    for fname in ("roster.confirmed.md", "roster.md"):
        for rec in common.read_pipe_records(Path(matter_dir) / fname, common.ROSTER_COLUMNS):
            aliases = set()
            for a in rec.get("aliases", "").split(";"):
                a = a.strip().strip("<>").lower()
                if a.startswith("mailto:"):
                    a = a[7:]
                if a:
                    aliases.add(a)
            people.append((norm_name(rec.get("name", "")), aliases))
    return people


def sender_check(matter_dir, name, address, internal):
    """internal | roster-address | roster-name-freemail | roster-name-other-domain | not-on-roster."""
    if internal:
        return "internal"
    people = roster_people(matter_dir)
    addr = (address or "").lower()
    if addr and any(addr in aliases for _, aliases in people):
        return "roster-address"
    n = norm_name(name)
    if n and any(n == pn for pn, _ in people if pn):
        if common.email_domain(addr) in common.FREEMAIL_DOMAINS:
            return "roster-name-freemail"
        return "roster-name-other-domain"
    return "not-on-roster"


def signals(p, ctx, index=None):
    """thread_matches, tag_matches and already_filed for one parsed email."""
    root = ctx.root
    if index is None:
        index = message_id_index(root)
    thread = {}
    for mid in p.thread_ids:
        for d in index.get(mid, []):
            thread.setdefault(d, []).append(mid)
    thread_matches = []
    for d, mids in thread.items():
        thread_matches.append({"folder": ctx.rel(d), "reference": _matter_ref(d),
                               "status": _matter_meta(d).get("status", ""), "matched_ids": mids})
    tag_matches = []
    for tag in p.info.get("tags", []):
        d = common.find_matter(root, tag)
        if d is None:
            tag_matches.append({"tag": tag, "found": False, "folder": "", "status": "",
                                "sender_check": "internal" if p.internal else "not-on-roster"})
            continue
        tag_matches.append({"tag": tag, "found": True, "folder": ctx.rel(d),
                            "status": _matter_meta(d).get("status", ""),
                            "sender_check": sender_check(d, p.from_name, p.from_addr, p.internal)})
    already = []
    for d in index.get(p.message_id, []) if p.message_id else []:
        already.append({"folder": ctx.rel(d), "reference": _matter_ref(d),
                        "status": _matter_meta(d).get("status", "")})
    return {"thread_matches": thread_matches, "tag_matches": tag_matches, "already_filed": already}
