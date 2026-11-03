"""Real token use from Claude Code's own logs, for tools/budget-update --measure.

Claude Code writes a transcript of every session, and of every subagent, on this computer:
  <config dir>/projects/<workspace path with every non-alphanumeric character as "-">/*.jsonl
  (and <session>/subagents/*.jsonl), where <config dir> is $CLAUDE_CONFIG_DIR or ~/.claude.
Each model response is a line of type "assistant" with message.model, message.id, a timestamp and
message.usage: input_tokens, cache_creation_input_tokens (split into 5-minute and 1-hour writes),
cache_read_input_tokens and output_tokens (thinking included). One response can appear on several
lines with the same message.id: it is counted once. Only the numbers are read; nothing leaves the machine.

Prices: BUDGET.md's prices_usd_per_mtok gives input/output (and optionally cache read) per million tokens
for each model family. Cache writes cost 1.25 times the input price (5-minute) or 2 times (1-hour).
Fast mode (usage.speed "fast") costs twice the standard price.
"""

import datetime as _dt
import json
import os
import re
from pathlib import Path

# Cache-read prices in USD per million tokens when BUDGET.md gives only input/output. They differ by model.
CACHE_READ_DEFAULT = {"opus": 0.20, "sonnet": 0.20, "haiku": 0.01, "fable": 0.25}
# List prices (input/output per million tokens) for families BUDGET.md does not name.
PRICE_DEFAULT = {"opus": (4.0, 20.0), "sonnet": (2.0, 10.0), "haiku": (0.10, 0.50), "fable": (10.0, 50.0)}
WRITE_5M, WRITE_1H, FAST = 1.25, 2.0, 2.0
FIELDS = ("requests", "input", "write_5m", "write_1h", "read", "output")


def family(model):
    m = (model or "").lower()
    for key in ("opus", "sonnet", "haiku"):
        if key in m:
            return key
    if "fable" in m or "mythos" in m:
        return "fable"
    return ""


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def config_dir():
    env = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return Path(env) if env else Path.home() / ".claude"


def transcript_dirs(root, override=None):
    """The folders holding this workspace's Claude Code transcripts (usually one)."""
    if override:
        return [Path(override)] if Path(override).is_dir() else []
    projects = config_dir() / "projects"
    if not projects.is_dir():
        return []
    names = {d.name.lower(): d for d in projects.iterdir() if d.is_dir()}
    wanted = {slug(Path(root)).lower(), slug(Path(root).resolve()).lower()}
    found = [names[w] for w in wanted if w in names]
    if found:
        return sorted(set(found))
    tail = "-" + slug(Path(root).resolve().name).lower()
    near = [d for n, d in names.items() if n.endswith(tail)]
    return near if len(near) == 1 else []


def parse_time(text):
    try:
        t = _dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=_dt.timezone.utc)


def collect(dirs, since, until):
    """{family or model: {requests, input, write_5m, write_1h, read, output, fast_usd_share}} for responses
    with since < timestamp <= until (aware datetimes), each response counted once."""
    seen, totals = set(), {}
    for d in dirs:
        for f in sorted(Path(d).rglob("*.jsonl")):
            try:
                if _dt.datetime.fromtimestamp(f.stat().st_mtime, _dt.timezone.utc) <= since:
                    continue
                fh = open(str(f), "r", encoding="utf-8", errors="replace")
            except OSError:
                continue
            with fh:
                for line in fh:
                    if '"usage"' not in line:
                        continue
                    try:
                        d_ = json.loads(line)
                    except ValueError:
                        continue
                    msg = d_.get("message") if isinstance(d_, dict) else None
                    if d_.get("type") != "assistant" or not isinstance(msg, dict):
                        continue
                    usage = msg.get("usage")
                    if not isinstance(usage, dict):
                        continue
                    t = parse_time(d_.get("timestamp", ""))
                    if t is None or t <= since or t > until:
                        continue
                    key_id = msg.get("id") or d_.get("requestId") or d_.get("uuid")
                    if key_id in seen:
                        continue
                    seen.add(key_id)
                    model = str(msg.get("model") or "")
                    if model.startswith("<"):          # <synthetic> lines carry no real use
                        continue
                    fam = family(model) or model
                    row = totals.setdefault(fam, dict.fromkeys(FIELDS, 0))
                    row.setdefault("fast", 0)
                    cc = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else {}
                    w1h = int(cc.get("ephemeral_1h_input_tokens") or 0)
                    w5m = int(cc.get("ephemeral_5m_input_tokens") or 0)
                    total_write = int(usage.get("cache_creation_input_tokens") or 0)
                    if total_write > w1h + w5m:        # no split given: count the rest as 5-minute writes
                        w5m += total_write - w1h - w5m
                    parts = {"input": int(usage.get("input_tokens") or 0), "write_5m": w5m, "write_1h": w1h,
                             "read": int(usage.get("cache_read_input_tokens") or 0),
                             "output": int(usage.get("output_tokens") or 0)}
                    row["requests"] += 1
                    for k, v in parts.items():
                        row[k] += v
                    if str(usage.get("speed") or "").lower() == "fast":
                        row["fast"] += 1
                        row.setdefault("fast_parts", dict.fromkeys(parts, 0))
                        for k, v in parts.items():
                            row["fast_parts"][k] += v
    return totals


def prices_for(fam, prices):
    """(input, output, cache read) per million tokens for a family, from BUDGET.md or the defaults."""
    p = prices.get(fam)
    if p is None:
        p = PRICE_DEFAULT.get(fam)
    if p is None:
        return None
    pin, pout = p[0], p[1]
    pread = p[2] if len(p) > 2 else CACHE_READ_DEFAULT.get(fam, 0.1 * pin)
    return pin, pout, pread


def cost(fam, row, prices):
    """USD for one family's totals, or None when its prices are unknown."""
    p = prices_for(fam, prices)
    if p is None:
        return None
    pin, pout, pread = p

    def usd(parts):
        return (parts["input"] * pin + parts["write_5m"] * pin * WRITE_5M + parts["write_1h"] * pin * WRITE_1H
                + parts["read"] * pread + parts["output"] * pout) / 1e6

    total = usd(row)
    if row.get("fast_parts"):
        total += usd(row["fast_parts"]) * (FAST - 1)   # fast mode: the same tokens at twice the price
    return total


def shares(row, prices, fam):
    """Where the money went for one family: {part: USD}."""
    p = prices_for(fam, prices)
    if p is None:
        return {}
    pin, pout, pread = p
    return {"fresh input": row["input"] * pin / 1e6, "cache writes": (row["write_5m"] * WRITE_5M + row["write_1h"]
            * WRITE_1H) * pin / 1e6, "cache reads": row["read"] * pread / 1e6, "output": row["output"] * pout / 1e6}
