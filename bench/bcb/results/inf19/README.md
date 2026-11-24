# inf19: BCB CPU measurement overlapping with measurement sessions

`inf19` is the label of this measurement. The same BCB piece was run 3 times under each of two conditions.

- Piece: a body-heavy history with N=100, K=40 (`H.jsonl`, no copy kept), `bcb.py run --arms rust,b1`.
- Compiler: the release `bmb` of `a512adfb`.
- Overlap (`overlap-*`): run at the same time as 2 qwen measurement sessions. Load average 1.3 to 1.4 (`overlap.log`).
- Quiet (`quiet-*`): run without model sessions. Load average 0.1 to 0.9 (`quiet.log`).

| Cumulative CPU (0 events) | Overlap | Quiet |
| --- | --- | --- |
| R1 | 14.0, 14.3, 14.1 s | 15.5, 15.2, 15.5 s |
| B1 | 5.4, 5.6, 5.7 s | 5.7, 6.1, 6.0 s |
| C_B1/C_R1 | 0.390, 0.390, 0.403 | 0.365, 0.402, 0.388 |

## Verdict

- The difference in absolute seconds between the conditions (R1 about 9%) is larger than the variation within a condition (about 2%).
- But its direction is the opposite of contamination. The overlapping side was faster. So it is taken as host variation that arose over a few hours, not as the overlap.
- For the ratio C_B1/C_R1, the quantity the verdict uses, the ranges of the two conditions overlap.

## Conclusion

- The `2a14e` measurement may run overlapping with measurement sessions.
- This piece ran both arms in one run (`--arms rust,b1`). But `suite` (the `2a14e` measurement) runs each arm separately, hours apart.
- So C_B1/C_R1 of `2a14e` is a ratio between runs and carries the host variation seen here (about 9% in absolute seconds).
- `2a14e` handles that variation by a verdict rule (`../2a14e/README.md`, registered before the measurement).
- The only overlap checked is with model sessions of a BMB arm (load about 1.4). Overlap with judging that runs compilation, the gate or cargo test was not checked (the rule of the BCB README stands).
