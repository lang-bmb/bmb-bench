#!/usr/bin/env python3
"""Gate of the port-twin harness: the item splitter, the Rust
tools' sandbox, and `pair.py check` on the fixture (twins agree on the
corpus, every oracle succeeds, every weak control fails its check)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pair  # noqa: E402


class Items(unittest.TestCase):
    def test_rust_items_take_docs_and_bodies(self):
        text = ('//! m\nuse a::b;\n\n/// Doc.\npub fn f(x: i64) -> i64 {\n    if x > 0 { "}" } else { \'{\' };\n'
                '    x\n}\n\npub const N: usize = 3;\nfn g() {}\n')
        it = pair.rust_items(text, "m")
        self.assertEqual(sorted(it), ["m::<rest>", "m::N", "m::f", "m::g"])
        self.assertTrue(it["m::f"].startswith("/// Doc.\npub fn f") and it["m::f"].endswith("    x\n}"))
        self.assertEqual(it["m::<rest>"], "//! m\nuse a::b;")

    def test_bmb_items_by_unit_indent(self):
        text = ('#[summary("u")]\nmod u {\n    spec fn p(x: i64) -> bool { x > 0 }\n\n    #[effects(pure)]\n'
                '    fn f(x: i64) -> i64\n        requires p(x),\n    {\n        x\n    }\n}\n')
        it = pair.split_items(text, "u", "    ", pair.BMB_ITEM)
        self.assertEqual(sorted(it), ["u::<rest>", "u::f", "u::p"])
        self.assertTrue(it["u::f"].startswith("    #[effects(pure)]\n    fn f") and it["u::f"].endswith("    }"))

    def test_scope(self):
        before = {"a::f": "1", "a::g": "2"}
        after = {"a::f": "1x", "a::g": "2", "a::h": "3"}
        task = {"scope": {"rust": ["a::f"]}}
        self.assertEqual(pair.out_of_scope(task, "rust", before, after), ["a::h"])
        task["scope"]["new"] = True
        self.assertEqual(pair.out_of_scope(task, "rust", before, after), [])


class Comments(unittest.TestCase):
    """The Rust arm without comments (ADR-0106)."""

    def test_strip_keeps_code_and_inner_doc(self):
        src = ("//! m doc\n/// d\npub fn f<'a>(x: &'a str) -> char { // tail\n"
               '    let s = "// no /* \\" x"; let r = r#"y // " z"#; let b = b"//";\n'
               "    /* a /* nested */ b */ let c = '\\''; let q = '\"'; let u = '\\u{2f}';\n"
               "    /** block doc */\n    c\n}\n")
        want = ("//! m doc\npub fn f<'a>(x: &'a str) -> char {\n"
                '    let s = "// no /* \\" x"; let r = r#"y // " z"#; let b = b"//";\n'
                "     let c = '\\''; let q = '\"'; let u = '\\u{2f}';\n    c\n}\n")
        self.assertEqual(pair.strip_comments(src), want)

    def test_inner_doc_must_be_the_summary(self):
        self.assertEqual(pair.inner_doc("//! vm: the stack\n//!\n//! codes: 1\nfn f() {}\n"), "vm: the stack codes: 1")
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "vm.bmb"), "w") as f:
                f.write('#[summary("vm: the stack")]\nmod vm {\n}\n')
            self.assertEqual(pair.summaries(d), {"vm": "vm: the stack"})
        self.assertEqual(pair.doc_parity("stk"), [])

    def test_docs_condition_keeps_outer_docs_only(self):
        src = "//! m\n/// d one\n/// d two\n//// not a doc\n#[inline]\nfn f() {} // tail\n/* b */\n"
        self.assertEqual(pair.strip_comments(src, docs=True), "//! m\n/// d one\n/// d two\n#[inline]\nfn f() {}\n")
        bmb = "mod m {\n    /// d one\n    /// d two\n    #[effects(pure)]\n    fn f() -> () {\n    }\n}\n"
        self.assertEqual(pair.strip_summaries(bmb), "mod m {\n    #[effects(pure)]\n    fn f() -> () {\n    }\n}\n")
        self.assertEqual(pair.item_docs(src), {"f": ["d one d two"]})
        self.assertEqual(pair.item_docs(bmb), {"f": ["d one d two"]})
        self.assertEqual(pair.item_docs("/// a\npub(crate) const N: usize = 1;\n/// b\nspec fn g() -> int;\n"),
                         {"N": ["a"], "g": ["b"]})

    def test_rust_docs_may_only_add_the_contract_in_words(self):
        ok = lambda extra: bool(pair.EXTRA.fullmatch(extra))  # noqa: E731
        self.assertTrue(ok(""))
        self.assertTrue(ok(" Requires `lo < hi <= s.len()`."))
        self.assertTrue(ok(" Requires x > 0. Ensures the result is 1.5 times x."))
        self.assertFalse(ok(" Also note the cache."))
        self.assertFalse(ok(" Requires x > 0. See vm."))

    def test_scope_ignores_comment_edits(self):
        a = pair.rust_items(pair.strip_comments("/// old\nfn f() {}\n"), "m")
        b = pair.rust_items(pair.strip_comments("/// new words\nfn f() {} // and here\n"), "m")
        self.assertEqual(pair.changed(a, b), [])


class RustTools(unittest.TestCase):
    def test_sandbox_and_edit(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "src"))
            with open(os.path.join(d, "src", "a.rs"), "w") as f:
                f.write("x x y\n")
            t = pair.RustTools(d, os.path.join(d, "target"))
            self.assertTrue(t.call("read_file", {"path": "../etc/passwd"})[1])
            self.assertTrue(t.call("write_file", {"path": "Cargo.toml", "content": ""})[1])
            self.assertTrue(t.call("edit_file", {"path": "src/a.rs", "old": "x", "new": "z"})[1])
            self.assertFalse(t.call("edit_file", {"path": "src/a.rs", "old": "y", "new": "z"})[1])
            self.assertEqual(t.call("read_file", {"path": "src/a.rs"})[0], "1\tx x z\n")
            self.assertEqual(t.call("grep", {"pattern": "z$"})[0], "src/a.rs:1:x x z\n")


class Rename(unittest.TestCase):
    """The Rust arm's `rename` (rust-analyzer), which only the tool
    condition `port-rename-both` gives."""

    def test_only_the_condition_gives_it(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "src"))
            t = pair.RustTools(d, os.path.join(d, "target"))
            self.assertEqual([x["name"] for x in t.tools], [x["name"] for x in pair.RUST_TOOLS])
            self.assertEqual(t.call("rename", {"path": "src/a.rs", "line": 1, "name": "x", "new_name": "y"}),
                             ("unknown tool rename", True))
            self.assertEqual(t.facts(), {})
        kept = os.environ.pop("PAIR_COND", None)
        try:
            self.assertEqual(pair.rust_extra("port-full"), [])
            os.environ["PAIR_COND"] = "port-rename"
            self.assertEqual(pair.rust_extra("port-full"), [])
            os.environ["PAIR_COND"] = "port-rename-both"
            self.assertEqual(pair.rust_extra("port-full"), ["rename"])
            self.assertEqual([x["name"] for x in pair.rust_tools(["rename"])][-1], "rename")
        finally:
            os.environ.pop("PAIR_COND", None)
            if kept is not None:
                os.environ["PAIR_COND"] = kept

    def test_edits_are_applied_by_utf16_position(self):
        import ra
        text = "let é = f(a);\nlet 𝑥 = f(b); f(c)\n"
        edit = lambda ln, a, b, new: {"range": {"start": {"line": ln, "character": a},  # noqa: E731
                                                "end": {"line": ln, "character": b}}, "newText": new}
        # `𝑥` is two UTF-16 units: the first `f` of line 1 is at unit 9, character 8.
        got = ra.apply_edits(text, [edit(0, 8, 9, "g"), edit(1, 9, 10, "g"), edit(1, 15, 16, "g")])
        self.assertEqual(got, "let é = g(a);\nlet 𝑥 = g(b); g(c)\n")
        self.assertEqual(ra.column("a.drop(drop_all, drop)", "drop"), 2)
        self.assertIsNone(ra.column("dropped", "drop"))

    @unittest.skipUnless(__import__("ra").version(), "no rust-analyzer (rustup component add rust-analyzer rust-src)")
    def test_a_rename_is_the_declaration_and_every_use(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            crate = os.path.join(d, "stk")
            shutil.copytree(os.path.join(HERE, "fixtures", "stk", "rust"), crate, ignore=shutil.ignore_patterns("target"))
            want = {}
            for f in ("vm.rs", "main.rs", "lex.rs"):
                with open(os.path.join(crate, "src", f), encoding="utf-8") as h:
                    want[f] = h.read().replace("pub fn drop(", "pub fn discard(").replace("vm::drop(st)", "vm::discard(st)")
            t = pair.RustTools(crate, os.path.join(d, "target"), ["rename"])
            try:
                with open(os.path.join(crate, "src", "main.rs"), encoding="utf-8") as h:
                    use = next(i for i, ln in enumerate(h.read().split("\n"), 1) if "vm::drop(st)" in ln)
                # Named by a use, not the declaration; the string "drop" on the line before stays.
                text, err = t.call("rename", {"path": "src/main.rs", "line": use, "name": "drop", "new_name": "discard"})
                self.assertEqual((text, err), ("renamed `drop` to `discard`: 2 places in 2 files\nsrc/main.rs: 1\n"
                                               "src/vm.rs: 1\n", False))
                for f, text in want.items():
                    with open(os.path.join(crate, "src", f), encoding="utf-8") as h:
                        self.assertEqual(h.read(), text, f)
                # What it refuses: a name that is not on the line, a name of the standard library, no identifier.
                refused = lambda **a: t.call("rename", {"path": "src/main.rs", "line": use, **a})  # noqa: E731
                self.assertEqual(refused(name="drop", new_name="x"),
                                 (f"error: `drop` is not on line {use} of src/main.rs", True))
                self.assertTrue(refused(name="discard", new_name="a b")[1])
                with open(os.path.join(crate, "src", "vm.rs"), encoding="utf-8") as h:
                    vec = next(i for i, ln in enumerate(h.read().split("\n"), 1) if "Vec<" in ln)
                text, err = t.call("rename", {"path": "src/vm.rs", "line": vec, "name": "Vec", "new_name": "List"})
                self.assertTrue(err and "non-local" in text, text)
                # An edit of the session is what the next rename sees.
                self.assertFalse(t.call("edit_file", {"path": "src/vm.rs", "old": "pub fn discard(",
                                                      "new": "\n\npub fn discard("})[1])
                text, err = t.call("rename", {"path": "src/main.rs", "line": use, "name": "discard", "new_name": "drop"})
                self.assertFalse(err, text)
                with open(os.path.join(crate, "src", "vm.rs"), encoding="utf-8") as h:
                    self.assertIn("\n\n\npub fn drop(st", h.read())
                facts = t.facts()
                self.assertEqual(len(facts["rename_s"]), 3)  # the two the harness refused did not reach the server
                self.assertGreater(facts["ra_ready_s"], 0)
            finally:
                t.close()
            self.assertEqual(pair.cargo(crate, os.path.join(d, "target"), ["build"])[0], 0)


class Gate(unittest.TestCase):
    def test_check(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "pair.py"), "check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-4000:])


class Port(unittest.TestCase):
    """The comprehension tasks on the port twin."""

    def test_rust_index_names_methods_by_their_type(self):
        import index
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "compiler", "src"))
            with open(os.path.join(d, "compiler", "src", "m.rs"), "w") as f:
                f.write('fn free(x: i64) -> i64 {\n    x // "E0001"\n}\n\nimpl<\'a> T<\'a> {\n    pub fn get(&self) -> i64 {\n'
                        '        free(self.x)\n    }\n}\n\nimpl Tr for U {\n    fn run(&mut self) {\n        self.n += 1;\n'
                        '    }\n}\n\n#[cfg(test)]\nmod tests {\n    fn t() {}\n}\n')
            it = index.rust_index(d, ["m.rs"])
        self.assertEqual(sorted(it), ["m::T::get", "m::U::run", "m::free"])
        self.assertNotIn("E0001", it["m::free"])  # a comment is not the function's text
        self.assertEqual(index.callers(it, "m::free"), {"m::T::get"})

    def test_tasks_are_generated_and_the_index_agrees_with_the_map(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "port_tasks.py"), "check"], capture_output=True,
                           text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_change_tasks_are_generated(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "port_change.py"), "check"], capture_output=True,
                           text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_swapping_two_parameters_follows_the_calls(self):
        import port_change
        text = ('fn f(&self, a: i64, b: Vec<u8>) -> i64 {\n    self.f(1, g(2, 3)) + T::f(self, x, "a,b)")\n}\n'
                'fn h() {\n    f::<T>(\n        p,\n        q[1],\n    );\n}')
        got, names = port_change.swapped(text, "f")
        self.assertEqual(names, ("a", "b"))
        self.assertEqual(got, 'fn f(&self, b: Vec<u8>, a: i64) -> i64 {\n    self.f(g(2, 3), 1) + T::f(self, "a,b)", x)\n}\n'
                              'fn h() {\n    f::<T>(\n        q[1],\n        p,\n    );\n}')
        # A closure in an argument list is not cut: no task is made of it.
        self.assertIsNone(port_change.swapped("fn f(a: i64, b: i64) {}\nfn g() { f(1, h(|x, y| x)) }", "f"))

    def test_edits_replace_stretches_that_occur_once(self):
        import port_change
        old, new = "a\nb\nc\nb\nd", "a\nB\nc\nb\nD"
        text = old
        for o, n in port_change.edits_between(old, new):
            self.assertEqual(text.count(o), 1)
            text = text.replace(o, n, 1)
        self.assertEqual(text, new)
        text = "x(1)\ny\nx(1)"
        for o, n in port_change.edits_for(text, r"x\(", "z("):
            self.assertEqual(text.count(o), 1)
            text = text.replace(o, n, 1)
        self.assertEqual(text, "z(1)\ny\nz(1)")

    def test_replay_tasks_are_generated(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "port_replay.py"), "check"], capture_output=True,
                           text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_statement_that_reports_a_code_is_cut_out(self):
        import port_replay
        rust = ('fn f(&mut self) {\n    if bad {\n        self.diags.push(\n            Diag::new("E0001", sp, "a; b")\n'
                '                .fix("c", None),\n        );\n        return None;\n    }\n}')
        self.assertEqual(port_replay.without(rust, "E0001"), 'fn f(&mut self) {\n    if bad {\n        return None;\n    }\n}')
        bmb = 'Some(o) => { self.err("E0001", "a {"); self.bump(); },'
        self.assertEqual(port_replay.without(bmb, "E0001"), 'Some(o) => { self.bump(); },')
        # Not a statement of its own: a `let`, an arm's value, a code reported twice.
        self.assertIsNone(port_replay.without('let d = Diag::new("E0001", sp);', "E0001"))
        self.assertIsNone(port_replay.without('match x { None => self.err("E0001", sp), }', "E0001"))
        self.assertIsNone(port_replay.without('a("E0001"); b("E0001");', "E0001"))

    def test_a_history_runs_its_steps_in_one_copy(self):
        tasks = [t for t in pair.load_tasks(os.path.join(HERE, "port")) if t.get("family") == "history"]
        self.assertGreaterEqual(len(tasks), 4)
        for t in tasks:
            names = [c["name"] for st in t["steps"] for c in st["cases"]]
            self.assertEqual(len(names), len(set(names)), t["id"])
            self.assertTrue(all(st["cases"] for st in t["steps"]), t["id"])

    def test_oracles_pass_and_weak_controls_fail(self):
        tasks = {t["id"]: t for t in pair.load_tasks(os.path.join(HERE, "port"))}
        self.assertGreaterEqual(len(tasks), 20)
        for family in ("callers", "diag"):
            t = next(t for t in tasks.values() if t["family"] == family)
            for arm in ("bmb", "rust"):
                self.assertTrue(pair.run_task(t, arm, "oracle")["success"], (t["id"], arm))
                self.assertFalse(pair.run_task(t, arm, "weak0", t["weak"][0][arm])["success"], (t["id"], arm))



class Report(unittest.TestCase):
    def rows(self, d, name, bmb_ok, changed):
        rows = []
        for arm, ok in (("bmb", bmb_ok), ("rust", True)):
            rows.append({"id": "r01-rename-f", "kind": "change", "arm": arm, "agent": "a", "docs": "none",
                         "success": ok, "tokens": 400 if arm == "bmb" else 100, "tool_calls": 1,
                         "changed": changed if arm == "bmb" else ["m::f", "m::g"], "stop": "stop",
                         "model_usage": {"input_tokens": 10, "output_tokens": 10}})
        path = os.path.join(d, name)
        with open(path, "w") as f:
            f.write("".join(json.dumps(r) + "\n" for r in rows))
        return path

    def test_diff_and_worked(self):
        import report
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "r01-rename-f.json"), "w") as f:
                json.dump({"id": "r01-rename-f", "scope": {"bmb": ["m::f", "m::g"], "rust": ["m::f", "m::g"]}}, f)
            a = self.rows(d, "one.jsonl", True, [])
            b = self.rows(d, "two.jsonl", True, ["m::f", "m::g"])
            text = report.diff([a, b])
            self.assertIn("| refactor | 1/1, 1/1 | 1/1, 1/1 | +0.0 |", text)
            self.assertIn("4.00", text)  # read tokens, BMB / Rust
            w = report.worked(d, [a, b])
            # Judged successful, but the first run's BMB session changed nothing.
            self.assertIn("| one | bmb | 1/1 | 0 | 1 | 0 | 0 |", w)
            self.assertIn("| two | bmb | 1/1 | 1 | 0 | 0 | 0 |", w)
            self.assertIn("| one | rust | 1/1 | 1 | 0 | 0 | 0 |", w)

if __name__ == "__main__":
    unittest.main()
