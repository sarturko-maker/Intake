"""matter-sync: keep each matter's two folders in step, without model cost.

For every matter (or those named):
  1. registers files nobody has recorded yet: anything in human/ (the lawyer's folder, except
     corrections.md and roster.confirmed.md, which are read directly) and anything put by
     hand into agent/correspondence/ or agent/documents/;
  2. a file in human/ whose content changed: its documents.md row is set back to read: pending;
  3. finds the lawyer's edits since the last run: human/corrections.md, roster.confirmed.md,
     and the agent's files (matter.md, brief.md, facts.md, roster.md, notes.md) when the lawyer
     edited them, by comparing with MANIFEST.csv (the state at the end of the last run); content
     the agent wrote itself (changes/agent-writes.csv, kept by the after-write hook) does not count;
  4. writes <matter>/START-HERE.md: status, next step and links to everything in both folders;
  5. reports, per matter, what a reader must read (documents.md rows with read: pending, and the
     edits found), to stdout and to changes/<run>-matters.md.
"""

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

JUNK = {".ds_store", "thumbs.db", "desktop.ini", ".gitkeep"}
AGENT_MEMORY = ("matter.md", "brief.md", "facts.md", "roster.md", "notes.md")
REGISTER_DIRS = ("correspondence", "documents")  # under agent/


def is_junk(name):
    low = name.lower()
    return low in JUNK or low.startswith("~$") or low.startswith(".~lock") or low.endswith(".tmp") \
        or low.endswith(".note.md")


def link(path_from_matter):
    return quote(path_from_matter.replace("\\", "/"), safe="/")


def manifest_hashes(root):
    return {r.get("path", ""): r.get("sha256", "") for r in common.read_csv(Path(root) / "MANIFEST.csv")}


def doc_rows(matter):
    return common.read_pipe_records(common.agent_dir(matter) / "documents.md", common.DOCUMENTS_COLUMNS)


def row_key(folder, name):
    return (folder or "").strip().strip("/") + "/" + (name or "").strip()


def candidate_files(matter):
    """(path, folder as documents.md writes it, name) of every file that should have a row."""
    out = []
    agent = common.agent_dir(matter)
    human = common.human_dir(matter)
    if human.is_dir():
        for f in sorted(human.rglob("*")):
            if not f.is_file() or is_junk(f.name) or "history" in f.relative_to(human).parts:
                continue
            if f.parent == human and f.name in common.HUMAN_ONLY_NAMES:
                continue
            folder = f.parent.relative_to(matter).as_posix()  # human or human/<sub>
            out.append((f, folder, f.name))
    for sub in REGISTER_DIRS:
        d = agent / sub
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if not f.is_file() or is_junk(f.name) or "history" in f.relative_to(agent).parts:
                continue
            folder = f.parent.relative_to(agent).as_posix()
            if f.suffix.lower() == ".msg" and (f.with_suffix(".eml")).exists():
                continue  # the original of a converted email has its own "no:" row
            out.append((f, folder, f.name))
    return out


def register(root, path, run):
    import place_email
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = place_email.main(["--register", str(path), "--run", run])
    return rc, (buf.getvalue() + err.getvalue()).strip()


def reset_changed(matter, rows, path, folder, name, sha, stamp_text, run):
    """A changed file in human/: new hash, read: pending, a log line. Rewrites that one row."""
    docs = common.agent_dir(matter) / "documents.md"
    lines = common.read_text(docs).split("\n")
    for r in rows:
        if row_key(r["folder"], r["name"]) == row_key(folder, name) and r.get("hash") != sha:
            i = r["_line"] - 1
            fields = [r.get(c, "") for c in common.DOCUMENTS_COLUMNS]
            fields[common.DOCUMENTS_COLUMNS.index("hash")] = sha
            fields[common.DOCUMENTS_COLUMNS.index("read")] = "pending"
            fields[common.DOCUMENTS_COLUMNS.index("date")] = stamp_text
            lines[i] = common.join_pipe(fields)
            common.write_text_atomic(docs, "\n".join(lines))
            common.append_line(common.agent_dir(matter) / "log.md", common.join_pipe(
                [stamp_text, "lawyer changed %s/%s" % (folder, name), "%s/%s" % (folder, name), run]))
            return True
    return False


def agent_writes(root):
    """sha256 values the agent itself wrote, per lower-case path: changes/agent-writes.csv, kept by the
    after-write hook and emptied when scan-changes writes the manifest."""
    out = {}
    for r in common.read_csv(Path(root) / "changes" / "agent-writes.csv"):
        out.setdefault(r.get("path", "").strip().lower(), set()).add(r.get("sha256", "").strip())
    return out


def lawyer_edits(root, matter, manifest, written=None):
    """Memory files the lawyer changed since the last run (per MANIFEST.csv). A file whose content the
    agent wrote itself (written: agent_writes) is not the lawyer's edit."""
    written = written or {}
    out = []
    files = [common.human_dir(matter) / n for n in common.HUMAN_ONLY_NAMES] + \
            [common.agent_dir(matter) / n for n in AGENT_MEMORY]
    for f in files:
        if not f.is_file():
            continue
        relp = common.rel(f, root)
        if relp not in manifest:
            tmpl = Path(root) / "skills" / "operations" / "matter-memory" / "templates" / f.name
            if f.parent.name == common.HUMAN and tmpl.is_file() and \
                    common.read_text(f).strip() != common.read_text(tmpl).strip():
                out.append(f.relative_to(matter).as_posix())
            continue
        if manifest[relp]:
            sha = common.sha256_file(f)
            if sha != manifest[relp] and sha not in written.get(relp.lower(), ()):
                out.append(f.relative_to(matter).as_posix())
    return out


def start_here(root, matter, meta, rows, pending, edits, stamp_text):
    ref = meta.get("reference", "") or matter.name.split("_", 1)[0]
    title = meta.get("title", "") or matter.name
    agent = common.agent_dir(matter)
    L = ["# %s %s" % (ref, title), ""]
    facts = []
    for key, label in (("status", "Status"), ("waiting_on", "Waiting on"), ("next_step", "Next step"),
                       ("due", "Due"), ("proposed_outcome", "Proposed")):
        if meta.get(key):
            facts.append("**%s:** %s" % (label, meta[key]))
    if facts:
        L += [" · ".join(facts), ""]
    L += ["_Kept up to date by tools/matter-sync (%s). Do not edit this page. Your own files go in "
          "[human/](human/); you may also change files in [agent/](agent/)._" % stamp_text, ""]
    quick = ["[Brief](agent/brief.md)", "[Matter summary](agent/matter.md)"]
    pack = "agent/%s_harvey-pack/" % ref
    if (matter / pack).is_dir():
        quick.append("[Harvey pack](%s)" % link(pack))
    quick += ["[Log](agent/log.md)", "[Notes](agent/notes.md)"]
    L += ["## Open first", "", " · ".join(quick), ""]
    if pending or edits:
        L += ["## New or changed since the last run", ""]
        for r in pending:
            p = r["folder"] + "/" + r["name"]
            shown = p if p.startswith(common.HUMAN) else "agent/" + p
            L.append("- [%s](%s)" % (shown, link(shown)))
        for e in edits:
            L.append("- %s (edited by you)" % e)
        L.append("")
    emails = [r for r in rows if r.get("folder") == "correspondence" and r["name"].lower().endswith(".eml")]
    emails.sort(key=lambda r: (r.get("date") or "", r["name"]), reverse=True)
    L += ["## Emails, newest first", ""]
    if not emails:
        L.append("None yet.")
    for r in emails:
        who = r.get("from") or ""
        L.append("- %s %s [%s](%s)" % (r.get("date", ""), ("(%s)" % who) if who else "",
                                       r["name"], link("agent/correspondence/" + r["name"])))
    L.append("")
    sections = (("Documents received", "documents/received"), ("Our documents", "documents/ours"),
                ("Reference copies", "documents/reference"))
    for label, folder in sections:
        items = [r for r in rows if r.get("folder") == folder]
        if items:
            L += ["## %s" % label, ""]
            for r in sorted(items, key=lambda r: r["name"].lower()):
                L.append("- [%s](%s)%s" % (r["name"], link("agent/%s/%s" % (folder, r["name"])),
                                           (" - " + r["summary"]) if r.get("summary") else ""))
            L.append("")
    human = common.human_dir(matter)
    L += ["## Your files (human/)", ""]
    mine = []
    if human.is_dir():
        for f in sorted(human.rglob("*")):
            if f.is_file() and not is_junk(f.name):
                relp = f.relative_to(matter).as_posix()
                mine.append("- [%s](%s)" % (relp[len(common.HUMAN) + 1:], link(relp)))
    L += mine or ["None yet. Save notes, call notes, documents and Harvey's output here."]
    L.append("")
    drafts = agent / "drafts"
    if drafts.is_dir():
        ds = sorted(f for f in drafts.iterdir() if f.is_file() and not is_junk(f.name))
        if ds:
            L += ["## Drafts", ""] + ["- [%s](%s)" % (f.name, link("agent/drafts/" + f.name)) for f in ds] + [""]
    return "\n".join(L)


def protect_received(matter):
    """Received files (agent/correspondence/, agent/documents/received/) are never edited: make any that
    are still writable read-only, so Word cannot save a sensitivity label into them. Returns how many."""
    n = 0
    for sub in ("correspondence", "documents/received"):
        d = common.agent_dir(matter) / sub
        if d.is_dir():
            for f in d.rglob("*"):
                if f.is_file() and not is_junk(f.name) and common.protect(f):
                    n += 1
    return n


def sync_matter(root, matter, run, manifest, stamp_text, do_register=True, written=None):
    rep = {"matter": common.rel(matter, root), "registered": [], "changed": [], "pending": [],
           "edits": [], "errors": []}
    rows = doc_rows(matter)
    known = {row_key(r["folder"], r["name"]): r for r in rows}
    if do_register:
        for path, folder, name in candidate_files(matter):
            key = row_key(folder, name)
            if key not in known:
                rc, out = register(root, path, run)
                if rc == 0:
                    rep["registered"].append(path.relative_to(matter).as_posix())
                else:
                    rep["errors"].append("%s: %s" % (path.relative_to(matter).as_posix(), out.splitlines()[-1] if out else rc))
            elif folder.startswith(common.HUMAN):
                sha = common.sha256_file(path)
                if known[key].get("hash") and known[key]["hash"] != sha:
                    if reset_changed(matter, rows, path, folder, name, sha, stamp_text, run):
                        rep["changed"].append(path.relative_to(matter).as_posix())
        rows = doc_rows(matter)
        rep["protected"] = protect_received(matter)
    pending = [r for r in rows if (r.get("read") or "").strip().lower() == "pending" and r.get("folder")]
    rep["pending"] = [(r["folder"] if r["folder"].startswith(common.HUMAN) else "agent/" + r["folder"])
                      + "/" + r["name"] for r in pending]
    # The lawyer's edits are only knowable before the agent writes: at the start of a run.
    rep["edits"] = lawyer_edits(root, matter, manifest, written) if do_register else []
    meta, _ = common.read_frontmatter_file(common.agent_dir(matter) / "matter.md")
    page = start_here(root, matter, meta, rows, pending, rep["edits"], stamp_text)
    target = matter / common.START_HERE
    if not target.exists() or common.read_text(target) != page + "\n":
        common.write_text_atomic(target, page + "\n")
    return rep


def resolve(root, value):
    if common.REF_RE.match(value):
        d = common.find_matter(root, value)
        if d is None:
            common.die("matter-sync: no matter with reference %s" % value, 2)
        return d
    p = Path(value)
    for c in ([p] if p.is_absolute() else [Path.cwd() / p, root / p]):
        if common.is_matter_dir(c):
            return c.resolve()
    common.die("matter-sync: not a matter folder (no agent/matter.md): %s" % value, 2)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/matter-sync",
                                 description="Register new and changed files in matters, find the lawyer's edits, "
                                             "write START-HERE.md, list what to read.")
    ap.add_argument("matters", nargs="*", metavar="REF|MATTER_FOLDER")
    ap.add_argument("--run")
    ap.add_argument("--pages-only", action="store_true", help="only rewrite START-HERE.md pages")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = common.find_root()
    run = a.run or common.run_id(root)
    stamp_text = common.stamp(root)
    legacy = list(common.iter_legacy_matter_dirs(root))
    mdirs = [resolve(root, m) for m in a.matters] if a.matters else list(common.iter_matter_dirs(root))
    manifest = manifest_hashes(root)
    written = agent_writes(root)
    reports = [sync_matter(root, m, run, manifest, stamp_text, do_register=not a.pages_only, written=written)
               for m in mdirs]
    lines = []
    for r in reports:
        bits = []
        if r["registered"]:
            bits.append("registered %d" % len(r["registered"]))
        if r["changed"]:
            bits.append("changed by you: " + ", ".join(r["changed"]))
        if r["edits"]:
            bits.append("edited by you: " + ", ".join(r["edits"]))
        if r["pending"]:
            bits.append("to read: " + ", ".join(r["pending"]))
        for e in r["errors"]:
            bits.append("could not register " + e)
        if bits:
            lines.append("- %s: %s" % (r["matter"], "; ".join(bits)))
    needs = [r for r in reports if r["pending"] or r["edits"]]
    head = "matter-sync: %d matters, %d need a reader, START-HERE.md pages up to date" % (len(reports), len(needs))
    if legacy:
        head += "; %d in the old layout (run bash tools/matter-migrate)" % len(legacy)
    protected = sum(r.get("protected", 0) for r in reports)
    if protected:
        head += "; %d received files set to read-only" % protected
    if not a.pages_only:
        out = Path(root) / "changes" / ("%s-matters.md" % run)
        common.write_text_atomic(out, "# Matters to read, run %s\n\n%s\n" % (run, "\n".join(lines) or "None."))
    if a.json:
        print(json.dumps({"summary": head, "matters": reports}, ensure_ascii=False, indent=2))
    else:
        print(head)
        for line in lines:
            print(line)
    return 1 if any(r["errors"] for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
