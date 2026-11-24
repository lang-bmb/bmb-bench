# BCB: BMB Cumulative-cost Bench (ADR-0040 G7 and H-AMORT, ADR-0042)

The same commit history is replayed on a BMB workspace and its Rust twin, and the CPU that checking takes is accumulated commit by commit. For BMB that is the incremental re-proof (the contract firewall, ADR-0032) and the remaining tests; for Rust, running the tests (all, selected, cached). The design and the refutation conditions registered beforehand are in ADR-0042.

| File | Contents |
| --- | --- |
| `history.py` | generates and replays histories. It edits the plan of `bench/m3/gen.py` and writes the same edit with both renderers (BMB `gen.py`, Rust `bench/bnb/twin.py`). A tree digest is recorded per commit and the replay checks it |
| `rtests.py` | the Rust tests: one `#[test]` per executable definition (`mod tests` at the end of the unit file). It calls the definition with fixed inputs that satisfy `requires` (boundary values + random values seeded by the name), and the only verdicts are the contract `debug_assert!`s of the twin and overflow and bounds panics. The large input set for the oracle (`strong_cases`) does not go into the twin |
| `rustify.py` | translator from BMB executable definitions to Rust in the twin's form (the generated subset). Every time, it checks that translating the original gives the twin byte for byte. Used to apply a mutant at the same place in both languages |
| `kills.py` | kill rates: applies W0904 mutants (`bmb mutate`) to both languages and compares the verdicts of the BMB proof, the Rust tests and the oracle tests |
| `bcb.py` | the replay harness (`run`) and the tables (`table`). Arms `rust` (R0, R1 and R2 in one replay: the build is the same and only the test selection differs), `b1` (kept cache), `b0` (a new cache at every sampled commit). Per commit it writes as JSONL the CPU (user+sys, `wait4`) and wall-clock time per command, the number of selected tests, the number of definitions R2 covers, and the definitions B1 proved again (`build --stats`). An event commit clears the caches and is measured once more (`"cold": true`) |
| `compat.py` | H-COMPAT: at every contract edit, whether `bmb query impact LEAF iface` names all the callers the generator knows (`Tree.callers`) (recall) and whether the `bmb weaken` verdict equals the ground truth (accuracy; undecided counts as a failure). `--write` gives the report |
| `test_bcb.py` | gate: determinism of the histories, reproduction of the digests, at every commit all of BMB proved and Rust `cargo check --tests` (warnings = errors), the properties of each kind of edit (a body edit leaves signature and contract unchanged), equal kills at the end of the `contract-heavy` history, edit localization (`localize.py`), the compatibility verdict (`compat.py`) |

```
python3 bench/bcb/bcb.py run H.jsonl --work W --out R.jsonl [--b0-every 50]   # measurement (arms rust,b1,b0)
python3 bench/bcb/bcb.py defects H.jsonl --work W --out D.jsonl           # planting defects
python3 bench/bcb/bcb.py table R.jsonl D.jsonl                             # tables of cumulative CPU and detection rates, and the verdict
python3 bench/bcb/kills.py --defs 1000                                     # equal kills (initial tree)
python3 bench/bcb/kills.py --history H.jsonl --at 500                      # at commit 500 of a history
python3 bench/bcb/history.py gen H.jsonl --defs 1000 --commits 1000 --profile body-heavy
python3 bench/bcb/history.py stats H.jsonl
python3 bench/bcb/history.py replay H.jsonl --bmb W/bmb --rust W/rust --upto 500
```

## Edits

| Kind | BMB | Rust twin |
| --- | --- | --- |
| `body` | the body only (constants, template, callees, result form). `#[uses]` may change with the callees' units | the same body |
| `contract` | puts an `_ok` predicate into a leaf's `ensures` or takes it out (the first time, the predicate is added) | the documentation line and the `debug_assert!` |
| `spec` | the upper bound of an `_ok` predicate | the body of the predicate function |
| `add` / `remove` | adds a leaf / deletes a leaf without callers | the same |

Profiles (`PROFILES` of `history.py`): `body-heavy`, `contract-heavy`, `body-only`. The toolchain event commits are the `events` of the header line (K·j/5), and the replay harness applies them.

## The freeze and the measurement plan

`MANIFEST` is the SHA-256 of the harness files (`bcb.py`, `history.py`, `rtests.py`, `rustify.py`, `kills.py`) and of the 8 measurement histories (`FROZEN` of `bcb.py`: 3 profiles × N=1,000 and 10,000, N=1,000 at depths 2 and 6, all with K=1,000). The history files are not committed and are made again deterministically (`manifest --histories DIR` makes and compares them). The gate checks the harness hashes.

`bcb.py suite --work W --results R` runs `SUITE` (the measurement plan) in order and writes the results to `R/<history>.<arm>.jsonl`. When interrupted, the same command continues where it stopped. A cut line is dropped. When an event commit has only its warm row, only the cold measurement is made (a repeated warm measurement would find its work already in the cache). The first commit after a resumption may still have partial work from the moment of the interruption (a partial compilation, for example). `from` of a result header line is the point of resumption. The header line also records the machine, the toolchain, the commit, the MANIFEST and the compiler's hash.

`suite` does not run on an uncommitted tree, and the first time it runs it copies the compiler to `W/bin/bmb` and uses only that copy. In the first attempt (2026-10-25) `cargo build --release` was run on the same machine during the measurement. That build could change the compiler being measured, and it competed for the CPU. So those results were thrown away and these two guards were added. During a measurement no heavy work such as compiling or the gate is done on the same machine.

Probe at N=10,000 (2026-10-25, K=5, preliminary): Rust about 19.5 seconds of CPU for a warm commit (build 5.3 + test build 14), 41 seconds for a cold one. B1 about 3.5 seconds for a warm commit, about 205 seconds for a cold one. The whole plan is about 28 hours (mostly the Rust arm at N=10,000).

## The real commands of the arms

| Arm | Per commit |
| --- | --- |
| R0, R1, R2 | `cargo build`, `cargo test --no-run` (shared), then the test executables with `--exact name..` (R0: all). R1 runs the tests of the changed units and of the units that depend on them (transitively); R2 the tests of the definitions that reach a changed definition through calls and contract checks, and the changed tests |
| B1 | `bmb build --cache C --stats S src tests driver -o exe` (the proof gate and the build are one command), running `exe` and comparing the output. The remaining tests are test functions in `tests/tU.bmb` for each `show` definition (the same inputs as the Rust tests), and `main` of `driver/bcb_main.bmb` calls those selected by the R2 rule. The expected output is computed from the plan |
| B0 | the same command with a new cache, all the remaining tests. At every `--b0-every S` commits (and at the last commit) |

## Planting defects (ADR-0042 §4)

For every commit `bcb.py defects` picks one executable definition that the commit edited (fixed seed) and makes a side branch in which one W0904 mutant of that definition (surviving mutants included) is planted in both languages. Each arm runs by its selection rule for that commit.

| Arm | Catches when |
| --- | --- |
| R0, R1, R2 | one of the selected Rust tests fails |
| B1, B0 | the proof gate fails (`proof`), or the output of a selected (B0: any) remaining test that reaches the planted definition differs from the plan's value (`B1_tests`) |

The side branch is undone before the next commit. A commit whose edits are only deletions, or that has no mutant, is `skipped`. The gate checks that a defect Rust catches always fails the proof too (the Rust tests look only at the contract) and that the selections nest.

## Test equality (ADR-0042 §4)

A mutant is killed in BMB when the definition is no longer proved, and in Rust when the test of that definition fails. When the oracle (hundreds of inputs) finds an input that violates the contract, the mutant really breaks the contract.

| Category | Meaning |
| --- | --- |
| `contract` | BMB rejects it and the oracle finds a violation too. **Equality is measured on this set**: the Rust tests must kill all of them (`gaps` = 0) |
| `annotation_only` | BMB rejects it but the contract holds. A mutation such as a loop start of 1 or a step of 2 breaks the invariant `k <= a.len()` (E0806, E0807). Tests that look only at the contract cannot tell these apart in principle. Reported apart as the part where BMB is stricter |
| `unsound` | the oracle found a violation and BMB proved it. Must be 0 (a cross-check of soundness) |
| `extra` | a Rust test killed it and BMB proved it. Must be 0 |

Measured (2026-10-25, release): of the 338 mutants of the initial tree at N=100, BMB rejects 195 (165 contract, 30 annotation only) and Rust 165; 0 gaps, unsound and extra. After 200 commits: `body-heavy`, of 424, contract 179 and Rust 179; `contract-heavy`, of 566, contract 209 and Rust 209; 0 gaps in both. Of the 3,351 of the initial tree at N=1,000: contract 1,571 and Rust 1,571, annotation only 300; 0 gaps, unsound and extra.

## Progress

- The design (ADR-0042), the history generator, the gate, `bmb verify --stats` (the set proved again).
- The Rust tests and equal kills (`rtests.py`, `rustify.py`, `kills.py`).
- The replay harness (`bcb.py`), `build --stats`.
- Planting defects (`bcb.py defects`, the detection rates of the table and condition 4).
- Next: the freeze and the measurement (registered in `results/2a14e/`).
