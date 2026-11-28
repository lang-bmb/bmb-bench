#!/usr/bin/env python3
"""The fixture of the port twin at full size (`fixtures/port-full`).

    port_corpus.py make COMMIT     write fixtures/port-full/fixture.json
    port_corpus.py check           the committed fixture is what `make` writes
                                   for its commit
    port_corpus.py agree EXE..     run every case with each program (the
                                   Rust side and a build of the port) at the
                                   fixture's commit: the same bytes and exit
                                   code, and the seconds each took

The fixture lists every `.rs` file of `compiler/src` at COMMIT (all of
stage0) and a corpus: command lines both programs answer with the same
bytes. A change task is judged on it (`pair.py`). Beside the crate a change task
gets what the fixture `port` names and the files the crate's manifest names
outside the crate (the sources of its examples).

The corpus is the corpus of the fixture `port` (the front end: 78 command
lines, kept as they are) and, for the rest of the compiler, command lines of
the product's differential cases (`tests/port/cases.json` at COMMIT). Of
those cases the ones in `CASES` are taken: the compiler itself is both
sides' command, it gets one file a run, it writes only to standard output
and needs no solver. Left out, and so not judged by the corpus:

    - the cases that run several files together (the whole port in one
      run): seconds a case on a debug build, several hundred runs a check;
    - the cases that need the solver (`verify`, `examples`, `stability`,
      the lints that prove) or leave files (`emit-llvm -o`, `fix`,
      `verify --emit-smt`): the judge compares standard output and the
      exit code;
    - the cases run by a script (the MCP server's sessions, the
      workspace's plans and transactions, the unified diff, the compact
      view).

Per case `PER_CASE` input files: the files the case names at COMMIT (its
globs over the tracked files, without its `except`) of at most `MAX_BYTES`,
in sorted order, shuffled by `SEED` and the case's name. A file is given by
its path in the repository; a case runs in a copy of the tree with only the
files of the corpus.
"""
import argparse
import fnmatch
import json
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.append(os.path.join(ROOT, "bench"))
import lang_bmb  # noqa: E402

NAME = "port-full"
FILE = os.path.join(HERE, "fixtures", NAME, "fixture.json")
BASE = os.path.join(HERE, "fixtures", "port", "fixture.json")
SEED = 20261128
PER_CASE = 4
MAX_BYTES = 8192
# The differential cases taken, by component (the front end, C0 to C4, has
# the corpus of the fixture `port` besides).
CASES = [
    "tokens", "tokens-edges",                               # C1 lexer
    "parse", "parse-edges",                                 # C2 parser
    "fmt-check",                                            # C3 normal form
    "std", "lower-edges", "decls-edges",                    # C4 checker
    "map-l0", "map-l1", "map-l2", "map-all", "map-window",  # C5 map
    "smt-decls", "smt", "smt-queries",                      # C6 proof encoding (the text, no solver)
    "lowered", "layout", "dump-runtime",                    # C8 code generation
    "reads",                                                # C9 incremental
    "lint-syntax", "fix-print", "ast", "uses",              # C10 tools
]
ABOUT = ("The port twin at full size (ADR-0104, ADR-0149 decision 5): all of stage0 and the whole port, taken from the "
         "repository at the task's commit. A comprehension task shows the Rust arm the files of `rust.files` (every "
         "file of `compiler/src`; a question builds nothing). A change task gives it the whole crate, which must "
         "build, with what its build reads from outside it (`rust.beside`). `corpus`: command lines both programs "
         "answer with the same bytes (the port's differential tests); the expected output is the Rust side's at the "
         "task's commit. Written by `port_corpus.py make` for `commit`; do not edit.")


def git(*args):
    return subprocess.run(["git", *args], cwd=lang_bmb.root(), capture_output=True, text=True, check=True).stdout


def make(commit):
    commit = git("rev-parse", commit).strip()
    with open(BASE, encoding="utf-8") as h:
        base = json.load(h)
    sizes = {}
    for ln in git("ls-tree", "-r", "-l", commit).splitlines():
        meta, path = ln.split("\t", 1)
        sizes[path] = int(meta.split()[3]) if meta.split()[1] == "blob" else None
    tracked = sorted(p for p, n in sizes.items() if n is not None)
    rust = sorted(p[len("compiler/"):] for p in tracked if p.startswith("compiler/src/") and p.endswith(".rs"))
    cases = {c["name"]: c for c in json.loads(git("show", f"{commit}:tests/port/cases.json"))["cases"]}
    corpus = list(base["corpus"])
    for name in CASES:
        c = cases[name]
        if c["a"][0] != "{bmb}" or c["b"] != ["{build:stage1}", *c["a"][1:]]:
            sys.exit(f"{name}: not a case of the compiler against the port")
        inp = c["inputs"]
        if inp.get("none"):
            corpus.append({"name": name, "args": c["a"][1:]})
            continue
        if inp.get("chunk") != 1 or c["a"][-1] != "{inputs}":
            sys.exit(f"{name}: not one file a run")
        files = [p for p in tracked if any(fnmatch.fnmatch(p, g) for g in inp["files"])
                 and not any(fnmatch.fnmatch(p, g) for g in inp.get("except", [])) and sizes[p] <= MAX_BYTES]
        random.Random(f"{SEED}:{name}").shuffle(files)
        for p in sorted(files[:PER_CASE]):
            stem = os.path.splitext(p)[0].replace("tests/", "").replace("/", "-")
            corpus.append({"name": f"{name}:{stem}", "args": c["a"][1:-1], "files": [p]})
    if len({c["name"] for c in corpus}) != len(corpus):
        sys.exit("two corpus cases have one name")
    # What the crate's manifest names outside the crate (the sources of its
    # examples): `cargo test` and `cargo build --all-targets` read them.
    manifest = git("show", f"{commit}:compiler/Cargo.toml")
    outside = sorted(os.path.normpath(os.path.join("compiler", m)) for m in re.findall(r'^path = "(\.\./[^"]+)"', manifest, re.M))
    doc = {"about": ABOUT, "commit": commit, "bmb": base["bmb"],
           "rust": {**base["rust"], "files": rust, "beside": base["rust"]["beside"] + outside}, "corpus": corpus}
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def cmd_make(a):
    text = make(a.commit)
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as h:
        h.write(text)
    doc = json.loads(text)
    print(f"wrote {len(doc['corpus'])} cases and {len(doc['rust']['files'])} Rust files to {os.path.relpath(FILE, ROOT)}")


def cmd_check(a):
    with open(FILE, encoding="utf-8") as h:
        have = h.read()
    if have != make(json.loads(have)["commit"]):
        sys.exit(f"{os.path.relpath(FILE, ROOT)}: differs from what `make` writes")
    doc = json.loads(have)
    print(f"ok: {len(doc['corpus'])} cases and {len(doc['rust']['files'])} Rust files are what `make` writes")


def cmd_agree(a):
    import tempfile
    with open(FILE, encoding="utf-8") as h:
        doc = json.load(h)
    bad = 0
    with tempfile.TemporaryDirectory() as tree:
        files = sorted({f for c in doc["corpus"] for f in c.get("files", [])})
        tar = subprocess.run(["git", "archive", doc["commit"], *files], cwd=lang_bmb.root(), capture_output=True,
                             check=True).stdout
        subprocess.run(["tar", "-x", "-C", tree], input=tar, check=True)
        before = sorted(os.path.join(d, f) for d, _, fs in os.walk(tree) for f in fs)
        took = [0.0] * len(a.exe)
        for c in doc["corpus"]:
            seen = []
            for k, exe in enumerate(a.exe):
                t0 = time.perf_counter()
                r = subprocess.run([os.path.abspath(exe), *c["args"], *c.get("files", [])], capture_output=True, cwd=tree)
                took[k] += time.perf_counter() - t0
                seen.append((r.returncode, r.stdout))
            if any(x != seen[0] for x in seen):
                bad += 1
                print(f"{c['name']}: the programs differ (exit codes {[x[0] for x in seen]})")
        if sorted(os.path.join(d, f) for d, _, fs in os.walk(tree) for f in fs) != before:
            bad += 1
            print("a case left a file")
    for exe, s in zip(a.exe, took):
        print(f"{exe}: {s:.1f} s for {len(doc['corpus'])} cases")
    if bad:
        sys.exit(1)
    print(f"ok: {len(doc['corpus'])} cases, the same bytes and exit code from {len(a.exe)} programs")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("make").add_argument("commit")
    sub.add_parser("check")
    sub.add_parser("agree").add_argument("exe", nargs="+")
    a = ap.parse_args()
    {"make": cmd_make, "check": cmd_check, "agree": cmd_agree}[a.cmd](a)


if __name__ == "__main__":
    main()
