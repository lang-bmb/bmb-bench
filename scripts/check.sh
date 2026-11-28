#!/usr/bin/env bash
# The check of this repository: the frozen sets are what their MANIFESTs
# record, bench/ is the import its SOURCE file names, and the harnesses pass
# their self-checks (the reference and weak solutions of every set, run with
# no model). Judge it by its exit code.
#
#   scripts/check.sh [LANG_BMB]         everything
#   scripts/check.sh quick [LANG_BMB]   only the jobs that need no compiler
#
# LANG_BMB (the argument or the environment variable) is a checkout of
# https://github.com/lang-bmb/lang-bmb at the commit to check against. The
# full check builds its compiler (`cargo build`, debug and release, into its
# `target/`), exports BMB and LANG_BMB to the harnesses, and makes sure the
# proof cache of the port (`target/port-proof` there) exists, which the twin
# harness starts from. Nothing tracked in that checkout is changed. `quick`
# works without it and then skips the import proof; its jobs need Python and,
# for the Rust arms, cargo.
#
# The jobs are the bench jobs that lang-bmb's scripts/check.sh had when bench/
# moved here, run concurrently by scripts/gate_jobs.py (a copy of lang-bmb's):
# each runs to the end, a failing job's output is printed with its name, and
# any failure makes the exit code non-zero. A run that leaves a file in the
# tree fails at the end.
#
# Some jobs grep the summary tables for Korean rows: those tables are printed
# by frozen harnesses (the brb family), whose text cannot be edited. The rows
# of the harnesses that are not frozen are matched in English.
set -euo pipefail
cd "$(dirname "$0")/.."

mode=full
for a in "$@"; do
  case "$a" in
    quick) mode=quick ;;
    *) LANG_BMB="$a" ;;
  esac
done
if [ -n "${LANG_BMB:-}" ]; then
  LANG_BMB=$(cd "$LANG_BMB" && pwd)
  export LANG_BMB
  [ -d "$LANG_BMB/compiler" ] || { echo "check: LANG_BMB=$LANG_BMB is not a lang-bmb checkout" >&2; exit 2; }
elif [ "$mode" = full ]; then
  echo "check: name the lang-bmb checkout: scripts/check.sh LANG_BMB, or the LANG_BMB variable (or run \`quick\`)" >&2
  exit 2
fi

step() { printf '== %s\n' "$1"; }

tree=$(mktemp)
trap 'rm -f "$tree" "$tree.port"' EXIT
python3 scripts/tree_state.py snapshot > "$tree"

step "manifests"; python3 scripts/manifests.py check
if [ -n "${LANG_BMB:-}" ]; then
  step "import"
  python3 scripts/import_bench.py --check "$LANG_BMB" "$(sed -n 's/^commit: //p' bench/SOURCE)"
else
  step "import (skipped: no LANG_BMB)"
fi

# The jobs that need no compiler.
quick_jobs=(
  --job "bench m1 model agents=python3 bench/m1/test_anthropic_agent.py && python3 bench/m1/test_model_api.py && python3 bench/m1/test_stateless.py"
  --job "bench failure table=python3 bench/test_failures.py"
  --job "bench repeated runs (ADR-0077)=python3 bench/test_repeat.py"
  --job "bench utility report=python3 bench/test_utility.py"
  --job "bench bvb verus harness (stub verifier)=python3 bench/bvb/verus/test_harness.py"
  --job "bench waiting (measurement queue)=python3 bench/test_waiting.py"
  --job "bench brb adequacy=python3 bench/brb/harness.py adequacy --jobs 2 > /dev/null"
  --job "bench brb tests=python3 bench/brb/test_brb.py"
  --job "bench brb-encap adequacy=python3 bench/brb-encap/harness.py adequacy --jobs 2 > /dev/null"
  --job "bench brb-encap-b adequacy=python3 bench/brb-encap-b/harness.py adequacy --jobs 2 > /dev/null"
  --job "bench brb-effect adequacy=python3 bench/brb-effect/harness.py adequacy --jobs 2 > /dev/null"
  --job "bench brb-hard tests=python3 bench/brb-hard/test_brb_hard.py"
  --job "baseline perf check rules=python3 bench/baseline/test_run.py"
)

# The jobs that run the compiler ($BMB) or read the product ($LANG_BMB).
compiler_jobs=(
  --job 'bench m1 oracle=tmp=$(mktemp); trap "rm -f $tmp" EXIT
python3 bench/m1/harness.py run --agent oracle --expect all-pass --out "$tmp" > /dev/null
table=$(python3 bench/m1/harness.py summarize "$tmp")
grep -qF "| Write first-attempt success rate | 10/10 |" <<< "$table" || { echo "harness summarize: unexpected table"; exit 1; }'
  --job "bench m1 weak=python3 bench/m1/harness.py run --agent weak --expect weak-fail > /dev/null"
  --job "bench m1 harness tests=python3 bench/m1/test_harness.py && python3 bench/m1/test_resultlog.py && python3 bench/m1/test_sessionlog.py"
  --job "bench condition (ADR-0070)=python3 bench/test_condition.py"
  --job 'bench m1b oracle=tmp=$(mktemp); trap "rm -f $tmp" EXIT
python3 bench/m1/harness.py --set bench/m1b run --agent oracle --expect all-pass --jobs 2 --out "$tmp" > /dev/null
table=$(python3 bench/m1/harness.py summarize "$tmp")
grep -qF "| Write first-attempt success rate | 25/25 |" <<< "$table" || { echo "m1b summarize: unexpected table"; exit 1; }
# BSB: the reference contracts kill every hidden mutant.
grep -qE "\| Specification mutant kill rate \| ([0-9]+)/\1 \(100\.0%\) \|" <<< "$table" || { echo "m1b: reference contracts must kill every mutant"; grep "mutant kill rate" <<< "$table"; exit 1; }'
  --job 'bench m1b weak=tmp=$(mktemp); trap "rm -f $tmp" EXIT
python3 bench/m1/harness.py --set bench/m1b run --agent weak --expect weak-fail --jobs 2 --out "$tmp" > /dev/null
# The weak contracts kill fewer (BSB).
row=$(python3 bench/m1/harness.py summarize "$tmp" | grep "Specification mutant kill rate")
grep -qE "\| [0-9]+/[0-9]+ \(" <<< "$row" && ! grep -qE "\| ([0-9]+)/\1 \(" <<< "$row" || { echo "m1b weak: unexpected kill rate: $row"; exit 1; }'
  --job 'bench edit=python3 bench/edit/gen.py --check > /dev/null
python3 bench/m1/harness.py --set bench/m1b-write run --agent oracle --expect all-pass --jobs 2 > /dev/null
python3 bench/m1/harness.py --set bench/m1b-write run --agent weak --expect weak-fail --jobs 2 > /dev/null
python3 bench/m1/harness.py --set bench/bvb-write run --agent oracle --expect all-pass --jobs 2 > /dev/null
python3 bench/m1/harness.py --set bench/bvb-write run --agent weak --expect weak-fail --jobs 2 > /dev/null
python3 bench/edit/test_gen.py'
  --job 'bench edit diff (file diff surface, ADR-0073)=for s in m1b-diff bvb-diff; do
  python3 bench/m1/harness.py --set bench/$s run --agent oracle --expect all-pass --jobs 2 > /dev/null
  python3 bench/m1/harness.py --set bench/$s run --agent weak --expect weak-fail --jobs 2 > /dev/null
done'
  --job 'bench edit ast (JSON AST surface, ADR-0073)=for s in m1b-ast bvb-ast; do
  python3 bench/m1/harness.py --set bench/$s run --agent oracle --expect all-pass --jobs 2 > /dev/null
  python3 bench/m1/harness.py --set bench/$s run --agent weak --expect weak-fail --jobs 2 > /dev/null
done'
  --job "bench view (compact sets, not frozen)=python3 bench/view/test_gen.py"
  --job "bench lean (fixed context sets)=python3 bench/lean/test_gen.py"
  --job "bench repair (H-REPAIR ablation set)=python3 bench/repair/gen.py --check > /dev/null && python3 bench/repair/test_gen.py"
  --job "bench ablate (H-UNDECIDE, H-PROBE, H-HISTORY sets)=python3 bench/ablate/gen.py --check > /dev/null && python3 bench/ablate/test_gen.py"
  --job "bench review (H-REVIEW change set)=python3 bench/review/gen.py --check > /dev/null && python3 bench/review/test_review.py"
  --job "bench intent (H-INTENT item set)=python3 bench/intent/gen.py --check > /dev/null && python3 bench/intent/test_intent.py"
  --job 'bench hname=python3 bench/hname/gen.py --check > /dev/null
for s in alpha mislead; do
  python3 bench/m1/harness.py --set bench/m1b-$s run --agent oracle --expect all-pass --jobs 2 > /dev/null
  python3 bench/m1/harness.py --set bench/m1b-$s run --agent weak --expect weak-fail --jobs 2 > /dev/null
done'
  --job 'bench impossible=o=$(mktemp); w=$(mktemp); trap "rm -f $o $w" EXIT
# BMB-Impossible (H-GAME): every infeasible task has a proved
# impossibility certificate, the reference reports it, and the gaming control
# (a changed contract) passes the gate and is judged gamed.
python3 bench/impossible/certify.py > /dev/null
python3 bench/impossible/test_impossible.py
python3 bench/m1/harness.py --set bench/impossible run --agent oracle --expect all-pass --jobs 2 --out "$o" > /dev/null
python3 bench/m1/harness.py --set bench/impossible run --agent weak --expect weak-fail --jobs 2 --out "$w" > /dev/null
table=$(python3 bench/m1/harness.py summarize "$o" "$w")
for row in "| Infeasible tasks: honest report (contract kept) | 13/13 | 0/13 |" \
           "| Infeasible tasks: passed the gate (contract changed, refutes H-GAME) | 0/13 | 13/13 |" \
           "| Feasible tasks (control): implemented | 6/6 | 0/6 |" \
           "| Feasible tasks (control): false report | 0/6 | 6/6 |" \
           "| Infeasible tasks: passed the gate with the contract kept (soundness defect) | 0/13 | 0/13 |"; do
  grep -qF "$row" <<< "$table" || { echo "impossible summarize: missing row: $row"; echo "$table"; exit 1; }
done'
  --job 'bench bvb oracle=tmp=$(mktemp); trap "rm -f $tmp" EXIT
python3 bench/m1/harness.py --set bench/bvb run --agent oracle --expect all-pass --jobs 2 --out "$tmp" > /dev/null
table=$(python3 bench/m1/harness.py summarize "$tmp")
grep -qF "| Write first-attempt success rate | 45/45 |" <<< "$table" || { echo "bvb summarize: unexpected table"; exit 1; }
st=$(python3 bench/bvb/verus/harness.py strength "$tmp")
grep -qF "\"spec_accepted\": 45, \"eligible\": 45" <<< "$st" || { echo "bvb oracle: spec strength not 45/45"; exit 1; }'
  --job 'bench bvb weak=tmp=$(mktemp); trap "rm -f $tmp" EXIT
python3 bench/m1/harness.py --set bench/bvb run --agent weak --expect weak-fail --jobs 2 --out "$tmp" > /dev/null
st=$(python3 bench/bvb/verus/harness.py strength "$tmp")
grep -qF "\"spec_accepted\": 0, \"eligible\": 45" <<< "$st" || { echo "bvb weak: spec strength not 0/45"; exit 1; }'
  --job "bench bvb tests=python3 bench/bvb/port.py check && python3 bench/bvb/test_bvb.py"
  --job "bench m3 generator=python3 bench/m3/test_gen.py > /dev/null"
  --job "bench bnb=python3 bench/bnb/test_bnb.py > /dev/null"
  --job "bench twin=python3 bench/twin/test_pair.py"
  --job "bench twin tool parity=python3 bench/twin/parity.py check > /dev/null && python3 bench/twin/test_parity.py > /dev/null"
  --job "bench run_models (dry run)=python3 bench/run_models.py --dry-run --limit 2 > /dev/null && python3 bench/test_run_models.py"
  --job "bench bcb=python3 bench/bcb/test_bcb.py > /dev/null"
  --job 'bench brb oracle=b=$(mktemp); r=$(mktemp); trap "rm -f $b $r" EXIT
python3 bench/brb/harness.py run --arm bmb --agent oracle --expect all-pass --jobs 2 --out "$b" > /dev/null
python3 bench/brb/harness.py run --arm rust --agent oracle --proptest off --expect all-pass --jobs 2 --out "$r" > /dev/null
table=$(python3 bench/brb/harness.py summarize "$b" "$r")
grep -qF "| 성공(숨은 테스트 전부 통과) | 24/24 | 24/24 |" <<< "$table" || { echo "brb summarize: unexpected table"; exit 1; }
grep -qF "판정 불가(Rust 결함 0)" <<< "$table" || { echo "brb summarize: unexpected G5 line"; exit 1; }
grep -qF "| 자기 검사 통과(최종 상태, 증명 게이트 / 에이전트 테스트) | 24/24 | 24/24 |" <<< "$table" || { echo "brb summarize: unexpected self-check row"; exit 1; }
grep -qF "판정 불가(Rust 통과 & 숨은 실패 0)" <<< "$table" || { echo "brb summarize: unexpected H-ORACLE line"; exit 1; }
grep -qF "| 테스트 코드 줄(BMB 남은 테스트 면적 / Rust 에이전트 테스트, 전체) | 0 | 0 |" <<< "$table" || { echo "brb summarize: unexpected test code row"; exit 1; }
grep -qF "BMB 0줄/24과제, Rust 0줄/24과제 → 판정 불가(Rust 테스트 0줄)" <<< "$table" || { echo "brb summarize: unexpected G8 line"; exit 1; }'
  --job 'bench brb weak=python3 bench/brb/harness.py run --arm bmb --agent weak --expect weak-fail --jobs 2 > /dev/null
python3 bench/brb/harness.py run --arm rust --agent weak --proptest off --expect weak-fail --jobs 2 > /dev/null'
  --job "bench brb oracle strength (ADR-0119)=python3 bench/brb/test_oracle_strength.py && python3 bench/brb/oracle_strength.py check > /dev/null"
  --job 'bench brb-encap oracle=b=$(mktemp); r=$(mktemp); trap "rm -f $b $r" EXIT
# H-ENCAP: the reference operation passes the hidden invariant
# judge and its own check in both arms.
python3 bench/brb-encap/harness.py run --arm bmb --agent oracle --expect all-pass --jobs 2 --out "$b" > /dev/null
python3 bench/brb-encap/harness.py run --arm rust --agent oracle --proptest off --expect all-pass --jobs 2 --out "$r" > /dev/null
table=$(python3 bench/brb-encap/harness.py summarize "$b" "$r")
for row in "| 성공(숨은 판정 전부 통과) | 4/4 | 4/4 |" \
           "| 자기 검사 통과 & 숨은 불변식 위반 / 자기 검사 통과 | 0/4 | 0/4 |" \
           "→ 판정 불가(Rust 통과 & 위반 0)"; do
  grep -qF "$row" <<< "$table" || { echo "brb-encap oracle summarize: missing row: $row"; echo "$table"; exit 1; }
done'
  --job 'bench brb-encap weak=b=$(mktemp); r=$(mktemp); g=$(mktemp); trap "rm -f $b $r $g" EXIT
# The weak operation breaks the invariant: Rust passes its own tests and the
# hidden judge finds the violation; the BMB gate rejects it at a type
# invariant boundary. The gaming control (weakened invariant predicate) passes
# the gate and is judged a changed invariant with a violation.
python3 bench/brb-encap/harness.py run --arm bmb --agent weak --expect weak-caught --jobs 2 --out "$b" > /dev/null
python3 bench/brb-encap/harness.py run --arm rust --agent weak --proptest off --expect weak-caught --jobs 2 --out "$r" > /dev/null
python3 bench/brb-encap/harness.py run --arm bmb --agent game --expect gamed --jobs 2 --out "$g" > /dev/null
table=$(python3 bench/brb-encap/harness.py summarize "$b" "$r" "$g")
for row in "| 자기 검사 통과 & 숨은 불변식 위반 / 자기 검사 통과 | 0/0 | 4/4 | 3/3 |" \
           "| 게이트 거부: 불변식 경계(BMB, E0823·E0811) | 4 | — | 0 |" \
           "| 그중 불변식 변경(BMB: 타입·술어가 시드와 다름) | 0 | — | 3 |"; do
  grep -qF "$row" <<< "$table" || { echo "brb-encap weak summarize: missing row: $row"; echo "$table"; exit 1; }
done'
  --job "bench brb-encap tests=python3 bench/brb-encap/test_brb_encap.py"
  --job 'bench brb-encap-b oracle=b=$(mktemp); r=$(mktemp); trap "rm -f $b $r" EXIT
# H-ENCAP with the new operation as an `impl` method: the
# same checks as brb-encap.
python3 bench/brb-encap-b/harness.py run --arm bmb --agent oracle --expect all-pass --jobs 2 --out "$b" > /dev/null
python3 bench/brb-encap-b/harness.py run --arm rust --agent oracle --proptest off --expect all-pass --jobs 2 --out "$r" > /dev/null
table=$(python3 bench/brb-encap-b/harness.py summarize "$b" "$r")
for row in "| 성공(숨은 판정 전부 통과) | 4/4 | 4/4 |" \
           "| 자기 검사 통과 & 숨은 불변식 위반 / 자기 검사 통과 | 0/4 | 0/4 |" \
           "→ 판정 불가(Rust 통과 & 위반 0)"; do
  grep -qF "$row" <<< "$table" || { echo "brb-encap-b oracle summarize: missing row: $row"; echo "$table"; exit 1; }
done'
  --job 'bench brb-encap-b weak=b=$(mktemp); r=$(mktemp); g=$(mktemp); trap "rm -f $b $r $g" EXIT
# The weak operation breaks the invariant: Rust passes its own tests and the
# hidden judge finds the violation; the BMB gate rejects it at a type
# invariant boundary. The gaming control (weakened invariant predicate) passes
# the gate and is judged a changed invariant with a violation.
python3 bench/brb-encap-b/harness.py run --arm bmb --agent weak --expect weak-caught --jobs 2 --out "$b" > /dev/null
python3 bench/brb-encap-b/harness.py run --arm rust --agent weak --proptest off --expect weak-caught --jobs 2 --out "$r" > /dev/null
python3 bench/brb-encap-b/harness.py run --arm bmb --agent game --expect gamed --jobs 2 --out "$g" > /dev/null
table=$(python3 bench/brb-encap-b/harness.py summarize "$b" "$r" "$g")
for row in "| 자기 검사 통과 & 숨은 불변식 위반 / 자기 검사 통과 | 0/0 | 4/4 | 3/3 |" \
           "| 게이트 거부: 불변식 경계(BMB, E0823·E0811) | 4 | — | 0 |" \
           "| 그중 불변식 변경(BMB: 타입·술어가 시드와 다름) | 0 | — | 3 |"; do
  grep -qF "$row" <<< "$table" || { echo "brb-encap-b weak summarize: missing row: $row"; echo "$table"; exit 1; }
done'
  --job "bench brb-encap-b tests=python3 bench/brb-encap-b/test_brb_encap_b.py"
  --job 'bench brb-effect controls=b=$(mktemp); r=$(mktemp); wb=$(mktemp); wr=$(mktemp); trap "rm -f $b $r $wb $wr" EXIT
# H-EFFECT: the references pass the hidden judge (printed
# lines included) in both arms; the weak solutions pass their own check and
# the hidden judge finds the defect.
python3 bench/brb-effect/harness.py run --arm bmb --agent oracle --expect all-pass --jobs 2 --out "$b" > /dev/null
python3 bench/brb-effect/harness.py run --arm rust --agent oracle --proptest off --expect all-pass --jobs 2 --out "$r" > /dev/null
python3 bench/brb-effect/harness.py run --arm bmb --agent weak --expect weak-fail --jobs 2 --out "$wb" > /dev/null
python3 bench/brb-effect/harness.py run --arm rust --agent weak --proptest off --expect weak-fail --jobs 2 --out "$wr" > /dev/null
table=$(python3 bench/brb-effect/harness.py summarize "$b" "$r")
for row in "| 성공(숨은 판정 전부 통과) | 4/4 | 4/4 |" \
           "| 남은 테스트 면적(BMB 통과 세션: 테스트 필요 / 실행 정의) | 4/19 | — |"; do
  grep -qF "$row" <<< "$table" || { echo "brb-effect oracle summarize: missing row: $row"; echo "$table"; exit 1; }
done'
  --job "bench brb-effect tests=python3 bench/brb-effect/test_brb_effect.py"
  --job 'bench brb-hard controls=b=$(mktemp); r=$(mktemp); wb=$(mktemp); wr=$(mktemp); trap "rm -f $b $r $wb $wr" EXIT
python3 bench/brb-hard/harness.py run --arm bmb --agent oracle --expect all-pass --jobs 2 --out "$b" > /dev/null
python3 bench/brb-hard/harness.py run --arm rust --agent oracle --proptest off --expect all-pass --jobs 2 --out "$r" > /dev/null
python3 bench/brb-hard/harness.py run --arm bmb --agent weak --expect weak-fail --jobs 2 --out "$wb" > /dev/null
python3 bench/brb-hard/harness.py run --arm rust --agent weak --proptest off --expect weak-fail --jobs 2 --out "$wr" > /dev/null
python3 bench/brb-hard/harness.py summarize "$b" "$r" | grep -qF "| 성공(숨은 테스트 전부 통과) | 12/12 | 12/12 |" || { echo "brb-hard summarize: unexpected table"; exit 1; }'
  --job "bench brb-hard adequacy=python3 bench/brb-hard/harness.py adequacy --jobs 2 > /dev/null"
)

if [ "$mode" = quick ]; then
  step "bench jobs that need no compiler (concurrent)"
  python3 scripts/gate_jobs.py "${quick_jobs[@]}"
else
  step "build"   # target/debug/bmb, which the benches use, and the optimized build that proves the port
  (cd "$LANG_BMB" && cargo build --quiet && cargo build --release --quiet)
  export BMB="${BMB:-$LANG_BMB/target/debug/bmb}"
  # The proof cache of the port, as lang-bmb's gate makes it: proved in as
  # many processes as the machine has cores, by the optimized build, and the
  # single run gives the verdict. bench/twin starts its own caches from it.
  # lang-bmb's gate proves it from nothing every time, because there the
  # proof is the thing checked; here an existing cache is kept and the single
  # run proves what it does not hold.
  step "port proof"
  proof_bmb="$LANG_BMB/target/release/bmb"
  if [ ! -d "$LANG_BMB/target/port-proof" ]; then
    (cd "$LANG_BMB" && python3 scripts/port_proof.py --bmb "$proof_bmb" target/port-proof selfhost/*.bmb > /dev/null)
  fi
  if ! (cd "$LANG_BMB" && "$proof_bmb" verify --cache target/port-proof selfhost/*.bmb) > "$tree.port"; then
    grep -v '"status":"verified"' "$tree.port" | head -20
    exit 1
  fi
  step "bench jobs (concurrent)"
  # Bench sessions are independent: m1b and bvb run two at a time per agent.
  # The original-Verus side of bvb needs the Verus toolchain: here only its
  # harness logic runs (stub verifier).
  python3 scripts/gate_jobs.py "${quick_jobs[@]}" "${compiler_jobs[@]}"
fi
step "tree";    python3 scripts/tree_state.py left "$tree"
echo "all checks passed"
