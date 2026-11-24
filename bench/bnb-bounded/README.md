# BNB response-window variants (ADR-0127)

Two variants that run the `bmb` arm of BNB (`bench/bnb`) with `bmb mcp --bounded` (a budget of 32,768 bytes) and `--bounded-16k` (16,384 bytes). The tasks, workspace, judging and call limit (40) are the original's, and what differs is the flag of `bmb mcp` and two places of the prompt. There is no Rust arm (the comparison is with the `bmb` arm of the original at the same commit).

This directory and `bench/bnb-bounded-16k` go as far as the freeze and the gate. The model run is a separate measurement (on the measurement machine).

| File | Contents |
| --- | --- |
| `set.json` | `mcp_flags` (frozen), the budget |
| `prompt-bmb.md` | the system prompt (frozen). The one line "start with `units`" of the original is changed to "start with `overview`" and a paragraph "Large results" is added (the gate checks that the other lines are the same) |
| `MANIFEST` | SHA-256 of the two above and of `../bnb/MANIFEST`. On a difference the run is refused |

```
python3 bench/bnb/bnb.py --set bench/bnb-bounded manifest                 # check the freeze
python3 bench/bnb/bnb.py --set bench/bnb-bounded run --sizes 10000 --arms bmb --out R.jsonl --expect all-pass   # scripted
python3 bench/bnb/bnb.py --set bench/bnb-bounded run --agent openai:MODEL --arms bmb --sizes 10000 --jobs 2 --sessions S --out R.jsonl
python3 bench/bnb/bnb.py --set bench/bnb-bounded-16k run ..               # budget 16,384
python3 bench/bnb/bnb.py run --agent openai:MODEL --arms bmb --sizes 10000 ..   # the original (same commit)
```

The result rows have `truncated` (the number of truncated responses) and `continued` (the number of calls continued with `offset`). What the model run looks at is the accuracy, the tokens, and whether a session that got a truncated response continued it or narrowed the query.

## Values measured before the run (2026-11-13, scripted oracle, no model)

The scripted oracle makes the same queries as on the original and continues a truncated result to the end with `next` (`bnb.call`). So these values are a lower bound of "does the window lose the answer" and of "the cost of continuing". The script does not follow the prompt's "start with `overview`" (as the cheapest correct strategy it makes narrow queries from the start).

| N | Variant | Succeeded | Response tokens | Calls | Max calls of one task | Truncated responses | Continued calls |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1,000 | original | 27/27 | 13,744 | 60 | 4 | 0 | 0 |
| 1,000 | 32K | 27/27 | 13,744 | 60 | 4 | 0 | 0 |
| 1,000 | 16K | 27/27 | 13,744 | 60 | 4 | 0 | 0 |
| 10,000 | original | 27/27 | 93,574 | 60 | 4 | 0 | 0 |
| 10,000 | 32K | 27/27 | 94,101 | 69 | 5 | 14 | 9 |
| 10,000 | 16K | 27/27 | 94,739 | 82 | 10 | 27 | 22 |

- **The window does not lose the answer.** Both budgets give 27/27 and no task reaches the call limit.
- **At N=1,000 no query of the script exceeds 16K.** The bytes of the three variants are the same.
- **At N=10,000 five tasks are truncated**: `effects` (n12, n24, n25) and `duplicates` (n26, n27), which ask about the whole workspace. Continued to the end, the tokens grow by 0.6% (32K) and 1.2% (16K), and the calls per task grow from 2 up to 5 (32K) and 10 (16K). The window does not cut the script's tokens: the script reads everything it needs. What can shrink is the case where a model narrows after seeing only the first window, and that is what the model run measures.
- **Size of the first call (N=10,000).** `units`, which the original prompt recommends, is 1,192,293 bytes (about 298 thousand tokens) and comes in one piece. In the window variants the first window is as large as the budget, and reading all of it takes 37 calls (32K) or 74 (16K), so at 16K it cannot all be read within the call limit (40). `overview`, which the window variants' prompt recommends, is 67,313 bytes and comes in 3 calls (32K) or 5 (16K). At N=1,000 `overview` is 6,663 bytes and fits one window (`units` is 117,205 bytes: 4 and 8 calls).
- A continuation carries a `truncated` row and is a little larger than the whole (`overview` 67,313 → 67,773 bytes, 32K).

## To be known beforehand

- The prompt differs in two places, so a difference from the original is the joint effect of "the window" and "the advice to start with `overview`". The two are not separated (the question of the model run is whether to make this configuration the default).
- The flag `--bounded-16k` of the 16K variant is for the measurement. After the verdict only one of the two stays, or both are removed (ADR-0120, ADR-0127).
- The script's calls are at most 10 for one task, well within the limit of 40, but a model that tries to continue `units` to the end reaches the limit. That session is recorded as `limit_hit`.
