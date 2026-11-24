#!/usr/bin/env python3
"""H-COMPAT on BCB histories (ADR-0078 §1). Deterministic.

  compat.py HISTORY.jsonl [--upto K] [--out FILE.jsonl] [--write REPORT.md]

Replays a BCB history (`history.py`) and, at every `contract` edit (a leaf's
`ensures` gains or loses its `_ok` predicate), asks the tools what the
generator knows:

- **Callers (recall).** `bmb query impact LEAF iface` on the workspace after
  the commit, against the generator's callers of the leaf (`Tree.callers`:
  the executable definitions whose proofs read its contract). Recall is the
  share of those callers `impact` names; a missed caller counts against it.
  Definitions `impact` names beyond them are reported, not counted against.
- **Verdict (accuracy).** `bmb weaken OLD NEW` on the leaf's unit before and
  after the commit: the generator's answer is `weakened` when the predicate
  is dropped (the caller loses a fact) and a compatible verdict (`refined`,
  `compatible`) when it is added. `undecided` is a failure.

H-COMPAT is confirmed by recall 100% and accuracy 100% (ADR-0078 §1). Uses
$BMB or target/debug/bmb. Standard library only.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import history  # noqa: E402

BMB = os.environ.get("BMB", os.path.join(ROOT, "target", "debug", "bmb"))


def bmb(*args):
    return subprocess.run([BMB, *args], capture_output=True, text=True)


def impact(src, path):
    files = sorted(os.path.join(src, f) for f in os.listdir(src) if f.endswith(".bmb"))
    out = bmb("query", "impact", path, "iface", "--", *files).stdout
    found = set()
    for line in out.splitlines():
        r = json.loads(line)
        if "path" in r and not r.get("summary") and r["path"] != path:
            found.add(r["path"])
    return found


def verdict(old_dir, new_dir, path):
    out = bmb("weaken", old_dir, new_dir).stdout
    for line in out.splitlines():
        r = json.loads(line)
        if r.get("def") == path:
            return r.get("verdict")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("history")
    ap.add_argument("--upto", type=int)
    ap.add_argument("--out")
    ap.add_argument("--write")
    a = ap.parse_args(argv)
    header, commits = history.load(a.history)
    work = tempfile.mkdtemp(prefix="bcb-compat-")
    rows = []
    try:
        old, new = os.path.join(work, "old"), os.path.join(work, "new")
        rust = os.path.join(work, "rust")
        prev = None
        for k, tree, changed in history.replay(header, commits, a.upto):
            if k == 0:
                history.write_tree(tree, new, rust)
                prev = {u: tree.text[("bmb", u)] for u in range(tree.n_units)}
                continue
            # The workspace before this commit is `old`, after it `new`.
            if os.path.isdir(old):
                shutil.rmtree(old)
            shutil.copytree(new, old)
            history.write_tree(tree, new, rust, units=changed)
            edits = [e for e in commits[k - 1]["edits"] if e["op"] == "contract"]
            for e in edits:
                u, leaf = e["unit"], e["def"]
                path = f"m{u}::{leaf}"
                truth = {f"m{v}::{n}" for v, n in tree.callers(u, leaf)}
                named = impact(os.path.join(new, "src"), path)
                want = "weakened" if e["set"]["post"] is False else "compatible"
                got = verdict(os.path.join(old, "src"), os.path.join(new, "src"), path)
                ok = got == "weakened" if want == "weakened" else got in ("refined", "compatible", "same")
                rows.append({
                    "k": k, "def": path, "post": e["set"]["post"], "callers": sorted(truth),
                    "missed": sorted(truth - named), "extra": sorted(named - truth),
                    "verdict": got, "expected": want, "verdict_ok": ok,
                })
            prev = {u: tree.text[("bmb", u)] for u in range(tree.n_units)}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    callers = sum(len(r["callers"]) for r in rows)
    missed = sum(len(r["missed"]) for r in rows)
    extra = sum(len(r["extra"]) for r in rows)
    right = sum(r["verdict_ok"] for r in rows)
    undecided = sum(r["verdict"] == "undecided" for r in rows)
    summary = {
        "summary": True, "history": os.path.basename(a.history), "profile": header["profile"],
        "defs": header["defs"], "commits": a.upto or header["commits"], "contract_edits": len(rows),
        "callers": callers, "missed": missed, "recall": (callers - missed) / callers if callers else None,
        "extra": extra, "verdicts_right": right, "undecided": undecided,
        "accuracy": right / len(rows) if rows else None,
    }
    if a.out:
        with open(a.out, "w") as f:
            for r in rows + [summary]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    text = report(summary, rows)
    if a.write:
        with open(a.write, "w") as f:
            f.write(text)
    print(text)
    return 0 if missed == 0 and right == len(rows) else 1


def report(s, rows):
    rec = f"{s['recall']:.1%}" if s["recall"] is not None else "—"
    acc = f"{s['accuracy']:.1%}" if s["accuracy"] is not None else "—"
    lines = [
        "# H-COMPAT: caller recall and verdict accuracy", "",
        f"- History `{s['history']}` (profile {s['profile']}, {s['defs']} definitions, {s['commits']} commits), {s['contract_edits']} contract edits",
        f"- {s['callers']} callers (the generator's ground truth), {s['missed']} missed by `impact`: **recall {rec}**. {s['extra']} named beyond the ground truth",
        f"- Edits where the `bmb weaken` verdict equals the generator's ground truth: {s['verdicts_right']}/{s['contract_edits']}: **accuracy {acc}** ({s['undecided']} undecided, counted as failures)",
        "", "Generated by `python3 bench/bcb/compat.py HISTORY --out .. --write ..`.",
    ]
    bad = [r for r in rows if r["missed"] or not r["verdict_ok"]]
    if bad:
        lines += ["", "| Commit | Definition | Missed callers | Verdict | Expected |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {r['k']} | `{r['def']}` | {', '.join(r['missed']) or '—'} | {r['verdict']} | {r['expected']} |" for r in bad]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
