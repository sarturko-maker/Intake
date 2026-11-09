"""area-lines: print only the lines of an area's playbook.md and intake.md (and a subject.md) that match
a pattern, each with the heading it sits under, so a reader can look up one point (a signatory, a letter of
authority, a sum) without reading whole files.

Run through the wrapper: bash tools/area-lines AREA PATTERN [--subject SLUG] [--after N]
PATTERN is a regular expression, case-insensitive ("signatory|LOA"). Exit 0 a match, 1 no match, 2 usage.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def search(path, rx, after):
    """[(line number, heading path, text, is_heading)] for the matching lines of one file, each followed by up
    to `after` lines of the same paragraph (a blank line or a heading ends it)."""
    hits, trail = [], []
    lines = common.read_text(path).splitlines()
    remaining = 0
    for n, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h:
            level = len(h.group(1))
            trail = [t for t in trail if t[0] < level] + [(level, h.group(2))]
        where = " > ".join(t[1] for t in trail)
        if rx.search(line):
            hits.append((n, where, line.rstrip(), bool(h)))
            remaining = after
        elif remaining and line.strip() and not h:
            hits.append((n, where, line.rstrip(), False))
            remaining -= 1
        else:
            remaining = 0
    return hits, [t[1] for t in trail]


def headings(path):
    return [m.group(2) for m in (HEADING.match(l) for l in common.read_text(path).splitlines()) if m]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/area-lines",
                                 description="Matching lines of an area's playbook.md and intake.md, with their headings.")
    ap.add_argument("area")
    ap.add_argument("pattern", help="regular expression, case-insensitive")
    ap.add_argument("--subject", metavar="SLUG", help="also search that subject's subject.md in the area")
    ap.add_argument("--after", type=int, default=2, metavar="N", help="lines of the same paragraph to show after each match (2)")
    ap.add_argument("--run", metavar="RUN", help="the run id; every tool accepts it (not used here)")
    a = ap.parse_args(argv)
    root = common.find_root()
    area = Path(root) / "areas" / a.area
    if not area.is_dir():
        common.die("area-lines: no area %s under areas/" % a.area, 2)
    try:
        rx = re.compile(a.pattern, re.I)
    except re.error as exc:
        common.die("area-lines: bad pattern: %s" % exc, 2)
    files = [area / "playbook.md", area / "intake.md"]
    if a.subject:
        found = sorted(p for p in area.rglob("subject.md") if p.parent.name == a.subject
                       and "history" not in p.parts)
        if not found:
            common.die("area-lines: no subject %s in areas/%s" % (a.subject, a.area), 2)
        files += found[:1]
    any_hit = False
    for f in files:
        if not f.is_file():
            continue
        hits, _ = search(f, rx, max(0, a.after))
        rel = common.rel(f, root)
        if not hits:
            print("%s: no match. Headings: %s" % (rel, "; ".join(headings(f)) or "none"))
            continue
        any_hit = True
        print("== %s" % rel)
        for n, where, text, is_heading in hits:
            print("%d [%s] %s" % (n, where or "top", text.strip()))
    return 0 if any_hit else 1


if __name__ == "__main__":
    sys.exit(main())
