# Port-twin harness (ADR-0104)

The same task is given to a BMB program and a Rust program with the same function (twins), with the same model and the same call limit (60), and is measured after the session with a hidden judge. The main field of measurement is stage0 and its BMB port (after porting phase P3), and `fixtures/stk` is a small fixture that puts the harness and the judge under the gate. There are two task sets on that field (`port_sets.py`): `port/`, the first one (components C0 to C4; it has no MANIFEST), which the sections below describe, and `gate-d/`, drawn anew at full size and frozen with a MANIFEST (its own section, near the end).

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
- **The server of the BMB arm.** `stk` uses `bmb mcp --write-tool`, the port twin `bmb mcp --write-tool --compact --bounded` (ADR-0146: a response is a window of 32,768 bytes and the description mentions the text search of bodies, `query text`. The first measurements, `3p-05a` and `3p-05b`, ran without `--bounded`: `PAIR_MCP="--write-tool --compact"`). `--compact` is ADR-0144 (the proof result is the status lines of the definitions that failed and one line with the number of proved definitions. Without the compact view the response to one write on the port is about 40 thousand tokens). `PAIR_MCP` changes it and `mcp` of the result row records it. `PAIR_COND` names a tool condition of `parity.json` instead (`port`, `port-rename`) and wins over `PAIR_MCP`; `cond` of the result row is the name of the condition that has exactly the server's flags (none for other flags and outside the port twin).
- **Gate.** `check` builds the crates of the three conditions and the BMB sources of the two conditions and compares them all with the corpus. The oracle and the weak controls run in the main condition.

## Tool parity (`parity.json`)

Twice a verdict of the twin was decided by a tool one arm lacked: text search (the first measurement) and renaming (the refactoring tasks). `parity.json` lists, operation by operation, the tools of each arm that do it, and marks every operation only one arm can do as a `gap` with its reason. It is written before a measurement is frozen, and a measurement report carries it (`parity.py table`).

- **Conditions.** `port` is the server of the port twin as measured so far (`--write-tool --compact --bounded`). `port-rename` adds `--rename-ops`: `write` then takes `rename` (a definition and every reference in one call). The Rust arm has no equal tool, so a measurement under `port-rename` reports that row as a gap in its favour. A run is made under a condition with `PAIR_COND=NAME`. Where a condition's tool changes a reference solution, the task carries the solution of that condition too (`bmb:port-rename` beside `bmb` in `oracle` and in each weak solution), and `pair.py` takes it under that condition: the `rename` tasks of `gate-d` do.
- **Check** (gate): every tool an arm has is in a row, every tool and form a row names exists, a row with an empty arm says why, and the tool lists equal the pinned ones (`parity.py pin` after the table was read against a change).
- **Gaps at present:** renaming in one call, a signature change across units in one step (Rust only), running tests (Rust only), proving (BMB only), running the program (neither).

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

## The set `gate-d`: the port twin at full size (ADR-0149 decision 5)

`gate-d/` is the task set of the next measurement. The tools of the BMB arm were changed after the results of `port/` were seen (text search, bounded responses, renaming), so the numbers of `port/` are an upper bound; this set is drawn anew: another seed, the whole compiler, and no target `port/` has a task about. It is frozen: `gate-d/MANIFEST` lists the tasks, `REVIEW.md`, the fixture and the two prompts (`port_sets.py manifest gate-d`; `scripts/manifests.py` checks it). The harness and the generators are not in the MANIFEST: a result row names the commit of this repository.

- **Field.** The fixture `fixtures/port-full/fixture.json` (`port_corpus.py`): every file of `compiler/src` (42 files, 1,699 functions and methods outside the test modules, 55 thousand lines of function text without comments) and the whole port (60 units, 3,516 functions, 75 thousand lines), at product commit `57556550`. `port/` had 16 files and 630 functions against 1,426.
- **Same generators, a row of parameters.** `port_sets.py` has, per set, the directory, the fixture, the seed, the counts and the sets it avoids; `port_tasks.py`, `port_change.py` and `port_replay.py` take `--set`. `port/` is still what they write for its row, byte for byte (the gate checks both sets).
- **No target of `port/`.** A function, a diagnostic code or a state field that a task of `port/` is named after (83 names: 34 functions and fields, 49 codes, the codes of the history steps among them) is no candidate in any family here.

| Axis | Family | Asked | Tasks | Candidates (after the targets of `port/` went) |
| --- | --- | --- | --- | --- |
| comprehension | `callers` | 10 | 10 | 196 in 22 files, 39 under the cap of 2 per file |
| | `impact` | 10 | 10 | 64 in 11 files, 19 under the cap |
| | `diag` | 10 | 10 | 49 codes in 8 files, 20 under the cap of 4 per file |
| | `state` | 10 | 10 | 10 fields (all are taken) |
| refactoring | `rename` | 12 | 12 | 596 in 32 files, 66 of them left out (below), 81 under the cap of 3 per file |
| | `swap` | 8 | 8 | 343 in 26 files, 43 left out, 46 under the cap of 2 per file |
| history | `history` (5 steps) | 12 | **8** | 44 codes: 40 go to the histories |
| replay | `replay` | 30 | **4** | the 4 codes the histories leave |

- **Short supply of replayed diagnostics.** A replay needs a diagnostic code that both sides report in statements of their own, that has a row in `docs/diagnostics.md`, and that the checker's error corpus (`tests/check/err`) shows. Of the 172 codes in the twin: 6 are on one side only, 20 have no file in that corpus (the prover's, the linter's and the build's codes: their corpora need the solver or are not `check`), 49 are targets of `port/`, 43 have a place on the Rust side that is no statement of its own (`let d = Diag::new(..)` pushed later, a `return`, an arm's value) and 10 more one on the BMB side. 44 are left. Under the rule of `port/` (one place a side) only 10 of them would be: this set takes a code however many places report it, when every place is a statement of its own, and removes them all (`sites: every` in `port_sets.py`; 33 of the 44 have several places, and 27 of the 40 history steps need more than one edit on a side). A call broken after its receiver (`self.diags` and `.push(..)` on the next line) counts as a statement here, not in `port/`.
- **Histories before single replays.** ADR-0149 asks first for enough histories for an interval on the life-cycle ratio, so the 44 codes are spent on histories first (`first: histories`): 8 histories of 5 steps (an exact interval for the median needs 6), and the 4 codes left are the single replays. The histories are not capped per Rust file (they were not in `port/`): 37 of the 44 codes are the checker's (`check.rs`), 5 the parser's, 2 the lexer's.
- **`state` at full size.** The table `STATE` of `port_tasks.py` was written by hand for the checker and the printer; five of its seven fields are tasks of `port/`. Here the fields are derived (`port_tasks.fields`): a field that exactly one structure of each side has under that name, and every use of which the text method decides (after `.field` comes a change the pattern sees, or one of the listed reading methods; a field followed by another method, by a field of its own, or by an element's method is no candidate, as is one passed on as `&mut` from deeper). 10 fields with answers of 2 to 9 functions: all ten are tasks, 3 of the parser, 3 of the proof encoding, 2 of the checker, 2 of the solver; every answer has two functions on at least one side.
- **Refactoring: generated families only, two tool conditions.** `rename` and `swap`; the hand-written families are not extended. The set is measured under `port` and under `port-rename` (`PAIR_COND`, `parity.json`). A `rename` task has the BMB reference and weak solutions of both: unit by unit under `port`, one `write` with `rename` under `port-rename`. A `swap` task has the same solution under both.
- **Targets left out, with the reason.** `port_change.left_out`: beside `EXCLUDE`, a function whose name is a word of a file the fixture puts beside the crate. The crate's manifest names three example programs outside the crate (`tests/port/*_ref.rs`, the references of the port's differential tests) that call the crate's functions; `cargo test` builds them, and the Rust arm's tools write only `src/` and `tests/`. Found by the check: the Rust reference solutions of `rename ite_val` and `swap flatten_elem_of` renamed every use in the crate and `cargo test` did not build. They are left out after the shuffle, so the other tasks kept their places.
- **Corpus of the judge.** 171 command lines: the 78 of the fixture `port` (the front end) and 93 from the product's differential cases (`tests/port/cases.json`) for the rest: tokens, parse tree, `fmt --check`, `dump std`, lowering and declarations on edge inputs, the map (L0, L1, L2, all levels, a window), the proof encoding as text (`dump smt-decls`, `smt`, `smt-queries`), `dump lowered`, `layout` and `runtime`, `reads`, the syntactic lints, `fix --print`, `ast`, `uses`; four input files a case, of at most 8 KiB, by a seeded shuffle. Taken: cases where the compiler is both sides' command, on one file, printing to standard output, with no solver. Not taken: the cases that run the whole port in one command line, those that need the solver or leave files (`verify`, `examples`, `emit-llvm -o`, `fix`), and those a script runs (the reasons are at the head of `port_corpus.py`). `port_corpus.py agree` runs every case with the Rust side and a build of the port: the same bytes and exit code from both (4.7 s with the release build, 8.5 s with the debug build the judge of the Rust arm uses, 4.9 s with the port).
- **Commit subjects.** The problem statements quote the subject of the commit that first had the code, as written, as `port/` does: 19 distinct subjects, 17 of them with the labels the project planned its work under (`2B-04a:`, `T1-18:`), none in Korean. The table `SOURCES` got the one code that is new since `port/` (E0517).
- **Check of the judge** (`pair.py check --tasks bench/twin/gate-d --jobs 2 --log L.jsonl`, release build, then the `rename` tasks of the BMB arm once more with `PAIR_COND=port-rename`). For all 72 tasks the reference solution passes in both arms (and the 12 `rename` solutions of `port-rename` pass), and every weak solution fails the check it names: 124 in each arm and 36 more under `port-rename`; 440 sessions, 8.6 hours on four cores with two sessions side by side. The first pass found the two targets now left out (above) and nothing else. The hidden judge of one change takes about 2 minutes in the BMB arm (`bmb build` of the whole port from the proof cache, then the 171 cases) and 45 to 55 seconds in the Rust arm (`cargo build`, `cargo test`, the cases on the debug build); a history is judged after each of its five steps (about 9 minutes and 80 seconds in all). `judge_s` of a row records it; it is no part of `wall_s`. The gate (`test_gate_d.py`) runs none of the change tasks: the set and its fixture are what the generators write, the MANIFEST lists them, no target is one of `port/`, the conditions pick their solutions, and two questions are answered by the oracle and missed by the weak control in both arms.
- **For a person to look at.** `gate-d/REVIEW.md`, as for `port/`: two tasks a family with the line that puts each definition into the answer. The derived `state` fields are the part no person has looked at yet.

Known biases of this set, beside those below:

- **Where the tasks are.** Histories and replays are diagnostics of the front end only (checker, parser, lexer): the full size of the code is what a session searches in, not where the change lands. The targets of comprehension and refactoring are in 8 of the 14 components (checker 14, proof encoding 12, parser 10, tools 9, solver 5, code generation 4, normal form 3, incremental 3): none in the base library, the lexer, the map, the workspace, the MCP server or the driver.
- **Replays of several places.** Most steps restore a diagnostic at several places; `port/` had one place a step. The numbers of the two sets are not comparable step by step.
- **What the corpus does not see.** The solver's answers, the generated LLVM text, the workspace, the MCP server and the driver's file-writing commands are judged by the build only (and on the Rust side by its unit tests; on the BMB side by the proofs). A refactoring there that changes behaviour and still builds passes.
- **Size and documentation.** Both arms now see the whole of their side (the Rust arm no longer sees a third of it). The documentation condition is `none`, as before.
- **Easy `state` and `diag` questions.** Most answers have two or three functions (the lower bound of the size rule).

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
python3 bench/twin/port_tasks.py --set gate-d make COMMIT          # the same three for another set (`supply COMMIT`: its candidates)
python3 bench/twin/port_corpus.py make COMMIT                      # the fixture of the set gate-d (`agree EXE..`: the programs print the same)
python3 bench/twin/port_sets.py manifest gate-d                    # its MANIFEST
BMB=target/release/bmb python3 bench/twin/pair.py check --tasks bench/twin/port   # the oracle and weak controls of every task (hours)
BMB=target/release/bmb python3 bench/twin/pair.py check --tasks bench/twin/gate-d --jobs 2 --log L.jsonl   # two sessions side by side; goes on from L.jsonl when cut
PAIR_COND=port-rename python3 bench/twin/pair.py run --tasks bench/twin/gate-d --only r01-rename-rec_valid --agent oracle   # under another tool condition
python3 bench/twin/report.py R.jsonl..                             # tables of the result rows (per axis and family)
python3 bench/twin/pair.py run --agent openai:qwen3.8-27b --out R.jsonl   # a real model (ADR-0066)
```

The cost is as in BNB. All bytes of tool responses, tokens = ceil(bytes/4) (ADR-0021). Request bytes are recorded apart.
