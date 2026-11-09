"""Tests for the Claude Code harness files: .claude/hooks/before-write, .claude/hooks/after-write,
.claude/settings.json and .claude/agents/*.md.

The hooks run the way the harness runs them: `bash <hook>` with the hook JSON on stdin and
CLAUDE_PROJECT_DIR set, in a temporary workspace built from ROOT/tools, ROOT/.claude/hooks and
the matter-memory templates. No agent or harness process is started.

Run from the workspace root: python3 -m unittest discover -s tools/tests -p 'test_*.py'
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
SETTINGS = ROOT / ".claude" / "settings.json"
AGENTS = ROOT / ".claude" / "agents"
TEMPLATES = ROOT / "skills" / "operations" / "matter-memory" / "templates"
BASH = shutil.which("bash")
if BASH and os.name == "nt" and "system32" in BASH.lower():
    BASH = None  # the WSL launcher, not Git Bash: hook tests are skipped

sys.path.insert(0, str(ROOT / "tools" / "lib"))
import common  # noqa: E402

HISTORY_RE = re.compile(r"^(?P<stem>[^.]+)\.\d{4}-\d{2}-\d{2}_\d{6}(?:-\d+)?\.md$")
REFUSED = "Refused: {} is human-only (RULES.md, Protections). Tell the human what to write instead.\n"
POSIX = os.name != "nt"

TOOL_NAMES = ["scan-changes", "unpack-email", "place-email", "new-matter", "msg2eml", "hash-files",
              "history-copy", "lint-facts", "lint-received", "index-rebuild", "budget-update",
              "skills-sync", "work-bundle", "tooling-setup", "matter-sync", "matter-migrate", "learn-add", "learn-index",
              "init-workspace", "area-lines", "redline-changes"]
DEMO_SCRIPTS = ["setup", "drop-batch", "check-filing"]
AGENT_MODELS = {"filer": "sonnet", "reader": "sonnet", "indexer": "sonnet", "researcher": "sonnet",
                "drafter": "sonnet", "reviewer": "sonnet", "distiller": "opus"}
READ_ONLY_AGENTS = {"filer", "researcher", "reviewer"}
KNOWN_TOOLS = {"Read", "Grep", "Glob", "Bash", "Write", "Edit"}

VALUES = {"reference": "2026-0001", "area": "commercial", "sub_area": "customers",
          "subject": "acme-automotive", "title": "Acme NDA: mutual NDA before MSA talks",
          "opened": "2026-10-12", "follows": "", "subject_name": "Acme Automotive",
          "created": "2026-10-12"}

FACT1 = "F0001 | 2026-10-12 | party | valid_from= | source=correspondence/a.eml | supersedes= | Acme Automotive GmbH is the counterparty"
FACT2 = "F0002 | 2026-10-12 | term | valid_from=2026-10-12 | source=documents/received/NDA_v1.docx s4 | supersedes= | Term is three years"
FACT2_BAD_TYPE = "F0002 | 2026-10-12 | Term | valid_from= | source=documents/received/NDA_v1.docx s4 | supersedes= | Term is three years"
FACT3 = "F0003 | 2026-10-13 | term | valid_from= | source=documents/received/NDA_v1.docx s9 | supersedes= | English law governs"
FACT4_NO_SOURCE = "F0004 | 2026-10-13 | term | valid_from= | source= | supersedes= | Non-compete clause removed"


def fill(text):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: VALUES.get(m.group(1), ""), text)


def utf8_wc_works():
    """True when `wc -m` counts characters in some UTF-8 locale (the hooks' no-Python fallback)."""
    for loc in ("C.UTF-8", "en_US.UTF-8", "UTF-8"):
        try:
            out = subprocess.run(["wc", "-m"], input="\u00e4".encode("utf-8"), capture_output=True,
                                 env=dict(os.environ, LC_ALL=loc), timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return False
        if out.strip() == b"1":
            return True
    return False


def restricted_bin(dest, drop_jq):
    """A PATH directory with every program on PATH except Python (and jq when asked)."""
    dest.mkdir(parents=True, exist_ok=True)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d or not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if name.startswith("py") or (drop_jq and name == "jq"):
                continue
            src = os.path.join(d, name)
            link = dest / name
            if link.exists() or link.is_symlink() or not os.path.isfile(src) or not os.access(src, os.X_OK):
                continue
            try:
                os.symlink(src, link)
            except OSError:
                pass
    return str(dest)


@unittest.skipUnless(BASH, "bash is not on PATH")
class HookCase(unittest.TestCase):
    """A temporary workspace with one matter, its subject and the house folder."""

    ws_name = "legal ws"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hooks-"))
        self.ws = self.tmp / self.ws_name
        self.ws.mkdir()
        shutil.copytree(ROOT / "tools", self.ws / "tools",
                        ignore=shutil.ignore_patterns("__pycache__", "tests", "fixtures"))
        shutil.copytree(HOOKS, self.ws / ".claude" / "hooks")
        if SETTINGS.exists():
            shutil.copy2(SETTINGS, self.ws / ".claude" / "settings.json")
        house = self.ws / "house"
        house.mkdir()
        (self.ws / "areas" / "h" / "human").mkdir(parents=True)
        (self.ws / "areas" / "h" / "human" / "brief.md").write_text("mine\n", encoding="utf-8")
        brief = ROOT / "templates" / "house" / "brief.md"
        if brief.exists():
            shutil.copy2(brief, house / "brief.md")
        else:
            (house / "brief.md").write_text("---\nstatus: template\n---\n# House brief\n", encoding="utf-8")
        self.subject_dir = self.ws / "areas" / "commercial" / "customers" / "acme-automotive"
        self.matter = self.subject_dir / "2026-0001_acme-automotive_nda-review"
        for sub in common.MATTER_DIRS:
            (self.matter / sub).mkdir(parents=True, exist_ok=True)
        for name in common.MATTER_FILES:
            self.write(self.matter / name, fill((TEMPLATES / name).read_text(encoding="utf-8")))
        self.write(self.subject_dir / "subject.md", fill((TEMPLATES / "subject.md").read_text(encoding="utf-8")))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers

    @staticmethod
    def write(path, text):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    @staticmethod
    def read(path):
        with open(path, "r", encoding="utf-8", newline="") as fh:
            return fh.read()

    def rel(self, path):
        return Path(path).relative_to(self.ws).as_posix()

    def payload(self, path, tool="Write", event="PreToolUse"):
        tool_input = {"file_path": str(path)}
        if tool == "Write":
            tool_input["content"] = "new text"
        else:
            tool_input.update(old_string="a", new_string="b", replace_all=False)
        return {"session_id": "test", "transcript_path": "/dev/null", "cwd": str(self.ws),
                "hook_event_name": event, "tool_name": tool, "tool_input": tool_input,
                "tool_use_id": "toolu_test"}

    def run_hook(self, hook, data, env=None, cwd=None, path_env=None, project=True):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False)
        if isinstance(data, str):
            data = data.encode("utf-8")
        e = dict(os.environ)
        e.pop("CLAUDE_PROJECT_DIR", None)
        if project:
            e["CLAUDE_PROJECT_DIR"] = str(self.ws)
        e["INTAKE_ROOT"] = str(self.ws)
        if env:
            e.update(env)
        if path_env is not None:
            e["PATH"] = path_env
        p = subprocess.run([BASH, str(self.ws / ".claude" / "hooks" / hook)], input=data,
                           capture_output=True, env=e, cwd=str(cwd or self.ws), timeout=120)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

    def before(self, path, **kw):
        return self.run_hook("before-write", self.payload(path, event="PreToolUse"), **kw)

    def after(self, path, **kw):
        return self.run_hook("after-write", self.payload(path, event="PostToolUse"), **kw)

    def history(self, path):
        hist = Path(path).parent / "history"
        stem = Path(path).stem
        if not hist.is_dir():
            return []
        return sorted(p for p in hist.iterdir() if HISTORY_RE.match(p.name) and p.name.split(".")[0] == stem)

    def write_cycle(self, path, text, **kw):
        """What the harness does around one Write: before-write, the write, after-write."""
        rc, out, err = self.before(path, **kw)
        self.assertEqual(rc, 0, err)
        self.write(path, text)
        return self.after(path, **kw)

    def lint_stub(self, body):
        stub = self.ws / "tools" / "lint-facts"
        self.write(stub, "#!/usr/bin/env bash\n" + body + "\n")
        stub.chmod(0o755)


class BeforeWriteRefusalTest(HookCase):

    def assertRefused(self, path, shown, **kw):
        before = self.read(path) if Path(path).is_file() else None
        rc, out, err = self.before(path, **kw)
        self.assertEqual(rc, 2, err)
        self.assertEqual(err, REFUSED.format(shown))
        self.assertEqual(out, "")
        if before is not None:
            self.assertEqual(self.read(path), before)

    def test_corrections_md(self):
        p = self.matter / "corrections.md"
        self.assertRefused(p, self.rel(p))
        self.assertFalse((self.matter / "history").exists() and any((self.matter / "history").iterdir()))

    def test_any_file_in_a_matters_human_folder(self):
        p = self.matter / "human" / "call-note.md"
        self.assertRefused(p, self.rel(p))

    def test_roster_confirmed_md(self):
        p = self.matter / "roster.confirmed.md"
        self.assertRefused(p, self.rel(p))

    def test_house_brief_md(self):
        self.assertRefused(self.ws / "areas" / "h" / "human" / "brief.md", "areas/h/human/brief.md")

    def test_house_is_not_refused_by_the_hook(self):
        rc, _, err = self.before(self.ws / "house" / "brief.md")
        self.assertEqual(rc, 0, err)

    def test_new_file_under_house(self):
        self.assertRefused(self.ws / "areas" / "h" / "human" / "notes" / "extra.md", "areas/h/human/notes/extra.md")

    def test_human_only_names_at_any_depth(self):
        self.assertRefused(self.ws / "corrections.md", "corrections.md")
        self.assertRefused(self.ws / "areas" / "commercial" / "roster.confirmed.md",
                           "areas/commercial/roster.confirmed.md")

    def test_case_variants(self):
        self.assertRefused(self.ws / "areas" / "H" / "Human" / "Brief.md", "areas/H/Human/Brief.md")
        p = self.matter / "CORRECTIONS.md"
        self.assertRefused(p, self.rel(p))

    def test_dot_dot_segments(self):
        p = str(self.ws / "areas") + "/x/../h/human/./brief.md"
        self.assertRefused(p, "areas/h/human/brief.md")

    def test_relative_path_resolves_against_project(self):
        self.assertRefused("areas/h/human/brief.md", "areas/h/human/brief.md", cwd=self.tmp)

    def test_without_project_dir_uses_current_directory(self):
        self.assertRefused("areas/h/human/brief.md", "areas/h/human/brief.md", project=False)

    @unittest.skipUnless(POSIX, "symlinks")
    def test_symlink_into_house(self):
        link = self.matter / "memo.md"
        os.symlink(self.ws / "areas" / "h" / "human" / "brief.md", link)
        self.assertRefused(link, "areas/h/human/brief.md")

    @unittest.skipUnless(POSIX, "symlinks")
    def test_symlinked_project_dir(self):
        alias = self.tmp / "alias-ws"
        os.symlink(self.ws, alias)
        self.assertRefused(self.ws / "areas" / "h" / "human" / "brief.md", "areas/h/human/brief.md",
                           env={"CLAUDE_PROJECT_DIR": str(alias)})

    def test_ordinary_files_pass_silently(self):
        for p in (self.matter / "brief.md", self.matter / "roster.md", self.ws / "knowledge" / "x.md",
                  self.ws / "houseboat" / "brief.md", self.matter / "drafts" / "corrections-note.md"):
            rc, out, err = self.before(p)
            self.assertEqual((rc, out, err), (0, "", ""), p)
        self.assertEqual(self.history(self.matter / "brief.md"), [])


class BeforeWriteHistoryTest(HookCase):

    def test_copy_before_matter_write(self):
        p = self.matter / "matter.md"
        original = self.read(p)
        rc, out, err = self.before(p)
        self.assertEqual((rc, out, err), (0, "", ""))
        copies = self.history(p)
        self.assertEqual(len(copies), 1)
        self.assertRegex(copies[0].name, r"^matter\.\d{4}-\d{2}-\d{2}_\d{6}\.md$")
        self.assertEqual(self.read(copies[0]), original)

    def test_copy_for_facts_and_subject(self):
        for p in (self.matter / "facts.md", self.subject_dir / "subject.md"):
            rc, _, err = self.before(p)
            self.assertEqual(rc, 0, err)
            self.assertEqual(len(self.history(p)), 1, p)
            self.assertEqual(self.read(self.history(p)[0]), self.read(p))

    def test_edit_tool_payload(self):
        p = self.matter / "facts.md"
        rc, _, err = self.run_hook("before-write", self.payload(p, tool="Edit"))
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.history(p)), 1)

    def test_no_copy_of_a_new_file(self):
        p = self.ws / "areas" / "general" / "unfiled" / "2026-0009_unfiled_new-thing" / "matter.md"
        rc, out, err = self.before(p)
        self.assertEqual((rc, out, err), (0, "", ""))
        self.assertFalse((p.parent / "history").exists())

    def test_cold_start_hook_proof(self):
        """cold-start skill, step 10: create areas/_hook-test/matter.md, edit it once, expect a copy."""
        p = self.ws / "areas" / "_hook-test" / "matter.md"
        self.assertEqual(self.write_cycle(p, "# hook test\n"), (0, "", ""))
        self.assertEqual(self.history(p), [])
        rc, _, err = self.run_hook("before-write", self.payload(p, tool="Edit"))
        self.assertEqual(rc, 0, err)
        self.write(p, "# hook test, edited\n")
        self.assertEqual(self.after(p), (0, "", ""))
        self.assertEqual(len(self.history(p)), 1)
        self.assertEqual(self.read(self.history(p)[0]), "# hook test\n")

    def test_repeated_writes_get_distinct_copies(self):
        p = self.matter / "matter.md"
        for _ in range(3):
            self.assertEqual(self.before(p)[0], 0)
        names = [c.name for c in self.history(p)]
        self.assertEqual(len(names), 3)
        self.assertEqual(len(set(names)), 3)

    def test_inline_copy_without_history_copy_tool(self):
        (self.ws / "tools" / "history-copy").unlink(missing_ok=True)
        p = self.matter / "matter.md"
        self.assertEqual(self.before(p)[0], 0)
        self.assertEqual(len(self.history(p)), 1)
        self.assertEqual(self.read(self.history(p)[0]), self.read(p))

    def test_inline_copy_when_tool_copies_nothing(self):
        stub = self.ws / "tools" / "history-copy"
        self.write(stub, "#!/usr/bin/env bash\nexit 0\n")
        p = self.subject_dir / "subject.md"
        self.assertEqual(self.before(p)[0], 0)
        self.assertEqual(len(self.history(p)), 1)

    @unittest.skipUnless((ROOT / "tools" / "history-copy").exists(), "tools/history-copy not built yet")
    def test_copy_through_history_copy_tool(self):
        p = self.matter / "facts.md"
        self.assertEqual(self.before(p)[0], 0)
        self.assertEqual(len(self.history(p)), 1)


class NotesAndAgentWritesTest(HookCase):
    """A matter's agent/notes.md holds the lawyer's words: the agent may only add lines at the end.
    Writes that stand to agent/ memory files are recorded in changes/agent-writes.csv."""

    def setUp(self):
        super().setUp()
        self.notes = self.matter / "agent" / "notes.md"
        self.write(self.notes, "# Notes\n\nIntro.\n\n- 2026-11-01: (you said) first\n")
        self.ledger = self.ws / "changes" / "agent-writes.csv"

    def ledger_rows(self):
        if not self.ledger.is_file():
            return []
        return [line for line in self.read(self.ledger).splitlines()[1:] if line]

    def test_adding_a_line_stands_and_is_recorded(self):
        new = self.read(self.notes) + "- 2026-11-02: (you said) second\n"
        self.assertEqual(self.write_cycle(self.notes, new), (0, "", ""))
        self.assertEqual(self.read(self.notes), new)
        self.assertEqual(len(self.history(self.notes)), 1)
        rows = self.ledger_rows()
        self.assertEqual(len(rows), 1)
        self.assertIn(self.rel(self.notes), rows[0])
        self.assertIn(hashlib.sha256(new.encode("utf-8")).hexdigest(), rows[0])

    def test_changing_an_earlier_line_is_restored(self):
        old = self.read(self.notes)
        rc, out, err = self.write_cycle(self.notes, old.replace("first", "changed") + "- 2026-11-02: x\n")
        self.assertEqual(rc, 2)
        self.assertIn("you may only add lines at the end", err)
        self.assertEqual(self.read(self.notes), old)
        self.assertEqual(self.ledger_rows(), [])

    def test_line_endings_and_trailing_blanks_do_not_count_as_changes(self):
        self.write(self.notes, "# Notes\r\n\r\n- 2026-11-01: first\r\n\r\n\r\n")
        rc, _, err = self.write_cycle(self.notes, "# Notes\n\n- 2026-11-01: first\n- 2026-11-02: second\n")
        self.assertEqual(rc, 0, err)

    def test_notes_elsewhere_are_not_checked(self):
        p = self.ws / "knowledge" / "notes.md"
        self.write(p, "a\n")
        self.assertEqual(self.write_cycle(p, "b\n"), (0, "", ""))
        self.assertEqual(self.history(p), [])
        self.assertEqual(self.ledger_rows(), [])

    def test_only_agent_memory_files_are_recorded(self):
        draft = self.matter / "agent" / "drafts" / "reply.md"
        self.write(draft, "draft\n")
        self.assertEqual(self.write_cycle(draft, "draft 2\n"), (0, "", ""))
        self.assertEqual(self.ledger_rows(), [])
        brief = self.matter / "agent" / "brief.md"
        self.write(brief, "# Brief\n")
        self.assertEqual(self.write_cycle(brief, "# Brief\n\nNew.\n"), (0, "", ""))
        self.assertEqual(len(self.ledger_rows()), 1)

    def test_a_rejected_write_is_not_recorded(self):
        page = self.matter / "agent" / "matter.md"
        self.write(page, "# Matter\n")
        rc, _, _ = self.write_cycle(page, "x" * 17000)
        self.assertEqual(rc, 2)
        self.assertEqual(self.ledger_rows(), [])


class MalformedInputTest(HookCase):

    CASES = [b"", b"   \n", b"{not json", b"[]", b"null", b'{"tool_input": "x"}',
             b'{"tool_input": {"file_path": 5}}', b'{"tool_input": {}}', b"\xff\xfe\x00garbage"]

    def test_never_blocks(self):
        truncated = '{"tool_name": "Write", "tool_input": {"file_path": "%s"' % (self.ws / "areas" / "h" / "human" / "brief.md")
        for hook in ("before-write", "after-write"):
            for data in self.CASES + [truncated.encode("utf-8")]:
                rc, out, err = self.run_hook(hook, data)
                self.assertEqual(rc, 0, (hook, data, err))
                self.assertIn("warning", err, (hook, data))
        self.assertFalse((self.matter / "history").exists() and any((self.matter / "history").iterdir()))


class WindowsPathTest(HookCase):

    WIN_PROJECT = "C:\\Users\\alex\\legal ws"

    def win(self, *parts):
        return "\\".join([self.WIN_PROJECT] + list(parts))

    def run_win(self, file_path, project=None):
        data = {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": "x"}}
        return self.run_hook("before-write", data, env={"CLAUDE_PROJECT_DIR": project or self.WIN_PROJECT})

    def test_drive_letter_house(self):
        rc, out, err = self.run_win(self.win("areas", "h", "human", "brief.md"))
        self.assertEqual(rc, 2)
        self.assertEqual(err, REFUSED.format("areas/h/human/brief.md"))

    def test_drive_letter_case_and_mixed_slashes(self):
        rc, _, err = self.run_win("c:/users/ALEX/legal ws/areas/h/Human\\Brief.md")
        self.assertEqual(rc, 2)
        self.assertEqual(err, REFUSED.format("areas/h/Human/Brief.md"))

    def test_drive_letter_corrections_anywhere(self):
        rc, _, err = self.run_win("D:\\other\\place\\corrections.md")
        self.assertEqual(rc, 2)
        self.assertIn("corrections.md is human-only", err)

    def test_cygdrive_form(self):
        rc, _, err = self.run_win("/cygdrive/c/Users/alex/legal ws/areas/h/human/brief.md")
        self.assertEqual(rc, 2)
        self.assertEqual(err, REFUSED.format("areas/h/human/brief.md"))

    def test_drive_letter_ordinary_file(self):
        rc, out, err = self.run_win(self.win("areas", "commercial", "memo.md"))
        self.assertEqual((rc, out, err), (0, "", ""))

    @unittest.skipUnless(POSIX, "backslash paths map onto real files only on POSIX here")
    def test_backslash_path_to_real_files(self):
        p = self.matter / "matter.md"
        rc, _, err = self.run_hook("before-write", self.payload(str(p).replace("/", "\\")))
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.history(p)), 1)
        rc, _, err = self.run_hook("before-write",
                                   self.payload(str(self.ws / "areas" / "h" / "human" / "brief.md").replace("/", "\\")))
        self.assertEqual(rc, 2)
        self.assertEqual(err, REFUSED.format("areas/h/human/brief.md"))


class AfterWriteCapTest(HookCase):

    def message(self, path, n):
        return ("Rejected: %s is %d characters; the cap is 16,000. The previous version is restored. "
                "Consolidate below 12,000 characters and write it again.\n" % (self.rel(path), n))

    def test_oversize_matter_is_restored(self):
        p = self.matter / "matter.md"
        original = self.read(p)
        rc, out, err = self.write_cycle(p, "x" * (common.PAGE_CAP + 1))
        self.assertEqual(rc, 2)
        self.assertEqual(err, self.message(p, common.PAGE_CAP + 1))
        self.assertEqual(out, "")
        self.assertEqual(self.read(p), original)
        self.assertEqual(len(self.history(p)), 1)

    def test_oversize_subject_is_restored(self):
        p = self.subject_dir / "subject.md"
        original = self.read(p)
        rc, _, err = self.write_cycle(p, "y" * 20000)
        self.assertEqual(rc, 2)
        self.assertIn("is 20000 characters; the cap is 16,000", err)
        self.assertEqual(self.read(p), original)

    def test_at_the_cap_is_kept(self):
        p = self.matter / "matter.md"
        rc, out, err = self.write_cycle(p, "x" * common.PAGE_CAP)
        self.assertEqual((rc, out, err), (0, "", ""))
        self.assertEqual(len(self.read(p)), common.PAGE_CAP)

    def test_counts_characters_not_bytes(self):
        p = self.matter / "matter.md"
        text = "\u00e4" * 15000
        rc, _, err = self.write_cycle(p, text)
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.read(p), text)

    def test_crlf_counts_once_and_bom_is_ignored(self):
        p = self.matter / "matter.md"
        text = "\ufeff" + "abcdefg\r\n" * 2000  # 16,000 characters as common.char_count counts them
        rc, _, err = self.write_cycle(p, text)
        self.assertEqual(rc, 0, err)

    def test_new_oversize_file_is_moved_aside(self):
        p = self.ws / "areas" / "commercial" / "customers" / "volta-rail" / "subject.md"
        rc, _, err = self.write_cycle(p, "z" * 17000)
        self.assertEqual(rc, 2)
        self.assertFalse(p.exists())
        moved = list((p.parent / "history").glob("subject.rejected.*.md"))
        self.assertEqual(len(moved), 1)
        self.assertRegex(moved[0].name, r"^subject\.rejected\.\d{4}-\d{2}-\d{2}_\d{6}\.md$")
        self.assertEqual(self.read(moved[0]), "z" * 17000)
        self.assertIn("There was no previous version, so the file was moved to "
                      "areas/commercial/customers/volta-rail/history/subject.rejected.", err)
        self.assertIn("Consolidate below 12,000 characters and write it again.", err)

    def test_restores_the_newest_copy(self):
        p = self.matter / "matter.md"
        hist = self.matter / "history"
        for name, text in (("matter.2025-12-31_235959-99.md", "D"), ("matter.2026-01-01_000000.md", "A"),
                           ("matter.2026-01-01_000000-2.md", "B"), ("matter.2026-01-01_000000-10.md", "C"),
                           ("matter.rejected.2027-01-01_000000.md", "E"), ("matter.2027-01-01.md", "F")):
            self.write(hist / name, text)
        self.write(p, "x" * 16500)
        rc, _, err = self.after(p)
        self.assertEqual(rc, 2, err)
        self.assertEqual(self.read(p), "C")

    def test_cap_follows_common_py(self):
        lib = self.ws / "tools" / "lib" / "common.py"
        self.write(lib, re.sub(r"(?m)^PAGE_CAP = \d+", "PAGE_CAP = 20000", self.read(lib)))
        p = self.matter / "matter.md"
        rc, _, err = self.write_cycle(p, "x" * 17000)
        self.assertEqual(rc, 0, err)
        rc, _, err = self.write_cycle(p, "x" * 20001)
        self.assertEqual(rc, 2)
        self.assertIn("the cap is 20,000", err)

    def test_other_files_are_not_capped(self):
        p = self.matter / "brief.md"
        self.write(p, "b" * 30000)
        self.assertEqual(self.after(p), (0, "", ""))


class AfterWriteFactsStubTest(HookCase):
    """after-write's handling of tools/lint-facts results, with stand-in lint tools."""

    def setUp(self):
        super().setUp()
        self.facts = self.matter / "facts.md"
        self.write(self.facts, self.read(self.facts) + FACT1 + "\n")
        self.original = self.read(self.facts)

    def test_lint_missing_warns_and_keeps_the_write(self):
        (self.ws / "tools" / "lint-facts").unlink(missing_ok=True)
        rc, out, err = self.write_cycle(self.facts, self.original + FACT2 + "\n")
        self.assertEqual(rc, 0)
        self.assertIn("tools/lint-facts is missing", err)
        ctx = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(ctx["hookEventName"], "PostToolUse")
        self.assertIn("was not checked", ctx["additionalContext"])
        self.assertEqual(self.read(self.facts), self.original + FACT2 + "\n")

    def test_python_missing_exit_3_warns(self):
        self.lint_stub("echo 'Python 3.8 or later was not found' >&2; exit 3")
        rc, out, err = self.write_cycle(self.facts, self.original + FACT2 + "\n")
        self.assertEqual(rc, 0)
        self.assertIn("Python is missing", err)
        self.assertIn("additionalContext", out)

    def test_usage_error_warns(self):
        self.lint_stub("echo 'usage: lint-facts FILE' >&2; exit 2")
        rc, _, err = self.write_cycle(self.facts, self.original + FACT2 + "\n")
        self.assertEqual(rc, 0)
        self.assertIn("exited 2", err)

    def test_lint_gets_the_previous_copy_from_the_matter_folder(self):
        record = self.tmp / "lint-args.txt"
        # The folder as a Windows path under Git Bash (cygpath -m), so Python on Windows can compare it.
        self.lint_stub('here="$(cygpath -m "$PWD" 2>/dev/null || pwd)"; printf "%s\\n" "$here" "$@" > "$LINT_ARGS"; exit 0')
        rc, _, err = self.write_cycle(self.facts, self.original + FACT2 + "\n", env={"LINT_ARGS": str(record)})
        self.assertEqual(rc, 0, err)
        lines = record.read_text(encoding="utf-8").splitlines()
        self.assertTrue(os.path.samefile(lines[0], self.matter))
        self.assertEqual(lines[1:3], ["facts.md", "--previous"])
        self.assertEqual("history/" + self.history(self.facts)[-1].name, lines[3])

    def test_failure_restores_the_previous_version(self):
        self.lint_stub("echo 'facts.md:5: F0001: changed: facts.md is append-only'; exit 1")
        rc, out, err = self.write_cycle(self.facts, "garbage\n")
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertEqual(self.read(self.facts), self.original)
        self.assertTrue(err.startswith("Rejected: %s failed tools/lint-facts.\n" % self.rel(self.facts)))
        self.assertIn("facts.md:5: F0001: changed", err)
        self.assertIn("facts.md is append-only: the previous version is restored.", err)

    def test_failure_without_history_moves_the_file_aside(self):
        self.lint_stub("echo 'facts.md:1: bad id'; exit 1")
        p = self.ws / "areas" / "general" / "unfiled" / "2026-0002_unfiled_misc" / "facts.md"
        self.write(p, "nonsense\n")
        rc, _, err = self.after(p)
        self.assertEqual(rc, 2)
        self.assertFalse(p.exists())
        self.assertEqual(len(list((p.parent / "history").glob("facts.rejected.*.md"))), 1)
        self.assertIn("there was no previous version, so the file was moved to", err)


@unittest.skipUnless((ROOT / "tools" / "lint-facts").exists(), "tools/lint-facts not built yet")
class AfterWriteFactsLintTest(HookCase):
    """after-write with the real tools/lint-facts."""

    def setUp(self):
        super().setUp()
        self.facts = self.matter / "facts.md"
        self.base = self.read(self.facts)
        self.write(self.facts, self.base + FACT1 + "\n")

    def test_valid_append_is_kept(self):
        text = self.read(self.facts) + FACT2 + "\n" + FACT3 + "\n"
        rc, out, err = self.write_cycle(self.facts, text)
        self.assertEqual((rc, out, err), (0, "", ""))
        self.assertEqual(self.read(self.facts), text)

    def test_changed_earlier_line_is_restored(self):
        before = self.read(self.facts)
        changed = before.replace("is the counterparty", "is our customer") + FACT2 + "\n"
        rc, _, err = self.write_cycle(self.facts, changed)
        self.assertEqual(rc, 2)
        self.assertEqual(self.read(self.facts), before)
        self.assertIn("F0001", err)
        self.assertIn("facts.md is append-only: the previous version is restored.", err)

    def test_removed_line_is_restored(self):
        before = self.read(self.facts)
        rc, _, err = self.write_cycle(self.facts, self.base + FACT2 + "\n")
        self.assertEqual(rc, 2)
        self.assertEqual(self.read(self.facts), before)

    def test_new_error_is_restored(self):
        before = self.read(self.facts)
        rc, _, err = self.write_cycle(self.facts, before + FACT4_NO_SOURCE + "\n")
        self.assertEqual(rc, 2)
        self.assertIn("source=", err)
        self.assertEqual(self.read(self.facts), before)

    def test_errors_already_there_do_not_block(self):
        self.write(self.facts, self.read(self.facts) + FACT2_BAD_TYPE + "\n")  # written without hooks
        text = self.read(self.facts) + FACT3 + "\n"
        rc, out, err = self.write_cycle(self.facts, text)
        self.assertEqual(rc, 0, err)
        self.assertIn("already had these errors", err)
        self.assertIn("additionalContext", out)
        self.assertEqual(self.read(self.facts), text)

    def test_new_error_on_top_of_old_errors_is_restored(self):
        self.write(self.facts, self.read(self.facts) + FACT2_BAD_TYPE + "\n")
        before = self.read(self.facts)
        rc, _, err = self.write_cycle(self.facts, before + FACT4_NO_SOURCE + "\n")
        self.assertEqual(rc, 2)
        self.assertEqual(self.read(self.facts), before)


class NonAsciiWorkspaceTest(HookCase):
    ws_name = "legal w\u00f6rk space"

    def test_refusal_copy_and_cap(self):
        rc, _, err = self.before(self.ws / "areas" / "h" / "human" / "brief.md")
        self.assertEqual(rc, 2)
        self.assertEqual(err, REFUSED.format("areas/h/human/brief.md"))
        p = self.matter / "matter.md"
        original = self.read(p)
        rc, _, err = self.write_cycle(p, "x" * 16001)
        self.assertEqual(rc, 2, err)
        self.assertEqual(self.read(p), original)


@unittest.skipUnless(POSIX and BASH, "restricted PATH needs symlinks")
class NoPythonFallbackTest(HookCase):
    """The hooks without Python: jq parses the JSON; without jq, the sed fallback does."""

    drop_jq = False

    @classmethod
    def setUpClass(cls):
        cls.bin_tmp = Path(tempfile.mkdtemp(prefix="hooks-bin-"))
        cls.path_env = restricted_bin(cls.bin_tmp / "bin", cls.drop_jq)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.bin_tmp, ignore_errors=True)

    def setUp(self):
        super().setUp()
        if not self.drop_jq and not shutil.which("jq", path=self.path_env):
            self.skipTest("jq is not installed")
        self.assertIsNone(shutil.which("python3", path=self.path_env))

    def test_refusals(self):
        for p, shown in ((self.matter / "corrections.md", None), (self.ws / "areas" / "h" / "human" / "brief.md", "areas/h/human/brief.md")):
            rc, _, err = self.before(p, path_env=self.path_env)
            self.assertEqual(rc, 2, err)
            self.assertEqual(err, REFUSED.format(shown or self.rel(p)))

    def test_windows_path(self):
        data = {"tool_input": {"file_path": "C:\\Users\\alex\\ws\\areas\\h\\human\\brief.md"}}
        rc, _, err = self.run_hook("before-write", data, path_env=self.path_env,
                                   env={"CLAUDE_PROJECT_DIR": "C:\\Users\\alex\\ws"})
        self.assertEqual(rc, 2)
        self.assertEqual(err, REFUSED.format("areas/h/human/brief.md"))

    def test_history_copy_and_restore(self):
        p = self.matter / "matter.md"
        original = self.read(p)
        rc, _, err = self.write_cycle(p, "x" * 16001, path_env=self.path_env)
        self.assertEqual(rc, 2, err)
        self.assertIn("is 16001 characters", err)
        self.assertEqual(self.read(p), original)
        self.assertEqual(len(self.history(p)), 1)

    def test_awkward_path(self):
        d = self.ws / "areas" / 'odd "quoted" dir'
        p = d / "subject.md"
        self.write(p, "subject\n")
        rc, _, err = self.before(p, path_env=self.path_env)
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.history(p)), 1)

    @unittest.skipUnless(utf8_wc_works(), "no UTF-8 locale for wc -m")
    def test_counts_characters_without_python(self):
        p = self.matter / "matter.md"
        rc, _, err = self.write_cycle(p, "\u00e4" * 15000 + "a\r\n" * 300, path_env=self.path_env)
        self.assertEqual(rc, 0, err)

    def test_malformed_never_blocks(self):
        for data in MalformedInputTest.CASES:
            for hook in ("before-write", "after-write"):
                rc, _, err = self.run_hook(hook, data, path_env=self.path_env)
                self.assertEqual(rc, 0, (hook, data, err))

    def test_facts_lint_without_python_warns(self):
        p = self.matter / "facts.md"
        rc, out, err = self.write_cycle(p, self.read(p) + FACT1 + "\n", path_env=self.path_env)
        self.assertEqual(rc, 0, err)
        self.assertIn("warning", err)
        self.assertIn("additionalContext", out)


class NoPythonNoJqFallbackTest(NoPythonFallbackTest):
    drop_jq = True

    def test_truncated_json_is_not_acted_on(self):
        data = '{"tool_input": {"file_path": "%s"' % (self.ws / "areas" / "h" / "human" / "brief.md")
        rc, _, err = self.run_hook("before-write", data, path_env=self.path_env)
        self.assertEqual(rc, 0, err)

    def test_content_mentioning_file_path_is_ignored(self):
        data = {"tool_name": "Write",
                "tool_input": {"file_path": str(self.matter / "brief.md"),
                               "content": '{"file_path": "%s"}' % (self.ws / "areas" / "h" / "human" / "brief.md")}}
        rc, out, err = self.run_hook("before-write", data, path_env=self.path_env)
        self.assertEqual((rc, out, err), (0, "", ""))


class SettingsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(SETTINGS.read_text(encoding="utf-8"))

    def test_keys(self):
        self.assertEqual(self.data.get("$schema"), "https://json.schemastore.org/claude-code-settings.json")
        self.assertIsInstance(self.data["permissions"]["allow"], list)
        self.assertIsInstance(self.data["permissions"]["deny"], list)
        self.assertIsInstance(self.data["hooks"], dict)

    def test_deny_rules(self):
        deny = self.data["permissions"]["deny"]
        for rule in ("Edit(**/corrections.md)", "Edit(**/roster.confirmed.md)", "Edit(/areas/**/human/**)"):
            self.assertIn(rule, deny)
        self.assertNotIn("Edit(**/notes.md)", deny, "the agent writes the lawyer's words into agent/notes.md")
        self.assertNotIn("Edit(/house/**)", deny)
        self.assertIn("Edit(/house/**)", self.data["permissions"]["ask"], "house/ asks the lawyer first")
        for rule in deny:
            self.assertNotRegex(rule, r"^(Write|MultiEdit|NotebookEdit)\(", "path rules for these never match")

    def test_allow_rules(self):
        allow = self.data["permissions"]["allow"]
        for rule in allow:
            self.assertRegex(rule, r"^Bash\(bash (tools|demo/scripts)/[a-z0-9-]+ \*\)$")
        for name in TOOL_NAMES:
            self.assertIn("Bash(bash tools/%s *)" % name, allow)
        for name in DEMO_SCRIPTS:
            self.assertIn("Bash(bash demo/scripts/%s *)" % name, allow)
        for p in (ROOT / "tools").iterdir():
            if p.is_file() and not p.suffix and p.read_bytes()[:2] == b"#!":
                self.assertIn("Bash(bash tools/%s *)" % p.name, allow, "new tool without an allow rule")

    def test_hooks(self):
        for event, script in (("PreToolUse", "before-write"), ("PostToolUse", "after-write")):
            groups = self.data["hooks"][event]
            commands = []
            for g in groups:
                tools = {t.strip() for t in re.split(r"[|,]", g.get("matcher", ""))}
                if {"Write", "Edit", "MultiEdit"} <= tools:
                    commands += [h["command"] for h in g["hooks"] if h.get("type") == "command"]
            self.assertIn('bash "$CLAUDE_PROJECT_DIR/.claude/hooks/%s"' % script, commands, event)
        bash_hooks = [h["command"] for g in self.data["hooks"]["PreToolUse"] if g.get("matcher") == "Bash"
                      for h in g["hooks"]]
        self.assertIn('bash "$CLAUDE_PROJECT_DIR/.claude/hooks/before-bash"', bash_hooks)


class BeforeBashTest(unittest.TestCase):
    """before-bash refuses Bash commands that would change memory, human-only or house files outside
    Write and Edit (so the history copy and checks cannot be skipped), and lets reading and tools through."""

    REFUSED = [
        "python3 -c \"open('areas/c/s/2026-0002_a_b/agent/matter.md','w').write('x')\"",
        "python3 - <<'PY'\nfrom pathlib import Path\nPath('agent/facts.md').write_text('x')\nPY",
        "python3 - <<'PY'\np='agent/brief.md'\nwith open(p, \"w\", encoding=\"utf-8\") as fh: fh.write('x')\nPY",
        "echo x >> areas/c/s/2026-0002_a_b/agent/facts.md",
        "cat new.md | tee agent/notes.md",
        "sed -i 's/a/b/' agent/matter.md",
        "cp /tmp/x.md areas/c/s/2026-0002_a_b/agent/matter.md",
        "rm areas/c/s/2026-0002_a_b/agent/facts.md",
        "echo x > areas/c/s/2026-0002_a_b/human/corrections.md",
        "echo x > house/brief.md",
        "git checkout -- house",
        "echo x > AREAS\\C\\S\\2026-0002_A_B\\AGENT\\MATTER.MD",
        "echo '2026-11-09 10:00 | filed | - | R1' >> areas/c/s/2026-0002_a_b/agent/log.md",
        "printf 'x' >> agent/documents.md",
        "f=areas/c/s/2026-0002_a_b/agent/log.md; echo x >> \"$f\"",
        "NOTES=\"agent/notes.md\"; printf '%s\\n' '- 2026-11-09: (you said) fine' | tee -a \"$NOTES\"",
        "for f in agent/log.md; do echo x >> ${f}; done",
        "echo x >> \"/c/Users/Jane Doe/OneDrive - Kestrel/legal/areas/c/s/2026-0002_a_b/agent/notes.md\"",
        "cat >> 'C:\\Users\\Jane Doe\\OneDrive - Kestrel\\areas\\c\\s\\2026-0002_a_b\\agent\\log.md' <<'EOF'\nx\nEOF",
        "awk -i inplace '{print}' agent/log.md",
        "truncate -s 0 agent/log.md",
    ]
    ALLOWED = [
        "cat agent/matter.md",
        "bash tools/lint-facts agent/facts.md --live > changes/live.txt 2>/dev/null",
        "bash tools/history-copy agent/matter.md",
        "python3 -c \"print(open('agent/matter.md', 'r', encoding='utf-8').read())\"",
        "printf 'did | x | correspondence/a.eml\\n' | bash tools/learn-add --matter 2026-0002 --work-type nda",
        "cp agent/matter.md /tmp/copy.md",
        "wc -m agent/matter.md agent/subject.md",
        "bash tools/place-email inbox/a.eml --to areas/c/s/2026-0002_a_b --run R1 --reason x --confidence 0.9",
        "echo hello > /tmp/out.txt",
        "git status",
        "grep -c pending areas/c/s/2026-0002_a_b/agent/documents.md",
        "tail -n 5 agent/log.md",
        "echo x >> CHANGELOG.md",
        "for f in /tmp/a /tmp/b; do echo x > \"$f\"; done",
        "cat \"/c/Users/Jane Doe/OneDrive - Kestrel/areas/c/s/2026-0002_a_b/agent/log.md\" > /tmp/log.txt",
    ]

    def run_hook(self, data):
        if not isinstance(data, bytes):
            data = json.dumps(data).encode("utf-8")
        p = subprocess.run([BASH, str(HOOKS / "before-bash")], input=data, capture_output=True, timeout=60)
        return p.returncode, p.stderr.decode("utf-8", "replace")

    @unittest.skipUnless(BASH, "bash not found")
    def test_refused_and_allowed(self):
        for cmd in self.REFUSED:
            rc, err = self.run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}})
            self.assertEqual(rc, 2, cmd)
            self.assertIn("Refused:", err)
            self.assertIn("Use the Edit tool", err)
        for cmd in self.ALLOWED:
            rc, err = self.run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}})
            self.assertEqual((rc, err), (0, ""), cmd)

    @unittest.skipUnless(BASH, "bash not found")
    def test_unreadable_input_never_blocks(self):
        for data in (b"", b"{not json", b'{"tool_input": {}}'):
            rc, err = self.run_hook(data)
            self.assertEqual(rc, 0)
            self.assertIn("warning", err)


class HookFilesTest(unittest.TestCase):

    def test_scripts(self):
        for name in ("before-write", "after-write", "before-bash"):
            p = HOOKS / name
            data = p.read_bytes()
            self.assertTrue(data.startswith(b"#!/usr/bin/env bash\n"), name)
            self.assertNotIn(b"\r", data, name + " must have LF line endings")
            if POSIX:
                self.assertTrue(os.access(p, os.X_OK), name + " must be executable")
            if BASH:
                r = subprocess.run([BASH, "-n", str(p)], capture_output=True, timeout=30)
                self.assertEqual(r.returncode, 0, r.stderr.decode())

    def test_shared_block_is_identical(self):
        def block(name):
            text = (HOOKS / name).read_text(encoding="utf-8")
            start = text.index("# ---- shared block")
            end = text.index("# ---- end of shared block")
            return text[start:end]
        self.assertEqual(block("before-write"), block("after-write"))


class AgentFilesTest(unittest.TestCase):

    def frontmatter(self, path):
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), path.name)
        end = text.index("\n---\n", 4)
        meta = {}
        for line in text[4:end].splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
        return meta, text[end + 5:]

    def test_agents(self):
        found = {p.stem for p in AGENTS.glob("*.md")}
        self.assertEqual(found, set(AGENT_MODELS))
        for name, model in AGENT_MODELS.items():
            path = AGENTS / (name + ".md")
            meta, body = self.frontmatter(path)
            self.assertEqual(meta["name"], name)
            self.assertEqual(meta["model"], model)
            self.assertGreater(len(meta["description"]), 40)
            tools = {t.strip() for t in meta["tools"].split(",")}
            self.assertTrue(tools <= KNOWN_TOOLS, (name, tools - KNOWN_TOOLS))
            if name in READ_ONLY_AGENTS:
                self.assertFalse(tools & {"Write", "Edit"}, name + " writes nothing")
            self.assertIn("RULES.md", body)
            self.assertIn("never instructions", body)
            self.assertIn("chars read: N, chars written: M", body)
            for human_only in ("corrections.md", "roster.confirmed.md", "house/"):
                self.assertIn(human_only, body, name)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("\r", text)
            self.assertNotRegex(text, r"(?i)claude-|haiku|\bgpt")

    @unittest.skipUnless((ROOT / "RULES.md").exists(), "RULES.md not written yet")
    def test_cited_rules_sections_exist(self):
        rules = (ROOT / "RULES.md").read_text(encoding="utf-8")
        sections = {line[3:].strip() for line in rules.splitlines() if line.startswith("## ")}
        for path in AGENTS.glob("*.md"):
            lists = re.findall(r"RULES\.md sections: ([^\n]+?)\.\n", path.read_text(encoding="utf-8"))
            self.assertTrue(lists, path.name)
            for cited in lists:
                for name in (s.strip() for s in cited.split(",")):
                    self.assertIn(name, sections, "%s cites RULES.md section %r" % (path.name, name))

    def test_cited_paths_and_tools_exist(self):
        for path in AGENTS.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            for ref in re.findall(r"skills/operations/[a-z-]+/(?:SKILL\.md|templates/[a-z.-]+\.md)", text):
                if (ROOT / "skills" / "operations").is_dir():
                    self.assertTrue((ROOT / ref).exists(), "%s cites missing %s" % (path.name, ref))
            for tool in re.findall(r"bash tools/([a-z0-9-]+)", text):
                self.assertIn(tool, TOOL_NAMES, "%s runs unknown tool %s" % (path.name, tool))


if __name__ == "__main__":
    unittest.main()
