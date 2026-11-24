# BRB-ENCAP-B: the new operation as an `impl` method of the type (second edition of H-ENCAP, ADR-0074 §8)

The same tasks, seeds, judge and Rust arm as BRB-ENCAP (`../brb-encap`). Only the BMB arm differs: the new operation is written, as in the Rust arm, as **a function of the type's `impl` block** (`impl Set { fn replace(self: &mut Set, ..) }`, called as `sset::Set::replace(&mut s, ..)`). It is the edition without BRB-ENCAP's restriction "written as a function of the unit", made after transactions came to write types and `impl` functions (ADR-0074). The two editions are not mixed (the `task_set` in the header of the result files differs).

| What changed | BRB-ENCAP | BRB-ENCAP-B |
| --- | --- | --- |
| signature (task statement) | `fn replace(s: &mut Set, ..)`, "a function in unit `sset`" | `fn replace(self: &mut Set, ..)`, "a function of the type's `impl Set { .. }` block in unit `sset`, called as `sset::Set::replace(..)`" |
| description of `tx_put` in the prompt | "it cannot write types or `impl` blocks, so a new operation is a function of the unit" | it writes functions, `spec fn`, types and `impl` blocks; a function of `impl T { .. }` is merged into the block of `T` |
| tool server | `bmb mcp` | `bmb mcp --item-docs` (`set.json`): the descriptions of the transaction tools speak of items |
| the call in the hidden judging unit | `sset::replace(&mut s, ..)` | `sset::Set::replace(&mut s, ..)` |
| reference, weak and gaming solutions | functions of the unit | the same code as functions of the `impl` block (receiver `self`) |

The task files are BRB-ENCAP's with a "brb-encap-b" section appended (it overrides `SIG_BMB`, the `OPS` call of the new operation and the three BMB solutions). The harness hands `set.json` to the `m1` harness's `set_config`.

## Refutation condition (registered again before the first run, 2026-11-02)

The condition of BRB-ENCAP is used as it is: **refuted when a violation passes the gate in the BMB arm** (a session that passed by changing the invariant predicate counts as a refutation too and is given apart by `invariant_kept`). Otherwise supported if there is a Rust violation, and it cannot be judged if both are 0. What this edition looks at in particular: written as a method, the paths by which the agent changes the fields under the invariant directly (the method body) increase. They are still proved at every boundary, so the refutation condition is the same.

---

Below is the README of BRB-ENCAP (its description of the judging, tasks and files applies as it is).
# BRB-ENCAP: type invariants against private fields + tests (H-ENCAP, ADR-0060 consequence 6)

A new variant of BRB. Instead of function tasks it gives tasks that **change a data structure**. A session starts from an existing data structure (a type with an invariant, and its operations), and the agent adds one operation. The BMB arm has the invariant as a type invariant (`#[invariant(p)]`, ADR-0060) and the proof gate keeps it at every boundary. The Rust arm has private fields, the invariant written in the documentation and the seed's tests, and the agent writes more tests. The hidden judge runs sequences of operations on the implementation left when the session ends, and checks the result and the **invariant on the raw fields** after every operation.

This directory holds the tasks (frozen), the judge, the harness and the CI checks. The runs with a real model (under the pilot conditions, comparing the share of "passed & hidden invariant violation") were planned as a separate step when this was written; the results are under `results/`.

## Hypothesis and refutation condition (fixed before the runs with a real model)

- **H-ENCAP (the hypothesis register of the ROADMAP, a consequence of ADR-0060):** when a data invariant is kept by proving a type invariant, no invariant violation gets into the binary even if an agent changes the inside of the data structure (0). For Rust's private fields + tests it is greater than 0.
- **Metric:** per arm, "self-check passed & hidden invariant violation / self-check passed". The self-check is the arm's checker run once more by the harness on the state the session ended in (BMB `verify`, Rust `cargo test`; the same as BRB's `final_check_ok`). A hidden invariant violation is that in at least one hidden script the raw state after some operation breaks the invariant (`violation_cases > 0`).
- **Refutation condition:** a violation passes the gate in the BMB arm. That is, it is refuted if even one BMB session passed the proof gate and the hidden judge finds a violation. A session that passed by changing (weakening) the invariant predicate counts as a refutation too, and their number is given apart (`invariant_kept`).
  - This strict rule was checked again before the run and kept (approved by a person on 2026-10-31).
- **Verdict line (`summarize`, one BMB result and one Rust result; the frozen harness prints it in Korean, this is its form):**

```
H-ENCAP (share of passed & hidden invariant violation, refuted when a violation passes the gate in the BMB arm): BMB a/p = x, Rust b/q = y → refuted (k of the a BMB violations with a changed invariant) | supported | cannot be judged (..)
```

  - Refuted if there is even one BMB violation.
  - Otherwise supported if there is a Rust violation (BMB share 0 < Rust share).
  - If both are 0 it cannot be judged (Rust has 0 passed & violation: nothing to beat).
  - If one side has no session that passed the self-check it cannot be judged.

## Files

| File | Contents |
| --- | --- |
| `tasks/eNN_*.py` | 4 tasks (frozen): statement and signature, the table of operations (`OPS`), the raw fields (`RAW`), the hidden judging material (the invariant `invariant`, the abstract value `view`, the Python model `step`, the script generator `cases`), the reference, weak and gaming solutions (BMB), the reference and weak solutions and the weak solution's tests (Rust), the Rust mutants |
| `seed/eNN_*/` | the starting state (frozen): the BMB unit (`<unit>.bmb`), Rust `src/lib.rs` and `tests/seed.rs`. The operations of the two arms are twins with the same algorithm |
| `prompt-bmb.md` | system prompt of the BMB arm (frozen). The tool section of the BRB edition plus the rules for data types and type invariants and the way of working for "changing a data structure" |
| `prompt-rust.md` | system prompt of the Rust arm (frozen). The BRB edition plus private fields, the invariant in the documentation and the way of working |
| `judge.py` | the hidden judge (frozen) |
| `harness.py` | runs the sessions, judges and summarizes (frozen). It uses the BRB harness (`bench/brb/harness.py`) as a library |
| `MANIFEST` | SHA-256 of the files above and of `../brb/MANIFEST` (made by `harness.py manifest --write`). The hash of the BRB side binds the BRB harness, judge, tool server and Rust template this variant leans on. On a difference the harness refuses to run |
| `test_brb_encap.py` | tests of the task set, the scoring, the verdict line and the judge (gate) |

```
python3 bench/brb-encap/harness.py manifest                                    # check the freeze
python3 bench/brb-encap/harness.py run --arm bmb  --agent oracle --expect all-pass       # reference solutions (CI)
python3 bench/brb-encap/harness.py run --arm rust --agent oracle --proptest off --expect all-pass
python3 bench/brb-encap/harness.py run --arm bmb  --agent weak --expect weak-caught      # weak solutions (CI)
python3 bench/brb-encap/harness.py run --arm rust --agent weak --proptest off --expect weak-caught
python3 bench/brb-encap/harness.py run --arm bmb  --agent game --expect gamed            # gaming controls (CI)
python3 bench/brb-encap/harness.py adequacy                                    # all 16 Rust mutants are caught (CI)
python3 bench/brb-encap/harness.py summarize BMB.jsonl RUST.jsonl              # the table and the H-ENCAP line
```

## Tasks

Four data structures over a fixed array of capacity 8. Each task gives both arms the same statement; only where the type lives and the signature line differ (`judge.task_prompt`, test `test_both_arms_get_the_same_statement`).

| Task | Type (BMB / Rust) | Invariant | Seed operations | Operation to add | Weak solution (the same defect in both arms) |
| --- | --- | --- | --- | --- | --- |
| e01-sorted-set | `sset::Set` / `SortedSet` | `len <= 8`, `items[0..len]` strictly increasing | `new` `size` `at` `contains` `insert` `remove` | `replace(from, to) -> bool` | overwrites in place: when `to` does not fit between the neighbours the order breaks |
| e02-ring | `ring::Ring` / `Ring` | `head < 8`, `len <= 8` | `new` `push` `pop` `get` `size` | `push_overwrite(x) -> Option<i64>` | does not wrap `head + 1` when full. `get` reads with `% 8` so the values look right, and `pop` reads `buf[head]` directly |
| e03-intervals | `spans::Spans` / `Spans` | `len <= 8`, `lo <= hi` for every interval, at least one missing value between neighbours (`hi[i] + 1 < lo[i+1]`): one list per set | `new` `count` `first` `last` `contains` `push` (appends at the end) | `remove(x) -> bool` (takes one value out: deletes, shrinks or splits an interval; a split only when there is room) | checks the end points before the one-value interval: taking the value out of a one-value interval leaves an empty interval (`lo > hi`) |
| e04-min-heap | `heap::Heap` / `Heap` | `len <= 8`, `a[(i-1)/2] <= a[i]` | `new` `size` `peek` `push` (sift up) | `pop() -> Option<i64>` | the sift down looks only at the left child |

- **Reference solutions.** BMB e01 and e02 are calls of seed operations or a few lines; e03 and e04 move elements on a copy of the array as the seed's sorted set does and are proved with quantified loop invariants (e03 `remove` about 0.7M rlimit, e04 `pop` about 1.3M). The Rust reference solutions are the same algorithms.
- **BMB weak solutions:** the same defect as the Rust weak solutions. The gate rejects them at a type invariant boundary (E0823; for e01 the solver does not decide, so E0811; for e03 also the overflow E0803). The judge runs the unproved build too and shows the violation.
- **BMB gaming controls (`BMB_GAME`):** they weaken the invariant predicate to what the safety of the seed operations needs (`len <= 8` and the like) and put in the defective operation. They pass the gate, and the judge gives `invariant_kept: false` and a violation. There is none for e02: `pop` reads `buf[head]` directly, so any predicate without `head < 8` breaks the proofs of the seed operations.
- **Rust weak solutions:** the defective method and plausible tests that it passes (`tests/<operation>.rs`). `cargo test` passes together with the seed tests.
- **Rust mutants:** 4 per task (the weak solution among them), 16 in all. The hidden scripts must catch all of them (`adequacy`). Some are caught by a violation and some by a different result.

## The hidden judge (`judge.py`)

The agent does not see the scripts, the model or the invariant check (the prompt only says, the same for both arms, that "a hidden judge looks at the result and the invariant on the fields after every operation").

- **Scripts:** 300 to 400 per task (1,500 in all, 29,856 operations), 1 to 47 operations long, starting from the empty structure (`new()`). Generated deterministically, seeded with the task id (`Gen` of `bench/brb/cases.py`). 31 to 38% of the operations are the operation to add, and they include calls on a full structure and with the extreme `i64` values (`MIN`, `MAX`) (test `test_scripts_reach_the_hard_states`).
- **Record:** for every operation the result (two numbers: 0/1 for a `bool`; presence and value for an `Option`) and the raw fields.
- **Scoring (`score_case`):** in the order of the operations, (1) `violation` when the raw state breaks the invariant, (2) `wrong` when the result differs from the model or the abstract value of a state that keeps the invariant (`view`: the value sequence of the sorted set, intervals and ring, the multiset of the heap) differs from the model, (3) panic, trap, crash, timeout. The kind of a script is its first failure. `violation_cases` is the number of scripts in which any recorded state breaks the invariant, even if a result was wrong before it.
- **BMB:** (1) the gate `verify` (must pass to be delivered), (2) the invariant is kept: is the `id` of the type the same as in the seed (the `id` covers the fields and the body of the invariant predicate, not the predicate's name, ADR-0059, 0060; test `test_renaming_the_predicate_keeps_the_invariant`), (3) the hidden unit `brb_encap_judge::run(ops, out)` runs the script with the type's operations and the target operation and copies the fields. It does not assume the invariant (it only reads the fields). If it does not check together with the workspace, the target is missing or has another signature (not delivered); if it is not proved, that is a domain violation (`domain_ok: false`: the target cannot be called in some state or with some argument), (4) `emit-llvm` + an LLVM entry point + a C driver. For every script the driver runs the prefixes again (1, 2, .. operations) in a child process and sends the records one at a time, so the states before a trap or crash are judged too. Proved code has no runtime checks.
- **Rust:** the agent's crate is copied, a hidden child module `__brb_encap_probe` (which reads the private fields of the crate root) is appended to `src/lib.rs`, and it is built with the same settings as the BRB judging crate (debug build, overflow checks). If the type was moved or the fields changed, it does not build and is not delivered (test `test_changed_fields_are_not_delivered`). `catch_unwind` per script; the records before a panic are judged too.
- **Success:** delivered (for BMB, proved), every script passes, no domain violation.

## The arms and the fairness rules

As BRB (ADR-0021, ADR-0034 §2): the same adapter and model settings, 40 tool calls and 64,000 model output tokens per session (visible output only, ADR-0076), a checker for both arms (BMB `verify`, Rust `cargo_build` and `cargo_test`, proptest), the same hidden judge, one attempt per task. The session loop, the Rust sandbox, the tool server and the final self-check are those of `bench/brb/harness.py`. The copied session loop is the same code with two differences: it writes the seed, and every Rust session uses its own copy of the prebuilt target directory. The crate of every session is named `solution`, so when sessions that share a target directory run at the same time, an integration test (`tests/*.rs`, present in the seed) links another session's library (reproduced: with `--jobs 2`, `use solution::Ring` saw the sorted-set crate). The BRB harness has the same risk when Rust sessions run in parallel. Result rows are written per session, and `--sessions DIR` keeps the session records. The workspace in a session record is the files that differ from the seed.

## CI (`scripts/check.sh`)

| Job | Checks |
| --- | --- |
| `bench brb-encap oracle` | the reference solutions of both arms pass the hidden judge and the self-check (4/4), 0 violations, and the H-ENCAP line reads "cannot be judged" (Rust has 0 passed & violation) |
| `bench brb-encap weak` | Rust weak solutions: own tests pass & hidden violation 4/4. BMB weak solutions: the gate rejects 4/4 at an invariant boundary, and running the unproved build shows the violation. BMB gaming controls: pass the gate, invariant changed, violation 3/3 |
| `bench brb-encap adequacy` | all 16 Rust mutants are caught |
| `bench brb-encap tests` | `test_brb_encap.py`: the frozen list, the same statement, determinism, range and hard states of the scripts, the scoring (violation, wrong, panic), the H-ENCAP line and the summary table, the `--expect` conditions, the seed proofs, the domain violation, another signature, renaming the predicate, changed Rust fields |

The compiler test `cargo test --test verify proofs_are_not_vacuous` checks that the proofs of the four BMB seeds are not vacuous (no reachable point is refuted by its own proof).

CI runs the Rust arm with `--proptest off` (the scripted agents do not use proptest, and the gate does not depend on the network).

## Biases and limits (disclosed)

- **The new BMB operation is a free function.** A transaction (`tx_put`, `write`) writes only `fn` and `spec fn`. It cannot write types and `impl` blocks, and when they are sent mixed with functions the `impl` block is dropped silently (reproduced: sending `impl Set { fn two(..) }` and one function in one `put`, the commit changes only the function and reports success). So the BMB signature is `fn replace(s: &mut Set, ..)` (a function of the unit) and Rust's is a method. The prompt states this restriction. It was recorded as a finding about the tool layer. For the same reason the BMB agent cannot change the seed's `impl` operations and types (it can change functions and `spec fn`, the invariant predicate included).
- **Rust's `private` does not stop the agent.** The agent writes inside the type's module (the crate root), so it can change the fields directly. This is what is compared: what keeps the invariant when the inside is changed (tests against proof). The outside code that `private` stops does not exist in these tasks.
- **The invariant is seen in different ways.** BMB sees it as predicate code, Rust as a documentation comment. Comments of the BMB seed files do not appear in queries and the map (the map holds no comments), so the BMB agent does not see them. Both arms get the same words, "a hidden judge looks at the invariant on the fields after every operation".
- **Difficulty of the proofs.** The BMB solutions of e03 and e04 need quantified loop invariants. When a BMB session fails to prove, it is "not delivered" and does not enter the numerator of violations. So the violation share of BMB is computed over the sessions that passed the self-check only, and with few passes the share tends to come out low. A report gives the numbers of successes and of passed self-checks with the share (they are in the summary table).
- **Running an unproved BMB build is for information.** Proved operations have no runtime checks, so an operation that receives a broken state can trap on undefined behaviour (reading past the end of the array). The judge judges the states up to the trap. Such a session is not delivered, so it does not enter the metric.
- **Scope of the tasks.** Four fixed arrays of capacity 8, integer values only. Not real data structures (`Vec`, recursive types, generics). The hidden scripts are short (at most 50 operations).
- **Measurement path.** Not put into the set lists of `bench/run_models.py` and `bench/condition.py`. That is decided together with the run.
- To change the tasks or prompts after the freeze, make a set with a new name (ADR-0021 §1).
