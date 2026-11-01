"""Temporary workspaces for the tools-index tests (not a test module itself).

Workspace() copies ROOT/tools and ROOT/skills into a temp dir, writes RULES.md and the
house files (spec B, invented demo company), and offers helpers to add matters (from the
matter-memory templates), noise rows and please-check notes. Tools run with INTAKE_ROOT set.
"""

import csv
import fnmatch
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import common  # noqa: E402

TEMPLATES = ROOT / "skills" / "operations" / "matter-memory" / "templates"

BRIEF = """---
status: ready
organisation: Kestrel Engineering
legal_entities: Kestrel Engineering Ltd, Kestrel Pumpen GmbH
house_domains: kestrel-eng.co.uk, kestrel-eng.de
legal_addresses: alex.morgan@kestrel-eng.co.uk, legal@kestrel-eng.co.uk
intake_mailbox: legal@kestrel-eng.co.uk
timezone: Europe/London
reference_prefix:
lawyer_name: Alex Morgan
---
# House brief (test)
"""

AREAS = """---
status: ready
---
# Areas (test)

## commercial
- key: commercial
- name: Commercial
- code: COM
- unit_label: matter
- description: Customer, supplier and partner contracts and questions.
- sub_areas: customers, suppliers, partners, internal
- subject_rule: counterparty company, slug of its short name (acme-automotive)
- examples: NDA review; MSA negotiation

## trade-compliance
- key: trade-compliance
- name: Trade compliance
- code: TRC
- unit_label: matter
- description: Export control, sanctions and customs.
- sub_areas: exports, sanctions, customs
- subject_rule: product or destination
- examples: dual-use query

## corporate
- key: corporate
- name: Corporate
- code: COR
- unit_label: matter
- description: Entities, signing authority, board matters.
- sub_areas: none
- subject_rule: topic
- examples: power of attorney

## general
- key: general
- name: General
- code: GEN
- unit_label: matter
- description: Anything that fits no other area.
- sub_areas: none
- subject_rule: unfiled
- examples: misdirected mail
"""


class Workspace:
    def __init__(self, tools=True, skills=True, house=True):
        self.tmp = Path(tempfile.mkdtemp(prefix="intake-test-"))
        self.root = self.tmp / "ws"
        self.root.mkdir()
        (self.root / "RULES.md").write_text("# Rules (test)\n", encoding="utf-8")
        if tools:
            shutil.copytree(str(ROOT / "tools"), str(self.root / "tools"),
                            ignore=shutil.ignore_patterns("__pycache__", "tests"))
        if skills:
            shutil.copytree(str(ROOT / "skills"), str(self.root / "skills"),
                            ignore=shutil.ignore_patterns("__pycache__"))
        if house:
            (self.root / "house").mkdir()
            (self.root / "house" / "brief.md").write_text(BRIEF, encoding="utf-8")
            (self.root / "house" / "areas.md").write_text(AREAS, encoding="utf-8")
        for d in ("areas", "inbox/noise/confirmed", "inbox/please-check", "changes", "digests"):
            (self.root / d).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ running tools

    def env(self, **extra):
        e = dict(os.environ)
        e["INTAKE_ROOT"] = str(self.root)
        e.update(extra)
        return e

    def run(self, tool, *args, env=None, cwd=None, input=None):
        return subprocess.run(["bash", str(self.root / "tools" / tool)] + [str(a) for a in args],
                              cwd=str(cwd or self.root), env=env or self.env(), input=input,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, encoding="utf-8")

    def cleanup(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    # ------------------------------------------------------------ files

    def path(self, relp):
        return self.root / relp

    def write(self, relp, text, binary=False):
        p = self.root / relp
        p.parent.mkdir(parents=True, exist_ok=True)
        if binary:
            p.write_bytes(text)
        else:
            with open(str(p), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        return p

    def read(self, relp):
        return common.read_text(self.root / relp)

    def meta(self, folder):
        meta, _ = common.read_frontmatter_file(Path(self.root / folder) / "matter.md")
        return meta

    # ------------------------------------------------------------ matters

    def make_matter(self, ref, area, subject, topic, sub_area="", **meta):
        """Create a matter folder from the templates; meta keys override the frontmatter."""
        subj_dir = self.root / "areas" / area / sub_area / subject if sub_area else self.root / "areas" / area / subject
        mdir = subj_dir / ("%s_%s_%s" % (ref, subject, topic))
        for d in common.MATTER_DIRS:
            (mdir / d).mkdir(parents=True, exist_ok=True)
        title = meta.pop("title", "Test matter %s" % ref)
        opened = meta.pop("opened", "2026-10-20")
        fill = {"{{reference}}": ref, "{{area}}": area, "{{sub_area}}": sub_area,
                "{{subject}}": subject, "{{title}}": title, "{{opened}}": opened,
                "{{follows}}": meta.pop("follows", ""),
                "{{subject_name}}": subject.replace("-", " ").title(), "{{created}}": opened}
        for name in common.MATTER_FILES:
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            for k, v in fill.items():
                text = text.replace(k, v)
            (mdir / name).write_text(text, encoding="utf-8")
        if not (subj_dir / "subject.md").exists():
            text = (TEMPLATES / "subject.md").read_text(encoding="utf-8")
            for k, v in fill.items():
                text = text.replace(k, v)
            (subj_dir / "subject.md").write_text(text, encoding="utf-8")
        if meta:
            common.update_frontmatter_file(mdir / "matter.md", meta, history=False)
        return mdir

    def rel(self, p):
        return common.rel(p, self.root)

    # ------------------------------------------------------------ noise and please-check

    def add_noise(self, nid, name, received, title, label, status="waiting_lawyer",
                  confirmed_outcome="", confirmed_by="", path_in_file=True, sender="news@example.org"):
        """Add a noise email and its NOISE.csv row, written as place-email writes it (BOM, CRLF,
        file = workspace path). path_in_file=False stores the bare file name instead."""
        noise_dir = self.root / "inbox" / "noise"
        where = noise_dir / "confirmed" if status == "closed" else noise_dir
        (where / name).write_text("From: %s\nSubject: %s\n\nbody\n" % (sender, title), encoding="utf-8")
        csv_path = noise_dir / "NOISE.csv"
        rows = []
        if csv_path.exists():
            rows = list(csv.DictReader(io.StringIO(common.read_text(csv_path))))
        rows.append({"id": nid, "file": common.rel(where / name, self.root) if path_in_file else name,
                     "received": received, "from": sender, "subject": title, "title": title,
                     "label": label, "status": status, "proposed_outcome": "nothing_needed",
                     "confirmed_outcome": confirmed_outcome, "confirmed_by": confirmed_by})
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=common.NOISE_COLUMNS, lineterminator="\r\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        csv_path.write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))
        return where / name

    def add_note(self, name, reason, **meta):
        fm = {"file": name, "received": "2026-10-21 16:05", "from": "j.schmidt@acme-automotive.de",
              "subject": "Quick question", "claimed_reference": "", "candidates": "", "run": "2026-10-21_170000"}
        fm.update(meta)
        body = "\n## Why the agent is unsure\n%s\n\n## What it would do\nFile it into the first candidate.\n" % reason
        self.write("inbox/please-check/%s.note.md" % name, common.render_frontmatter(fm, body))
        self.write("inbox/please-check/%s" % name, "From: x\n\nbody\n")


def read_index(ws):
    return list(csv.DictReader(io.StringIO(common.read_text(ws.root / "INDEX.csv"))))


def write_index_rows(ws, rows, columns=None):
    """Write INDEX.csv as the human's Excel would (UTF-8 BOM, CRLF)."""
    columns = columns or common.INDEX_COLUMNS
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    (ws.root / "INDEX.csv").write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))


def make_bin(dest, hide=(), extra=None):
    """A folder to use as PATH: links to every command on PATH except names matching `hide`
    (fnmatch patterns), plus `extra` scripts {name: text}. Lets a test hide Python or a tool."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d or not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if any(fnmatch.fnmatch(name, pat) for pat in hide) or os.path.lexists(str(dest / name)):
                continue
            src = os.path.join(d, name)
            if os.path.isfile(src) and os.access(src, os.X_OK):
                os.symlink(src, str(dest / name))
    for name, text in (extra or {}).items():
        target = dest / name
        if os.path.lexists(str(target)):
            target.unlink()
        target.write_text(text, encoding="utf-8")
        target.chmod(0o755)
    return dest
