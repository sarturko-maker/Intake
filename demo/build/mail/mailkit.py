"""MIME building for the demo emails.

- Deterministic bytes: fixed boundaries, fixed Date seconds, CRLF line endings.
- Headers in a realistic order; Message-ID, In-Reply-To and References by the spec G rule
  <{id}.{YYYYMMDDHHMM local}@{sender domain}>.
- Replies quote earlier mails ('On ... wrote:', 'Am ... schrieb ...:'), forwards carry the
  original (English Outlook block, or German '-----Ursprungliche Nachricht-----' block).
- Emails that carry a {{REF:Gxx}} placeholder are 7bit US-ASCII in every text part, so
  drop-batch can replace the bytes exactly. Others are US-ASCII when they can be, else UTF-8
  quoted-printable.
- Batch file names follow Outlook drag and drop: subject without the [{{REF:..}}]
  placeholder, without \\ / : * ? " < > |, spaces collapsed, plus .eml.

Dev tool. Python 3.9+ standard library.
"""

import datetime as dt
import email.charset
import html
import io
import re
from email import encoders
from email.generator import BytesGenerator
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.policy import compat32
from email.utils import format_datetime
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")
DE = ZoneInfo("Europe/Berlin")
PLACEHOLDER_RE = re.compile(r"\{\{REF:G\d\d\}\}")
BAD_NAME_CHARS = '\\/:*?"<>|'
DE_DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
DE_MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
             "September", "Oktober", "November", "Dezember"]

_UTF8_QP = email.charset.Charset("utf-8")
_UTF8_QP.header_encoding = email.charset.QP
_UTF8_QP.body_encoding = email.charset.QP

POLICY = compat32.clone(linesep="\r\n", max_line_length=998)


def addr(person):
    """'Name <address>' or a bare address."""
    name, address = person
    if not name:
        return address
    if any(c in name for c in ',;:"()<>@[]'):
        name = '"%s"' % name.replace('"', '\\"')
    return "%s <%s>" % (name, address)


def domain_of(address):
    return address.rsplit("@", 1)[1].lower()


def message_id(mail_id, when, address):
    return "<%s.%s@%s>" % (mail_id, when.strftime("%Y%m%d%H%M"), domain_of(address))


def outlook_file_name(subject):
    """File name Outlook gives on drag and drop (spec G rule), without the ' (2)' suffix."""
    s = re.sub(r"\[\{\{REF:G\d\d\}\}\]", " ", subject or "")
    s = "".join(c for c in s if c not in BAD_NAME_CHARS)
    s = re.sub(r"\s+", " ", s).strip()
    return (s or "(no subject)") + ".eml"


class Mail:
    """One email of the corpus (or a mail that exists only as quoted text)."""

    def __init__(self, mail_id, when, frm, to, subject, body, cc=None, quote=None,
                 quote_style=None, html_alt=False, logo=None, logo_cid=None,
                 logo_layout="related-outer", attachments=None, in_reply_to=None,
                 references=None, extra_headers=None, calendar=None, from_header=None,
                 quote_zone=None, batch=None, html_note=None):
        self.id = mail_id
        self.when = when
        self.frm = frm
        self.to = to
        self.cc = cc or []
        self.subject = subject
        self.body = body.strip("\n")
        self.quote = quote
        self.quote_style = quote_style
        self.html_alt = html_alt
        self.logo = logo
        self.logo_cid = logo_cid
        self.logo_layout = logo_layout
        self.attachments = attachments or []
        self.in_reply_to = in_reply_to or []
        self.references = references or []
        self.extra_headers = extra_headers or []
        self.calendar = calendar
        self.from_header = from_header
        self.quote_zone = quote_zone or (DE if domain_of(frm[1]).endswith(".de") else UK)
        self.batch = batch
        self.html_note = html_note

    # ---------------------------------------------------------------- identity

    @property
    def message_id(self):
        return message_id(self.id, self.when, self.frm[1])

    @property
    def message_id_bare(self):
        return self.message_id.strip("<>")

    def seconds(self):
        return (sum(ord(c) for c in self.id) * 7) % 60

    def date_header(self):
        return format_datetime(self.when.replace(second=self.seconds()))

    # ---------------------------------------------------------------- text

    def full_text(self):
        """New text plus the quoted or forwarded history, as the plain-text part shows it."""
        if not self.quote:
            return self.body + "\n"
        return self.body + "\n\n" + self.quote_block() + "\n"

    def quote_block(self):
        q = self.quote
        local = q.when.astimezone(self.quote_zone)
        original = q.full_text().rstrip("\n")
        if self.quote_style == "on":
            head = "On %s at %s, %s <%s> wrote:" % (local.strftime("%a, %d %b %Y"),
                                                    local.strftime("%H:%M"), q.frm[0], q.frm[1])
            return head + "\n" + prefix_lines(original)
        if self.quote_style == "am":
            head = "Am %s um %s schrieb %s <%s>:" % (local.strftime("%d.%m.%Y"),
                                                     local.strftime("%H:%M"), q.frm[0], q.frm[1])
            return head + "\n" + prefix_lines(original)
        if self.quote_style == "fwd-outlook":
            lines = ["________________________________",
                     "From: %s <%s>" % (q.frm[0], q.frm[1]),
                     "Sent: %s" % local.strftime("%d %B %Y %H:%M").lstrip("0"),
                     "To: %s" % "; ".join(addr(p) for p in q.to)]
            if q.cc:
                lines.append("Cc: %s" % "; ".join(addr(p) for p in q.cc))
            lines.append("Subject: %s" % q.subject)
            return "\n".join(lines) + "\n\n" + original
        if self.quote_style == "fwd-de":
            when = "%s, %d. %s %d %s" % (DE_DAYS[local.weekday()], local.day,
                                         DE_MONTHS[local.month - 1], local.year,
                                         local.strftime("%H:%M"))
            lines = ["-----Ursprüngliche Nachricht-----",
                     "Von: %s <%s>" % (q.frm[0], q.frm[1]),
                     "Gesendet: %s" % when,
                     "An: %s" % "; ".join(addr(p) for p in q.to)]
            if q.cc:
                lines.append("Cc: %s" % "; ".join(addr(p) for p in q.cc))
            lines.append("Betreff: %s" % q.subject)
            return "\n".join(lines) + "\n\n" + original
        raise ValueError("unknown quote style %r" % self.quote_style)

    # ---------------------------------------------------------------- html

    def html_content(self, with_logo=True):
        """HTML alternative: the new text as paragraphs, the logo in the signature, and the
        history in a blockquote (or after a separator for forwards)."""
        blocks = re.split(r"\n\s*\n", self.body.strip("\n"))
        footer = []
        if with_logo and self.logo and len(blocks) > 1 and " | Registered office" in blocks[-1]:
            footer = [blocks.pop()]  # the logo sits in the signature, above the legal footer
        parts = [paragraphs_html("\n\n".join(blocks))]
        if with_logo and self.logo:
            parts.append('<p><img src="cid:%s" width="160" height="40" alt="%s"></p>'
                         % (self.logo_cid.strip("<>"), html.escape(self.html_note or "logo")))
        if footer:
            parts.append(paragraphs_html(footer[0]))
        if self.quote:
            q = self.quote
            local = q.when.astimezone(self.quote_zone)
            head = None
            if self.quote_style == "on":
                head = "On %s at %s, %s &lt;%s&gt; wrote:" % (
                    local.strftime("%a, %d %b %Y"), local.strftime("%H:%M"),
                    html.escape(q.frm[0]), q.frm[1])
            elif self.quote_style == "am":
                head = "Am %s um %s schrieb %s &lt;%s&gt;:" % (
                    local.strftime("%d.%m.%Y"), local.strftime("%H:%M"),
                    html.escape(q.frm[0]), q.frm[1])
            if head:
                parts.append("<div>%s</div>" % head)
                parts.append('<blockquote style="margin:0 0 0 .8ex;border-left:1px solid #ccc;'
                             'padding-left:1ex">\n%s\n</blockquote>' % q.html_content(False))
            else:
                parts.append("<hr>\n" + paragraphs_html(self.quote_block()))
        return "\n".join(parts)

    def html_document(self, charset):
        body = self.html_content()
        doc = ('<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html; '
               'charset=%s">\n</head>\n<body style="font-family:Arial,sans-serif;font-size:10pt">'
               '\n%s\n</body>\n</html>\n' % (charset, body))
        return wrap_long_lines(doc)

    # ---------------------------------------------------------------- MIME

    def needs_ascii(self):
        return bool(PLACEHOLDER_RE.search(self.subject) or PLACEHOLDER_RE.search(self.full_text()))

    def _text_part(self, text, subtype):
        if text.isascii():
            return MIMEText(text, subtype, "us-ascii")
        if self.needs_ascii():
            bad = sorted({c for c in text if not c.isascii()})
            raise ValueError("%s carries a placeholder but has non-ASCII text: %r" % (self.id, bad))
        return MIMEText(text, subtype, _UTF8_QP)

    def to_bytes(self):
        tag = self.id.replace("-", "")
        text = self.full_text()
        alt_parts = [self._text_part(text, "plain")]
        html_part = None
        if self.html_alt:
            charset = "us-ascii" if (text.isascii() and self.html_document("x").isascii()) \
                else "utf-8"
            html_part = self._text_part(self.html_document(charset), "html")
        cal_part = None
        if self.calendar:
            cal_part = MIMEText(self.calendar, "calendar", "us-ascii" if self.calendar.isascii()
                                else _UTF8_QP)
            cal_part.replace_header("Content-Type", cal_part["Content-Type"] + "; method=REQUEST")
        logo_part = None
        if self.logo:
            logo_part = MIMEImage(self.logo, "png", name=self.logo_name())
            logo_part.add_header("Content-ID", self.logo_cid)
            logo_part.add_header("Content-Disposition", "inline", filename=self.logo_name())

        if self.logo and self.logo_layout == "related-inner":
            # text/plain beside an HTML-with-image block (newsletter-style mailers)
            related = MIMEMultipart("related", boundary="----=_Rel_%s_02" % tag)
            related.attach(html_part)
            related.attach(logo_part)
            body = MIMEMultipart("alternative", boundary="----=_Alt_%s_01" % tag)
            body.attach(alt_parts[0])
            body.attach(related)
        else:
            if html_part is not None:
                alt_parts.append(html_part)
            if cal_part is not None:
                alt_parts.append(cal_part)
            if len(alt_parts) == 1:
                body = alt_parts[0]
            else:
                body = MIMEMultipart("alternative", boundary="----=_Alt_%s_01" % tag)
                for p in alt_parts:
                    body.attach(p)
            if self.logo:
                related = MIMEMultipart("related", type="multipart/alternative",
                                        boundary="----=_Rel_%s_02" % tag)
                related.attach(body)
                related.attach(logo_part)
                body = related
        root = body
        if self.attachments:
            root = MIMEMultipart("mixed", boundary="----=_Mix_%s_00" % tag)
            root.attach(body)
            for name, data, ctype in self.attachments:
                maintype, subtype = ctype.split("/", 1)
                part = MIMEBase(maintype, subtype, name=name)
                part.set_payload(data)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=name)
                root.attach(part)
        for part in root.walk():
            if part is not root and "MIME-Version" in part:
                del part["MIME-Version"]
        mime_headers = [(k, v) for k, v in root._headers
                        if k.lower() in ("content-type", "content-transfer-encoding")]
        root._headers = []
        root["From"] = self.from_header or addr(self.frm)
        root["To"] = ", ".join(addr(p) for p in self.to)
        if self.cc:
            root["Cc"] = ", ".join(addr(p) for p in self.cc)
        root["Subject"] = self.subject
        root["Date"] = self.date_header()
        root["Message-ID"] = self.message_id
        if self.in_reply_to:
            root["In-Reply-To"] = " ".join(self.in_reply_to)
        if self.references:
            root["References"] = " ".join(self.references)
        for k, v in self.extra_headers:
            root[k] = v
        root["MIME-Version"] = "1.0"
        for k, v in mime_headers:
            root[k] = v
        buf = io.BytesIO()
        BytesGenerator(buf, mangle_from_=False, policy=POLICY).flatten(root)
        data = buf.getvalue()
        if self.needs_ascii():
            assert data.isascii(), self.id
            # every placeholder must survive intact (no folding or encoding inside it)
            assert data.count(b"{{REF:") == len(re.findall(rb"\{\{REF:G\d\d\}\}", data)), self.id
        return data

    def logo_name(self):
        return "image001.png" if "image001" in (self.logo_cid or "") else "logo.png"


def prefix_lines(text):
    return "\n".join(("> " + line) if line else ">" for line in text.split("\n"))


def paragraphs_html(text):
    out = []
    for block in re.split(r"\n\s*\n", text.strip("\n")):
        lines = [html.escape(line, quote=False) for line in block.split("\n")]
        out.append("<p>%s</p>" % "<br>\n".join(lines))
    return "\n".join(out)


def wrap_long_lines(doc, limit=76):
    """Break long HTML source lines at spaces so every line stays well under 998 bytes."""
    out = []
    for line in doc.split("\n"):
        while len(line) > limit:
            cut = line.rfind(" ", 0, limit)
            if cut <= 0:
                cut = line.find(" ", limit)
                if cut == -1:
                    break
            out.append(line[:cut])
            line = line[cut + 1:]
        out.append(line)
    return "\n".join(out)


def local(zone, y, mo, d, h, mi):
    """An aware local time."""
    return dt.datetime(y, mo, d, h, mi, tzinfo=zone)
