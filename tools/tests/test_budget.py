"""Tests for tools/budget-update (spec D10)."""

import datetime as dt
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsfixture import Workspace  # noqa: E402

KEY_BLOCK = """cap_usd: 100
month: 2026-10
estimated_spend_usd: 0.00
percent_of_cap: 0
mode: full
overhead_factor: 1.25
last_actual_usd:
last_actual_date:
thresholds: lean=70 minimal=90 paused=100
prices_usd_per_mtok: opus=4/20/0.20 sonnet=2/10/0.20 haiku=0.10/0.50/0.01 fable=10/50/0.25
"""

# sonnet at 2 USD per million input tokens, overhead 1.25: one input character costs 6.25e-7 USD
CHARS_PER_USD_SONNET_IN = 1600000


class BudgetTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(skills=False)
        self.budget = self.ws.root / "BUDGET.md"

    def tearDown(self):
        self.ws.cleanup()

    def bu(self, *args, today="2026-10-05"):
        return self.ws.run("budget-update", "--today", today, *args)

    def keys(self, path=None):
        text = (path or self.budget).read_text(encoding="utf-8")
        return dict(re.findall(r"^([a-z_]+): ?(.*)$", text.split("## Ledger")[0], re.M))

    def ledger(self, path=None):
        text = (path or self.budget).read_text(encoding="utf-8")
        lines = text.split("## Ledger")[1].strip().splitlines()
        self.assertEqual(lines[0], "run | date | model | in_chars | out_chars | est_usd | note")
        return [line.split(" | ") for line in lines[1:]]

    def spend(self, usd, run="R", today="2026-10-05"):
        r = self.bu("--run", run, "--model", "sonnet", "--in-chars", str(int(round(usd * CHARS_PER_USD_SONNET_IN))),
                    "--out-chars", "0", today=today)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    # ------------------------------------------------------------ init and format

    def test_init_writes_the_format(self):
        r = self.bu("--init")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = self.budget.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Budget\nKept by the agent. Once a month, type the actual bill: "
                                        "say \"budget actual 37.20\".\n"))
        self.assertIn("as of 2026-10-06", text, "the prices carry their date and a note to check them")
        self.assertIn("\n\n" + KEY_BLOCK + "\n## Ledger\nrun | date | model | in_chars | out_chars | est_usd | note\n",
                      text)
        again = self.bu("--init")
        self.assertIn("exists", again.stdout)
        self.assertEqual(self.budget.read_text(encoding="utf-8"), text)

    def test_init_with_month(self):
        self.bu("--init", "--month", "2026-12")
        self.assertEqual(self.keys()["month"], "2026-12")

    def test_run_creates_budget_when_absent(self):
        r = self.bu("--run", "R1", "--model", "haiku", "--in-chars", "4000", "--out-chars", "400")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("created BUDGET.md", r.stdout)
        self.assertEqual(len(self.ledger()), 1)

    # ------------------------------------------------------------ estimates

    def test_estimate_per_line(self):
        self.bu("--init")
        self.bu("--run", "2026-10-05_090000", "--model", "sonnet", "--in-chars", "400000", "--out-chars", "40000",
                "--note", "intake batch 1")
        self.bu("--run", "2026-10-05_090000", "--model", "opus", "--in-chars", "200000", "--out-chars", "20000")
        self.bu("--run", "2026-10-05_090000", "--model", "haiku", "--in-chars", "4000000", "--out-chars", "400000")
        rows = self.ledger()
        # (in/4 * price_in + out/4 * price_out) / 1e6 * 1.25
        self.assertEqual(rows[0], ["2026-10-05_090000", "2026-10-05", "sonnet", "400000", "40000", "0.3750",
                                   "intake batch 1"])
        self.assertEqual(rows[1][5], "0.3750")   # (50000*4 + 5000*20)/1e6*1.25
        self.assertEqual(rows[1][6], "-")
        self.assertEqual(rows[2][5], "0.1875")   # (1e6*0.10 + 1e5*0.50)/1e6*1.25
        k = self.keys()
        self.assertEqual((k["estimated_spend_usd"], k["percent_of_cap"], k["mode"]), ("0.94", "0", "full"))

    def test_prices_overhead_and_cap_come_from_the_file(self):
        self.bu("--init")
        text = self.budget.read_text(encoding="utf-8")
        text = text.replace("sonnet=2/10", "sonnet=3/15").replace("overhead_factor: 1.25", "overhead_factor: 2")
        text = text.replace("cap_usd: 100", "cap_usd: 10")
        self.budget.write_text(text, encoding="utf-8")
        self.bu("--run", "R1", "--model", "sonnet", "--in-chars", "4000000", "--out-chars", "0")
        self.assertEqual(self.ledger()[0][5], "6.0000")  # 1e6 tokens * 3 / 1e6 * 2
        k = self.keys()
        self.assertEqual((k["estimated_spend_usd"], k["percent_of_cap"], k["mode"]), ("6.00", "60", "full"))

    def test_note_with_separator_stays_one_field(self):
        self.bu("--run", "R1", "--model", "opus", "--in-chars", "4", "--out-chars", "4", "--note", "batch | 2")
        self.assertEqual(self.ledger()[0][6], "batch / 2")
        self.bu("--run", "R2", "--model", "opus", "--in-chars", "4", "--out-chars", "4")
        self.assertEqual(len(self.ledger()), 2)

    # ------------------------------------------------------------ modes

    def test_modes_at_70_90_100(self):
        self.bu("--init")
        self.spend(69.99)
        self.assertEqual(self.bu("--mode").stdout.strip(), "full")
        self.assertEqual(self.keys()["percent_of_cap"], "69")
        r = self.spend(0.01)
        self.assertIn("mode changed: full -> lean", r.stdout)
        self.assertEqual((self.keys()["percent_of_cap"], self.keys()["mode"]), ("70", "lean"))
        self.assertEqual(self.bu("--mode").stdout, "lean\n")
        self.spend(20)
        self.assertEqual(self.bu("--mode").stdout.strip(), "minimal")
        self.spend(9.99)
        self.assertEqual(self.bu("--mode").stdout.strip(), "minimal")
        self.spend(0.01)
        self.assertEqual(self.bu("--mode").stdout.strip(), "paused")
        self.assertEqual(self.keys()["estimated_spend_usd"], "100.00")

    def test_thresholds_come_from_the_file(self):
        self.bu("--init")
        text = self.budget.read_text(encoding="utf-8").replace("lean=70 minimal=90", "lean=50 minimal=60")
        self.budget.write_text(text, encoding="utf-8")
        self.spend(55)
        self.assertEqual(self.bu("--mode").stdout.strip(), "lean")

    def test_mode_without_budget_file(self):
        r = self.bu("--mode")
        self.assertEqual((r.returncode, r.stdout), (0, "full\n"))
        self.assertIn("BUDGET.md not found", r.stderr)
        self.assertFalse(self.budget.exists())

    # ------------------------------------------------------------ month rollover

    def test_month_rollover_moves_the_ledger(self):
        self.bu("--init")
        self.spend(80, run="2026-10-20_090000", today="2026-10-20")
        r = self.bu("--run", "2026-11-02_090000", "--model", "sonnet", "--in-chars", "1600000", "--out-chars", "0",
                    today="2026-11-02")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("the 2026-10 ledger moved to digests/budget-2026-10.md", r.stdout)
        archive = self.ws.root / "digests" / "budget-2026-10.md"
        self.assertTrue(archive.exists())
        self.assertEqual([row[0] for row in self.ledger(archive)], ["2026-10-20_090000"])
        self.assertEqual(self.keys(archive)["estimated_spend_usd"], "80.00")
        k = self.keys()
        self.assertEqual((k["month"], k["estimated_spend_usd"], k["mode"]), ("2026-11", "1.00", "full"))
        self.assertEqual([row[0] for row in self.ledger()], ["2026-11-02_090000"])

    def test_reads_treat_an_ended_month_as_reset(self):
        self.bu("--init")
        self.spend(95, today="2026-10-20")
        before = self.budget.read_text(encoding="utf-8")
        self.assertEqual(self.bu("--mode", today="2026-10-31").stdout.strip(), "minimal")
        self.assertEqual(self.bu("--mode", today="2026-11-01").stdout.strip(), "full")
        show = self.bu("--show", today="2026-11-01")
        self.assertIn("the month has changed", show.stdout)
        self.assertEqual(self.budget.read_text(encoding="utf-8"), before, "reads never write")

    def test_never_rolls_back_to_an_earlier_month(self):
        self.bu("--init", today="2026-11-02")
        self.spend(5, today="2026-11-02")
        before = self.budget.read_text(encoding="utf-8")
        r = self.bu("--run", "R0", "--model", "opus", "--in-chars", "4", "--out-chars", "4", today="2026-10-31")
        self.assertEqual(r.returncode, 1)
        self.assertIn("before the month in BUDGET.md", r.stderr)
        self.assertEqual(self.budget.read_text(encoding="utf-8"), before)
        self.assertFalse((self.ws.root / "digests" / "budget-2026-11.md").exists())

    def test_unreadable_month_keeps_the_ledger(self):
        self.bu("--init")
        self.spend(7, run="R-oct", today="2026-10-20")
        text = self.budget.read_text(encoding="utf-8").replace("month: 2026-10", "month: October")
        self.budget.write_text(text, encoding="utf-8")
        r = self.spend(1, run="R-nov", today="2026-11-02")
        self.assertIn("read as 2026-10", r.stderr)
        archive = self.ws.root / "digests" / "budget-2026-10.md"
        self.assertEqual([row[0] for row in self.ledger(archive)], ["R-oct"])
        self.assertEqual([row[0] for row in self.ledger()], ["R-nov"])
        text = self.budget.read_text(encoding="utf-8").replace("month: 2026-11", "month: ?")
        self.budget.write_text(text, encoding="utf-8")
        self.spend(1, run="R-nov2", today="2026-11-03")
        self.assertEqual([row[0] for row in self.ledger()], ["R-nov", "R-nov2"], "this month's lines stay")
        self.assertEqual(self.keys()["month"], "2026-11")

    # ------------------------------------------------------------ actual bill

    def test_actual_recalibrates_this_month(self):
        self.bu("--init")
        self.spend(20)
        r = self.bu("--actual", "30", "--date", "2026-10-25")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("overhead factor 1.25 -> 1.88", r.stdout)
        k = self.keys()
        self.assertEqual((k["overhead_factor"], k["last_actual_usd"], k["last_actual_date"]),
                         ("1.88", "30.00", "2026-10-25"))
        self.bu("--run", "R2", "--model", "sonnet", "--in-chars", "4000000", "--out-chars", "0")
        self.assertEqual(self.ledger()[-1][5], "3.7600", "new lines use the new factor")

    def test_actual_is_clamped(self):
        self.bu("--init")
        self.spend(10)
        r = self.bu("--actual", "100")
        self.assertIn("limited to the range 1.0 to 5.0", r.stdout)
        self.assertEqual(self.keys()["overhead_factor"], "5.00")
        self.bu("--actual", "1")
        self.assertEqual(self.keys()["overhead_factor"], "1.00")

    def test_actual_for_last_month_after_rollover(self):
        self.bu("--init")
        self.spend(40, today="2026-10-20")
        self.spend(1, today="2026-11-01")
        r = self.bu("--actual", "60", today="2026-11-03")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("actual USD 60.00 for 2026-10 against estimated USD 40.00", r.stdout)
        self.assertEqual(self.keys()["overhead_factor"], "1.88")
        archive = self.ws.root / "digests" / "budget-2026-10.md"
        self.assertEqual((self.keys(archive)["actual_usd"], self.keys(archive)["actual_date"]),
                         ("60.00", "2026-11-03"))
        r = self.bu("--actual", "2", today="2026-11-04")
        self.assertIn("for 2026-11", r.stdout, "last month's bill is recorded, so this is spend to date")

    def test_actual_before_rollover_closes_the_month(self):
        self.bu("--init")
        self.spend(40, today="2026-10-20")
        r = self.bu("--actual", "50", today="2026-11-02")
        self.assertIn("for 2026-10 against estimated USD 40.00", r.stdout)
        archive = self.ws.root / "digests" / "budget-2026-10.md"
        self.assertEqual(self.keys(archive)["actual_usd"], "50.00")
        self.assertEqual(self.keys(archive)["overhead_factor"], "1.25", "the factor October was estimated with")
        self.assertEqual(self.keys()["overhead_factor"], "1.56")
        self.assertEqual((self.keys()["month"], self.keys()["estimated_spend_usd"]), ("2026-11", "0.00"))

    def test_actual_without_estimate_keeps_the_factor(self):
        self.bu("--init")
        r = self.bu("--actual", "12")
        self.assertIn("overhead factor stays 1.25", r.stdout)
        self.assertEqual(self.keys()["last_actual_usd"], "12.00")

    # ------------------------------------------------------------ show and usage

    def test_show(self):
        self.bu("--init")
        self.spend(12.5, run="2026-10-05_090000")
        r = self.bu("--show")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Budget 2026-10: USD 12.50 estimated of a USD 100 cap (12%). Mode: full.", r.stdout)
        self.assertIn("Ledger, 1 line this month:", r.stdout)
        self.assertIn("2026-10-05_090000 | 2026-10-05 | sonnet |", r.stdout)

    def test_human_lines_in_the_header_survive(self):
        self.bu("--init")
        text = self.budget.read_text(encoding="utf-8").replace("cap_usd: 100", "cap_usd: 100\nNote from Alex: keep it lean.")
        self.budget.write_text(text, encoding="utf-8")
        self.spend(1)
        self.assertIn("Note from Alex: keep it lean.", self.budget.read_text(encoding="utf-8"))

    def test_usage_errors(self):
        self.assertEqual(self.bu().returncode, 2)
        self.assertEqual(self.bu("--show", "--mode").returncode, 2)
        self.assertEqual(self.bu("--run", "R", "--model", "nosuchmodel", "--in-chars", "1", "--out-chars", "1").returncode, 2)
        self.assertEqual(self.bu("--run", "R", "--model", "opus").returncode, 2)
        self.assertEqual(self.bu("--run", "R", "--model", "opus", "--in-chars", "-1", "--out-chars", "1").returncode, 2)
        self.assertEqual(self.bu("--init", "--month", "2026-13").returncode, 2)
        self.assertEqual(self.bu("--mode", "--date", "2026-10-01").returncode, 2)
        self.assertEqual(self.bu("--show", "--model", "opus").returncode, 2)
        self.assertEqual(self.bu("--actual", "lots").returncode, 2)
        self.assertEqual(self.bu("--actual", "5").returncode, 2, "no BUDGET.md yet")
        self.assertEqual(self.bu("--show").returncode, 1, "no BUDGET.md yet")


if __name__ == "__main__":
    unittest.main()


class MeasureTest(unittest.TestCase):
    """budget-update --measure: the real token use from Claude Code's logs, priced exactly."""

    def setUp(self):
        self.ws = Workspace(skills=False)
        self.budget = self.ws.root / "BUDGET.md"
        self.config = self.ws.root.parent / "claude-config"
        slug = "".join(ch if ch.isalnum() else "-" for ch in str(self.ws.root.resolve()))
        self.logs = self.config / "projects" / slug
        (self.logs / "sess-1" / "subagents").mkdir(parents=True)
        self.now = dt.datetime.now(dt.timezone.utc)

    def tearDown(self):
        self.ws.cleanup()

    def entry(self, mid, model, minutes_ago, usage, speed="standard", when=None):
        t = (when or (self.now - dt.timedelta(minutes=minutes_ago))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        u = dict(usage, speed=speed)
        return json.dumps({"type": "assistant", "timestamp": t, "requestId": "req_" + mid,
                           "message": {"id": mid, "model": model, "usage": u}})

    def write(self, rel, lines):
        p = self.logs / rel
        with open(str(p), "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def bu(self, *args):
        env = dict(self.ws.env(), CLAUDE_CONFIG_DIR=str(self.config))
        return self.ws.run("budget-update", "--today", self.now.strftime("%Y-%m-%d"), *args, env=env)

    def ledger(self):
        text = self.budget.read_text(encoding="utf-8")
        return [line.split(" | ") for line in text.split("## Ledger")[1].strip().splitlines()[1:]]

    def test_measures_every_model_and_subagent_once_and_prices_the_cache(self):
        sonnet = {"input_tokens": 1000, "cache_creation_input_tokens": 10000, "cache_read_input_tokens": 100000,
                  "output_tokens": 2000, "cache_creation": {"ephemeral_1h_input_tokens": 10000,
                                                            "ephemeral_5m_input_tokens": 0}}
        opus = {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 1000000,
                "output_tokens": 10000}
        self.write("sess-1.jsonl", [self.entry("m1", "claude-sonnet-5-5", 5, sonnet),
                                    self.entry("m1", "claude-sonnet-5-5", 5, sonnet),     # same response twice
                                    "not json", json.dumps({"type": "user", "message": {"content": "x"}})])
        self.write("sess-1/subagents/agent-a.jsonl", [self.entry("m2", "claude-opus-5-5", 3, opus)])
        r = self.bu("--measure", "--run", "R1", "--note", "intake")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = {f[2]: f for f in self.ledger()}
        # sonnet: 1000*2 + 10000*2*2 (1-hour write) + 100000*0.20 + 2000*10 = 82,000 micro-USD
        self.assertAlmostEqual(float(rows["sonnet"][5]), 0.082, places=6)
        # opus: 1,000,000 cache reads at 0.20 + 10,000 out at 20 = 0.40
        self.assertAlmostEqual(float(rows["opus"][5]), 0.40, places=6)
        self.assertTrue(rows["sonnet"][6].startswith("measured: 1 requests"))
        self.assertIn("intake", rows["sonnet"][6])
        self.assertIn("estimated_spend_usd: 0.48", self.budget.read_text(encoding="utf-8"))
        self.assertIn("measured_until: ", self.budget.read_text(encoding="utf-8"))
        # a second measurement counts only what came after the first
        self.write("sess-1.jsonl", [self.entry("m3", "claude-sonnet-5-5", 0, {"input_tokens": 0, "output_tokens": 1000},
                                               speed="fast", when=dt.datetime.now(dt.timezone.utc))])
        r = self.bu("--measure", "--run", "R2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        last = self.ledger()[-1]
        self.assertEqual((last[0], last[2]), ("R2", "sonnet"))
        self.assertAlmostEqual(float(last[5]), 1000 * 10 * 2 / 1e6, places=6)     # fast mode: twice the price
        self.assertIn("fast mode on 1", last[6])

    def test_cost_is_split_by_step(self):
        """Each subagent's log sits beside a meta file naming its type: the split shows which step spent what."""
        use = {"input_tokens": 0, "output_tokens": 100000}
        self.write("sess-1.jsonl", [self.entry("m1", "claude-opus-5-5", 4, use)])
        for n in (1, 2):
            self.write("sess-1/subagents/agent-r%d.jsonl" % n, [self.entry("r%d" % n, "claude-sonnet-5-5", 3, use)])
            (self.logs / "sess-1" / "subagents" / ("agent-r%d.meta.json" % n)).write_text('{"agentType": "reader"}')
        r = self.bu("--measure", "--run", "R1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("main session: opus USD 2.00", r.stdout)
        self.assertIn("reader x2: sonnet USD 2.00", r.stdout)
        rows = {f[2]: f for f in self.ledger()}
        self.assertIn("by step: reader 100%", rows["sonnet"][6])
        self.assertIn("by step: main session 100%", rows["opus"][6])

    def test_first_measurement_replaces_this_months_estimates(self):
        r = self.ws.run("budget-update", "--today", self.now.strftime("%Y-%m-%d"), "--run", "R0", "--model", "sonnet",
                        "--in-chars", "400000", "--out-chars", "0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.write("sess-1.jsonl", [self.entry("m1", "claude-haiku-5-5", 2, {"input_tokens": 1000000,
                                                                             "output_tokens": 0})])
        r = self.bu("--measure")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1 estimated ledger lines replaced", r.stdout)
        rows = self.ledger()
        self.assertEqual(rows[0][5], "0")
        self.assertIn("estimate replaced by measured", rows[0][6])
        self.assertAlmostEqual(float(rows[1][5]), 0.10, places=6)
        self.assertIn("estimated_spend_usd: 0.10", self.budget.read_text(encoding="utf-8"))
        # the bill then leaves the overhead factor alone: nothing is estimated any more
        r = self.ws.run("budget-update", "--today", self.now.strftime("%Y-%m-%d"), "--actual", "0.12")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("overhead_factor: 1.25", self.budget.read_text(encoding="utf-8"))

    def test_no_logs_says_so(self):
        env = dict(self.ws.env(), CLAUDE_CONFIG_DIR=str(self.ws.root.parent / "nowhere"))
        r = self.ws.run("budget-update", "--measure", env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no Claude Code logs found", r.stderr)
        self.assertFalse(self.budget.exists())

    def test_measure_takes_no_estimate_flags(self):
        self.assertEqual(self.bu("--measure", "--model", "sonnet").returncode, 2)
