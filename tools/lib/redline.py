"""redline-changes: the tracked changes and comments of a Word mark-up (.docx), each with its clause number,
author and date, and each changed paragraph as it reads with the changes marked. pandoc's plain text gives
the whole document; this gives what changed and little else.

Run through the wrapper: bash tools/redline-changes FILE.docx [--clause N] [--summary] [--no-context]
Clause numbers come from Word's automatic numbering (numbering.xml and the paragraph styles), or from a number
typed at the start of a paragraph (9.1, (a), Clause 9); a paragraph without one takes the clause above it;
before the first numbered paragraph, the paragraph's position (para 3). A schedule or annex heading is kept as
a prefix (schedule 2 para 1.1). Footnotes, headers and footers are searched too.
In context lines [-text-] was deleted and {+text+} inserted. Formatting changes are counted, not listed.
Exit 0 (changes printed, or none found), 2 not a readable .docx.
"""

import argparse
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
W14 = "{http://schemas.microsoft.com/office/word/2010/wordml}"
W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
STRICT = b"http://purl.oclc.org/ooxml/wordprocessingml/main"
TRANSITIONAL = b"http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MAX_PART = 200 * 1024 * 1024
CHANGE = {W + "ins": "inserted", W + "del": "deleted", W + "moveTo": "moved here", W + "moveFrom": "moved away"}
REMOVED = ("deleted", "moved away")
COMMENTS = ("comment", "reply")
FORMAT = {W + t for t in ("rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "trPrChange",
                          "tcPrChange", "tblGridChange", "numberingChange")}
SKIP = {W + "pPr", W + "rPr", W + "p"}
TYPED = re.compile(r"^\s*(?:(clause|section|article|paragraph)\s+(\d+(?:\.\d+)*[a-z]?)\b"
                   r"|(\d{1,3}\.(?:\d{1,3}\.?)*)(?=\s)"
                   r"|\(([a-z]{1,4}|\d{1,2})\)(?=\s)"
                   r"|([a-z])\)(?=\s))", re.I)
PART = re.compile(r"^\s*(schedule|annex|annexure|appendix|exhibit|attachment)\s+([0-9a-z]{1,4})\b", re.I)
ROMAN = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
         (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]


def roman(n):
    out = ""
    for value, letters in ROMAN:
        while n >= value:
            out += letters
            n -= value
    return out


def fmt(n, kind):
    if kind in ("lowerLetter", "upperLetter"):
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(97 + r) + s
        return s.upper() if kind == "upperLetter" else s
    if kind in ("lowerRoman", "upperRoman"):
        return roman(n).upper() if kind == "upperRoman" else roman(n)
    if kind == "decimalZero":
        return "%02d" % n
    return str(n)


def val(el, tag):
    """The w:val of child tag of el, or None."""
    if el is None:
        return None
    child = el.find(W + tag)
    return None if child is None else child.get(W + "val")


def read_xml(z, name):
    """A part of the package as XML, or None when it is missing. Strict OOXML is read as transitional."""
    try:
        info = z.getinfo(name)
    except KeyError:
        return None
    if info.file_size > MAX_PART:
        raise ValueError("%s is too large to read safely (%d MB)" % (name, info.file_size // 2 ** 20))
    data = z.read(name)
    if STRICT in data:
        data = data.replace(STRICT, TRANSITIONAL)
    root = ET.fromstring(data)
    for parent in list(root.iter()):           # drawings carry a second copy of text boxes as a fallback
        for child in list(parent):
            if child.tag == MC_FALLBACK:
                parent.remove(child)
    return root


def main_part(z):
    try:
        for r in ET.fromstring(z.read("_rels/.rels")):
            if (r.get("Type") or "").endswith("/officeDocument"):
                return (r.get("Target") or "").lstrip("/") or "word/document.xml"
    except (KeyError, ET.ParseError):
        pass
    return "word/document.xml"


class Numbering:
    """Word's automatic numbers, from numbering.xml and the paragraph styles that carry numbering."""

    def __init__(self, z):
        self.num_to_abs, self.levels, self.level_of_style, self.styles = {}, {}, {}, {}
        self.counts, self.full = {}, {}
        root = read_xml(z, "word/numbering.xml")
        if root is not None:
            for ab in root.findall(W + "abstractNum"):
                aid = ab.get(W + "abstractNumId")
                for lvl in ab.findall(W + "lvl"):
                    il = int(lvl.get(W + "ilvl") or 0)
                    start = val(lvl, "start")
                    self.levels[(aid, il)] = (val(lvl, "numFmt") or "decimal", val(lvl, "lvlText"),
                                              int(start) if start and start.isdigit() else 1)
                    if val(lvl, "pStyle"):
                        self.level_of_style[(aid, val(lvl, "pStyle"))] = il
            for num in root.findall(W + "num"):
                if val(num, "abstractNumId") is not None:
                    self.num_to_abs[num.get(W + "numId")] = val(num, "abstractNumId")
        root = read_xml(z, "word/styles.xml")
        if root is not None:
            for st in root.findall(W + "style"):
                np_ = st.find(W + "pPr/" + W + "numPr")
                il = val(np_, "ilvl")
                self.styles[st.get(W + "styleId")] = (val(np_, "numId"), int(il) if il and il.isdigit() else None,
                                                      val(st, "basedOn"))

    def from_style(self, style):
        for _ in range(12):                      # follow basedOn a few steps, never in a loop
            if not style or style not in self.styles:
                break
            num_id, ilvl, based = self.styles[style]
            if num_id is not None:
                return num_id, ilvl
            style = based
        return None, None

    def label(self, p):
        """The automatic number of paragraph p with its parents (9.1(a)), or ''. Call once per paragraph."""
        ppr = p.find(W + "pPr")
        style = val(ppr, "pStyle")
        np_ = ppr.find(W + "numPr") if ppr is not None else None
        num_id, il = val(np_, "numId"), val(np_, "ilvl")
        ilvl = int(il) if il and il.isdigit() else None
        if num_id is None and style:
            num_id, style_ilvl = self.from_style(style)
            ilvl = style_ilvl if ilvl is None else ilvl
        if num_id is None or num_id == "0" or num_id not in self.num_to_abs:
            return ""
        aid = self.num_to_abs[num_id]
        if ilvl is None:
            ilvl = self.level_of_style.get((aid, style), 0)
        kind, text, start = self.levels.get((aid, ilvl), ("decimal", None, 1))
        counts, full = self.counts.setdefault(aid, {}), self.full.setdefault(aid, {})
        counts[ilvl] = counts.get(ilvl, start - 1) + 1
        for deeper in [k for k in counts if k > ilvl]:
            del counts[deeper]
            full.pop(deeper, None)
        if kind in ("bullet", "none"):
            return ""
        if text is None:
            text = "%%%d." % (ilvl + 1)
        own = text
        for lv in range(9):
            token = "%%%d" % (lv + 1)
            if token in own:
                lk, _, ls = self.levels.get((aid, lv), ("decimal", None, 1))
                own = own.replace(token, fmt(counts.get(lv, ls), lk))
        own = own.strip()
        if not own:
            return ""
        parents = [k for k in full if k < ilvl]
        if ilvl > 0 and "%1" not in text and parents:
            core = own.strip("().")
            parent = full[max(parents)].rstrip(".")
            own = parent + ("." + core if core.isdigit() else "(" + core + ")")
        full[ilvl] = own
        return own


def comments_of(z):
    """{comment id: (author, date, text, parent comment id or None, resolved)}. Replies and resolved marks come
    from commentsExtended.xml (Word 2013 and later), which links each comment's last paragraph to its parent's."""
    root = read_xml(z, "word/comments.xml")
    out, para_to_id = {}, {}
    for c in ([] if root is None else root.findall(W + "comment")):
        paras = c.findall(W + "p")
        text = " ".join(t for t in (" ".join(x.text for x in p.iter(W + "t") if x.text) for p in paras) if t.strip())
        out[c.get(W + "id")] = [c.get(W + "author") or "unknown", (c.get(W + "date") or "")[:10], text.strip(),
                                None, False]
        if paras and paras[-1].get(W14 + "paraId"):
            para_to_id[paras[-1].get(W14 + "paraId")] = c.get(W + "id")
    ext = read_xml(z, "word/commentsExtended.xml")
    for ce in ([] if ext is None else ext.iter(W15 + "commentEx")):
        cid = para_to_id.get(ce.get(W15 + "paraId"))
        if cid in out:
            out[cid][3] = para_to_id.get(ce.get(W15 + "paraIdParent"))
            out[cid][4] = ce.get(W15 + "done") == "1"
    return {k: tuple(v) for k, v in out.items()}


def anchors_of(root):
    """{comment id: the text it is anchored to, as it now reads (the deleted text when nothing else is left)}."""
    open_, now, removed = set(), {}, {}

    def walk(node, gone):
        for child in node:
            tag = child.tag
            if tag == W + "commentRangeStart":
                open_.add(child.get(W + "id"))
            elif tag == W + "commentRangeEnd":
                open_.discard(child.get(W + "id"))
            elif tag in (W + "t", W + "delText"):
                if child.text and open_:
                    for cid in open_:
                        (removed if gone or tag == W + "delText" else now).setdefault(cid, []).append(child.text)
            else:
                walk(child, gone or tag in (W + "del", W + "moveFrom"))

    walk(root, False)
    return {k: squeeze("".join(now.get(k) or removed.get(k) or [])).strip() for k in set(now) | set(removed)}


def segments(p, notes, anchors):
    """Paragraph p in order as [kind, author, date, text, anchor, note]: kind '' for unchanged text, a CHANGE
    value, 'comment' or 'reply' (text the comment, anchor the text it is on, note 'reply to <author>' and
    'resolved'). Nested paragraphs (text boxes) are left out."""
    out = []

    def add(kind, author, date, text):
        if out and out[-1][0] == kind and out[-1][1:3] == [author, date]:
            out[-1][3] += text
        else:
            out.append([kind, author, date, text, "", ""])

    def walk(node, kind, author, date):
        for child in node:
            tag = child.tag
            if tag in SKIP:
                continue
            if tag in CHANGE:
                walk(child, CHANGE[tag], child.get(W + "author") or "unknown", (child.get(W + "date") or "")[:10])
            elif tag == W + "t" or (tag == W + "delText" and kind in REMOVED):
                if child.text:
                    add(kind, author, date, child.text)
            elif tag in (W + "tab", W + "br", W + "cr") and node.tag == W + "r":
                add(kind, author, date, " ")
            elif tag == W + "commentReference":
                cid = child.get(W + "id")
                if cid in notes:
                    who, when, text, parent, done = notes[cid]
                    note = ("reply to %s" % notes[parent][0]) if parent in notes else ""
                    note = ", ".join(x for x in (note, "resolved" if done else "") if x)
                    out.append(["reply" if parent in notes else "comment", who, when, text,
                                "" if parent in notes else anchors.get(cid, ""), note])
            else:
                walk(child, kind, author, date)

    walk(p, "", None, None)
    return out


def squeeze(text):
    return re.sub(r"\s+", " ", text)


def context(segs):
    """The paragraph as it reads with [-deleted-] and {+inserted+} text; long unchanged stretches shortened."""
    parts = [s for s in segs if s[0] not in COMMENTS]
    out = []
    for i, (kind, _, _, text, _, _) in enumerate(parts):
        text = squeeze(text)
        lead, core = text[:len(text) - len(text.lstrip())], text.strip()
        trail = text[len(text.rstrip()):] if core else ""
        if kind in REMOVED and core:
            out.append("%s[-%s-]%s" % (lead, core, trail))
        elif kind and core:
            out.append("%s{+%s+}%s" % (lead, core, trail))
        elif kind:
            out.append(text)
        elif len(text) > 240:
            first, last = i == 0, i == len(parts) - 1
            if first and last:
                out.append(text)
            elif first:
                out.append("..." + text[-120:])
            elif last:
                out.append(text[:120] + "...")
            else:
                out.append(text[:100] + " ... " + text[-100:])
        else:
            out.append(text)
    return "".join(out).strip()


def typed_label(text):
    """('main', '9.1') or ('sub', 'a') for a number typed at the start of a paragraph, else None."""
    m = TYPED.match(text)
    if not m:
        return None
    if m.group(1):
        return "main", "%s %s" % (m.group(1).lower(), m.group(2))
    if m.group(3):
        return "main", m.group(3).rstrip(".")
    return "sub", (m.group(4) or m.group(5)).lower()


def paragraphs(root):
    body = root.find(W + "body")
    return list((body if body is not None else root).iter(W + "p"))


def collect(path):
    """(records, number of formatting changes); a record is {where, items, context} for each paragraph with a
    tracked change or a comment, in document order."""
    try:
        z = zipfile.ZipFile(path)
        main = read_xml(z, main_part(z))
        if main is None:
            raise KeyError("no main document part")
        numbering, notes = Numbering(z), comments_of(z)
        others = [(n, read_xml(z, n)) for n in sorted(z.namelist())
                  if re.match(r"word/(footnotes|endnotes|header\d*|footer\d*)\.xml$", n)]
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError, ValueError) as exc:
        raise ValueError("not a readable .docx: %s" % exc)
    records, current, main_label, part = [], "", "", ""
    anchors = anchors_of(main)
    formatting = sum(1 for root in [main] + [r for _, r in others if r is not None]
                     for el in root.iter() if el.tag in FORMAT)
    for n, p in enumerate(paragraphs(main), 1):
        auto = numbering.label(p)
        segs = segments(p, notes, anchors)
        final = "".join(s[3] for s in segs if s[0] not in REMOVED and s[0] not in COMMENTS)
        heading = PART.match(final) if len(final.strip()) <= 80 else None
        if heading:
            part, current, main_label = "%s %s" % (heading.group(1).lower(), heading.group(2)), "", ""
        typed = None if auto else typed_label(final)
        if auto and not auto.startswith("("):
            current = main_label = auto.rstrip(".")
        elif auto or (typed and typed[0] == "sub"):
            sub = (auto or typed[1]).strip("()")
            current = (main_label + "(" + sub + ")") if main_label else "(" + sub + ")"
        elif typed:
            current = main_label = typed[1]
        numbered = current[:1].isdigit() or current.startswith("(")
        if current and numbered:
            where = ("%s para %s" % (part, current)) if part else "clause " + current
        else:
            where = current or part or "para %d" % n      # "article 9" as typed; else the schedule; else position
        items = [s for s in segs if s[0] and (s[0] in COMMENTS or s[3].strip())]
        if items:
            records.append({"where": where, "items": items, "context": context(segs)})
    for name, root in others:
        if root is None:
            continue
        kind = re.match(r"word/([a-z]+)", name).group(1).rstrip("s")
        part_anchors = anchors_of(root)
        for p in root.iter(W + "p"):
            segs = segments(p, notes, part_anchors)
            items = [s for s in segs if s[0] and (s[0] in COMMENTS or s[3].strip())]
            if items:
                records.append({"where": kind, "items": items, "context": context(segs)})
    return records, formatting


def counted(kinds):
    """'2 inserted, 1 deleted, 3 comments' from {kind: number}, in first-seen order."""
    plural = {"comment": "comments", "reply": "replies"}
    return ", ".join("%d %s" % (k, plural.get(v, v) if k != 1 else v) for v, k in kinds.items())


def matches(where, wanted):
    """Whether a record's place is clause `wanted` or inside it: 9 matches clause 9, 9.1 and 9.2(a), not 19."""
    w, x = where.lower(), wanted.lower().strip()
    x = re.sub(r"^clause ", "", x)
    label = w.split(" para ", 1)[1] if " para " in w else re.sub(r"^[a-z]+ ", "", w)
    return w == x or w.startswith(x + " ") or label == x or label.startswith(x + ".") or label.startswith(x + "(")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bash tools/redline-changes",
                                 description="Tracked changes and comments of a .docx, with clause numbers.")
    ap.add_argument("file")
    ap.add_argument("--clause", metavar="N", help="only this clause and its sub-clauses (9 gives 9, 9.1, 9.2(a))")
    ap.add_argument("--summary", action="store_true", help="one line per changed clause: what kind of changes, by whom")
    ap.add_argument("--no-context", action="store_true", help="leave out the paragraph each change sits in")
    ap.add_argument("--run", metavar="RUN", help="the run id; every tool accepts it (not used here)")
    a = ap.parse_args(argv)
    try:
        records, formatting = collect(a.file)
    except ValueError as exc:
        sys.stderr.write("redline-changes: %s. A .doc or .pdf: use pandoc, or ask for the .docx.\n" % exc)
        return 2
    if a.clause:
        records = [r for r in records if matches(r["where"], a.clause)]
    if not records:
        print("no tracked changes or comments%s in %s" % (" in clause " + a.clause if a.clause else "", a.file))
        if formatting and not a.clause:
            print("-- %d formatting change%s, not listed" % (formatting, "" if formatting == 1 else "s"))
        return 0
    tally, order = {}, []
    for r in records:
        for kind, who, _, _, _, _ in r["items"]:
            if who not in tally:
                tally[who] = {}
                order.append(who)
            tally[who][kind] = tally[who].get(kind, 0) + 1
    if a.summary:
        by_where, seen = {}, []
        for r in records:
            if r["where"] not in by_where:
                by_where[r["where"]] = ({}, [])
                seen.append(r["where"])
            kinds, people = by_where[r["where"]]
            for kind, who, _, _, _, _ in r["items"]:
                kinds[kind] = kinds.get(kind, 0) + 1
                if who not in people:
                    people.append(who)
        for where in seen:
            kinds, people = by_where[where]
            print("%s | %s | %s" % (where, counted(kinds), "; ".join(people)))
    else:
        for r in records:
            for kind, who, when, text, anchor, note in r["items"]:
                line = '%s | %s | %s | %s | "%s"' % (r["where"], kind, who, when or "no date", squeeze(text).strip())
                if anchor:
                    line += ' on "%s"' % (anchor if len(anchor) <= 120 else anchor[:117] + "...")
                if note:
                    line += " (%s)" % note
                print(line)
            if not a.no_context and any(i[0] not in COMMENTS for i in r["items"]):
                print('    reads: "%s"' % r["context"])
    n_items = sum(len(r["items"]) for r in records)
    print("-- %d item%s in %d paragraph%s. %s.%s" % (
        n_items, "" if n_items == 1 else "s", len(records), "" if len(records) == 1 else "s",
        ". ".join("%s: %s" % (who, counted(tally[who])) for who in order),
        (" %d formatting change%s, not listed." % (formatting, "" if formatting == 1 else "s")) if formatting else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
