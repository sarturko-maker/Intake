"""Tests for tools/learn-add and tools/learn-index (the learning register)."""

import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lib"))
from test_new_matter import WorkspaceTest  # noqa: E402
import common  # noqa: E402


class LearningTest(WorkspaceTest):
    def add(self, stdin, *args):
        import os
        e = dict(os.environ)
        e["INTAKE_ROOT"] = str(self.ws.root)
        return subprocess.run(["bash", "tools/learn-add"] + list(args), input=stdin, capture_output=True,
                              text=True, env=e, cwd=str(self.ws.root))

    def index(self):
        return self.ws.run("learn-index")

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

    def test_knowledge_and_questions(self):
        self.assertEqual(self.add("entity | Example ME FZE is a UAE free zone company | 2026-0001 email\n",
                                  "--matter", "2026-0001", "--knowledge").returncode, 0)
        self.assertEqual(self.add("nda-review | Why was the cap raised for one customer only? | 2026-0003\n",
                                  "--matter", "2026-0003", "--question").returncode, 0)
        kc = (self.ws.root / "learning" / "knowledge-candidates.md").read_text()
        self.assertIn("K-2026-0001-1 |", kc)
        self.assertIn("| pending", kc)
        self.assertIn("Q-2026-0003-1 |", (self.ws.root / "learning" / "questions.md").read_text())

    def test_index_readiness_and_next_steps(self):
        for ref in ("2026-0001", "2026-0002", "2026-0003"):
            self.add("asked | NDA review requested | x\nposition | No non-compete | y\n",
                     "--matter", ref, "--work-type", "nda-review", "--work-type-name", "NDA review")
        self.add("asked | Guarantee review | x\n", "--matter", "2026-0004", "--work-type", "pcg-review")
        self.add("entity | A fact | z\n", "--matter", "2026-0001", "--knowledge")
        r = self.index()
        self.assertEqual(r.returncode, 0, r.stderr)
        page = (self.ws.root / "learning" / "index.md").read_text()
        self.assertIn("| [NDA review](work-types/nda-review.md) | 3 |", page)
        self.assertIn("ready for an interview", page)
        self.assertIn("collecting evidence (1 of 3 matters)", page)
        self.assertIn("Confirm the facts noted about the company: 1 waiting", r.stdout)
        self.assertIn("interview me about NDA review", r.stdout)
        # after an interview, the work type is ready to draft; after a draft skill, it waits for approval
        iv = self.ws.root / "seeds" / "interviews"
        iv.mkdir(parents=True, exist_ok=True)
        (iv / "2026-11-03_nda-review.notes.md").write_text("S01 | position | x | yes | yes |\n")
        self.assertIn("draft a skill for NDA review", self.index().stdout)
        sk = self.ws.root / "skills" / "commercial" / "nda-review"
        sk.mkdir(parents=True, exist_ok=True)
        (sk / "SKILL.md").write_text("---\nname: nda-review\nstatus: draft\n---\n# NDA review\n")
        self.assertIn("approve the draft NDA review skill", self.index().stdout.replace("Read and a", "a"))


if __name__ == "__main__":
    unittest.main()
