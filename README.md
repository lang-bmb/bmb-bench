# bmb-bench

The measurement apparatus of the [BMB language](https://github.com/lang-bmb/lang-bmb): benchmark harnesses,
frozen task sets, raw result rows and the measurement reports that judge them.

BMB's claims are written only where a measurement backs them, including the claims a measurement refuted.
This repository is where those measurements can be read, checked and run again.

## Layout

| Path | What it holds |
| --- | --- |
| `bench/<set>/` | one directory per benchmark or task set: runner, judge, reference and weak solutions, tasks and prompts. [`bench/README.md`](bench/README.md) lists them (in Korean) |
| `bench/<set>/MANIFEST` | the frozen files of a set with their SHA-256. A frozen file is never edited; a changed set is a new set |
| `bench/<set>/results/` | result rows, one JSON object per session (`*.jsonl`), as the harness wrote them, and for some runs the session records (`*.sessions/<task>.json.gz`: every tool call and model request) |
| `bench/conditions/` | reports that two commits' harnesses are the same instrument (`bench/condition.py`) |
| `bench/SOURCE` | where `bench/` came from, and which files changed here since |
| `reports/` | the measurement reports: conditions, tables, verdict, limits. Being translated; see [`reports/README.md`](reports/README.md) |
| `scripts/` | the check of this repository and the import from `lang-bmb` |

`bench/` was moved here from `lang-bmb` at commit `6bbf72cb` (its ADR-0147) and keeps the directory name and
the layout it had there: the harnesses refer to each other by those paths, and 70 of them are frozen. Much of
the text in it is Korean: the task statements and prompts of some frozen sets (changing them would change the
set), and harness comments and per-set READMEs that have not been translated yet.

## Reading the data

- A frozen set is data, not documentation.
- A result row is what the harness wrote at the time. One change was made before publication: the host name
  of the model gateway the measurements ran through reads `<gateway>` (as in `https://<gateway>/openai/v1`),
  in the result rows and inside the session records. It appeared in the error messages of failed requests.
  Nothing else in a row was edited, and no frozen file held the name. `scripts/import_bench.py` is the whole
  transformation, and `scripts/import_bench.py --check` proves that `bench/` is `lang-bmb`'s tree with it
  applied.
- Results are first attempts, without retries, on frozen tasks and prompts.
- **The `commit` field of a row.** Rows written before the move name a commit of `lang-bmb`, which then held
  the compiler, the harness and the sets together. From this repository on, `commit` is a commit of
  `bmb-bench` (the harness and the sets), and the compiler's commit is the new field `lang_bmb_commit`, taken
  from the checkout `LANG_BMB` names. The frozen harnesses could not be edited to say so: the `brb` family
  gets `lang_bmb_commit` in its header and summary rows through the shared `condition_fields`, but
  `bench/review/harness.py` and `bench/bcb/bcb.py` write only `commit`, and tables that the frozen harnesses
  print still label that field "컴파일러 커밋" (compiler commit). For their rows the compiler's commit has
  to be recorded with the run.

## Running it

The harnesses need Python 3 (standard library only), the BMB compiler and its Z3, and for the Rust arms a
Rust toolchain. The compiler comes from a checkout of `lang-bmb`:

```sh
scripts/check.sh quick                 # manifests, and the jobs that need no compiler (seconds)
scripts/check.sh /path/to/lang-bmb     # everything; or LANG_BMB=/path/to/lang-bmb scripts/check.sh
```

`scripts/check.sh` is the one check, judged by its exit code:

1. every `MANIFEST` matches its files (`scripts/manifests.py check`);
2. `bench/` equals the transformed import of the commit `bench/SOURCE` names (`scripts/import_bench.py --check`);
3. the full check builds the compiler in the `lang-bmb` checkout (untracked `target/` there; nothing tracked
   is touched), prepares the proof cache of the compiler's BMB port that `bench/twin` starts from, and runs
   the bench jobs of `lang-bmb`'s own gate, word for word: the reference solution of every task must pass
   and the weak one must fail, with no model. This takes about a quarter of an hour on four cores;
4. the run must not leave or change a file in the tree.

Environment variables the harnesses read:

| Variable | Meaning |
| --- | --- |
| `BMB` | the compiler binary. `scripts/check.sh` sets it to `$LANG_BMB/target/debug/bmb` |
| `LANG_BMB` | the `lang-bmb` checkout, for what a harness needs besides the binary: product sources, git history, a build, the caches under its `target/` (`bench/lang_bmb.py`). A harness that needs it and does not find it says so |
| `BMB_GATEWAY` | for runs with a real model: the URL of a gateway serving the OpenAI-compatible API under `/openai/v1` and the Anthropic API under `/anthropic/v1`. `BMB_OPENAI_BASE_URL` and `BMB_ANTHROPIC_BASE_URL` give either base URL whole instead. No host is written in this repository, and no keys |

A real measurement is `bench/run_models.py` ([`bench/README.md`](bench/README.md)). It refuses to start on an
uncommitted tree, here or in the `lang-bmb` checkout, and each harness refuses a set that differs from its
`MANIFEST`.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option. Task sets derived from other projects keep the licenses of their sources; see
[THIRD-PARTY.md](THIRD-PARTY.md).
