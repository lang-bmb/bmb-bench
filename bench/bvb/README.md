# BVB: BMB-Verus Bench (ADR-0034 §2)

Of the public Verus tasks (Verus-Bench, Vericoding), the 45 that can be carried into the M1 language (ADR-0016) are ported as BMB tasks, and the same tasks are solved under the same rules in the original Verus toolchain, so that the first-attempt success rates of the same model are compared directly. Sources, licenses and the selection record are in `SOURCES.md`.

| File | Contents |
| --- | --- |
| `prompt.md` | the agent's system prompt (frozen). Byte for byte the same as `bench/m1/prompt.md` |
| `seed/` | the starting workspace (frozen). One unit `given`: the 11 specification functions that the originals use in their specifications for recursion and triggers (rule G1) |
| `tasks/` | 45 tasks (frozen): 30 from Verus-Bench (`vb-*`), 15 from Vericoding (`vc-*`). All are write tasks |
| `MANIFEST` | SHA-256 of the frozen files. On a difference both harnesses refuse to run |
| `port/`, `port.py` | the task sources (in a form a person reads). `port.py build` makes `tasks/` and `port.py check` catches a mismatch |
| `sources.py`, `licenses/` | the pinned upstream commits, the selection record (the decision and reason for every upstream task), the source check |
| `verus/` | the harness of the original-Verus comparison side: installation, prompt, judging, comparison table |

```
python3 bench/m1/harness.py --set bench/bvb manifest                       # check the freeze
python3 bench/m1/harness.py --set bench/bvb run --agent oracle --jobs 4    # BMB reference solutions: all succeed (gate)
python3 bench/m1/harness.py --set bench/bvb run --agent weak --jobs 4      # BMB weak controls: all fail (gate)
bench/bvb/verus/install.sh [--dry-run]                                     # install the pinned Verus release
python3 bench/bvb/verus/harness.py run --agent oracle --jobs 4             # original Verus solutions: all succeed (CI bvb-verus)
python3 bench/bvb/verus/harness.py run --agent weak --jobs 4               # Verus weak controls: all fail (CI bvb-verus)
python3 bench/bvb/verus/harness.py compare BMB.jsonl VERUS.jsonl           # BMB and Verus side by side per task
python3 bench/bvb/verus/harness.py strength RESULTS.jsonl                  # specification strength and total tokens of one run (either side)
```

## Task format

The keys of an `m1b` write task (`prompt`, `signature`, `accept`, `reference`, `weak_reference`) plus the following. `bench/m1/harness.py` reads these keys without changing the judging of `m1` and `m1b`.

| Key | Meaning |
| --- | --- |
| `source` | the upstream benchmark, the upstream task (`origin`, `path`), the porting rules applied |
| `ref_*` helper predicates in `accept.specs` | helper predicates the hidden reference contract uses. All go into `#[uses]` of the judging definitions (before, only `ref_pre` and `ref_post`) |
| `frozen` | the `given` definitions the hidden contract calls by name. At judging their definition hashes must equal the seed's (`given_intact`). This blocks an answer that changes them to pass the specification check |
| `verus` | the original Verus side: a `prompt` with the same description and the original signature, `signature`, `target`, the original specification (`specs`, `pre`, `post`; helper functions only renamed to `bvb_ref_*`), a verified solution `reference` with its origin `reference_origin`, and `given` for G1 tasks |

The prompts of the two languages use the same description (`description`) and differ only in the signature at the end. The BMB side has the one line "Create unit `tasks`" in front. For G1 tasks both sides show the code of the given specification functions in the prompt.

## Porting rules

| Rule | Original (Verus) | BMB |
| --- | --- | --- |
| T1 | `&Vec<T>`, `Vec<T>` (read only), `&[T]`; `&mut Vec<T>` that does not change the length | `&[T']`; `&mut [T']` |
| T2 | `i8`, `i16`, `i32` / `u8`, `u16`, `u32` / element `usize` | `i64` / `u64` / `u64`. When the range of the original type affects the computation or the specification (overflow, input domain), that range goes into the hidden `requires` and the description. When it does not, it is left out (the solution has to be right over all 64 bits, so the task is not weakened) |
| T3 | `exists\|x\| P` | `!(forall\|x\| !P)` (M1 has no `exists`) |
| T4 | recursive specification over `Seq` (`drop_last`/`last`) | a recursive specification function over the prefix length `n` |
| T5 | `int` specification function | an `i64` specification function with the same expression (specification arithmetic is over unbounded integers, ADR-0017 §2) |
| T6 | a clause that is always true by itself (`exists\|i\| (range ==> ..)`) | left out, as its meaning (`true`). Left out of the hidden contract of the Verus side too (`vb-misc-findmax`) |
| T7 | `/` and `%` of `int` (Euclidean) | for a negative dividend, carried over as `(n % d + d) % d` and the quotient that matches it (BMB truncates toward 0) |
| G1 | the original specification is a recursive specification function, or a quantifier's trigger is an arithmetic expression and needs a named predicate | the function is **given** to the task as in the original (BMB `given::f`, the Verus starting file). If the two contracts were written with recursive functions of different names, proving the implication would need induction and the specification strength check would lose its meaning. The original Verus-Bench and Vericoding tasks gave these functions too |

The hidden contract is a translation of the original specification. The triggers of quantifiers, though, are put on array element terms (`a[i]`) (the Verus side does the same, and for this the trigger annotation of one original solution was changed: `vb-mbpp-113`, `reference_origin: upstream-triggers`). Two original solutions (`vb-misc-reverse`, `vb-misc-map`) were moved to the `&mut` postcondition syntax of the pinned Verus version (`final(v)`) (`upstream-migrated`). The Verus solutions of the 5 Vericoding tasks without an original solution were written for BVB (`bvb`).

## Judging

- **BMB:** ADR-0021 §2 as it is (the whole workspace proved, the signature, implication of the hidden contract) + `given_intact` for G1 tasks.
- **Verus (`verus/harness.py`):** the same idea carried to Verus. (1) The last file verifies with `verus --no-cheating` (`assume`, `admit`, `external_body` and `assume_specification` are refused, to match BMB M1 having no escape hatch). (2) The target function's signature is the same (ignoring `pub`, whitespace and the result name). (3) With `fn bvb_check(..) requires original pre ensures original post { target(..) }` appended to the file, it verifies again. For G1 tasks the given functions must be unchanged.
- **Weak controls:** for BMB a weak specification written per task, for Verus the original solution with the target function's `ensures` removed (automatic). Both must verify and fail the specification check.
- **Session rules (fairness):** one session per task, no retry, 40 tool calls, the same model settings (effort and `max_tokens` of `bench/m1/anthropic_agent.py`). The Verus agent has three tools, `read_file`, `write_file` and `verify`; BMB has the MCP tools. Neither has a file system or a shell. `task_set` of the result files is `bvb` for BMB and `bvb-verus` for Verus, and `compare` makes a table only when the MANIFESTs of the two files are the same.

## Metrics of the comparison table (H-SPEC, H-FAMILIAR)

`compare` gives two more columns beside the first-attempt success rate. Both were fixed before the runs with a real model.

- **Specification strength:** of the tasks whose final code verifies with the right signature, the share whose agent contract implies the hidden original contract (`spec_accepted`). Implementation failures are not in the denominator, so this reads the specification apart from the first-attempt success rate. The reference solutions must give 45/45 on both sides and the weak controls 0/45 (gate `bench bvb oracle` and `weak`, CI `bvb-verus`).
- **Total model tokens:** the sum of input and output (prompt included).

H-FAMILIAR (ADR-0040 §4) is refuted when the BMB first-attempt success rate ≤ that of Verus. For H-SPEC the BSB is the main verdict and the BVB specification strength an auxiliary column.

## Comparison with a real model (the user's machine, paid)

```
bench/bvb/verus/install.sh                       # the pinned Verus 0.2026.10.04.426d8b0 + Rust 1.98.1 (about 500 MB)
python3 bench/m1/harness.py --set bench/bvb run --agent anthropic:MODEL --out bench/bvb/results/$(date +%F)-MODEL.jsonl
python3 bench/bvb/verus/harness.py run --agent anthropic:MODEL --out bench/bvb/results/$(date +%F)-MODEL-verus.jsonl
python3 bench/bvb/verus/harness.py compare bench/bvb/results/DATE-MODEL.jsonl bench/bvb/results/DATE-MODEL-verus.jsonl
```

## Known limits

- **The specification strength check is sensitive to triggers (in both languages).** When an agent's quantifier has its trigger only on an application of its own predicate (`p(a[i])`), the solver may not find the implication to the hidden contract even though the meaning is the same. The hidden contracts reduce this risk with element-term triggers but do not remove it. A task that fails only `spec_accepted` in the results of a real model is checked for this possibility.
- **A BMB completeness problem (found while porting):** a specification function that takes an `i64` array element as an argument is not unfolded inside a quantifier. Example: from `forall|i| i < a.len() ==> small(#[trigger] a[i])` it does not prove `forall|i| .. ==> a[i] < 5` (it does for `u64`). The cause is that `fresh_elems` in `verify.rs` adds the element range axiom only for unsigned elements, and the definition axiom of a specification function has the argument range as its guard (ADR-0017 §4). The hidden contracts and reference solutions of BVB avoid this form, but an agent writes it naturally. It is a candidate to fix before a real measurement.
- For the selection bias see "Disclosure of the selection bias" in `SOURCES.md`.
