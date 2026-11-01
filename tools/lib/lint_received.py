"""lint-received: recompute sha256 of received files and compare with documents.md.

Run through the wrapper: bash tools/lint-received [MATTER_FOLDER|REF ...]   (default: every matter)
For every documents.md row whose folder is correspondence or documents/received, the file's
sha256 is recomputed and compared. Reports changed files, missing files, rows without a hash,
and files in those folders that have no row. Exit 0 clean, 1 findings, 2 usage error.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

CHECKED_FOLDERS = ("correspondence", "documents/received")
JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", ".gitkeep"}
# Rows place-email records without storing a file (spec D3).
NOT_STORED_READ = ("no: signature", "no: calendar")


def is_junk(name):
    return (name in JUNK_NAMES or name.startswith("~$") or name.startswith(".~lock")
            or name.lower().endswith(".tmp"))


def not_stored(row):
    return row.get("read", "").strip().lower().startswith(NOT_STORED_READ)


def resolve_matter(root, arg):
    if common.REF_RE.match(arg):
        d = common.find_matter(root, arg)
        if d is None:
            common.die("lint-received: no matter with reference %s under areas/" % arg, 2)
        return d
    p = Path(arg)
    cands = [p] if p.is_absolute() else [Path.cwd() / p, root / p]
    for c in cands:
        if (c / "matter.md").is_file():
            return c.resolve()
    common.die("lint-received: not a matter folder (no matter.md): %s" % arg, 2)


def lint_matter(root, mdir):
    """Return (findings, files_checked)."""
    findings = []
    checked = 0
    docs = mdir / "documents.md"
    rows = common.read_pipe_records(docs, common.DOCUMENTS_COLUMNS)
    expected = {}
    for r in rows:
        folder = r.get("folder", "").strip().strip("/")
        if folder not in CHECKED_FOLDERS:
            continue
        name = r.get("name", "").strip()
        if not name:
            findings.append("bad row: %s line %d has no name" % (common.rel(docs, root), r["_line"]))
            continue
        expected.setdefault(folder + "/" + name, []).append(r)

    for relp in sorted(expected):
        path = mdir / relp
        shown = common.rel(path, root)
        rs = expected[relp]
        if path.is_file():
            checked += 1
            actual = common.sha256_file(path)
            for r in rs:
                want = r.get("hash", "").strip().lower()
                if not want:
                    findings.append("no hash: %s (documents.md line %d records no sha256)" % (shown, r["_line"]))
                elif want != actual:
                    findings.append("changed: %s (sha256 differs from documents.md line %d)" % (shown, r["_line"]))
        elif not all(not_stored(r) or r.get("duplicate_of", "").strip() for r in rs):
            first = [r for r in rs if not (not_stored(r) or r.get("duplicate_of", "").strip())][0]
            findings.append("missing: %s (documents.md line %d, file not found)" % (shown, first["_line"]))

    for folder in CHECKED_FOLDERS:
        d = mdir / folder
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if not f.is_file() or is_junk(f.name):
                continue
            relp = f.relative_to(mdir).as_posix()
            if relp in expected:
                continue
            # The original .msg of a converted email moves beside its .eml (spec D3).
            if f.suffix.lower() == ".msg" and (relp[:-4] + ".eml") in expected:
                continue
            findings.append("no row: %s (not in documents.md)" % common.rel(f, root))
    return findings, checked


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/lint-received",
                                 description="Recompute hashes of received files and compare with documents.md.")
    ap.add_argument("matters", nargs="*", metavar="MATTER_FOLDER")
    a = ap.parse_args(argv)
    root = common.find_root()
    if a.matters:
        mdirs = [resolve_matter(root, m) for m in a.matters]
    else:
        mdirs = list(common.iter_matter_dirs(root))
    findings = []
    checked = 0
    for m in mdirs:
        f, c = lint_matter(root, m)
        findings.extend(f)
        checked += c
    for line in findings:
        print(line)
    print("lint-received: %d files checked in %d matters, %d findings" % (checked, len(mdirs), len(findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
