# BNB: BMB Navigation Bench (ADR-0034 G4)

The same navigation questions on the same code structure are solved in two arms, and tokens and accuracy are compared.

| Arm | Code | Tools |
| --- | --- | --- |
| `bmb` | a workspace made by `bench/m3/gen.py` | the existing tools of `bmb mcp` (`query`, `map` and others) + `answer` |
| `rust` | the Rust twin crate that `twin.py` makes from the same plan | `list_dir`, `read_file` (line range), `grep` (regular expression, several paths, context lines before and after) + `answer` |

The two arms have the same agent interface (`next_calls`, `set_tools`; as `bench/m1/harness.py`) and budget rule (40 tool calls, `answer` included). The cost is all bytes of tool responses, and tokens are ceil(bytes/4) (ADR-0021). Request bytes (tool arguments) are recorded apart. Fixed costs of a session such as the system prompt and the tool descriptions are not counted.

| File | Contents |
| --- | --- |
| `twin.py` | generator of the Rust twin. It shares `gen.Unit` (names, kinds, constants) and `gen.choose` (callees, result forms) with the BMB generation, so the definitions, the call graph, the `&mut` write paths and the io functions are the same by construction |
| `analyze.py` | analyzer of the Rust side that reads only the twin's source (it handles only this generator's fixed layout). It rebuilds the call and write edges, the contract predicates, io and the duplicate groups |
| `bnb.py` | task generation, computing the answers, the tools of both arms (the BMB arm has only `query` and `map`), the scripted oracles, session runs (a run of one arm at one size writes its results per session and resumes; `--sessions`, `--jobs`), tables |
| `tasks/` | 27 tasks (frozen). `bnb.py tasks` makes them by picking roles from the plan |
| `prompt-bmb.md`, `prompt-rust.md` | the system prompt of each arm (frozen, for real models) |
| `MANIFEST` | SHA-256 of the frozen files |
| `test_bnb.py` | gate: the freeze, determinism and locality of the twin, the file tools, and at N=100 `cargo check`, agreement of the answers and success of both oracles on everything |
| `results/` | measurement records |
| `../bnb-bounded`, `../bnb-bounded-16k` | response-window variants of the `bmb` arm (`bnb.py --set DIR`): the same tasks, `bmb mcp --bounded` and `--bounded-16k`, and their prompts |

```
python3 bench/bnb/bnb.py manifest                                   # check the freeze
python3 bench/bnb/bnb.py run --sizes 100 --check-truth --cargo-check --expect all-pass   # the same check as CI
BMB=target/release/bmb python3 bench/bnb/bnb.py run --sizes 100 1000 10000 \
    --check-truth --cargo-check --work W --out R.jsonl                # measurement
python3 bench/bnb/bnb.py table R.jsonl                              # tables
python3 bench/bnb/bnb.py run --agent openai:MODEL --arms bmb --sizes 10000 --jobs 2 --sessions S --out R.jsonl   # a real model (ADR-0066), one file per arm and size; when cut, the same command resumes
```

## BMB → Rust correspondence

| BMB | Rust twin |
| --- | --- |
| unit `mod mU { .. }`, `#[summary("..")]` | file `src/mU.rs` (module documentation `//! ..`), `pub mod mU;` in `lib.rs` |
| call `mV::f(..)` / in the same unit `f(..)` | the same notation. Other units are brought in as modules only, by `use crate::{mV, ..};` |
| `fn`, `#[effects(pure\|io)]` | `pub fn` (no effect declaration) |
| `spec fn P` | `pub fn P(..) -> bool`, documentation line `/// Predicate (specification only).` A `forall` over a slice is `.iter().all(..)` |
| `requires P(..)` | documentation line `/// Requires: \`P(..)\`.` and a `debug_assert!` on entry |
| `ensures Q(..)`, `-> (r: T)` | documentation line `/// Ensures: \`Q(..)\`.`, the result bound by `let r = ..;` and a `debug_assert!` before the return |
| `invariant`, `decreases` | a comment above the loop `// invariant: ..` (`decreases` is dropped) |
| `#[uses(..)]` | none (Rust has no opaque predicates) |
| `print_i64(e)` | `println!("{}", e)` |
| `0 - c`, `-> ()` | `-c`, return type omitted |

It passes `cargo check` (warnings as errors). The crate attribute `#![allow(unused_variables)]` is there for the predicates, which keep the BMB parameter lists.

## Tasks and answers

12 for each of the units `m1` and `m2` (direct and transitive callers, transitive callees, the impact of a contract change (itself + direct callers), functions that use a predicate in a pre- or postcondition, functions that pass on a `&mut` argument, functions a `&mut` argument reaches transitively, io functions that transitively call a leaf) and 3 over the whole (functions that reach io, 2 on duplicates). The question text is the same for both arms, and the conventions of each language are in the arm's prompt.

The answers are computed from the BMB map (`bmb query`; it reuses the harness answer kinds `kinds`, `reasons` and `list` and `closure`, with only `effects` and `duplicates` apart). `--check-truth` computes the same answers again from the Rust source with `analyze.py` and compares them per task, and also compares the whole structure (the executable call and `&mut` write edges, the contract edges (loop invariants included), the io set, the duplicate groups). Any difference fails the run.

The task roles are picked on the plan graph of N=1,000 and frozen as files. The neighbourhood of `m1` and `m2` is the same at every size from N ≥ 340 (the locality of gen.py); at N=100 the later units do not exist and some answers are smaller. The answers of the 3 whole-workspace tasks grow in proportion to N.

## Oracles

The oracle of an arm is the cheapest correct strategy found with that arm's tools. So the oracle's tokens are a lower bound of the arm's cost (a real agent spends more on searching and checking).

- `bmb`: `edges DEF in|out 64` (the transitive closure in one call), `edges DEF in 1`, `impact DEF iface`, `contracts PRED`, `effects`, `duplicates`. The `&mut` closure takes `edges X out 1` per step (a deep `edges` also gives the call and contract edges below a write).
- `rust`: it uses the layout conventions that can be learned from the first file (module = file, an item starts with `pub fn` in column 0 and ends with `}` in column 0, `use` of modules). Callers: per step a `grep 'mU::f\('` over the whole crate and a `grep` of the bare name in its own file, and a `grep` of the `^pub fn ` header lines of the matching files (once per file, remembered) to find the enclosing function. Callees: a `read_file` line range per function. Contracts: a `grep` of the `/// Requires:` and `/// Ensures:` lines. io: `grep println!` (3 lines of context before), then the closure of callers. Duplicates: a `grep` of the first body line of the target with context before and after, compared after normalization.
