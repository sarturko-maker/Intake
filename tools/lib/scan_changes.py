"""scan-changes: compare the workspace tree with MANIFEST.csv and report what changed.

Interface: tools/scan-changes (usage text) and the build spec, D1. Files are compared by
size and mtime; only candidates are hashed. A deleted path whose hash reappears at a
new path is reported as moved.
"""

import argparse
import fnmatch
import json
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402

EXCLUDED_TOP = {".git", ".claude", "tools", "demo", "phase-2", ".github", "changes", "digests", "learning"}
EXCLUDED_NAMES = {"MANIFEST.csv", "JOURNAL.md", "INDEX.md", "WORKFLOW-LOG.md", "TOOLING.md",
                  "BUDGET.md", "HANDOFF.md", "START-HERE.md"}
JUNK_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}
JUNK_PATTERNS = ("~$*", "*.tmp", ".~lock*")
GROUP_PARTS = ("inbox", "knowledge", "house", "seeds", "skills", "areas")
MANIFEST_COLUMNS = ["path", "size", "mtime", "sha256", "first_seen", "last_seen", "last_processed"]
KINDS = ("new", "modified", "touched", "moved", "deleted")


def is_junk(name):
    low = name.lower()
    return low in JUNK_NAMES or any(fnmatch.fnmatchcase(low, p) for p in JUNK_PATTERNS)


def walk(root):
    """{relative path: (size, mtime seconds, absolute path)} for every included file."""
    root = str(root)
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = "" if rel_dir == "." else rel_dir.replace(os.sep, "/")
        keep = []
        for d in dirnames:
            if rel_dir == "" and d in EXCLUDED_TOP:
                continue
            if d == "history":
                continue
            if d.endswith("_harvey-pack") or (os.path.basename(dirpath) in ("work-product", "agent") and (
                    d.startswith("bundle-") or d.startswith("."))):
                continue  # generated packs and bundles are copies
            keep.append(d)
        dirnames[:] = sorted(keep)
        for f in sorted(filenames):
            if f in EXCLUDED_NAMES or is_junk(f):
                continue
            full = os.path.join(dirpath, f)
            try:
                st = os.stat(full)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            rel = rel_dir + "/" + f if rel_dir else f
            out[rel] = (st.st_size, int(st.st_mtime), full)
    return out


def group_of(path):
    parts = path.split("/")
    for i, part in enumerate(parts[:-1]):
        if common.MATTER_DIR_RE.match(part):
            return "/".join(parts[:i + 1])
    if len(parts) > 1 and parts[0] in GROUP_PARTS:
        return parts[0]
    return "root"


def group_key(group):
    if group == "root":
        return (2, 0, group)
    if group in GROUP_PARTS:
        return (1, GROUP_PARTS.index(group), group)
    return (0, 0, group)


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def compare(root, current, manifest):
    """(entries, hashes, unreadable). manifest is {path: row} or None for a first scan."""
    old = manifest or {}
    entries = []
    hashes = {}
    unreadable = {}
    new_paths = []
    for rel in sorted(current):
        size, mtime, full = current[rel]
        row = old.get(rel)
        if row is not None and _int(row.get("size")) == size and _int(row.get("mtime")) == mtime \
                and row.get("sha256"):
            hashes[rel] = row["sha256"]
            continue
        try:
            h = common.sha256_file(full)
        except OSError as exc:
            unreadable[rel] = str(exc)
            continue
        hashes[rel] = h
        if row is None:
            new_paths.append(rel)
        elif h == row.get("sha256"):
            entries.append({"kind": "touched", "path": rel, "size": size})
        else:
            entries.append({"kind": "modified", "path": rel, "size": size})
    deleted = sorted(p for p in old if p not in current and p not in unreadable)
    by_hash = {}
    for p in new_paths:
        by_hash.setdefault(hashes[p], []).append(p)
    moved_new, moved_old = set(), set()
    for d in deleted:
        h = old[d].get("sha256", "")
        if h and by_hash.get(h):
            newp = by_hash[h].pop(0)
            moved_new.add(newp)
            moved_old.add(d)
            entries.append({"kind": "moved", "path": newp, "old_path": d, "size": current[newp][0]})
    for p in new_paths:
        if p not in moved_new:
            entries.append({"kind": "new", "path": p, "size": current[p][0]})
    for d in deleted:
        if d not in moved_old:
            entries.append({"kind": "deleted", "path": d, "size": _int(old[d].get("size")) or 0})
    return entries, hashes, unreadable


def entry_line(e):
    if e["kind"] == "moved":
        return "- moved: %s -> %s" % (e["old_path"], e["path"])
    return "- %s: %s (%d)" % (e["kind"], e["path"], e["size"])


def counts_of(entries):
    c = {k: 0 for k in KINDS}
    for e in entries:
        c[e["kind"]] += 1
    return c


def counts_text(c):
    return ", ".join("%s %d" % (k, c[k]) for k in KINDS)


def render_report(run, entries, unreadable, nfiles, first_scan):
    c = counts_of(entries)
    lines = ["# Changes %s" % run, "",
             "Scanned %d files against MANIFEST.csv: %s." % (nfiles, counts_text(c))]
    if first_scan:
        lines.append("First scan: there was no MANIFEST.csv, so every file is reported as new.")
    if not entries and not unreadable:
        lines += ["", "No changes since the last manifest."]
    groups = {}
    for e in entries:
        groups.setdefault(group_of(e["path"]), []).append(e)
    for g in sorted(groups, key=group_key):
        lines += ["", "## " + g]
        for e in sorted(groups[g], key=lambda x: (KINDS.index(x["kind"]), x["path"])):
            lines.append(entry_line(e))
    if unreadable:
        lines += ["", "## Unreadable"]
        for p in sorted(unreadable):
            lines.append("- unreadable: %s (%s)" % (p, unreadable[p]))
    return "\n".join(lines) + "\n"


def top_inbox(rel):
    return rel.startswith("inbox/") and rel.count("/") == 1


def manifest_rows(run, current, hashes, unreadable, manifest, entries):
    old = manifest or {}
    moved_from = {e["path"]: e["old_path"] for e in entries if e["kind"] == "moved"}
    rows = []
    for rel in sorted(current):
        prev = old.get(rel) or old.get(moved_from.get(rel, ""), None) or {}
        if rel in unreadable:
            if rel in old:
                rows.append(dict(old[rel]))
            continue
        size, mtime, _ = current[rel]
        rows.append({
            "path": rel, "size": size, "mtime": mtime, "sha256": hashes[rel],
            "first_seen": prev.get("first_seen") or run,
            "last_seen": run,
            "last_processed": (old.get(rel) or {}).get("last_processed", "") if top_inbox(rel) else run,
        })
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/scan-changes",
                                 description="Compare the workspace with MANIFEST.csv and report changes.")
    ap.add_argument("--run")
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    root = common.find_root()
    run = args.run or common.run_id(root)
    if "/" in run or "\\" in run or not run.strip():
        sys.stderr.write("--run must be a run id such as 2026-10-15_091200\n")
        return 2
    mpath = root / "MANIFEST.csv"
    manifest = None
    if mpath.exists():
        manifest = {r["path"]: r for r in common.read_csv(mpath) if r.get("path")}
    current = walk(root)
    entries, hashes, unreadable = compare(root, current, manifest)
    report = root / "changes" / ("%s.md" % run)
    common.write_text_atomic(report, render_report(run, entries, unreadable, len(current), manifest is None))
    if args.write_manifest:
        common.write_csv(mpath, MANIFEST_COLUMNS,
                         manifest_rows(run, current, hashes, unreadable, manifest, entries), bom=False)
    c = counts_of(entries)
    rel_report = common.rel(report, root)
    if args.json:
        sys.stdout.write(json.dumps({
            "run": run, "report": rel_report, "first_scan": manifest is None, "files": len(current),
            "counts": c, "changes": entries, "unreadable": unreadable,
            "manifest_written": bool(args.write_manifest)}, ensure_ascii=False, indent=2) + "\n")
    elif args.quiet:
        sys.stdout.write(rel_report + "\n")
    else:
        lead = "first scan, " if manifest is None else ""
        sys.stdout.write("scan: %s%s (%d files)\n" % (lead, counts_text(c), len(current)))
        if unreadable:
            sys.stdout.write("unreadable: %d file(s), listed in the report\n" % len(unreadable))
        sys.stdout.write("report: %s\n" % rel_report)
        if args.write_manifest:
            sys.stdout.write("manifest: MANIFEST.csv rewritten (%d files)\n" % len(current))
    return 0


if __name__ == "__main__":
    sys.exit(main())
