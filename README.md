# bmb-bench

The measurement apparatus of the [BMB language](https://github.com/lang-bmb/lang-bmb): benchmark harnesses,
frozen task sets, raw result rows and the measurement reports that judge them.

BMB's claims are written only where a measurement backs them, including the claims a measurement refuted.
This repository is where those measurements can be read, checked and run again.

## Status

The contents are being moved here from `lang-bmb` (its ADR-0147). Until the move, the harnesses and results
are in `lang-bmb` under `bench/` at the commits the reports name.

| Part | What it will hold | State |
| --- | --- | --- |
| harnesses | one directory per benchmark: runner, judge, reference and weak solutions | to be moved |
| frozen sets | tasks and prompts, with a `MANIFEST` of hashes; a frozen set is never edited | to be moved |
| results | one JSON row per session, as the harness wrote it | to be moved |
| reports | per measurement: conditions, tables, verdict, limits | to be moved |

## Reading the data

- A frozen set is data, not documentation. Some sets hold Korean text (task statements written before the
  project's documents moved to English); changing it would change the set.
- A result row is what the harness wrote at the time. Before publication one change is made to the rows: the
  host name of the model gateway inside error messages is replaced by `<gateway>`. Nothing else is edited.
- Every report names the commit of `lang-bmb` it measured. Results are first attempts, without retries, on
  frozen tasks and prompts.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option. Task sets derived from other projects keep the licenses of their sources; see
[THIRD-PARTY.md](THIRD-PARTY.md).
