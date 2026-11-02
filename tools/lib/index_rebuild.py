"""index-rebuild: apply the lawyer's INDEX.csv edits, rebuild INDEX.csv and INDEX.md, write digest parts.

Run through the wrapper:
  bash tools/index-rebuild [--today YYYY-MM-DD] [--run RUN] [--digest-parts FILE] [--no-apply]
                           [--confirm-noise IDS] [--json]
Spec D11. Steps: 1 human edits (INDEX.csv against changes/INDEX.generated.csv, cell by cell, rows
matched by reference); 2 rows from every matter.md and NOISE.csv; 3 sort; 4 write INDEX.csv
(UTF-8 BOM, CRLF), the byte copy changes/INDEX.generated.csv, INDEX.md; 5 digest parts;
6 integrity. Exit 0 ok, 1 integrity problems, 2 usage error.
"""

import argparse
import csv
import datetime as _dt
import decimal
import io
import json
import re
import shutil
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

STALE_DAYS = 10            # RULES.md: stale after 10 days
RECENT_CLOSED_DAYS = 30
REQUIRED_KEYS = ("reference", "area", "subject", "title", "status", "opened")
DATE_COLUMNS = ("opened", "last_activity", "due")
NUMBER_COLUMNS = ("days_open", "hours_to_ready", "lawyer_minutes")
CASELESS_COLUMNS = ("kind", "status", "proposed_outcome", "confirmed_outcome",
                    "accepted_unchanged", "waiting_on")
NOISE_NEXT_STEP = "Confirm as nothing needed"
BOM = b"\xef\xbb\xbf"
NOISE_ID_FIND = re.compile(r"NOISE-[0-9]{4,}")


# ---------------------------------------------------------------- small helpers

def strict_date(s):
    s = (s or "").strip()
    if not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", s):
        return None
    try:
        return _dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None


def any_date(s):
    """A date from the first 10 characters (frontmatter dates, 'YYYY-MM-DD HH:MM')."""
    return strict_date((s or "").strip()[:10])


def to_number(s):
    s = (s or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fmt_number(x):
    """Round half up to 0.1 and drop a trailing .0: 2.25 -> '2.3', 4.0 -> '4'."""
    if x is None:
        return ""
    d = decimal.Decimal(repr(float(x))).quantize(decimal.Decimal("0.1"), rounding=decimal.ROUND_HALF_UP)
    s = format(d, "f")
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s in ("-0", "") else s


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def md_cell(v):
    return str("" if v is None else v).replace("\n", " ").replace("|", "\\|").strip()


def norm_outcome(v):
    return re.sub(r"[\s-]+", "_", (v or "").strip().lower())


def norm_yes_no(v):
    v = (v or "").strip().lower()
    if v in ("y", "yes", "true", "1"):
        return "yes"
    if v in ("n", "no", "false", "0"):
        return "no"
    return None


def add_flag(flags, flag):
    items = [f.strip() for f in (flags or "").split(",") if f.strip()]
    if flag not in items:
        items.append(flag)
    return ", ".join(items)


class Report:
    def __init__(self):
        self.applied = []          # dicts: ref, column, old, new, file
        self.closed = []           # references closed by the lawyer
        self.noise_confirmed = []  # dicts: id, file
        self.pending = []          # --no-apply: what would happen
        self.warnings = []
        self.integrity = []
        self.notes = []
        self.written = []


# ---------------------------------------------------------------- CSV in and out

def decode_csv_bytes(data):
    if data.startswith(BOM):
        data = data[len(BOM):]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")  # Excel "CSV (Comma delimited)"
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_csv_tolerant(path):
    """Rows of a CSV the human may have saved from Excel: BOM or not, UTF-8 or cp1252, ',' or ';'."""
    text = decode_csv_bytes(Path(path).read_bytes())
    first = text.split("\n", 1)[0]
    delim = ";" if first.count(";") > first.count(",") else ","
    rows = []
    for r in csv.DictReader(io.StringIO(text), delimiter=delim):
        rows.append({(k or "").strip(): ("" if v is None else v) for k, v in r.items()
                     if k is not None and not isinstance(v, list)})
    return rows


def read_noise(root):
    """(path, columns, rows, fmt). fmt keeps the file's BOM and line endings for rewriting."""
    path = Path(root) / "inbox" / "noise" / "NOISE.csv"
    fmt = {"bom": False, "eol": "\n"}
    if not path.is_file():
        return path, list(common.NOISE_COLUMNS), [], fmt
    data = path.read_bytes()
    fmt["bom"] = data.startswith(BOM)
    fmt["eol"] = "\r\n" if b"\r\n" in data else "\n"
    reader = csv.DictReader(io.StringIO(decode_csv_bytes(data)))
    columns = [c.strip() for c in (reader.fieldnames or [])] or list(common.NOISE_COLUMNS)
    rows = []
    for r in reader:
        row = {(k or "").strip(): ("" if v is None else v.strip()) for k, v in r.items()
               if k is not None and not isinstance(v, list)}
        if any(row.values()):
            rows.append(row)
    for c in common.NOISE_COLUMNS:
        if c not in columns:
            columns.append(c)
    return path, columns, rows, fmt


def write_noise(path, columns, rows, fmt):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator=fmt["eol"])
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") or "" for c in columns})
    common.write_text_atomic(path, buf.getvalue(), encoding="utf-8-sig" if fmt["bom"] else "utf-8")


# ---------------------------------------------------------------- journal and log

def journal(root, run, action, item, destination, reason, confidence="-"):
    path = Path(root) / "JOURNAL.md"
    if not path.exists():
        common.append_line(path, "# " + " | ".join(common.JOURNAL_COLUMNS))  # same header as place-email
    common.append_line(path, common.join_pipe([common.stamp(root), run, action, item,
                                               destination, reason, confidence]))


def matter_log(root, mdir, run, event):
    common.append_line(Path(mdir) / "log.md",
                       common.join_pipe([common.stamp(root), event, "INDEX.csv", run]))


# ---------------------------------------------------------------- matters and noise

def collect_matters(root):
    """(folder, meta) for every matter.md under areas/, outside history/ and work-product/,
    and not nested inside another matter folder. Superset of common.iter_matters: folders
    whose name lacks a reference are kept so the integrity check can report them."""
    areas = Path(root) / "areas"
    out = []
    if not areas.is_dir():
        return out
    for mfile in sorted(areas.rglob("matter.md")):
        d = mfile.parent
        relparts = d.relative_to(areas).parts
        if "history" in relparts or "work-product" in relparts:
            continue
        nested = False
        cur = d.parent
        while cur != areas and areas in cur.parents:
            if (cur / "matter.md").is_file():
                nested = True
                break
            cur = cur.parent
        if nested:
            continue
        meta, _ = common.read_frontmatter_file(mfile)
        out.append((d, meta))
    return out


def matter_ref(d, meta):
    ref = (meta.get("reference") or "").strip()
    if ref:
        return ref
    m = common.MATTER_DIR_RE.match(d.name)
    return m.group(1) if m else ""


def noise_file_path(root, row):
    v = (row.get("file") or "").strip()
    if not v:
        return None
    if "/" in v or "\\" in v:
        return Path(root) / v.replace("\\", "/")
    p = Path(root) / "inbox" / "noise" / v
    c = Path(root) / "inbox" / "noise" / "confirmed" / v
    if c.exists() and (not p.exists() or (row.get("status") or "").strip() == "closed"):
        return c
    return p


def unique_dest(dest):
    if not dest.exists():
        return dest
    n = 2
    while True:
        cand = dest.with_name("%s-%d%s" % (dest.stem, n, dest.suffix))
        if not cand.exists():
            return cand
        n += 1


def matter_row(root, d, meta, today):
    area, sub, subj = common.matter_location(root, d)
    status = (meta.get("status") or "").strip()
    opened = any_date(meta.get("opened"))
    end = today
    if status == "closed":
        end = any_date(meta.get("closed")) or any_date(meta.get("last_activity")) or today
    days = (end - opened).days if opened else ""
    hours = ""
    a = common.parse_datetime(meta.get("arrived") or "")
    b = common.parse_datetime(meta.get("ready_at") or "")
    if a and b:
        hours = fmt_number((b - a).total_seconds() / 3600.0)

    def g(k):
        return (meta.get(k) or "").strip()

    return {
        "reference": matter_ref(d, meta), "kind": g("kind") or "matter",
        "area": g("area") or area, "sub_area": g("sub_area") or sub, "subject": g("subject") or subj,
        "title": g("title"), "label": g("label"), "status": status,
        "proposed_outcome": g("proposed_outcome"), "confirmed_outcome": g("confirmed_outcome"),
        "confirmed_by": g("confirmed_by"), "opened": g("opened"), "last_activity": g("last_activity"),
        "days_open": days, "requester": g("requester"), "counterparty": g("counterparty"),
        "waiting_on": g("waiting_on"), "next_step": g("next_step"), "due": g("due"),
        "hours_to_ready": hours, "lawyer_minutes": g("lawyer_minutes"),
        "accepted_unchanged": g("accepted_unchanged"), "follows": g("follows"),
        "folder": common.rel(d, root), "_closed": end.isoformat() if status == "closed" else "",
    }


def noise_row(root, nr, today):
    status = (nr.get("status") or "").strip() or "waiting_lawyer"
    received = any_date(nr.get("received"))
    is_open = status != "closed"
    path = noise_file_path(root, nr)
    day = received.isoformat() if received else ""
    return {
        "reference": (nr.get("id") or "").strip(), "kind": "noise", "area": "", "sub_area": "",
        "subject": "", "title": (nr.get("title") or "").strip() or (nr.get("subject") or "").strip(),
        "label": (nr.get("label") or "").strip(), "status": status,
        "proposed_outcome": "nothing_needed",
        "confirmed_outcome": (nr.get("confirmed_outcome") or "").strip(),
        "confirmed_by": (nr.get("confirmed_by") or "").strip(),
        "opened": day, "last_activity": day,
        "days_open": (today - received).days if (received and is_open) else "",
        "requester": "", "counterparty": "", "waiting_on": "you" if is_open else "",
        "next_step": NOISE_NEXT_STEP if is_open else "", "due": "", "hours_to_ready": "",
        "lawyer_minutes": "", "accepted_unchanged": "", "follows": "",
        "folder": common.rel(path, root) if path else "",
        "_received": (nr.get("received") or "").strip(), "_closed": "",
    }


def sort_rows(rows):
    def closed(r):
        return r["status"] == "closed"

    def open_key(r):
        due = any_date(r["due"])
        days = r["days_open"] if isinstance(r["days_open"], int) else None
        return (due is None, due or _dt.date.max, days is None, -(days or 0), r["reference"])

    def closed_key(r):
        la = any_date(r["last_activity"])
        return (la is None, -(la.toordinal() if la else 0), r["reference"])

    matters = [r for r in rows if r["kind"] != "noise"]
    noise = [r for r in rows if r["kind"] == "noise"]
    out = sorted([r for r in matters if not closed(r)], key=open_key)
    out += sorted([r for r in matters if closed(r)], key=closed_key)
    out += sorted(noise, key=lambda r: (closed(r), r["reference"]))
    return out


# ---------------------------------------------------------------- step 1: human edits

def same_cell(col, gen, hum):
    a, b = (gen or "").strip(), (hum or "").strip()
    if a == b:
        return True
    if col in CASELESS_COLUMNS and a.lower() == b.lower():
        return True
    if col in DATE_COLUMNS and a and b:
        da, db = excel_dates(a), excel_dates(b)
        if da and db and (da & db):
            return True
    if col in NUMBER_COLUMNS and a and b:
        na, nb = to_number(a), to_number(b)
        if na is not None and nb is not None and abs(na - nb) < 1e-9:
            return True
    return False


def excel_dates(s):
    """Every date a cell could mean: Excel rewrites ISO dates in the local short format."""
    out = set()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d", "%d-%m-%Y",
                "%d/%m/%y", "%m/%d/%y", "%d.%m.%y"):
        try:
            out.add(_dt.datetime.strptime(s.strip(), fmt).date())
        except ValueError:
            pass
    return out


def detect_edits(root, rep):
    """List of edits (ref, kind, column, old, new) typed into INDEX.csv since it was generated."""
    idx = Path(root) / "INDEX.csv"
    gen = Path(root) / "changes" / "INDEX.generated.csv"
    if not idx.is_file():
        return []
    if not gen.is_file():
        rep.warnings.append("changes/INDEX.generated.csv is missing, so edits typed into INDEX.csv "
                            "cannot be detected this time (first run)")
        return []
    human = read_csv_tolerant(idx)
    base = read_csv_tolerant(gen)
    base_by_ref = {}
    for r in base:
        ref = (r.get("reference") or "").strip()
        if ref and ref not in base_by_ref:
            base_by_ref[ref] = r
    edits = []
    seen = set()
    for r in human:
        ref = (r.get("reference") or "").strip()
        if not ref:
            if any((v or "").strip() for v in r.values()):
                rep.warnings.append("INDEX.csv has a row without a reference; it was ignored")
            continue
        if ref in seen:
            rep.warnings.append("%s appears twice in INDEX.csv; only the first row was read" % ref)
            continue
        seen.add(ref)
        b = base_by_ref.get(ref)
        if b is None:
            rep.warnings.append("%s: this row is not in the last generated index, so it was ignored "
                                "(rows come from the matter files)" % ref)
            continue
        kind = (b.get("kind") or "").strip().lower() or ("noise" if common.NOISE_RE.match(ref) else "matter")
        for col in common.INDEX_COLUMNS:
            if col == "reference" or col not in r or col not in b:
                continue
            if not same_cell(col, b[col], r[col]):
                edits.append((ref, kind, col, (b[col] or "").strip(), (r[col] or "").strip()))
    for ref in base_by_ref:
        if ref not in seen:
            rep.warnings.append("%s: the row was deleted from INDEX.csv; it comes back from the matter files" % ref)
    return edits


def normalise_human(ref, col, value, rep):
    v = (value or "").strip()
    if not v:
        return ""
    if col == "confirmed_outcome":
        k = norm_outcome(v)
        if k in common.OUTCOMES:
            return k
        rep.warnings.append("%s: confirmed_outcome '%s' is not one of %s; written as typed"
                            % (ref, v, ", ".join(common.OUTCOMES)))
    elif col == "accepted_unchanged":
        k = norm_yes_no(v)
        if k:
            return k
        rep.warnings.append("%s: accepted_unchanged '%s' is not yes or no; written as typed" % (ref, v))
    elif col == "lawyer_minutes":
        n = to_number(v)
        if n is not None:
            return fmt_number(n)
        rep.warnings.append("%s: lawyer_minutes '%s' is not a number; written as typed" % (ref, v))
    return v


def kept_by_agent(rep, ref, col):
    rep.warnings.append("%s: column %s is kept by the agent; say it in chat instead" % (ref, col))


def apply_matter_edits(root, ref, edits, mdir, run, today, apply, rep):
    mfile = mdir / "matter.md"
    meta, _ = common.read_frontmatter_file(mfile)
    updates = {}
    log_bits = []
    closing = False
    for _, _, col, old, new in edits:
        if col in common.HUMAN_COLUMNS:
            val = normalise_human(ref, col, new, rep)
            updates[col] = val
            log_bits.append("%s=%s" % (col, val or "(cleared)"))
        elif col == "status":
            if new.strip().lower() == "closed":
                if (meta.get("status") or "").strip() != "closed":
                    closing = True
                    updates["status"] = "closed"
                    updates["closed"] = today.isoformat()
                    updates["flags"] = add_flag(meta.get("flags", ""), "wrap-up-pending")
            else:
                kept_by_agent(rep, ref, col)
        elif col == "title":
            if not new.strip():
                rep.warnings.append("%s: the title was emptied in INDEX.csv; a matter needs a title, so it was kept" % ref)
            else:
                updates["title"] = new.strip()
                updates["title_locked"] = "yes"
        else:
            kept_by_agent(rep, ref, col)
    # Only what differs from matter.md: the agent may already hold the value (said in chat).
    updates = dict((k, v) for k, v in updates.items() if (meta.get(k) or "").strip() != v)
    log_bits = [b for b in log_bits if b.split("=", 1)[0] in updates]
    if not updates:
        return
    rel_m = common.rel(mfile, root)
    if not apply:
        for k, v in updates.items():
            rep.pending.append("would set %s %s = %s (%s)" % (ref, k, v, rel_m))
        if closing:
            rep.pending.append("would close %s: the lawyer typed closed in INDEX.csv" % ref)
        return
    common.update_frontmatter_file(mfile, updates)
    for k, v in updates.items():
        old = (meta.get(k) or "").strip()
        rep.applied.append({"ref": ref, "column": k, "old": old, "new": v, "file": rel_m})
        if k in ("status", "closed", "flags", "title_locked"):
            continue
        journal(root, run, "human-edit-applied", "%s %s" % (ref, k), rel_m,
                "typed in INDEX.csv: '%s' (was '%s')" % (v, old))
    if closing:
        rep.closed.append(ref)
        journal(root, run, "closed-by-lawyer", ref, common.rel(mdir, root),
                "the lawyer typed closed in INDEX.csv; wrap-up pending")
        matter_log(root, mdir, run, "closed by the lawyer in INDEX.csv; wrap-up pending")
    if "title" in updates:
        matter_log(root, mdir, run, "title changed by the lawyer in INDEX.csv: %s" % updates["title"])
    if log_bits:
        matter_log(root, mdir, run, "lawyer columns updated in INDEX.csv: %s" % ", ".join(log_bits))


def confirm_noise(root, ids, run, apply, rep, outcome="nothing_needed", by="you", how="INDEX.csv"):
    """Close noise rows: move each file to inbox/noise/confirmed/ and update NOISE.csv (spec D11 1d)."""
    path, columns, rows, fmt = read_noise(root)
    by_id = {(r.get("id") or "").strip(): r for r in rows}
    moves = []
    for nid, out, who in ids:
        r = by_id.get(nid)
        if r is None:
            rep.warnings.append("%s: not in inbox/noise/NOISE.csv; nothing to confirm" % nid)
            continue
        if (r.get("status") or "").strip() == "closed":
            rep.notes.append("%s: already confirmed" % nid)
            continue
        out = out or outcome
        who = who or by
        if norm_outcome(out) != "nothing_needed":
            rep.warnings.append("%s: confirmed outcome is %s, not nothing_needed; if this email needs "
                                "work, ask the agent to file it into a matter" % (nid, out))
        src = noise_file_path(root, r)
        dest = None
        confirmed_dir = Path(root) / "inbox" / "noise" / "confirmed"
        if src is not None and src.exists() and src.parent != confirmed_dir:
            dest = unique_dest(confirmed_dir / src.name)
        elif src is None or not src.exists():
            rep.warnings.append("%s: file %s not found; NOISE.csv updated anyway"
                                % (nid, r.get("file") or "(none recorded)"))
        if not apply:
            rep.pending.append("would confirm %s as %s%s" % (nid, out, (" and move it to " + common.rel(dest, root)) if dest else ""))
            continue
        r["status"] = "closed"
        r["confirmed_outcome"] = out
        r["confirmed_by"] = who
        if dest is not None:
            v = (r.get("file") or "").strip()
            r["file"] = common.rel(dest, root) if ("/" in v or "\\" in v) else dest.name
            moves.append((nid, src, dest))
        else:
            moves.append((nid, None, src))
        r["_how"] = "confirmed %s (%s)" % ("nothing needed" if norm_outcome(out) == "nothing_needed" else "as " + out, how)
    if not apply or not moves:
        return
    reasons = dict((nid, by_id[nid].pop("_how", "")) for nid, _, _ in moves)
    try:
        write_noise(path, columns, rows, fmt)
    except OSError as e:
        rep.warnings.append("could not update %s (%s); noise not confirmed" % (common.rel(path, root), e))
        return
    for nid, src, dest in moves:
        if src is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
        shown = common.rel(dest, root) if dest is not None else "(file not found)"
        rep.noise_confirmed.append({"id": nid, "file": shown})
        journal(root, run, "human-edit-applied", nid, shown, reasons.get(nid) or "confirmed (%s)" % how)


def apply_noise_edits(root, ref, edits, run, apply, rep):
    close = False
    outcome = ""
    by = ""
    for _, _, col, old, new in edits:
        if col == "status":
            if new.strip().lower() == "closed":
                close = True
            else:
                kept_by_agent(rep, ref, col)
        elif col == "confirmed_outcome":
            if new.strip():
                close = True
                outcome = normalise_human(ref, col, new, rep)
        elif col == "confirmed_by":
            by = new.strip()
        elif col in ("lawyer_minutes", "accepted_unchanged"):
            rep.warnings.append("%s: column %s is not kept for noise rows" % (ref, col))
        else:
            kept_by_agent(rep, ref, col)
    if close:
        confirm_noise(root, [(ref, outcome, by)], run, apply, rep)
    elif by:
        rep.warnings.append("%s: confirmed_by was typed but nothing was confirmed; type closed in "
                            "status, or a confirmed_outcome" % ref)


def apply_edits(root, edits, run, today, apply, rep):
    by_ref = {}
    order = []
    for e in edits:
        if e[0] not in by_ref:
            order.append(e[0])
        by_ref.setdefault(e[0], []).append(e)
    matters = {}
    for d, meta in collect_matters(root):
        matters.setdefault(matter_ref(d, meta), d)
    for ref in order:
        es = by_ref[ref]
        if es[0][1] == "noise":
            apply_noise_edits(root, ref, es, run, apply, rep)
        else:
            d = matters.get(ref)
            if d is None:
                rep.warnings.append("%s: matter not found under areas/; its INDEX.csv edits were not applied" % ref)
                continue
            apply_matter_edits(root, ref, es, d, run, today, apply, rep)


# ---------------------------------------------------------------- measures

def measures(rows):
    matters = [r for r in rows if r["kind"] != "noise"]
    closed = [r for r in matters if r["status"] == "closed"]
    mins = [to_number(r["lawyer_minutes"]) for r in closed]
    mins = [m for m in mins if m is not None]
    yes = sum(1 for r in matters if norm_yes_no(r["accepted_unchanged"]) == "yes")
    no = sum(1 for r in matters if norm_yes_no(r["accepted_unchanged"]) == "no")
    conf = [r for r in rows if (r["confirmed_outcome"] or "").strip()]
    agree = sum(1 for r in conf if norm_outcome(r["confirmed_outcome"]) == norm_outcome(r["proposed_outcome"]))
    hours = [to_number(r["hours_to_ready"]) for r in matters]
    hours = [h for h in hours if h is not None]
    return {
        "lawyer_minutes_per_matter": float(fmt_number(statistics.mean(mins))) if mins else None,
        "lawyer_minutes_n": len(mins),
        "accepted_unchanged_share": (yes / float(yes + no)) if (yes + no) else None,
        "accepted_unchanged_yes": yes, "accepted_unchanged_n": yes + no,
        "outcome_agreement_share": (agree / float(len(conf))) if conf else None,
        "outcome_agreement_agree": agree, "outcome_agreement_n": len(conf),
        "hours_to_ready_median": float(fmt_number(statistics.median(hours))) if hours else None,
        "hours_to_ready_n": len(hours),
    }


def measure_lines(m):
    def pct(x):
        return "%d%%" % int(round(x * 100))
    out = []
    if m["lawyer_minutes_per_matter"] is None:
        out.append("- Lawyer minutes per matter: n/a (no closed matter has minutes yet)")
    else:
        out.append("- Lawyer minutes per matter: %s (mean over %s)"
                   % (fmt_number(m["lawyer_minutes_per_matter"]), plural(m["lawyer_minutes_n"], "closed matter")))
    if m["accepted_unchanged_share"] is None:
        out.append("- Share of deliverables accepted unchanged: n/a (none marked yes or no yet)")
    else:
        out.append("- Share of deliverables accepted unchanged: %s (%d of %d)"
                   % (pct(m["accepted_unchanged_share"]), m["accepted_unchanged_yes"], m["accepted_unchanged_n"]))
    if m["outcome_agreement_share"] is None:
        out.append("- Agreement between proposed and confirmed outcome: n/a (no confirmed outcomes yet)")
    else:
        out.append("- Agreement between proposed and confirmed outcome: %s (%d of %d)"
                   % (pct(m["outcome_agreement_share"]), m["outcome_agreement_agree"], m["outcome_agreement_n"]))
    if m["hours_to_ready_median"] is None:
        out.append("- Hours from arrival to ready: n/a (no matter has both times yet)")
    else:
        out.append("- Hours from arrival to ready: %s (median over %s)"
                   % (fmt_number(m["hours_to_ready_median"]), plural(m["hours_to_ready_n"], "matter")))
    return out


# ---------------------------------------------------------------- INDEX.md

def area_order(root, rows):
    areas = common.parse_areas(root)
    keys = list(areas.keys())
    extra = sorted(set(r["area"] for r in rows) - set(keys))
    names = {k: (areas[k].get("name") or k) for k in keys}
    ordered = [k for k in keys if k != "general"] + [k for k in extra if k != "general"]
    if "general" in keys or "general" in extra:
        ordered.append("general")
    return ordered, names


def oldest_first(r):
    o = any_date(r["opened"])
    return (o is None, o or _dt.date.max, r["reference"])


def confirm_line(noise_open):
    return "confirm nothing needed: " + ", ".join(r["reference"] for r in noise_open)


def render_index_md(root, rows, today, mlines):
    open_m = [r for r in rows if r["kind"] != "noise" and r["status"] != "closed"]
    closed_m = [r for r in rows if r["kind"] != "noise" and r["status"] == "closed"]
    noise_open = [r for r in rows if r["kind"] == "noise" and r["status"] != "closed"]
    L = ["# Index", "",
         "Rebuilt by tools/index-rebuild on %s from the matter files. Do not edit this page. "
         "To change the columns you own (confirmed_outcome, confirmed_by, lawyer_minutes, "
         "accepted_unchanged), edit INDEX.csv. Type closed in its status column to close a matter." % today,
         "", "## Open matters", ""]
    if not open_m:
        L += ["None.", ""]
    order, names = area_order(root, open_m)
    for key in order:
        group = sorted([r for r in open_m if r["area"] == key], key=oldest_first)
        if not group:
            continue
        L += ["### %s" % names.get(key, key or "No area"), "",
              "| Reference | Title | Status | Waiting on | Next step | Due | Days open |",
              "|---|---|---|---|---|---|---|"]
        for r in group:
            L.append("| %s |" % " | ".join([ref_link(r)] + [md_cell(r[c]) for c in
                     ("title", "status", "waiting_on", "next_step", "due", "days_open")]))
        L.append("")
    L += ["## Noise awaiting confirmation", ""]
    if not noise_open:
        L += ["None.", ""]
    else:
        L += ["| Id | Title | Label | Received | File |", "|---|---|---|---|---|"]
        for r in noise_open:
            L.append("| %s |" % " | ".join(md_cell(x) for x in
                     (r["reference"], r["title"], r["label"], r.get("_received") or r["opened"], r["folder"])))
        L += ["", "To confirm them all, paste this line into chat:", "", confirm_line(noise_open), ""]
    L += ["## Closed in the last %d days" % RECENT_CLOSED_DAYS, ""]
    recent = []
    for r in closed_m:
        c = any_date(r.get("_closed")) or any_date(r["last_activity"])
        if c and 0 <= (today - c).days <= RECENT_CLOSED_DAYS:
            recent.append((c, r))
    recent.sort(key=lambda x: (-x[0].toordinal(), x[1]["reference"]))
    if not recent:
        L += ["None.", ""]
    else:
        L += ["| Reference | Title | Closed | Proposed | Confirmed | Lawyer minutes |",
              "|---|---|---|---|---|---|"]
        for c, r in recent:
            L.append("| %s |" % " | ".join([ref_link(r)] + [md_cell(x) for x in
                     (r["title"], c.isoformat(), r["proposed_outcome"],
                      r["confirmed_outcome"], r["lawyer_minutes"])]))
        L.append("")
    L += ["## Measures", ""] + mlines + [""]
    return "\n".join(L)


# ---------------------------------------------------------------- digest parts

def please_check_notes(root):
    d = Path(root) / "inbox" / "please-check"
    out = []
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.note.md")):
        meta, body = common.read_frontmatter_file(p)
        reason = ""
        for line in body.split("\n"):
            s = line.strip()
            if (not s or s.startswith("#") or s.startswith("<!--") or s == common.FENCE
                    or s.startswith("Recorded by the agent") or s == "---"):
                continue
            reason = re.sub(r"^[-*]\s+", "", s)
            break
        if len(reason) > 200:
            reason = reason[:197].rstrip() + "..."
        name = (meta.get("file") or "").strip() or p.name[:-len(".note.md")]
        out.append({"note": common.rel(p, root), "file": name,
                    "subject": (meta.get("subject") or "").strip(),
                    "from": (meta.get("from") or "").strip(),
                    "received": (meta.get("received") or "").strip(),
                    "claimed": (meta.get("claimed_reference") or "").strip(),
                    "candidates": (meta.get("candidates") or "").strip(),
                    "reason": reason or "no reason written in the note"})
    return out


def stale_rows(rows, today):
    out = []
    for r in rows:
        if r["kind"] == "noise" or r["status"] == "closed":
            continue
        la = any_date(r["last_activity"])
        if la and (today - la).days >= STALE_DAYS:
            out.append(((today - la).days, r))
    out.sort(key=lambda x: (-x[0], x[1]["reference"]))
    return out


def waiting_on_you(r):
    return r["status"] == "waiting_lawyer" or (r["waiting_on"] or "").strip().lower() == "you"


def ref_link(r, prefix=""):
    """Markdown link from a row's reference to its brief (matters) or its file (noise)."""
    folder = (r.get("folder") or "").strip()
    if not folder:
        return r["reference"]
    target = folder if r.get("kind") == "noise" else folder + "/brief.md"
    return "[%s](%s%s)" % (r["reference"], prefix, target.replace(" ", "%20"))


def item_line(r, extra=""):
    step = r["next_step"] or "no next step recorded"
    return "%s %s: %s%s" % (ref_link(r, "../"), r["title"] or "(no title)", step, extra)


def render_digest_parts(rows, today, mlines, notes):
    open_m = [r for r in rows if r["kind"] != "noise" and r["status"] != "closed"]
    noise_open = [r for r in rows if r["kind"] == "noise" and r["status"] != "closed"]
    nn = [r for r in open_m if norm_outcome(r["proposed_outcome"]) == "nothing_needed"]
    stale = stale_rows(rows, today)
    L = ["## Nothing needed (confirm)", ""]
    if not noise_open and not nn:
        L.append("None.")
    for r in noise_open:
        L.append("- %s: %s (%s, received %s) - %s" % (r["reference"], r["title"], r["label"] or "no label",
                                                     r.get("_received") or r["opened"], r["folder"]))
    if noise_open:
        L += ["", "To confirm them all, paste this line into chat:", "", confirm_line(noise_open)]
    if nn:
        if noise_open:
            L.append("")
        L.append("Matters where the agent proposes nothing needed (say \"close REF\" if you agree):")
        for r in sorted(nn, key=oldest_first):
            L.append("- " + item_line(r))
    L += ["", "## Please check", ""]
    if not notes:
        L.append("None.")
    for n in notes:
        bits = ["- %s" % (n["subject"] or n["file"])]
        if n["from"]:
            bits.append(" from %s" % n["from"])
        if n["received"]:
            bits.append(" (received %s)" % n["received"])
        bits.append(": %s" % n["reason"])
        if n["claimed"]:
            bits.append(" Claims %s." % n["claimed"])
        if n["candidates"]:
            bits.append(" Candidates: %s." % n["candidates"])
        bits.append(" Note: %s" % n["note"])
        L.append("".join(bits))
    L += ["", "## Quiet for ten days or more", ""]
    if not stale:
        L.append("None.")
    for days, r in stale:
        L.append("- %s %s: quiet for %d days (last activity %s). Next step: %s"
                 % (r["reference"], r["title"], days, r["last_activity"], r["next_step"] or "none recorded"))
    L += ["", "## Measures", ""] + mlines
    L += ["", "## What you should do next", ""]
    items = []
    seen = set()
    dated = [r for r in open_m if any_date(r["due"])]
    for r in sorted(dated, key=lambda r: (any_date(r["due"]), r["reference"])):
        items.append(item_line(r, " (due %s)" % r["due"]))
        seen.add(r["reference"])
    for r in sorted([r for r in open_m if waiting_on_you(r)], key=oldest_first):
        if r["reference"] not in seen:
            items.append(item_line(r))
            seen.add(r["reference"])
    if noise_open:
        items.append("%s: %s proposed as nothing needed: confirm with the line under "
                     "Nothing needed (confirm)" % (", ".join(r["reference"] for r in noise_open),
                                                   plural(len(noise_open), "email")))
    for r in sorted(nn, key=oldest_first):
        if r["reference"] not in seen:
            items.append(item_line(r, " (proposed: nothing needed; close it if you agree)"))
            seen.add(r["reference"])
    for n in notes:
        items.append("%s %s: decide where it goes (%s)" % (n["claimed"] or "please-check",
                                                         n["subject"] or n["file"], n["note"]))
    for days, r in stale:
        if r["reference"] not in seen:
            items.append(item_line(r, " (quiet for %d days)" % days))
            seen.add(r["reference"])
    if not items:
        items.append("Nothing is waiting on you.")
    L += ["%d. %s" % (i, t) for i, t in enumerate(items, 1)]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- step 6: integrity

def integrity(root, matters, noise_rows, rep):
    by_ref = {}
    for d, meta in matters:
        relp = common.rel(d, root)
        missing = [k for k in REQUIRED_KEYS if not (meta.get(k) or "").strip()]
        if missing:
            rep.integrity.append("%s/matter.md: missing %s" % (relp, ", ".join(missing)))
        ref = (meta.get("reference") or "").strip()
        if ref:
            by_ref.setdefault(ref, []).append(relp)
            if not d.name.startswith(ref + "_"):
                rep.integrity.append("%s: folder name does not start with its reference %s" % (relp, ref))
        st = (meta.get("status") or "").strip()
        if st and st not in common.STATUSES:
            rep.warnings.append("%s: status '%s' is not one of %s" % (ref or relp, st, ", ".join(common.STATUSES)))
    for nr in noise_rows:
        nid = (nr.get("id") or "").strip()
        if nid:
            by_ref.setdefault(nid, []).append("inbox/noise/NOISE.csv")
    for ref in sorted(by_ref):
        if len(by_ref[ref]) > 1:
            rep.integrity.append("duplicate reference %s: %s" % (ref, "; ".join(by_ref[ref])))


# ---------------------------------------------------------------- main

def write_outputs(root, rows, md_text, run, rep):
    idx = Path(root) / "INDEX.csv"
    had_index = idx.is_file()
    gen = Path(root) / "changes" / "INDEX.generated.csv"
    if had_index and not gen.is_file():
        keep = Path(root) / "changes" / ("INDEX.before-%s.csv" % run)
        keep.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(idx), str(keep))
        rep.notes.append("kept the old INDEX.csv as %s in case it held edits" % common.rel(keep, root))
    written = common.write_csv(idx, common.INDEX_COLUMNS, rows)
    if Path(written).name == "INDEX.csv":
        gen.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(written), str(gen))
        rep.written += ["INDEX.csv", "changes/INDEX.generated.csv"]
        if (Path(root) / "INDEX.new.csv").exists():
            rep.notes.append("INDEX.new.csv is left over from a run when INDEX.csv was locked; you can delete it")
    else:
        rep.written.append(common.rel(written, root))
        rep.warnings.append("INDEX.csv is locked (open in Excel?): wrote INDEX.new.csv instead. Close "
                            "Excel and run again; edits typed into INDEX.csv are still picked up.")
    common.write_text_atomic(Path(root) / "INDEX.md", md_text)
    rep.written.append("INDEX.md")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/index-rebuild",
                                 description="Apply INDEX.csv edits, rebuild INDEX.csv and INDEX.md.")
    ap.add_argument("--today", metavar="YYYY-MM-DD")
    ap.add_argument("--run", metavar="RUN")
    ap.add_argument("--digest-parts", metavar="FILE")
    ap.add_argument("--no-apply", action="store_true")
    ap.add_argument("--confirm-noise", metavar="IDS")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    root = common.find_root()
    if a.today:
        today = strict_date(a.today)
        if today is None:
            common.die("index-rebuild: --today needs YYYY-MM-DD, got '%s'" % a.today, 2)
    else:
        today = common.now_house(root).date()
    confirm_ids = []
    if a.confirm_noise is not None:
        confirm_ids = NOISE_ID_FIND.findall(a.confirm_noise)
        if not confirm_ids:
            common.die("index-rebuild: --confirm-noise needs ids like NOISE-0001,NOISE-0002", 2)
    run = a.run or common.run_id(root)
    apply = not a.no_apply
    rep = Report()

    # 1. human edits, then confirmations asked for in chat
    edits = detect_edits(root, rep)
    apply_edits(root, edits, run, today, apply, rep)
    if confirm_ids:
        confirm_noise(root, [(i, "", "") for i in confirm_ids], run, apply, rep, how="chat")

    # 2. rows, 3. sort
    matters = collect_matters(root)
    _, _, noise_rows, _ = read_noise(root)
    rows = [matter_row(root, d, meta, today) for d, meta in matters]
    rows += [noise_row(root, nr, today) for nr in noise_rows]
    rows = sort_rows(rows)
    m = measures(rows)
    mlines = measure_lines(m)

    # 6. integrity (before writing, so INDEX.md and the output agree)
    integrity(root, matters, noise_rows, rep)

    # 4. writes
    if apply:
        write_outputs(root, rows, render_index_md(root, rows, today, mlines), run, rep)
    # 5. digest parts
    if a.digest_parts:
        dp = Path(a.digest_parts)
        common.write_text_atomic(dp, render_digest_parts(rows, today, mlines, please_check_notes(root)))
        rep.written.append(common.rel(dp, root))

    open_m = sum(1 for r in rows if r["kind"] != "noise" and r["status"] != "closed")
    closed_m = sum(1 for r in rows if r["kind"] != "noise" and r["status"] == "closed")
    noise_n = sum(1 for r in rows if r["kind"] == "noise")
    noise_open = sum(1 for r in rows if r["kind"] == "noise" and r["status"] != "closed")
    if a.json:
        print(json.dumps({
            "today": today.isoformat(), "run": run, "applied": rep.applied,
            "closed_by_lawyer": rep.closed, "noise_confirmed": rep.noise_confirmed,
            "pending": rep.pending, "warnings": rep.warnings, "notes": rep.notes,
            "integrity": rep.integrity, "written": rep.written,
            "counts": {"matters_open": open_m, "matters_closed": closed_m,
                       "noise": noise_n, "noise_open": noise_open},
            "measures": m}, indent=2))
    else:
        for x in rep.applied:
            if x["ref"] in rep.closed and x["column"] in ("status", "closed", "flags"):
                continue  # reported by the closed-by-lawyer line
            if x["column"] == "title_locked":
                continue
            extra = " (title locked)" if x["column"] == "title" else ""
            print("applied: %s %s = %s%s (%s)" % (x["ref"], x["column"], x["new"] or "(empty)", extra, x["file"]))
        for x in rep.noise_confirmed:
            print("noise confirmed: %s -> %s" % (x["id"], x["file"]))
        for ref in rep.closed:
            print("closed-by-lawyer %s: run the wrap-up" % ref)
        for x in rep.pending:
            print(x)
        for x in rep.notes:
            print("note: " + x)
        for x in rep.warnings:
            print("warning: " + x)
        print("index: %d open and %d closed matters, %d noise rows (%d awaiting confirmation)%s"
              % (open_m, closed_m, noise_n, noise_open,
                 (" -> " + ", ".join(rep.written)) if rep.written else " (nothing written: --no-apply)"))
        for x in rep.integrity:
            print("integrity: " + x)
    return 1 if rep.integrity else 0


if __name__ == "__main__":
    sys.exit(main())
