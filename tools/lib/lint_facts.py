"""lint-facts: check a facts.md file; print the live or as-of view.

Run through the wrapper: bash tools/lint-facts FILE [--previous OLDFILE] [--live] [--as-of YYYY-MM-DD]
Checks (spec D8): 7 fields per record; id pattern, unique, ascending; type; recorded and
valid_from dates; source= non-empty; supersedes targets exist and come earlier; with
--previous, OLDFILE's records are an unchanged prefix of FILE's records (append-only).
Exit 0 clean, 1 errors (one line each), 2 usage error.
Lint mode prints errors on stdout. View mode prints the view on stdout and errors on stderr.
"""

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

ID_RE = re.compile(r"^F([0-9]{4,})$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
FIELDS_HINT = "id | recorded | type | valid_from=DATE | source=PATH | supersedes=ID | text"


class Record:
    __slots__ = ("line", "raw", "fields", "key", "id", "num", "recorded", "valid_from",
                 "targets", "ok_fields")

    def __init__(self, line, raw):
        self.line = line
        self.raw = raw.rstrip()
        self.fields = common.split_pipe(raw)
        self.key = " | ".join(self.fields)
        self.ok_fields = len(self.fields) == 7
        first = self.fields[0] if self.fields else ""
        m = ID_RE.match(first)
        self.id = first if m else None
        self.num = int(m.group(1)) if m else None
        self.recorded = None
        self.valid_from = None
        self.targets = []


def parse_date(s):
    s = (s or "").strip()
    if not DATE_RE.match(s):
        return None
    try:
        return _dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None


def parse_records(text):
    recs = []
    for n, line in enumerate(text.split("\n"), 1):
        if common.is_record_line(line):
            recs.append(Record(n, line))
    return recs


def keyed_value(field, key):
    """('value', True) for 'key=value'; (None, False) when the key prefix is missing."""
    prefix = key + "="
    if field.startswith(prefix):
        return field[len(prefix):].strip(), True
    return None, False


def check(recs):
    """Validate records in place. Returns a list of (line, id, message)."""
    errors = []
    seen = {}       # id -> line of first occurrence
    position = {}   # id -> index of first occurrence
    last_num = None
    last_id = None
    for idx, r in enumerate(recs):
        f = r.fields
        label = r.id or (f[0] if f else "")
        if not r.ok_fields:
            errors.append((r.line, label, "%d fields, expected 7: %s" % (len(f), FIELDS_HINT)))
        # id: pattern, unique, ascending
        if r.id is None:
            errors.append((r.line, label, "bad id '%s': expected F and 4 or more digits" % (f[0] if f else "")))
        elif r.id in seen:
            errors.append((r.line, r.id, "duplicate id (first on line %d)" % seen[r.id]))
        else:
            if last_num is not None and r.num <= last_num:
                errors.append((r.line, r.id, "id is not above the previous id %s: ids ascend" % last_id))
            seen[r.id] = r.line
            position[r.id] = idx
            last_num, last_id = r.num, r.id
        if not r.ok_fields:
            continue
        # recorded
        r.recorded = parse_date(f[1])
        if r.recorded is None:
            errors.append((r.line, label, "recorded '%s' is not a date (YYYY-MM-DD)" % f[1]))
        # type
        if f[2] not in common.FACT_TYPES:
            errors.append((r.line, label, "type '%s' is not one of %s" % (f[2], ", ".join(common.FACT_TYPES))))
        # valid_from
        v, has = keyed_value(f[3], "valid_from")
        if not has:
            errors.append((r.line, label, "field 4 must be valid_from=YYYY-MM-DD or valid_from= (got '%s')" % f[3]))
        elif v:
            r.valid_from = parse_date(v)
            if r.valid_from is None:
                errors.append((r.line, label, "valid_from '%s' is not a date (YYYY-MM-DD)" % v))
        # source
        v, has = keyed_value(f[4], "source")
        if not has:
            errors.append((r.line, label, "field 5 must be source=<file in the matter> (got '%s')" % f[4]))
        elif not v:
            errors.append((r.line, label, "source= is empty: every fact needs a source"))
        # supersedes
        v, has = keyed_value(f[5], "supersedes")
        if not has:
            errors.append((r.line, label, "field 6 must be supersedes=<id> or supersedes= (got '%s')" % f[5]))
        elif v:
            for t in [x for x in re.split(r"[,;\s]+", v) if x]:
                if not ID_RE.match(t):
                    errors.append((r.line, label, "supersedes '%s' is not a fact id" % t))
                elif t == r.id:
                    errors.append((r.line, label, "supersedes itself"))
                elif t in position and position[t] < idx:
                    r.targets.append(t)
                elif any(x.id == t for x in recs[idx + 1:]):
                    errors.append((r.line, label, "supersedes %s, which comes later: a fact can only supersede an earlier one" % t))
                else:
                    errors.append((r.line, label, "supersedes %s, which does not exist" % t))
        # text
        if not f[6]:
            errors.append((r.line, label, "text is empty"))
    return errors


def check_prefix(old, new):
    """Append-only: old records must appear unchanged and in order as a prefix of new."""
    errors = []
    new_by_id = {}
    for j, r in enumerate(new):
        if r.id and r.id not in new_by_id:
            new_by_id[r.id] = j
    new_keys = set(r.key for r in new)
    for o in old:
        if o.id is None:
            if o.key not in new_keys:
                errors.append((None, "", "previous line %d was removed or changed: %s" % (o.line, o.key[:60])))
            continue
        j = new_by_id.get(o.id)
        if j is None:
            errors.append((None, o.id, "removed: facts.md is append-only, never remove a line"))
        elif new[j].key != o.key:
            errors.append((new[j].line, o.id, "changed: facts.md is append-only; add a new line with supersedes=%s instead" % o.id))
    if errors:
        return errors
    for k, o in enumerate(old):
        if k >= len(new) or new[k].key != o.key:
            r = new[k] if k < len(new) else None
            what = (r.id or "line %d" % r.line) if r else "a line"
            errors.append((r.line if r else None, what,
                           "inserted before %s: add new lines at the end" % (o.id or "line %d" % o.line)))
            break
    return errors


def superseded_ids(recs, in_force=None):
    """Ids superseded by a later record. in_force(r) limits which superseding records count."""
    out = set()
    for r in recs:
        if in_force is not None and not in_force(r):
            continue
        out.update(r.targets)
    return out


def live_view(recs):
    sup = superseded_ids(recs)
    return [r for r in recs if r.id not in sup]


def as_of_view(recs, day):
    """Records held on DAY (recorded on or before it) and in force on DAY (valid_from, or
    recorded when empty, on or before it), not superseded by such a record."""
    def in_force(r):
        if r.recorded is None or r.recorded > day:
            return False
        eff = r.valid_from or r.recorded
        return eff <= day
    sup = superseded_ids(recs, in_force)
    return [r for r in recs if in_force(r) and r.id not in sup]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/lint-facts",
                                 description="Check a facts.md file; print the live or as-of view.")
    ap.add_argument("file", metavar="FILE")
    ap.add_argument("--previous", metavar="OLDFILE",
                    help="previous version: its records must be an unchanged prefix (append-only)")
    view = ap.add_mutually_exclusive_group()
    view.add_argument("--live", action="store_true", help="print only live records")
    view.add_argument("--as-of", metavar="YYYY-MM-DD", help="print the records live on that date")
    ap.add_argument("--run", metavar="RUN", help="the run id; every tool accepts it (not used here)")
    a = ap.parse_args(argv)

    path = Path(a.file)
    if not path.is_file():
        common.die("lint-facts: no such file: %s" % a.file, 2)
    day = None
    if a.as_of is not None:
        day = parse_date(a.as_of)
        if day is None:
            common.die("lint-facts: --as-of needs a date as YYYY-MM-DD, got '%s'" % a.as_of, 2)

    recs = parse_records(common.read_text(path))
    errors = check(recs)
    if a.previous:
        old_path = Path(a.previous)
        if old_path.is_file():
            errors.extend(check_prefix(parse_records(common.read_text(old_path)), recs))
        else:
            sys.stderr.write("lint-facts: no previous version at %s; append-only check skipped\n" % a.previous)

    viewing = a.live or day is not None
    out_err = sys.stderr if viewing else sys.stdout
    for line, ident, msg in errors:
        loc = "%s:%d" % (a.file, line) if line else a.file
        out_err.write("%s: %s%s\n" % (loc, (ident + ": ") if ident else "", msg))

    if viewing:
        rows = live_view(recs) if a.live else as_of_view(recs, day)
        for r in rows:
            sys.stdout.write(r.raw.strip() + "\n")
    elif not errors:
        sys.stdout.write("ok: %s: %d records, %d live\n" % (a.file, len(recs), len(live_view(recs))))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
