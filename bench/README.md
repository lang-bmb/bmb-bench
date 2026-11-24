# Benches

| Directory | Bench | Model |
| --- | --- | --- |
| `m1`, `m1b` | first-attempt success rate of writing and navigation, BSB kill rate (ADR-0021, 0025, 0035) | needed |
| `bvb` | tasks ported from Verus, compared with the original Verus (ADR-0038) | needed |
| `impossible` | BMB-Impossible: honest report against passing the gate on an infeasible contract (H-GAME) | needed (not for the certificates and controls) |
| `brb` | BMB + proof against Rust + tests (G5, H-ORACLE, G8) | needed |
| `brb-encap` | changing a data structure: type invariants against private fields + tests (H-ENCAP) | needed (not for the reference, weak and gaming solutions) |
| `brb-encap-b` | the new operation of `brb-encap` as an `impl` method (H-ENCAP) | needed (not for the reference, weak and gaming solutions) |
| `brb-effect` | tasks with output and state: the remaining test area (H-EFFECT) | needed (not for the reference and weak solutions) |
| `brb-hard` | defects that tests miss easily, 12 tasks ported from QuixBugs (H-ORACLE) | needed (not for the reference and weak solutions) |
| `repair` | `m1b-write-norepair`, the ablation variant of `m1b-write` (tool results without counterexamples and `fix`, H-REPAIR), and its verdict | needed (not for the scripted agents) |
| `ablate` | the six ablation variants of `bvb-write` and `brb-write`: `-undecided` (`--undecided-info`, H-UNDECIDE), `-probe` (`--probe-tool`, H-PROBE), `-stateless` (stateless repair turns, H-HISTORY). Each differs from its original in one thing in `set.json` (ADR-0136) | needed (not for the scripted agents) |
| `review` | reviewing a change: the specification diff (with the `bmb weaken` verdict) against the code diff, 143 changes made from BVB (H-REVIEW) | needed (not for the scripted reviewers) |
| `intent` | reviewing a contract: specification + the examples and counterexamples of `bmb examples` against code + specification, 90 items made from BVB (H-INTENT). The second set of the `review` harness | needed (not for the scripted reviewers) |
| `bnb` | map tools against file tools (Rust twin) | not needed for the oracle arm |
| `twin` | port-twin harness: comprehension, refactoring and tasks on the BMB workspace and the Rust crate of the same program (ADR-0104) | needed (not for the reference and weak scripts) |
| `bcb` | cumulative verification cost (ADR-0042) | not needed |
| `m3` | generated code bases | not needed |
| `baseline` | performance baseline (against safe Rust) | not needed |

## Names of measurements

Some result directories and scripts are named after the label a measurement was planned under, for example `bench/twin/results/3p-17/`, `bench/bnb/results/3a06/`, `bench/bcb/results/inf19/`, `bench/syntax/results/2r05/` and `bench/twin/run_3p05a.sh`. Such a name is only the label of that measurement: the README beside the rows says what was measured. The `task` field of `bench/waiting.json` holds labels of the same kind for runs that have not been made yet. The replay tasks of `bench/twin` quote the subjects of the commits they replay as they were written, with the labels those subjects carry.

## The `commit` field of a result row

Rows written before `bench/` moved to this repository (`bench/SOURCE` names the commit of the move) have one commit field: `commit` is a commit of `lang-bmb`, which then held the compiler, the harnesses and the sets together. Rows written from this repository carry two: `commit` is a commit of this repository (the harness and the sets), and `lang_bmb_commit` is the commit of the `lang-bmb` checkout that `LANG_BMB` names (the compiler). The harnesses that take their condition fields from `bench/m1/harness.py` write both (`bench/lang_bmb.py`). `bench/review/harness.py` and `bench/bcb/bcb.py` are frozen and write only `commit`; for their rows the compiler's commit has to be recorded with the run. The tables that frozen harnesses print keep their old label for the `commit` field, the Korean for "compiler commit": read it as the `commit` field as described here.

## Measurements with a real model: one command (`run_models.py`)

It runs the frozen task sets that need a model through the existing harnesses in a fixed order (by default the official write surface of ADR-0101: bvb-verus, brb-rust, m1b-write, bvb-write, brb-write. The transaction originals m1, m1b, bvb and brb-bmb run only when named, and a metric is read from the write variant when there is one), and gives every summary, and whether each metric was filled, in one report. Each harness checks its own MANIFEST and keeps the rule of one attempt without retry (ADR-0021).

```
python3 bench/run_models.py --dry-run                     # to the end with the scripted reference solutions (no cost). The gate uses --limit 2
python3 bench/run_models.py --agent openai:qwen3.8-27b \
    --price-in 0 --price-out 0 --budget 0 --report report.md        # the default model (ADR-0066, local)
python3 bench/run_models.py --agent anthropic:claude-sonnet-5-5 \
    --price-in P --price-out Q --budget USD --report report.md      # frontier cross-check
python3 bench/run_models.py --agent ... --sets brb-bmb,brb-rust   # only some, or the rest after a stop by the budget
```

- **Model environment (ADR-0066).** The agent kinds are `openai:MODEL` (Chat Completions) and `anthropic:MODEL` (Messages API), and the address comes from the environment: `BMB_GATEWAY` (the URL of a gateway that serves both APIs under `/openai/v1` and `/anthropic/v1`) or `BMB_OPENAI_BASE_URL` and `BMB_ANTHROPIC_BASE_URL` (either base URL whole). The repository does not hold the gateway's host name, and in the result rows and session records it reads `<gateway>`. The environment supplies the credentials and the repository holds no keys (`bench/m1/model_api.py`). The default is `qwen3.8-27b`; `claude-sonnet-5-5` is used only for the cross-check on the same sets at the same commit. `run --agent` of each harness takes the same strings.

- **Prices are arguments.** Prices change, so give USD per million tokens from the provider's price list.
- **Budget guard.** After each set the spend is computed from the recorded tokens, and before the next set starts its cost is projected as (the mean cost per session so far × the number of sessions of that set). When spend + projection exceeds the budget, that set and the ones after it do not start. A set is never cut in the middle, so the budget can be exceeded by one set. The first set (m1, 15 sessions) has no projection.
- **Interruption and resumption.** A harness appends the result row as each session ends (the first line is a `partial` header that identifies the run), and when the set ends it writes the rows again in task order and adds the summary row. Run again with the same arguments, a set finished at this commit with this model is not run again and goes into the report, and a set left partial continues from the tasks without a row. A task with a row is not run again, so this is not a retry. The number of resumptions stays in `resumes` of the summary.
- **Refused before the start.** An uncommitted tree (`+dirty` results are not used in a report), a MANIFEST mismatch, bvb-verus selected without Verus (`bench/bvb/verus/install.sh`). When a results file of the same date and model at another commit already exists, it is not overwritten. Result files (`bench/*/results/`) do not count as uncommitted changes.
- **Where the results go.** `bench/<set>/results/<date>-<model>[-verus|-bmb|-rust].jsonl`. The reports are written from these files.
- **Metrics filled in one go.** G2 (write first-attempt success rate of m1 and m1b), G3 (BSB kill rate of m1b), H-SPEC auxiliary (BVB specification strength), H-FAMILIAR (BVB, BMB against Verus; needs Verus), G5, H-ORACLE and G8 (BRB). The result rows keep the final files (BRB `final_sources`), so a metric defined later is computed without running again.
- **Per-turn context record (optional).** With `BMB_CONTEXT_LOG=1` the result rows also get the input and output tokens of each request (`model_usage.request_input_tokens`, `request_output_tokens`) and the tool and result bytes of each call (`calls`). It is off by default and the rows are then unchanged; what the model sees is the same either way.
- The gate (`bench run_models (dry run)`) runs without Verus, so it reports H-FAMILIAR as "skipped" and checks that every other line is filled.
