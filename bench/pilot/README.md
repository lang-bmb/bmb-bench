# Pilot runs (ADR-0058 T0)

The frozen tasks are run with the Claude Code CLI as the agent under test. It is a marked temporary measure to get data for judging the direction before the official path (automatic runs with an API key) was approved. It ends when the official path exists.

**A pilot is not an ADR-0021 measurement.** Every result row carries `"pilot": true`. These results are used only for the "pilot" state of the hypothesis register and for judging priorities, and not as the basis of a claim in the documents.

| File | Contents |
| --- | --- |
| `cli_pilot.py` | runs `claude -p` once per task in an empty directory and scores with the harness's judging |
| `mcp_proxy.py` | MCP relay between the CLI and `bmb mcp`. The harness's metrics (tool calls, bytes read, commits, E02xx), the limit of 40 calls, and the `answer` tool of navigation tasks |
| `verus_pilot.py`, `verus_mcp.py` | the Verus side of BVB: the three tools of the Verus harness (`read_file`, `write_file`, `verify`) and its judging in the same kind of CLI session |
| `brb_pilot.py`, `rust_mcp.py` | BRB: uses the frozen harness `bench/brb/harness.py` as a library for the same workspace, crate, prompts, tools and hidden judge; only the session is the CLI. The tools of the Rust side are `rust_tools.py` wrapped as MCP. The harness's limit on output tokens per session (64,000) cannot be kept |
| `results/` | result JSONL (the last line is the summary) |

```
python3 bench/pilot/cli_pilot.py --set bench/m1 --model claude-opus-5-5 --jobs 3 --out bench/pilot/results/DATE-m1-MODEL.jsonl
```

## What is the same as the official measurement, and what differs

| Item | Official (`bench/m1/anthropic_agent.py`) | Pilot |
| --- | --- | --- |
| tasks, MANIFEST, prompt | the frozen ones | the same (`prompt.md` is the whole system prompt, `--system-prompt`) |
| tools | `bmb mcp` only | the same (`--tools ""`, `--strict-mcp-config`, the working directory is an empty directory outside the repository) |
| call limit, retries | 40 calls, one session per task | the same (the relay keeps the limit) |
| judging | the harness | the same functions (`judge_write`, `spec_kill`, `judge_navigate`) |
| reasoning effort | `high` | the same (`--effort high`) |
| agent loop | the harness calls the Messages API directly | the CLI holds it (prompt cache, thinking, internal retries, calls of auxiliary models) |
| cost record | tokens | the tokens the CLI reports and `total_cost_usd` |

## Results (2026-10-28, model `claude-opus-5-5`)

### Second run (r2, commit `d39ff084`): the one used for verdicts

The first run (below) had a defect of the pilot runner. The CLI does not put a tool result over a certain size into the conversation; it moves it to a file and shows only the first 2 KB. The pilot agent has no tool to read files. So some sessions did not see large `map` and `query` results (the first call of `m1b/n12-io`, `map L1`, 59,442 bytes). The official adapter passes results on as they are, so this is a defect of the pilot condition. It was fixed by `mcp_proxy.py` raising the threshold through `_meta` of the tool definitions (`anthropic/maxResultSizeChars`) and `cli_pilot.py` raising `MAX_MCP_OUTPUT_TOKENS`. After a probe confirmed that all 116 rows are visible, the three sets of the BMB side were run again (`*-r2.jsonl`, the final sources kept with `--keep`). The largest result of the Verus side is 5,782 bytes, so this defect does not affect it.

| Set | Write | Navigation | Specification strength (BSB mutants killed) | Cost |
| --- | --- | --- | --- | --- |
| m1 | 10/10 | 5/5 | — | $1.17 |
| m1b | 25/25 | 12/12 | 186/186 | $6.97 |
| BVB (BMB) | 42/45 | — | — | $4.44 |
| BVB (Verus, `verus_pilot.py`) | 44/45 | — | — | $2.07 |

**The two arms of BVB (`bench/bvb/verus/harness.py compare`):**

| Metric | BMB | Verus |
| --- | --- | --- |
| first-attempt success | 42/45 | 44/45 |
| kinds of failure | all three "undecided by the solver" in the specification strength check | one, a failed specification strength check (the Verus judging does not separate undecided from refuted) |
| cost | $4.44 | $2.07 |
| model output tokens | 107,554 | 52,262 |
| tool calls | 407 | 111 |

- The two differ on four tasks: only BMB fails `vb-mbpp-454-contains-z`, `vb-misc-choose-odd` and `vc-va0093-max-balance`; only Verus fails `vc-va0590-boring-apartment`.
- Part of the difference in tool calls is the writing procedure. One write in BMB is `tx_begin`, `tx_unit`, `tx_put`, `tx_commit`, `verify` (at least five), in Verus `write_file`, `verify` (two).
- The "model input tokens" of the table are reported by the CLI without cache reads, so they are not used for the comparison. The cost (`total_cost_usd`) includes the cache.

### BRB: BMB + proof against Rust + tests (`claude-opus-5-5`)

The gist of the table from `bench/brb/harness.py summarize` (raw data `results/2026-10-28-brb-*-claude-opus-5-5.jsonl`).

| Metric | BMB | Rust (proptest on) |
| --- | --- | --- |
| success (all 9,651 hidden cases) | 24/24 | 24/24 |
| self-check passed & hidden failure | 0/24 | 0/24 |
| test code lines (passed tasks) | 0 | 834 |
| cost | $3.56 | $1.45 |
| total tokens (cache included) | 1,308,034 | 361,488 |
| output tokens | 105,571 | 35,916 |
| tool calls / checker calls | 252 / 41 | 88 / 29 |

- **H-ORACLE cannot be judged.** The Rust side has no "tests passed & hidden failure" either. For this model the BRB tasks are easy in both languages. Discrimination has to come from a small model (ADR-0034 decision 3) or from harder tasks.
- **G8:** 0 lines for BMB against 834 for Rust (a pilot, so not a claim). Both sides were right, so these 834 lines are the amount of "tests attached to correct code".
- **The cost side of G5 points to not met.** Total token ratio 3.6 (provisional criterion: within 2), cost ratio 2.45. Tool calls are 2.9 times, part of which is the writing procedure (a transaction is at least five calls) and proof iterations (checks 41 against 29). BVB pointed the same way (cost 2.1 times).
- **With a small model (`claude-haiku-5-5`, raw data `results/2026-10-28-brb-*-claude-haiku-5-5.jsonl`) BMB loses.** BMB 21/24 against Rust 24/24. Cost $0.45 against $0.07, total tokens 7,433,902 against 624,498 (11.9 times), output tokens 522,129 against 72,712, tool calls 435 against 155. Self-check passed & hidden failure is 0/21 against 0/22, so H-ORACLE cannot be judged this time either. On the Rust side the two tasks that ended with their own tests failing (22/24) passed the hidden judge too. Test code is 0 lines against 1,277.
- **The three tasks BMB missed are all non-linear integer arithmetic.** `t10-mod-floor`, `t16-gcd`, `t24-pow-mod`. All three sessions hit the limit of 40 calls and left no proved state. The sessions wrote the facts they needed as pure functions with only an `ensures` and the body `true`, to use them like lemmas, and spent calls on the transaction procedure (in t10, 9 `tx_begin` and 4 `tx_abort`).
- **Correction: the cause of the failures was the call budget, not the lack of lemmas.** At first these failures were read as due to the absence of user lemmas (ADR-0062). Run again with the same model on the `write` variant (the write surface section below), all three tasks succeeded: t10 ended in 17 calls, t16 in 5, t24 in 9. t10 and t16 proved specifications that fix the result completely. For t10 it is the range and the congruence, with the facts split into executable functions and used like lemmas. For t16 it is equality with the recursive specification `gcd_spec`. Only t24 fell back to the range specification `0 <= r < m`. This variant does not judge specification strength, so the success of t24 rests on the hidden tests. So BRB is no evidence for ADR-0062. What remains is only the observation that t24 alone "did not prove a functional specification".
- **The cause of the cost is the writing procedure (breakdown of the BVB calls).** BMB: 69 write attempts with the four `tx_begin`, `tx_unit`, `tx_put`, `tx_commit` each, 68 `verify` and 60 `query` (407 in all); Verus: 51 writes with one `write_file` and one `verify` each, and 9 `read_file` (111 in all). The numbers of write attempts are close, but the model turns are 452 against 156, and every turn takes the whole conversation in again, so the cost follows the number of turns. The layer it belongs to is the tool surface.

### Write surface: `write`, which writes and proves in one call (`claude-opus-5-5`)

`bench/m1b-write` has the seed, tasks and mutants of m1b and shows the model one `write` in place of the seven transaction tools (`bmb mcp --write-tool`).

| Variant | Success | BSB | Tool calls | Model turns | Output tokens | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| m1b (transaction tools, second run) | 37/37 | 186/186 | 257 | 294 | 57,622 | $6.97 |
| m1b-write(`write`) | 37/37 | 186/186 | 138 | 175 | 47,984 | $5.43 |

- The success rate and the specification strength are the same; tool calls −46%, model turns −40%, cost −22%. Over the write tasks alone: turns 250 → 127 (−49%), cost $5.78 → $4.20 (−27%).
- The breakdown that put the cost difference down to the writing procedure (the BRB section above) was right. The effect of fixing it in the layer it belongs to (the tools) was confirmed on the same tasks.
- The measurement condition differs (the tool surface), so this variant is not reported mixed with the original.

**The same variant of BVB and BRB (`bench/bvb-write`, `bench/brb-write`, the same generator).**

| Variant | Success | Tool calls | Model turns | Output tokens | Cache reads | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| BVB, BMB (transactions, second run) | 42/45 | 407 | 452 | 107,554 | 1,202,518 | $4.44 |
| BVB, BMB (`write`) | 44/45 | 98 | 143 | 84,488 | 677,231 | $3.38 |
| BVB, Verus | 44/45 | 111 | 156 | 52,262 | 224,531 | $2.07 |
| BRB large model, BMB (transactions) | 24/24 | 252 | — | 105,571 | — | $3.56 |
| BRB large model, BMB (`write`) | 24/24 | 51 | — | 72,709 | — | $2.47 |
| BRB large model, Rust | 24/24 | 88 | — | 35,916 | — | $1.45 |
| BRB small model, BMB (transactions) | 21/24 | 435 | — | 522,129 | — | $0.45 |
| BRB small model, BMB (`write`) | 24/24 | 132 | — | 477,686 | — | $0.64 |
| BRB small model, Rust | 24/24 | 155 | — | 72,712 | — | $0.07 |

- BVB: the success rate now equals Verus's (44/45), and the model turns are fewer than Verus's. The cost ratio went from 2.15 to 1.64. The remaining failure `vc-va0093-max-balance` passed the proof, and its specification strength is undecided (not refuted).
- The cost difference left in BVB is not the number of turns but the size per turn. Cache reads per turn are about 4,700 tokens for BMB and about 1,400 for Verus, and the output tokens are 1.6 times. Of the fixed part alone, the system prompt is 3,471 bytes against 1,131, and the tool definitions of `bmb mcp` (`tools/list`) are about 4 KB. The rest of the breakdown was left as later work.
- BRB large model: success stays 24/24, cost −31%, total tokens 1,308,034 → 562,600. The total token ratio to Rust went from 3.6 to 1.56, inside the token side of the provisional G5 criterion (within 2). The cost ratio is 1.70. Tool calls are 51, fewer than Rust's 88, and `verify` was called separately only once (`write` returns the proof result). On the defect-rate side both are 0, so G5 still cannot be judged.
- BRB small model: the three failures of the transaction variant all turned into successes (the correction above). The cost rose because of one task: `t13-rotate-right` used 161,868 output tokens and $0.39; without it the cost is $0.25. With a single run the variance cannot be told apart.

### H-NAME: m1b with its names removed or misleading (`claude-opus-5-5`)

The two twins of `bench/hname/gen.py` were run under the conditions of the second run. The compiler was built again in the middle of the run of the misleading variant, but what changed is a tool that only `--write-tool` turns on, so the tool list and behaviour of this run are the same.

| Variant | Success | BSB | Cost | Tool calls | Model turns | Output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| m1b (original names, second run) | 37/37 | 186/186 | $6.97 | 257 | 294 | 57,622 |
| m1b-alpha (opaque names, neutral summaries) | 37/37 | 186/186 | $7.69 | 293 | 330 | 64,125 |
| m1b-mislead (names shuffled within the same kind) | 37/37 | 186/186 | $7.86 | 301 | 339 | 69,265 |

- With names that lost their meaning or said something false, the success rate and the specification strength stayed the same. Only the cost grew by 10 to 13% (more read calls).
- This is the BMB half of H-NAME. The hypothesis is "the drop is smaller than that of the Rust + tests twin", so a verdict needs a Rust side with the same transformation. For this model the drop on the BMB side is 0, so any drop greater than 0 on the Rust side would point toward support.

### Failure analysis

**The specification strength failures were not due to weak specifications.** The judge was made to record the reason of a rejection (`spec_rejections` of `harness.py`: `refuted` when there is a counterexample, `undecided` when the solver does not decide; the verdict itself is unchanged). The four that can be analyzed (`vc-vv0039-max-of-list`, a failure of the first run that failed again when run again for diagnosis, and the three of the second run) are all `undecided`, and the agent's contract meant the same as the hidden contract.

| Task | Agent's contract | Why the judging did not decide |
| --- | --- | --- |
| `vc-vv0039-max-of-list` | membership of the element by a recursive predicate `contains_prefix` | recursive predicate → the implication to an existential quantifier needs induction |
| `vb-mbpp-454-contains-z` | `z_in_prefix` (recursive) | the same |
| `vb-misc-choose-odd` | a recursive predicate | the same |
| `vc-va0093-max-balance` | the same expression rewritten with division toward 0 | non-linear arithmetic of division and remainder by a constant. The two expressions were confirmed equal by comparing all of the domain -128..127 |

- `m1/w09-spread` and `bvb/vb-mbpp-62-smallest` of the first run succeeded when run again for diagnosis. The original sources were not kept, so the cause cannot be seen. Only that the result of the same task varies from run to run was confirmed.
- **Correction:** after the first run this document and the project's planning notes recorded the three failures as "the specification was weak" and read them as grounds for the direction of ADR-0040, "the next bottleneck is the validity of specifications". The analysis showed that reading was wrong. The cause is the incompleteness of the judge and the prover. The root fixes of the two classes are inductive lemmas (the proposal of ADR-0062) and the encoding of division and remainder by a constant.
- **The navigation failure (`m1b/n12-io`) was a defect of the pilot** (above). After the fix it succeeded.

### First run (commit `327a391d`): kept only as a record

| Set | Write | Navigation | Specification strength (BSB mutants killed) | Cost |
| --- | --- | --- | --- | --- |
| m1 | 9/10 | 5/5 | — | $1.22 |
| m1b | 25/25 | 11/12 | 186/186 | $5.21 |
| BVB | 43/45 | — | — | $4.68 |

Results under the defect of not seeing large tool results. Verdicts and the register use the second run.
