"""Tests for tools/learn-add, tools/learn-mark and tools/learn-index (the learning register)."""

import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lib"))
from test_new_matter import WorkspaceTest  # noqa: E402
import common  # noqa: E402

SKILL = """---
name: nda-review
description: "Working skill. Use when an NDA comes in for review."
area: commercial
version: %s
status: %s
written: %s
evidence_lines: %s
supporting_matters: 2026-0001, 2026-0002
---
# NDA review

## Questions we ask first
- Which of our companies signs? (2026-0001)
"""


class LearningBase(WorkspaceTest):
    def add(self, stdin, *args):
        import os
        e = dict(os.environ)
        e["INTAKE_ROOT"] = str(self.ws.root)
        return subprocess.run(["bash", "tools/learn-add"] + list(args), input=stdin, capture_output=True,
                              text=True, env=e, cwd=str(self.ws.root))

    def index(self, *args):
        return self.ws.run("learn-index", *args)

    def page(self):
        return (self.ws.root / "learning" / "index.md").read_text(encoding="utf-8")

    def evidence(self, ref, lines="asked | NDA review requested | x\ndid | Marked up the NDA | y\n",
                 slug="nda-review", name="NDA review", *more):
        r = self.add(lines, "--matter", ref, "--work-type", slug, "--work-type-name", name,
                     "--area", "commercial", "--date", "2026-11-02", *more)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def skill(self, version="1", status="working", written="2026-11-03", lines="4", slug="nda-review"):
        p = self.ws.root / "skills" / "commercial" / slug / "SKILL.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((SKILL % (version, status, written, lines)).replace("nda-review", slug), encoding="utf-8")
        return p


class LearnAddTest(LearningBase):

    def test_evidence_lines_and_new_work_type(self):
        r = self.add("asked | Sales asked whether the customer's NDA can be signed | agent/correspondence/a.eml\n"
                     "position | Non-compete deleted; customer accepted | agent/documents/ours/nda.docx\n"
                     "nonsense | refused line | x\n",
                     "--matter", "2026-0001", "--work-type", "nda-review", "--work-type-name", "NDA review",
                     "--area", "commercial", "--date", "2026-11-02")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("2 added, 1 refused", r.stdout)
        p = self.ws.root / "learning" / "work-types" / "nda-review.md"
        meta, body = common.read_frontmatter_file(p)
        self.assertEqual((meta["work_type"], meta["area"]), ("NDA review", "commercial"))
        lines = [l for l in body.split("\n") if l.startswith("2026-0001-")]
        self.assertEqual(lines[0].split(" | ")[:4], ["2026-0001-1", "2026-11-02", "2026-0001", "asked"])
        self.assertEqual(lines[1].split(" | ")[-1], "observed")
        # a second reader on the same matter continues the numbering
        self.add("phrasing | \"Please go ahead and sign.\" | agent/correspondence/b.eml\n",
                 "--matter", "2026-0001", "--work-type", "nda-review")
        self.assertIn("2026-0001-3 |", p.read_text())

    def test_run_is_accepted_everywhere_and_dates_the_lines(self):
        r = self.add("asked | Sales asked for an NDA | agent/correspondence/a.eml\n",
                     "--matter", "2026-0001", "--work-type", "nda-review", "--work-type-name", "NDA review",
                     "--area", "commercial", "--run", "2026-11-08_101500")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        body = (self.ws.root / "learning" / "work-types" / "nda-review.md").read_text()
        self.assertIn("2026-0001-1 | 2026-11-08 | 2026-0001 | asked", body)
        r = self.add("entity | Example Ltd is our UK company | 2026-0001 email\n", "--matter", "2026-0001",
                     "--knowledge", "--run", "2026-11-08_101500", "--date", "2026-11-09")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("2026-11-09", (self.ws.root / "learning" / "knowledge-candidates.md").read_text())
        self.assertEqual(self.ws.run("learn-index", "--run", "2026-11-08_101500").returncode, 0)
        self.assertEqual(self.ws.run("learn-index", "--quiet", "--run=R").returncode, 0)
        self.assertEqual(self.ws.run("learn-mark", "K-2026-0001-1", "--status", "dropped (test)",
                                     "--run", "2026-11-08_101500").returncode, 0)

    def test_knowledge_and_open_points(self):
        self.assertEqual(self.add("entity | Example ME FZE is a UAE free zone company | 2026-0001 email\n"
                                  "position | Liability capped at 100% of annual fees | 2026-0001 our email\n",
                                  "--matter", "2026-0001", "--knowledge").returncode, 0)
        self.assertEqual(self.add("nda-review | Why was the cap raised for one customer only? | 2026-0003\n",
                                  "--matter", "2026-0003", "--question").returncode, 0)
        kc = (self.ws.root / "learning" / "knowledge-candidates.md").read_text()
        self.assertIn("K-2026-0001-1 |", kc)
        self.assertIn("K-2026-0001-2 | ", kc)
        self.assertIn("| pending", kc)
        self.assertIn("Q-2026-0003-1 |", (self.ws.root / "learning" / "questions.md").read_text())

    def test_the_watching_kinds_are_accepted(self):
        r = self.add("expected | ask: which company signs; the purpose. do: send our mutual template | brief.md\n"
                     "we-asked | Which of our companies signs? | correspondence/2026-11-03_0910_out_legal_re-nda.eml\n"
                     "answer | to \"which company signs\": the German company | correspondence/2026-11-03_1502_in_sales_re-nda.eml\n"
                     "compared | partly: asked 1 of 2 expected; missed: the term; not needed: the purpose | correspondence/2026-11-03_0910_out_legal_re-nda.eml\n"
                     "correction | Not our practice: Dutch law for NDAs | lawyer in chat 2026-11-20 | lawyer\n",
                     "--matter", "2026-0001", "--work-type", "nda-review")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("5 added", r.stdout)
        body = (self.ws.root / "learning" / "work-types" / "nda-review.md").read_text()
        self.assertIn("| correction | Not our practice: Dutch law for NDAs | lawyer in chat 2026-11-20 | lawyer", body)

    def test_a_position_from_inbound_mail_is_only_stated(self):
        r = self.add("position | We accepted a 150% cap | correspondence/2026-11-03_1502_in_acme_re-msa.eml\n"
                     "position | We held the cap at 100% | correspondence/2026-11-04_0910_out_legal_re-msa.eml\n"
                     "context | The customer says its policy needs 150% | correspondence/2026-11-03_1502_in_acme_re-msa.eml\n"
                     "approval | The CFO approved the exception | correspondence/2026-11-05_0800_in_cfo_re-msa.eml\n",
                     "--matter", "2026-0002", "--work-type", "msa-negotiation")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("kept as stated, not observed", r.stdout)
        lines = [l for l in (self.ws.root / "learning" / "work-types" / "msa-negotiation.md").read_text().split("\n")
                 if l.startswith("2026-0002-")]
        self.assertEqual([l.split(" | ")[-1] for l in lines], ["stated", "observed", "observed", "observed"])

    def test_lines_as_arguments_need_no_pipe(self):
        r = self.ws.run("learn-add", "--matter", "2026-0001", "--work-type", "nda-review", "--date", "2026-11-02",
                        "--line", "did | Sent our template | correspondence/a.eml",
                        "--line", 'phrasing | "Please send it as it is." | correspondence/a.eml')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("2 added", r.stdout)
        body = (self.ws.root / "learning" / "work-types" / "nda-review.md").read_text()
        self.assertIn('2026-0001-2 | 2026-11-02 | 2026-0001 | phrasing | "Please send it as it is." | '
                      "correspondence/a.eml | observed", body)
        r = self.ws.run("learn-add", "--matter", "chat", "--knowledge", "--line", "entity | Example Ltd is ours | chat")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.add("", "--matter", "2026-0001", "--work-type", "nda-review").returncode, 2)

    def test_the_workspaces_own_types(self):
        r = self.add("trade_mark | KESTREL is registered in the UK, class 7 | register.xlsx row 3\n",
                     "--matter", "2026-0001", "--knowledge")
        self.assertEqual(r.returncode, 1, r.stdout)
        (self.ws.root / "knowledge").mkdir(exist_ok=True)
        (self.ws.root / "knowledge" / "TYPES.local.md").write_text(
            "# Types added in this workspace\n\n| Type | Folder | What it holds |\n|---|---|---|\n"
            "| trade_mark | knowledge/trade-marks/ | A registered mark and its renewal date |\n", encoding="utf-8")
        r = self.add("trade_mark | KESTREL is registered in the UK, class 7 | register.xlsx row 3\n",
                     "--matter", "2026-0001", "--knowledge")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class LearnMarkTest(LearningBase):

    def test_marks_facts_and_open_points(self):
        self.add("entity | Example Ltd is our UK company | 2026-0001 email\n"
                 "entity | Example GmbH is our German company | 2026-0001 email\n"
                 "policy | Travel policy applies to contractors | 2026-0001 email\n",
                 "--matter", "2026-0001", "--knowledge")
        self.add("nda-review | Do we always ask for the purpose? | 2026-0001\n", "--matter", "2026-0001", "--question")
        r = self.ws.run("learn-mark", "K-2026-0001-1,K-2026-0001-2", "--status",
                        "written (knowledge/entities/example-ltd.md)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("2 marked", r.stdout)
        kc = [l for l in (self.ws.root / "learning" / "knowledge-candidates.md").read_text().split("\n")
              if l.startswith("K-")]
        self.assertTrue(kc[0].endswith("| written (knowledge/entities/example-ltd.md)"), kc[0])
        self.assertTrue(kc[1].endswith("| written (knowledge/entities/example-ltd.md)"), kc[1])
        self.assertTrue(kc[2].endswith("| pending"), kc[2])
        self.assertIn("| Example Ltd is our UK company | 2026-0001 email |", kc[0])
        r = self.ws.run("learn-mark", "Q-2026-0001-1", "--status",
                        "settled (2026-11-20): yes, in every matter so far (2026-0001, 2026-0004)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        q = (self.ws.root / "learning" / "questions.md").read_text()
        self.assertIn("| settled (2026-11-20): yes, in every matter so far (2026-0001, 2026-0004)", q)
        self.assertTrue(q.startswith(common.FENCE))

    def test_wrote_keeps_the_agents_version(self):
        p = self.ws.root / "skills" / "commercial" / "nda-review" / "SKILL.md"
        p.parent.mkdir(parents=True)
        p.write_text("v1\n", encoding="utf-8")
        r = self.ws.run("learn-mark", "--wrote", "skills/commercial/nda-review/SKILL.md", "skills/nosuch/SKILL.md")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("no file: skills/nosuch/SKILL.md", r.stdout)
        copies = sorted((p.parent / "history").iterdir())
        self.assertEqual(len(copies), 1)
        self.assertTrue(copies[0].name.endswith(".written.md"))
        self.assertEqual(copies[0].read_text(encoding="utf-8"), "v1\n")
        self.assertEqual(self.ws.run("learn-mark", "K-1", "--wrote", "x").returncode, 2)
        self.assertEqual(self.ws.run("learn-mark", "K-1").returncode, 2)

    def test_unknown_ids(self):
        self.add("entity | Example Ltd is our UK company | x\n", "--matter", "2026-0001", "--knowledge")
        r = self.ws.run("learn-mark", "K-2026-0001-1,K-2026-0009-9", "--status", "dropped (not a company fact)")
        self.assertEqual(r.returncode, 1)
        self.assertIn("1 marked, 1 not found", r.stdout)
        self.assertEqual(self.ws.run("learn-mark", "X-1", "--status", "x").returncode, 2)


class LearnIndexTest(LearningBase):

    def due(self, *args):
        r = self.index(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return ([l for l in r.stdout.split("\n") if l.startswith("due: ")],
                [l for l in r.stdout.split("\n") if l.startswith("later: ")])

    def test_first_write_needs_two_matters_showing_our_work(self):
        self.evidence("2026-0001")
        self.evidence("2026-0004", "asked | Guarantee review | x\n", "pcg-review", "Guarantee review")
        due, later = self.due("--today", "2026-11-02")
        self.assertEqual((due, later), ([], []))
        page = self.page()
        self.assertIn("| [NDA review](work-types/nda-review.md) | 1 | 2 | 0 | none yet |", page)
        self.assertIn("collecting: 1 of 2 matters", page)
        self.assertIn("Nothing here waits for you", page)
        self.assertNotIn("interview", page.lower())
        # two matters, but nothing of our own work yet: still collecting
        self.evidence("2026-0005", "asked | Another guarantee | x\n", "pcg-review", "Guarantee review")
        self.assertEqual(self.due("--today", "2026-11-02")[0], [])
        # the second matter with our work: the skill is due, with the line count the learner records
        self.evidence("2026-0002")
        due, _ = self.due("--today", "2026-11-02")
        self.assertEqual(len(due), 1, due)
        self.assertEqual(due[0], "due: skill nda-review | area commercial | first write: 2 matters, 4 lines | "
                                 "evidence_lines 4 | no skill yet")
        self.assertIn("to write at the next learning pass", self.page())

    def test_the_lawyers_word_is_enough_for_a_first_write(self):
        self.add("position | We never accept a term over three years | lawyer in chat 2026-11-02\n",
                 "--matter", "chat", "--work-type", "nda-review", "--work-type-name", "NDA review",
                 "--origin", "lawyer")
        due, _ = self.due()
        self.assertEqual(len(due), 1)
        self.assertIn("first write: 0 matters, 1 lines", due[0])

    def test_a_written_skill_is_rewritten_when_enough_is_new(self):
        self.evidence("2026-0001")
        self.evidence("2026-0002")
        self.skill()
        self.assertEqual(self.due("--today", "2026-11-04"), ([], []))
        page = self.page()
        self.assertIn("[working v1](../skills/commercial/nda-review/SKILL.md) | 2026-11-03 | - | up to date", page)
        self.assertIn("Nothing to write", page)
        # one new line: it can wait, until the skill is a week old
        self.evidence("2026-0003", "did | Sent our template | y\n")
        due, later = self.due("--today", "2026-11-04")
        self.assertEqual(due, [])
        self.assertEqual(later, ["later: skill nda-review | area commercial | 1 new lines since working v1 "
                                 "(2026-11-03) | evidence_lines 5 | skills/commercial/nda-review/SKILL.md"])
        due, later = self.due("--today", "2026-11-10")
        self.assertEqual(len(due), 1)
        self.assertIn("1 new lines since working v1 (2026-11-03)", due[0])
        # a line from the lawyer makes it due at once
        self.add("correction | Not our practice: Dutch law for NDAs | lawyer in chat 2026-11-04\n",
                 "--matter", "chat", "--work-type", "nda-review", "--origin", "lawyer")
        due, _ = self.due("--today", "2026-11-04")
        self.assertIn("2 new lines since working v1 (2026-11-03), 1 from the lawyer", due[0])
        self.assertIn("| evidence_lines 6 | skills/commercial/nda-review/SKILL.md", due[0])

    def test_eight_new_lines_are_due_at_once(self):
        self.evidence("2026-0001")
        self.evidence("2026-0002")
        self.skill()
        self.evidence("2026-0003", "".join("did | step %d | y\n" % i for i in range(8)))
        due, _ = self.due("--today", "2026-11-04")
        self.assertIn("8 new lines", due[0])

    def test_an_approved_skill_and_an_old_draft(self):
        self.evidence("2026-0001")
        self.evidence("2026-0002")
        p = self.skill(version="3", status="approved")
        self.due("--today", "2026-11-04")
        self.assertIn("[approved v3](../skills/commercial/nda-review/SKILL.md)", self.page())
        # a draft from before: counted as working, and every line is new to it
        p.write_text("---\nname: nda-review\nstatus: draft\nversion: 0\n---\n# NDA review\n", encoding="utf-8")
        due, _ = self.due("--today", "2026-11-04")
        self.assertIn("4 new lines since working v0", due[0])

    def test_expected_right(self):
        self.evidence("2026-0001", "did | x | y\ncompared | match: asked 2 of 2 expected | a.eml\n"
                                   "compared | Match: position as expected | b.eml\n")
        self.evidence("2026-0002", "did | x | y\ncompared | missed: legal asked for the value; I expected none | c.eml\n"
                                   "compared | match | d.eml\n")
        self.due()
        self.assertIn("| 75% of 4 |", self.page())

    def test_hand_edits_are_found_and_shown(self):
        self.evidence("2026-0001")
        self.evidence("2026-0002")
        p = self.skill()
        self.assertIn("no hand edits", self.index("--edits").stdout)
        r = self.index("--edits", "skills/commercial/nda-review/SKILL.md")
        self.assertIn("no copy of skills/commercial/nda-review/SKILL.md as the agent wrote it in history/", r.stdout)
        common.history_copy(p)                      # any other copy is not "as the agent wrote it"
        self.assertIn("no copy of", self.index("--edits", "skills/commercial/nda-review/SKILL.md").stdout)
        r = self.ws.run("learn-mark", "--wrote", "skills/commercial/nda-review/SKILL.md")   # what the hook keeps
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"skills/commercial/nda-review/history/SKILL\.\d{4}-\d\d-\d\d_\d{6}\.written\.md")
        self.assertIn("no hand edits", self.index("--edits", "skills/commercial/nda-review/SKILL.md").stdout)
        p.write_text(p.read_text(encoding="utf-8") + "- We never accept more than three years.\n", encoding="utf-8")
        self.assertIn("edited by hand: skills/commercial/nda-review/SKILL.md", self.index("--edits").stdout)
        r = self.index("--edits", "skills/commercial/nda-review/SKILL.md")
        self.assertIn("+- We never accept more than three years.", r.stdout)
        self.assertIn("as the agent last wrote it", r.stdout)
        due, _ = self.due("--today", "2026-11-04")
        self.assertIn("edited by hand since working v1", due[0])
        self.assertIn("you edited it", self.page())
        # a copy kept before a write (the hand-edited version) is not "as the agent last wrote it"
        (p.parent / "history" / "SKILL.2099-01-01_000000.before.md").write_text("other\n", encoding="utf-8")
        self.assertIn("+- We never accept more than three years.",
                      self.index("--edits", "skills/commercial/nda-review/SKILL.md").stdout)
        # a plain copy of the hand-edited version (someone ran history-copy) does not hide the edit
        common.history_copy(p)
        self.assertIn("edited by hand: skills/commercial/nda-review/SKILL.md", self.index("--edits").stdout)
        # line endings alone are not an edit; two versions in one second keep their order
        self.ws.run("learn-mark", "--wrote", "skills/commercial/nda-review/SKILL.md")
        self.ws.run("learn-mark", "--wrote", "skills/commercial/nda-review/SKILL.md")
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.assertIn("no hand edits", self.index("--edits").stdout)
        self.assertEqual(self.index("--edits", "nosuch.md").returncode, 2)

    def test_lists_from_an_earlier_version_no_longer_say_they_wait(self):
        base = self.ws.root / "learning"
        base.mkdir(parents=True, exist_ok=True)
        (base / "knowledge-candidates.md").write_text(
            common.FENCE + "\n# Facts about the company noted from the work. Written to knowledge/ only after "
            "the lawyer's yes.\n# id | date | type | fact | source | status\n"
            "# status: pending, confirmed (knowledge/<file>), rejected\n"
            "K-2026-0001-1 | 2026-11-02 | entity | Example Ltd is our UK company | x | pending\n"
            "K-2026-0001-2 | 2026-11-02 | entity | Example GmbH | y | confirmed (knowledge/entities/example-gmbh.md)\n",
            encoding="utf-8")
        (base / "questions.md").write_text(
            common.FENCE + "\n# Questions for the lawyer raised by the evidence.\n"
            "# id | date | about | question | evidence | status\n# status: open, answered (<date>)\n"
            "Q-2026-0001-1 | 2026-11-02 | nda-review | Why five years? | 2026-0001 | open\n"
            "Q-2026-0001-2 | 2026-11-02 | nda-review | Who signs? | 2026-0001 | answered (2026-11-03)\n",
            encoding="utf-8")
        r = self.index("--today", "2026-11-03")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 facts to write up; 1 open points", r.stdout)
        kc = (base / "knowledge-candidates.md").read_text(encoding="utf-8")
        qs = (base / "questions.md").read_text(encoding="utf-8")
        self.assertNotIn("only after the lawyer's yes", kc)
        self.assertIn("The learning pass writes them up", kc)
        self.assertIn("K-2026-0001-2 | 2026-11-02 | entity | Example GmbH | y | confirmed (knowledge/entities/example-gmbh.md)", kc)
        self.assertNotIn("Questions for the lawyer", qs)
        self.assertIn("Nobody is asked", qs)
        self.assertIn("Q-2026-0001-2 | 2026-11-02 | nda-review | Who signs? | 2026-0001 | answered (2026-11-03)", qs)
        before = (kc, qs)
        self.index()
        self.assertEqual(((base / "knowledge-candidates.md").read_text(encoding="utf-8"),
                          (base / "questions.md").read_text(encoding="utf-8")), before)

    def test_operational_skills_are_never_learned_files(self):
        self.evidence("2026-0001", slug="intake", name="Intake")
        self.evidence("2026-0002", slug="intake", name="Intake")
        due, _ = self.due()
        self.assertIn("no skill yet", due[0])


class KnowledgeTest(LearningBase):

    ENTRY = ("---\ntype: entity\nname: Kestrel Pumpen GmbH\naliases: Kestrel Germany\nstatus: working\nowner:\n"
             "source: 2026-0001 correspondence/a.eml\norigin: matter\nvalid_from: 2026-11-02\nseen_in: 2026-0001\n"
             "---\n" + common.FENCE + "\n\nOur German company; it signs supply contracts in Germany.\n\n"
             "## Key facts\n- Registered in Munich (2026-0001 documents/received/extract.pdf p1)\n"
             "- Two managing directors sign jointly (2026-0001 correspondence/a.eml)\n\n"
             "## You said\n- Finance holds the commercial register extracts (2026-11-03)\n")

    def put(self, rel, text):
        p = self.ws.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def entry(self, text=None, rel="knowledge/entities/kestrel-pumpen-gmbh.md"):
        return self.put(rel, text or self.ENTRY)

    def test_facts_are_due_by_number_or_age(self):
        self.add("entity | Example Ltd is our UK company | x\n", "--matter", "2026-0001", "--knowledge",
                 "--date", "2026-11-02")
        r = self.index("--today", "2026-11-03")
        self.assertIn("later: knowledge | 1 facts to write up, oldest 1 days", r.stdout)
        # a fact the lawyer stated is written up at the next pass, however new
        self.add("person_role | Finance owns the credit insurance answers | lawyer in chat 2026-11-03\n",
                 "--matter", "chat", "--knowledge", "--date", "2026-11-03")
        self.assertIn("due: knowledge | 2 facts to write up, oldest 1 days, 1 from the lawyer",
                      self.index("--today", "2026-11-03").stdout)
        self.assertEqual(self.ws.run("learn-mark", "K-chat-1", "--status", "written (knowledge/people/finance.md)").returncode, 0)
        self.assertIn("due: knowledge | 1 facts to write up, oldest 3 days", self.index("--today", "2026-11-05").stdout)
        self.add("".join("entity | Fact %d | x\n" % i for i in range(9)), "--matter", "2026-0002", "--knowledge",
                 "--date", "2026-11-03")
        self.assertIn("due: knowledge | 10 facts to write up", self.index("--today", "2026-11-03").stdout)
        page = (self.ws.root / "learning" / "index.md").read_text(encoding="utf-8")
        self.assertIn("Facts noted and not yet written up: 10 ([list](knowledge-candidates.md))", page)
        # written up: nothing waits
        ids = ",".join(["K-2026-0001-1"] + ["K-2026-0002-%d" % i for i in range(1, 10)])
        self.assertEqual(self.ws.run("learn-mark", ids, "--status", "written (knowledge/entities/x.md)").returncode, 0)
        self.assertNotIn("knowledge |", self.index("--today", "2026-11-10").stdout)

    def test_entries_are_counted_and_indexed_without_a_model(self):
        p = self.entry()
        self.entry(self.ENTRY.replace("status: working", "status: approved").replace("Kestrel Pumpen GmbH", "Kestrel Ltd"),
                   "knowledge/entities/kestrel-ltd.md")
        self.put("knowledge/policies/travel-policy.md", "# Travel policy\nA dropped original, no frontmatter.\n")
        self.put("knowledge/entities/history/kestrel-ltd.2026-11-01_100000.md", self.ENTRY)
        self.put("knowledge/TYPES.md", "---\ntype: not-an-entry\n---\n")
        r = self.index()
        self.assertIn("2 knowledge entries (1 working, 1 approved)", r.stdout)
        self.assertIn("knowledge/INDEX.md: 2 entries added or refreshed", r.stdout)
        idx = (self.ws.root / "knowledge" / "INDEX.md").read_text(encoding="utf-8")
        self.assertTrue(idx.startswith("# Knowledge index\n"))
        self.assertIn("## knowledge/entities/\n", idx)
        self.assertIn("### knowledge/entities/kestrel-pumpen-gmbh.md\n<!-- sha256: %s -->\n"
                      "- type: entity | status: working | owner: - | valid_from: 2026-11-02 | origin: matter\n"
                      "- summary: Our German company; it signs supply contracts in Germany.\n"
                      "- sections:\n  - Key facts (L" % common.sha256_file(p), idx)
        self.assertIn("  - You said (L", idx)
        self.assertNotIn("travel-policy", idx)
        self.assertNotIn("history/", idx)
        self.assertIn("Entries: 1 working, 1 approved", (self.ws.root / "learning" / "index.md").read_text())
        # nothing changed: nothing written
        self.assertNotIn("knowledge/INDEX.md:", self.index().stdout)

    def test_the_indexers_blocks_are_left_alone(self):
        self.put("knowledge/INDEX.md", "# Knowledge index\nBuilt by the indexer.\n"
                      "## house/\n### house/brief.md\n<!-- sha256: aaa -->\n- summary: the brief\n"
                      "## knowledge/entities/\n### knowledge/entities/group-chart.pdf\n<!-- sha256: bbb -->\n"
                      "- type: entity | owner: - | valid_from: - | origin: document\n- summary: the chart\n"
                      "### `knowledge/entities/kestrel-pumpen-gmbh.md` \n<!-- sha256: old -->\n- summary: stale\n"
                      "## seeds/\n### seeds/harvey/x.md\n<!-- sha256: ccc -->\n- summary: a seed\n"
                      "## Needs an owner or date\n- knowledge/entities/group-chart.pdf: no owner\n")
        self.entry()
        self.entry(self.ENTRY.replace("type: entity", "type: policy"), "knowledge/policies/gifts.md")
        self.assertIn("2 entries added or refreshed", self.index().stdout)
        idx = (self.ws.root / "knowledge" / "INDEX.md").read_text(encoding="utf-8")
        for kept in ("### house/brief.md\n<!-- sha256: aaa -->\n- summary: the brief\n",
                     "### knowledge/entities/group-chart.pdf\n<!-- sha256: bbb -->",
                     "### seeds/harvey/x.md\n<!-- sha256: ccc -->\n- summary: a seed\n",
                     "## Needs an owner or date\n- knowledge/entities/group-chart.pdf: no owner\n"):
            self.assertIn(kept, idx)
        self.assertNotIn("stale", idx)
        self.assertEqual(idx.count("### knowledge/entities/kestrel-pumpen-gmbh.md"), 1)
        # the new folder group sits before seeds/ and the closing list
        self.assertLess(idx.index("## knowledge/policies/"), idx.index("## seeds/"))
        self.assertLess(idx.index("## seeds/"), idx.index("## Needs an owner or date"))
        self.assertTrue(idx.rstrip().endswith("- knowledge/entities/group-chart.pdf: no owner"))

    def test_an_entry_edited_by_hand_is_due(self):
        p = self.entry()
        self.assertEqual(self.ws.run("learn-mark", "--wrote", "knowledge/entities/kestrel-pumpen-gmbh.md").returncode, 0)
        p.write_text(p.read_text(encoding="utf-8") + "- Registered number HRB 1234 (the lawyer)\n", encoding="utf-8")
        r = self.index()
        self.assertIn("due: knowledge | 1 entries edited by hand: knowledge/entities/kestrel-pumpen-gmbh.md", r.stdout)
        self.assertIn("edited by hand: knowledge/entities/kestrel-pumpen-gmbh.md", self.index("--edits").stdout)


if __name__ == "__main__":
    unittest.main()
