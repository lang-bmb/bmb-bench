#!/usr/bin/env python3
"""Commit replay tasks on the port twin (ADR-0104: H-TASK).

    port_replay.py [--set NAME] make COMMIT    write the set's t*.json and h*.json
                                               for that commit
    port_replay.py [--set NAME] check          the committed tasks are what `make`
                                               writes for their commit
    port_replay.py [--set NAME] supply COMMIT  the candidates
    port_replay.py sources COMMIT              print the table `SOURCES` for that
                                               commit

A task takes one thing a commit of stage0's history added, undoes it on
both sides of the twin, and asks for it with what a developer had then:
the commit's subject, the rule as the documentation states it, and
examples. The hidden judge is the corpus the history wrote for it.

What is replayed here is a diagnostic: the commit that first reported a
code. Undoing it is mechanical where each side reports the code in one
statement (`self.diags.push(Diag::new("E0250", ..))`, `self.c.help("E0250",
..)`): the statement goes, the code around it stays, so both sides still
build and the program accepts what the rule rejects. A set whose `sites` is `every` (`port_sets.py`) also takes
the codes reported in several places, where every place is such a statement
on both sides: all of them go. A task then has

    setup    the tool calls that remove the statement (`pair.py` applies
             them before the session)
    oracle   the calls that put it back
    cases    `check` on every file of `tests/check/err` whose expected
             output has the code
    scope    "any": finding where the rule belongs is the task
    weak     doing nothing (the rule is still missing), and the oracle with
             a change of what every diagnostic prints

The targets are chosen as in `port_tasks.py`: the codes that meet the rule
in sorted order, a seeded shuffle, at most `PER_FILE` per Rust file. The
seed and the counts are the set's (`port_sets.py`); a set that avoids
another takes no code the other has a task or a step about. Where the
candidates do not reach both counts, the set says which is filled first
(`first`): the single replays, or the histories.
`EXCLUDE` names the codes whose undone state does not build or prove, or
whose corpus does not tell the two states apart, with the reason.
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.append(os.path.join(ROOT, "bench"))
import lang_bmb  # noqa: E402
sys.path.insert(0, HERE)
import index  # noqa: E402
import port_change as ch  # noqa: E402
import port_sets  # noqa: E402

PER_FILE = 12
CORPUS = os.path.join("tests", "check", "err")
EXAMPLES = 2

PROMPT = ("`bmb check` does not report the diagnostic {code} yet: {doc}. It came with the commit \"{subject}\". "
          "Implement it. Examples of what `bmb check` must print (one JSON line per diagnostic; the path in "
          "`file` is the one given on the command line), each after the source line it points at:\n\n{examples}\n\n"
          "Everything else the program prints must stay as it is.")

# The commit that first had each code in `compiler/src` (`sources`).
SOURCES = {
    'E0101': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0102': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0103': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0104': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0105': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0106': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0107': ('864b9afea', 'Nesting limits for JSON and the parser (1A-11), linear JSON strings (1D-16)'),
    'E0108': ('bd65ee653', '2N-02: bit operations and literal bases (ADR-0048 §2-§5)'),
    'E0109': ('04d8f4878', 'T2-03: f64 (ADR-0061 F2-F7), checkpoint at session handoff'),
    'E0201': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0202': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0203': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0204': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0205': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0206': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0207': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0208': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0209': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0210': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0211': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0212': ('12f4a94ba', '2C-02: integer conversions — T::try_from(x).unwrap() with the E0815 range obligation, .ok() as Option<T>, print_u64'),
    'E0213': ('12f4a94ba', '2C-02: integer conversions — T::try_from(x).unwrap() with the E0815 range obligation, .ok() as Option<T>, print_u64'),
    'E0214': ('53e50f25c', '2V-15: `use` is rewritten to full paths by `bmb fix` (E0214)'),
    'E0215': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
    'E0216': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
    'E0217': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
    'E0218': ('0ac7a430a', '2G-02: the Vec surface in the checker and move checking (ADR-0031 §1, §2, §7)'),
    'E0219': ('0ac7a430a', '2G-02: the Vec surface in the checker and move checking (ADR-0031 §1, §2, §7)'),
    'E0220': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0221': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0222': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0223': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0224': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0225': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0226': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0227': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0228': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0229': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0230': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0231': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0232': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0233': ('58573af29', '2B-04d: Rust habits around data types, with mechanical fixes (E0220-E0233)'),
    'E0234': ('d0b04a992', '2S-02 (part): u8, byte literals, print_bytes and the proved bytes library'),
    'E0235': ('61304be45', '2T-07a: user traits, impls, bounds and static trait calls'),
    'E0236': ('61304be45', '2T-07a: user traits, impls, bounds and static trait calls'),
    'E0237': ('2f4b09b4a', '2T-01: generic functions and data types, proved once, monomorphized'),
    'E0238': ('870b70497', '2O-01: Box<T> through checker, moves, prover and code generation'),
    'E0239': ('6e5d2a9d0', '2O-04: std::mem::replace and swap, E0239, type parameters without Copy'),
    'E0240': ('f7ddf8e47', '2T-03: where clauses to the normal form; impl context in definition hashes'),
    'E0241': ('76edfb6f6', '2K-01e: the ? operator, encoded as its match expansion (ADR-0049 §1, §3)'),
    'E0242': ('086bfcd4a', 'T1-48 (ADR-0063), 2O-07 (ADR-0081), 2D-29: canonical query symbols; static drops at branch joins; Rust path and closure diagnostics'),
    'E0250': ('7e68041ba', '2K-01b/c: break, continue, labels and loop with a value (ADR-0049)'),
    'E0251': ('7e68041ba', '2K-01b/c: break, continue, labels and loop with a value (ADR-0049)'),
    'E0252': ('c36ed11af', '2K-01d: range for, encoded as its while expansion (ADR-0049 §2)'),
    'E0253': ('c36ed11af', '2K-01d: range for, encoded as its while expansion (ADR-0049 §2)'),
    'E0254': ('1e649110e', 'T1-11: type invariants (ADR-0060 tasks 1-5)'),
    'E0255': ('1e649110e', 'T1-11: type invariants (ADR-0060 tasks 1-5)'),
    'E0256': ('4e338a7fc', 'T1-18: proof functions and induction (ADR-0062 P1-P5)'),
    'E0257': ('4e338a7fc', 'T1-18: proof functions and induction (ADR-0062 P1-P5)'),
    'E0258': ('4e338a7fc', 'T1-18: proof functions and induction (ADR-0062 P1-P5)'),
    'E0259': ('f3a8f3318', 'const items (ADR-0052, 2V-19: scalar constants); health fixes'),
    'E0260': ('f3a8f3318', 'const items (ADR-0052, 2V-19: scalar constants); health fixes'),
    'E0261': ('f3a8f3318', 'const items (ADR-0052, 2V-19: scalar constants); health fixes'),
    'E0262': ('4f81bfbe9', 'Closures without captures (ADR-0053, 2V-20b)'),
    'E0263': ('4f81bfbe9', 'Closures without captures (ADR-0053, 2V-20b)'),
    'E0264': ('5dccd6a94', 'Function values: E0264 and E0265 (ADR-0053, part of 2V-20d)'),
    'E0265': ('5dccd6a94', 'Function values: E0264 and E0265 (ADR-0053, part of 2V-20d)'),
    'E0301': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0302': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0303': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0304': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0305': ('2de6df771', '2B-04a: check data type declarations, names and signatures (ADR-0026)'),
    'E0306': ('20bb11ab7', '2B-04b: check data type values, fields and variants (ADR-0026)'),
    'E0307': ('20bb11ab7', '2B-04b: check data type values, fields and variants (ADR-0026)'),
    'E0308': ('2de6df771', '2B-04a: check data type declarations, names and signatures (ADR-0026)'),
    'E0309': ('2de6df771', '2B-04a: check data type declarations, names and signatures (ADR-0026)'),
    'E0310': ('2de6df771', '2B-04a: check data type declarations, names and signatures (ADR-0026)'),
    'E0311': ('61304be45', '2T-07a: user traits, impls, bounds and static trait calls'),
    'E0312': ('61304be45', '2T-07a: user traits, impls, bounds and static trait calls'),
    'E0313': ('3ef88eac5', '2M-01: method calls resolve to impl and trait functions (ADR-0051)'),
    'E0314': ('3ef88eac5', '2M-01: method calls resolve to impl and trait functions (ADR-0051)'),
    'E0315': ('61304be45', '2T-07a: user traits, impls, bounds and static trait calls'),
    'E0316': ('61304be45', '2T-07a: user traits, impls, bounds and static trait calls'),
    'E0317': ('7e68041ba', '2K-01b/c: break, continue, labels and loop with a value (ADR-0049)'),
    'E0318': ('f3a8f3318', 'const items (ADR-0052, 2V-19: scalar constants); health fixes'),
    'E0401': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0402': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0403': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0404': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0405': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0406': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0407': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0408': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0409': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0410': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0411': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0412': ('12f4a94ba', '2C-02: integer conversions — T::try_from(x).unwrap() with the E0815 range obligation, .ok() as Option<T>, print_u64'),
    'E0413': ('0ac7a430a', '2G-02: the Vec surface in the checker and move checking (ADR-0031 §1, §2, §7)'),
    'E0414': ('0ac7a430a', '2G-02: the Vec surface in the checker and move checking (ADR-0031 §1, §2, §7)'),
    'E0420': ('2de6df771', '2B-04a: check data type declarations, names and signatures (ADR-0026)'),
    'E0421': ('2de6df771', '2B-04a: check data type declarations, names and signatures (ADR-0026)'),
    'E0422': ('20bb11ab7', '2B-04b: check data type values, fields and variants (ADR-0026)'),
    'E0423': ('ec96f3abc', '2B-04c: check match (one arm per variant, declaration order, payload bindings)'),
    'E0424': ('20bb11ab7', '2B-04b: check data type values, fields and variants (ADR-0026)'),
    'E0425': ('20bb11ab7', '2B-04b: check data type values, fields and variants (ADR-0026)'),
    'E0426': ('ec96f3abc', '2B-04c: check match (one arm per variant, declaration order, payload bindings)'),
    'E0427': ('ec96f3abc', '2B-04c: check match (one arm per variant, declaration order, payload bindings)'),
    'E0428': ('2f4b09b4a', '2T-01: generic functions and data types, proved once, monomorphized'),
    'E0429': ('2f4b09b4a', '2T-01: generic functions and data types, proved once, monomorphized'),
    'E0430': ('2f4b09b4a', '2T-01: generic functions and data types, proved once, monomorphized'),
    'E0431': ('de81979c1', '2O-03d: struct-only recursion as Int handles (ADR-0056)'),
    'E0432': ('de81979c1', '2O-03d: struct-only recursion as Int handles (ADR-0056)'),
    'E0433': ('ccfe02bfd', '2O-03: owned fields and partial moves'),
    'E0434': ('b5dcab8df', 'T0-23 (ADR-0074) and 2B-13 (ADR-0080): transactions write every item; struct literal fields in declaration order'),
    'E0435': ('13fc71cc5', 'T1-26a: copy_within (ADR-0083)'),
    'E0436': ('0a9bd19a2', '4C-02 (e): interactive processes, std::process::spawn and Child'),
    'E0437': ('f3a8f3318', 'const items (ADR-0052, 2V-19: scalar constants); health fixes'),
    'E0438': ('41a331219', '진단 연쇄의 남은 것 (2V-23)'),
    'E0501': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0502': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0503': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0504': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0505': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0506': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0507': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0508': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0509': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0510': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0511': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0512': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0513': ('12f4a94ba', '2C-02: integer conversions — T::try_from(x).unwrap() with the E0815 range obligation, .ok() as Option<T>, print_u64'),
    'E0514': ('0ac7a430a', '2G-02: the Vec surface in the checker and move checking (ADR-0031 §1, §2, §7)'),
    'E0515': ('6f82b9242', '2N-03: by (bit_vector) sub-proofs and bit methods (ADR-0048 §2, §4)'),
    'E0516': ('6f82b9242', '2N-03: by (bit_vector) sub-proofs and bit methods (ADR-0048 §2, §4)'),
    'E0517': ('50a08ccd3', 'Reject a trigger that is a bound variable alone'),
    'E0601': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0602': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0603': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0604': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0605': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0606': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
    'E0607': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
    'E0608': ('0b34dc992', 'Function values (ADR-0053, 2V-20a): Fn bounds, calls, function items'),
    'E0701': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0702': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0703': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0704': ('d3949466e', 'compiler: M1 front end (parse, check, JSONL diagnostics)'),
    'E0801': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0802': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0803': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0804': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0805': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0806': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0807': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0808': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0809': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0810': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0811': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0812': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0813': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0814': ('0d8d29fff', 'compiler: proof gate (1B-02..1B-13)'),
    'E0815': ('12f4a94ba', '2C-02: integer conversions — T::try_from(x).unwrap() with the E0815 range obligation, .ok() as Option<T>, print_u64'),
    'E0816': ('38630cc43', '2G-03: Vec in the proof encoding (ADR-0031 §3)'),
    'E0817': ('61304be45', '2T-07a: user traits, impls, bounds and static trait calls'),
    'E0818': ('6f82b9242', '2N-03: by (bit_vector) sub-proofs and bit methods (ADR-0048 §2, §4)'),
    'E0819': ('4e338a7fc', 'T1-18: proof functions and induction (ADR-0062 P1-P5)'),
    'E0820': ('9bff4618c', '2U: String, &str and char (ADR-0050); 4A-04h: fix_cmd and verify through the CLI; 4C-03, 4B-03 drafts'),
    'E0823': ('1e649110e', 'T1-11: type invariants (ADR-0060 tasks 1-5)'),
    'E1001': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
    'E1002': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
    'E1003': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
    'E1004': ('5644c8404', '2F-02, 2F-03 (ADR-0030), 2E-02..2E-04 (ADR-0029): effect sets with alloc and panic; escapes with rationales and trust levels'),
}

# Codes left out, with the reason (found by `pair.py check`).
EXCLUDE = {}


def statement(text, at, chain=False):
    """(start, end) of the statement around `text[at]`: from after the
    `;` or `{` before it to its own `;`. None when what is there is not
    a statement of its own (an arm's value, a `let`, a `return`). With
    `chain`, a call whose receiver and method are on two lines
    (`self.diags` and `.push(..)` below it, as rustfmt breaks a long one)
    is a statement too."""
    depth, inside, i = 0, 0, at
    while i > 0:
        c = text[i - 1]
        if c in ")]}":
            depth += 1
        elif c in "([":
            if depth == 0:
                inside += 1
            else:
                depth -= 1
        elif c == "{":
            if depth == 0:
                break
            depth -= 1
        elif c == ";" and depth == 0:
            break
        i -= 1
    start = i
    depth, j = inside, at
    while j < len(text):
        c = text[j]
        if c == '"':
            j += 1
            while j < len(text) and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth < 0:
                return None
        elif depth == 0 and c == ",":
            return None
        elif depth == 0 and c == ";":
            break
        j += 1
    else:
        return None
    body = text[start:j + 1].strip()
    head = r"[A-Za-z_][\w.:]*(?:\s*\.\w+)*\(" if chain else r"[A-Za-z_][\w.:]*\("
    if not re.match(head, body) or re.search(r"\b(return|let|break|continue)\b|=>|\?", body.split('"')[0]):
        return None
    return start, j + 1


def without(text, code, every=False):
    """`text` without the one statement that reports `code`; None when
    the code is not in exactly one statement of its own. With `every`:
    without every statement that has the code, None when one of its
    places is not a statement of its own (`statement` with `chain`) or
    there is none."""
    hits = [m.start() for m in re.finditer(re.escape(f'"{code}"'), text)]
    if every:
        if not hits:
            return None
        while hits:
            text = without_at(text, statement(text, hits[-1], chain=True))
            if text is None:
                return None
            hits = [m.start() for m in re.finditer(re.escape(f'"{code}"'), text)]
        return text
    if len(hits) != 1:
        return None
    return without_at(text, statement(text, hits[0]))


def without_at(text, got):
    """`text` without the statement at `got` (`statement`'s answer)."""
    if got is None:
        return None
    start, end = got
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end < 0 else line_end
    if not text[line_start:start].strip() and not text[end:line_end].strip():
        # A statement on lines of its own.
        nl = text.rfind("\n", 0, start)
        return text[:max(nl, 0)] + text[line_end:] if nl >= 0 else text[line_end + 1:]
    # In a one-line block: `{ a; STMT b; }`.
    return text[:start].rstrip(" ") + (" " if text[end:end + 1] == " " else "") + text[end:].lstrip(" ")


def code_sites(texts):
    out = defaultdict(list)
    for key, t in texts.items():
        for c in set(re.findall(r'"(E\d{4})"', t)):
            out[c].append(key)
    return out


def doc_rows(commit):
    """{code: what the diagnostics page says of it}."""
    text = subprocess.run(["git", "show", f"{commit}:docs/diagnostics.md"], cwd=lang_bmb.root(), capture_output=True, text=True,
                          check=True).stdout
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"^\| (E\d{4}) \| (.*?) \|$", text, re.M)}


def corpus_of(commit):
    """{code: [(file, [(source line, expected JSON line)])]} over the
    checker's error corpus at `commit`."""
    names = subprocess.run(["git", "ls-tree", "--name-only", f"{commit}:{CORPUS}"], cwd=lang_bmb.root(), capture_output=True,
                           text=True, check=True).stdout.split()
    show = lambda f: subprocess.run(["git", "show", f"{commit}:{CORPUS}/{f}"], cwd=lang_bmb.root(), capture_output=True,  # noqa: E731
                                    text=True, check=True).stdout
    out = defaultdict(list)
    for f in sorted(n for n in names if n.endswith(".jsonl")):
        src = f[:-len(".jsonl")] + ".bmb"
        if src not in names:
            continue
        rows = [json.loads(ln) for ln in show(f).splitlines() if ln.strip()]
        lines = show(src).split("\n")
        by = defaultdict(list)
        for row in rows:
            by[row["code"]].append((lines[row["line"] - 1].strip(), json.dumps(row, ensure_ascii=False)))
        for code, ex in by.items():
            out[code].append((f"{CORPUS}/{src}", ex))
    return out


def examples_of(files):
    """Up to `EXAMPLES` examples with different messages."""
    seen, out = set(), []
    for _, ex in files:
        for src, row in ex:
            msg = json.loads(row)["message"]
            if msg in seen or len(out) == EXAMPLES:
                continue
            seen.add(msg)
            out.append(f"    {src}\n    {row}")
    return "\n\n".join(out)


def candidates(twin, commit, avoid=(), every=False):
    """[(Rust file, code, BMB definition)] of the codes each side reports
    in one statement of its own, with a documentation row and a corpus.
    With `every` (a set whose `sites` is `every`): the codes every place
    of which, on both sides, is a statement of its own, however many
    places there are; the two other fields are then the first Rust file
    and the lists of the files and the definitions."""
    docs, corpus = doc_rows(commit), corpus_of(commit)
    # Without the table of codes each side has (`diag.rs`, `diag::codes`).
    r_sites = code_sites({f: t for f, t in twin.files.items() if f in twin.targets and f != "diag.rs"})
    b_sites = code_sites({p: t for p, t in twin.bf.items() if p != "diag::codes"})
    out = []
    for code in sorted(set(r_sites) & set(b_sites)):
        if code in EXCLUDE or code not in SOURCES or code not in docs or code not in corpus:
            continue
        if code.lower() in avoid:
            continue
        if every:
            fs, ps = sorted(r_sites[code]), sorted(b_sites[code])
            if all(without(twin.files[f], code, True) is not None for f in fs) and \
                    all(without(twin.b[p], code, True) is not None for p in ps):
                out.append((fs[0], code, (fs, ps)))
            continue
        if len(r_sites[code]) != 1 or len(b_sites[code]) != 1:
            continue
        f, p = r_sites[code][0], b_sites[code][0]
        if without(twin.files[f], code) is None or without(twin.b[p], code) is None:
            continue
        out.append((f, code, p))
    return out, docs, corpus


class State:
    """The two sides with the statements of some codes removed."""

    def __init__(self, twin, sites, every=False):
        self.twin, self.sites, self.every = twin, sites, every  # sites: {code: ([Rust file], [BMB definition])}

    def rust(self, f, gone):
        text = self.twin.files[f]
        for code in sorted(c for c in gone if f in self.sites[c][0]):
            text = without(text, code, self.every)
        return text

    def bmb(self, p, gone):
        text = self.twin.b[p]
        for code in sorted(c for c in gone if p in self.sites[c][1]):
            text = without(text, code, self.every)
        return text

    def calls(self, before, after):
        """The tool calls of each arm that take the state without the
        codes `before` to the state without the codes `after`."""
        moved = set(before) ^ set(after)
        rust = []
        for f in sorted({f for c in moved for f in self.sites[c][0]}):
            rust += [["edit_file", {"path": "src/" + f, "old": o, "new": n}]
                     for o, n in ch.edits_between(self.rust(f, before), self.rust(f, after))]
        units = defaultdict(dict)
        for p in sorted({p for c in moved for p in self.sites[c][1]}):
            units[ch.unit_of(p)][p] = self.bmb(p, after)
        bmb = [["write", {"unit": u, "code": ch.bmb_code(sorted(texts), texts, self.twin.heads)}]
               for u, texts in sorted(units.items())]
        return {"rust": rust, "bmb": bmb}


def case(src):
    return {"name": "replay-" + os.path.basename(src)[:-4], "args": ["check"], "files": [src]}


def prompt_of(code, docs, corpus):
    return PROMPT.format(code=code, doc=docs[code], subject=SOURCES[code][1], examples=examples_of(corpus[code]))


def source_of(code):
    return {"code": code, "commit": SOURCES[code][0], "subject": SOURCES[code][1]}


def histories_of(rest, corpus, count, steps):
    """([codes of a history], the codes left): up to `count` histories
    of `steps` codes each, taken from `rest` in order. A history is the
    next codes in order that leave each other a file of its own."""
    files_of = {code: [src for src, _ in corpus[code]] for code in rest}

    def owned(codes):
        return {c: [s for s in files_of[c] if not any(s in files_of[d] for d in codes if d != c)] for c in codes}

    out = []
    while len(out) < count:
        codes = []
        for c in rest:
            if len(codes) < steps and all(owned(codes + [c]).values()):
                codes.append(c)
        if len(codes) < steps:
            break
        rest = [c for c in rest if c not in codes]
        out.append(codes)
    return out, rest, files_of, owned


def singles_of(pool, count):
    """(the codes of the single replays, the codes left): the first
    `count` of `pool`, at most `PER_FILE` per Rust file."""
    seen, picked, rest = defaultdict(int), [], []
    for f, code in pool:
        if len(picked) < count and seen[f] < PER_FILE:
            seen[f] += 1
            picked.append(code)
        else:
            rest.append(code)
    return picked, rest


def plan(pool, corpus, s):
    """(single codes, histories, files_of, owned) of the shuffled `pool`.
    The set's `first` is filled from the whole pool, the other from what
    it leaves."""
    pairs = [(f, code) for f, code, _ in pool]
    if s["first"] == "replays":
        picked, rest = singles_of(pairs, s["replays"])
        groups, _, files_of, owned = histories_of(rest, corpus, s["histories"], s["steps"])
    else:
        groups, rest, files_of, owned = histories_of([c for _, c in pairs], corpus, s["histories"], s["steps"])
        picked, _ = singles_of([(f, c) for f, c in pairs if c in rest], s["replays"])
    return picked, groups, files_of, owned


def make(commit, s):
    commit = subprocess.run(["git", "rev-parse", commit], cwd=lang_bmb.root(), capture_output=True, text=True,
                            check=True).stdout.strip()
    twin = ch.Twin(commit, port_sets.rust_files(s))
    every = s["sites"] == "every"
    pool, docs, corpus = candidates(twin, commit, port_sets.avoided(s), every)
    random.Random(f"{s['seed']}:replay").shuffle(pool)
    state = State(twin, {code: (p if every else ([f], [p])) for f, code, p in pool}, every)
    picked, groups, files_of, owned = plan(pool, corpus, s)
    STEPS = s["steps"]
    head = {"kind": "change", "fixture": s["fixture"], "commit": commit, "scope": "any"}
    spoil = lambda arm: ch.weak(arm, twin, "corpus")  # noqa: E731
    out = {}
    for code in picked:
        tid = f"t{len(out) + 1:02d}-replay-{code.lower()}"
        oracle = state.calls([code], [])
        task = {"id": tid, "family": "replay", **head, "source": source_of(code),
                "prompt": prompt_of(code, docs, corpus), "setup": state.calls([], [code]),
                "cases": [case(src) for src, _ in corpus[code]], "oracle": oracle,
                "weak": [{"fails": "corpus", "bmb": [], "rust": []},
                         {"fails": "corpus", **{arm: oracle[arm] + spoil(arm) for arm in ("bmb", "rust")}}]}
        out[tid + ".json"] = json.dumps(task, indent=1, ensure_ascii=False) + "\n"
    # Histories (ADR-0102, G5-L): `STEPS` of the remaining codes are undone
    # together and asked for one after the other in one copy of the code.
    # A step's cases are the files that show its code and no other code of
    # the history; the last step also has the files left out so.
    n = 0
    for codes in groups:
        own = owned(codes)
        n += 1
        steps, used = [], set()
        for k, code in enumerate(codes):
            srcs = own[code]
            if k == STEPS - 1:
                srcs = srcs + sorted({s for c in codes for s in files_of[c]} - {s for c in codes for s in own[c]})
            steps.append({"source": source_of(code), "prompt": prompt_of(code, docs, corpus),
                          "cases": [case(s) for s in srcs if s not in used],
                          "oracle": state.calls(codes[k:], codes[k + 1:])})
            used |= set(srcs)
        tid = f"h{n:02d}-history-{codes[0].lower()}"
        last = lambda arm: steps[-1]["oracle"][arm] + spoil(arm)  # noqa: E731
        task = {"id": tid, "family": "history", **head, "setup": state.calls([], codes), "steps": steps,
                "weak": [{"fails": "corpus", "bmb": [[] for _ in steps], "rust": [[] for _ in steps]},
                         {"fails": "corpus", **{arm: [st["oracle"][arm] for st in steps[:-1]] + [last(arm)]
                                                for arm in ("bmb", "rust")}}]}
        out[tid + ".json"] = json.dumps(task, indent=1, ensure_ascii=False) + "\n"
    return out


def cmd_supply(a):
    """The codes that meet the rule (after the avoided ones went) per
    Rust file, and what the set's counts take of them."""
    s = port_sets.get(a.set)
    commit = subprocess.run(["git", "rev-parse", a.commit], cwd=lang_bmb.root(), capture_output=True, text=True,
                            check=True).stdout.strip()
    twin = ch.Twin(commit, port_sets.rust_files(s))
    pool, _, corpus = candidates(twin, commit, port_sets.avoided(s), s["sites"] == "every")
    per = defaultdict(int)
    for f, _, _ in pool:
        per[f] += 1
    random.Random(f"{s['seed']}:replay").shuffle(pool)
    picked, groups, _, _ = plan(pool, corpus, s)
    print(f"replay: {len(pool)} codes ({', '.join(f'{f} {n}' for f, n in sorted(per.items()))}); "
          f"{len(groups)} histories of {s['steps']} ({s['histories']} asked), {len(picked)} single replays "
          f"({s['replays']} asked), {len(pool) - len(picked) - s['steps'] * len(groups)} codes left")


def cmd_make(a):
    s = port_sets.get(a.set)
    OUT = port_sets.out_dir(s)
    files = make(a.commit, s)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if re.fullmatch(r"[th]\d\d-.*\.json", f):
            os.remove(os.path.join(OUT, f))
    for name, text in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as h:
            h.write(text)
    print(f"wrote {len(files)} tasks to {os.path.relpath(OUT, ROOT)}")


def cmd_check(a):
    s = port_sets.get(a.set)
    OUT = port_sets.out_dir(s)
    have = {f: open(os.path.join(OUT, f), encoding="utf-8").read() for f in sorted(os.listdir(OUT))
            if re.fullmatch(r"[th]\d\d-.*\.json", f)}
    if not have:
        sys.exit("no tasks")
    commits = {json.loads(t)["commit"] for t in have.values()}
    if len(commits) != 1:
        sys.exit(f"tasks of several commits: {sorted(commits)}")
    want = make(commits.pop(), s)
    problems = [f"{f}: differs from what `make` writes" for f in sorted(set(have) | set(want))
                if have.get(f) != want.get(f)]
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        sys.exit(1)
    print(f"ok: {len(have)} tasks are what `make` writes")


def cmd_sources(a):
    """The first commit before `a.commit` whose `compiler/src` has each
    code (needs the repository's whole history)."""
    twin = ch.Twin(subprocess.run(["git", "rev-parse", a.commit], cwd=lang_bmb.root(), capture_output=True, text=True,
                                  check=True).stdout.strip(), port_sets.rust_files(port_sets.get(a.set)))
    codes = sorted(set(code_sites(twin.files)) & set(code_sites(twin.bf)))
    print("SOURCES = {")
    for code in codes:
        r = subprocess.run(["git", "log", "--reverse", "--format=%H\t%s", f"-S\"{code}\"", a.commit, "--",
                            "compiler/src"], cwd=lang_bmb.root(), capture_output=True, text=True, check=True).stdout
        if r.strip():
            sha, subject = r.splitlines()[0].split("\t", 1)
            print(f"    {code!r}: ({sha[:9]!r}, {subject!r}),")
    print("}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    port_sets.add_argument(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("make", "sources", "supply"):
        sub.add_parser(name).add_argument("commit")
    sub.add_parser("check")
    a = ap.parse_args()
    {"make": cmd_make, "check": cmd_check, "sources": cmd_sources, "supply": cmd_supply}[a.cmd](a)


if __name__ == "__main__":
    main()
