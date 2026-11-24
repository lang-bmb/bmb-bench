# 2r05, write variant: syntax A/B before and after ADR-0095 (`bench/m1b-write`)

The same comparison as `2r05` (`../2r05/`) on the official write surface (ADR-0101). The working tree is `2624533f`, and the compilers are `99138a9d` (before) and `2624533f` (after). The harness is `bench/m1/harness.py --set bench/m1b-write`.

## Verdict rule (registered before the first run, 2026-11-09)

1. It runs once with qwen (all tasks). If the difference of the write success rates is over D (30%p), the verdict is made on that difference.
2. If the difference is inside D, only the write tasks are repeated under the same conditions, up to 3 runs (ADR-0103 decision 2). The order alternates before→after, and session records are kept.
3. Verdict over the 3 runs: for each side the 95% interval of ADR-0077 §3 (`bench/repeat.py interval`).
   - If the lower end of after is above the upper end of before, it is "after is higher".
   - If the lower end of before is above the upper end of after, it is "after is lower".
   - Otherwise it is "inside run-to-run variation".
   - Whether to repeat is decided by the difference of the first run only.
4. Auxiliary metrics (not used for the verdict): rejected commits, limit reached, unstable tasks, model input tokens.
5. sonnet (ADR-0103 decision 3, the reference model of the claim) runs once with each of the two compilers at the same commit. A difference for sonnet is claimed only when it is over D (30%p). Otherwise it is reported with the qwen verdict as "direction only". sonnet is not repeated (ADR-0077 §2).

## Results (qwen3.8-27b, 2026-11-10)

| Run | Before | After |
| --- | --- | --- |
| 1 (37 tasks) | 25/25 | 22/25 |
| 2 (25 write) | 23/25 | 24/25 |
| 3 (25 write) | 24/25 | 24/25 |
| mean [95% interval] | 0.960 [0.861, 1.000] | 0.933 [0.819, 1.000] |

- The difference of run 1 (−12%p) is inside D, so by rule 2 it was repeated up to 3 runs.
- The verdict over the 3 runs is, by rule 3, **inside run-to-run variation** (the intervals overlap). The direction changes from run to run (−3, +1, 0).
- Auxiliary metrics:
  - Rejected commits: before 28, 37, 30; after 16, 13, 11; fewer in all three runs (sum 95 → 40).
  - Limit reached: 0 on both sides.
  - Unstable tasks: 2 before (w11, w24), 4 after (w02, w10, w11, w14).
- The after run of run 1 was resumed once after a container restart (`resumes`).
## sonnet (rule 5, 2026-11-10)

| | Before | After |
| --- | --- | --- |
| write successes | 25/25 | 25/25 |
| navigation successes | 12/12 | 12/12 |
| rejected commits (write) | 4 | 1 |
| model input tokens of the write tasks | 1.53 million | 1.75 million |

- The difference is 0, so by rule 5 nothing is claimed. Both sides are at the ceiling.
- Rejected commits go the same way as for qwen (fewer), but the numbers are small.
- The working tree is `2624533f`, and the result files are `sonnet-{before,after}.jsonl`.
