#!/usr/bin/env python3
"""Gate of the task set `gate-d` (the port twin at full size): the set and
its fixture are what the generators write, it shares no target with the set
`port`, its sizes are the frozen ones, the tool conditions pick the
reference solutions written for them, and the oracle and the weak control
of two questions behave in both arms. The oracles and weak controls of the
change tasks take hours (`pair.py check --tasks bench/twin/gate-d`) and are
run when the set changes, not here."""
import collections
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pair  # noqa: E402
import port_replay  # noqa: E402
import port_sets  # noqa: E402
import port_tasks  # noqa: E402

SET = os.path.join(HERE, "gate-d")
SIZES = {"callers": 10, "impact": 10, "diag": 10, "state": 10, "rename": 12, "swap": 8, "replay": 4, "history": 8}


def run(*argv):
    return subprocess.run([sys.executable, *argv], capture_output=True, text=True)


class Generated(unittest.TestCase):
    def test_the_fixture_is_generated(self):
        r = run(os.path.join(HERE, "port_corpus.py"), "check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_tasks_are_generated(self):
        for script in ("port_tasks.py", "port_change.py", "port_replay.py"):
            r = run(os.path.join(HERE, script), "--set", "gate-d", "check")
            self.assertEqual(r.returncode, 0, script + ": " + r.stdout + r.stderr)

    def test_the_manifest_lists_the_set(self):
        r = run(os.path.join(HERE, "port_sets.py"), "manifest", "gate-d", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Frozen(unittest.TestCase):
    def setUp(self):
        self.tasks = pair.load_tasks(SET)

    def test_sizes(self):
        self.assertEqual(dict(collections.Counter(t["family"] for t in self.tasks)), SIZES)
        self.assertEqual({t["fixture"] for t in self.tasks}, {"port-full"})
        self.assertEqual(len({t["commit"] for t in self.tasks}), 1)

    def test_no_target_of_the_first_set(self):
        new, old = port_sets.targets(port_sets.get("gate-d")), port_sets.targets(port_sets.get("port"))
        self.assertGreaterEqual(len(old), 60)
        self.assertEqual(new & old, set())
        self.assertEqual(port_sets.avoided(port_sets.get("gate-d")), old)

    def test_histories_have_five_steps_with_cases_of_their_own(self):
        for t in self.tasks:
            if t["family"] != "history":
                continue
            self.assertEqual(len(t["steps"]), 5, t["id"])
            names = [c["name"] for st in t["steps"] for c in st["cases"]]
            self.assertEqual(len(names), len(set(names)), t["id"])
            self.assertTrue(all(st["cases"] for st in t["steps"]), t["id"])

    def test_a_rename_has_the_solution_of_each_condition(self):
        for t in self.tasks:
            if t["kind"] != "change" or "steps" in t:
                continue
            for calls in [t["oracle"]] + [w for w in t["weak"] if w["bmb"]]:
                arms = sorted(k for k in calls if k != "fails")
                self.assertEqual(arms, ["bmb", "bmb:port-rename", "rust"] if t["family"] == "rename" else ["bmb", "rust"],
                                 t["id"])
            name, args = t["oracle"].get("bmb:port-rename", [[None, {}]])[0]
            if t["family"] == "rename":
                self.assertEqual((name, sorted(args), len(t["oracle"]["bmb:port-rename"])), ("write", ["rename"], 1))
                self.assertGreater(len(t["oracle"]["bmb"]), 1)


class Conditions(unittest.TestCase):
    def setUp(self):
        self.kept = {k: os.environ.pop(k, None) for k in ("PAIR_COND", "PAIR_MCP")}

    def tearDown(self):
        for k, v in self.kept.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def test_the_condition_names_the_flags_and_picks_the_calls(self):
        calls = {"bmb": ["plain"], "bmb:port-rename": ["one write"], "rust": ["edits"]}
        self.assertEqual(pair.condition("port-full"), "port")
        self.assertEqual(pair.condition("stk"), None)
        self.assertEqual(pair.calls_of(calls, "bmb", "port-full"), ["plain"])
        os.environ["PAIR_COND"] = "port-rename"
        self.assertEqual(pair.mcp_flags("port-full"), ["--write-tool", "--compact", "--bounded", "--rename-ops"])
        self.assertEqual(pair.calls_of(calls, "bmb", "port-full"), ["one write"])
        self.assertEqual(pair.calls_of(calls, "rust", "port-full"), ["edits"])
        self.assertEqual(pair.calls_of({"bmb": ["plain"], "rust": []}, "bmb", "port-full"), ["plain"])
        task = {"fixture": "port-full"}
        self.assertEqual(pair.stamp(task, "bmb"), {"docs": "none", "mcp": "--write-tool --compact --bounded --rename-ops",
                                                   "cond": "port-rename"})
        self.assertEqual(pair.stamp(task, "rust"), {"docs": "none", "mcp": None, "cond": "port-rename"})
        del os.environ["PAIR_COND"]
        # Flags given one by one are named when a condition has exactly them.
        os.environ["PAIR_MCP"] = "--write-tool --compact --bounded --rename-ops"
        self.assertEqual(pair.condition("port-full"), "port-rename")
        os.environ["PAIR_MCP"] = "--write-tool --compact"
        self.assertEqual(pair.condition("port-full"), None)


class Rules(unittest.TestCase):
    def test_every_statement_that_reports_a_code_is_cut_out(self):
        rust = ('fn f(&mut self) {\n    if a {\n        self.err("E0001", sp, "x");\n    }\n    let n = 1;\n    self.diags\n'
                '        .push(Diag::new("E0001", sp, "y").fix("z", None));\n    done();\n}')
        self.assertEqual(port_replay.without(rust, "E0001", True),
                         'fn f(&mut self) {\n    if a {\n    }\n    let n = 1;\n    done();\n}')
        # One place that is not a statement of its own: no candidate.
        self.assertIsNone(port_replay.without('a("E0001");\nlet d = Diag::new("E0001", sp);', "E0001", True))
        self.assertIsNone(port_replay.without("f();", "E0001", True))
        # The rule of the first set does not take a call broken after its receiver, nor two places.
        self.assertIsNone(port_replay.without('self.diags\n    .push(Diag::new("E0001", sp));', "E0001"))
        self.assertIsNone(port_replay.without(rust, "E0001"))

    def test_a_derived_field_is_one_whose_every_use_is_decided(self):
        plain = port_tasks.plain_field
        self.assertTrue(plain("pos", ["self.pos = 1; self.pos += 1; let n = self.pos.saturating_add(1); f(&mut self.pos)"]))
        self.assertTrue(plain("seen", ["self.seen.insert(k); if self.seen.contains(&k) { self.seen.clear() }"]))
        self.assertFalse(plain("slot", ["let old = self.slot.take();"]))         # a method that may change it
        self.assertFalse(plain("rows", ["self.rows[i].push(1);"]))               # an element changed in place
        self.assertFalse(plain("tab", ["self.tab.items[at] = x;"]))              # a field of the field
        self.assertFalse(plain("pos", ["step(&mut self.toks.pos);"]))            # passed on from deeper
        self.assertTrue(plain("rows", ["let n = self.rows[i].len();"]))

    def test_the_first_set_fills_replays_first_and_this_one_histories(self):
        corpus = {c: [(f"{c}.bmb", [])] for c in "abcdefg"}
        pool = [("x.rs", c, None) for c in "abcdefg"]
        s = {"replays": 3, "histories": 2, "steps": 2}
        picked, groups, _, _ = port_replay.plan(pool, corpus, {**s, "first": "replays"})
        self.assertEqual((picked, groups), (["a", "b", "c"], [["d", "e"], ["f", "g"]]))
        picked, groups, _, _ = port_replay.plan(pool, corpus, {**s, "first": "histories"})
        self.assertEqual((picked, groups), (["e", "f", "g"], [["a", "b"], ["c", "d"]]))


class Oracles(unittest.TestCase):
    def test_oracles_pass_and_weak_controls_fail(self):
        tasks = pair.load_tasks(SET)
        for family in ("callers", "state"):
            t = next(t for t in tasks if t["family"] == family)
            for arm in ("bmb", "rust"):
                self.assertTrue(pair.run_task(t, arm, "oracle")["success"], (t["id"], arm))
                self.assertFalse(pair.run_task(t, arm, "weak0", t["weak"][0][arm])["success"], (t["id"], arm))


if __name__ == "__main__":
    unittest.main()
