"""Shared helpers for demo/scripts (setup, drop-batch, check-filing). Python 3.8+, standard library.

The scripts sit in <repo>/demo/scripts/ and, after setup, in <workspace>/demo/scripts/ too.
They read demo/expected.csv and demo/batches/ next to themselves, and use tools/lib/common.py
from the same tree for matter-folder rules.
"""

import csv
import datetime as dt
import io
import re
import sys
from email import policy as _policy
from email.parser import BytesHeaderParser
from email.utils import parsedate_to_datetime
from pathlib import Path

LIB = Path(__file__).resolve().parent
DEMO = LIB.parents[1]                       # .../demo
SRC_ROOT = DEMO.parent                      # the repository (or workspace) holding these scripts
sys.path.insert(0, str(SRC_ROOT / "tools" / "lib"))

import common  # noqa: E402

EXPECTED = DEMO / "expected.csv"
BATCHES = DEMO / "batches"
MARKER = Path("demo") / ".demo-workspace"
PLACEHOLDER_RE = re.compile(rb"\{\{REF:(G\d\d)\}\}")
JUNK = {".gitkeep", ".DS_Store", "Thumbs.db", "desktop.ini"}


def die(msg, code=2):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def alts(value):
    """'a|b' -> ['a', 'b']; '' -> [''] (meaning: must be empty)."""
    value = (value or "").strip()
    if not value:
        return [""]
    return [v.strip() for v in value.split("|")]


def load_expected(path=EXPECTED):
    if not path.exists():
        die("missing %s" % path)
    text = path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    for r in rows:
        for k in list(r):
            r[k] = (r[k] or "").strip()
    return rows


def resolve_workspace(arg):
    """The demo workspace: --workspace DIR, else the tree these scripts sit in, if setup made it."""
    if arg:
        ws = Path(arg).expanduser().resolve()
        if not ws.is_dir():
            die("no such folder: %s" % ws)
        if not (ws / "inbox").is_dir():
            die("%s does not look like a workspace (no inbox/ folder). Run demo/scripts/setup "
                "first." % ws)
        return ws
    if (SRC_ROOT / MARKER).exists():
        return SRC_ROOT
    nested = sorted(p.parent.parent for p in (SRC_ROOT / "demo").glob("workspace*/" + MARKER.as_posix()))
    if len(nested) == 1:
        return nested[0]
    die("Which workspace? Give --workspace DIR (the folder made by demo/scripts/setup), or run "
        "this script from inside that folder.")


def header_info(path):
    """(message_id without brackets, aware Date or None, subject) from an .eml's headers."""
    try:
        with open(path, "rb") as fh:
            msg = BytesHeaderParser(policy=_policy.default).parse(fh)
    except OSError:
        return "", None, ""
    raw_id = str(msg.get("Message-ID", "") or "")
    m = re.search(r"<([^<>\s]+)>", raw_id)
    mid = m.group(1) if m else raw_id.strip().strip("<>")
    when = None
    try:
        if msg.get("Date"):
            when = parsedate_to_datetime(str(msg.get("Date")))
            if when is not None and when.tzinfo is None:
                when = when.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        when = None
    return mid, when, str(msg.get("Subject", "") or "")


class Loc:
    """Where an email sits in the workspace."""

    def __init__(self, kind, path, ws):
        self.kind = kind                      # matter | noise | please-check | inbox
        self.path = path
        self.ws = ws
        self.rel = common.rel(path, ws)
        self.folder = None
        self.ref = ""
        self.area = self.sub_area = self.subject = ""
        self.resolved_dir = False
        if kind == "matter":
            self.folder = path.parent.parent
            m = common.MATTER_DIR_RE.match(self.folder.name)
            self.ref = m.group(1) if m else ""
            self.area, self.sub_area, self.subject = common.matter_location(ws, self.folder)
        self.message_id, self.date, self.subject_line = header_info(path)

    def where(self):
        """The matter folder for a filed email, else the file itself (workspace-relative)."""
        if self.kind == "matter":
            return common.rel(self.folder, self.ws)
        return self.rel


def iter_emails(ws):
    """Every .eml the checks look at, as Loc objects."""
    areas = ws / "areas"
    if areas.is_dir():
        for p in sorted(areas.rglob("*.eml")):
            parts = p.relative_to(ws).parts
            if p.parent.name != "correspondence" or "work-product" in parts or "history" in parts:
                continue
            yield Loc("matter", p, ws)
    inbox = ws / "inbox"
    for sub, kind in (("noise", "noise"), ("noise/confirmed", "noise"),
                      ("please-check", "please-check"), ("please-check/resolved", "please-check")):
        d = inbox / sub
        if d.is_dir():
            for p in sorted(d.glob("*.eml")):
                loc = Loc(kind, p, ws)
                loc.resolved_dir = sub.endswith("resolved")
                yield loc
    if inbox.is_dir():
        for p in sorted(inbox.glob("*.eml")):
            yield Loc("inbox", p, ws)


def index_emails(ws):
    """{message_id: [Loc, ...]}"""
    idx = {}
    for loc in iter_emails(ws):
        if loc.message_id:
            idx.setdefault(loc.message_id, []).append(loc)
    return idx


def inbox_leftovers(ws):
    inbox = ws / "inbox"
    if not inbox.is_dir():
        return []
    return sorted(p for p in inbox.iterdir() if p.is_file() and p.name not in JUNK
                  and not p.name.startswith("."))


def id_time(message_id):
    """YYYYMMDDHHMM from a demo Message-ID (local time of the sender), for ordering."""
    m = re.match(r"^b\d-\d\d\.(\d{12})@", message_id or "")
    return m.group(1) if m else "999999999999"


def matter_meta(folder):
    try:
        meta, _ = common.read_frontmatter_file(Path(folder) / "matter.md")
    except OSError:
        meta = {}
    return meta
