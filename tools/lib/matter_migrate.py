"""matter-migrate: convert matters from the old one-folder layout to agent/ + human/.

Old: <matter>/matter.md, brief.md, ..., corrections.md, correspondence/, documents/, work-product/ ...
New: <matter>/agent/  matter.md brief.md facts.md roster.md notes.md log.md documents.md
                      correspondence/ documents/ drafts/ history/ (and the Harvey pack)
     <matter>/human/  corrections.md roster.confirmed.md, and the lawyer's own files
Files are moved, never edited: received files keep their names and bytes. Deliverables that were in
work-product/ move to human/, and their documents.md rows follow. Old bundles and packs are dropped
(they are copies; the next work-bundle run rebuilds the pack).
Harvey packs that an earlier version split by mistake (it took a pack, which holds a copy of matter.md,
for an old matter) are removed so work-bundle rebuilds them; see repair_packs.
Matters already in the new layout are tidied: human/notes.md moves to agent/notes.md (the agent now
writes there what the lawyer says in chat), and a missing memory file is added from the templates.
Never overwrites. Idempotent.
"""

import argparse
import re
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
    repaired = repair_packs(root, run, a.dry_run)
    if repaired:
        print("%s %d matters: Harvey packs split by an earlier matter-migrate %s (they are only copies; "
              "bash tools/work-bundle --all rebuilds them)" % ("would repair" if a.dry_run else "repaired",
                                                               repaired, "would be removed" if a.dry_run else "removed"))
    legacy = list(common.iter_legacy_matter_dirs(root))
    for m in legacy:
        moves, dropped = migrate(root, m, run, a.dry_run)
        print("%s %s: %d moved, %d old bundles dropped" % ("would migrate" if a.dry_run else "migrated",
                                                           common.rel(m, root), len(moves), len(dropped)))
    tidied = 0 if a.dry_run else tidy(root, run)
    if not legacy and not tidied and not repaired:
        print("matter-migrate: nothing to do; every matter has agent/, human/ and its files.")
        return 0
    if tidied:
        print("tidied %d matters: notes.md now in agent/, missing memory files added from the templates" % tidied)
    if not a.dry_run:
        print("Next: bash tools/matter-sync (writes START-HERE.md), then bash tools/work-bundle --all.")
    return 0


SPLIT_LOG_LINE = "moved to the agent/ and human/ layout"


def free_name(path):
    """path, or <stem>-2<suffix>, -3 ... when it is taken."""
    path = Path(path)
    stem, suffix, k = path.stem, path.suffix, 2
    while path.exists():
        path = path.with_name("%s-%d%s" % (stem, k, suffix))
        k += 1
    return path


def is_split_log(path):
    """A log.md that holds only the line an earlier matter-migrate wrote into a Harvey pack it split."""
    lines = [x for x in common.read_text(path).splitlines() if x.strip()]
    return bool(lines) and all(SPLIT_LOG_LINE in x for x in lines)


def repair_packs(root, run, dry):
    """Undo an earlier mistake: matter-migrate took each Harvey pack (it holds a copy of matter.md) for an
    old one-folder matter and split it into agent/ and human/. A pack is only a copy, so a split pack is
    removed; the next work-bundle run rebuilds it. A file the lawyer saved at the top of the pack after it
    was built moves to the matter's human/ first. A log.md that work-bundle then moved into human/ (only the
    split's log line) goes to agent/history/, and its documents.md row is dropped. Returns matters repaired."""
    repaired = 0
    stamp_text = common.stamp(root)
    for m in common.iter_matter_dirs(root):
        agent, human = common.agent_dir(m), common.human_dir(m)
        did = []
        for pack in sorted(agent.glob("*_harvey-pack")):
            if not (pack.is_dir() and (pack / common.AGENT).is_dir()):
                continue
            did.append("removed the split Harvey pack %s" % pack.name)
            if dry:
                continue
            stamp = pack / ".stamp"
            built = stamp.stat().st_mtime if stamp.is_file() else None
            for f in sorted(pack.iterdir()):
                if built is not None and f.is_file() and f.name != ".stamp" and f.stat().st_mtime > built:
                    human.mkdir(exist_ok=True)
                    dest = free_name(human / f.name)
                    shutil.move(str(f), str(dest))
                    did.append("moved %s from the pack to human/%s" % (f.name, dest.name))
            common.force_rmtree(pack)
        stray = [f for f in sorted(human.glob("log.md*")) if f.is_file() and is_split_log(f)] if human.is_dir() else []
        for f in stray:
            dest = free_name(agent / "history" / ("log.split-pack.%s.md" % run))
            did.append("moved human/%s (a stray log line from the split pack) to %s"
                       % (f.name, dest.relative_to(m).as_posix()))
            if dry:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
            docs = agent / "documents.md"
            if docs.is_file():
                lines = common.read_text(docs).split("\n")
                keep = [x for x in lines if not (common.is_record_line(x) and
                                                 common.split_pipe(x)[:2] == [f.name, common.HUMAN])]
                if len(keep) != len(lines):
                    common.write_text_atomic(docs, "\n".join(keep))
        if did:
            repaired += 1
            for line in did:
                print("%s: %s%s" % (common.rel(m, root), "would have " if dry else "", line))
            if not dry:
                common.append_line(agent / "log.md", common.join_pipe(
                    [stamp_text, "repaired: " + "; ".join(did), "-", run]))
    return repaired


def has_notes(path):
    """True when a notes file holds anything beyond the template: a line outside HTML comments that is
    not a heading, and not the template's opening paragraph."""
    text = re.sub(r"<!--.*?-->", "", common.read_text(path), flags=re.S)
    for line in text.splitlines():
        t = line.strip()
        if t and not t.startswith("#") and not t.startswith("Your notes on this matter"):
            return True
    return False


def tidy(root, run):
    """Matters already in agent/ + human/: notes.md belongs in agent/ (the agent writes what the lawyer
    says); add any missing memory file from the templates. Never overwrites. Returns matters changed."""
    tdir = Path(root) / TEMPLATES
    changed = 0
    for m in common.iter_matter_dirs(root):
        did = []
        old_notes, new_notes = common.human_dir(m) / "notes.md", common.agent_dir(m) / "notes.md"
        if old_notes.is_file():
            if new_notes.is_file() and not has_notes(new_notes):
                kept = common.history_copy(new_notes)        # the blank file is kept in history/, not lost
                new_notes.unlink()
                did.append("blank agent/notes.md kept as %s" % kept.relative_to(m).as_posix())
            if not new_notes.exists():
                shutil.move(str(old_notes), str(new_notes))
                did.append("moved human/notes.md to agent/notes.md")
            else:
                print("%s: human/notes.md and agent/notes.md both hold notes; both left as they are. "
                      "Copy your lines from human/notes.md into agent/notes.md." % common.rel(m, root))
        for n in common.MATTER_FILES:
            target = common.mpath(m, n)
            if not target.exists() and (tdir / n).is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(tdir / n), str(target))
                did.append("added %s" % target.relative_to(m).as_posix())
        if did:
            changed += 1
            common.append_line(common.agent_dir(m) / "log.md", common.join_pipe(
                [common.stamp(root), "; ".join(did), "-", run]))
    return changed


if __name__ == "__main__":
    sys.exit(main())
