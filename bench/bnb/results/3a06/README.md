# 3a06: BNB model runs (H-SCALE, G4, ADR-0105 decision 4)

The model runs of BNB (`3a06` is the label of this measurement), an item of ADR-0103. The verdict rules are registered by this file before the first model session (2026-11-10).

## Conditions

- **Tasks and prompts:** the 27 frozen tasks and `prompt-{bmb,rust}.md` (`../../MANIFEST`). The tool call limit is 40, and `answer` counts as one call too.
- **Tools:**
  - The BMB arm sees and can call only `query` and `map` of `bmb mcp`. The `verify`, `build` and transaction tools the server also offers are not in the frozen prompt, and the Rust arm has no write or build tools either.
  - The Rust arm uses `list_dir`, `read_file` and `grep`.
- **Unit of a run:** one result file is one (model, arm, size).
  - It runs as `bnb.py run --agent M --arms A --sizes N --jobs 2 --sessions S --out F`.
  - A result row is written as each session ends, and when cut the run resumes from that file.
  - The compiler is fixed as a copy of `target/release/bmb` of the same commit. The harness refuses an uncommitted tree.
- **Sizes and models:** at sizes 10,000 and 1,000, qwen (`openai:qwen3.8-27b`) and sonnet (`anthropic:claude-sonnet-5-5`) run once each. 3,000 runs under the same rules if time is left.
- **Concurrent runs:** on the measurement machine it may overlap with the qwen repeats of `brb-hard`, because the CPU of the BMB queries (below) is small. This run is bound to one core with `taskset -c 3`, and overlapping sessions are noted in the record of the results.

## Metrics

| Metric | Definition |
| --- | --- |
| success | the answer set equals the correct answer (precision = recall = 1) |
| tokens read | all bytes of tool responses of a session counted as ceil(bytes/4) (ADR-0021). This is the "tokens" of G4 and H-COMPREHEND |
| model tokens | input + output. Reported as auxiliary |
| local tasks | the 24 of the units `m1` and `m2` (n01~n24). Their answers are the same at every size N ≥ 340. The answers of the 3 whole-program tasks (n25~n27) are proportional to N |

## Verdict

The verdict is made on the comparison at size 10,000. The reference model of the claim is sonnet (ADR-0103 decision 3), and qwen is reported side by side in the same table.

1. **G4 (ADR-0034):** at size 10,000, over all 27 tasks.
   - There are two conditions to pass. The token ratio (sum of tokens read by BMB / sum of tokens read by Rust) is 1/3 or less, and the BMB success rate is at least the Rust success rate.
   - When the BMB success rate is below Rust's, it is looked at again with the interval of ADR-0077 §3. If the intervals overlap it is written as "equal accuracy not confirmed".
2. **The condition of ADR-0105 decision 4 (sonnet, 10,000):** applied as the registered sentence. If one of the following holds, the fix of the query surface comes before the comprehension tasks of the port twin and is finished before the P5 porting.
   - The BMB success rate is lower than Rust's by more than D (0.30).
   - The token ratio is over 1/3.
3. **H-SCALE (BMB arm):** judged on the 24 local tasks.
   - **Supported:** from 1,000 to 10,000 the drop of the success rate is inside D and the sum of tokens read grows by a factor of 1.5 or less.
   - **Refuted:** the success rate drops by more than D, or the token sum grows by a factor of 3 or more.
   - **Cannot be judged:** in between.
   - The same factors of the Rust arm are reported with it for comparison.
4. **Repeats (ADR-0103 decision 2):** if in the comparison at 10,000 of the first qwen run the success rates of the two arms differ by less than D, the two arms at 10,000 are repeated up to 3 times at the same commit and condition.
   - Whether to repeat is decided by that one number only. 1,000 is not repeated.
5. **No adjustment after the fact:** the tasks, prompts and tools are not changed and run again after seeing the results. If something to fix shows up, it is written down as an item for the next edition.

## Facts known before the run (oracles, the compiler of the measurement commit)

The scripted oracles (the cheapest correct strategy of each arm) are a lower bound of each arm's cost.

| Size 10,000 | BMB | Rust | Ratio |
| --- | --- | --- | --- |
| 24 local tasks | 24,001 | 75,139 | 0.319 |
| all 27 | 93,574 | 120,288 | 0.778 |

- In the edition of 2026-10-25 (`../2026-10-25.md`) the BMB total was 57,218. Since then the `duplicates` response has grown 2.5 times (n26 and n27 each 12,059 → 30,110).
- So at this commit the oracle too is over the 1/3 of G4 on all 27 tasks. The cause is that `duplicates` gives the groups of the whole program whatever the question.
- It is not fixed before the run. If the condition of verdict 2 holds, that fix is the first target of the query surface fix.
- CPU of the BMB queries: the 60 tool calls of the oracle's BMB arm at 10,000 over the 27 tasks take 24 seconds of wall-clock time (about 0.4 seconds per call).
- Computing the answers and building the map cache of the same run take about 110 seconds, once at the start of the run.
