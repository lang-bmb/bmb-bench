# brb-write-undecided (H-UNDECIDE)

A variant that `bench/ablate/gen.py` makes from `bench/brb-write` (frozen). It is not edited by hand; the generator makes it again. It differs from brb-write in one thing in `set.json`: the server flag `--undecided-info` (the verdict of a bounded search on an undecided obligation). The prompt, seed, tasks and judging are unchanged. The comparison and the refutation condition were registered in ADR-0108 before the run.
