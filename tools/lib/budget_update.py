"""budget-update: keep BUDGET.md (cap, monthly estimate, mode, ledger).

Run through the wrapper (spec D10):
  bash tools/budget-update --init [--month YYYY-MM]
  bash tools/budget-update --run RUN --model opus|sonnet|haiku --in-chars N --out-chars M [--note T]
  bash tools/budget-update --actual USD [--date YYYY-MM-DD] [--month YYYY-MM]
  bash tools/budget-update --show
  bash tools/budget-update --mode
  --today YYYY-MM-DD stands in for today (tests, catching up).
Estimate per ledger line: (in_chars/4 * price_in + out_chars/4 * price_out) / 1e6 * overhead_factor.
On any write, a BUDGET.md month that is not the current month moves its ledger to
digests/budget-<month>.md and the estimate starts again at 0.
Exit 0 ok, 1 check failed, 2 usage error.
"""

import argparse
import datetime as _dt
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

DEFAULT_CAP = "100"
DEFAULT_OVERHEAD = 1.25
DEFAULT_THRESHOLDS = "lean=70 minimal=90 paused=100"
DEFAULT_PRICES = "opus=4/20 sonnet=2/10 haiku=0.10/0.50"
PRICES_AS_OF = "2026-10-06"
LEDGER_COLUMNS = ["run", "date", "model", "in_chars", "out_chars", "est_usd", "note"]
LEDGER_HEADER = " | ".join(LEDGER_COLUMNS)
KEYS = ["cap_usd", "month", "estimated_spend_usd", "percent_of_cap", "mode", "overhead_factor",
        "last_actual_usd", "last_actual_date", "thresholds", "prices_usd_per_mtok"]
MODES = ("full", "lean", "minimal", "paused")
KEY_RE = re.compile(r"^([a-z_]+):[ \t]*(.*?)\s*$")
MONTH_RE = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")

HEADER = ["# Budget",
          'Kept by the agent. Once a month, type the actual bill: say "budget actual 37.20".',
          "Prices are list prices in USD per million tokens (input/output) as of %s. "
          "Check them and edit the prices line if they change." % PRICES_AS_OF,
          ""]


class UsageError(Exception):
    pass


class CheckFailed(Exception):
    pass


# ---------------------------------------------------------------- parsing

def parse_pairs(text):
    out = {}
    for part in (text or "").split():
        if "=" in part:
            k, _, v = part.partition("=")
            out[k.strip().lower()] = v.strip()
    return out


def parse_prices(text, warn):
    prices = {}
    for k, v in parse_pairs(text).items():
        try:
            pin, _, pout = v.partition("/")
            prices[k] = (float(pin), float(pout))
        except ValueError:
            warn("could not read the price for %s ('%s'); left out" % (k, v))
    if not prices:
        warn("could not read prices_usd_per_mtok; using the defaults %s" % DEFAULT_PRICES)
        return parse_prices(DEFAULT_PRICES, warn)
    return prices


def parse_thresholds(text, warn):
    t = {"lean": 70.0, "minimal": 90.0, "paused": 100.0}
    for k, v in parse_pairs(text).items():
        if k in t:
            try:
                t[k] = float(v)
            except ValueError:
                warn("could not read threshold %s='%s'; using %g" % (k, v, t[k]))
    return t


def to_float(s, default=None):
    s = (s or "").strip().replace(",", ".")
    s = re.sub(r"^(usd|\$)\s*", "", s, flags=re.I)
    try:
        return float(s)
    except ValueError:
        return default


def money(x):
    return "%.2f" % x if (x == 0 or abs(x) >= 0.01) else "%.4f" % x


def num_text(x):
    return ("%g" % x) if x == int(x) else ("%.2f" % x)


class Budget:
    """BUDGET.md (or a digests/budget-<month>.md archive) as lines plus parsed values."""

    def __init__(self, text):
        lines = text.replace("\r\n", "\n").split("\n")
        self.head = []
        self.ledger_other = []
        self.ledger = []
        in_ledger = False
        for line in lines:
            if re.match(r"^##\s+Ledger\s*$", line.strip()):
                in_ledger = True
                continue
            if not in_ledger:
                self.head.append(line)
                continue
            s = line.strip()
            if not s:
                continue
            # The note is the last field and may hold anything, so split at most 6 times.
            fields = [f.strip() for f in re.split(r"\s*\|\s*", s, maxsplit=6)]
            if fields and fields[0] == "run" and len(fields) >= 6:
                continue  # header row
            if s.startswith("#") or len(fields) < 6:
                self.ledger_other.append(s)
                continue
            while len(fields) < 7:
                fields.append("")
            self.ledger.append(fields)
        while self.head and not self.head[-1].strip():
            self.head.pop()
        self.keys = {}
        for line in self.head:
            m = KEY_RE.match(line)
            if m:
                self.keys.setdefault(m.group(1), m.group(2))

    def get(self, k, default=""):
        return self.keys.get(k, default)

    def set(self, k, v):
        self.keys[k] = v
        for i, line in enumerate(self.head):
            m = KEY_RE.match(line)
            if m and m.group(1) == k:
                self.head[i] = ("%s: %s" % (k, v)).rstrip()
                return
        last = max([i for i, line in enumerate(self.head) if KEY_RE.match(line)] or [len(self.head) - 1])
        self.head.insert(last + 1, ("%s: %s" % (k, v)).rstrip())

    def estimate(self):
        return sum(to_float(f[5], 0.0) for f in self.ledger)

    def render(self):
        out = list(self.head) + ["", "## Ledger", LEDGER_HEADER]
        out += self.ledger_other
        out += [ledger_line(f) for f in self.ledger]
        return "\n".join(out) + "\n"


def ledger_line(fields):
    f = list(fields[:7]) + [""] * (7 - len(fields[:7]))
    f[6] = f[6] or "-"
    return common.join_pipe(f).rstrip()


def new_budget_text(month):
    lines = list(HEADER) + [
        "cap_usd: %s" % DEFAULT_CAP, "month: %s" % month, "estimated_spend_usd: 0.00",
        "percent_of_cap: 0", "mode: full", "overhead_factor: %s" % DEFAULT_OVERHEAD,
        "last_actual_usd:", "last_actual_date:", "thresholds: %s" % DEFAULT_THRESHOLDS,
        "prices_usd_per_mtok: %s" % DEFAULT_PRICES, "", "## Ledger", LEDGER_HEADER]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- computing

class Ctx:
    def __init__(self, root, today):
        self.root = Path(root)
        self.today = today
        self.month = today.strftime("%Y-%m")
        self.path = self.root / "BUDGET.md"
        self.warnings = []

    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)


def settings(ctx, b):
    cap = to_float(b.get("cap_usd"), None)
    if cap is None or cap <= 0:
        ctx.warn("cap_usd '%s' is not a positive number; using %s" % (b.get("cap_usd"), DEFAULT_CAP))
        cap = float(DEFAULT_CAP)
    factor = to_float(b.get("overhead_factor"), None)
    if factor is None or factor <= 0:
        ctx.warn("overhead_factor '%s' is not a positive number; using %s" % (b.get("overhead_factor"), DEFAULT_OVERHEAD))
        factor = DEFAULT_OVERHEAD
    return {"cap": cap, "factor": factor,
            "thresholds": parse_thresholds(b.get("thresholds", DEFAULT_THRESHOLDS), ctx.warn),
            "prices": parse_prices(b.get("prices_usd_per_mtok", DEFAULT_PRICES), ctx.warn)}


def percent(est, cap):
    return round(est * 100.0 / cap, 6)


def mode_for(pct, thr):
    if pct >= thr["paused"]:
        return "paused"
    if pct >= thr["minimal"]:
        return "minimal"
    if pct >= thr["lean"]:
        return "lean"
    return "full"


def refresh(ctx, b):
    """Recompute estimate, percent and mode from the ledger. Returns (est, pct, mode)."""
    s = settings(ctx, b)
    est = b.estimate()
    pct = percent(est, s["cap"])
    mode = mode_for(pct, s["thresholds"])
    b.set("estimated_spend_usd", money(est))
    b.set("percent_of_cap", str(int(math.floor(pct))))
    b.set("mode", mode)
    return est, pct, mode


def effective(ctx, b):
    """(month, est, pct, mode) as of today, without writing: a past month counts as reset."""
    s = settings(ctx, b)
    if b.get("month") != ctx.month:
        return ctx.month, 0.0, 0.0, mode_for(0.0, s["thresholds"])
    est = b.estimate()
    pct = percent(est, s["cap"])
    return ctx.month, est, pct, mode_for(pct, s["thresholds"])


def archive_path(ctx, month):
    return ctx.root / "digests" / ("budget-%s.md" % month)


def archive_month(ctx, b, actual=None):
    """Move BUDGET.md's ledger to digests/budget-<month>.md. actual = (usd, date) to record."""
    old = b.get("month") or "unknown"
    path = archive_path(ctx, old)
    s = settings(ctx, b)
    if path.exists():
        a = Budget(common.read_text(path))
        a.ledger += b.ledger
    else:
        a = Budget("\n".join([
            "# Budget for %s (closed)" % old,
            "Moved here from BUDGET.md on %s when the month changed. Estimates only; the actual bill "
            "is recorded below once you type it." % ctx.today.isoformat(), "",
            "cap_usd: %s" % num_text(s["cap"]), "month: %s" % old, "estimated_spend_usd: 0.00",
            "percent_of_cap: 0", "mode: full", "overhead_factor: %s" % b.get("overhead_factor", DEFAULT_OVERHEAD),
            "actual_usd:", "actual_date:", "", "## Ledger", LEDGER_HEADER, ""]))
        a.ledger = list(b.ledger)
    est = a.estimate()
    pct = percent(est, s["cap"])
    a.set("estimated_spend_usd", money(est))
    a.set("percent_of_cap", str(int(math.floor(pct))))
    a.set("mode", mode_for(pct, s["thresholds"]))
    if actual is not None:
        a.set("actual_usd", money(actual[0]))
        a.set("actual_date", actual[1])
    common.write_text_atomic(path, a.render())
    return path


def check_not_backwards(ctx, b):
    """A write never moves BUDGET.md back to an earlier month (for example a --today in the past)."""
    cur = b.get("month")
    if MONTH_RE.match(cur or "") and ctx.month < cur:
        raise CheckFailed("today (%s) is before the month in BUDGET.md (%s); nothing written" % (ctx.month, cur))


def roll_if_needed(ctx, b, out, actual=None):
    """On a write: a stale month moves to digests/ and the estimate resets."""
    cur = b.get("month")
    if cur == ctx.month:
        return
    if not MONTH_RE.match(cur or ""):
        # Unreadable month: take it from the ledger dates; lines of this month stay.
        months = sorted(set(f[1][:7] for f in b.ledger if MONTH_RE.match(f[1][:7])))
        guess = months[0] if months else ""
        ctx.warn("BUDGET.md month '%s' is not YYYY-MM; read as %s" % (cur, guess or ctx.month))
        if not guess or guess == ctx.month:
            b.set("month", ctx.month)
            return
        b.set("month", guess)
        cur = guess
    if b.ledger or actual is not None:
        path = archive_month(ctx, b, actual)
        out.append("month changed: the %s ledger moved to %s; the estimate starts again at 0"
                   % (cur, common.rel(path, ctx.root)))
    b.ledger = []
    b.ledger_other = []
    b.set("month", ctx.month)


def load(ctx):
    """BUDGET.md, or None when it does not exist."""
    if not ctx.path.exists():
        return None
    return Budget(common.read_text(ctx.path))


def save(ctx, b):
    common.write_text_atomic(ctx.path, b.render())


# ---------------------------------------------------------------- actions

def do_init(ctx, month):
    if ctx.path.exists():
        b = Budget(common.read_text(ctx.path))
        return ["BUDGET.md exists (month %s); nothing changed" % (b.get("month") or "?")]
    common.write_text_atomic(ctx.path, new_budget_text(month or ctx.month))
    return ["created BUDGET.md for %s (cap USD %s, overhead factor %s)" % (month or ctx.month, DEFAULT_CAP, DEFAULT_OVERHEAD)]


def do_run(ctx, run, model, in_chars, out_chars, note):
    out = []
    existed = ctx.path.exists()
    b = Budget(common.read_text(ctx.path) if existed else new_budget_text(ctx.month))
    s = settings(ctx, b)
    model = model.lower()
    if model not in s["prices"]:
        raise UsageError("unknown model '%s': BUDGET.md has prices for %s" % (model, ", ".join(sorted(s["prices"]))))
    check_not_backwards(ctx, b)
    if not existed:
        out.append("created BUDGET.md for %s" % ctx.month)
    roll_if_needed(ctx, b, out)
    s = settings(ctx, b)
    before = mode_for(percent(b.estimate(), s["cap"]), s["thresholds"])
    pin, pout = s["prices"][model]
    est = (in_chars / 4.0 * pin + out_chars / 4.0 * pout) / 1e6 * s["factor"]
    b.ledger.append([run, ctx.today.isoformat(), model, str(in_chars), str(out_chars), "%.4f" % est, note or "-"])
    total, pct, mode = refresh(ctx, b)
    save(ctx, b)
    out.append("ledger: %s %s in %d out %d chars = USD %.4f; %s: USD %s of %s (%d%%), mode %s"
               % (run, model, in_chars, out_chars, est, ctx.month, money(total), num_text(s["cap"]),
                  int(math.floor(pct)), mode))
    if mode != before:
        out.append("mode changed: %s -> %s (RULES.md, Budget)" % (before, mode))
    return out


def previous_month(month):
    y, m = int(month[:4]), int(month[5:7])
    return "%04d-%02d" % ((y - 1, 12) if m == 1 else (y, m - 1))


def do_actual(ctx, usd, date, month_arg):
    out = []
    b = load(ctx)
    if b is None:
        raise UsageError("BUDGET.md not found: run bash tools/budget-update --init first")
    check_not_backwards(ctx, b)
    s = settings(ctx, b)
    stale = b.get("month") != ctx.month
    if month_arg:
        billed = month_arg
    elif stale:
        billed = b.get("month")
    else:
        prev = previous_month(ctx.month)
        ap = archive_path(ctx, prev)
        billed = prev if (ap.exists() and not Budget(common.read_text(ap)).get("actual_usd")) else ctx.month
    if billed == b.get("month"):
        estimated = b.estimate()
        archived = None
    else:
        archived = archive_path(ctx, billed)
        if not archived.exists():
            raise CheckFailed("no estimate for %s: %s not found" % (billed, common.rel(archived, ctx.root)))
        estimated = Budget(common.read_text(archived)).estimate()
    old = s["factor"]
    if estimated <= 0:
        new = old
        out.append("no estimate for %s to compare with; overhead factor stays %.2f" % (billed, old))
    else:
        raw = old * usd / estimated
        new = min(5.0, max(1.0, raw))
        out.append("actual USD %s for %s against estimated USD %s: overhead factor %.2f -> %.2f%s"
                   % (money(usd), billed, money(estimated), old, new,
                      "" if new == raw else " (limited to the range 1.0 to 5.0; check the prices line)"))
    if stale and billed == b.get("month"):
        roll_if_needed(ctx, b, out, actual=(usd, date))  # the archive keeps the factor that month used
    else:
        if archived is not None:
            a = Budget(common.read_text(archived))
            a.set("actual_usd", money(usd))
            a.set("actual_date", date)
            common.write_text_atomic(archived, a.render())
            out.append("recorded the bill in %s" % common.rel(archived, ctx.root))
        roll_if_needed(ctx, b, out)
    b.set("overhead_factor", "%.2f" % new)
    b.set("last_actual_usd", money(usd))
    b.set("last_actual_date", date)
    refresh(ctx, b)
    save(ctx, b)
    return out


def do_show(ctx):
    b = load(ctx)
    if b is None:
        raise CheckFailed("BUDGET.md not found: run bash tools/budget-update --init")
    s = settings(ctx, b)
    month, est, pct, mode = effective(ctx, b)
    out = []
    if b.get("month") != ctx.month:
        out.append("BUDGET.md still shows %s; the month has changed, so the estimate starts again at 0 "
                   "on the next write." % (b.get("month") or "no month"))
    out.append("Budget %s: USD %s estimated of a USD %s cap (%d%%). Mode: %s."
               % (month, money(est), num_text(s["cap"]), int(math.floor(pct)), mode))
    last = b.get("last_actual_usd")
    out.append("Overhead factor %.2f. Last actual bill: %s." % (
        s["factor"], ("USD %s on %s" % (last, b.get("last_actual_date") or "?")) if last else "none yet"))
    t = s["thresholds"]
    out.append("Modes: lean from %g%%, minimal from %g%%, paused at %g%%." % (t["lean"], t["minimal"], t["paused"]))
    out.append("Prices, USD per million tokens in/out: %s (as of %s unless edited)."
               % (b.get("prices_usd_per_mtok") or DEFAULT_PRICES, PRICES_AS_OF))
    rows = b.ledger if b.get("month") == ctx.month else []
    out.append("Ledger, %d line%s this month:" % (len(rows), "" if len(rows) == 1 else "s"))
    out.append(LEDGER_HEADER)
    out += [ledger_line(f) for f in rows]
    return out


def do_mode(ctx):
    b = load(ctx)
    if b is None:
        ctx.warn("BUDGET.md not found; mode full until bash tools/budget-update --init")
        return ["full"]
    return [effective(ctx, b)[3]]


# ---------------------------------------------------------------- main

def parse_day(s, what):
    s = (s or "").strip()
    if not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", s):
        raise UsageError("%s needs YYYY-MM-DD, got '%s'" % (what, s))
    try:
        return _dt.date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        raise UsageError("%s needs a real date, got '%s'" % (what, s))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/budget-update", description="Keep BUDGET.md.")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--month", metavar="YYYY-MM")
    ap.add_argument("--run", metavar="RUN")
    ap.add_argument("--model")
    ap.add_argument("--in-chars", type=int, metavar="N")
    ap.add_argument("--out-chars", type=int, metavar="M")
    ap.add_argument("--note", default="")
    ap.add_argument("--actual", metavar="USD")
    ap.add_argument("--date", metavar="YYYY-MM-DD")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--mode", action="store_true")
    ap.add_argument("--today", metavar="YYYY-MM-DD")
    a = ap.parse_args(argv)
    root = common.find_root()
    try:
        actions = [n for n, on in (("--init", a.init), ("--run", a.run is not None),
                                   ("--actual", a.actual is not None), ("--show", a.show),
                                   ("--mode", a.mode)) if on]
        if len(actions) != 1:
            raise UsageError("give exactly one of --init, --run, --actual, --show, --mode")
        today = parse_day(a.today, "--today") if a.today else common.now_house(root).date()
        ctx = Ctx(root, today)
        if a.month is not None and not MONTH_RE.match(a.month):
            raise UsageError("--month needs YYYY-MM, got '%s'" % a.month)
        if a.month is not None and actions[0] not in ("--init", "--actual"):
            raise UsageError("--month goes with --init or --actual")
        run_only = [n for n, v in (("--model", a.model), ("--in-chars", a.in_chars),
                                   ("--out-chars", a.out_chars), ("--note", a.note or None)) if v is not None]
        if run_only and actions[0] != "--run":
            raise UsageError("%s goes with --run" % ", ".join(run_only))
        if a.date is not None and actions[0] != "--actual":
            raise UsageError("--date goes with --actual")
        if actions[0] == "--init":
            out = do_init(ctx, a.month)
        elif actions[0] == "--run":
            if not a.run.strip() or a.model is None or a.in_chars is None or a.out_chars is None:
                raise UsageError("--run needs RUN, --model, --in-chars and --out-chars")
            if a.in_chars < 0 or a.out_chars < 0:
                raise UsageError("--in-chars and --out-chars cannot be negative")
            out = do_run(ctx, a.run.strip(), a.model, a.in_chars, a.out_chars, a.note)
        elif actions[0] == "--actual":
            usd = to_float(a.actual, None)
            if usd is None or usd < 0:
                raise UsageError("--actual needs an amount in USD, like 37.20; got '%s'" % a.actual)
            date = parse_day(a.date, "--date").isoformat() if a.date else today.isoformat()
            out = do_actual(ctx, usd, date, a.month)
        elif actions[0] == "--show":
            out = do_show(ctx)
        else:
            out = do_mode(ctx)
    except UsageError as e:
        common.die("budget-update: %s" % e, 2)
    except CheckFailed as e:
        common.die("budget-update: %s" % e, 1)
    for w in ctx.warnings:
        sys.stderr.write("warning: %s\n" % w)
    for line in out:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
