"""new-matter: create a matter folder and its memory files from the templates.

Interface: tools/new-matter (usage text) and the build spec, D4. References come from
common.next_reference; templates from skills/operations/matter-memory/templates/.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
import emailtools as et  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_FOLDER = 70
MAX_TITLE = 80
TEMPLATES = Path("skills") / "operations" / "matter-memory" / "templates"
PLACEHOLDERS = ("reference", "area", "sub_area", "subject", "title", "opened", "follows",
                "subject_name", "created")
QUOTED = ("title", "subject_name")   # placeholders that sit inside "..." in frontmatter


class Refusal(Exception):
    pass


def fill(text, values):
    for key in QUOTED:
        text = text.replace('"{{%s}}"' % key, '"%s"' % values[key].replace('"', '\\"'))
    for key in PLACEHOLDERS:
        text = text.replace("{{%s}}" % key, values[key])
    return "\n".join(line.rstrip() for line in text.split("\n"))


def folder_name(ref, subject, topic):
    """<ref>_<subject>_<topic>, at most 70 characters, by shortening the topic."""
    name = "%s_%s_%s" % (ref, subject, topic)
    if len(name) <= MAX_FOLDER:
        return name
    room = MAX_FOLDER - len(ref) - len(subject) - 2
    if room < 1:
        raise Refusal("the subject slug '%s' is too long for a %d-character folder name; use a shorter one"
                      % (subject, MAX_FOLDER))
    cut = topic[:room]
    if topic[room:room + 1] not in ("", "-") and "-" in cut.strip("-"):
        cut = cut[:cut.rstrip("-").rfind("-")]   # drop the partial last word
    cut = cut.strip("-") or topic[:room].strip("-") or topic[:room]
    return "%s_%s_%s" % (ref, subject, cut)


def check_slug(flag, value):
    if not SLUG_RE.match(value or ""):
        raise Refusal("%s must be a slug of a-z, 0-9 and hyphens, for example acme-automotive "
                      "(got '%s'; try '%s')" % (flag, value, common.slugify(value or "", 40)))


def short_title(title):
    title = " ".join((title or "").split())
    if len(title) <= MAX_TITLE:
        return title
    cut = title[:MAX_TITLE]
    if " " in cut[MAX_TITLE // 2:]:
        cut = cut[:cut.rfind(" ")]
    sys.stderr.write("warning: title shortened to %d characters\n" % MAX_TITLE)
    return cut.rstrip(" ,;:-")


def area_check(root, area, sub_area):
    areas = common.parse_areas(root)
    if area != "general" and area not in areas:
        known = ", ".join(sorted(set(areas) | {"general"}))
        raise Refusal("area '%s' is not in house/areas.md. Areas: %s. Use general for mail that fits no area."
                      % (area, known))
    if sub_area:
        declared = areas.get(area, {}).get("sub_areas_list", [])
        if sub_area not in declared:
            raise Refusal("sub-area '%s' is not declared for %s. File under areas/%s/<subject>/ and propose "
                          "the sub-area in the digest." % (sub_area, area, area))


def create(root, args, run):
    area = args.area
    sub = args.sub_area or ""
    check_slug("--area", area)
    if sub:
        check_slug("--sub-area", sub)
    check_slug("--subject", args.subject)
    check_slug("--topic", args.topic)
    area_check(root, area, sub)
    if args.opened:
        if not DATE_RE.match(args.opened) or common.parse_date(args.opened) is None:
            raise Refusal("--opened must be a date YYYY-MM-DD (got '%s')" % args.opened)
        opened = common.parse_date(args.opened)
    else:
        opened = common.now_house(root).date()
    follows = (args.follows or "").strip().strip("[]")
    if follows:
        if not common.REF_RE.match(follows):
            raise Refusal("--follows must be a reference such as 2026-0042 (got '%s')" % args.follows)
        if common.find_matter(root, follows) is None:
            sys.stderr.write("warning: no matter folder found for --follows %s; recorded anyway\n" % follows)
    tdir = root / TEMPLATES
    names = list(common.MATTER_FILES) + ["subject.md"]
    missing = [n for n in names if not (tdir / n).is_file()]
    if missing:
        raise Refusal("templates missing in %s: %s" % (TEMPLATES.as_posix(), ", ".join(missing)))

    subject_name = " ".join((args.subject_name or "").split()) or \
        " ".join(w.capitalize() for w in args.subject.split("-") if w)
    title = short_title(args.title or "%s: %s" % (subject_name, args.topic.replace("-", " ")))
    ref = common.next_reference(root, year=opened.year)
    base = root / "areas" / area
    if sub:
        base = base / sub
    subject_dir = base / args.subject
    matter = subject_dir / folder_name(ref, args.subject, args.topic)
    if matter.exists():
        raise Refusal("matter folder already exists: %s" % common.rel(matter, root))
    values = {"reference": ref, "area": area, "sub_area": sub, "subject": args.subject,
              "title": title, "opened": opened.isoformat(), "follows": follows,
              "subject_name": subject_name, "created": opened.isoformat()}
    new_subject = not subject_dir.is_dir()
    subject_dir.mkdir(parents=True, exist_ok=True)
    if not (subject_dir / "subject.md").exists():
        common.write_text_atomic(subject_dir / "subject.md", fill(common.read_text(tdir / "subject.md"), values))
    matter.mkdir()
    for d in common.MATTER_DIRS:
        (common.agent_dir(matter) / d).mkdir(parents=True, exist_ok=True)
    common.human_dir(matter).mkdir(parents=True, exist_ok=True)
    for n in common.MATTER_FILES:
        common.write_text_atomic(common.mpath(matter, n), fill(common.read_text(tdir / n), values))
    stamp = common.stamp(root)
    common.append_line(common.agent_dir(matter) / "log.md", common.join_pipe([stamp, "opened matter", "matter.md", run]))
    reason = "new subject" if new_subject else "existing subject"
    if follows:
        reason += "; follows " + follows
    et.append_journal(root, stamp, run, "new-matter", ref, common.rel(matter, root), reason, "")
    return ref, matter


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/new-matter",
                                 description="Create a matter folder with its memory files.")
    ap.add_argument("--area")
    ap.add_argument("--sub-area")
    ap.add_argument("--subject")
    ap.add_argument("--topic")
    ap.add_argument("--subject-name")
    ap.add_argument("--title")
    ap.add_argument("--follows", metavar="REF")
    ap.add_argument("--opened", metavar="YYYY-MM-DD")
    ap.add_argument("--run")
    ap.add_argument("--next-ref", action="store_true", help="print the next reference only")
    ap.add_argument("--year", metavar="YYYY", help="with --next-ref: the year (default this year)")
    args = ap.parse_args(argv)
    root = common.find_root()
    try:
        if args.next_ref:
            if args.year is not None and not re.match(r"^20\d{2}$", args.year):
                raise Refusal("--year must be a year such as 2026 (got '%s')" % args.year)
            year = int(args.year) if args.year else common.now_house(root).year
            sys.stdout.write(common.next_reference(root, year=year) + "\n")
            return 0
        if args.year is not None:
            raise Refusal("--year goes with --next-ref; for a new matter use --opened YYYY-MM-DD")
        if not (args.area and args.subject and args.topic):
            ap.print_usage(sys.stderr)
            raise Refusal("give --area, --subject and --topic (or --next-ref)")
        run = args.run or common.run_id(root)
        ref, matter = create(root, args, run)
    except Refusal as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    except OSError as exc:
        sys.stderr.write("could not create the matter: %s\n" % exc)
        return 1
    sys.stdout.write("%s\t%s\n" % (ref, common.rel(matter, root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
