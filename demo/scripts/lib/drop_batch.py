"""demo/scripts/drop-batch: put one demo batch into a workspace inbox. Python 3.8+.

Copies demo/batches/N/* into <workspace>/inbox/. Each {{REF:Gxx}} placeholder (in batches 2 and
3, in subject lines and bodies) becomes the reference of group Gxx: the earliest expected email
of that group in demo/expected.csv is looked up by Message-ID under
<workspace>/areas/**/correspondence/, and the reference is read from its matter folder name.
A placeholder that cannot be resolved stays as it is and is reported. Files are written as bytes;
the emails that carry placeholders are 7bit ASCII, so the replacement is exact.
"""

import argparse
import sys

from demo_common import (BATCHES, JUNK, PLACEHOLDER_RE, alts, die, id_time, index_emails,
                         inbox_leftovers, load_expected, resolve_workspace)


def group_candidates(rows):
    """{group: [row, ...]} of matter emails, earliest first. Rows naming several groups are
    left out (they are not evidence for where a group is filed)."""
    out = {}
    for r in rows:
        if "matter" not in alts(r["kind"]):
            continue
        groups = [g for g in alts(r["group"]) if g]
        if len(groups) != 1:
            continue
        out.setdefault(groups[0], []).append(r)
    for g in out:
        out[g].sort(key=lambda r: (int(r["batch"]), id_time(r["message_id"]), r["id"]))
    return out


def resolve(group, candidates, index):
    """(reference, row id used, matter folder, note) or None."""
    rows = candidates.get(group, [])
    for i, r in enumerate(rows):
        for loc in index.get(r["message_id"], []):
            if loc.kind == "matter" and loc.ref:
                note = ""
                if i:
                    note = "earliest %s not found; used %s" % (rows[0]["id"], r["id"])
                return loc.ref, r["id"], loc.where(), note
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="drop-batch",
                                 description="Copy a demo batch into the workspace inbox.")
    ap.add_argument("batch", type=int, choices=(1, 2, 3), help="batch number")
    ap.add_argument("--workspace", help="the demo workspace (default: the one this script is in)")
    ap.add_argument("--force", action="store_true",
                    help="drop even if the inbox already has files")
    args = ap.parse_args(argv)
    ws = resolve_workspace(args.workspace)
    src = BATCHES / str(args.batch)
    if not src.is_dir():
        die("missing %s" % src)
    files = sorted(p for p in src.iterdir() if p.is_file() and p.name not in JUNK
                   and not p.name.startswith("."))
    if not files:
        die("no files in %s" % src)
    inbox = ws / "inbox"
    left = inbox_leftovers(ws)
    if left and not args.force:
        sys.stderr.write("drop-batch: the inbox is not empty (%d file(s), for example %s). Process "
                         "it first, or add --force to drop anyway.\n" % (len(left), left[0].name))
        return 1

    rows = load_expected()
    candidates = group_candidates(rows)
    index = index_emails(ws)
    resolved, unresolved = {}, {}
    copied = 0
    for p in files:
        data = p.read_bytes()
        for g in sorted(set(m.decode("ascii") for m in PLACEHOLDER_RE.findall(data))):
            if g not in resolved and g not in unresolved:
                hit = resolve(g, candidates, index)
                if hit:
                    resolved[g] = hit
                else:
                    unresolved[g] = []
            if g in resolved:
                data = data.replace(("{{REF:%s}}" % g).encode("ascii"),
                                    resolved[g][0].encode("ascii"))
            else:
                unresolved[g].append(p.name)
        (inbox / p.name).write_bytes(data)
        copied += 1

    print("drop-batch %d -> %s" % (args.batch, inbox))
    print("copied: %d files" % copied)
    for g in sorted(resolved):
        ref, used, folder, note = resolved[g]
        print("resolved {{REF:%s}} -> %s (%s in %s)%s" % (g, ref, used, folder,
                                                          "; " + note if note else ""))
    for g in sorted(unresolved):
        first = candidates.get(g, [{}])[0].get("id", "?")
        print("unresolved {{REF:%s}}: no matter correspondence with the Message-ID of %s or a "
              "later %s email; left as is in: %s" % (g, first, g, ", ".join(unresolved[g])))
    print("next: say \"process the inbox\"")
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
