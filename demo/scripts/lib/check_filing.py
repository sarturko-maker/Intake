"""demo/scripts/check-filing: compare a demo workspace with demo/expected.csv. Python 3.8+.

Reads every .eml under areas/**/correspondence/ (not work-product/ or history/), inbox/noise/
(and confirmed/), inbox/please-check/ (and resolved/) and the inbox itself, and maps each
Message-ID to where it sits. For each expected row of the batches dropped so far it checks:
- kind: matter, noise or please-check (alternatives with '|');
- for matters: area, sub_area and subject (alternatives with '|'; empty means none);
- groups: one matter folder per group, different groups in different folders; a row naming
  several groups (b2-06: G02|G06) may sit in please-check, or in the first group's folder once
  the human has re-filed it there;
- proposed outcome: matter.md's proposed_outcome against the latest email of the group;
- flags (warnings; failures with --strict): ';' joins required items, '|' gives alternatives;
  follows:Gxx checks matter.md follows, label:X checks the label; for a please-check row the
  flag is looked for in the email's note. A please-check note should name its group's reference.
Prints a PASS/FAIL table and a total. Exit 1 on any FAIL.
"""

import argparse
import collections
import json
import re
import sys

from demo_common import (alts, common, die, id_time, index_emails, inbox_leftovers,
                         load_expected, matter_meta, resolve_workspace)

KIND_ORDER = {"matter": 0, "please-check": 1, "noise": 2, "inbox": 3}


class Result:
    def __init__(self, row):
        self.row = row
        self.id = row["id"]
        self.loc = None
        self.fails = []
        self.warns = []
        self.notes = []

    @property
    def status(self):
        return "FAIL" if self.fails else "PASS"


def norm(s):
    return re.sub(r"[\s_-]+", "-", (s or "").strip().lower())


def sort_key(res):
    loc = res.loc
    if loc is not None and loc.date is not None:
        return (loc.date.timestamp(), res.id)
    return (0, res.id)


def note_files(loc):
    """Please-check notes that belong to the email at loc."""
    if loc is None:
        return []
    d = loc.path.parent
    out = []
    for p in sorted(d.glob("*.note.md")):
        if p.name.startswith(loc.path.name) or p.name.startswith(loc.path.stem + "."):
            out.append(p)
    if not out:
        for p in sorted(d.glob("*.note.md")):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if loc.path.name in text:
                out.append(p)
    return out


def refiling_evidence(ws, loc):
    """True if the workspace shows the email went through please-check before its matter."""
    name = loc.path.name
    resolved = ws / "inbox" / "please-check" / "resolved"
    if resolved.is_dir():
        for p in resolved.iterdir():
            if p.name.startswith(name) or p.name.startswith(loc.path.stem):
                return True
            if p.suffix == ".md":
                try:
                    if name in p.read_text(encoding="utf-8", errors="replace"):
                        return True
                except OSError:
                    pass
    log = ws / "WORKFLOW-LOG.md"
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if "re-filed" in line and (name in line or loc.ref and loc.ref in line):
                return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check-filing",
                                 description="Check a demo workspace against demo/expected.csv.")
    ap.add_argument("--workspace", help="the demo workspace (default: the one this script is in)")
    ap.add_argument("--batch", type=int, choices=(1, 2, 3),
                    help="check batches 1..N (default: the highest batch found in the workspace)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the table")
    args = ap.parse_args(argv)
    ws = resolve_workspace(args.workspace)
    rows = load_expected()
    index = index_emails(ws)

    if args.batch:
        upto = args.batch
    else:
        found = [int(r["batch"]) for r in rows if r["message_id"] in index]
        if not found:
            sys.stderr.write("check-filing: no demo emails found in %s. Drop a batch and process "
                             "the inbox first.\n" % ws)
            return 1
        upto = max(found)
    scope = [r for r in rows if int(r["batch"]) <= upto]
    results = [Result(r) for r in scope]
    by_id = {res.id: res for res in results}

    # ------------------------------------------------------------ locate and check kind
    for res in results:
        r = res.row
        locs = sorted(index.get(r["message_id"], []), key=lambda l: KIND_ORDER.get(l.kind, 9))
        if not locs:
            msg = "not found anywhere in the workspace"
            if r["file"].lower().endswith(".msg"):
                stem = r["file"][:-4]
                msgs = [p for p in ws.rglob("*.msg") if "demo" not in p.relative_to(ws).parts[:1]]
                hits = [p for p in msgs if p.stem == stem] or msgs
                if hits:
                    msg += "; .msg found but no converted .eml: " + ", ".join(
                        common.rel(p, ws) for p in hits[:3])
            res.fails.append(msg)
            continue
        res.loc = locs[0]
        if len(locs) > 1:
            res.fails.append("found in %d places: %s" % (len(locs), ", ".join(l.rel for l in locs)))
        kinds = alts(r["kind"])
        if res.loc.kind == "inbox":
            res.fails.append("still in the inbox (not processed)")
            continue
        if res.loc.kind not in kinds:
            res.fails.append("expected %s, found %s" % (r["kind"], res.loc.kind))
            continue
        if res.loc.kind == "matter":
            for col, got in (("area", res.loc.area), ("sub_area", res.loc.sub_area),
                             ("subject", res.loc.subject)):
                if got not in alts(r[col]):
                    res.fails.append("%s: expected %s, found %s" % (
                        col, r[col] or "(none)", got or "(none)"))
            if not res.loc.ref:
                res.fails.append("matter folder name does not start with a reference")

    # ------------------------------------------------------------ groups
    folders = collections.defaultdict(collections.Counter)
    first_row = {}
    for res in results:
        groups = [g for g in alts(res.row["group"]) if g]
        if len(groups) == 1 and res.loc is not None and res.loc.kind == "matter":
            folders[groups[0]][res.loc.where()] += 1
            first_row.setdefault((groups[0], res.loc.where()), res.id)
    group_folder = {}
    for g, counter in folders.items():
        best = max(counter.items(), key=lambda kv: (kv[1], -int(re.sub(r"\D", "",
                                                                      first_row[(g, kv[0])]))))
        group_folder[g] = best[0]
    owner = {}
    for g in sorted(group_folder):
        f = group_folder[g]
        if f in owner:
            for res in results:
                if [x for x in alts(res.row["group"]) if x] == [g]:
                    res.fails.append("%s shares its folder with %s: %s" % (g, owner[f], f))
        else:
            owner[f] = g
    for res in results:
        groups = [g for g in alts(res.row["group"]) if g]
        if res.loc is None or res.loc.kind != "matter" or not groups:
            continue
        if len(groups) == 1:
            g = groups[0]
            if group_folder.get(g) and res.loc.where() != group_folder[g]:
                res.fails.append("%s is split: this email is in %s, the group is in %s" % (
                    g, res.loc.where(), group_folder[g]))
        else:
            target = group_folder.get(groups[0])
            if target is None:
                res.fails.append("filed in %s, but %s has no folder yet" % (res.loc.where(),
                                                                            groups[0]))
            elif res.loc.where() != target:
                res.fails.append("filed in %s; only %s's folder (%s) is accepted" % (
                    res.loc.where(), groups[0], target))
            elif not refiling_evidence(ws, res.loc):
                res.warns.append("filed into %s without a resolved please-check note "
                                 "(inbox/please-check/resolved/)" % groups[0])
            else:
                res.notes.append("re-filed by the human into %s" % groups[0])

    # ------------------------------------------------------------ outcomes
    for g, folder in sorted(group_folder.items()):
        members = [res for res in results if [x for x in alts(res.row["group"]) if x] == [g]
                   and res.loc is not None and res.loc.kind == "matter"
                   and res.loc.where() == folder and res.row["proposed_outcome"]]
        if not members:
            continue
        latest = max(members, key=lambda res: (sort_key(res), id_time(res.row["message_id"])))
        meta = matter_meta(ws / folder)
        got = meta.get("proposed_outcome", "")
        want = alts(latest.row["proposed_outcome"])
        if got in want:
            latest.notes.append("outcome %s ok (%s)" % (got, meta.get("reference", "")))
        else:
            latest.fails.append("proposed_outcome %s, expected %s" % (
                got or "(empty)", latest.row["proposed_outcome"]))
        for res in members:
            if res is not latest:
                res.notes.append("outcome checked on %s" % latest.id)

    # ------------------------------------------------------------ flags and notes
    for res in results:
        r = res.row
        loc = res.loc
        if loc is None or loc.kind not in alts(r["kind"]):
            continue
        items = [i for i in r["flags"].split(";") if i.strip()]
        if loc.kind == "matter":
            meta = matter_meta(loc.folder)
            have = {f.strip() for f in meta.get("flags", "").split(",") if f.strip()}
            for item in items:
                options = alts(item)
                ok = False
                for opt in options:
                    if opt.startswith("follows:"):
                        g = opt.split(":", 1)[1]
                        ref = ""
                        if g in group_folder:
                            m = common.MATTER_DIR_RE.match(group_folder[g].rsplit("/", 1)[-1])
                            ref = m.group(1) if m else ""
                        ok = ok or (bool(ref) and meta.get("follows", "").strip() == ref)
                    elif opt.startswith("label:"):
                        ok = ok or norm(meta.get("label", "")) == norm(opt.split(":", 1)[1])
                    else:
                        ok = ok or opt in have
                if not ok:
                    res.warns.append("%s not set in matter.md (flags: %s; follows: %s; label: %s)"
                                     % (item, meta.get("flags", "") or "-",
                                        meta.get("follows", "") or "-",
                                        meta.get("label", "") or "-"))
        elif loc.kind == "please-check":
            notes = note_files(loc)
            text = ""
            for p in notes:
                try:
                    text += p.read_text(encoding="utf-8", errors="replace") + "\n"
                except OSError:
                    pass
            if not notes:
                res.warns.append("no note beside %s" % loc.rel)
            for item in items:
                if not any(opt in text for opt in alts(item)):
                    res.warns.append("note does not mention %s" % item)
            for g in [x for x in alts(r["group"]) if x]:
                if g in group_folder:
                    m = common.MATTER_DIR_RE.match(group_folder[g].rsplit("/", 1)[-1])
                    ref = m.group(1) if m else ""
                    if ref and ref not in text:
                        res.warns.append("note does not name %s (%s)" % (g, ref))

    # ------------------------------------------------------------ workspace-level
    extra = []
    left = inbox_leftovers(ws)
    if left:
        extra.append(("warn", "inbox not empty: %d file(s): %s" % (
            len(left), ", ".join(p.name for p in left[:5]))))
    known = {r["message_id"] for r in rows}
    for mid, locs in sorted(index.items()):
        if mid not in known:
            extra.append(("info", "email not in expected.csv: %s" % locs[0].rel))

    if args.strict:
        for res in results:
            res.fails += ["(strict) " + w for w in res.warns]
            res.warns = []
        extra = [("fail" if k == "warn" else k, t) for k, t in extra]

    n_fail = sum(1 for res in results if res.fails) + sum(1 for k, _ in extra if k == "fail")
    n_warn = sum(len(res.warns) for res in results) + sum(1 for k, _ in extra if k == "warn")
    if args.json:
        out = {"workspace": str(ws), "batches": upto, "rows": [], "extra": extra,
               "pass": sum(1 for res in results if not res.fails), "fail": n_fail,
               "warnings": n_warn}
        for res in results:
            out["rows"].append({"id": res.id, "result": res.status, "kind": res.row["kind"],
                                "group": res.row["group"],
                                "found": res.loc.where() if res.loc else "",
                                "fails": res.fails, "warnings": res.warns, "notes": res.notes})
        print(json.dumps(out, indent=2))
        return 1 if n_fail else 0

    print("check-filing: %s (batches 1-%d, %d rows)" % (ws, upto, len(results)))
    print("")
    print("%-6s %-5s %-21s %-8s %s" % ("id", "check", "expected", "group", "found"))
    for res in results:
        found = res.loc.where() if res.loc else "-"
        if res.loc is not None and res.loc.kind != "matter":
            found = "%s: %s" % (res.loc.kind, res.loc.rel)
        print("%-6s %-5s %-21s %-8s %s" % (res.id, res.status, res.row["kind"], res.row["group"]
                                           or "-", found))
        for f in res.fails:
            print("       fail: " + f)
        for w in res.warns:
            print("       warn: " + w)
        for n in res.notes:
            print("       " + n)
    for kind, text in extra:
        print("%s: %s" % (kind, text))
    n_pass = sum(1 for res in results if not res.fails)
    ws_fails = sum(1 for k, _ in extra if k == "fail")
    print("")
    print("Total: %d PASS, %d FAIL, %d warnings (%d rows, batches 1-%d)%s" % (
        n_pass, len(results) - n_pass, n_warn, len(results), upto,
        "; %d workspace failure(s)" % ws_fails if ws_fails else ""))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
