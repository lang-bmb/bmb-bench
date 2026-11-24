# brb-write-probe (H-PROBE)

A variant that `bench/ablate/gen.py` makes from `bench/brb-write` (frozen). It is not edited by hand; the generator makes it again. It differs from brb-write in one thing in `set.json`: the server flag `--probe-tool` (a read tool that tries a candidate invariant without a commit). The prompt, seed, tasks and judging are unchanged. The comparison and the refutation condition were registered in ADR-0109 before the run.
