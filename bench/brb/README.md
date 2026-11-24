# BRB: BMB + proof against Rust + tests (ADR-0034 G5)

A comparison bench that measures premises E2 and E3 (DESIGN.md §2) directly. The same tasks are solved by the same model with the same budget in (a) BMB (proof, MCP tools) and (b) Rust (tests written by the agent, `cargo test`, proptest), and the **implementation** left when the session ends is measured by its behaviour with a hidden adversarial judge. The metrics are the hidden defect rate, total model tokens (writing + checking), tool calls and wall-clock time.

This directory holds the harness, the tasks (frozen) and the CI checks. Runs with a real model use the model environment of ADR-0066 (`openai:qwen3.8-27b` by default, `anthropic:claude-sonnet-5-5` for the cross-check). When this was written there were only pilot results (`bench/pilot/`); the official results are under `results/`. The MANIFEST was frozen again on 2026-10-30 with only the branch on the agent kind (`make_model_agent`) and the `+dirty` verdict (result files of earlier sets of the same run do not count) changed. The tasks, prompts and judging are unchanged. It was frozen again once more the same day: the only change is that a result row is written as each session ends and an interrupted run is resumed; the tasks, prompts, judging and limits are unchanged. The first official measurements (qwen, then sonnet) ran on the edition before that (`8d569693`), and the two editions' MANIFESTs differ in one line of `harness.py`. It was frozen again on 2026-11-02: `run --variant DIR` was added (BMB arm only; it uses the prompt and `set.json` of a write-surface variant such as `bench/brb-write` and records them in the row's `task_set` and `variant_manifest`), and without it a run is unchanged. The MANIFESTs of the variants that hold BRB's MANIFEST (`brb-encap`, `brb-encap-b`, `brb-effect`, `brb-write`, `brb-diff`, `brb-ast`) were written again with it (all before their first run).

| File | Contents |
| --- | --- |
| `tasks/tNN_*.py` | 24 tasks (frozen). The problem in natural language, the domain and the signature; the hidden judging material (model, case generators, Rust mutants); the reference solution and the weak control (for BMB and for Rust) |
| `prompt-bmb.md` | system prompt of the BMB arm (frozen). The language rules and tool descriptions of `bench/m1/prompt.md` as they are; only "How to work" is BRB's |
| `prompt-rust.md` | system prompt of the Rust arm (frozen) |
| `rust-template/` | the starting crate `solution` of the Rust arm (frozen). The dev-dependency `proptest =1.12.0` and `Cargo.lock` |
| `rust_tools.py` | tool server of the Rust arm (frozen): `list_files`, `read_file`, `write_file` (only `.rs` under `src/` and `tests/`), `cargo_build`, `cargo_test` |
| `judge.py` | the hidden judge (frozen) |
| `cases.py` | case generation tools (frozen). Deterministic random numbers seeded with the task id |
| `harness.py` | runs the sessions, judges and summarizes (frozen) |
| `MANIFEST` | SHA-256 of the files above. On a difference the harness refuses to run |
| `test_brb.py` | unit tests of the harness (gate) |

```
python3 bench/brb/harness.py manifest                                   # check the freeze
python3 bench/brb/harness.py run --arm bmb  --agent oracle --jobs 4     # reference solutions: 0 defects (CI)
python3 bench/brb/harness.py run --arm rust --agent oracle --jobs 4     # reference solutions: 0 defects (CI uses --proptest off)
python3 bench/brb/harness.py run --arm bmb  --agent weak --jobs 4       # weak controls: the self-check passes, the hidden judge finds the defect (CI)
python3 bench/brb/harness.py adequacy --jobs 4                          # the hidden cases kill all 96 Rust mutants (CI)
python3 bench/brb/harness.py summarize BMB.jsonl RUST.jsonl             # the table and the G5 verdict line
```

## Tasks

24 function tasks that can be solved both in the M1 subset of BMB (ADR-0016: integers, slices, `while`) and in Rust. Each task gives both arms **the same statement** (the problem and the input domain), and only the one signature line differs per language (`judge.task_prompt`, test `test_both_arms_get_the_same_statement`). The parameter types of the signatures are the same on both sides (`i64`, `u64`, `usize`, `&[i64]`, `&mut [i64]`; BMB has `-> (r: T)`, Rust `pub fn .. -> T`).

| Group | Tasks | Common defects |
| --- | --- | --- |
| overflow, range of representation | t02 midpoint, t03 sat_sum, t09 div_floor, t10 mod_floor, t16 gcd, t17 isqrt, t18 count_digits, t24 pow_mod | `a + b`, `abs(MIN)`, `MIN % -1`, `mid * mid`, `b * b`, floating-point `sqrt` |
| boundaries, ties, off by one | t01 clamp, t04 count_in_range, t05 first_max_index, t06 last_min_index, t07 strictly_increasing, t08 lower_bound, t12 second_max, t19 range_sum, t20 majority, t21 longest_run | `<` against `<=`, first/last, the empty slice, `max_by_key` picks the last, Boyer–Moore without verification |
| in-place transformation | t11 max_subarray, t13 rotate_right, t14 dedup_sorted, t15 move_zeros, t22 merge_sorted, t23 sort | `k > len`, tail not cleaned up, order not kept, the rest of one side not copied |

The 13 tasks with a domain also have a domain predicate for BMB (`BMB_DOMAIN`; step 2 of the judging below).

## The hidden judge (`judge.py`)

The agent does not see the judging material (the task prompt holds only the statement, the domain and the signature). Both arms are judged the same way.

- **Expected values come from a Python model** (`model`). They are not taken from the reference implementation, so an error in the reference implementation does not get into the verdict. CI checks that the reference solutions (BMB and Rust) agree with the model on every case.
- **Cases**: 267 to 810 per task, 9,651 in all. Combinations of boundary values (`i64::MIN`, `MIN+1`, `-1`, `0`, `MAX` and so on), values near overflow, lengths 0, 1, 2 and random lengths, element distributions with many duplicates and over the full range, traps specific to a task such as `k^2-1`. Cases outside the domain are dropped at generation (a test checks this).
- **Adequacy of the judge**: 4 plausible wrong Rust implementations (mutants) per task, 96 in all. The hidden cases must kill all of them (`adequacy`, CI).
- **Defect**: a different output, or a panic, trap, crash or timeout. When the process dies or hangs, that case is recorded as failed and the run starts again from the next case (`run_cases`, 20 seconds per process, at most 25 restarts).
- **Not delivered**: when the implementation does not build, every case fails.

The procedure per arm:

| Step | BMB | Rust |
| --- | --- | --- |
| 1. Delivery | the target `tasks::NAME` has the required signature (types only, names do not matter), and the whole workspace is proved (`bmb emit-llvm` exit code 0 = the condition of `bmb build`) | the judging crate builds with a path dependency on the agent's crate (the agent's tests and dev-dependencies are not used) |
| 2. Domain | a hidden unit proves a function that calls the target under `requires dom(..)`. That is, the agent's `requires` must follow from the domain written in the statement. If this fails it is a defect (domain violation) even when the outputs are right | not applicable (Rust has no precondition. A panic on an input in the domain is a defect) |
| 3. Execution | the target is called through a generated LLVM wrapper + a C driver. The program is proved, so there are no runtime checks | a generated `main` calls it under `catch_unwind`. A debug build (`overflow-checks = true`), so an overflow is a panic |

## The arms and the fairness rules

They follow ADR-0021 (frozen, one attempt, no retry, biases stated) and ADR-0034 §2 (the same model and the same token limit, tools of the same level on the Rust side).

1. **The same model and settings.** Both arms run through the same adapter of `bench/m1/anthropic_agent.py` (the same `EFFORT`, `MAX_TOKENS` per request). The tools have the MCP shape (`name`, `description`, `inputSchema`), so the adapter does not tell them apart.
2. **The same budget.** 40 tool calls per session (ADR-0021 §3), 64,000 model output tokens per session (`SESSION_OUTPUT_TOKENS`, checked at every model turn). This limit counts only the visible output (text and tool calls, ceil(bytes/4)). Reasoning tokens are recorded apart and not counted (ADR-0076; runs before it counted the reasoning too). When the limit is reached, the implementation at that moment is judged. A response cut at the output limit is continued once in the same turn (ADR-0076).
3. **Both get a checker.** BMB: `verify` (diagnostics, counterexamples); Rust: compiler errors (`cargo_build`) and test runs (`cargo_test`, proptest allowed, ADR-0034 decision 5). Neither has a shell or the network (cargo on the Rust side always runs `--offline`; the dependencies are fetched once before the sessions and built ahead).
4. **The same judging.** The hidden judge above. Only BMB gets the domain check as well, because in BMB the contract of a "proved function" is the condition of calling it (see the disclosure of biases below).
5. **One attempt.** One session per task, not run again on failure. Both arms run at the same commit with the same MANIFEST (`summarize` refuses results with different MANIFESTs).

## Metrics and the G5 verdict

`summarize` gives a table with one column per result file: success (all hidden cases pass), defect rate (tasks with a defect / tasks), not delivered, domain violations, share of failed cases, total model tokens (input + output) and input and output each, tool calls, checker calls, limit reached, session wall-clock time, tool time. Then a table per task. The harness is frozen and prints its row labels and verdict lines in Korean; the lines below give their form in English.

Given one BMB result and one Rust result it adds the G5 verdict line (the provisional criterion of ADR-0034, M2):

```
G5 (provisional criterion: defect rate ratio ≤ 1/2, total token ratio ≤ 2): defect rate ratio X, total token ratio Y → pass | not met | cannot be judged (..)
```

Defect rate ratio = BMB defect rate / Rust defect rate, total token ratio = BMB total tokens / Rust total tokens. When Rust has 0 defects the ratio is not defined and the line reads "cannot be judged" (the defect rates of the table are then reported as they are).

**H-ORACLE (ADR-0040 §4, fixed before the runs with a real model).** When the session ends, the harness runs the arm's checker once more on the final state (BMB `verify`, Rust `cargo test`; not counted as an agent call, `final_check_ok`). The metric is the share of tasks that passed the self-check in which the hidden judge found a defect. The table has the rows "self-check passed" and "self-check passed & hidden failure / self-check passed", and with both arms a verdict line is added.

```
H-ORACLE (share of passed & hidden failure, refuted when BMB ≥ Rust): BMB a/p = x, Rust b/q = y → supported | refuted | cannot be judged (..)
```

It is refuted when the BMB share is at least the Rust share (also when they are equal). When no task of one arm passed the self-check, or Rust has 0 passed & hidden failure, there is nothing to beat and it cannot be judged. `cargo test` passes even when the agent wrote no test, so a task without tests is among the "self-check passed" too (having no tests is also a choice that saves test cost).

**G8 test code (ADR-0041, fixed before the runs with a real model).** The lines of test code are compared over the tasks that passed the hidden judge only. For BMB it is the remaining test area the compiler computes (`test_lines` of the summary of `bmb query tests` on the final workspace: canonical-form lines of the definitions that still need tests), for Rust the lines of test code the agent wrote (every file under `tests/` and the `#[cfg(test)]` items in `src/`, without blank lines and lines that are only a `//` comment). It is stored in `test_code` of the result row, and the table gets the totals over all tasks and over the passed tasks, and a verdict line.

```
G8 (test code lines, tasks that passed the hidden judge): BMB a lines/n tasks, Rust b lines/m tasks → ratio x (provisional M3 criterion ≤ 1/10: met | not met) | cannot be judged (..)
```

The M2 goal is "start measuring", so this line is only reported. With 0 lines of Rust tests it cannot be judged. The units of the two sides differ (for BMB the size of the code that needs tests, for Rust the size of the tests actually written). 0 for BMB means "no test needs to be written"; a non-zero value is an upper approximation that that much code needs tests.

Each row of the results also holds the final files the agent could write (`final_sources`: BMB `src/*.bmb`, Rust `.rs` under `src/` and `tests/`). This is so that a metric defined later, as the amount of test code (G8) was, is computed from these results without a new paid run.

## Runs with a real model (the user's machine, paid)

```
python3 bench/brb/harness.py manifest
python3 bench/brb/harness.py run --arm bmb  --agent anthropic:claude-opus-5-5 --out bench/brb/results/$(date +%F)-claude-opus-5-5-bmb.jsonl
python3 bench/brb/harness.py run --arm rust --agent anthropic:claude-opus-5-5 --out bench/brb/results/$(date +%F)-claude-opus-5-5-rust.jsonl
python3 bench/brb/harness.py summarize bench/brb/results/<date>-claude-opus-5-5-bmb.jsonl bench/brb/results/<date>-claude-opus-5-5-rust.jsonl
```

- The Rust arm has proptest on by default (`--proptest on`). The first time, it fetches the crates of `Cargo.lock` from crates.io (needs the network). After that the sessions are offline.
- A real model runs with `--jobs 1` (the default). The two arms run one after the other at the same commit, and results of a `+dirty` commit are not used in a report.
- In the Rust arm, code the agent wrote (tests) runs during the session, and at judging the implementations of both arms run. Run it in an isolated environment (container, VM).
- The raw data is committed under `bench/brb/results/` and the summary as a measurement report (ADR-0021 §5). The 2 models (the main model and a small model, ADR-0034 decision 3) get separate tables.

## CI (`scripts/check.sh`)

| Job | Checks |
| --- | --- |
| `bench brb oracle` | the reference solutions of both arms pass the hidden judge and the final self-check (24/24, 0 defects), and the BMB reference solutions pass the domain check too. The summary table, the G5 line ("cannot be judged", Rust has 0 defects), the H-ORACLE line ("cannot be judged", Rust has 0 passed & hidden failure), test code lines 0 and 0 and the G8 line ("cannot be judged", 0 lines of Rust tests) |
| `bench brb weak` | the weak controls of both arms pass the self-check (BMB `verify`, Rust's own tests) during the session and on the final state, and the hidden judge finds a defect in all 24 tasks |
| `bench brb adequacy` | all 96 Rust mutants are killed |
| `bench brb tests` | `test_brb.py`: invariants of the task set (determinism, domains, sizes, the same statement), the computation of G5, H-ORACLE and G8 and the summary table, counting Rust test lines, recovery from a crash or hang, the sandbox of the Rust tools, the checker's verdict, a Rust session and the output token limit through the real-model adapter (with a fake client). The proptest session test runs only when the proptest crates are available offline (skipped otherwise) |

CI runs the Rust arm with `--proptest off`. The scripted agents do not use proptest, and the gate does not depend on the network.

## Biases and limits (disclosed)

- **Choice of tasks.** We wrote the tasks, and picked only what can be solved and proved in M1 BMB: integers and slices, small algorithmic functions. No structs, collections, strings or input/output. Many tasks make overflow and boundary defects easy to show (8 overflow, 10 boundary), which may favour BMB, where integer overflow is forced as a proof obligation. No public tasks were ported, so a rate of dropped tasks does not apply. Results are reported per task group as well.
- **Only BMB has the domain check.** When the `requires` of the BMB agent means the same as the domain of the statement but the prover does not find the implication, it counts as a defect (incompleteness of the prover). Such a case shows apart as "domain violation" in the table per task.
- **BMB has no tool that runs code.** The BMB agent cannot run tests and only proves (this is the comparison by design). `build` can make an executable, but there is no tool to run it.
- **Input tokens.** The BMB system prompt (with the language rules) is longer than the Rust prompt. Total tokens are counted as the model reports input + output (the cost of the prompt included).
- **Scope of the judging.** The hidden cases are short slices (mostly of length 20 or less). Defects that show only on long inputs (timeouts and the like) are not measured. Time is only recorded as wall-clock time; performance is not judged.
- **The Rust judging build.** Judged with a debug build (overflow checks on). Code that wraps around in a release build counts as a defect too (the value is mathematically wrong for an input in the domain).
