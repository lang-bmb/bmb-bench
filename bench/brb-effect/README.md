# BRB-EFFECT: tasks with output and state (H-EFFECT, ADR-0078)

A new variant of BRB (`../brb`). In every task the function **prints lines** (BMB `print_i64`, Rust `println!`) and **carries state** along the input elements (a balance, a number of tokens, the run in progress). The hidden judge checks the printed lines, in order, together with the return value. The hypothesis H-EFFECT is: "I/O and state exposed as effects separate a pure core that is proved from a shell that needs tests, and the remaining test area is small".

This directory holds the tasks (frozen), the judge, the harness and the CI checks. When this was written there was no run with a real model yet; the results are under `results/`.

| File | Contents |
| --- | --- |
| `tasks/fNN_*.py` | 4 tasks (frozen). The BRB task format with output added: `model(*args)` gives `(return value, printed lines)` |
| `judge.py` | the hidden judge (frozen). It loads the BRB judge (`bench/brb/judge.py`, frozen) as a private copy and changes only the expected values, the scoring, the case execution and the caller's effect in the domain check |
| `harness.py` | runs the sessions, judges and summarizes (frozen). It loads the BRB harness as a library and runs it with this set's judge |
| `MANIFEST` | SHA-256 of the files above and of BRB's MANIFEST (prompts, tool server, Rust template) |
| `test_brb_effect.py` | unit tests of the harness (gate) |

```
python3 bench/brb-effect/harness.py manifest                                  # check the freeze
python3 bench/brb-effect/harness.py run --arm bmb  --agent oracle --jobs 4    # reference solutions: 0 defects (CI)
python3 bench/brb-effect/harness.py run --arm rust --agent oracle --jobs 4    # (CI uses --proptest off)
python3 bench/brb-effect/harness.py run --arm bmb  --agent weak --jobs 4      # weak controls: the self-check passes, the hidden judge finds the defect (CI)
python3 bench/brb-effect/harness.py adequacy --jobs 4                         # the hidden cases kill all 16 Rust mutants (CI)
python3 bench/brb-effect/harness.py summarize BMB.jsonl RUST.jsonl            # the table and the H-EFFECT verdict line
```

The session conditions are BRB's: the same prompts (`bench/brb/prompt-*.md`: the BMB prompt says that only `#[effects(io)]` functions can call `print_i64`), the same tools, limits (40 tool calls, 64,000 model output tokens per session) and the self-check after the session (BMB `verify`, Rust `cargo test`). The task statement is the same for both arms and names the way to print (`print_i64` / `println!`) together in one sentence. The statement does not ask for a decomposition (nothing says to split off a pure core).

## Tasks

| Task | State | Common defects | Decomposition of the reference solution (BMB) |
| --- | --- | --- | --- |
| f01 ledger | a balance, 4 kinds of operation (deposit, withdrawal, interest, fee) | overflow (deposit, `(b/100)*a`), refusing a full withdrawal, printing the balance instead of -1 on a refusal | 4 pure functions, one per operation, + 1 branch + 1 output: area 1/6 |
| f02 report | minimum, maximum, midpoint, count, longest run | midpoint overflow, rounding toward 0, `>=`, a run that reaches the end left out | 6 pure + 1 output: 1/7 |
| f03 limiter | number of tokens, reference time of the refill | `tokens + g` overflows, the reference time set to the request time (the rest of the period dropped), starting with an empty bucket | 3 pure + 1 output: 1/4 |
| f04 rle | the value and length in progress | piece length limit+1, limit ignored, order of length and value, the last piece left out | 1 pure + 1 output: 1/2 |

All reference solutions: 4 definitions that need tests / 19 executable definitions = **0.211**, 96 lines of remaining area.

## The hidden judge (`judge.py`)

The same as BRB (expected values from a Python model, deterministic cases seeded with the task id, 366 to 583 per task and 1,842 in all, a panic, crash or timeout is a defect, BMB delivers only a proved workspace, the domain check). Added:

- **Printed lines.** A case passes when the return value, the `&mut` slices and the printed lines (one integer per line, surrounding whitespace ignored) are all right. Cases where the return value is right and only the lines are wrong are counted apart as `wrong_output`.
- **Reading the lines.** The BRB driver prints the header line `K ok ..` when a case ends, and flushes. The target's output uses the same stdout (BMB `print_i64` is the C library's `printf`; Rust's `println!` and the judge's `write!` are the same `std::io::stdout()`), so it comes right before that case's header line. A header line is only a line that carries the next case number.
- **The caller in the domain check** is `#[effects(io)]` (it calls a target that prints).
- **Adequacy of the judge**: 4 Rust mutants per task, 16 in all, and the hidden cases kill all of them (`adequacy`, CI).

Controls: the weak solutions pass the self-check in both arms and have a defect under the hidden judge (CI). In three of the four BMB weak solutions (f01 the output on a refusal, f03 the update of the reference time, f04 the output order) the defect is inside the printing function (where the proof states nothing about the values). In f02 the defect is in the pure core (`longest_above`), and it passes the proof because the reference solution's contract does not state that value.

## Refutation condition (registered before the first run, 2026-11-02)

The H-EFFECT row of ADR-0078 is used as it is. The definitions of the measurement on this set:

- **Remaining test area:** Σ`test_needed_defs` / Σ`exec_defs` over the `bmb query tests` summaries of the BMB sessions that passed the hidden judge. The denominator is the executable definitions (a `spec fn` is a definition that needs no test, so counting it would make the area smaller the more predicates are used).
- **Test code lines:** as G8 of BRB. For BMB the lines of the remaining area of the passed sessions (`test_lines`), for Rust the lines of test code the agent wrote in the passed sessions.
- **Verdict (one BMB result and one Rust result per model):** when the area ≤ 0.20 and the BMB lines ≤ Rust lines × 1/3, the confirmation condition is met for that model; when either is exceeded, it is refuted. The hypothesis is confirmed when both models (qwen, sonnet, ADR-0066) meet it. When no session of one arm passed the hidden judge, or Rust has 0 lines of tests, it cannot be judged (refuted if the area is already over).

**To be known beforehand:** even with the decomposition of the reference solutions the area is 0.211, over the criterion (0.20). There is at least one printing shell per task, so the smaller the task the larger the lower bound of the area (1/2 for f04). To meet the area condition on this set an agent has to split finer than the reference solutions. The tasks were not grown to fit the criterion (the task size is BRB's, and the statement does not ask for a decomposition). **Decision (approved by a person on 2026-11-02, adopting the recommended option):** the criterion 0.20 stays (it is not relaxed before the measurement). Below the verdict line the multiple of the reference solutions' area (4/19 = 0.211) is given as an auxiliary metric (`REFERENCE_AREA`, not used for the verdict).

What H-EFFECT does not measure: external dependencies (clock, random numbers, files). The language's `io` is output only for now (input comes as arguments).
