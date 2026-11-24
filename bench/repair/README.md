# H-REPAIR ablation (ADR-0078)

Hypothesis H-REPAIR: the counterexamples and repair suggestions (`fix`) of failure diagnostics reduce the repair iterations. Two variants are compared on the same tasks, model and commit.

| Variant | Set | Tool results the model sees |
| --- | --- | --- |
| (a) full | `bench/m1b-write` (frozen) | as they are now: the counterexample at the end of a diagnostic message, `fix` (suggested fixes, hints) |
| (b) ablated | `bench/m1b-write-norepair` (a frozen variant made by `gen.py`) | with the counterexamples (`; counterexample: ..`, `; unconfirmed counterexample: ..`) and every `fix` and `counterexample` field removed |

The two variants differ only in `"tool_filter": "no-repair"` of `set.json`. The m1 harness (`strip_repair` of `bench/m1/harness.py`) applies the filter to every tool result that goes to the model. Lines that are not JSON and lines with nothing to remove keep their bytes. The prompt is the same text too (the sentence "failures come with counterexamples" stays: changing it would make two differences). The code and location of a diagnostic and the sentence before the counterexample stay.

| File | Contents |
| --- | --- |
| `gen.py` | makes `bench/m1b-write-norepair` (`--check`: whether the committed variant equals a newly made one) |
| `compare.py` | the comparison table of two result files and the H-REPAIR verdict line |
| `test_gen.py` | gate: the generation agrees, the filter, counting failed proofs, the scripted agents, the verdict rule |

```
python3 bench/m1/harness.py --set bench/m1b-write run --agent openai:MODEL --out FULL.jsonl
python3 bench/m1/harness.py --set bench/m1b-write-norepair run --agent openai:MODEL --out NONE.jsonl
python3 bench/repair/compare.py FULL.jsonl NONE.jsonl
```

## Verdict rule (registered before the first run, 2026-11-02)

- **Metric:** (rejected commits `commits_rejected` + failed proofs `proofs_failed`) per successful write (`write`) session. `proofs_failed` is the number of writes whose proof failed after the commit and of `verify` calls whose proof failed (results with an error diagnostic, `proof_failed` of the m1 harness). Navigation tasks have no writes and are left out.
- **Confirmed:** the metric of (a) is at least 40% below that of (b) ((a) ≤ 0.6 × (b)). **Refuted:** otherwise. The two results must have the same agent, compiler commit and condition (`compare.py` refuses otherwise), and when one side has no successful write session or the metric of (b) is 0 it cannot be judged.
- The model is qwen (ADR-0078). (a) is a run of `m1b-write` at the same commit (the qwen run of the write-surface measurement, if it is at the same commit).
- The difference of the success rates is reported apart. With a single measurement no direction is claimed for a success-rate difference at or below the minimum difference D of ADR-0077.
