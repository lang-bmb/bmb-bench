#!/usr/bin/env python3
"""The parity check holds on the committed table and fails on tables that are
wrong in each way it names. Standard library only."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pair  # noqa: E402
import parity  # noqa: E402


def main():
    doc = json.load(open(parity.FILE, encoding="utf-8"))
    bmb_of = {cond: parity.bmb_tools(c["flags"]) for cond, c in doc["conditions"].items()}
    rust = pair.RUST_TOOLS
    assert parity.problems(doc, rust, bmb_of) == [], parity.problems(doc, rust, bmb_of)

    def wrong(change, word):
        d = copy.deepcopy(doc)
        r, b = copy.deepcopy(rust), copy.deepcopy(bmb_of)
        change(d, r, b)
        got = parity.problems(d, r, b)
        assert any(word in g for g in got), (word, got)

    def row(d, op):
        return next(x for x in d["operations"] if x["op"] == op)

    # A tool one arm does not have.
    wrong(lambda d, r, b: row(d, "run tests")["rust"].append({"tool": "run"}), "no tool `run`")
    wrong(lambda d, r, b: row(d, "build the program")["bmb"].append({"tool": "run"}), "no tool `run`")
    # A tool of an arm that the table does not place.
    wrong(lambda d, r, b: r.append({"name": "rename", "description": "", "inputSchema": {}}), "`rename` is in no row")
    wrong(lambda d, r, b: b["port"].append({"name": "run", "description": "", "inputSchema": {}}), "`run` is in no row")
    # A form the tool does not name.
    wrong(lambda d, r, b: row(d, "find a definition by name")["bmb"].append({"tool": "query", "form": "regex P"}),
          "does not name `regex`")
    # One arm cannot do it and the row does not say so.
    wrong(lambda d, r, b: row(d, "run tests").pop("gap"), "has no `gap`")
    wrong(lambda d, r, b: row(d, "rename a definition and every use in one call").pop("gap"), "has no `gap`")
    # A gap on a row both arms can do.
    wrong(lambda d, r, b: row(d, "build the program").update(gap="x"), "both arms can do")
    # The tools changed since the pin.
    wrong(lambda d, r, b: r[0].update(description="other"), "Rust tools changed")
    wrong(lambda d, r, b: b["port"][0].update(description="other"), "port: the BMB tools changed")
    # The rename of `write` exists only with its flag.
    names = {c: " ".join(json.dumps(t["inputSchema"]) for t in bmb_of[c] if t["name"] == "write") for c in bmb_of}
    assert '"rename"' not in names["port"] and '"rename"' in names["port-rename"]
    assert not any(t["name"].startswith("tx_") for c in bmb_of for t in bmb_of[c])
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
