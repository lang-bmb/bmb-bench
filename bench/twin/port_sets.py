#!/usr/bin/env python3
"""The task sets of the port twin: what the generators are run with.

A set is a directory of tasks under `bench/twin/` made by `port_tasks.py`,
`port_change.py` and `port_replay.py` (`--set NAME`) from one fixture, one
seed and the counts below. Everything a set is made from is in its row
here, in the generators and in the product at the tasks' commit.

    port     the first set: components C0 to C4 against their port. The
             tools of the BMB arm were changed after its results were seen.
    gate-d   the set drawn anew at full size: every file of `compiler/src`
             against the whole port, another seed, and no target (function,
             diagnostic code, state field) the set `port` used.

Fields:

    dir         the set's directory under `bench/twin/`
    fixture     `fixtures/NAME/fixture.json`: its `rust.files` are the Rust
                files the targets are taken from
    seed        of the shuffles
    avoid       sets whose targets are no candidates here (`avoided`)
    comprehend  tasks per family of `port_tasks.py`
    state       where the `state` family's fields come from: `table` (the
                hand-kept `STATE` of `port_tasks.py`) or `derived` (every
                field one structure of each side has, `port_tasks.fields`)
    change      tasks per generated family of `port_change.py`
    hand        whether the hand-written families of `port_hand.py` follow
    conditions  the tool conditions of `parity.json` a `rename` task also
                carries reference and weak solutions for, beside the main
                one (`port`)
    replays, histories, steps
                the counts of `port_replay.py`
    sites       which diagnostic codes are replayed: `one` (each side
                reports the code in one statement) or `every` (in any
                number of statements, all of which are removed)
    first       what the replay candidates are spent on first when both
                counts cannot be met: `replays` or `histories`

    port_sets.py manifest NAME [--check]   write (or compare) the set's MANIFEST

A frozen set has a `MANIFEST` (`scripts/manifests.py`): its tasks and
`REVIEW.md`, its fixture and the two prompts. The harness and the
generators are not in it: a result row names the commit of this repository
it was made with.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SETS = {
    "port": {
        "dir": "port", "fixture": "port", "seed": 20261117, "avoid": [],
        "comprehend": {"callers": 7, "impact": 5, "diag": 7, "state": 5}, "state": "table",
        "change": {"rename": 10, "swap": 6}, "hand": True, "conditions": [],
        "replays": 22, "histories": 4, "steps": 5, "first": "replays", "sites": "one",
    },
    "gate-d": {
        "dir": "gate-d", "fixture": "port-full", "seed": 20261128, "avoid": ["port"],
        "comprehend": {"callers": 10, "impact": 10, "diag": 10, "state": 10}, "state": "derived",
        "change": {"rename": 12, "swap": 8}, "hand": False, "conditions": ["port-rename"],
        "replays": 30, "histories": 12, "steps": 5, "first": "histories", "sites": "every",
    },
}


def get(name):
    if name not in SETS:
        raise SystemExit(f"no set {name!r}: {', '.join(sorted(SETS))}")
    return {"name": name, **SETS[name]}


def out_dir(s):
    return os.path.join(HERE, s["dir"])


def add_argument(parser):
    parser.add_argument("--set", default="port", choices=sorted(SETS), help="the task set (default: port)")


def rust_files(s):
    """The Rust files of the set's fixture, relative to `compiler/src`."""
    with open(os.path.join(HERE, "fixtures", s["fixture"], "fixture.json"), encoding="utf-8") as h:
        files = json.load(h)["rust"]["files"]
    return [f[len("src/"):] for f in files]


def beside(s):
    """What the set's fixture puts beside the Rust crate."""
    with open(os.path.join(HERE, "fixtures", s["fixture"], "fixture.json"), encoding="utf-8") as h:
        return json.load(h)["rust"].get("beside", [])


def targets(s):
    """What the tasks of set `s` are about, in lower case: the last part
    of a task's name (a function, a diagnostic code or a field: the
    generators name a task after its target) and the code of every step of
    a history."""
    out = set()
    d = out_dir(s)
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(d, f), encoding="utf-8") as h:
            task = json.load(h)
        out.add(task["id"].split("-", 2)[2])
        out |= {st["source"]["code"].lower() for st in task.get("steps", [])}
    return out


def avoided(s):
    """The targets of the sets `s` avoids."""
    out = set()
    for name in s["avoid"]:
        out |= targets(get(name))
    return out


def manifest(s):
    """The text of the set's MANIFEST: `<sha256>  <path>` per frozen file,
    the path relative to the set's directory."""
    d = out_dir(s)
    paths = sorted(f for f in os.listdir(d) if f.endswith(".json") or f == "REVIEW.md")
    paths += [f"../fixtures/{s['fixture']}/fixture.json", "../prompt-bmb.md", "../prompt-rust.md"]
    lines = []
    for p in paths:
        with open(os.path.join(d, p), "rb") as h:
            lines.append(f"{hashlib.sha256(h.read()).hexdigest()}  {p}\n")
    return "".join(lines)


def main():
    if len(sys.argv) not in (3, 4) or sys.argv[1] != "manifest" or sys.argv[3:] not in ([], ["--check"]):
        sys.exit(__doc__)
    s = get(sys.argv[2])
    path, text = os.path.join(out_dir(s), "MANIFEST"), manifest(s)
    if sys.argv[3:]:
        with open(path, encoding="utf-8") as h:
            if h.read() != text:
                sys.exit(f"{s['dir']}/MANIFEST does not list the set as it is (a task not listed, or one that changed)")
        print(f"ok: {s['dir']}/MANIFEST lists {text.count(chr(10))} files")
        return
    with open(path, "w", encoding="utf-8") as h:
        h.write(text)
    print(f"wrote {s['dir']}/MANIFEST: {text.count(chr(10))} files")


if __name__ == "__main__":
    main()
