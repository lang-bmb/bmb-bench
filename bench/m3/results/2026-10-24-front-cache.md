# m3 query time: the MCP front-end cache and proving one definition (2026-10-24)

The measurement of two changes: the MCP server keeps the front-end result between calls (below, "front-end cache"), and `surface DEF` proves only DEF (below, "single-definition proof"). The baseline is the earlier measurement of the same day, `2026-10-24.md` (findings 1 and 2). That file is left as it is.
Raw data: `2026-10-24-front-cache.jsonl`. In every row `build` is `before` (the compiler of commit `5d3ab9c`) or `after` (commit `6e85bfa`). The two builds were measured one after the other on the same workspace with the same harness (`scale.py` of this commit).

## Environment

| Item | Value |
| --- | --- |
| CPU | Intel Xeon @ 2.10GHz, vCPU 4 |
| OS | Linux 6.18.44 (firecracker VM), Python 3.13.17 |
| Z3 | 4.15.4, `rlimit` 5000000 |
| Build | `cargo build --release` |
| Load | load average about 1 to 2 (quieter than the about 10 of the earlier measurement). CPU time is the `/proc` value of the server process, so it has a 10 ms grain: `0` means under 10 ms |

## Reproduction

```
cargo build --release
python3 bench/m3/scale.py verify  --work W                  # generate + prove (workspace and .bmb-cache)
bmb verify --cache W/nNNNNN/.bmb-cache W/nNNNNN              # after changing the build, warm the incremental cache with that build (the key holds the compiler's identity)
BMB=path/to/bmb python3 bench/m3/scale.py queries --work W --runs 5 --out R.jsonl
python3 bench/m3/scale.py table R.jsonl
```

`scale.py` grew by two things this time. `$BMB` picks the binary, and after the queries it measures writes (`tx_commit`, `slice after commit`, `surface after commit`): it commits the branch constant of the first `shift` leaf of m1 by tx_put, alternately +1 and back (the contract stays), and each time calls `slice` and `surface` of the chain_top probe once. That is the cost of the first read right after a commit. It commits an even number of times and so ends with the original source.

## Results

### Response bytes

At every size, probe and query the response bytes of before and after are the same (284 rows compared, 0 differences). Apart from that, on the N=1,000 workspace the output and exit code of 431 requests were the same for the two builds: CLI `map L0/L1/L2/all`, `units`, `status`, `duplicates`, `effects`, `contracts`, `find`, and for 28 definitions `surface`, `slice`, `impact` (iface, body), `effects`, `find`, `edges` (out/in/both × depth 1 to 3) (a helper script of the measurement, not committed). In the gate `tests/mcp_cache.rs` checks the same (below).

### Per-definition queries (N=10,000, server CPU ms, median of 5)

| Probe | `find` | `slice` | `edges` | `edges both` | `impact` | `effects` | `surface` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| chain_top | 500 → 10 | 500 → 10 | 510 → 0 | 440 → 0 | 490 → 0 | 480 → 0 | 1,150 → 140 |
| leaf | 470 → 10 | 450 → 0 | 510 → 0 | 470 → 0 | 440 → 0 | 430 → 0 | 1,270 → 140 |
| remap | 420 → 0 | 470 → 0 | 540 → 0 | 450 → 0 | 500 → 0 | 540 → 10 | 1,170 → 80 |
| reset | 590 → 10 | 540 → 0 | 420 → 0 | 430 → 0 | 460 → 0 | 450 → 0 | 1,210 → 120 |
| show | 490 → 0 | 460 → 0 | 660 → 0 | 680 → 0 | 580 → 0 | 480 → 0 | 1,430 → 90 |
| spec_inb | 540 → 0 | - | 470 → 0 | 520 → 0 | 620 → 0 | - | 1,240 → 90 |

Wall clock (after, N=10,000): per-definition queries other than `surface` take 3 to 7 ms, `surface` 88 to 138 ms.

### Summary per size (CPU ms, min/median/max or median)

| Query | N=100 before → after | N=1,000 | N=10,000 |
| --- | --- | --- | --- |
| per definition (`find`, `slice`, `edges`, `impact`, `effects`; 34) | 0/0/0 → 0/0/0 | 30/30/50 → 0/0/0 | 420/485/680 → 0/0/10 |
| `surface` (6) | 10 → 0 | 90 → 10 | 1,150/1,225/1,430 → 80/105/140 |
| `map L0` (whole, 1.19 MB) | 0 → 0 | 30 → 0 | 510 → 40 |
| `find inb` (matches proportional to N) | 0 → 0 | 30 → 0 | 520 → 10 |
| `tx_commit` (1 write) | 5 → 0 | 60 → 95 | 905 → 1,030 |
| first `slice` right after a commit | 0 → 0 | 30 → 25 | 485 → 230 |
| first `surface` right after a commit | 10 → 0 | 95 → 10 | 1,295 → 115 |
| `cli check` (CLI, front end only, baseline) | 4 → 6 | 27 → 29 | 333 → 333 |

## Design (what reuses what)

- **Front-end cache, `FrontCache` (`compiler/src/lib.rs`).** The server reads `src/*.bmb` again at every call (about 5 ms at 10,000; other writers and direct edits are seen). For every file it keeps (name, position, source, syntax tree, lexer and parser diagnostics), and a file whose name, position and source are the same is not parsed again. Spans hold file positions, so a file whose position changed is parsed again. If even one changed, the checker runs on the whole program again: its tables (`fns`, `types`, `recursive`) are global, so splitting by unit would need a change of the checker (remaining cost below). If nothing changed, neither the check nor the index is redone.
- **Map index (`map::Index`).** `Model` was split into an `Index` without references to the program (units, definition entries, edges, the `io` set, a table of reverse edges) and a thin view made per query (`Model::view`: one pass over the definition list + the table of proof states). Definition hashes (ADR-0019 §2) are computed on first use (`OnceCell`). A per-definition query finds outgoing edges by a range lookup in the sorted edge set and incoming edges in the reverse edge table, and does not scan all edges (`slice`, `edges`, `impact`, `effects`, `uses` of L1 rows). This part applies to the CLI too.
- **Single-definition proof, `surface DEF`.** The state of a definition is fixed by its own obligations alone: a query is made from its own source and the contract and `#[uses]` texts of other definitions, and every obligation is solved in a solver after `(reset)`. So only DEF is proved (`verify::verify_only`). Unlike `verify_defs` it does not stop at the first failure, so the `failed` count of a failing definition is the same too. The incremental key computes only the hashes and texts of the definitions DEF reaches (`incremental::Session::new_for`, lazily in the same key function), and the SHA-256 of the lines of the incremental cache file is checked only for the lines read (when saving all are checked, so a damaged line is dropped as now).
- **Checking identity.** `tests/mcp_cache.rs` (gate): (1) the same requests are sent to one long-lived server and to a new server per call, and the whole response JSON is compared. The session mixes an empty workspace, a commit, a commit changing a body (checking 1 file parsed again and 1 check together), a commit by another server (a unit that sorts in front, so the position of every file changes), a direct edit that puts in a syntax error and its repair, and the removal of a unit, and every time compares all `map` levels, all queries (7 definitions × 9 kinds), `verify` and `build` (refused). (2) For every definition it checks that the `surface` row equals the `map L1` row of the whole proof, with no cache, a cold and a warm cache, and that a cold cache gets only the entries of that definition. A definition with 2 failing obligations is included.

## Interpretation

**The time of a per-definition query no longer depends on the whole size (principle 7).** While nothing changes, at 10,000 definitions `find`, `slice`, `edges`, `impact` and `effects` take under 10 ms of server CPU (3 to 7 ms wall clock), indistinguishable from 1,000 and 100 (before: 420 to 680 ms, linear in N). The remaining fixed cost is reading the files and comparing the sources at every call (about 5 to 10 ms at 10,000), proportional to the size but two orders of magnitude smaller than before. Removing it would mean detecting file changes by mtime or the like, which weakens the guarantee of byte identity, so it was not done.

**`surface` fell a little more than 10 times but still has a part proportional to N.** At 10,000, from 1.15~1.43 seconds to 80~140 ms. The key computation and the proof of the requested definition are small, and what remains is preparation cost proportional to the size of the workspace (profiled with a helper program, not committed): reading the proof cache file (`proofs`, 39,740 lines) about 10 ms, preparing the incremental session (definition list, table of `spec fn` declarations 7 ms, splitting the cache file into lines) about 20 to 30 ms, preparing `verify_only` (definition list, `spec fn` declarations and symbol table) about 20 ms. Keeping these three in the server's memory (deciding by length and mtime whether to read the cache file again) could reduce it further (a candidate).

**The first read right after a commit pays for the whole check.** At 10,000 the first `slice` after a commit takes 230 ms (before: 485 ms): only the one changed file is parsed, but the whole checker (about 130 ms) and the rebuilding of the index (about 65 ms) run again. From the second read on it is under 10 ms again. That the first `surface` after a commit, 115 ms, is cheaper than `slice` is due to the order (the `slice` before it already paid for the recheck and the reindexing). Rechecking per unit would need the checker's global tables split per unit (a candidate).

**`tx_commit` did not change (about 0.9 to 1.0 seconds, linear in N).** The commit is outside the scope of this work, and `workspace::commit` reads the workspace again and parses and checks the whole twice (for the hashes before the change, and for the check after applying it). The difference 905 → 1,030 ms is taken as within the variation of repeated measurements (the code path is the same). Handing the server's cached program and hashes to `plan` could remove the parse and check before the change (a candidate).

**Whole-workspace queries.** `map L0` (a 1.19 MB response) went from 510 to 40 ms and is now mostly serialization. `status` and `map L1` run the whole incremental session, so they are still proportional to N (not among the probes of this measurement).

## Verdict

- Front-end cache: the goal (per-definition queries at 10,000 far below 400 to 500 ms) is met. Under 10 ms of CPU at 10,000, with the same response bytes. The first read after a commit pays for the whole check (230 ms).
- Single-definition proof: `surface` at 10,000 from 1.15~1.43 seconds to 80~140 ms, and the row has the same bytes as with the whole proof. The 80 ms or so that remain are the preparation of the cache file and the declaration tables, proportional to the size.
