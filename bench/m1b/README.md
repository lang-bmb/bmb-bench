# m1b measurement (ADR-0025)

The second frozen task set, for the stage 2 verdict. The language is the M1 subset (ADR-0016) unchanged, and the procedure, judging and metrics are those of ADR-0021. The harness is `bench/m1/harness.py` with `--set bench/m1b`.

| File | Contents |
| --- | --- |
| `prompt.md` | the agent's system prompt (frozen). Byte for byte the same as `bench/m1/prompt.md` (ADR-0025 §1, test `test_m1b_prompt_is_m1_prompt`) |
| `seed/` | the starting workspace (frozen). 9 units, 116 definitions (53 executable functions, 63 `spec fn`), all proved |
| `tasks/` | 37 tasks (frozen): 25 write, 12 navigation. Every write task has a hidden reference contract, a reference solution and a weak control |
| `MANIFEST` | SHA-256 of the frozen files. On a difference the harness refuses to run |
| `mutants/` | the hidden BSB mutants (`<task>.json` per write task) and their SHA-256 in `mutants/MANIFEST`. Frozen apart from the `MANIFEST` above (see "Specification mutant kill rate" below) |

```
python3 bench/m1/harness.py --set bench/m1b manifest                       # check the freeze
python3 bench/m1/harness.py --set bench/m1b run --agent oracle --jobs 4    # reference solutions: all succeed (CI)
python3 bench/m1/harness.py --set bench/m1b run --agent weak --jobs 4      # weak controls: all fail (CI)
```

## Kinds of task

| Kind | Tasks | What it looks at |
| --- | --- | --- |
| new definition | w01~w11, w22~w24 (unit `tasks`), w13 (`arr`), w25 (`ledger`) | does the agent find what to use in a large seed and reuse it (`search::lower_bound`, `order::min_index`, `ledger::deposit`, `arith::sum_to` and others) |
| strengthening an existing definition | w12, w14~w19 | does the agent change a contract and keep the proofs of the affected definitions. w12, w14, w17 and w19 also need a callee's contract strengthened |
| writing several units | w20 (`num::abs_diff` + `tasks::max_gap`) | the signature and specification strength are judged separately for each `also_check` definition of the task |
| navigation | n01~n12 | direct and transitive call relations, `impact` (definitions to prove again, one step), contract view, `&mut` writes, `#[uses]`, effects. The harness computes the answer from the map |

## Procedure for comparing models

Several models run under the same conditions and are compared as columns of the `summarize` table. Runs with a real model are paid, so they are made on the user's machine ("Runs with a real model" in `bench/m1/README.md`).

1. **The same input.** Every run uses the same task set (`--set`), the same MANIFEST and the same compiler commit. Check first with `manifest` and `run --agent oracle --expect all-pass`. The harness records `task_set`, `manifest` (SHA-256 of the MANIFEST) and `commit` in the summary row. A run whose commit is `+dirty` is not used in a report.
2. **Once per model.** One session per task, no retry (ADR-0021 §3). A real model runs with `--jobs 1` (the default). A failed run is not run again to pick the better one.
3. **Result file names.** `bench/<set>/results/<date>-<model>.jsonl`. The date is `date +%F`, the model the API model ID as it is.
   ```
   python3 bench/m1/harness.py --set bench/m1b run --agent anthropic:claude-opus-5-5 \
       --out bench/m1b/results/$(date +%F)-claude-opus-5-5.jsonl
   python3 bench/m1/harness.py --set bench/m1b run --agent anthropic:MODEL_B \
       --out bench/m1b/results/$(date +%F)-MODEL_B.jsonl
   ```
4. **Tables.** `python3 bench/m1/harness.py summarize bench/m1b/results/A.jsonl bench/m1b/results/B.jsonl`. One file is one column. The first table has the task set, the agent, the commit and the metrics of ADR-0021 §4 (write and navigation first-attempt success rates, navigation precision and recall, tokens per query, Rust habit error rate, unproved obligations, `io` definitions, tool calls, limit reached, model input and output tokens) and the specification mutant kill rate (BSB, below); the second has success or the cause of failure per task.
5. **No mixing.** `summarize` refuses files of different task sets together (an older result without `task_set` is `m1`). `m1` and `m1b` get separate tables, and their numbers are neither added nor averaged. Columns with different commits show in the table, so the report states the difference.
6. **Report.** The raw data (the result files) is committed, and the summary is written as a measurement report. It states the task bias (integers and arrays only), the number of tasks, the limits and the failure cases (ADR-0021 §5).

## Specification mutant kill rate (BSB, ADR-0034 G3)

Every write task has a hidden set of mutants of its reference solution (`mutants/<task>.json`, frozen by `mutants/MANIFEST`). After the session the harness counts how many mutants the agent's contract rejects (`bsb_mutants`, `bsb_killed`, `bsb_survivors`), and `summarize` gives the sum in the row "Specification mutant kill rate". The judging code is `bench/m1/bsb.py`, the generator `bench/m1/bsb_gen.py`.

- **Mutants.** For the target definition and every executable function it calls (transitively), each W0904 mutation that `bmb mutate` makes (operator, constant, condition, index ±1, negated `if` condition). The text is not edited directly: the compiler changes the syntax tree and prints it in canonical form.
- **Execution.** The reference solution and each mutant run on inputs fixed per task (all satisfy the hidden `ref_pre`). The driver is built with the real back end: `bmb emit-llvm --all-checks` (no proof; the contracts are not trusted, so every overflow, bounds and division check stays as a trap) + clang. After a trap it is built again from the next input.
- **Classification.** `no_check` (does not check) / `equivalent` (the same output on every input: no distinguishing input among the fixed ones) / `trap_only` (differs only by a trap or an endless loop: a contract speaks about the result, so this is the proof gate's part) / `allowed` (ends normally and differs, but every output satisfies the hidden reference contract: another index of the same minimum, for example) / **kept** (some input gives an output the hidden reference contract rejects, that is, there is a witness). Whether an input is a witness is decided by the same kill check as below, against a stub with the hidden contract, with `bmb verify`. At most 2 witnesses, in input order.
- **Kill.** One judging function per mutant: it calls the agent's function on the witness inputs (proving the precondition) and proves an `assert` that the results cannot all equal the mutant's outputs. A function is seen only through its contract (ADR-0017 §4), so a proof means the contract rejects that mutant. The calls are independent, so this equals "the contract excludes at least one of the witnesses". One `bmb verify` per task (with the session cache). When the workspace is not proved or the signature differs, it counts as 0 killed.
- **Limits.** The mutation operators are only the W0904 set (no variable swap, no statement deletion), so for some weak contracts no mutant shows the weakness (for example w11, keeping the elements inside the range). The equivalence verdict is a test on fixed inputs, not a proof. When the contract's precondition is stronger than `ref_pre` and rejects the witness inputs, that mutant is not killed.

| Generation | Count |
| --- | --- |
| mutants generated | 426 (26 targets: 25 write tasks + `num::abs_diff` of w20) |
| kept | 186 |
| dropped: `equivalent` / `trap_only` / `allowed` / `no_check` | 31 / 114 / 95 / 0 |
| contracts of the reference solutions (oracle) | 186/186 (100.0%) |
| contracts of the weak controls (weak) | 45/186 (24.2%) |

```
python3 bench/m1/bsb_gen.py --jobs 4            # generate again (about 8 minutes, the result is deterministic). On a change the MANIFEST is written anew
python3 bench/m1/bsb_gen.py --check --tasks w03-max3   # generate again and only check it equals the files
```
