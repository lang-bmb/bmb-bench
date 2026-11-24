# 2r05: syntax A/B before and after ADR-0095 (qwen3.8-27b)

The frozen harness of one working tree (`2624533f`; `bench/m1/harness.py --set bench/m1b`, ADR-0066) was run with two compilers. `2r05` is the label of this measurement.

- Before: the `bmb` of commit `99138a9d`, right before ADR-0095.
- After: the `bmb` of `2624533f`.
- `commit` of the result rows is the commit of the working tree, so it is `2624533f` in both files.

| File | Contents |
| --- | --- |
| `qwen-r1-before.jsonl`, `qwen-r1-after.jsonl` | run 1, 37 tasks (25 write, 12 navigation). No session records. The after run was resumed twice, after a container restart and a 2-hour limit (`resumes`) |
| `qwen-r{2,3}-{before,after}.jsonl`, `.sessions/` | runs 2 and 3 (`repeat` 2 and 3), the 25 write tasks, with session records. Runs cut by the time limit were resumed |

The write first-attempt success rate of run 1 is 20/25 before and 24/25 after. The difference of +16%p is inside the minimum difference D (30%p), so by ADR-0103 decision 2 it is repeated up to 3 runs at the same commit and condition.

- Only the 25 write tasks are repeated. The navigation tasks were 12/12 on both sides in run 1 (the ceiling).
- The order alternates before→after→before→after, and session records are kept.
- Verdict and interpretation: the write success rate is 0.813 [0.711, 0.885] before and 0.920 [0.821, 1.000] after; the intervals overlap, so it is inside run-to-run variation (the direction is after higher in all three runs). Rejected commits fell from 60 to 26.
