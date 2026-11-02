"""Tests for tools/index-rebuild (spec D11)."""

import contextlib
import csv
import io
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsfixture import ROOT, Workspace, common, read_index, write_index_rows  # noqa: E402

TODAY = "2026-11-01"
NOISE1 = "2026-10-12_0730_in_brightlaw_autumn-employment-law-update.eml"
NOISE2 = "2026-10-13_1200_in_kestrel-eng_invitation-supplier-day-2026.eml"
NOTE = "2026-10-21_1605_in_jschmidt_quick-question.eml"


def build_demo(ws):
    """Six matters, two noise rows and one please-check note, as after a few demo runs."""
    m = {}
    m["A"] = ws.make_matter("2026-0001", "commercial", "acme-automotive", "nda", sub_area="customers",
                            title="Acme NDA", status="waiting_lawyer", proposed_outcome="ready_for_lawyer",
                            opened="2026-10-12", last_activity="2026-10-14", waiting_on="you",
                            next_step="Approve the NDA", arrived="2026-10-12 09:12", ready_at="2026-10-12 11:42",
                            requester="Tom Hale", counterparty="Acme Automotive")
    m["B"] = ws.make_matter("2026-0002", "commercial", "acme-automotive", "msa-liability-cap", sub_area="customers",
                            title="Acme MSA: liability cap", status="waiting_counterparty",
                            proposed_outcome="in_progress", opened="2026-10-15", last_activity="2026-10-27",
                            waiting_on="counterparty", next_step="Wait for the reply on the cap", due="2026-11-03",
                            follows="2026-0001", arrived="2026-10-15 08:47", ready_at="2026-10-15 12:47")
    m["C"] = ws.make_matter("2026-0003", "trade-compliance", "px-400", "dual-use-egypt", sub_area="exports",
                            title="PX-400 pumps to Egypt", status="closed", closed="2026-10-16",
                            proposed_outcome="ready_for_lawyer", confirmed_outcome="ready_for_lawyer",
                            confirmed_by="you", lawyer_minutes="15", accepted_unchanged="yes",
                            opened="2026-10-13", last_activity="2026-10-15",
                            arrived="2026-10-13 14:20", ready_at="2026-10-13 16:20")
    m["D"] = ws.make_matter("2026-0004", "general", "unfiled", "invoice-dispute",
                            title="Northgate invoice short payment", status="open", proposed_outcome="out_of_area",
                            opened="2026-10-16", last_activity="2026-10-16", waiting_on="nobody",
                            next_step="Route to accounts payable")
    m["E"] = ws.make_matter("2026-0005", "corporate", "signing-authority", "poa-germany",
                            title="Vollmacht für die GmbH: wer zeichnet", status="waiting_lawyer",
                            proposed_outcome="needs_info_from_requester", opened="2026-10-28",
                            last_activity="2026-10-29", waiting_on="you",
                            next_step="Confirm the notarisation route", due="2026-11-05")
    m["F"] = ws.make_matter("2026-0006", "commercial", "acme-automotive", "signed-nda", sub_area="customers",
                            title="Signed Acme NDA received", status="open", proposed_outcome="nothing_needed",
                            opened="2026-10-14", last_activity="2026-10-14", waiting_on="nobody",
                            next_step="Confirm nothing needed and close")
    ws.add_noise("NOISE-0001", NOISE1, "2026-10-12 07:30", "Autumn employment law update", "newsletter",
                 sender="news@brightlaw.co.uk")
    ws.add_noise("NOISE-0002", NOISE2, "2026-10-13 12:00", "Invitation: Supplier day 2026", "calendar",
                 sender="events@kestrel-eng.co.uk")
    ws.add_note(NOTE, "No tag, and two open Acme matters could fit.", candidates="2026-0002, 2026-0006")
    return m


class IndexRebuildTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.m = build_demo(self.ws)

    def tearDown(self):
        self.ws.cleanup()

    def rebuild(self, *args):
        return self.ws.run("index-rebuild", "--today", TODAY, "--run", "TEST", *args)

    def rows(self):
        return {r["reference"]: r for r in read_index(self.ws)}

    def edit(self, changes, encoding="utf-8", delimiter=",", drop=(), add=()):
        """Edit INDEX.csv as the lawyer would in Excel: changes = {ref: {column: value}}."""
        rows = [r for r in read_index(self.ws) if r["reference"] not in drop]
        for r in rows:
            r.update(changes.get(r["reference"], {}))
        rows += list(add)
        if encoding == "utf-8" and delimiter == ",":
            write_index_rows(self.ws, rows)
            return
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=common.INDEX_COLUMNS, delimiter=delimiter, lineterminator="\r\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        (self.ws.root / "INDEX.csv").write_bytes(buf.getvalue().encode(encoding))

    def journal(self):
        p = self.ws.root / "JOURNAL.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    # ------------------------------------------------------------ writes

    def test_first_run_writes_csv_generated_copy_and_md(self):
        r = self.rebuild()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("index: 5 open and 1 closed matters, 2 noise rows (2 awaiting confirmation)", r.stdout)
        data = (self.ws.root / "INDEX.csv").read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM for Excel")
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""), "CRLF line endings only")
        header = data[3:].split(b"\r\n")[0].decode("utf-8")
        self.assertEqual(header.split(","), common.INDEX_COLUMNS)
        self.assertEqual((self.ws.root / "changes" / "INDEX.generated.csv").read_bytes(), data)
        md = self.ws.read("INDEX.md")
        heads = [h for h in ("## Open matters", "## Noise awaiting confirmation", "## Closed in the last 30 days",
                             "## Measures")]
        self.assertEqual([md.index(h) for h in heads], sorted(md.index(h) for h in heads))
        self.assertIn("Vollmacht für die GmbH: wer zeichnet", data.decode("utf-8"))

    def test_rows_and_computed_columns(self):
        self.rebuild()
        rows = self.rows()
        a = rows["2026-0001"]
        self.assertEqual(a["kind"], "matter")
        self.assertEqual(a["days_open"], "20")
        self.assertEqual(a["hours_to_ready"], "2.5")
        self.assertEqual(a["folder"], "areas/commercial/customers/acme-automotive/2026-0001_acme-automotive_nda")
        self.assertEqual((a["area"], a["sub_area"], a["subject"]), ("commercial", "customers", "acme-automotive"))
        self.assertEqual(rows["2026-0002"]["hours_to_ready"], "4")
        self.assertEqual(rows["2026-0002"]["follows"], "2026-0001")
        self.assertEqual(rows["2026-0003"]["days_open"], "3", "closed date minus opened")
        self.assertEqual(rows["2026-0004"]["hours_to_ready"], "", "no arrived/ready_at")
        n = rows["NOISE-0001"]
        self.assertEqual((n["kind"], n["status"], n["proposed_outcome"]), ("noise", "waiting_lawyer", "nothing_needed"))
        self.assertEqual((n["opened"], n["last_activity"], n["days_open"]), ("2026-10-12", "2026-10-12", "20"))
        self.assertEqual((n["waiting_on"], n["next_step"]), ("you", "Confirm as nothing needed"))
        self.assertEqual((n["title"], n["label"]), ("Autumn employment law update", "newsletter"))
        self.assertEqual(n["folder"], "inbox/noise/" + NOISE1)

    def test_sort_order(self):
        self.rebuild()
        refs = [r["reference"] for r in read_index(self.ws)]
        self.assertEqual(refs, ["2026-0002", "2026-0005",              # due ascending
                                "2026-0001", "2026-0006", "2026-0004",  # no due: days_open descending
                                "2026-0003",                            # closed by last_activity
                                "NOISE-0001", "NOISE-0002"])            # noise, open first

    def test_index_md_groups_open_matters_by_area_oldest_first(self):
        self.rebuild()
        md = self.ws.read("INDEX.md")
        open_part = md.split("## Open matters")[1].split("## Noise awaiting confirmation")[0]
        self.assertLess(open_part.index("### Commercial"), open_part.index("### Corporate"))
        self.assertLess(open_part.index("### Corporate"), open_part.index("### General"))
        commercial = open_part.split("### Commercial")[1].split("###")[0]
        order = [commercial.index(x) for x in ("2026-0001", "2026-0006", "2026-0002")]
        self.assertEqual(order, sorted(order))
        self.assertIn("confirm nothing needed: NOISE-0001, NOISE-0002", md)
        closed_part = md.split("## Closed in the last 30 days")[1].split("## Measures")[0]
        self.assertIn("2026-0003", closed_part)

    # ------------------------------------------------------------ human edits

    def test_csv_round_trip_of_human_columns(self):
        self.rebuild()
        self.edit({"2026-0002": {"confirmed_outcome": "Ready for lawyer", "confirmed_by": "you",
                                 "lawyer_minutes": "25", "accepted_unchanged": "N"}})
        r = self.rebuild()
        self.assertEqual(r.returncode, 0, r.stdout)
        meta = self.ws.meta(self.m["B"])
        self.assertEqual((meta["confirmed_outcome"], meta["confirmed_by"], meta["lawyer_minutes"],
                          meta["accepted_unchanged"]), ("ready_for_lawyer", "you", "25", "no"))
        hist = list((self.m["B"] / "history").glob("matter.*.md"))
        self.assertEqual(len(hist), 1, "one history copy before the frontmatter change")
        row = self.rows()["2026-0002"]
        self.assertEqual((row["confirmed_outcome"], row["lawyer_minutes"], row["accepted_unchanged"]),
                         ("ready_for_lawyer", "25", "no"))
        self.assertEqual(self.journal().count("human-edit-applied | 2026-0002"), 4)
        self.assertIn("lawyer columns updated in INDEX.csv", (self.m["B"] / "log.md").read_text())
        again = self.rebuild()
        self.assertNotIn("applied:", again.stdout, "nothing to apply on an unedited index")
        self.assertEqual(len(list((self.m["B"] / "history").glob("matter.*.md"))), 1)
        self.edit({"2026-0002": {"lawyer_minutes": ""}})
        self.rebuild()
        self.assertEqual(self.ws.meta(self.m["B"])["lawyer_minutes"], "", "a cleared cell clears the value")

    def test_value_already_in_matter_md_is_not_applied_again(self):
        self.rebuild()
        common.update_frontmatter_file(self.m["B"] / "matter.md", {"lawyer_minutes": "25"}, history=False)
        self.edit({"2026-0002": {"lawyer_minutes": "25", "confirmed_by": "you"}})
        r = self.rebuild()
        applied = [x for x in r.stdout.splitlines() if x.startswith("applied:")]
        self.assertEqual(applied, ["applied: 2026-0002 confirmed_by = you (%s/matter.md)" % self.ws.rel(self.m["B"])])
        self.assertNotIn("2026-0002 lawyer_minutes", self.journal())

    def test_closed_typed_in_csv(self):
        self.rebuild()
        self.edit({"2026-0001": {"status": "Closed"}})
        r = self.rebuild()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("closed-by-lawyer 2026-0001: run the wrap-up", r.stdout)
        meta = self.ws.meta(self.m["A"])
        self.assertEqual((meta["status"], meta["closed"]), ("closed", TODAY))
        self.assertIn("wrap-up-pending", [f.strip() for f in meta["flags"].split(",")])
        self.assertIn("| closed-by-lawyer | 2026-0001 |", self.journal())
        self.assertIn("closed by the lawyer in INDEX.csv", (self.m["A"] / "log.md").read_text())
        row = self.rows()["2026-0001"]
        self.assertEqual((row["status"], row["days_open"]), ("closed", "20"))
        closed_part = self.ws.read("INDEX.md").split("## Closed in the last 30 days")[1]
        self.assertIn("2026-0001", closed_part)
        again = self.rebuild()
        self.assertNotIn("closed-by-lawyer", again.stdout, "reported once")

    def test_closing_keeps_other_flags(self):
        common.update_frontmatter_file(self.m["A"] / "matter.md", {"flags": "personal-address"}, history=False)
        self.rebuild()
        self.edit({"2026-0001": {"status": "closed"}})
        self.rebuild()
        self.assertEqual(self.ws.meta(self.m["A"])["flags"], "personal-address, wrap-up-pending")

    def test_title_edit_sets_title_locked(self):
        self.rebuild()
        self.edit({"2026-0002": {"title": "Acme MSA: data breach cap still open"}})
        r = self.rebuild()
        self.assertIn("applied: 2026-0002 title = Acme MSA: data breach cap still open (title locked)", r.stdout)
        meta = self.ws.meta(self.m["B"])
        self.assertEqual((meta["title"], meta["title_locked"]), ("Acme MSA: data breach cap still open", "yes"))
        self.assertEqual(self.rows()["2026-0002"]["title"], "Acme MSA: data breach cap still open")

    def test_noise_confirmed_by_typing_closed(self):
        self.rebuild()
        self.edit({"NOISE-0001": {"status": "closed"}})
        r = self.rebuild()
        self.assertEqual(r.returncode, 0, r.stdout)
        moved = self.ws.root / "inbox" / "noise" / "confirmed" / NOISE1
        self.assertTrue(moved.exists())
        self.assertFalse((self.ws.root / "inbox" / "noise" / NOISE1).exists())
        self.assertIn("noise confirmed: NOISE-0001 -> inbox/noise/confirmed/" + NOISE1, r.stdout)
        raw = (self.ws.root / "inbox" / "noise" / "NOISE.csv").read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "NOISE.csv keeps its BOM")
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""), "NOISE.csv keeps CRLF")
        noise = {r["id"]: r for r in common.read_csv(self.ws.root / "inbox" / "noise" / "NOISE.csv")}
        n1 = noise["NOISE-0001"]
        self.assertEqual((n1["status"], n1["confirmed_outcome"], n1["confirmed_by"], n1["file"]),
                         ("closed", "nothing_needed", "you", "inbox/noise/confirmed/" + NOISE1))
        self.assertEqual(noise["NOISE-0002"]["status"], "waiting_lawyer")
        row = self.rows()["NOISE-0001"]
        self.assertEqual((row["status"], row["folder"], row["waiting_on"], row["next_step"]),
                         ("closed", "inbox/noise/confirmed/" + NOISE1, "", ""))
        self.assertIn("human-edit-applied | NOISE-0001", self.journal())

    def test_noise_confirmed_by_typing_an_outcome(self):
        self.rebuild()
        self.edit({"NOISE-0002": {"confirmed_outcome": "nothing needed", "confirmed_by": "Alex"}})
        self.rebuild()
        noise = {r["id"]: r for r in common.read_csv(self.ws.root / "inbox" / "noise" / "NOISE.csv")}
        self.assertEqual((noise["NOISE-0002"]["status"], noise["NOISE-0002"]["confirmed_outcome"],
                          noise["NOISE-0002"]["confirmed_by"]), ("closed", "nothing_needed", "Alex"))
        self.assertTrue((self.ws.root / "inbox" / "noise" / "confirmed" / NOISE2).exists())

    def test_noise_with_bare_file_name(self):
        self.ws.add_noise("NOISE-0003", "2026-10-22_0800_in_flowtechseals_catalogue.eml", "2026-10-22 08:00",
                          "New 2027 catalogue", "marketing", path_in_file=False)
        self.rebuild()
        self.assertEqual(self.rows()["NOISE-0003"]["folder"],
                         "inbox/noise/2026-10-22_0800_in_flowtechseals_catalogue.eml")
        self.edit({"NOISE-0003": {"status": "closed"}})
        self.rebuild()
        noise = {r["id"]: r for r in common.read_csv(self.ws.root / "inbox" / "noise" / "NOISE.csv")}
        self.assertEqual(noise["NOISE-0003"]["file"], "2026-10-22_0800_in_flowtechseals_catalogue.eml")
        self.assertEqual(self.rows()["NOISE-0003"]["folder"],
                         "inbox/noise/confirmed/2026-10-22_0800_in_flowtechseals_catalogue.eml")

    def test_confirm_noise_from_chat_line(self):
        r = self.rebuild("--confirm-noise", "confirm nothing needed: NOISE-0001, NOISE-0002, NOISE-0042")
        self.assertEqual(r.returncode, 0, r.stdout)
        for name in (NOISE1, NOISE2):
            self.assertTrue((self.ws.root / "inbox" / "noise" / "confirmed" / name).exists())
        self.assertIn("NOISE-0042: not in inbox/noise/NOISE.csv", r.stdout)
        self.assertIn("confirmed nothing needed (chat)", self.journal())
        self.assertIn("index: 5 open and 1 closed matters, 2 noise rows (0 awaiting confirmation)", r.stdout)

    def test_agent_owned_edits_are_ignored_with_a_warning(self):
        self.rebuild()
        before = (self.m["B"] / "matter.md").read_text()
        self.edit({"2026-0002": {"next_step": "Chase Acme today", "status": "open"},
                   "NOISE-0002": {"label": "event"}})
        r = self.rebuild()
        self.assertEqual(r.returncode, 0)
        self.assertIn("warning: 2026-0002: column next_step is kept by the agent; say it in chat instead", r.stdout)
        self.assertIn("warning: 2026-0002: column status is kept by the agent; say it in chat instead", r.stdout)
        self.assertIn("warning: NOISE-0002: column label is kept by the agent; say it in chat instead", r.stdout)
        self.assertEqual((self.m["B"] / "matter.md").read_text(), before)
        self.assertEqual(self.rows()["2026-0002"]["next_step"], "Wait for the reply on the cap")

    def test_excel_reformatting_is_not_an_edit(self):
        """Excel in a German locale: ';' delimiter, cp1252, dates and decimals reformatted."""
        self.rebuild()
        self.edit({"2026-0001": {"opened": "12/10/2026", "hours_to_ready": "2,5", "days_open": "20.0",
                                 "lawyer_minutes": "12"},
                   "2026-0002": {"due": "03.11.2026"}},
                  encoding="cp1252", delimiter=";")
        r = self.rebuild()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("warning:", r.stdout)
        applied = [x for x in r.stdout.splitlines() if x.startswith("applied:")]
        self.assertEqual(applied, ["applied: 2026-0001 lawyer_minutes = 12 (%s/matter.md)" % self.ws.rel(self.m["A"])])
        self.assertEqual(self.ws.meta(self.m["E"])["title"], "Vollmacht für die GmbH: wer zeichnet")

    def test_rows_added_or_deleted_in_csv_are_ignored(self):
        self.rebuild()
        extra = dict.fromkeys(common.INDEX_COLUMNS, "")
        extra.update({"reference": "2026-0099", "title": "Typed by hand"})
        self.edit({}, drop=("2026-0004",), add=(extra,))
        r = self.rebuild()
        self.assertIn("2026-0099: this row is not in the last generated index", r.stdout)
        self.assertIn("2026-0004: the row was deleted from INDEX.csv; it comes back from the matter files", r.stdout)
        refs = self.rows()
        self.assertIn("2026-0004", refs)
        self.assertNotIn("2026-0099", refs)

    def test_no_apply_reports_only(self):
        self.rebuild()
        self.edit({"2026-0001": {"status": "closed"}, "2026-0002": {"lawyer_minutes": "30"},
                   "NOISE-0001": {"status": "closed"}})
        index_before = (self.ws.root / "INDEX.csv").read_bytes()
        a_before = (self.m["A"] / "matter.md").read_text()
        b_before = (self.m["B"] / "matter.md").read_text()
        md_before = self.ws.read("INDEX.md")
        r = self.rebuild("--no-apply")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("would close 2026-0001", r.stdout)
        self.assertIn("would set 2026-0002 lawyer_minutes = 30", r.stdout)
        self.assertIn("would confirm NOISE-0001", r.stdout)
        self.assertIn("nothing written: --no-apply", r.stdout)
        self.assertEqual((self.ws.root / "INDEX.csv").read_bytes(), index_before)
        self.assertEqual((self.m["A"] / "matter.md").read_text(), a_before)
        self.assertEqual((self.m["B"] / "matter.md").read_text(), b_before)
        self.assertEqual(self.ws.read("INDEX.md"), md_before)
        self.assertTrue((self.ws.root / "inbox" / "noise" / NOISE1).exists())
        self.assertNotIn("human-edit-applied", self.journal())
        r = self.rebuild()
        self.assertIn("closed-by-lawyer 2026-0001", r.stdout, "the edits are still applied later")

    def test_first_run_without_generated_copy_detects_nothing(self):
        self.rebuild()
        self.edit({"2026-0001": {"status": "closed"}})
        (self.ws.root / "changes" / "INDEX.generated.csv").unlink()
        r = self.rebuild()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.ws.meta(self.m["A"])["status"], "waiting_lawyer")
        self.assertIn("cannot be detected this time", r.stdout)
        kept = self.ws.root / "changes" / "INDEX.before-TEST.csv"
        self.assertTrue(kept.exists())
        self.assertIn("2026-0001", kept.read_text(encoding="utf-8-sig"))
        self.assertTrue((self.ws.root / "changes" / "INDEX.generated.csv").exists())

    def test_locked_index_falls_back_to_new_csv(self):
        self.rebuild()
        self.edit({"2026-0002": {"lawyer_minutes": "40"}})
        index_before = (self.ws.root / "INDEX.csv").read_bytes()
        gen_before = (self.ws.root / "changes" / "INDEX.generated.csv").read_bytes()
        sys.path.insert(0, str(ROOT / "tools" / "lib"))
        import index_rebuild
        real = common.write_text_atomic

        def locked(path, text, encoding="utf-8"):
            if Path(path).name == "INDEX.csv":
                raise PermissionError("locked by Excel")
            return real(path, text, encoding)

        out = io.StringIO()
        with mock.patch.dict(os.environ, {"INTAKE_ROOT": str(self.ws.root)}), \
                mock.patch.object(common, "write_text_atomic", locked), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = index_rebuild.main(["--today", TODAY, "--run", "TEST"])
        self.assertEqual(code, 0)
        self.assertIn("INDEX.csv is locked", out.getvalue())
        self.assertTrue((self.ws.root / "INDEX.new.csv").exists())
        self.assertEqual((self.ws.root / "INDEX.csv").read_bytes(), index_before)
        self.assertEqual((self.ws.root / "changes" / "INDEX.generated.csv").read_bytes(), gen_before,
                         "the generated copy still describes INDEX.csv")
        self.assertEqual(self.ws.meta(self.m["B"])["lawyer_minutes"], "40")

    # ------------------------------------------------------------ integrity

    def test_integrity_errors_exit_1(self):
        ws = self.ws
        ws.make_matter("2026-0002", "commercial", "halden-water", "nda", sub_area="customers", title="Halden NDA",
                       opened="2026-10-20")
        bad = ws.make_matter("2026-0007", "commercial", "meridian-bank", "liability-schedule", sub_area="customers",
                             title="", opened="")
        mismatch = ws.make_matter("2026-0008", "commercial", "volta-rail", "rfq", sub_area="customers",
                                  title="Volta RFQ")
        common.update_frontmatter_file(mismatch / "matter.md", {"reference": "2026-0009"}, history=False)
        r = self.rebuild()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertRegex(r.stdout, r"integrity: duplicate reference 2026-0002: areas/.*acme-automotive.*; areas/.*halden-water")
        self.assertIn("integrity: %s/matter.md: missing title, opened" % ws.rel(bad), r.stdout)
        self.assertIn("integrity: %s: folder name does not start with its reference 2026-0009" % ws.rel(mismatch),
                      r.stdout)
        self.assertTrue((ws.root / "INDEX.csv").exists(), "the index is still written")

    def test_folder_without_reference_is_reported(self):
        d = self.ws.root / "areas" / "commercial" / "customers" / "acme-automotive" / "acme-loose-folder"
        d.mkdir(parents=True)
        (d / "matter.md").write_text("---\nreference: 2026-0010\nkind: matter\narea: commercial\nsubject: acme-automotive\n"
                                     "title: Loose\nstatus: open\nopened: 2026-10-30\n---\n", encoding="utf-8")
        r = self.rebuild()
        self.assertEqual(r.returncode, 1)
        self.assertIn("acme-loose-folder: folder name does not start with its reference 2026-0010", r.stdout)

    # ------------------------------------------------------------ measures and digest parts

    def test_measures(self):
        ws = self.ws
        common.update_frontmatter_file(self.m["C"] / "matter.md", {"lawyer_minutes": "45"}, history=False)
        common.update_frontmatter_file(self.m["A"] / "matter.md",
                                       {"status": "closed", "closed": "2026-10-20", "lawyer_minutes": "15",
                                        "confirmed_outcome": "nothing_needed", "accepted_unchanged": "yes"},
                                       history=False)
        common.update_frontmatter_file(self.m["B"] / "matter.md",
                                       {"accepted_unchanged": "no", "confirmed_outcome": "in_progress",
                                        "lawyer_minutes": "500"}, history=False)
        r = self.rebuild("--json")
        self.assertEqual(r.returncode, 0, r.stdout)
        m = json.loads(r.stdout)["measures"]
        self.assertEqual(m["lawyer_minutes_per_matter"], 30.0, "mean over closed matters only")
        self.assertAlmostEqual(m["accepted_unchanged_share"], 2 / 3.0)
        self.assertAlmostEqual(m["outcome_agreement_share"], 2 / 3.0)
        self.assertEqual(m["hours_to_ready_median"], 2.5)
        md = ws.read("INDEX.md")
        self.assertIn("- Lawyer minutes per matter: 30 (mean over 2 closed matters)", md)
        self.assertIn("- Share of deliverables accepted unchanged: 67% (2 of 3)", md)
        self.assertIn("- Agreement between proposed and confirmed outcome: 67% (2 of 3)", md)
        self.assertIn("- Hours from arrival to ready: 2.5 (median over 3 matters)", md)

    def test_measures_are_na_without_data(self):
        ws = Workspace()
        try:
            ws.make_matter("2026-0001", "commercial", "acme-automotive", "nda", sub_area="customers",
                           title="Acme NDA", status="open", opened="2026-10-30", last_activity="2026-10-30")
            r = ws.run("index-rebuild", "--today", TODAY, "--digest-parts", "changes/parts.md")
            self.assertEqual(r.returncode, 0, r.stdout)
            for text in (ws.read("INDEX.md"), ws.read("changes/parts.md")):
                self.assertIn("- Lawyer minutes per matter: n/a", text)
                self.assertIn("- Share of deliverables accepted unchanged: n/a", text)
                self.assertIn("- Agreement between proposed and confirmed outcome: n/a", text)
                self.assertIn("- Hours from arrival to ready: n/a", text)
            self.assertIn("1. Nothing is waiting on you.", ws.read("changes/parts.md"))
        finally:
            ws.cleanup()

    def test_empty_workspace(self):
        ws = Workspace()
        try:
            r = ws.run("index-rebuild", "--today", TODAY)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(read_index(ws), [])
            self.assertIn("## Open matters\n\nNone.", ws.read("INDEX.md"))
        finally:
            ws.cleanup()

    def test_digest_parts_sections_and_order(self):
        r = self.rebuild("--digest-parts", "changes/TEST-digest.md")
        self.assertEqual(r.returncode, 0, r.stdout)
        text = self.ws.read("changes/TEST-digest.md")
        heads = ["## Nothing needed (confirm)", "## Please check", "## Quiet for ten days or more", "## Measures",
                 "## What you should do next"]
        self.assertEqual([h for h in re.findall(r"^## .*$", text, re.M)], heads)
        self.assertIn("\nconfirm nothing needed: NOISE-0001, NOISE-0002\n", text)
        nothing = text.split(heads[0])[1].split(heads[1])[0]
        self.assertIn("2026-0006](../areas/", nothing)
        self.assertIn("Signed Acme NDA received", nothing, "matters proposing nothing_needed too")
        check = text.split(heads[1])[1].split(heads[2])[0]
        self.assertIn("No tag, and two open Acme matters could fit.", check)
        self.assertIn("Candidates: 2026-0002, 2026-0006.", check)
        quiet = text.split(heads[2])[1].split(heads[3])[0]
        self.assertEqual(re.findall(r"^- \[?([A-Z0-9-]+)", quiet, re.M), ["2026-0001", "2026-0006", "2026-0004"])
        self.assertIn("quiet for 16 days (last activity 2026-10-16)", quiet)
        steps = text.split(heads[4])[1].strip().splitlines()
        self.assertEqual([s.split(" ")[0] for s in steps], ["1.", "2.", "3.", "4.", "5.", "6.", "7."])
        firsts = [re.sub(r"^\[([^\]]+)\]\(.*", r"\1", s.split(" ")[1]) for s in steps]
        self.assertEqual(firsts, ["2026-0002", "2026-0005",   # due soonest
                                  "2026-0001",                # waiting on you, oldest first
                                  "NOISE-0001,", "2026-0006",  # confirmations
                                  "please-check",             # please-check items
                                  "2026-0004"])               # stale
        self.assertIn("Acme MSA: liability cap: Wait for the reply on the cap (due 2026-11-03)", steps[0])
        self.assertIn("[2026-0002](../", steps[0])
        self.assertIn("Northgate invoice short payment: Route to accounts payable (quiet for 16 days)",
                      steps[6])

    def test_json_output(self):
        r = self.rebuild("--json")
        self.assertEqual(r.returncode, 0, r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["counts"], {"matters_open": 5, "matters_closed": 1, "noise": 2, "noise_open": 2})
        self.assertEqual(data["integrity"], [])
        self.assertIn("INDEX.csv", data["written"])

    def test_closed_without_closed_date_uses_last_activity(self):
        common.update_frontmatter_file(self.m["C"] / "matter.md", {"closed": ""}, history=False)
        self.rebuild()
        self.assertEqual(self.rows()["2026-0003"]["days_open"], "2")

    def test_usage_errors(self):
        self.assertEqual(self.ws.run("index-rebuild", "--today", "2026-13-01").returncode, 2)
        self.assertEqual(self.ws.run("index-rebuild", "--bogus").returncode, 2)
        self.assertEqual(self.ws.run("index-rebuild", "--confirm-noise", "nothing").returncode, 2)


if __name__ == "__main__":
    unittest.main()
