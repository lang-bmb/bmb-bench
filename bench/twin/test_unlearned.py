#!/usr/bin/env python3
"""Gate of the unlearned control arm (`unlearned.py`): the lexer, the two
mappings and their escape, the frozen table, prompt, task set and MANIFEST
are what `make` writes, every Rust file of the fixtures maps to the surface
and back to its own bytes, the compiler's output is mapped forward, and the
oracle and the weak controls of the tasks on `stk` and of two questions on
the compiler behave in the arm. The change tasks on the compiler take
minutes each (`pair.py check --tasks bench/twin/unlearned/tasks --arms
unlearned`) and are run when the set changes, not here."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pair  # noqa: E402
import unlearned  # noqa: E402

TASKS = os.path.join(unlearned.DIR, "tasks")


class Tokens(unittest.TestCase):
    def test_the_lexer_keeps_the_text_and_tells_the_kinds(self):
        src = ("fn f<'a>(x: &'a str) -> char { // fn in a comment\n"
               '    let s = "fn \\" let"; let r = br#"fn " let"#; let c = \'f\'; let q = b\'\\\'\';\n'
               "    /* let /* fn */ mut */ let n = 0xffu8 + 1_000usize + 1.5e3f64 + x.0; r#fn(1..2)\n}\n")
        toks = unlearned.lex(src)
        self.assertEqual("".join(t for _, t in toks), src)
        idents = [t for k, t in toks if k == "ident"]
        self.assertEqual(idents.count("fn"), 1)
        self.assertEqual(idents.count("let"), 5)
        self.assertIn("r#fn", idents)
        self.assertEqual([t for k, t in toks if k == "life"], ["'a", "'a"])
        self.assertEqual([t for k, t in toks if k == "num"], ["0xffu8", "1_000usize", "1.5e3f64", "0", "1", "2"])
        self.assertEqual(len([t for k, t in toks if k == "comment"]), 2)

    def test_the_mapping_is_by_token_and_goes_back(self):
        t = unlearned.Table()
        f = t.fwd
        src = ('pub fn f(v: &mut Vec<u8>) -> usize { let fn_name = "fn let {v:?} {{fn}}"; // let\n'
               "    let n = 0xffu8 as usize + 2u32 as usize; 'static: loop { break 'static; } v.len() + n }\n")
        s = t.to_surface(src)
        self.assertEqual(t.to_rust(s), src)
        self.assertIn(f"{f['pub']} {f['fn']} f(v: &{f['mut']} {f['Vec']}<{f['u8']}>) -> {f['usize']}", s)
        self.assertIn('fn_name = "fn let {v:?} {{fn}}"; // let', s)      # a string and a comment stay
        self.assertIn(f"0xff{f['u8']} {f['as']} {f['usize']} + 2{f['u32']}", s)   # a number's suffix
        self.assertIn(f"'{f['static']}: {f['loop']}", s)                  # a keyword as a lifetime
        # A name a format string takes from scope is an identifier.
        self.assertEqual(t.to_surface('println!("{len} {x:>3} {{len}}", x = 1)'),
                         f'{f["println"]}!("{{{f.get("len", "len")}}} {{x:>3}} {{{{len}}}}", x = 1)')

    def test_a_word_of_the_original_is_not_that_word_in_the_surface(self):
        t = unlearned.Table()
        # Rust written in the surface does not build as Rust: its words map back escaped, and forward again.
        self.assertEqual(t.to_rust("pub fn f() -> u8 { 0u8 }"), "pub__ fn__ f() -> u8__ { 0u8__ }")
        self.assertEqual(t.to_surface("pub__ fn__ f() -> u8__ { 0u8__ }"), "pub fn f() -> u8 { 0u8 }")
        self.assertEqual(t.to_surface(t.to_rust("fn__ x")), "fn__ x")
        for w in ("fn", "fn__", t.fwd["fn"], "plain", "plain__"):
            self.assertEqual(t.word(t.word(w, False), True), w)

    def test_the_table_is_a_bijection_of_non_words(self):
        t = unlearned.Table()
        self.assertEqual(len(t.back), len(t.fwd))
        self.assertGreaterEqual(set(t.fwd), set(unlearned.KEYWORDS) | set(unlearned.PRIMITIVES))
        for w in ("Vec", "Option", "Some", "None", "println", "derive", "std", "unwrap", "len", "new"):
            self.assertIn(w, t.fwd)
        # A library name that every fixture using it declares as an item of its own stays (`String` is
        # a variant of the compiler's own types).
        self.assertNotIn("String", t.fwd)
        src = " ".join(unlearned.sources().values())
        words = set(unlearned.re.findall(r"[A-Za-z_][A-Za-z0-9_]*", src))
        for w, s in t.fwd.items():
            self.assertNotIn(s, words)
            self.assertNotIn(s.lower(), {k.lower() for k in t.fwd})
            self.assertTrue(s[:2].lower() in unlearned.STARTS and s[0].lower() not in "abcdef", s)
            self.assertEqual((w[0].isupper(), w.isupper() and len(w) > 1), (s[0].isupper(), s.isupper()), (w, s))

    def test_what_the_survey_takes_for_the_library(self):
        src = ("use std::collections::HashMap;\n#[derive(Debug)]\nstruct Own { len: usize }\n"
               "impl Own { fn push(&self, last: u8) { let v: Vec<u8> = Vec::new(); v.iter().last(); self.push(last); "
               "println!(\"x\"); helper(v.len()) } }\nfn helper(n: usize) {}\n")
        words, _ = unlearned.library_names({"a/x.rs": src}, {"a": "a"})
        self.assertEqual({w for w in words if w not in unlearned.KEYWORDS and w not in unlearned.PRIMITIVES},
                         {"std", "collections", "HashMap", "derive", "Debug", "Vec", "new", "iter", "last", "println"})
        # `len` and `push` are the fixture's own items; `last` is only its local, and the library's method.
        self.assertEqual((words["std"], words["HashMap"], words["println"], words["derive"], words["last"]),
                         ("module", "type", "macro", "attribute", "function"))


class Output(unittest.TestCase):
    def test_a_sentence_is_mapped_in_backticks_and_for_telling_words(self):
        t = unlearned.Table()
        f = t.fwd
        got = t.message("expected `u8`, found `usize` in src/vm.rs: the trait `Clone` is for a struct or Vec, as a thread")
        self.assertEqual(got, f"expected `{f['u8']}`, found `{f['usize']}` in src/vm{t.ext}: the {f['trait']} "
                              f"`{f['Clone']}` is for a {f['struct']} or {f['Vec']}, as a thread")
        self.assertEqual(t.leaks(got), {})
        self.assertEqual(t.leaks("a struct of Vec, built by cargo; a thread writes"), {"struct": 1, "Vec": 1, "cargo": 1})

    def test_cargo_output_is_written_anew(self):
        t = unlearned.Table()
        f = t.fwd
        d = {"reason": "compiler-message", "message": {
            "level": "error", "message": "mismatched types", "code": {"code": "E0308"},
            "spans": [{"file_name": "src/vm.rs", "line_start": 3, "column_start": 17, "is_primary": True,
                       "label": "expected `u8`, found `usize`",
                       "text": [{"text": "    let n: u8 = st.len();"}]}],
            "children": [{"level": "help", "message": "consider using `as`", "spans": []},
                         {"level": "note", "message": "for more information, see rustc --explain E0308", "spans": []}]}}
        out = "\n".join(["   Compiling stk v0.1.0 (/tmp/x)", json.dumps(d),
                         "error: could not compile `stk` (bin \"stk\") due to 1 previous error",
                         "test vm::tests::fn_like ... FAILED", "note: run with `RUST_BACKTRACE=1` environment variable"])
        col = len(f"    {f['let']} n: {f['u8']} = ") + 1
        self.assertEqual(unlearned.render(out, t, "/x"),
                         f"error: mismatched types\n  --> src/vm{t.ext}:3:{col}\n"
                         f"   |     {f['let']} n: {f['u8']} = st.{f.get('len', 'len')}();\n"
                         f"   = expected `{f['u8']}`, found `{f['usize']}`\n   = help: consider using `{f['as']}`\n"
                         "test vm::tests::fn_like ... FAILED\n")


class Frozen(unittest.TestCase):
    def test_everything_is_what_make_writes(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "unlearned.py"), "make", "--check"], capture_output=True,
                           text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_file_of_the_fixtures_maps_back_to_its_bytes(self):
        problems, n = unlearned.roundtrip()
        self.assertEqual(problems, [])
        self.assertGreaterEqual(n["files"], 45)

    def test_the_set(self):
        tasks = pair.load_tasks(TASKS)
        self.assertEqual(len(tasks), 3 + sum(unlearned.PER_FAMILY.values()))
        self.assertEqual(sorted(t["id"] for t in tasks if t["fixture"] == "stk"),
                         ["c01-callers-is", "r01-rename-drop", "t01-neg"])
        frozen = {t["id"]: t for t in pair.load_tasks(os.path.join(HERE, unlearned.FROM))}
        table = unlearned.Table()
        for t in tasks:
            arms = sorted(k for k in t["weak"][0] if k != "fails" and ":" not in k)
            self.assertEqual(arms, ["bmb", "rust", "unlearned"], t["id"])
            if t["fixture"] == "stk":
                continue
            # A task of the frozen set with the arm's part added: the other arms' parts are the frozen ones.
            src = frozen[t["id"]]
            self.assertEqual(t["commit"], src["commit"])
            if "steps" not in t:
                self.assertEqual({k: v for k, v in t["oracle"].items() if k != "unlearned"},
                                 {k: v for k, v in src["oracle"].items() if ":port-rename-both" not in k})
                self.assertEqual({k: v for k, v in t["prompt"].items() if k != "unlearned"},
                                 src["prompt"] if isinstance(src["prompt"], dict) else {"bmb": src["prompt"],
                                                                                         "rust": src["prompt"]})
                # No word of the table in what the arm's solution writes or answers.
                for name, args in t["oracle"]["unlearned"]:
                    for k in ("old", "new", "content"):
                        if k in args:
                            left = {x for kind, x in unlearned.lex(args[k]) if kind == "ident" and x in table.fwd}
                            self.assertEqual(left, set(), (t["id"], k))
                    self.assertNotIn(name, ("cargo_build", "cargo_test"))

    def test_the_prompt_names_no_word_of_the_original(self):
        table = unlearned.Table()
        with open(unlearned.PROMPT, encoding="utf-8") as h:
            text = h.read()
        self.assertEqual(text, unlearned.prompt_text(table))
        tools = {t["name"] for t in unlearned.tool_list(table)}  # `test` is a tool's name there
        ticked = [x for x in text.split("`")[1::2] if x not in tools]
        for w in table.fwd:
            self.assertNotIn(w, ticked, w)
        self.assertNotIn("Rust", text)
        self.assertNotIn("cargo", text.lower())
        for w in unlearned.KEYWORDS:
            self.assertIn(f"`{table.fwd[w]}`", text)


class Arm(unittest.TestCase):
    def test_the_tools_show_and_take_the_surface_only(self):
        table = unlearned.Table()
        with tempfile.TemporaryDirectory() as d:
            task = next(t for t in pair.load_tasks(TASKS) if t["id"] == "t01-neg")
            root = pair.set_up(task, "unlearned", os.path.join(d, "code"), d)
            tools = pair.make_tools(task, "unlearned", root, os.path.join(d, "target"))
            self.assertEqual([t["name"] for t in tools.tools],
                             ["list_dir", "read_file", "grep", "write_file", "edit_file", "build", "test"])
            self.assertNotIn(".rs", json.dumps(tools.tools))
            self.assertNotIn("cargo", json.dumps(tools.tools).lower())
            self.assertEqual(tools.call("list_dir", {})[0], "src/\n")       # no manifest, no build script
            self.assertEqual(tools.call("list_dir", {"path": "src"})[0], "".join(f"{m}{table.ext}\n" for m in ("lex", "main", "vm")))
            self.assertEqual(tools.call("cargo_build", {}), ("unknown tool cargo_build", True))
            self.assertTrue(tools.call("write_file", {"path": "src/x.rs", "content": ""})[1])
            self.assertEqual(tools.call("grep", {"pattern": r"\b(fn|let|pub|mut|Vec|i64)\b"})[0], "(no matches)\n")
            # Rust written into the surface is not built as Rust; the message is in the agent's words.
            vm = "src/vm" + table.ext
            with open(os.path.join(root, vm), encoding="utf-8") as h:
                text = h.read()
            tools.call("write_file", {"path": vm, "content": text + "\npub fn extra() -> u8 { 0 }\n"})
            out, err = tools.call("build", {})
            self.assertTrue(err and "found `fn`" in out and "__" not in out, out)
            self.assertNotIn("rustc", out)
            self.assertNotIn(".rs", out)
            tools.call("write_file", {"path": vm, "content": text})
            self.assertEqual(tools.call("build", {}), ("exit status: 0\n", False))
            self.assertEqual(tools.facts(), {"unmapped": {"fn": 2, "pub": 1, "u8": 1}})   # the agent's own Rust, echoed
            self.assertEqual(pair.stamp(task, "unlearned")["table"], table.digest)
            # The crate behind the surface is the Rust arm's, byte for byte.
            rust = pair.materialize(task, "rust", os.path.join(d, "rust"))
            for f in ("lex.rs", "main.rs", "vm.rs"):
                with open(os.path.join(rust, "src", f), "rb") as a, open(os.path.join(unlearned.sync(root), "src", f), "rb") as b:
                    self.assertEqual(a.read(), b.read(), f)

    def test_oracles_pass_and_weak_controls_fail(self):
        only = ["c01-callers-is", "r01-rename-drop", "t01-neg"]
        only += sorted(t["id"] for t in pair.load_tasks(TASKS) if t.get("family") in ("callers", "state"))[1:3]
        r = subprocess.run([sys.executable, os.path.join(HERE, "pair.py"), "check", "--tasks", TASKS, "--arms", "unlearned",
                            "--only", *only], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-4000:])
        self.assertIn("ok: 5 tasks", r.stdout)


if __name__ == "__main__":
    unittest.main()
