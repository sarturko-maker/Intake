"""demo/scripts/setup: make a fresh demo workspace from this repository. Python 3.8+.

Copies the repository's files (not .git, not demo/build/**/node_modules, not Python caches or
files a live workspace generates) to the target, then installs the demo house settings,
knowledge and seeds: demo/house/* -> house/, demo/knowledge/** -> knowledge/,
demo/seeds/** -> seeds/. Existing .gitkeep files stay. Refuses a non-empty target unless
--force. Prints the next steps.
"""

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

from demo_common import DEMO, MARKER, SRC_ROOT, die

# Files a live workspace writes at its root; never part of a fresh demo workspace.
GENERATED = {"TOOLING.md", "BUDGET.md", "MANIFEST.csv", "INDEX.csv", "INDEX.md", "JOURNAL.md",
             "WORKFLOW-LOG.md"}
JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def skip(rel):
    parts = rel.parts
    if not parts:
        return False
    if parts[0] == ".git":
        return True
    if "__pycache__" in parts or rel.suffix == ".pyc" or rel.name in JUNK_NAMES:
        return True
    if len(parts) > 2 and parts[0] == "demo" and parts[1] == "build" and "node_modules" in parts:
        return True
    if len(parts) == 1 and rel.name in GENERATED:
        return True
    if len(parts) >= 2 and parts[0] == "demo" and parts[1].startswith("workspace"):
        return True  # demo workspaces made inside the repository (ignored by git)
    if rel == MARKER:
        return True
    return False


def copy_tree(src, dst, counter):
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if skip(rel):
            continue
        target = dst / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif p.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(p), str(target))
            counter[0] += 1


def install(src, dst, label, counter):
    """Copy a demo folder's files into the workspace, keeping what is there (.gitkeep files)."""
    if not src.is_dir():
        print("warning: %s is missing, so the demo %s were not installed" % (
            src.relative_to(SRC_ROOT).as_posix(), label))
        return 0
    n = 0
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if "__pycache__" in rel.parts or p.name in JUNK_NAMES:
            continue
        target = dst / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif p.is_file():
            if p.name == ".gitkeep" and target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(p), str(target))
            n += 1
    counter[0] += n
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(prog="setup", description="Make a fresh demo workspace.")
    ap.add_argument("target", nargs="?", help="the new workspace folder")
    ap.add_argument("--workspace", help="the new workspace folder (same as the positional TARGET)")
    ap.add_argument("--force", action="store_true", help="use the folder even if it is not empty")
    args = ap.parse_args(argv)
    raw = args.workspace or args.target
    if not raw:
        ap.print_usage(sys.stderr)
        die("setup: give the folder for the new workspace, for example: bash demo/scripts/setup "
            "~/kestrel-demo")
    target = Path(raw).expanduser().resolve()
    src = SRC_ROOT
    if target == src or src in target.parents:
        rel = target.relative_to(src).parts
        if not (len(rel) == 2 and rel[0] == "demo" and rel[1].startswith("workspace")):
            die("setup: choose a folder outside %s, or demo/workspace inside it (git ignores "
                "demo/workspace*/)." % src)
    if target in src.parents:
        die("setup: %s contains the repository; choose a new, separate folder." % target)
    if target.exists() and not target.is_dir():
        die("setup: %s exists and is not a folder." % target)
    if target.exists() and any(target.iterdir()) and not args.force:
        sys.stderr.write("setup: %s is not empty. Choose an empty folder, or add --force to copy "
                         "into it anyway (files with the same names are replaced; nothing is "
                         "deleted).\n" % target)
        return 1
    target.mkdir(parents=True, exist_ok=True)

    counter = [0]
    copy_tree(src, target, counter)
    n_files = counter[0]
    n_house = install(DEMO / "house", target / "house", "house settings", counter)
    n_know = install(DEMO / "knowledge", target / "knowledge", "knowledge files", counter)
    n_seeds = install(DEMO / "seeds", target / "seeds", "seeds", counter)
    marker = target / MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("Demo workspace made by demo/scripts/setup on %s from %s.\n"
                      "drop-batch and check-filing use this folder when run from inside it.\n"
                      % (dt.date.today().isoformat(), src), encoding="utf-8")

    t = str(target)
    print("Demo workspace ready: %s" % t)
    print("Copied %d workspace files, then %d house files, %d knowledge files and %d seed files."
          % (n_files, n_house, n_know, n_seeds))
    print("")
    print("Next steps:")
    print("1. Open the folder in Claude Code (or another assistant that reads RULES.md):")
    print("     cd %s" % t)
    print("2. Say \"cold start\". Answer its questions as demo/SCRIPT.md shows.")
    print("3. Put the first batch of emails in the inbox:")
    print("     bash demo/scripts/drop-batch 1")
    print("4. Say \"process the inbox\".")
    print("5. Check where the emails were filed:")
    print("     bash demo/scripts/check-filing --batch 1")
    print("6. Do the steps for batch 1 in demo/SCRIPT.md, then repeat 3 to 5 for batches 2 and 3.")
    print("The plain-English walk-through is in demo/README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
