# Third-party sources

Some task sets are derived from other projects. Each keeps the license of its source, and the license text
travels with the set.

| Set | Source | License | Where the license text is |
| --- | --- | --- | --- |
| `bench/brb-hard` | QuixBugs (D. Lin, J. Koppel, A. Chen, A. Solar-Lezama, "QuixBugs: A Multi-Lingual Program Repair Benchmark Set Based on the Quixey Challenge", SPLASH Companion 2017; <https://github.com/jkoppel/QuixBugs>). The twelve tasks restate its problem descriptions and reimplement its documented defects; its code is not copied (`bench/brb-hard/README.md`) | MIT | `bench/brb-hard/QUIXBUGS-LICENSE` |
| `bench/bvb` and the sets generated from it (`bvb-write`, `bvb-diff`, `bvb-ast`, `bvb-write-lean`, `bvb-write-probe`, `bvb-write-stateless`, `bvb-write-undecided`, and the items of `review` and `intent`) | public Verus tasks (Verus-Bench, Vericoding), pinned commits and selection record in `bench/bvb/sources.py` and `bench/bvb/SOURCES.md` | as recorded per source | `bench/bvb/licenses/` |

## Not yet settled

These parts refer to work outside the project, and their record here is incomplete. They are listed so that
nobody takes the table above for the whole answer.

| Part | What is known | What is open |
| --- | --- | --- |
| `bench/game` | BMB programs for four tasks of the Computer Language Benchmarks Game, and single-threaded Rust references in `ref/`. Its README says the programs and the references were written for this project from the public algorithms, not taken from the official submissions | whether the task definitions and the expected outputs (`*.out`) need an attribution or a license notice of the Benchmarks Game |
| `bench/lib/sha2_crate` | a small program of this project that depends on the `sha2` crate (`=0.11.1`) from crates.io, with a `Cargo.lock`. No source of the crate or of its dependencies is in this repository | nothing to license here as far as we see; listed because the lock file names third-party crates |
| `bench/twin/fixtures/stk` | a small stack-machine program in BMB and in Rust with a corpus of inputs and outputs. Nothing in it names an outside source | confirmation that it was written for this project |
