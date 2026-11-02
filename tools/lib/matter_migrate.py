"""matter-migrate: convert matters from the old one-folder layout to agent/ + human/.

Old: <matter>/matter.md, brief.md, ..., corrections.md, correspondence/, documents/, work-product/ ...
New: <matter>/agent/  matter.md brief.md facts.md roster.md log.md documents.md
                      correspondence/ documents/ drafts/ history/ (and the Harvey pack)
     <matter>/human/  notes.md corrections.md roster.confirmed.md, and the lawyer's own files
Files are moved, never edited: received files keep their names and bytes. Deliverables that were in
work-product/ move to human/, and their documents.md rows follow. Old bundles and packs are dropped
(they are copies; the next work-bundle run rebuilds the pack). Idempotent.
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

TEMPLATES = Path("skills") / "operations" / "matter-memory" / "templates"


def migrate(root, m, run, dry):
    moves = []
    agent, human = m / common.AGENT, m / common.HUMAN
    for n in common.AGENT_FILES:
        if (m / n).exists():
            moves.append((m / n, agent / n))
    for d in ("correspondence", "documents", "drafts", "history"):
        if (m / d).exists():
            moves.append((m / d, agent / d))
    for n in common.HUMAN_ONLY_NAMES:
        if (m / n).exists():
            moves.append((m / n, human / n))
    wp = m / "work-product"
    dropped, deliverables = [], []
    if wp.is_dir():
        for f in sorted(wp.iterdir()):
            if f.is_dir() and (f.name.startswith("bundle-") or f.name.endswith("_harvey-pack") or f.name.startswith(".")):
                dropped.append(f)
            else:
                deliverables.append(f)
                moves.append((f, human / f.name))
    if dry:
        return moves, dropped
    agent.mkdir(exist_ok=True)
    human.mkdir(exist_ok=True)
    for src, dest in moves:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            k = 2
            while (dest.parent / ("%s-%d%s" % (dest.stem, k, dest.suffix))).exists():
                k += 1
            dest = dest.parent / ("%s-%d%s" % (dest.stem, k, dest.suffix))
        shutil.move(str(src), str(dest))
    for d in dropped:
        shutil.rmtree(str(d), ignore_errors=True)
    if wp.is_dir() and not any(wp.iterdir()):
        wp.rmdir()
    for d in common.MATTER_DIRS:
        (agent / d).mkdir(parents=True, exist_ok=True)
    tdir = Path(root) / TEMPLATES
    for n in common.HUMAN_ONLY_NAMES:
        if not (human / n).exists() and (tdir / n).is_file():
            shutil.copy2(str(tdir / n), str(human / n))
    docs = agent / "documents.md"
    if docs.exists():
        lines = common.read_text(docs).split("\n")
        changed = False
        for i, line in enumerate(lines):
            if not common.is_record_line(line):
                continue
            fields = common.split_pipe(line)
            if len(fields) > 1 and (fields[1] == "work-product" or fields[1].startswith("work-product/")):
                fields[1] = common.HUMAN + fields[1][len("work-product"):]
                if len(fields) > 2 and fields[2] == "work-product":
                    fields[2] = "human"
                lines[i] = common.join_pipe(fields)
                changed = True
        if changed:
            common.write_text_atomic(docs, "\n".join(lines))
    common.append_line(agent / "log.md", common.join_pipe(
        [common.stamp(root), "moved to the agent/ and human/ layout", "-", run]))
    return moves, dropped


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/matter-migrate",
                                 description="Convert matters in the old one-folder layout to agent/ + human/.")
    ap.add_argument("--run")
    ap.add_argument("--dry-run", action="store_true", help="show what would move, change nothing")
    a = ap.parse_args(argv)
    root = common.find_root()
    run = a.run or common.run_id(root)
    legacy = list(common.iter_legacy_matter_dirs(root))
    if not legacy:
        print("matter-migrate: nothing to do; every matter already has agent/ and human/.")
        return 0
    for m in legacy:
        moves, dropped = migrate(root, m, run, a.dry_run)
        print("%s %s: %d moved, %d old bundles dropped" % ("would migrate" if a.dry_run else "migrated",
                                                           common.rel(m, root), len(moves), len(dropped)))
    if not a.dry_run:
        print("Next: bash tools/matter-sync (writes START-HERE.md), then bash tools/work-bundle --all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
