# Benchmarks Game programs

Tasks of the [Computer Language Benchmarks Game](https://benchmarksgame-team.pages.debian.net/benchmarksgame/) written in BMB. Each program is fully proved together with the standard library units it uses (`std::bytes`, `lib/std/`, added by the compiler) (gate test `game_programs_are_proved`). Running takes tens of seconds, so the gate does not run them.

| Program | Argument | Output | What is proved | Notes |
| --- | --- | --- | --- | --- |
| `binarytrees.bmb` | n = 21 | `binarytrees.out` | no panic and no overflow, termination of the recursion | the sum of the node counts `check` is a `wrapping_add`. Writing "the number of nodes of a complete tree of depth d = 2^(d+1) - 1" as a contract needs an inductive lemma (the proposal of ADR-0062). The `+` of the Rust submission gives the same value in a release build too |
| `nbody.bmb` | n = 1000 (the small argument) | `nbody.out` | no panic, every index in range (5 bodies) | `f64` (ADR-0061). The output is the bench's expected output -0.169075164 / -0.169087605 and equals that of `ref/nbody.rs` (a Rust reference written from the public algorithm) |
| `spectralnorm.bmb` | n = 100 (the small argument) | `spectralnorm.out` | no panic and no overflow, index ranges, exactness of `f64::from` (`i, j <= 10000`) | output 1.274219991. Equals `ref/spectralnorm.rs` (`game_programs_match_their_rust_references`) |
| `fannkuchredux.bmb` | n = 12 | `fannkuchredux.out` | no panic and no overflow, every index in range (permutation elements < 12, the invariant of the counters 1..=i+1) | termination of the flipping loop (topswops) is a theorem that one decreasing measure does not prove, so it is bounded by a fuel of 1000 (the upper bound for n = 12 is Knuth's F(13) = 233). The checksum uses `wrapping_add` and `wrapping_sub` |

```
target/debug/bmb build bench/game/binarytrees.bmb -o bt && ./bt | diff - bench/game/binarytrees.out
target/debug/bmb build bench/game/fannkuchredux.bmb -o fk && ./fk | diff - bench/game/fannkuchredux.out
```

## State

- n-body and spectral-norm run briefly, so the gate builds and runs them and compares the output with `.out` and the Rust reference. The time and size rows for the bench sizes (50 million, 5500) are measured on a quiet machine (the machine that made this commit was shared, so they are left empty). `ref/*.rs` are not the official submissions but single-threaded Rust written after the public algorithms.

- The two outputs are the values each algorithm fixes, and they equal the known results of these tasks (fannkuch-redux 12: `3968050`, `Pfannkuchen(12) = 65`). The byte comparison with the official expected output files and the time and size comparison with the official Rust submissions have not been done yet. The official sources (salsa.debian.org, benchmarksgame-team.pages.debian.net) were blocked by the network policy of the environment this was written in.
- Single-threaded. Most official Rust submissions use several threads. BMB has no threads yet, so the comparison is with single-threaded submissions or with runs bound to one core by `taskset`.
