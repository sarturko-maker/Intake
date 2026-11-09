"""place-email: move one email into a matter, noise or please-check, with its bookkeeping.

Interface: tools/place-email (usage text) and the build spec, D3. Parsing comes from
emailtools.py, so names, hashes and attachment kinds agree with unpack-email.

Rules kept here:
- the bytes of a received file (email or attachment) are never changed; files are moved,
  attachments written once and never overwritten;
- the only deletion: an inbox email whose identical bytes are already filed (hash checked);
- JOURNAL.md, log.md and documents.md get one whole line at a time (common.append_line).
"""

import argparse
import re
import csv
import datetime as _dt
import io
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
import emailtools as et  # noqa: E402

DOCUMENTS_HEADER = ("# Every email and file in this matter, one line each. Appended by tools/place-email; "
                    "summaries and read status by the reader.\n"
                    "# name | folder | origin | from | date | version_of | message_id | hash | read | "
                    "summary | duplicate_of\n")
NOISE_REL = "inbox/noise/NOISE.csv"
CHECK_REL = "inbox/please-check"
NOISE_DIR_REL = "inbox/noise"


class Refusal(Exception):
    """Usage or safety refusal: exit 2, nothing changed."""


class Failure(Exception):
    """An operation failed part-way: exit 1."""


class Run:
    """Shared state for one invocation: context, run id, printed actions."""

    def __init__(self, ctx, run, as_json):
        self.ctx = ctx
        self.root = ctx.root
        self.run = run
        self.as_json = as_json
        self.actions = []
        self.result = {"run": run}

    def say(self, action, item, destination="", detail=""):
        self.actions.append({"action": action, "item": item, "destination": destination, "detail": detail})
        if not self.as_json:
            line = "%s: %s" % (action, item)
            if destination:
                line += " -> " + destination
            if detail:
                line += " (" + detail + ")"
            sys.stdout.write(line + "\n")

    def rel(self, path):
        return self.ctx.rel(path)

    def journal(self, action, item, destination, reason="", confidence=""):
        et.append_journal(self.root, self.ctx.stamp(), self.run, action, item, destination, reason, confidence)

# ---------------------------------------------------------------- file helpers


def resolve_input(root, value):
    """A path as given: relative to the current folder, else to the workspace."""
    p = Path(value)
    if not p.is_absolute() and not p.exists():
        alt = Path(root) / value
        if alt.exists():
            p = alt
    return p.resolve() if p.exists() else p


def inside(path, folder):
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
        return True
    except ValueError:
        return False


def move_file(src, dest):
    """Move without overwriting and without touching the bytes."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if os.path.exists(common.os_path(dest)):
        raise Failure("will not overwrite %s" % dest)
    try:
        shutil.move(common.os_path(src), common.os_path(dest))
    except OSError as exc:
        raise Failure("could not move %s to %s: %s (is it open in another program?)" % (src, dest, exc))
    if common.is_received_path(dest):
        common.protect(dest)      # received files are never edited: read-only on disk
    return dest


def write_new(dest, data):
    with open(common.os_path(dest), "xb") as fh:
        fh.write(data)
    if common.is_received_path(dest):
        common.protect(dest)


def msg_sibling(path):
    """The .msg original beside a converted .eml (same stem), or None."""
    path = Path(path)
    for cand in (path.with_suffix(".msg"), path.with_suffix(".MSG"), path.with_suffix(".Msg")):
        if cand.is_file() and cand != path:
            return cand
    try:
        for p in path.parent.iterdir():
            if p.stem == path.stem and p.suffix.lower() == ".msg" and p.is_file():
                return p
    except OSError:
        pass
    return None


def identical_on_disk(paths, sha):
    for c in paths:
        try:
            if Path(c).is_file() and common.sha256_file(c) == sha:
                return Path(c)
        except OSError:
            continue
    return None

# ---------------------------------------------------------------- documents.md


def documents_path(matter):
    path = Path(matter) / "documents.md"
    if not path.exists():
        tmpl = common.find_root() / "skills" / "operations" / "matter-memory" / "templates" / "documents.md"
        text = common.read_text(tmpl) if tmpl.exists() else DOCUMENTS_HEADER
        common.write_text_atomic(path, text if text.endswith("\n") else text + "\n")
    return path


def doc_line(name, folder, origin, frm, date, mid, sha, read, dup="", summary=""):
    return common.join_pipe([name, folder, origin, frm, date, "", mid, sha, read, summary, dup])


def subject_read_index(agent):
    """{sha256: (reference, folder, name, summary, card or None)} for files already read in the other matters of this
    matter's subject, that is the same client (RULES.md, hard rule 6: the matter and its subject folder).
    Not for general/unfiled, which gathers unrelated matters."""
    mdir = Path(agent).parent
    subj = mdir.parent
    if subj.name == "unfiled" or not subj.is_dir():
        return {}
    out = {}
    for sib in sorted(subj.iterdir()):
        if sib == mdir or not sib.is_dir() or not common.is_matter_dir(sib):
            continue
        ref = common.MATTER_DIR_RE.match(sib.name).group(1)
        for r in common.read_pipe_records(common.agent_dir(sib) / "documents.md", common.DOCUMENTS_COLUMNS):
            h = (r.get("hash") or "").strip().lower()
            summary = (r.get("summary") or "").strip()
            if h and summary and (r.get("read") or "").strip().lower() == "yes":
                name = (r.get("name") or "").strip()
                card = common.agent_dir(sib) / "summaries" / (name + ".md")
                out.setdefault(h, (ref, (r.get("folder") or "").strip(), name, summary,
                                   card if card.is_file() else None))
    return out


def stored_hashes(records):
    """{sha256: name} of the first stored (not duplicate, not unstored) row per hash."""
    out = {}
    for r in records:
        h = r.get("hash", "")
        if h and r.get("folder") and not r.get("duplicate_of") and h not in out:
            out[h] = r.get("name", "")
    return out


def row_path(agent, folder, name):
    """A documents.md row's file: folders are relative to agent/, except human/... (the lawyer's folder)."""
    folder = folder or ""
    if folder == common.HUMAN or folder.startswith(common.HUMAN + "/"):
        return Path(agent).parent / folder / name
    return Path(agent) / folder / name


def stored_copy(matter, records, sha):
    """Path of a file in this matter that holds exactly these bytes (per documents.md), or None."""
    for r in records:
        if r.get("hash") == sha and r.get("folder"):
            hit = identical_on_disk([row_path(matter, r["folder"], r["name"])], sha)
            if hit:
                return hit
    return None

# ---------------------------------------------------------------- please-check notes


def resolve_note(state, email_src, destination, reason):
    """Move <email>.note.md from please-check to please-check/resolved/ with the resolution."""
    note = Path(str(email_src) + ".note.md")
    if not note.is_file():
        return
    text = common.read_text(note).rstrip("\n")
    text += "\n\n## Resolution\n\n- %s (run %s): moved to %s.%s\n" % (
        state.ctx.stamp(), state.run, destination, (" " + reason) if reason else "")
    dest = et.unique_path(state.root / CHECK_REL / "resolved", note.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    common.write_text_atomic(dest, text)
    os.remove(str(note))
    state.say("note resolved", state.rel(note), state.rel(dest))

# ---------------------------------------------------------------- attachments


def store_attachments(state, matter, p, records, rows):
    """Attachment rows (and files) for one email. Appends to rows; returns nothing."""
    out_dir_rel = "documents/ours" if p.direction == "out" else "documents/received"
    origin = "ours" if p.direction == "out" else "received"
    target = Path(matter) / out_dir_rel
    known = stored_hashes(records)
    read_elsewhere = None                  # built on first need: the same file read in another matter of this client
    date = p.info["date"]
    for a in p.attachments:
        if a.kind == "signature-image":
            rows.append(doc_line(a.name, "", origin, p.from_addr, date, p.message_id, a.sha256,
                                 "no: signature image"))
            state.say("not stored", a.name, "", "signature image")
            continue
        if a.kind == "calendar":
            rows.append(doc_line(a.name, "", origin, p.from_addr, date, p.message_id, a.sha256,
                                 "no: calendar part"))
            state.say("not stored", a.name, "", "calendar part")
            continue
        if a.sha256 in known:
            first = known[a.sha256]
            rows.append(doc_line(a.name, "", origin, p.from_addr, date, p.message_id, a.sha256,
                                 "no: duplicate of %s" % first, first))
            state.say("duplicate", a.name, "", "same bytes as %s; not stored again" % first)
            continue
        target.mkdir(parents=True, exist_ok=True)
        stored = common.fit_name(target, a.name)    # a name too long for Windows paths is shortened
        renamed = "original name: %s; " % a.name.replace("|", "/") if stored != a.name else ""
        existing = target / stored
        if os.path.isfile(common.os_path(existing)) and common.sha256_file(existing) == a.sha256:
            dest = existing  # identical bytes already there without a row: record them
        else:
            dest = et.unique_path(target, stored)
            write_new(dest, a.data)
        if renamed:
            state.say("shortened", a.name, state.rel(dest), "the full path would be too long for Windows; "
                      "the original name is kept in documents.md")
        if common.too_long(dest):
            state.say("warning", state.rel(dest), "", "this path is longer than Windows programs accept; "
                      "move the workspace to a shorter folder (for example C:/Legal/intake)")
        known[a.sha256] = dest.name
        if read_elsewhere is None:
            read_elsewhere = subject_read_index(matter)
        seen = read_elsewhere.get(a.sha256.lower())
        if seen:
            ref, folder, name, summary, card = seen
            where = "%s %s/%s" % (ref, folder, name) if folder else "%s %s" % (ref, name)
            if card is not None:                # the card goes with it, under this matter's name for the file
                own = Path(matter) / "summaries" / (dest.name + ".md")
                if not own.exists():
                    own.parent.mkdir(parents=True, exist_ok=True)
                    common.write_text_atomic(own, "Copied from %s, where the same file was read (%s).\n\n%s"
                                             % (ref, where, common.read_text(card)))
                summary = summary.replace("summaries/%s.md" % name, "summaries/%s.md" % dest.name)
            rows.append(doc_line(dest.name, out_dir_rel, origin, p.from_addr, date, p.message_id, a.sha256,
                                 "no: read in %s, same file" % where, summary=renamed + summary.replace("|", "/")))
            state.say("stored", a.name, state.rel(dest), "same file already read in %s; summary copied" % ref)
            continue
        rows.append(doc_line(dest.name, out_dir_rel, origin, p.from_addr, date, p.message_id,
                             a.sha256, "pending", summary=renamed.rstrip("; ")))
        state.say("stored", a.name, state.rel(dest))

# ---------------------------------------------------------------- into a matter


def resolve_matter(root, value, what="--to"):
    if common.REF_RE.match(value or ""):
        d = common.find_matter(root, value)
        if d is None:
            raise Refusal("%s: no matter with reference %s" % (what, value))
    else:
        d = resolve_input(root, value)
    d = Path(d)
    if d.name == common.AGENT and (d / "matter.md").is_file():
        d = d.parent
    if not common.is_matter_dir(d):
        if common.is_legacy_matter_dir(d):
            raise Refusal("%s: %s is in the old one-folder layout; run bash tools/matter-migrate first" % (what, value))
        raise Refusal("%s: not a matter folder (no agent/matter.md): %s" % (what, value))
    if not inside(d, Path(root) / "areas"):
        raise Refusal("%s: matter folders live under areas/: %s" % (what, value))
    return common.agent_dir(d.resolve())


def place_matter(state, src, p, matter, args):
    corr = matter / "correspondence"
    docs = documents_path(matter)
    records = common.read_pipe_records(docs, common.DOCUMENTS_COLUMNS)
    item = state.rel(src)
    sibling = msg_sibling(src)
    reason = args.reason or ""
    conf = args.confidence or ""

    same = stored_copy(matter, records, p.sha256) or \
        identical_on_disk(et.candidate_paths(corr, p.canonical_name), p.sha256)
    if same is not None:
        drop_duplicate(state, src, sibling, same, matter, records)
        return
    twin = msg_twin(sibling, et.candidate_paths(corr, Path(p.canonical_name).stem + ".msg"), matter, records)
    if twin is not None:
        drop_converted_duplicate(state, src, sibling, twin)
        return

    copy_of = same_email_row(records, p)
    if copy_of is not None:
        file_copy(state, src, sibling, p, matter, corr, docs, copy_of, reason, conf)
        return

    dest = et.unique_path(corr, p.canonical_name)
    from_please_check = inside(src, state.root / CHECK_REL)
    move_file(src, dest)
    state.say("filed", item, state.rel(dest))
    origin = "ours" if p.direction == "out" else "received"
    rows = [doc_line(dest.name, "correspondence", origin, p.from_addr, p.info["date"], p.message_id,
                     p.sha256, "pending")]
    if sibling is not None:
        sib_dest = et.unique_path(corr, dest.stem + ".msg")
        sib_sha = common.sha256_file(sibling)
        sib_item = state.rel(sibling)
        move_file(sibling, sib_dest)
        rows.append(doc_line(sib_dest.name, "correspondence", origin, p.from_addr, p.info["date"],
                             p.message_id, sib_sha, "no: original of %s" % dest.name))
        state.say("moved original", sib_item, state.rel(sib_dest))
    att_rows = []
    store_attachments(state, matter, p, records, att_rows)
    rows.extend(att_rows)
    for line in rows:
        common.append_line(docs, line)
    subject = p.subject or "(no subject)"
    common.append_line(matter / "log.md", common.join_pipe(
        [state.ctx.stamp(), "filed %s email from %s: %s" % (p.direction, p.from_addr or "unknown sender", subject),
         "correspondence/" + dest.name, state.run]))
    state.journal("filed", item, state.rel(dest), reason, conf)
    if from_please_check:
        resolve_note(state, src, state.rel(dest), reason)
    if args.cross_ref:
        cross_ref(state, args.cross_ref, matter, dest, p, reason, conf)
    state.result.update({"destination": state.rel(dest), "matter": state.rel(matter.parent)})


def _subject_part(name):
    """The subject slug of a canonical email name: YYYY-MM-DD_HHMM_dir_from_<subject>.eml."""
    parts = Path(name).stem.split("_", 4)
    return re.sub(r"-\d+$", "", parts[4]) if len(parts) == 5 else Path(name).stem


def same_email_row(records, p):
    """The documents.md row of the same email filed before (another copy: intake mailbox and sent
    items, or .eml and .msg), by Message-ID, else by canonical name (same minute, direction, sender
    and subject) when either side has no Message-ID. None if this email is new to the matter."""
    stem = Path(p.canonical_name).stem
    for r in records:
        name = r.get("name", "")
        if r.get("folder") != "correspondence" or not name.lower().endswith(".eml") or r.get("duplicate_of"):
            continue
        mid = (r.get("message_id") or "").strip()
        if p.message_id and mid:
            # the same Message-ID and the same subject: the same email, from another mailbox
            if mid == p.message_id and _subject_part(name) == _subject_part(p.canonical_name):
                return r
            continue
        base = Path(name).stem
        if base == stem or re.match(re.escape(stem) + r"-\d+$", base):
            return r
    return None


def file_copy(state, src, sibling, p, matter, corr, docs, row, reason, conf):
    """Keep a second copy of an email already filed: stored, recorded as duplicate_of, never read."""
    item = state.rel(src)
    dest = et.unique_path(corr, p.canonical_name)
    move_file(src, dest)
    first = row.get("name", "")
    lines = [doc_line(dest.name, "correspondence", "ours" if p.direction == "out" else "received",
                      p.from_addr, p.info["date"], p.message_id, p.sha256, "no: copy of %s" % first, first)]
    if sibling is not None:
        sib_dest = et.unique_path(corr, dest.stem + ".msg")
        sib_sha = common.sha256_file(sibling)
        move_file(sibling, sib_dest)
        lines.append(doc_line(sib_dest.name, "correspondence", "received", "", "", p.message_id, sib_sha,
                              "no: original of %s" % dest.name))
    for line in lines:
        common.append_line(docs, line)
    common.append_line(matter / "log.md", common.join_pipe(
        [state.ctx.stamp(), "filed a second copy of %s (same email from another mailbox); not read again" % first,
         "correspondence/" + dest.name, state.run]))
    state.say("copy", item, state.rel(dest), "same email as %s; recorded, not read again" % first)
    state.journal("filed", item, state.rel(dest), (reason + "; " if reason else "") + "copy of " + first, conf)
    if inside(src, state.root / CHECK_REL):
        resolve_note(state, src, state.rel(dest), reason)
    state.result.update({"destination": state.rel(dest), "matter": state.rel(matter.parent), "copy_of": first})


def drop_duplicate(state, src, sibling, same, matter, records):
    """Identical bytes are already filed: delete the inbox copy (the only deletion any tool makes)."""
    item = state.rel(src)
    from_please_check = inside(src, state.root / CHECK_REL)
    os.remove(str(src))
    state.say("duplicate-dropped", item, "", "identical to %s; inbox copy deleted" % state.rel(same))
    state.journal("duplicate-dropped", item, state.rel(same), "identical bytes already filed", "1")
    if sibling is not None:
        sib_sha = common.sha256_file(sibling)
        sib_item = state.rel(sibling)
        corr = Path(same).parent
        twin = (stored_copy(matter, records, sib_sha) if matter is not None else None) or \
            identical_on_disk([corr / (Path(same).stem + ".msg")], sib_sha)
        if twin is not None:
            os.remove(str(sibling))
            state.say("duplicate-dropped", sib_item, "", "identical to %s; inbox copy deleted" % state.rel(twin))
            state.journal("duplicate-dropped", sib_item, state.rel(twin), "identical bytes already filed", "1")
        else:
            sib_dest = et.unique_path(corr, Path(same).stem + ".msg")
            move_file(sibling, sib_dest)
            state.say("moved original", sib_item, state.rel(sib_dest))
            if matter is not None:
                common.append_line(documents_path(matter), doc_line(
                    sib_dest.name, "correspondence", "received", "", "", "", sib_sha,
                    "no: original of %s" % Path(same).name))
    if from_please_check:
        resolve_note(state, src, state.rel(same), "identical email already filed")
    state.result.update({"destination": state.rel(same), "duplicate_of": state.rel(same)})


def drop_converted_duplicate(state, src, sibling, twin):
    """The .msg original is identical to one already filed: drop it and the .eml converted from it."""
    item = state.rel(sibling)
    from_please_check = inside(src, state.root / CHECK_REL)
    os.remove(str(sibling))
    os.remove(str(src))
    state.say("duplicate-dropped", item, "", "identical to %s; inbox copy and its converted %s deleted"
              % (state.rel(twin), Path(src).name))
    state.journal("duplicate-dropped", item, state.rel(twin), "identical .msg already filed; converted .eml dropped", "1")
    if from_please_check:
        resolve_note(state, src, state.rel(twin), "identical email already filed")
    state.result.update({"destination": state.rel(twin), "duplicate_of": state.rel(twin)})


def msg_twin(sibling, candidates, matter=None, records=()):
    """A filed file with exactly the bytes of the .msg sibling, or None."""
    if sibling is None:
        return None
    sha_ = common.sha256_file(sibling)
    if matter is not None:
        hit = stored_copy(matter, records, sha_)
        if hit is not None:
            return hit
    return identical_on_disk(candidates, sha_)


def cross_ref(state, target_value, primary, filed_path, p, reason, conf):
    other = resolve_matter(state.root, target_value, "--cross-ref")
    pref = et._matter_ref(primary.parent if primary.name == common.AGENT else primary) or state.rel(primary)
    subject = p.subject or "(no subject)"
    common.append_line(other / "log.md", common.join_pipe(
        [state.ctx.stamp(), "cross-ref: email filed in %s also concerns this matter: %s" % (pref, subject),
         state.rel(filed_path), state.run]))
    state.journal("cross-ref", state.rel(filed_path), state.rel(other.parent), reason, conf)
    state.say("cross-ref", state.rel(filed_path), state.rel(other / "log.md"))

# ---------------------------------------------------------------- noise


def next_noise_id(rows):
    high = 0
    for r in rows:
        m = common.NOISE_RE.match((r.get("id") or "").strip())
        if m:
            high = max(high, int(m.group(1)))
    return "NOISE-%04d" % (high + 1)


def _csv_line(values):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(values)
    return buf.getvalue()


def append_csv_row(path, columns, values):
    """Append one CSV row (CRLF). A new file gets a BOM and the header, as common.write_csv writes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with open(str(path), "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(_csv_line(columns) + _csv_line(values))
        return
    with open(str(path), "rb") as fh:
        fh.seek(-1, os.SEEK_END)
        needs_nl = fh.read(1) not in (b"\n", b"\r")
    with open(str(path), "a", encoding="utf-8", newline="") as fh:
        fh.write(("\r\n" if needs_nl else "") + _csv_line(values))


def ensure_noise_csv(path):
    """Create NOISE.csv with its header if absent; refuse early if it cannot be written."""
    path = Path(path)
    try:
        if not path.exists() or path.stat().st_size == 0:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(path), "w", encoding="utf-8-sig", newline="") as fh:
                fh.write(_csv_line(common.NOISE_COLUMNS))
        with open(str(path), "a", encoding="utf-8", newline=""):
            pass
    except OSError as exc:
        raise Refusal("cannot write %s: %s (close it in Excel and run again)" % (NOISE_REL, exc))


def place_noise(state, src, p, args):
    noise_dir = state.root / NOISE_DIR_REL
    item = state.rel(src)
    sibling = msg_sibling(src)
    same = identical_on_disk(et.candidate_paths(noise_dir, p.canonical_name)
                             + et.candidate_paths(noise_dir / "confirmed", p.canonical_name), p.sha256)
    if same is not None:
        drop_duplicate(state, src, sibling, same, None, [])
        return
    stem_msg = Path(p.canonical_name).stem + ".msg"
    twin = msg_twin(sibling, et.candidate_paths(noise_dir, stem_msg) + et.candidate_paths(noise_dir / "confirmed", stem_msg))
    if twin is not None:
        drop_converted_duplicate(state, src, sibling, twin)
        return
    csv_path = state.root / NOISE_REL
    ensure_noise_csv(csv_path)
    from_please_check = inside(src, state.root / CHECK_REL)
    dest = et.unique_path(noise_dir, p.canonical_name)
    move_file(src, dest)
    state.say("noise", item, state.rel(dest))
    if sibling is not None:
        sib_item = state.rel(sibling)
        sib_dest = move_file(sibling, et.unique_path(noise_dir, dest.stem + ".msg"))
        state.say("moved original", sib_item, state.rel(sib_dest))
    rows = common.read_csv(csv_path)
    nid = next_noise_id(rows)
    title = args.title or p.subject or "(no subject)"
    label = args.label if args.label is not None else (p.info["noise_hints"][0] if p.info["noise_hints"] else "")
    append_csv_row(csv_path, common.NOISE_COLUMNS, [
        nid, state.rel(dest), p.info["date"], p.from_addr, p.subject, title, label,
        "waiting_lawyer", "nothing_needed", "", ""])
    state.say("noise row", nid, NOISE_REL, title)
    state.journal("noise", item, state.rel(dest), args.reason or "", args.confidence or "")
    if from_please_check:
        resolve_note(state, src, state.rel(dest) + " as " + nid, args.reason or "")
    state.result.update({"destination": state.rel(dest), "noise_id": nid})

# ---------------------------------------------------------------- please-check


def place_check(state, src, p, args):
    check_dir = state.root / CHECK_REL
    if Path(src).resolve().parent == check_dir.resolve():
        raise Refusal("already in please-check: %s" % state.rel(src))
    item = state.rel(src)
    sibling = msg_sibling(src)
    same = identical_on_disk(et.candidate_paths(check_dir, p.canonical_name), p.sha256)
    if same is not None:
        drop_duplicate(state, src, sibling, same, None, [])
        return
    twin = msg_twin(sibling, et.candidate_paths(check_dir, Path(p.canonical_name).stem + ".msg"))
    if twin is not None:
        drop_converted_duplicate(state, src, sibling, twin)
        return
    note_text = args.note or args.reason
    dest = et.unique_path(check_dir, p.canonical_name)
    note_path = Path(str(dest) + ".note.md")
    move_file(src, dest)
    state.say("please-check", item, state.rel(dest))
    if sibling is not None:
        sib_item = state.rel(sibling)
        sib_dest = move_file(sibling, et.unique_path(check_dir, dest.stem + ".msg"))
        state.say("moved original", sib_item, state.rel(sib_dest))
    meta = {
        "file": state.rel(dest),
        "received": p.info["date"],
        "from": p.from_addr,
        "subject": p.subject,
        "claimed_reference": args.claimed or "",
        "candidates": ", ".join(args.candidate_list),
        "run": state.run,
    }
    example = (args.candidate_list or [args.claimed or "<reference>"])[0]
    body = ("# Please check: %s\n\n%s\n\nTo settle it, tell the agent where this email belongs "
            "(for example \"file it in %s\"), or that it is noise.\n"
            % (p.subject or "(no subject)", note_text.strip(), example))
    common.write_text_atomic(note_path, common.render_frontmatter(meta, body))
    state.say("note", state.rel(note_path))
    state.journal("please-check", item, state.rel(dest), args.reason or note_text.strip().split("\n")[0],
                  args.confidence or "")
    state.result.update({"destination": state.rel(dest), "note": state.rel(note_path)})

# ---------------------------------------------------------------- loose files (not emails)


def _file_date(state, path):
    when = _dt.datetime.fromtimestamp(Path(path).stat().st_mtime, tz=_dt.timezone.utc)
    return state.ctx.to_house(when).strftime("%Y-%m-%d %H:%M")


def place_check_file(state, src, args):
    """A dropped file that is not an email: to please-check under its own name, with a note."""
    check_dir = state.root / CHECK_REL
    if Path(src).resolve().parent == check_dir.resolve():
        raise Refusal("already in please-check: %s" % state.rel(src))
    item = state.rel(src)
    received = _file_date(state, src)
    dest = et.unique_path(check_dir, Path(src).name)
    move_file(src, dest)
    state.say("please-check", item, state.rel(dest), "not an email")
    note_path = Path(str(dest) + ".note.md")
    meta = {"file": state.rel(dest), "received": received, "from": "", "subject": "",
            "claimed_reference": args.claimed or "", "candidates": ", ".join(args.candidate_list),
            "run": state.run}
    example = (args.candidate_list or [args.claimed or "<reference>"])[0]
    body = ("# Please check: %s\n\n%s\n\nThis file is not an email. To settle it, tell the agent which "
            "matter it belongs to (for example \"file it in %s\"), or that it can stay here.\n"
            % (dest.name, (args.note or args.reason).strip(), example))
    common.write_text_atomic(note_path, common.render_frontmatter(meta, body))
    state.say("note", state.rel(note_path))
    state.journal("please-check", item, state.rel(dest), args.reason or "not an email", args.confidence or "")
    state.result.update({"file": item, "destination": state.rel(dest), "note": state.rel(note_path)})


def place_file_matter(state, src, matter, args):
    """A loose file from please-check into the matter's documents/received/ (never deleted)."""
    item = state.rel(src)
    docs = documents_path(matter)
    records = common.read_pipe_records(docs, common.DOCUMENTS_COLUMNS)
    sha = common.sha256_file(src)
    known = stored_hashes(records)
    date = _file_date(state, src)
    target = matter / "documents" / "received"
    dest = et.unique_path(target, Path(src).name)
    move_file(src, dest)
    state.say("filed", item, state.rel(dest), "not an email")
    if sha in known:
        line = doc_line(dest.name, "documents/received", "received", "", date, "", sha,
                        "no: duplicate of %s" % known[sha], known[sha])
    else:
        line = doc_line(dest.name, "documents/received", "received", "", date, "", sha, "pending")
    common.append_line(docs, line)
    common.append_line(matter / "log.md", common.join_pipe(
        [state.ctx.stamp(), "filed loose file %s (from please-check)" % dest.name,
         "documents/received/" + dest.name, state.run]))
    state.journal("filed", item, state.rel(dest), args.reason or "", args.confidence or "")
    resolve_note(state, src, state.rel(dest), args.reason or "")
    state.result.update({"file": item, "destination": state.rel(dest), "matter": state.rel(matter.parent)})

# ---------------------------------------------------------------- register


FOLDER_ORIGIN = (("human", "human"), ("work-product", "work-product"), ("documents/ours", "ours"),
                 ("documents/reference", "reference"), ("drafts", "ours"))


def matter_of(root, path):
    """The matter's agent/ folder for a path inside the matter (agent/ or human/), or None."""
    d = common.matter_of_path(root, path)
    return common.agent_dir(d) if d is not None else None


def register(state, value):
    path = resolve_input(state.root, value)
    if not os.path.isfile(common.os_path(path)):
        raise Refusal("no file: %s" % value)
    matter = matter_of(state.root, path)
    if matter is None:
        raise Refusal("--register takes a file inside a matter folder (areas/.../<reference>_...): %s" % value)
    root_rel = Path(path).resolve().relative_to(matter.parent).as_posix()
    if root_rel.startswith(common.HUMAN + "/"):
        rel_in = root_rel                      # human/...: kept relative to the matter folder
    elif root_rel.startswith(common.AGENT + "/"):
        rel_in = root_rel[len(common.AGENT) + 1:]
    else:
        raise Refusal("--register takes a file in the matter's agent/ or human/ folder: %s" % value)
    folder = rel_in.rsplit("/", 1)[0] if "/" in rel_in else ""
    name = Path(path).name
    parts = rel_in.split("/")[:-1]
    if not folder or "history" in parts or (folder == common.HUMAN and name in common.HUMAN_ONLY_NAMES):
        raise Refusal("--register takes a received or added file, not a memory file or history copy: %s" % value)
    if any(x.startswith("bundle-") or x.endswith("_harvey-pack") for x in parts):
        raise Refusal("--register: files in a work bundle are copies; register the original instead: %s" % value)
    docs = documents_path(matter)
    records = common.read_pipe_records(docs, common.DOCUMENTS_COLUMNS)
    sha = common.sha256_file(path)
    for r in records:
        if r.get("folder") == folder and (r.get("name") == name):
            state.say("already registered", state.rel(path))
            state.result.update({"destination": state.rel(path), "registered": False})
            return
    known = stored_hashes(records)
    origin = "received"
    for prefix, org in FOLDER_ORIGIN:
        if folder == prefix or folder.startswith(prefix + "/"):
            origin = org
    rows = []
    if et.is_email_file(path):
        p = et.parse_email(path, state.ctx)
        if folder == "correspondence":
            origin = "ours" if p.direction == "out" else "received"
        if sha in known:
            rows.append(doc_line(name, folder, origin, p.from_addr, p.info["date"], p.message_id, sha,
                                 "no: duplicate of %s" % known[sha], known[sha]))
            state.say("registered", state.rel(path), "", "duplicate of %s" % known[sha])
        else:
            rows.append(doc_line(name, folder, origin, p.from_addr, p.info["date"], p.message_id, sha,
                                 "pending"))
            state.say("registered", state.rel(path))
            records = records + [{"hash": sha, "folder": folder, "name": name, "duplicate_of": ""}]
            att_rows = []
            store_attachments(state, matter, p, records, att_rows)
            rows.extend(att_rows)
        event = "registered %s email from %s (put in by hand): %s" % (
            p.direction, p.from_addr or "unknown sender", p.subject or "(no subject)")
    else:
        when = state.ctx.to_house(_dt.datetime.fromtimestamp(os.stat(common.os_path(path)).st_mtime,
                                                             tz=_dt.timezone.utc))
        date = when.strftime("%Y-%m-%d %H:%M")
        if sha in known:
            rows.append(doc_line(name, folder, origin, "", date, "", sha, "no: duplicate of %s" % known[sha],
                                 known[sha]))
            state.say("registered", state.rel(path), "", "duplicate of %s" % known[sha])
        else:
            rows.append(doc_line(name, folder, origin, "", date, "", sha, "pending"))
            state.say("registered", state.rel(path))
        if et.is_msg_file(path):
            state.say("hint", "convert it with: bash tools/msg2eml %s, then register the .eml" % state.rel(path))
        event = "registered %s (put in by hand)" % name
    for line in rows:
        common.append_line(docs, line)
    common.append_line(matter / "log.md", common.join_pipe([state.ctx.stamp(), event, rel_in, state.run]))
    state.journal("filed", state.rel(path), state.rel(matter.parent), "registered in place (put there by hand)", "")
    state.result.update({"destination": state.rel(path), "matter": state.rel(matter.parent), "registered": True})

# ---------------------------------------------------------------- main


def check_args(args):
    if args.confidence is not None:
        try:
            c = float(args.confidence)
        except ValueError:
            raise Refusal("--confidence must be a number from 0 to 1")
        if not 0 <= c <= 1:
            raise Refusal("--confidence must be a number from 0 to 1")
        args.confidence = args.confidence.strip()
    args.candidate_list = []
    if args.candidates:
        for ref in [c.strip() for c in args.candidates.replace(";", ",").split(",") if c.strip()]:
            if not common.REF_RE.match(ref):
                raise Refusal("--candidates: not a reference: %s" % ref)
            args.candidate_list.append(ref)
    if args.claimed and not common.REF_RE.match(args.claimed.strip("[] ")):
        raise Refusal("--claimed: not a reference: %s" % args.claimed)
    if args.claimed:
        args.claimed = args.claimed.strip("[] ")


def place(state, args):
    root = state.root
    src = resolve_input(root, args.file)
    if et.is_msg_file(src):
        raise Refusal("convert first: bash tools/msg2eml %s" % args.file)
    if not Path(src).is_file():
        raise Refusal("no file: %s" % args.file)
    inbox = root / "inbox"
    if not inside(src, inbox) or inside(src, inbox / "noise") or inside(src, root / CHECK_REL / "resolved"):
        raise Refusal("refused: %s is not in inbox/ or inbox/please-check/. place-email moves inbox emails only; "
                      "for a file put into a matter by hand use: bash tools/place-email --register PATH"
                      % args.file)
    to = args.to
    matter = None
    if to not in ("noise", "please-check"):
        matter = resolve_matter(root, to)
    if args.cross_ref:
        resolve_matter(root, args.cross_ref, "--cross-ref")
        if matter is None:
            raise Refusal("--cross-ref is for emails filed into a matter")
    if to == "please-check" and not (args.note or args.reason):
        raise Refusal("please-check needs --note: why you are unsure, what you would do, what the lawyer should decide")
    if not et.is_email_file(src):
        # A loose file (not an email): please-check first; into a matter only from please-check.
        if to == "please-check":
            place_check_file(state, src, args)
            return
        if matter is not None and inside(src, root / CHECK_REL) and not args.cross_ref:
            place_file_matter(state, src, matter, args)
            return
        raise Refusal("not an .eml file: %s. Loose files go to please-check first: bash tools/place-email "
                      "FILE --to please-check --note TEXT; after the lawyer decides, place it from "
                      "inbox/please-check/ into the matter." % args.file)
    try:
        p = et.parse_email(src, state.ctx)
    except OSError as exc:
        raise Failure("cannot read %s: %s" % (args.file, exc))
    state.result.update({"file": state.rel(src), "canonical_name": p.canonical_name,
                         "direction": p.direction, "message_id": p.message_id})
    if to == "noise":
        place_noise(state, src, p, args)
    elif to == "please-check":
        place_check(state, src, p, args)
    else:
        place_matter(state, src, p, matter, args)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/place-email",
                                 description="Move one inbox email into a matter, noise or please-check.")
    ap.add_argument("file", nargs="?", metavar="FILE")
    ap.add_argument("--to", metavar="MATTER_FOLDER|REF|noise|please-check")
    ap.add_argument("--register", metavar="PATH_INSIDE_MATTER")
    ap.add_argument("--run")
    ap.add_argument("--reason")
    ap.add_argument("--confidence")
    ap.add_argument("--note")
    ap.add_argument("--title")
    ap.add_argument("--label")
    ap.add_argument("--claimed", metavar="REF")
    ap.add_argument("--candidates", metavar="REF,REF")
    ap.add_argument("--cross-ref", metavar="MATTER_FOLDER")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    ctx = et.Context(common.find_root())
    state = Run(ctx, args.run or ctx.run_id(), args.json)
    try:
        check_args(args)
        if args.register:
            if args.file or args.to:
                raise Refusal("--register takes one path inside a matter, without FILE or --to")
            register(state, args.register)
        else:
            if not args.file or not args.to:
                ap.print_usage(sys.stderr)
                raise Refusal("give FILE and --to <matter folder|reference|noise|please-check>, or --register PATH")
            place(state, args)
    except Refusal as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    except (Failure, OSError) as exc:
        if isinstance(exc, OSError):
            exc = Failure("could not complete: %s" % exc)
        sys.stderr.write(str(exc) + "\n")
        if args.json:
            state.result["error"] = str(exc)
            state.result["actions"] = state.actions
            sys.stdout.write(json.dumps(state.result, ensure_ascii=False, indent=2) + "\n")
        return 1
    if args.json:
        state.result["actions"] = state.actions
        sys.stdout.write(json.dumps(state.result, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
