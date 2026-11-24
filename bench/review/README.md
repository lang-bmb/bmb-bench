# REVIEW: reviewing the specification diff against reviewing the code diff (H-REVIEW, ADR-0078)

Hypothesis H-REVIEW: a reviewer who sees only the specification diff catches as many defects as a review of the code diff. The premise is "a defect that passed the proof gate is a specification defect". So the programs before and after a change are all proved programs, and a defect is a change after which the contract no longer says the intent.

This directory holds the change set (frozen), the views, the judging, the harness and the gate. There is no run with a real model yet (it is made on the measurement machine).

| File | Contents |
| --- | --- |
| `changes/*.json` | 143 changes (a frozen product). `gen.py` makes them from the BVB tasks (`bench/bvb/tasks`, frozen) |
| `gen.py` | the generator (frozen). `--check`: checks the structure without a compiler. `--regen`: makes it again with the compiler and compares byte for byte |
| `mutants.py` | derivation of the body mutation changes (frozen): `bmb mutate`, `bmb verify`, comparing runs, proving that the hidden contract rejects |
| `set.json` | the arms (lists of view parts), the two arms compared, the criterion for the token ratio, the compiler commit used for the generation, the further files that go into the MANIFEST (frozen) |
| `prompt.md` | the reviewer's system prompt (frozen). Both arms use the same prompt |
| `views.py` | what the reviewer sees (frozen): extraction of the contract text, the diffs, running `bmb weaken`, the message |
| `judge.py` | the judging (frozen): the answer format, detection, false alarm and format error, the verdict rule of the hypothesis |
| `harness.py` | runs, result files, tables (frozen) |
| `MANIFEST` | SHA-256 of the frozen files above and of `../bvb/MANIFEST`. On a difference the run is refused |
| `test_review.py` | gate |

```
python3 bench/review/harness.py manifest                                   # check the freeze
python3 bench/review/gen.py --check                                        # check the structure (no compiler)
python3 bench/review/gen.py --regen                                        # make it again and compare byte for byte (compiler, about 13 minutes)
python3 bench/review/harness.py sizes                                      # view sizes per arm and kind, and the token ratio (no model)
python3 bench/review/harness.py verdicts                                   # the `bmb weaken` verdict of every change, per kind
python3 bench/review/harness.py view --arm spec --change vb-misc-sum.weaken  # the message the reviewer gets
python3 bench/review/harness.py run --arm spec --agent oracle --expect all-right      # scripted: gets everything right
python3 bench/review/harness.py run --arm code --agent blind --expect none-detected   # scripted: misses everything
python3 bench/review/harness.py run --arm spec --agent openai:MODEL --out bench/review/results/DATE-MODEL-spec.jsonl
python3 bench/review/harness.py run --arm code --agent openai:MODEL --out bench/review/results/DATE-MODEL-code.jsonl
python3 bench/review/harness.py table [--d PP] SPEC.jsonl CODE.jsonl       # the table per arm and the H-REVIEW verdict line
```

## The change set

Each of the 45 BVB tasks has an intent sentence (the description of the prompt), a `reference` (a contract that says the intent) and a `weak_reference` (a contract for the same code that is consistent and proved but does not say the intent).

| Change | Kind (`kind`) | Before → after | Hidden label | Count | Tasks |
| --- | --- | --- | --- | --- | --- |
| `<task>.weaken` | `contract-weakened` | `reference` → `weak_reference` | `defect` | 45 | 45 |
| `<task>.restore` | `contract-restored` | `weak_reference` → `reference` | `clean` | 45 | 45 |
| `<task>.mutant-defect-N` | `contract-weakened+body` | `reference` → weak contract + body mutant | `defect` | 26 | 17 |
| `<task>.mutant-clean-N` | `body-only` | `reference` → the same contract + body mutant | `clean` | 27 | 20 |

143 in all: 71 `defect`, 72 `clean`. 53 changes change the body.

- No program is written by hand. The intent is the description of the task prompt without the "Create unit" line and the "Required signature" line (with the code of the given specification functions), and the program is one file with the task's `put` code inside the unit `tasks`, and the BVB seed (`given`). The order of the definitions is the task's (not the compiler's canonical form). The after program of a mutation change is that text with the one site the compiler names (`bmb mutate`, W0904) changed, and only those are used whose `bmb fmt` result equals the mutant the compiler gave.
- **The rule for body mutations (fixed before the measurement):** per task, in the order `bmb mutate` gives (the executable functions of the unit in source order, within a function the compiler's order of sites), the first K = 2 that meet the condition are used for each kind.
  - `body-only`: a mutant of the `reference` program passes `bmb verify` under the unchanged reference contract (it is equivalent, or a rewriting the contract allows).
  - `contract-weakened+body`: a mutant of the `weak_reference` program passes `bmb verify` under the weak contract, and there is an evidence input: on an input for which the hidden precondition is proved, the mutant terminates, its output differs from the reference program's, and it is proved that the hidden reference contract rejects that output (the same form as the kill check of `bench/m1/bsb.py`; run with `emit-llvm --all-checks` and clang). The evidence stays in `witness` of the change file (the reviewer does not see it).
  - The inputs were not written per task. A generator seeded with the task id draws 60 from the types of the signature (small integers, arrays of length 0 to 5), and only those for which the hidden precondition is proved are used. A mutant whose difference does not show on those inputs is not included (only what is decided).
- Result of the generation (commit `9938d706`): 602 mutants of the reference programs (6 whose site could not be carried to the text). 28 tasks have mutants proved under the weak contract, and for 11 of them no evidence came out (1 has no input for which the precondition is proved).
- **The committed `changes/` is the frozen product.** Which mutants meet the condition depends on the compiler, so they are not made again at run time. The compiler commit used for the generation is in `generated_with` of `set.json`. `gen.py --check` checks without a compiler: the 90 that change only the contract are made again byte for byte and compared, and for the mutation changes it looks at whether the before is the reference program and the after is the program with the recorded one-site substitution applied, and whether they are 1..n (n ≤ K) per task and kind. `gen.py --regen` makes everything again and compares byte for byte (equal at `9938d706`, about 13 minutes).
- Basis of the labels (gate): the 143 distinct programs (45 reference, 45 weak, 53 mutated) all pass `bmb verify`, and the m1 judging (ADR-0021 §2: the contract implies the task's hidden reference contract) accepts every program with the reference contract (the after of `clean`) and rejects every program with the weak contract (the after of `defect`).
- `bmb weaken` only compares two contracts with each other; it does not know the intent, and it may not decide. At commit `9938d706`:

| Kind | Label | `weakened` | `undecided` | `refined` | `compatible` | `same` |
| --- | --- | --- | --- | --- | --- | --- |
| `contract-weakened` | `defect` | 33 | 12 | 0 | 0 | 0 |
| `contract-weakened+body` | `defect` | 19 | 7 | 0 | 0 | 0 |
| `contract-restored` | `clean` | 0 | 2 | 33 | 10 | 0 |
| `body-only` | `clean` | 0 | 0 | 0 | 0 | 27 |

  The gate does not check the counts but "what is decided does not contradict the label" (`defect` does not come out as `same`, `refined` or `compatible`, `clean` not as `weakened`, and `body-only` is `same`).

## Arms (`set.json`)

| Arm | What it sees |
| --- | --- |
| `spec` | the contract diff (a unified diff of the function's signature line, the `requires` and `ensures` lines, and the whole definitions of the `spec fn`s of the unit that those lines call directly or indirectly) and the output of `bmb weaken before after` as it is |
| `code` | a unified diff of the whole program file (`src/tasks.bmb`) |

Both arms get the intent sentence first. The contract diff of a change that does not change the contract (`body-only`) is not the empty string but the one line `(no difference)`. Bodies, attributes (`#[uses]`, `#[effects]`), `decreases`, loop invariants and `spec fn`s used only by proofs are not contract text. The seed's `given::..` does not change, so it is in no diff (for the tasks that give that code, it is in the intent sentence). `bmb weaken` is run at run time with the compiler of that commit, so the commit in the result header fixes the view. Size is the bytes of the view and `ceil(bytes / 4)` tokens (ADR-0021 §4). The message size with the intent sentence is given as well.

## Verdict (registered before the first run, 2026-11-12)

For every change the reviewer answers in one request (no tools, no retry) with one JSON object: `{"verdict": "defect" | "ok", "reason": "one line"}`.

- **Detection:** `"defect"` on a `defect` change. **False alarm:** `"defect"` on a `clean` change.
- **Format error:** an answer that is not that one object (or that object inside one code fence). Other text before or after, other keys, another `verdict` value, a `reason` that is not a string, and an empty answer after an API error all belong here. Counted apart, neither as a detection nor as a false alarm. It stays in the denominator.
- **Detection rate** = detections / 71 `defect`, **false alarm rate** = false alarms / 72 `clean`, **amount read** = the mean of the view tokens (143 changes). The verdict is made on the whole set. `table` also gives the share of `defect` answers per kind (not used for the verdict).

The H-REVIEW row of ADR-0078 as it is:

> Confirmed: the detection rate is equal or higher (inside D counts as equal), and the amount read (tokens) is 1/5 or less. Refuted: the detection rate is lower by more than D

- On this set: **refuted** if the detection rate of `spec` is lower than that of `code` by more than D; otherwise **confirmation condition met** if the mean view tokens of `spec` are 1/5 or less of those of `code`; else **not confirmed** (the detection rate is inside D, the token ratio is over the criterion). D is the minimum difference of ADR-0077 §4, and while this set has no repeated measurement it is the global value of 30%p (changed with `table --d`, ADR-0086 §2).
- `table` always computes the value of the rule but gives the verdict line only for the two arms of one model run: one result file per arm, the same set, MANIFEST, model and commit, all changes, nothing uncommitted. Otherwise it is `not judged (reason)`.
- Models as in ADR-0066: qwen first, sonnet as the cross-check. The hypothesis is confirmed when both models meet the condition.
- The false alarm rate is not in the verdict rule. It is reported with it (a reviewer that always answers `defect` has a detection rate of 100% and a false alarm rate of 100%).

**The only evaluators are model reviewers.** ADR-0078 §3 kept a human sample for calibration, but the calibration with a human sample is not done (decided by a person on 2026-11-11). The verdict on this set holds for model reviewers only and is not carried over to human reviewers.

## To be known beforehand

- **The token criterion (1/5) cannot be met on this set. The same holds for the changes that change the body alone.** Mean view tokens at commit `9938d706` (`harness.py sizes`):

| Kind | Changes | `spec` (contract diff + `bmb weaken`) | `code` | Ratio spec/code | Ratio with the intent sentence |
| --- | --- | --- | --- | --- | --- |
| all | 143 | 289.8 (106.4 + 154.7) | 165.4 | 1.752 | 1.497 |
| `contract-weakened` | 45 | 364.8 (125.8 + 210.3) | 170.9 | 2.135 | 1.777 |
| `contract-restored` | 45 | 265.3 (125.8 + 111.0) | 170.9 | 1.553 | 1.379 |
| `contract-weakened+body` | 26 | 380.5 (145.7 + 206.1) | 228.3 | 1.667 | 1.474 |
| `body-only` | 27 | 118.3 (4.0 + 85.3) | 86.7 | 1.364 | 1.170 |

  (In parentheses are the tokens of the two parts; the rest is the title lines.) A body mutation is a one-site substitution, so the code diff with its 3 lines of context is 80 to 230 tokens, and the output of `bmb weaken` alone is larger than that or about the same. For `body-only` the contract diff is 4 tokens but 85 tokens of tool output come with it. The ratio of the 53 that change the body is 1.58 ((26 × 380.5 + 27 × 118.3) / (26 × 228.3 + 27 × 86.7)). So the verdicts this set can give are only **refuted** and **not confirmed**, and what it measures is the detection rate (does the specification diff with the tool's verdict catch as much as the code diff). To reach 1/5 there would have to be changes whose code diff is more than five times the contract diff, that is, changes that edit several lines of a body, and those cannot be made from the frozen material with one-site mutations. The composition rule (K, the order) was fixed before measuring and was not changed to fit the ratio. Nor was the criterion.
- **Every defect comes with a weakened contract.** The 71 `defect` are 45 "only the contract weakened" and 26 "the contract weakened and the body changed too". There is no change where the contract stays and only the body changes wrongly: a mutant proved under the reference contract keeps the contract by definition and so is `clean` (the meaning of the premise "a defect that passed the proof is a specification defect"). Changes where the body changes wrongly under a contract that was weak from the start (weak → weak + mutation) were not included. That is a kind the `spec` arm cannot catch in principle, since the contract diff is empty, and it is a gap on the side unfavourable to the hypothesis. Rewritings of a contract with the same meaning and justified weakenings are absent too.
- **The `bmb weaken` verdict almost separates the labels.** `weakened` occurs only for `defect` (52/71), `refined`, `compatible` and `same` only for `clean` (70/72), and only the 21 `undecided` (19 `defect`, 2 `clean`) are not separated by the tool. The detection rate of the `spec` arm may be a reading of the tool's verdict, and it is not generalized to kinds of change the tool cannot separate.
- **`contract-weakened+body` exists for only 17 tasks and `body-only` for 20.** Only the tasks where a mutant met the condition (at most 2 per task), and the evidence inputs come from a general generator, so tasks with a narrow precondition (for example a sorted array) drop out easily.
- **Pairs.** `weaken` and `restore` of a task are inverses of each other, and the mutation changes start from the same reference program. A review is an independent request per change, so the reviewer does not see the other changes.
- The task bias is BVB's (integers and arrays, units of one function, `bench/bvb/SOURCES.md`). One change is 1.4%p of the detection rate.
- The intent sentence states directly "what the contract has to say" (the sentence of the BVB prompt). It is closer to a specification than the description of the intent of a real change is.
- `--regen` does all the proofs and runs again, so it is slow (13 to 14 minutes on 4 cores), and which mutants are proved depends on the compiler. So it is not in the push gate, and when the set is made again it is run with the compiler of the `generated_with` commit of `set.json`. The gate is `--check` (structure) and `test_review.py` (proves all 143 stored programs with the current compiler).

## How to add another set (H-INTENT)

The harness runs another set with `--set DIR`. A set is data: the directory holds `set.json`, `prompt.md`, `changes/*.json` and `MANIFEST`.

- `arms` of `set.json` maps an arm name to a list of view parts. The parts are `contract_diff`, `weaken`, `code_diff`, `contract` (the contract text of the after program), `code` (the after program file) and `field:NAME` (text frozen in the change file; its title is in `titles`). The H-INTENT set (`bench/intent`) has `{"code+spec": ["code"], "spec+examples": ["contract", "field:examples"]}` and `"compare": {"candidate": "spec+examples", "baseline": "code+spec", "token_ratio": [1, 2]}`, and froze the output of `bmb examples` in `examples` of its items (the program file holds the contract, so `contract` is not attached to `code+spec` a second time).
- When `frozen` lists that set's generator and `../review/views.py`, `../review/judge.py` and `../review/harness.py`, the MANIFEST binds them together (`harness.py --set DIR manifest --write` only when a new set is made).
- Keys of a change file: `id`, `intent`, `seed` (the path of the seed relative to the set directory; left out when there is none), `file`, `before`, `after`, `label` (`defect` or `clean`), and the texts to show with `field:`.
- A new part, when needed, is added to `views.py`. `views.py` and `harness.py` are in this set's MANIFEST, so changing them means freezing this set again (only before there are official results), and the output of the existing parts is not changed.
- The gate's `OtherSet` test runs this shape (other arms, ratio 1/2) on a temporary set. The gate of the real second set is `bench/intent/test_intent.py`.
