# BVB sources, licenses and selection record (ADR-0034 §2)

## Sources and licenses

| Source | Repository | Pinned commit | License | What was used |
| --- | --- | --- | --- | --- |
| Verus-Bench (AutoVerus artifact) | https://github.com/microsoft/verus-proof-synthesis `benchmarks/Verus-Bench/` | `cbf9c0c6337b224fd8e5b7cb4e01ae65c0f98bc1` | MIT (Copyright (c) 2024 Microsoft), `licenses/verus-proof-synthesis.LICENSE` | the task list (`tasks.jsonl`), the specifications, the verified solutions (`*/verified/*.rs`) |
| Vericoding (the Verus part) | https://github.com/Beneficial-AI-Foundation/vericoding-benchmark | `387cd69996792d452ead7b0460f36ee4c5cdd148` | MIT (Copyright (c) 2025 Beneficial AI Foundation), `licenses/vericoding-benchmark.LICENSE` | the specifications (`jsonl/verus_tasks.jsonl`), the verified solutions (`vericoded/*_vericoded.rs`) |
| VeriContest (NeurIPS 2026, arXiv 2605.08553) | no public data repository found (searched 2026-10-25) | — | — | not used. The problem statements are the original text of LeetCode and Codeforces, so even if it is published the conditions of redistribution have to be checked separately |

- Both repositories are MIT, so the original Verus text (specifications, solutions) is redistributed as it is in the `verus` key of the task files. The copyright notices in the table above and the full texts in `licenses/` meet the MIT condition (keeping the notice).
- The two repositories come in turn from other public sets (Verus-Bench: CloverBench, MBPP-DFY-153, SV-COMP array-fpi (Diffy), the Verus tutorial; Vericoding: APPS, DafnyBench, HumanEval, Verina and others; see each repository's README). BVB does not carry over the problem statements of those originals. The task descriptions (`description`) are written anew from the specifications, and the only thing taken is the Verus code that the MIT repositories above distribute.
- Source check: `python3 bench/bvb/sources.py fetch DIR` fetches the pinned commits and `sources.py check DIR` checks that the original Verus text of the task files (`reference_origin: upstream`) and the given specification functions equal the originals. `sources.py select DIR` computes the selection below again from the originals and compares it with `tasks/` (it needs the network, so it runs outside the gate. Run on 2026-10-25: both passed).

## Selection procedure

**Verus-Bench (150 tasks), all of them.** One decision per task: it is ported, or excluded for one of the reasons below. Of duplicates (the same form of signature, the same specification) the one that comes first in `tasks.jsonl` stays.

**Vericoding Verus (2,166 tasks; the 168 of the quality problem list `verus_issues.jsonl` are already set apart upstream), a sample.**
1. Automatic filter (`vericoding_filter` in `sources.py`): one function to implement, parameters that are integers, `bool` or slices/`Vec` of them (no mutable `Vec`), an integer or `bool` result, and a specification without struct, string, real or set types and without sequence construction. 386 remain.
2. Sample order: ascending `sha256("bvb:" + id)` (a fixed order the author cannot choose).
3. In that order each one is looked at and ported or excluded with a reason, stopping at 15 ported. 37 were looked at.

| | Verus-Bench | Vericoding |
| --- | --- | --- |
| upstream tasks | 150 | 2,166 (+168 quality problems) |
| passed the automatic filter | — (all reviewed) | 386 |
| reviewed | 150 | 37 (the front of the sample order) |
| **ported** | **30** | **15** |
| excluded: returns or grows a `Vec` | 49 | — |
| excluded: invariant tasks on a fixed program (Diffy 38 + `cell_2_sum`) | 39 | — |
| excluded: tuple or `Option` result | 6 | — |
| excluded: nested `Vec` input | 6 | — |
| excluded: duplicate | 5 | 3 |
| excluded: `i128` result | 3 | — |
| excluded: proof-only task | 3 | — |
| excluded: specification with an existential `Seq::subrange` | 2 | — |
| excluded: specification that quantifies over indices outside the array | 2 | — |
| excluded: signed index result (−1) | 1 | 2 |
| excluded: `&mut` scalar | 1 | 1 |
| excluded: strings, permutation specification, `assume` | 1 + 1 + 1 | — |
| excluded: cannot be solved with the original types (`unsat`) | — | 11 |
| excluded: trivial specification (`true`, or always true by the types) | — | 2 |
| excluded: no input (a constant) | — | 1 |
| excluded: **no BMB reference solution could be written** | — | **2** |

**Disclosure of the selection bias (the fairness rules of ADR-0034).**
- Port rate: Verus-Bench 30/150 (20%), Vericoding 15/37 reviewed (41%), and 0.7% of all of Vericoding when the filter is counted. Most exclusions are features M1 does not have (`Vec`, strings, tuples, structs), and BVB does not measure those tasks. A BVB result is about "tasks with integers, slices, loops and recursion".
- **2 exclusions in BMB's favour:** for `VH0013` (maximality of gcd: needs an inductive lemma over all common divisors) and `VV0128` (perfect square: monotonicity of squaring has to be used under a quantifier) the author could not write a BMB reference solution, because M1 has no lemma functions and no `assert forall` (`VV0128` failed after an attempt). Verus can solve these tasks, so leaving the two out is a choice that leans toward BMB. It is stated with the results.
- **Left out on both sides:** the 11 `unsat` tasks are upstream defects where no implementation can satisfy the specification with the original types (counterexample inputs in the table below). Carried to BMB (64 bits) they would become solvable, so they are left out of the comparison.
- The reference solutions, weak controls and specification translations were all written by one author (the same bias as m1b).

## Decision table

This is the output of `python3 bench/bvb/sources.py table` (a test checks that this table and `sources.py` agree). The meaning of the reason codes is in `REASONS` of `sources.py`.

| Source | Decision |
| --- | --- |
| Verus-Bench `cloverbench_all_digits_strong` | excluded: string |
| Verus-Bench `cloverbench_array_append_strong` | excluded: vec-out |
| Verus-Bench `cloverbench_array_concat_strong` | excluded: vec-out |
| Verus-Bench `cloverbench_array_copy_strong` | excluded: vec-out |
| Verus-Bench `cloverbench_array_product_strong` | excluded: vec-out |
| Verus-Bench `cloverbench_array_sum_strong` | excluded: vec-out |
| Verus-Bench `cloverbench_binary_search` | `vb-clover-binary-search` |
| Verus-Bench `cloverbench_cal_div` | excluded: tuple-option |
| Verus-Bench `cloverbench_is_prime` | `vb-clover-is-prime` |
| Verus-Bench `cloverbench_linear_search2` | `vb-clover-linear-search` |
| Verus-Bench `cloverbench_two_sum` | excluded: tuple-option |
| Verus-Bench `diffy_brs1` | excluded: fixed-program |
| Verus-Bench `diffy_brs2` | excluded: fixed-program |
| Verus-Bench `diffy_brs3` | excluded: fixed-program |
| Verus-Bench `diffy_brs4` | excluded: fixed-program |
| Verus-Bench `diffy_brs5` | excluded: fixed-program |
| Verus-Bench `diffy_conda` | excluded: fixed-program |
| Verus-Bench `diffy_condg` | excluded: fixed-program |
| Verus-Bench `diffy_condm` | excluded: fixed-program |
| Verus-Bench `diffy_condn` | excluded: fixed-program |
| Verus-Bench `diffy_ms1` | excluded: fixed-program |
| Verus-Bench `diffy_ms2` | excluded: fixed-program |
| Verus-Bench `diffy_ms3` | excluded: fixed-program |
| Verus-Bench `diffy_ms4` | excluded: fixed-program |
| Verus-Bench `diffy_ms5` | excluded: fixed-program |
| Verus-Bench `diffy_res1` | excluded: fixed-program |
| Verus-Bench `diffy_res1o` | excluded: fixed-program |
| Verus-Bench `diffy_res2` | excluded: fixed-program |
| Verus-Bench `diffy_res2o` | excluded: fixed-program |
| Verus-Bench `diffy_s12if` | excluded: fixed-program |
| Verus-Bench `diffy_s1if` | excluded: fixed-program |
| Verus-Bench `diffy_s1lif` | excluded: fixed-program |
| Verus-Bench `diffy_s22if` | excluded: fixed-program |
| Verus-Bench `diffy_s2if` | excluded: fixed-program |
| Verus-Bench `diffy_s2lif` | excluded: fixed-program |
| Verus-Bench `diffy_s32if` | excluded: fixed-program |
| Verus-Bench `diffy_s3if` | excluded: fixed-program |
| Verus-Bench `diffy_s3lif` | excluded: fixed-program |
| Verus-Bench `diffy_s42if` | excluded: fixed-program |
| Verus-Bench `diffy_s4if` | excluded: fixed-program |
| Verus-Bench `diffy_s4lif` | excluded: fixed-program |
| Verus-Bench `diffy_s52if` | excluded: fixed-program |
| Verus-Bench `diffy_s5if` | excluded: fixed-program |
| Verus-Bench `diffy_s5lif` | excluded: fixed-program |
| Verus-Bench `diffy_sina1` | excluded: fixed-program |
| Verus-Bench `diffy_sina2` | excluded: fixed-program |
| Verus-Bench `diffy_sina3` | excluded: fixed-program |
| Verus-Bench `diffy_sina4` | excluded: fixed-program |
| Verus-Bench `diffy_sina5` | excluded: fixed-program |
| Verus-Bench `mbpp_task_id_105` | `vb-mbpp-105-count-true` |
| Verus-Bench `mbpp_task_id_113` | `vb-mbpp-113-is-integer` |
| Verus-Bench `mbpp_task_id_133` | excluded: i128 |
| Verus-Bench `mbpp_task_id_142` | `vb-mbpp-142-count-identical` |
| Verus-Bench `mbpp_task_id_145` | `vb-mbpp-145-max-difference` |
| Verus-Bench `mbpp_task_id_161` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_170` | excluded: i128 |
| Verus-Bench `mbpp_task_id_18` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_2` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_230` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_240` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_249` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_251` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_261` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_262` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_273` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_282` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_284` | `vb-mbpp-284-all-equal` |
| Verus-Bench `mbpp_task_id_290` | excluded: nested-vec |
| Verus-Bench `mbpp_task_id_3` | `vb-mbpp-3-is-non-prime` |
| Verus-Bench `mbpp_task_id_307` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_399` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_412` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_414` | `vb-mbpp-414-any-value-exists` |
| Verus-Bench `mbpp_task_id_424` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_426` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_431` | excluded: dup (= `mbpp_task_id_414`) |
| Verus-Bench `mbpp_task_id_433` | `vb-mbpp-433-is-greater` |
| Verus-Bench `mbpp_task_id_436` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_445` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_447` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_454` | `vb-mbpp-454-contains-z` |
| Verus-Bench `mbpp_task_id_457` | excluded: nested-vec |
| Verus-Bench `mbpp_task_id_460` | excluded: nested-vec |
| Verus-Bench `mbpp_task_id_461` | `vb-mbpp-461-count-uppercase` |
| Verus-Bench `mbpp_task_id_472` | `vb-mbpp-472-consecutive` |
| Verus-Bench `mbpp_task_id_474` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_476` | `vb-mbpp-476-sum-min-max` |
| Verus-Bench `mbpp_task_id_477` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_554` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_557` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_567` | `vb-mbpp-567-is-sorted` |
| Verus-Bench `mbpp_task_id_572` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_576` | excluded: subrange-exists |
| Verus-Bench `mbpp_task_id_578` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_579` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_586` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_588` | `vb-mbpp-588-max-min-diff` |
| Verus-Bench `mbpp_task_id_602` | excluded: tuple-option |
| Verus-Bench `mbpp_task_id_605` | excluded: dup (= `cloverbench_is_prime`) |
| Verus-Bench `mbpp_task_id_610` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_616` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_618` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_62` | `vb-mbpp-62-smallest` |
| Verus-Bench `mbpp_task_id_624` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_629` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_644` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_69` | excluded: subrange-exists |
| Verus-Bench `mbpp_task_id_70` | excluded: nested-vec |
| Verus-Bench `mbpp_task_id_728` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_732` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_733` | excluded: tuple-option |
| Verus-Bench `mbpp_task_id_741` | `vb-mbpp-741-all-same` |
| Verus-Bench `mbpp_task_id_743` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_755` | excluded: tuple-option |
| Verus-Bench `mbpp_task_id_760` | excluded: dup (= `mbpp_task_id_741`) |
| Verus-Bench `mbpp_task_id_764` | `vb-mbpp-764-count-digits` |
| Verus-Bench `mbpp_task_id_769` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_775` | `vb-mbpp-775-odd-at-odd` |
| Verus-Bench `mbpp_task_id_790` | excluded: dup (= `mbpp_task_id_775`) |
| Verus-Bench `mbpp_task_id_798` | excluded: i128 |
| Verus-Bench `mbpp_task_id_8` | excluded: vec-out |
| Verus-Bench `mbpp_task_id_804` | `vb-mbpp-804-product-even` |
| Verus-Bench `mbpp_task_id_807` | excluded: tuple-option |
| Verus-Bench `mbpp_task_id_808` | `vb-mbpp-808-contains-k` |
| Verus-Bench `mbpp_task_id_809` | `vb-mbpp-809-is-smaller` |
| Verus-Bench `mbpp_task_id_94` | excluded: nested-vec |
| Verus-Bench `mbpp_task_id_95` | excluded: nested-vec |
| Verus-Bench `misc_arg_free` | excluded: no-exec |
| Verus-Bench `misc_basic_nonlinear` | excluded: no-exec |
| Verus-Bench `misc_binary_search` | excluded: dup (= `cloverbench_binary_search`) |
| Verus-Bench `misc_bubble` | excluded: permutation |
| Verus-Bench `misc_cell_2_sum` | excluded: fixed-program |
| Verus-Bench `misc_choose_odd` | `vb-misc-choose-odd` |
| Verus-Bench `misc_conditional_average` | excluded: vec-out |
| Verus-Bench `misc_deduplicate` | excluded: vec-out |
| Verus-Bench `misc_fib` | excluded: vec-out |
| Verus-Bench `misc_filter` | excluded: vec-out |
| Verus-Bench `misc_filter_weak` | excluded: vec-out |
| Verus-Bench `misc_findmax` | `vb-misc-findmax` |
| Verus-Bench `misc_havoc_inline_post` | excluded: escape-hatch |
| Verus-Bench `misc_len_intersect` | excluded: no-exec |
| Verus-Bench `misc_linearsearch` | excluded: signed-index |
| Verus-Bench `misc_map` | `vb-misc-map` |
| Verus-Bench `misc_max_index` | `vb-misc-max-index` |
| Verus-Bench `misc_remove_all_greater` | excluded: vec-out |
| Verus-Bench `misc_reverse` | `vb-misc-reverse` |
| Verus-Bench `misc_simple_nested` | excluded: out-of-range |
| Verus-Bench `misc_sum` | `vb-misc-sum` |
| Verus-Bench `misc_tail_triangle` | excluded: mut-scalar |
| Verus-Bench `misc_trigger` | excluded: out-of-range |
| Vericoding `VJ0020` | excluded: dup (= `misc_findmax`) |
| Vericoding `VH0047` | excluded: unsat (base = height = 255: area 32512 > u8::MAX) |
| Vericoding `VD0791` | `vc-vd0791-month-30-days` |
| Vericoding `VA0523` | `vc-va0523-min-abs-diff` |
| Vericoding `VD0722` | `vc-vd0722-last-digit` |
| Vericoding `VH0013` | excluded: no-bmb-ref |
| Vericoding `VA0590` | `vc-va0590-boring-apartment` |
| Vericoding `VA0676` | excluded: unsat (r = 0, g = 127: 2g - r = 254 > i8::MAX) |
| Vericoding `VV0104` | excluded: unsat (a = [i32::MAX - 1, i32::MIN + 1]: even - odd overflows i32) |
| Vericoding `VA0205` | excluded: unsat (n = 127, m = 2: 253 days > i8::MAX) |
| Vericoding `VD0356` | excluded: unsat (n = 2^63: f(n) = 3 * 2^63 - 1 > u64::MAX) |
| Vericoding `VT0094` | excluded: no-input |
| Vericoding `VJ0055` | excluded: mut-scalar |
| Vericoding `VD0114` | excluded: dup (= `misc_max_index`) |
| Vericoding `VV0128` | excluded: no-bmb-ref |
| Vericoding `VV0033` | excluded: unsat (len >= 2^31: `nums.len() as i32` is negative, so result >= 0 && result <= it fails) |
| Vericoding `VA0532` | `vc-va0532-crackers` |
| Vericoding `VA0093` | `vc-va0093-max-balance` |
| Vericoding `VA0053` | `vc-va0053-aspect-pairs` |
| Vericoding `VD0727` | `vc-vd0727-calculate-loss` |
| Vericoding `VV0039` | `vc-vv0039-max-of-list` |
| Vericoding `VA0399` | `vc-va0399-late-brother` |
| Vericoding `VD0131` | excluded: unsat (v = [i32::MAX, i32::MAX]: both are peeks, sum 2 * i32::MAX > i32::MAX) |
| Vericoding `VA0219` | `vc-va0219-pyramid-height` |
| Vericoding `VH0043` | excluded: unsat (n = 127: 127 * 127 > i8::MAX) |
| Vericoding `VH0085` | excluded: unsat (n = 3: 100 + 90 - 10 = 180 > i8::MAX) |
| Vericoding `VD0126` | `vc-vd0126-first-zero` |
| Vericoding `VV0100` | excluded: trivial |
| Vericoding `VD0465` | `vc-vd0465-increasing-run` |
| Vericoding `VD0670` | excluded: unsat (a = [i32::MIN, -1]: sum < i32::MIN) |
| Vericoding `VS0021` | excluded: unsat (a = -128, b = 0: gcd 128 > i8::MAX) |
| Vericoding `VV0135` | `vc-vv0135-compare` |
| Vericoding `VD0199` | excluded: signed-index |
| Vericoding `VV0073` | excluded: trivial |
| Vericoding `VV0149` | excluded: dup (= `cloverbench_linear_search2`) |
| Vericoding `VD0239` | excluded: signed-index |
| Vericoding `VA0644` | `vc-va0644-takahashi-dates` |

## Reason codes

| Code | Meaning |
| --- | --- |
| `vec-out` | returns or grows a Vec (M1 has no heap or Vec) |
| `nested-vec` | takes nested Vecs (M1 slices hold only integers or bool) |
| `string` | takes a String or char (no strings in M1) |
| `tuple-option` | returns a tuple or an Option (no tuples, structs or enums in M1) |
| `i128` | result needs i128 (largest M1 integer is 64-bit) |
| `subrange-exists` | spec is an existential over Seq::subrange equality; in BMB it needs a named window predicate the agent cannot know (trigger matching), so it is not portable faithfully |
| `signed-index` | returns an index as a signed integer with a -1 sentinel; M1 has no integer conversion, so a spec cannot index with the result |
| `mut-scalar` | &mut scalar parameter (M1 references are slices only) |
| `permutation` | spec is a permutation of a Seq (needs sequence values) |
| `out-of-range` | spec quantifies over indices outside the array (Seq semantics) |
| `fixed-program` | invariant-synthesis task on a fixed program whose spec is a weak property of its output; as spec-to-code it is solved by a constant |
| `no-exec` | proof-only task or no specification to implement |
| `escape-hatch` | the original uses assume |
| `dup` | same signature shape and spec as an earlier upstream task (kept the first) |
| `unsat` | unsolvable as stated: the spec forces a result outside the original return type for some valid input |
| `trivial` | postcondition holds for every value of the result type |
| `no-input` | no input (a constant) |
| `no-bmb-ref` | the author found no BMB reference proof: M1 has no lemma functions or quantifier introduction (bias toward BMB, disclosed) |
| `upstream-issue` | listed in vericoding verus_issues.jsonl (upstream quality issue) |
