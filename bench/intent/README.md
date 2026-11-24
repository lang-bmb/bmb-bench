# INTENT: reviewing the specification + generated examples against reviewing code + specification (H-INTENT, ADR-0078)

Hypothesis H-INTENT: shown examples and counterexamples generated from the specification, a reviewer catches a specification that departs from the intent better than a review that reads the code and the specification together. An item is one proved program and its intent sentence, and the reviewer answers "does this contract say the intent".

This directory is the second set of the `bench/review` harness (data: `set.json`, `prompt.md`, `changes/`, `MANIFEST`). The views, the judging and the runs are `views.py`, `judge.py` and `harness.py` of `bench/review` as they are. There is no run with a real model yet (it is made on the measurement machine).

| File | Contents |
| --- | --- |
| `changes/*.json` | 90 items (a frozen product). The harness reads a set from `changes/`, hence the name; the program is the item's `after` (there is no `before`) |
| `gen.py` | the generator (frozen). `--check`: checks without a compiler. `--regen`: makes it again with the compiler and compares byte for byte. `--stats`: properties of the example output per label |
| `set.json` | the arms, the two arms compared, the criterion for the token ratio (1/2), the compiler commit that made the examples, the further files that go into the MANIFEST (frozen) |
| `prompt.md` | the reviewer's system prompt (frozen). Both arms use the same prompt. The question differs from that of `bench/review` |
| `MANIFEST` | SHA-256 of the frozen files above, `../review/{gen,views,judge,harness}.py` and `../bvb/MANIFEST`. On a difference the run is refused |
| `test_intent.py` | gate |

```
python3 bench/review/harness.py --set bench/intent manifest                 # check the freeze
python3 bench/intent/gen.py --check                                         # check the structure (no compiler)
python3 bench/intent/gen.py --regen                                         # make the examples again and compare byte for byte (compiler, about 1 minute)
python3 bench/intent/gen.py --stats                                         # properties of the example output per label (table below)
python3 bench/review/harness.py --set bench/intent sizes                    # view sizes per arm and label, and the token ratio (no model)
python3 bench/review/harness.py --set bench/intent view --arm spec+examples --change vb-mbpp-62-smallest.weak
python3 bench/review/harness.py --set bench/intent run --arm spec+examples --agent oracle --expect all-right
python3 bench/review/harness.py --set bench/intent run --arm code+spec --agent blind --expect none-detected
python3 bench/review/harness.py --set bench/intent run --arm spec+examples --agent openai:MODEL --out bench/intent/results/DATE-MODEL-examples.jsonl
python3 bench/review/harness.py --set bench/intent run --arm code+spec --agent openai:MODEL --out bench/intent/results/DATE-MODEL-code.jsonl
python3 bench/review/harness.py --set bench/intent table [--d PP] EXAMPLES.jsonl CODE.jsonl   # the table per arm and the H-INTENT verdict line
```

## The item set

Each of the 45 BVB tasks (`bench/bvb/tasks`, frozen) has an intent sentence, a `reference` (a contract that says the intent) and a `weak_reference` (a contract that is consistent and proved but does not say the intent). Per task there are two items with the same intent sentence.

| Item | Kind (`kind`) | Program | Hidden label | Count |
| --- | --- | --- | --- | --- |
| `<task>.reference` | `reference-contract` | `reference` | `clean` | 45 |
| `<task>.weak` | `weak-contract` | `weak_reference` | `defect` | 45 |

90 in all: 45 `defect`, 45 `clean`.

- Nothing is written by hand. The intent and the program text are as `bench/review/gen.py` makes them (the description of the task prompt; one file with the task's `put` code in unit `tasks`, and the BVB seed). The two items are the before and after of the `<task>.weaken` change of `bench/review` (the gate checks this).
- `examples` is the standard output of `bmb examples <the task's def> -- <seed>/src/given.bmb src/tasks.bmb` as it is (default count 3). The tool reads only `requires` and `ensures`, not the body. The target is the one function of the task; there are no examples for the helper functions that show in the contract text (three tasks).
- **The committed `changes/` is the frozen product.** The reviewer sees the committed example text (the tool is not run again at run time; the views are made without a compiler). The compiler commit used for the generation is `generated_with` in `set.json` (`8ba498b0`). `gen.py --check` makes everything except `examples` again byte for byte and compares, and looks at the shape of `examples` (JSONL rows of the target definition, the last one a summary, the counts of the summary equal to the rows, no paths).
- Basis of the labels (gate): all 90 programs pass `bmb verify`, and the m1 judging (ADR-0021 §2: the contract implies the task's hidden reference contract) accepts every `clean` and rejects every `defect`.

## Arms (`set.json`)

| Arm | ADR-0078 | What it sees |
| --- | --- | --- |
| `code+spec` | (a) code + specification | the whole program file (`src/tasks.bmb`): contract and body |
| `spec+examples` | (b) specification + generated examples and counterexamples | the contract text (the function's signature line, the `requires` and `ensures` lines, and the whole definitions of the `spec fn`s of the unit that those lines call: the extraction of `bench/review/views.py`) and the frozen output of `bmb examples` |

- Both arms get the intent sentence first. The seed's `given::..` is in neither arm (for the tasks that give that code, it is in the intent sentence).
- **Representation of the examples (frozen): the JSONL the tool printed, as it is.** The rows (`allowed`, `rejected`, `excluded`) and the summary row are shown line by line in their order. Nothing is rewritten or shortened (`rlimit` and `max_len` of the summary stay too). The prompt states the meaning of the three kinds, the meaning of two `allowed` lines for the same input, and that no rows, or `undecided` greater than 0, means the tool could not make examples, not that there are none.
- `code+spec` is the one program file only. The file holds the contract, so the contract text is not attached a second time (attaching it would add tokens to (a), which favours the hypothesis on the token criterion).
- Size is the bytes of the view and `ceil(bytes / 4)` tokens (ADR-0021 §4). The message size with the intent sentence is given as well.

## Verdict (registered before the first run, 2026-11-12)

The shape of the answer and the judging are those of `bench/review` (`judge.py`). For every item the reviewer answers in one request (no tools, no retry) with one `{"verdict": "defect" | "ok", "reason": "one line"}`.

- **Detection:** `"defect"` on a `defect` item. **False alarm:** `"defect"` on a `clean` item. **Format error:** an answer that is not that one object. Counted apart, neither a detection nor a false alarm, and it stays in the denominator.
- **Detection rate** = detections / 45, **false alarm rate** = false alarms / 45, **amount read** = the mean of the view tokens (90 items).

The H-INTENT row of ADR-0078 as it is:

> Confirmed: the detection rate of (b) is at least that of (a) (inside D counts as equal), and the tokens (b) reads are 1/2 or less of those of (a). Refuted: the detection rate of (b) is lower than that of (a) by more than D

- On this set: **refuted** if the detection rate of `spec+examples` is lower than that of `code+spec` by more than D; otherwise **confirmation condition met** if the mean view tokens of `spec+examples` are 1/2 or less of those of `code+spec`; else **not confirmed**. D is the minimum difference of ADR-0077 §4, and while this set has no repeated measurement it is the global value of 30%p (`table --d`).
- `table` always computes the value of the rule but gives the verdict line only for the two arms of one model run (one result file per arm, the same set, MANIFEST, model and commit, all items, nothing uncommitted). Otherwise it is `not judged (reason)`.
- Models as in ADR-0066: qwen first, sonnet as the cross-check. The hypothesis is confirmed when both models meet the condition. The false alarm rate is not in the rule and is reported with it.

**The only evaluators are model reviewers.** ADR-0078 §3 kept a human sample for calibration, but the calibration with a human sample is not done (decided by a person on 2026-11-11). The verdict on this set holds for model reviewers only and is not carried over to human reviewers.

## To be known beforehand

These values were measured deterministically before any model run (the re-freeze at commit `8ba498b0`, ADR-0134; the first freeze was `ba563ed4`; the gate fixes the numbers). The composition and the representation were fixed first and measured then, and were not changed to fit the ratio.

- **The token criterion (1/2) cannot be met on this set.** Mean view tokens (`harness.py --set bench/intent sizes`):

| Label | Items | `code+spec` | `spec+examples` (contract + examples) | Ratio (b)/(a) | Ratio with the intent sentence |
| --- | --- | --- | --- | --- | --- |
| all | 90 | 216.1 | 359.0 (85.3 + 241.7) | 1.662 | 1.486 |
| `clean` | 45 | 221.4 | 341.9 (91.7 + 218.3) | 1.544 | 1.403 |
| `defect` | 45 | 210.7 | 376.1 (78.9 + 265.2) | 1.785 | 1.572 |

  (In parentheses are the tokens of the two parts; the rest is the title lines.) The example output alone (241.7) is larger than the whole program (216.1). The contract text alone is 0.39 times the program, so the examples would have to be under 22 tokens on average (less than one JSONL line) to reach 1/2. 0 of the 90 items have a ratio of 1/2 or less. This is because a task is one function with a short body. So the verdicts this set can give are only **refuted** and **not confirmed**, and what it measures is the detection rate. The criterion was not changed.
- **The examples the tool gives differ by label (`gen.py --stats`).**

| Property of the example output | `clean` (45) | `defect` (45) |
| --- | --- | --- |
| no rows at all | 0 | 0 |
| no `allowed` row | 0 | 0 |
| no `rejected` row | 0 | 2 |
| no `excluded` row | 16 | 16 |
| `undecided` > 0 | 4 | 3 |
| `reason` in the summary (no query) | 0 | 0 |
| two `allowed` results for one input | 5 | 44 |
| has `allowed` rows and one result per input | 40 | 1 |
| mean number of rows | 7.93 | 9.93 |

  - **Every item has `allowed` rows.** In the first freeze (`ba563ed4`) the items without `allowed` rows were 10 `clean` and 2 `defect` (for reference contracts that go through a recursive `spec fn` the solver found no model). That difference was a shortcut, "no examples means `ok`". After the tool came to write recursive definitions as recursive functions and to ask with small inputs written in (ADR-0134), the set was frozen again and that shortcut is gone. Items with `undecided` > 0 are 4 against 3, and all have rows (one more row of some kind did not come out).
  - **"Two `allowed` results for one input" almost separates the labels.** The rule that answers `defect` when such a row exists and `ok` otherwise gets 84 of the 90 right (93.3%) without reading the contract or the intent: detection 44/45, false alarms 5/45. A weak contract does not fix the result, so the tool shows a second result (which is what the tool is for), and the prompt states that meaning. So the detection rate of `spec+examples` may be a reading of this one signal. It is wrong on tasks whose intent does not fix one result: the 5 that are `clean` and show a second result (`vb-clover-binary-search`, `vb-mbpp-145-max-difference`, `vb-misc-choose-odd`, `vb-misc-findmax`, `vc-vd0465-increasing-run`) and the 1 that is `defect` with one result per input (`vb-misc-max-index`). The false alarm rate has to be read with it, and the false alarms on these five are looked at apart.
  - **The amount follows the label too.** In 39 of the 45 tasks the `defect` side has more example rows (equal in 4, fewer in 2), and the example tokens are 265.2 against 218.3 on average. Totals of rows: `clean` has 147 `allowed`, 135 `rejected`, 75 `excluded` and 8 undecided; `defect` has 245, 127, 75 and 4.
- **No task has the same example text for its two items.** In all 45 tasks the examples differ by label.
- **The `code+spec` arm has a size difference too.** The weak contract is shorter, so the program is 210.7 against 221.4 tokens on average and the contract text 78.9 against 91.7.
- **Every defect is "the contract says less".** The 45 `defect` items are BVB's `weak_reference`: a contract weaker than the intent. The other forms of "consistent but with another meaning" that ADR-0078 names (a contract that states strongly something other than the intent, a contract whose `requires` is too narrow) are absent. The second `allowed` result is a signal that only a weak contract produces, so the result is not generalized to such defects.
- **Pairs.** The two items of a task have the same intent. A review is an independent request per item, so the reviewer does not see the pair.
- The intent sentence states directly "what the contract has to say" (the sentence of the BVB prompt). It is closer to a specification than a real description of intent is. The task bias is BVB's (integers and arrays, units of one function). One item is 2.2%p of the detection rate.
- **Regeneration and the gate.** The examples are the solver's answers, but with a fixed seed and `rlimit` they are the same bytes under the same compiler (made again on this machine and equal, about 1 minute). So the gate (`test_intent.py`) makes them again with the current compiler and compares them with the committed text. When the compiler changes and the tool's output differs, that test fails. The committed text is not edited then (what the model sees is the frozen product). If there are no official results, the set is made again at the new commit and frozen again; if there are, the comparison is taken out of the push gate, as with `--regen` of `bench/review`, and run only with the compiler of the `generated_with` commit (the decision goes into an ADR).
- `views.py`, `judge.py`, `harness.py` and `../review/gen.py` are in the MANIFESTs of both sets. Changing them means freezing both sets again.
