"""unpack-email: headers, new body text, attachments and filing signals of .eml files.

Read-only, except the files --extract writes. Interface: tools/unpack-email (usage text)
and the build spec, D2. Parsing lives in emailtools.py, shared with place-email.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
import emailtools as et  # noqa: E402


def _yn(v):
    return "yes" if v else "no"


def _addr(a):
    if a.get("name") and a.get("address"):
        return "%s <%s>" % (a["name"], a["address"])
    return a.get("address") or a.get("name") or ""


def _list(values):
    return ", ".join(values) if values else "(none)"


def render_markdown(info):
    out = ["## %s" % info["file"]]
    add = out.append
    add("- canonical_name: %s" % info["canonical_name"])
    add("- direction: %s" % info["direction"])
    add("- internal: %s" % _yn(info["internal"]))
    add("- personal_address: %s" % _yn(info["personal_address"]))
    add("- date: %s" % info["date"])
    add("- from: %s" % (_addr(info["from"]) or "(none)"))
    add("- to: %s" % _list([_addr(a) for a in info["to"]]))
    add("- cc: %s" % _list([_addr(a) for a in info["cc"]]))
    add("- subject: %s" % (info["subject"] or "(none)"))
    add("- message_id: %s" % (info["message_id"] or "(none)"))
    add("- in_reply_to: %s" % (info["in_reply_to"] or "(none)"))
    add("- references: %s" % _list(info["references"]))
    add("- tags: %s" % _list(info["tags"]))
    add("- noise_hints: %s" % _list(info["noise_hints"]))
    add("- notes: %s" % _list(info["notes"]))
    add("- sha256: %s" % info["sha256"])
    atts = info["attachments"]
    add("- attachments: %s" % (len(atts) if atts else "(none)"))
    for a in atts:
        bits = [a["name"], a["kind"], a["content_type"], "%d bytes" % a["size"]]
        if a["inline"]:
            bits.append("inline")
        bits.append("sha256 " + a["sha256"])
        if a.get("extracted"):
            bits.append("extracted to " + a["extracted"])
        add("  - " + " | ".join(bits))
    sig = info.get("signals")
    if sig is not None:
        tm = sig["thread_matches"]
        add("- thread_matches: %s" % ("" if tm else "(none)"))
        for t in tm:
            add("  - %s (%s, status %s) via %s" % (t["folder"], t["reference"], t["status"] or "?",
                                                   ", ".join(t["matched_ids"])))
        gm = sig["tag_matches"]
        add("- tag_matches: %s" % ("" if gm else "(none)"))
        for t in gm:
            if t["found"]:
                add("  - [%s] %s (status %s), sender_check %s" % (t["tag"], t["folder"],
                                                                  t["status"] or "?", t["sender_check"]))
            else:
                add("  - [%s] no matter with this reference, sender_check %s" % (t["tag"], t["sender_check"]))
        af = sig["already_filed"]
        add("- already_filed: %s" % ("" if af else "(none)"))
        for t in af:
            add("  - %s (%s, status %s) has this Message-ID" % (t["folder"], t["reference"], t["status"] or "?"))
    add("- body_chars_total: %d (quoted history stripped: %d characters)"
        % (info["body_chars_total"], info["quoted_chars"]))
    if info.get("quoted_first_date"):
        add("- quoted_first_date: %s" % info["quoted_first_date"])
    if info.get("reply_kind_hint"):
        add("- reply_kind_hint: %s" % info["reply_kind_hint"])
    if info.get("quoted_file"):
        add("- quoted_file: %s (%d characters)" % (info["quoted_file"], info.get("quoted_chars_total", 0)))
    add("")
    add("### Body")
    add(info["body"] if info["body"] else "(empty)")
    if "quoted" in info:
        add("")
        add("### Quoted history")
        add(info["quoted"] if info["quoted"] else "(none)")
    return "\n".join(out).rstrip() + "\n"


def extract(p, ctx, dest_root):
    """Write document, image and email attachments to DIR/<canonical stem>/. Returns paths."""
    folder = Path(dest_root) / os.path.splitext(p.canonical_name)[0]
    written = {}
    for i, a in enumerate(p.attachments):
        if a.kind not in et.STORED_KINDS:
            continue
        folder.mkdir(parents=True, exist_ok=True)
        dest = et.unique_path(folder, a.name)
        with open(str(dest), "xb") as fh:
            fh.write(a.data)
        written[i] = common.rel(dest, ctx.root)
    return written


QUOTED_SHOWN = 3000

# Where a disclaimer or legal footer starts: the rest of that message is dropped from what is shown.
_DISCLAIMER = re.compile(
    r"^(?:this (?:e-?mail|message|communication)\b.{0,100}\b(?:confidential|privileged|intended)"
    r"|confidentiality (?:notice|note)|disclaimer\b|the information (?:contained )?in this (?:e-?mail|message)"
    r"|if you (?:are not the intended|have received this)|please consider the environment"
    r"|registered (?:office|in england)|company (?:registration|number)|diese (?:e-?mail|nachricht) (?:enth|ist))",
    re.I)
_QUOTE_MARKS = re.compile(r"^[ \t]*(?:>[ \t]?)+")


def quoted_messages(history):
    """The quoted history split into messages, newest first as in the email, quote marks removed."""
    lines = [_QUOTE_MARKS.sub("", l) for l in history.split("\n")]
    starts = [i for i in range(len(lines)) if et._history_starts(lines, i)]
    if not starts or starts[0] != 0:
        starts = [0] + starts
    bounds = starts + [len(lines)]
    return [lines[a:b] for a, b in zip(bounds, bounds[1:]) if any(x.strip() for x in lines[a:b])]


def clean_message(lines):
    """One quoted message without its disclaimer or legal footer, and without runs of blank lines."""
    out = []
    for line in lines:
        if _DISCLAIMER.match(line.strip()):
            break
        out.append(line.rstrip())
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return text


def quoted_to_file(p, info, root):
    """One source for the quoted history: every quoted message, without disclaimers, goes to
    changes/quoted/<canonical stem>.txt, and only the oldest message, where the request usually is, is
    shown. Printing whole threads made every later step read them again."""
    messages = [clean_message(m) for m in quoted_messages(p.quoted_body)]
    messages = [m for m in messages if m]
    qdir = Path(root) / "changes" / "quoted"
    qdir.mkdir(parents=True, exist_ok=True)
    qf = qdir / (os.path.splitext(p.canonical_name)[0] + ".txt")
    common.write_text_atomic(qf, "\n\n----\n\n".join(messages) + "\n")
    info["quoted_file"] = common.rel(qf, root)
    info["quoted_chars_total"] = len(p.quoted_body)
    info["quoted_messages"] = len(messages)
    oldest = messages[-1] if messages else ""
    if len(oldest) > QUOTED_SHOWN:
        oldest = oldest[:QUOTED_SHOWN].rstrip() + "\n[... cut at %d characters]" % QUOTED_SHOWN
    info["quoted"] = ("[the oldest of %d quoted messages, where the request usually is; all of them, without "
                      "disclaimers, are in %s]\n%s" % (len(messages), info["quoted_file"], oldest))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/unpack-email",
                                 description="Headers, new body, attachments and signals of .eml files.")
    ap.add_argument("--json", action="store_true", help="JSON array instead of Markdown")
    ap.add_argument("--body-chars", type=int, default=et.BODY_CHARS, metavar="N",
                    help="body limit in characters (default %d)" % et.BODY_CHARS)
    ap.add_argument("--extract", metavar="DIR", help="write attachments to DIR/<canonical stem>/")
    ap.add_argument("--no-signals", action="store_true", help="skip thread and tag matching")
    ap.add_argument("--with-quoted", action="store_true",
                    help="also give the quoted history (for our sent emails that start a matter): its oldest "
                         "message, where the request usually is; every quoted message, without disclaimers, goes "
                         "to changes/quoted/<name>.txt")
    ap.add_argument("--quoted-inline", action="store_true",
                    help="with --with-quoted: print the whole quoted history instead")
    ap.add_argument("--no-quoted", action="store_true",
                    help="skip the quoted history (no first date, no history): fast, for ordering many emails")
    ap.add_argument("files", nargs="*", metavar="FILE")
    ap.add_argument("--run", metavar="RUN", help="the run id; every tool accepts it (not used here)")
    args = ap.parse_args(argv)
    if not args.files:
        ap.print_usage(sys.stderr)
        sys.stderr.write("give at least one .eml file\n")
        return 2
    if args.no_quoted and (args.with_quoted or args.quoted_inline):
        sys.stderr.write("--no-quoted cannot go with --with-quoted or --quoted-inline\n")
        return 2
    if args.body_chars < 0:
        sys.stderr.write("--body-chars must be 0 or more\n")
        return 2

    root = common.find_root()
    ctx = et.Context(root)
    index = None
    results = []
    failed = False
    for name in args.files:
        path = Path(name)
        if et.is_msg_file(path):
            sys.stderr.write("convert first: bash tools/msg2eml %s\n" % name)
            failed = True
            continue
        if not path.is_file():
            sys.stderr.write("no file: %s\n" % name)
            failed = True
            continue
        if not et.is_email_file(path):
            sys.stderr.write("not an .eml file: %s (unpack-email reads .eml only)\n" % name)
            failed = True
            continue
        try:
            p = et.parse_email(path, ctx, body_chars=args.body_chars, with_quoted=args.with_quoted,
                               quoted=not args.no_quoted)
        except OSError as exc:
            sys.stderr.write("cannot read %s: %s\n" % (name, exc))
            failed = True
            continue
        info = p.info
        if args.with_quoted and not args.quoted_inline and p.quoted_body:
            quoted_to_file(p, info, root)
        if args.extract:
            try:
                for i, where in extract(p, ctx, args.extract).items():
                    info["attachments"][i]["extracted"] = where
            except OSError as exc:
                sys.stderr.write("cannot extract attachments of %s: %s\n" % (name, exc))
                failed = True
        if not args.no_signals:
            if index is None:
                index = et.message_id_index(root)
            info["signals"] = et.signals(p, ctx, index)
        results.append(info)

    if args.json:
        sys.stdout.write(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write("\n".join(render_markdown(i) for i in results))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
