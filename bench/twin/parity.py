#!/usr/bin/env python3
"""The tool parity table of the port twin (`parity.json`).

  parity.py check    the table agrees with the tools the harness gives
  parity.py pin      record the present tool lists in the table
  parity.py table    the table as Markdown (for a measurement report)

Twice a verdict of the twin was decided by a tool one arm lacked (text
search, renaming). The table says, operation by operation, which tools of
each arm do it, and names every operation only one arm can do (`gap`). It is
written before a measurement is frozen. `check` fails when

  - a tool the table names does not exist in that arm, or a tool an arm has
    is in no row (a new tool must be placed before it is measured with);
  - a `form` of a BMB tool (a query name, a field of `write`) is not in that
    tool's description or schema;
  - a row has an empty arm and no `gap`, or a `gap` and no empty arm (a
    `needs` entry counts as empty in the conditions without that flag);
  - the tool lists changed since `pin` (their digests are in the table): the
    table is read again against the new tools, then pinned.

The BMB tools are read from `bmb mcp FLAGS` of each condition, with the
transaction tools hidden as the harness hides them. Standard library only.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pair  # noqa: E402

FILE = os.path.join(HERE, "parity.json")


def digest(tools):
    text = json.dumps(sorted(tools, key=lambda t: t["name"]), sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def bmb_tools(flags):
    """The tools an agent of the BMB arm sees under FLAGS."""
    with tempfile.TemporaryDirectory() as ws:
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "bmb-parity", "version": "1"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        r = subprocess.run([pair.bmb_bin(), "mcp", *flags, ws], capture_output=True, text=True,
                           input="".join(json.dumps(x) + "\n" for x in requests))
    lines = r.stdout.splitlines()
    if not lines:
        sys.exit(f"parity: `bmb mcp {' '.join(flags)}` gave no answer: {r.stderr.strip()}")
    tools = json.loads(lines[-1])["result"]["tools"]
    return [t for t in tools if t["name"] not in pair.HIDDEN]


def problems(doc, rust, bmb_of):
    """What is wrong with table DOC, given the Rust tools and the BMB tools
    of each condition (a list of sentences; empty when it holds)."""
    out = []
    rust_names = {t["name"] for t in rust}
    if doc.get("rust_tools") != digest(rust):
        out.append("the Rust tools changed since the table was pinned")
    used_rust = set()
    for row in doc["operations"]:
        for e in row["rust"]:
            used_rust.add(e["tool"])
            if e["tool"] not in rust_names:
                out.append(f"{row['op']}: the Rust arm has no tool `{e['tool']}`")
    for n in sorted(rust_names - used_rust):
        out.append(f"the Rust tool `{n}` is in no row")
    for cond, c in doc["conditions"].items():
        tools = {t["name"]: t for t in bmb_of[cond]}
        if c.get("tools") != digest(bmb_of[cond]):
            out.append(f"{cond}: the BMB tools changed since the table was pinned")
        used = set()
        for row in doc["operations"]:
            have = []
            for e in row["bmb"]:
                if "needs" in e and e["needs"] not in c["flags"]:
                    continue
                have.append(e)
                used.add(e["tool"])
                t = tools.get(e["tool"])
                if t is None:
                    out.append(f"{cond}: {row['op']}: the BMB arm has no tool `{e['tool']}`")
                    continue
                if "form" in e:
                    word = e["form"].split()[0]
                    text = t["description"] + json.dumps(t["inputSchema"])
                    if word not in text:
                        out.append(f"{cond}: {row['op']}: `{e['tool']}` does not name `{word}`")
            one_sided = not have or not row["rust"]
            if one_sided and "gap" not in row:
                out.append(f"{cond}: {row['op']}: one arm cannot do it and the row has no `gap`")
        for n in sorted(set(tools) - used):
            out.append(f"{cond}: the BMB tool `{n}` is in no row")
    for row in doc["operations"]:
        if "gap" in row and row["rust"] and all(
                any("needs" not in e or e["needs"] in c["flags"] for e in row["bmb"])
                for c in doc["conditions"].values()):
            out.append(f"{row['op']}: a `gap` on a row both arms can do in every condition")
    return out


def table(doc):
    def cell(es):
        return ", ".join("`" + e["tool"] + (" " + e["form"] if "form" in e else "") + "`"
                         + (f" (with `{e['needs']}`)" if "needs" in e else "") for e in es) or "none"
    lines = ["| Operation | Rust arm | BMB arm | Note |", "| --- | --- | --- | --- |"]
    for row in doc["operations"]:
        note = row.get("gap") or row.get("note") or ""
        mark = "**Gap.** " if "gap" in row else ""
        lines.append(f"| {row['op']} | {cell(row['rust'])} | {cell(row['bmb'])} | {mark}{note} |")
    return "\n".join(lines) + "\n"


def main():
    cmd = sys.argv[1] if len(sys.argv) == 2 else ""
    doc = json.load(open(FILE, encoding="utf-8"))
    if cmd == "table":
        sys.stdout.write(table(doc))
        return 0
    if cmd not in ("check", "pin"):
        sys.stderr.write(__doc__)
        return 2
    bmb_of = {cond: bmb_tools(c["flags"]) for cond, c in doc["conditions"].items()}
    if cmd == "pin":
        doc["rust_tools"] = digest(pair.RUST_TOOLS)
        for cond, c in doc["conditions"].items():
            c["tools"] = digest(bmb_of[cond])
        with open(FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    bad = problems(doc, pair.RUST_TOOLS, bmb_of)
    for b in bad:
        print(f"parity: {b}")
    if bad:
        return 1
    gaps = sum(1 for row in doc["operations"] if "gap" in row)
    print(f"parity: {len(doc['operations'])} operations, {gaps} gaps, {len(doc['conditions'])} conditions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
