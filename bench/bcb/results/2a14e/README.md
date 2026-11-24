# 2a14e: BCB measurement at N=1,000 and 10,000 (H-AMORT, G7)

`2a14e` is the label of this measurement. What follows is registered before the first `suite` row (2026-11-10).

## Conditions

- **Plan:** `bcb.py suite` runs `SUITE` in order. For every history the arms (`rust`, `b1`, `b0`, `defects`) run separately.
  - When interrupted, the same command continues where it stopped.
  - The result header line has the commit, the MANIFEST and the compiler's hash.
- **Compiler:** only the copy that `suite` makes at `W/bin/bmb` the first time it runs.
- **Overlap:**
  - It may overlap with model sessions of a BMB arm (measured in `../inf19/`).
  - It does not overlap with judging that runs compilation, the gate or `cargo test` (BCB README). Such work is done only between chunks of the run.
  - Any stretch that did overlap is stated in the record.
- **CPU pinning:** none. The condition that `../inf19/` checked was without pinning.

## Verdict

1. **The verdict lines are those of ADR-0042 §5.**
   - Condition 1: refuted if C_B1 ≥ C_R1 at N = 10,000, K = 1,000, 0 events. `body-heavy` and `contract-heavy` are looked at separately.
   - Condition 2: the firewall comparison.
   - Condition 3: refuted if C_B1 > C_R1 at 4 events.
   - Condition 4: refuted if the defect detection rate of B1 < that of R2.
2. **Band of host variation (`../inf19/`).** When the ratio C_B1/C_R1 of condition 1 or 3 is between 0.9 and 1.1, that item is written as **cannot be judged (host variation)**.
   - Reason: the two arms are different runs, and the absolute CPU moved by up to about 9% between runs.
   - Outside the band the verdict is that of ADR-0042 §5.
   - The band applies to both sides alike. 0.9 to 1.0 is not called "supported" either.
3. **G7 (ROADMAP) is read from the results above.** The criterion is "at or below the Rust twin with test selection and caching, and defect detection equal or better".
