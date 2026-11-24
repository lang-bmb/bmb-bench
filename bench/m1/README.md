# M1 measurement (ADR-0021)

Measures whether an agent solves BMB tasks with MCP tools only, without files.

| File | Contents |
| --- | --- |
| `prompt.md` | the agent's system prompt (frozen) |
| `seed/` | the starting workspace (frozen). 23 definitions |
| `tasks/` | 15 tasks (frozen): 10 write, 5 navigation. A write task has a hidden reference contract and a reference solution |
| `MANIFEST` | SHA-256 of the frozen files. On a difference the harness refuses to run |
| `harness.py` | runs the sessions, judges them, computes the metrics |
| `anthropic_agent.py` | adapter for a real model (paid, needs a person's approval) |

```
python3 bench/m1/harness.py manifest                  # check the freeze
python3 bench/m1/harness.py run --agent oracle        # reference solutions: all must succeed (CI)
python3 bench/m1/harness.py run --agent weak          # weak specifications: all must fail (CI)
python3 bench/m1/harness.py run --agent anthropic:claude-opus-5-5 --out results/DATE-MODEL.jsonl
python3 bench/m1/harness.py summarize results/*.jsonl  # the metric table of ADR-0021 §4 (one column per file)
```

The harness takes the task set directory as `--set DIR` (default: this directory). The second set `m1b` and the procedure for comparing models are in `bench/m1b/README.md` (ADR-0025). `--jobs N` runs N sessions in parallel (for CI, default 1).

Success of a write task = the whole workspace proved + the required signature + the **specification strength check** (the hidden `ref_pre ⇒ agent requires` and `agent ensures ⇒ ref_post`, proved as definitions made for judging). The answer of a navigation task is computed from the map. A task with a given contract (`given`, `bench/impossible`) starts from a workspace where the task's `setup` is committed onto the seed, the harness adds the `report` tool, and the verdict comes from passing the gate, `bmb weaken` (start against end) and the report. Every `bmb` call of the judge goes through the proof cache of the session workspace (`.bmb-cache/`, the one `bmb mcp` uses). The cache does not change the output bytes and stores only proved obligations by the hash of the solver input, so the verdict is the same. A session starts from a copy of a cache warmed once per process with the seed.

## Runs with a real model (the user's machine)

A measurement with a real model uses a paid API, so it runs on the user's machine. The project's cloud sessions do only the code and the checks that can run there.

```
# 1. Tools, in the lang-bmb checkout: Rust (pinned by rust-toolchain.toml), Z3 4.15.4, LLVM 18
./scripts/setup.sh                       # checks/installs z3 (pip) and LLVM. On macOS install z3 and llvm@18 yourself
cargo build                              # target/debug/bmb
cargo run -q -- doctor                   # checks the z3 and llvm versions (both must be "ok")

# 2. Check the harness with the reference solutions (free)
python3 bench/m1/harness.py run --agent oracle --expect all-pass

# 3. A real model (paid)
pip install anthropic
export ANTHROPIC_API_KEY=...             # or `ant auth login`
python3 bench/m1/harness.py run --agent anthropic:claude-opus-5-5 \
    --out bench/m1/results/$(date +%F)-claude-opus-5-5.jsonl
```

- One session per task. A failed one is not run again (ADR-0021 §3).
- `--tasks w01-clamp` runs one task first, to check the cost and the behaviour. Results of such a run are not mixed into a report.
- Once the result files are committed, the summary is written from them.
