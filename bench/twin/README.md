# Port-twin harness (ADR-0104)

The same task is given to a BMB program and a Rust program with the same function (twins), with the same model and the same call limit (60), and is measured after the session with a hidden judge. The main field of measurement is stage0 and its BMB port (after porting phase P3), and `fixtures/stk` is a small fixture that puts the harness and the judge under the gate. Tasks and prompts are frozen when the measurement set is made from the comprehension, refactoring and replay tasks (no MANIFEST yet).

| Arm | Code | Tools |
| --- | --- | --- |
| `bmb` | a workspace made by `bmb import` | `bmb mcp --write-tool` (the official write surface of ADR-0101, `tx_*` hidden): `query`, `map`, `verify`, `build`, `write` |
| `rust` | a copy of the crate | `list_dir`, `read_file` (line range), `grep`, `write_file`, `edit_file` (changes exactly one place), `cargo_build`, `cargo_test` |

Comprehension tasks end with `answer` (definition paths `module::name`) in both arms.

## Judging

| Task kind | Success |
| --- | --- |
| `comprehend` | the set of definitions answered equals `truth` (precision and recall 1) |
| `change` | all four hold (the fourth for tasks that have `must_change`). (1) Build: for BMB `bmb build` (every obligation proved), for Rust `cargo build` and `cargo test`. (2) Corpus: for every `corpus/NAME.in` of the fixture it prints the bytes of `NAME.out` exactly, and the same for the task's `cases` (hidden tests of the new feature). (3) Scope: the definitions that changed, appeared or went are inside the task's `scope` (new definitions are allowed when `new` is true). (4) Work done: every definition of the task's `must_change` changed, appeared or went (without this, a session that changes nothing passes the first three. The rows of the measurement `3p-05a` were judged before this condition, and `report.py worked` counts it after the fact) |

Scope is decided by the source text per definition. For BMB the canonical source of the workspace (ADR-0019) is cut per definition, so it is exact. For Rust the file is cut into top-level items (`fn`, `const`, `struct` and so on, with their documentation lines), and the other lines (`use`, `mod`, macros) count as one `module::<rest>` (an approximation).

Why the identity hash (`bmb hash`, ADR-0059) is not used: an identity holds its callees by their identities. So changing the body of a callee changes the identity of every caller (in the first run of the harness, adding `vm::neg` and changing `main::step` made `main::run_line` and `main::main` come out as changed). That is not an edit of the caller.

## Fairness: documentation conditions (ADR-0118, ADR-0106)

The environment variable `PAIR_DOCS` picks the condition, and `docs` of the result row records it.

| Condition | BMB arm | Rust arm | Use |
| --- | --- | --- | --- |
| `summary` (default of `stk`) | definition summaries (`///` of the source → `#[summary]` of the canonical form, map L1) | only `///` kept, other comments removed | main condition of `stk` |
| `none` (default of the port twin) | no definition summaries | no comments | main condition of the port twin (ADR-0144: the port's summaries are Korean and the `///` of stage0 English, so they are not "the same text") |
| `all` | as `summary` | as written | control: if the difference shrinks to inside D, the claim is limited to "against Rust with documentation comments only" |

- **The same text.** The `#[summary]` of a unit is letter for letter the `//!` of the Rust module. The `///` of a BMB definition equals the `///` of the Rust item of the same name, and the Rust side may only add `Requires ..` and `Ensures ..` sentences after it (what the BMB arm reads as contracts). `spec fn` and `proof fn` get no summary. `doc_parity` checks this.
- **Scope.** Rust definition text is compared after all comments are removed, and BMB's hash does not read summaries. A definition with only its documentation changed has not changed.
- **The server of the BMB arm.** `stk` uses `bmb mcp --write-tool`, the port twin `bmb mcp --write-tool --compact --bounded` (ADR-0146: a response is a window of 32,768 bytes and the description mentions the text search of bodies, `query text`. The first measurements, `3p-05a` and `3p-05b`, ran without `--bounded`: `PAIR_MCP="--write-tool --compact"`). `--compact` is ADR-0144 (the proof result is the status lines of the definitions that failed and one line with the number of proved definitions. Without the compact view the response to one write on the port is about 40 thousand tokens). `PAIR_MCP` changes it and `mcp` of the result row records it.
- **Gate.** `check` builds the crates of the three conditions and the BMB sources of the two conditions and compares them all with the corpus. The oracle and the weak controls run in the main condition.

## The fixture `stk`

A program that executes the commands on standard input on one stack (three units `lex`, `vm`, `main`; in Rust three modules of the same names). Errors are `error LINE: WHAT`, with `depth N` at the end. The BMB side is fully proved. On the 8 corpus files (overflow, `i64::MIN`, the stack limit of 4096, whitespace and CR, bytes that are not UTF-8, empty input) the output bytes of the two sides are the same (`check` verifies this every time).

| Task | Kind | Weak control (the check that must fail) |
| --- | --- | --- |
| `c01-callers-is` | the transitive callers of `lex::is` | only the direct callers (answer) |
| `r01-rename-drop` | rename `vm::drop` to `vm::discard` | no error on an empty stack (corpus), an edit of `vm::swap` outside the scope (scope) |
| `t01-neg` | a new command `neg` (the shape of a commit replay: a problem statement + hidden tests) | wraps on overflow (corpus) |

In the first gate run the weak control "`drop` on an empty stack gives no error" passed the corpus. The corpus did not have that case, and it was added to `errors.in`. The adequacy of the hidden judge of the measurement tasks is checked the same way (do the weak controls fail).

## Comprehension tasks of the port twin (H-COMPREHEND)

The field of measurement is the components C0 to C4 of stage0 (16 files of `compiler/src`, Rust) and their port (`selfhost/`, BMB). The fixture `fixtures/port/fixture.json` points at those places of the `lang-bmb` repository, and they are taken at the task's `commit` (the workspace by `bmb import`; the Rust arm gets a `src/` with only those files). The tasks are the 24 `port/c*.json`, made by `port_tasks.py make COMMIT`. No answer is written by hand.

| Family | Question | Count | Source of the answer |
| --- | --- | --- | --- |
| `callers` | the direct callers of a function that exists under the same name on both sides | 7 | BMB: the call edges of the map. Rust: by name in the definition texts |
| `impact` | those callers up to two steps (what a change reaches first) | 5 | the same |
| `diag` | the functions that have a diagnostic code in their own body (the paths on which that diagnostic comes out) | 7 | definition texts on both sides |
| `state` | the functions that change one field of the checker's or printer's state | 5 | definition texts on both sides |

- **The answers of the two sides differ.** The port is not a line-by-line copy (630 Rust functions, 1,426 BMB ones). The same question is asked in each arm with its own names (`prompt` is per arm), and the answer is per arm too (`truth` is per arm). The unit of a definition is a function or method (`index.py`: for BMB the path of the map, for Rust `module::Type::method`).
- **How far call sites found by name can be trusted.** The Rust side has no call graph tool. So the targets are limited to functions whose name is unique on both sides, and the same method is run on the BMB side and only targets for which it agrees exactly with the edges of the map are used (the method is checked on the side where the answer is known). Of the 417 that exist once under the same name on both sides, 405 do.
- **The targets are picked by machine.** The candidates that fit a family's rule are put in order, shuffled with a fixed seed and picked from the front (up to `PER_FILE` per family for one Rust file). The rules, the candidates and the seed are in `port_tasks.py`.
- **Check.** `port_tasks.py check` (gate): the committed tasks and `REVIEW.md` equal the output of `make`, and the BMB functions of the index equal the functions of the map (1,426). `pair.py check --tasks bench/twin/port`: the oracle of the 24 tasks passes in both arms and the weak control (an answer with one definition missing) fails (about 6 minutes; the gate runs only two tasks).
- **For a person to look at.** `port/REVIEW.md`: for every family the questions of two tasks and the answers of both sides, and for every answer the line that put that definition into the answer. A person checks the sample before the first model run (a condition of the measurement).

## Refactoring tasks of the port twin (H-REFACTOR)

`port/r*.json`, made by `port_change.py make COMMIT`. For `rename` and `swap` the generator makes both the reference solution (`oracle`) and the weak solutions (`weak`). The solutions of the other two families were written by hand (`port_hand.py`: written as substitutions that must match the text of the task's commit exactly once, from which the tool calls and the scope are made. If one does not match, `make` stops).

| Family | Task | Count | Reference solution |
| --- | --- | --- | --- |
| `rename` | rename a function that exists once under the same name on both sides, and make every use follow | 10 | substitution of the word (only functions for which every occurrence of the word is the declaration or a call are picked) |
| `swap` | swap the first two parameters (after `self`) of such a function and fix every call | 6 | the argument lists of the declaration and the calls are cut by parenthesis depth and the two pieces exchanged |
| `inline` | remove a function and put its body at every call (`type_def`, `sha`) | 2 | by hand |
| `extract` | take a part of a function out into a new function and call it (`reserved_name`, `rationale_line`) | 2 | by hand |

Success is the three conditions of a `change` task (build, corpus, scope). What they mean on the port twin:

- **Build.** The BMB arm is `bmb build` (every obligation proved), and the workspace holds the proof cache of the port (`.bmb-cache`, built once per commit): a session proves only as much as it changed. With a warm cache, verifying the whole port takes 19 seconds with the release build (run it with `BMB=target/release/bmb`; with the debug build one write takes about 1 minute). The Rust arm gets the whole crate (`compiler/`, without `tests/`) and what the build reads from outside (`scripts/toolchain.env`, `lib/std`), and must pass `cargo build` and `cargo test` (the unit tests).
- **Corpus.** The 78 `corpus` entries of the fixture: command lines for which the two programs give the same bytes (`check`, `fmt`, `hash`, `dump types`, `moves`, `texts`, `lower`, `decls` and `codes` on generated programs, edge inputs and files of the run corpus). The expected output is the output and exit code of the Rust side (release) built at the task's commit. The port's differential tests show that the two sides are the same, so one reference is enough.
- **Scope.** Per function and method (`rest=True` of `index.py`: a function with its own attribute lines, the other lines as `unit::<rest>`). Summaries and comments are not text.
- **Weak solutions.** Three per task: the reference solution plus an edit of a function outside the scope (`sha256`) (must fail the scope), one with the printed characters of a diagnostic changed (must fail the corpus), and one that does nothing (must fail the work done: `must_change` is the task's scope, that is, the definitions the reference solution changes).
- **Changes across units.** `write` writes one unit at a time, and after every write the whole program must pass the check. A signature change whose call sites are in other units cannot be written in one go: the reference solution puts in the new signature under another name, moves the calls unit by unit, deletes the old one, and does the same once more to restore the name (`r12` is such a case: 6 writes). The Rust arm has no such restriction. The candidates were not narrowed to those inside one unit (narrowing would hide the cost on the BMB side).
- **Missing families.** Replacing a data structure and splitting a unit are absent. A task that moves one function to another unit (`identity::sha` → `sha256::sha`) was written down to its solution and left out: after the BMB solution every definition is proved, and `bmb build` still refuses the program.
- **Excluded targets.** `EXCLUDE` of `port_change.py`: the functions the generator's rules do not fit, with the reasons (they are removed after the shuffle, so the other tasks stay in place).
- **Documentation condition and reference solutions.** The reference solutions of the Rust arm (`old` of `edit_file`) are made for the text of the `none` condition (no comments). In other conditions they may not match.

## Replay tasks of the port twin (H-TASK and G5-L)

`port/t*.json` (22) and `port/h*.json` (4 histories), made by `port_replay.py make COMMIT`.

- **What is replayed.** The commit that first gave one diagnostic. Only diagnostics that both sides emit with one statement of their own are picked (`self.diags.push(Diag::new("E0250", ..))`, `self.c.help("E0250", ..)`). The state with that statement removed is the start of the task (`setup`: `pair.py` applies it before the session. On the BMB side it is proved once and kept in a cache per commit). The code around it stays, so both sides build, and the program accepts what that rule used to stop. There are 51 such codes on both sides.
- **Problem statement.** The subject of the commit that first added the code (`SOURCES`; `port_replay.py sources` finds it in the history), the line of the diagnostics document (`docs/diagnostics.md`), and up to two examples (one line of expected output of the corpus and the source line it points at). Both arms get the same text. The commit subjects are quoted as they were written, some of them in Korean and with the labels the project planned its work under.
- **Hidden judge.** `check` on every file of `tests/check/err` whose expected output has the code (the task's `cases`), and the corpus of the fixture. The scope is not asked (`scope: "any"`): finding where to put it is the task.
- **Weak solutions.** One that does nothing (the rule is still missing), and the reference solution with the printed characters of a diagnostic changed. Both must fail the corpus.
- **Histories (`h*`).** Five codes that the single tasks do not use are removed together and asked for one after the other. Every step is a new session and the code is as the previous step left it (G5-L of ADR-0102: follow-up changes on the same code base). The verdict of a step is the `cases` up to that step, and only the last step also looks at the corpus of the fixture (before it, the diagnostics of the later steps are still missing). The files of a step are only those without another code of that history. The result row holds the values per step (`steps`) and their sum, and success is the verdict of the last step.
- **Limits.** What was removed is one statement, so it is smaller than the real commit (the condition and the recovery code stay). The difficulty is in "where, and with which characters". The examples of the problem statement give the characters.

Known biases (stated in the measurement report):

- **Documentation condition.** The main condition `none` takes `///` away from the Rust arm. The control with commented Rust (`PAIR_DOCS=all`, Rust arm only) measures its size (ADR-0144 decision 2).
- **Compact view.** The BMB arm runs with `--compact`. Whether the compact view lowers the success rate was not measured separately.
- **Text search.** The BMB arm of the first measurement (`3p-05a`) had no text search: `diag` and `state` are questions the Rust arm reaches with one `grep`, and the BMB arm had to read definitions (sonnet 23 times and 7 times). Since ADR-0146 there is `query text` (literal, no pattern language; the `grep` of the Rust arm is a regular expression). Reported per family.
- **Size.** The Rust arm sees only the files of C0 to C4 (about 23 thousand lines of function bodies with comments removed). The port is about 30 thousand lines. Given all of stage0 (67 thousand lines), only the Rust arm would search larger code.
- **The same lineage.** Both sides were carried over by the same author (ADR-0104 decision 4).

```
python3 bench/twin/pair.py check                                   # gate (run by test_pair.py)
python3 bench/twin/port_tasks.py make COMMIT                       # make the comprehension tasks of the port twin again at that commit
python3 bench/twin/port_change.py make COMMIT                      # refactoring tasks
python3 bench/twin/port_replay.py make COMMIT                      # replay tasks and histories
BMB=target/release/bmb python3 bench/twin/pair.py check --tasks bench/twin/port   # the oracle and weak controls of every task (hours)
python3 bench/twin/report.py R.jsonl..                             # tables of the result rows (per axis and family)
python3 bench/twin/pair.py run --agent openai:qwen3.8-27b --out R.jsonl   # a real model (ADR-0066)
```

The cost is as in BNB. All bytes of tool responses, tokens = ceil(bytes/4) (ADR-0021). Request bytes are recorded apart.
