"""unpack-email: headers, new body text, attachments and filing signals of .eml files.

Read-only, except the files --extract writes. Interface: tools/unpack-email (usage text)
and the build spec, D2. Parsing lives in emailtools.py, shared with place-email.
"""

import argparse
import json
import os
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


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/unpack-email",
                                 description="Headers, new body, attachments and signals of .eml files.")
    ap.add_argument("--json", action="store_true", help="JSON array instead of Markdown")
    ap.add_argument("--body-chars", type=int, default=et.BODY_CHARS, metavar="N",
                    help="body limit in characters (default %d)" % et.BODY_CHARS)
    ap.add_argument("--extract", metavar="DIR", help="write attachments to DIR/<canonical stem>/")
    ap.add_argument("--no-signals", action="store_true", help="skip thread and tag matching")
    ap.add_argument("--with-quoted", action="store_true",
                    help="also give the quoted history (for our sent emails that start a matter)")
    ap.add_argument("files", nargs="*", metavar="FILE")
    args = ap.parse_args(argv)
    if not args.files:
        ap.print_usage(sys.stderr)
        sys.stderr.write("give at least one .eml file\n")
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
            p = et.parse_email(path, ctx, body_chars=args.body_chars, with_quoted=args.with_quoted)
        except OSError as exc:
            sys.stderr.write("cannot read %s: %s\n" % (name, exc))
            failed = True
            continue
        info = p.info
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
