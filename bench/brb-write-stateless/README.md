# brb-write-stateless (H-HISTORY)

A variant that `bench/ablate/gen.py` makes from `bench/brb-write` (frozen). It is not edited by hand; the generator makes it again. It differs from brb-write in one thing in `set.json`: `"history": "stateless"` (every repair turn gets the fixed context, the current state and one line per attempt). The prompt, seed, tasks and judging are unchanged. The comparison and the refutation condition were registered in ADR-0110 before the run (the Rust arm is `harness.py --history stateless`).
