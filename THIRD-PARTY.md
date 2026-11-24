# Third-party sources

Some task sets are derived from other projects. Each keeps the license of its source, and the license text
travels with the set.

| Set | Source | License | Where the license text is |
| --- | --- | --- | --- |
| `bench/brb-hard` | QuixBugs (D. Lin, J. Koppel, A. Chen, A. Solar-Lezama, "QuixBugs: A Multi-Lingual Program Repair Benchmark Set Based on the Quixey Challenge", SPLASH Companion 2017; <https://github.com/jkoppel/QuixBugs>). The twelve tasks restate its problem descriptions and reimplement its documented defects; its code is not copied (`bench/brb-hard/README.md`) | MIT | `bench/brb-hard/QUIXBUGS-LICENSE` |
| `bench/bvb` and the sets generated from it (`bvb-write`, `bvb-diff`, `bvb-ast`, `bvb-write-lean`, `bvb-write-probe`, `bvb-write-stateless`, `bvb-write-undecided`, and the items of `review` and `intent`) | public Verus tasks (Verus-Bench, Vericoding), pinned commits and selection record in `bench/bvb/sources.py` and `bench/bvb/SOURCES.md` | as recorded per source | `bench/bvb/licenses/` |

## Written for this project

These parts refer to work outside the project but copy nothing from it.

| Part | What it is |
| --- | --- |
| `bench/game` | BMB programs for four tasks of the Computer Language Benchmarks Game (<https://benchmarksgame-team.pages.debian.net/benchmarksgame/>) and single-threaded Rust references in `ref/`. The programs and the references were written for this project from the public descriptions of the algorithms; no submission of the Benchmarks Game is copied. The expected outputs (`*.out`) are what these programs print for the stated arguments |
| `bench/lib/sha2_crate` | a small program of this project that depends on the `sha2` crate (`=0.11.1`) from crates.io. Cargo fetches the crate when the program is built; no source of the crate or of its dependencies is in this repository. The `Cargo.lock` only names them |
| `bench/twin/fixtures/stk` | a small stack-machine program in BMB and in Rust with a corpus of inputs and outputs, written for this project |
