#!/usr/bin/env python3
"""The unlearned control arm of the port twin (ADR-0154 decision 2).

A third arm: the Rust side with its keywords and the names of its standard
library renamed consistently to non-words, so that what a model pays for a
language it was not trained on is measured apart from what it pays for the
design of BMB. The agent sees and writes only the renamed surface; the
build maps the names back and runs cargo; what the compiler and the tests
print is mapped forward before the agent reads it.

    unlearned.py make [--check]       the table, the prompt, the task set and its
                                      MANIFEST (or: they are what `make` writes)
    unlearned.py roundtrip            every Rust file of the fixtures maps to the
                                      surface and back to its own bytes
    unlearned.py show FILE            a Rust file as the arm shows it
    unlearned.py leaks                the table's words left in the surface of the
                                      fixtures (comments and strings are not mapped)

What is renamed (`table.json`, frozen; `make` generates it from the seed):

    keyword     every strict and reserved keyword of the 2024 edition, and the
                weak ones (`union`, `macro_rules`)
    primitive   the primitive type names, also as the suffix of a number
                (`1u32`) and in a lifetime position (`'static` is a keyword)
    fragment    the fragment specifiers of `macro_rules` (`expr`, `tt`, ..)
    library     every identifier the fixtures use and never declare: it comes
                from the language or its library. By where it stands: `macro`
                (before `!`), `attribute` (only inside `#[..]`), `type`
                (capitalised: types, traits, variants, constants), `module`
                (lower case, before `::`), `function` (the rest: functions,
                methods, fields). A fixture's local variable of that
                name is renamed with it

What is not renamed, and why:

    the fixtures' own names   they are the program, the same in the Rust arm
    a library name that every fixture using it also declares as an item
    (`new`, `len`, `fmt`: the methods of its own types and of the traits
    it implements)            a token has no type: the word cannot be split
                              between the library's use and the crate's
    words inside string literals
                              they are the program's output, compared byte by
                              byte. The one exception is a name in braces
                              (`{name}`, `{name:?}`): a format string takes it
                              from scope, so it is an identifier and maps as
                              one (a string that has such braces as data maps
                              with them, and back to its bytes)
    comments                  prose; the measured documentation condition of
                              the port twin has none
    punctuation and syntax    `->`, `::`, `&mut`'s `&`, `#[..]`, `'a`, `?`:
                              the arm renames words, it does not hide a grammar
    file names                a module's file is the module's name; the
                              extension `.rs` is replaced

Renaming is by token (a lexer for Rust's tokens: nested block comments,
strings, byte, C and raw strings, characters against lifetimes, raw
identifiers, number suffixes), never by text search. A word of the original
language written in the surface is not that language's word there: it maps
back to itself with `__` appended (an ordinary, unknown name), so the agent
cannot write Rust and have it built. The mapping is a bijection on
identifiers, and `roundtrip` holds it on every file of the fixtures.

Standard library only.
"""
import hashlib
import json
import os
import random
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pair  # noqa: E402

DIR = os.path.join(HERE, "unlearned")
TABLE = os.path.join(DIR, "table.json")
PROMPT = os.path.join(HERE, "prompt-unlearned.md")
SEED = 20261128
# The task set: the fixture `stk` whole, and from `gate-d` this many per
# family by a seeded shuffle of the family's tasks.
STK = os.path.join(HERE, "tasks")
FROM = "gate-d"
PER_FAMILY = {"callers": 2, "impact": 2, "diag": 2, "state": 2, "rename": 2, "swap": 2, "replay": 2, "history": 1}

# Each keyword with what a reference of the language says of it; the
# prompt gives these lines under the surface word, never the Rust word.
KEYWORDS = {
    "as": "converts a value to another type; also renames an import",
    "async": "reserved", "await": "reserved",
    "break": "leaves the enclosing loop, optionally with a value",
    "const": "declares a constant computed when the program is built",
    "continue": "goes on with the next round of the enclosing loop",
    "crate": "the root of the program's own modules, in a path",
    "dyn": "a value of any type that has the given interface, behind a reference",
    "else": "the other branch of a condition",
    "enum": "declares a type that is one of several named variants",
    "extern": "declares something defined outside the program",
    "false": "the boolean value false",
    "fn": "declares a function",
    "for": "a loop over the items of a sequence; also `X for T` when an interface is given to a type",
    "if": "a condition",
    "impl": "the block of functions of a type, or of an interface given to a type",
    "in": "between the pattern and the sequence of an item loop",
    "let": "declares a local variable",
    "loop": "a loop without a condition",
    "match": "chooses a branch by the shape of a value; every shape must be covered",
    "mod": "declares a module (a file of the same name, or a block)",
    "move": "makes a function value take what it uses by value",
    "mut": "marks a variable or a reference as changeable",
    "pub": "makes a declaration visible outside its module",
    "ref": "binds by reference in a pattern",
    "return": "leaves the function with a value",
    "self": "the value a method is called on; also the present module, in a path",
    "Self": "the type the enclosing block is about",
    "static": "declares a value that lives for the whole run; as a lifetime, that length",
    "struct": "declares a type with named or numbered fields",
    "super": "the parent module, in a path",
    "trait": "declares an interface: functions a type may be given",
    "true": "the boolean value true",
    "type": "gives a type another name",
    "unsafe": "marks code the compiler does not check for memory safety",
    "use": "brings a name of another module into scope",
    "where": "starts the list of conditions on type parameters",
    "while": "a loop with a condition",
    "abstract": "reserved", "become": "reserved", "box": "reserved", "do": "reserved", "final": "reserved",
    "gen": "reserved", "macro": "reserved", "override": "reserved", "priv": "reserved", "try": "reserved",
    "typeof": "reserved", "unsized": "reserved", "virtual": "reserved", "yield": "reserved",
    "union": "declares a type whose fields share one place",
    "macro_rules": "declares a macro by patterns",
}
PRIMITIVES = {
    "bool": "true or false", "char": "one Unicode scalar value", "str": "text (UTF-8), always behind a reference",
    "u8": "unsigned integer, 8 bits", "u16": "unsigned integer, 16 bits", "u32": "unsigned integer, 32 bits",
    "u64": "unsigned integer, 64 bits", "u128": "unsigned integer, 128 bits",
    "usize": "unsigned integer of the machine's address size (indexes and lengths)",
    "i8": "signed integer, 8 bits", "i16": "signed integer, 16 bits", "i32": "signed integer, 32 bits",
    "i64": "signed integer, 64 bits", "i128": "signed integer, 128 bits",
    "isize": "signed integer of the machine's address size",
    "f32": "floating point number, 32 bits", "f64": "floating point number, 64 bits",
}
FRAGMENTS = ["block", "expr", "ident", "item", "lifetime", "literal", "meta", "pat", "path", "stmt", "tt", "ty", "vis"]
ITEM_WORDS = {"fn", "struct", "enum", "union", "trait", "type", "mod", "const", "static"}
# Keywords that are plain English in a compiler's sentence: outside
# backticks they are left as they are (inside backticks everything maps).
ENGLISH = {"as", "in", "for", "if", "use", "type", "where", "while", "let", "move", "do", "try", "final", "box",
           "static", "match", "loop", "return", "break", "self", "true", "false", "super", "become", "yield", "macro",
           "override", "virtual", "abstract", "continue", "else", "const", "ref", "gen", "union"}


# ---------- tokens ----------

TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<line>//[^\n]*)
  | (?P<block>/\*)
  | (?P<raw>(?:br|cr|r)(?P<hashes>\#*)")
  | (?P<rawid>r\#[A-Za-z_][A-Za-z0-9_]*)
  | (?P<str>(?:b|c)?")
  | (?P<char>b?'(?:\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|.)|[^\\'\n])')
  | (?P<life>'[A-Za-z_][A-Za-z0-9_]*)
  | (?P<num>(?:0[xob][0-9a-fA-F_]+|[0-9][0-9_]*(?:\.[0-9][0-9_]*)?(?:[eE][+-]?[0-9_]+)?)[A-Za-z0-9_]*)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<punct>.)
""", re.X | re.S)


def lex(text):
    """[(kind, text)] of Rust source: `ws`, `comment`, `str` (any string or
    character literal), `life`, `num`, `ident` (a raw identifier too) and
    `punct` (one character). Joined, the texts are `text`."""
    out, i, n = [], 0, len(text)
    while i < n:
        m = TOKEN.match(text, i)
        kind, j = m.lastgroup, m.end()
        if kind == "block":
            depth = 1
            while j < n and depth:
                if text.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            kind = "comment"
        elif kind == "line":
            kind = "comment"
        elif kind == "raw":
            end = text.find('"' + m.group("hashes"), j)
            j = n if end < 0 else end + 1 + len(m.group("hashes"))
            kind = "str"
        elif kind == "str":
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j = min(n, j + 1)
        elif kind == "char":
            kind = "str"
        elif kind == "rawid":
            kind = "ident"
        out.append((kind, text[i:j]))
        i = j
    return out


# A number and its suffix. After hexadecimal digits a suffix starts with a
# letter that is none (Rust's integer suffixes do, and so does every
# non-word, `ONSETS`); after a decimal number with any letter.
NUM = re.compile(r"(0x[0-9a-fA-F_]*?)([G-Zg-z][A-Za-z0-9_]*)?|"
                 r"(0[ob][0-9_]*|[0-9][0-9_]*(?:\.[0-9][0-9_]*)?(?:[eE][+-]?[0-9][0-9_]*)?)([A-Za-z][A-Za-z0-9_]*)?")


FORMAT = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)(?=[:}])")


class Table:
    """The frozen table and the two mappings."""

    def __init__(self, doc=None):
        if doc is None:
            with open(TABLE, encoding="utf-8") as h:
                doc = json.load(h)
        self.doc = doc
        self.fwd = {w: e["to"] for w, e in doc["words"].items()}
        self.back = {s: w for w, s in self.fwd.items()}
        self.ext = doc["extension"]
        self.digest = "sha256:" + hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()

    def _stem(self, w):
        while w.endswith("__"):
            w = w[:-2]
        return w

    def word(self, w, forward):
        """One identifier mapped. A word of the other side's vocabulary is
        escaped (`fn` written in the surface is `fn__` in Rust, and back)."""
        if forward:
            if w in self.fwd:
                return self.fwd[w]
            return w[:-2] if w.endswith("__") and self._stem(w) in self.fwd else w
        if w in self.back:
            return self.back[w]
        return w + "__" if self._stem(w) in self.fwd else w

    def tokens(self, text, forward):
        out = []
        for kind, t in lex(text):
            if kind == "ident":
                t = self.word(t, forward)
            elif kind == "life":
                t = "'" + self.word(t[1:], forward)
            elif kind == "num":
                m = NUM.fullmatch(t)
                digits, suffix = (m.group(1), m.group(2)) if m and m.group(1) is not None else (
                    m.group(3), m.group(4)) if m else (t, None)
                if suffix:
                    t = digits + self.word(suffix, forward)
            elif kind == "str" and "{" in t and not t.startswith(("'", "b'")):
                # A name a format string takes from scope (`{name}`, `{name:?}`) is an identifier.
                t = FORMAT.sub(lambda m: "{" + self.word(m.group(1), forward), t)
            out.append(t)
        return "".join(out)

    def to_surface(self, text):
        return self.tokens(text, True)

    def to_rust(self, text):
        return self.tokens(text, False)

    def path(self, p, forward=True):
        a, b = (".rs", self.ext) if forward else (self.ext, ".rs")
        return p[:-len(a)] + b if p.endswith(a) else p

    def message(self, text):
        """A sentence of the compiler or the test runner for the agent: file
        names get the surface's extension, what stands in backticks is
        mapped as code, and outside them the table's words that are not
        plain English (`telling`)."""
        text = re.sub(r"\b([\w./-]+)\.rs\b", lambda m: m.group(1) + self.ext, text)
        parts = text.split("`")
        for k, part in enumerate(parts):
            if k % 2 and k < len(parts) - 1:
                parts[k] = self.to_surface(part)
            else:
                parts[k] = re.sub(r"[A-Za-z_][A-Za-z0-9_]*",
                                  lambda m: self.word(m.group(0), True) if self.telling(m.group(0)) else m.group(0), part)
        return "`".join(parts)

    def telling(self, w):
        """Whether a word of a sentence, outside backticks, is the
        original language's and not plain English: a keyword or primitive
        type that is no English word, or a library name that is
        capitalised or has an underscore (`Vec`, `to_string`; `thread`,
        `write` and `panic` read as English and stay)."""
        e = self.doc["words"].get(w)
        if e is None:
            return False
        if e["class"] in ("keyword", "primitive"):
            return w not in ENGLISH
        return w != w.lower() or "_" in w

    def leaks(self, text):
        """{word: count} of what is left of the original vocabulary in a
        text the agent reads (plain English words apart), and of the names
        of the tool chain."""
        out = {}
        for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
            if self.telling(w) or w.lower() in ("rust", "rustc", "cargo", "rustup"):
                out[w] = out.get(w, 0) + 1
        return out


# ---------- the table, by rule ----------

def sources():
    """{name: text} of every Rust file of the fixtures the arm is run on:
    `stk` as committed, and the compiler at the commit of the full-size
    fixture."""
    out = {}
    stk = os.path.join(HERE, "fixtures", "stk", "rust", "src")
    for f in sorted(os.listdir(stk)):
        if f.endswith(".rs"):
            with open(os.path.join(stk, f), encoding="utf-8") as h:
                out["stk/src/" + f] = h.read()
    import index
    with open(os.path.join(HERE, "fixtures", "port-full", "fixture.json"), encoding="utf-8") as h:
        commit = json.load(h)["commit"]
    src = os.path.join(pair.commit_tree(commit, ["compiler"]), "compiler", "src")
    for f in index.rust_files(src):
        with open(os.path.join(src, f), encoding="utf-8") as h:
            out["port-full/src/" + f] = h.read()
    return out


def survey(text, items, places):
    """What one file says of its identifiers. `items` gets the names it
    declares as part of the program: after an item keyword, the fields
    and variants in the body of a `struct`, `enum` or `union`, type
    parameters, a macro's name and its parameters. (A local binding is no
    such declaration: a variable called `last` does not make `.last()` the
    program's.) `places` {word: {where it stands}}: `macro` (before `!`),
    `attribute` and `code` (inside `#[..]` or not), `head` (before `::`),
    `path` (after `::`), `member` (after `.`)."""
    toks = [(k, t) for k, t in lex(text) if k not in ("ws", "comment")]
    attr = 0        # bracket depth inside `#[..]` (-1: after the `#`)
    bodies = []     # (brace depth, bracket depth, keyword) of open struct, enum and union bodies
    depth = round_ = 0
    pending = None
    n = len(toks)
    for i, (k, t) in enumerate(toks):
        prev = toks[i - 1][1] if i else ""
        nxt = toks[i + 1][1] if i + 1 < n else ""
        nxt2 = toks[i + 2][1] if i + 2 < n else ""
        if t == "#" and nxt in ("[", "!"):
            attr = -1
        elif t == "[" and attr:
            attr = 1 if attr == -1 else attr + 1
        elif t == "]" and attr > 0:
            attr -= 1
        elif t == "{":
            depth += 1
            if pending:
                bodies.append((depth, round_, pending))
                pending = None
        elif t == "}":
            if bodies and bodies[-1][0] == depth:
                bodies.pop()
            depth -= 1
        elif t == ";":
            pending = None
        elif k == "punct" and t in "([":
            round_ += 1
        elif k == "punct" and t in ")]":
            round_ -= 1
        if k != "ident":
            continue
        where = places.setdefault(t, set())
        where.add("attribute" if attr > 0 else "code")
        if nxt == "!" and nxt2 != "=":
            where.add("macro")
        if nxt == ":" and nxt2 == ":":
            where.add("head")
        if prev == ":" and i > 1 and toks[i - 2][1] == ":":
            where.add("path")
        if prev == "." and (i < 2 or toks[i - 2][1] != "."):
            where.add("member")
        if attr > 0:
            continue
        if prev in ITEM_WORDS or (prev == "!" and i > 1 and toks[i - 2][1] == "macro_rules") or prev == "$":
            items.add(t)
            pending = pending or (prev if prev in ("struct", "enum", "union") else None)
        elif bodies and round_ == bodies[-1][1] and (
                (nxt == ":" and nxt2 != ":")       # a named field (of a variant too)
                or (bodies[-1][2] == "enum" and depth == bodies[-1][0] and prev in ("{", ",", "]"))):  # a variant
            items.add(t)
        if t in ("fn", "impl", "struct", "enum", "trait", "type") or prev in ("fn", "struct", "enum", "trait", "type"):
            # Type parameters: `impl<T, U: X>`, `fn f<T>`.
            j = i + 1
            if j < n and toks[j][1] == "<":
                d = 0
                while j < n:
                    x = toks[j][1]
                    d += x == "<"
                    d -= x == ">" and toks[j - 1][1] != "-"
                    if d == 0:
                        break
                    if d == 1 and toks[j][0] == "ident" and toks[j - 1][1] in ("<", ","):
                        items.add(x)
                    j += 1


# Every non-word starts with two consonants no English word starts with
# (so none is a word), and with none of the letters a to f (a number's
# suffix is told from hexadecimal digits by its first letter).
STARTS = ["vl", "zr", "kv", "zv", "zl", "gv", "tl", "sv"]
MIDDLES = ["k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "lk", "lv", "nz", "rk", "rv", "sk", "zn"]
VOWELS = ["a", "e", "i", "o", "u"]
CODAS = ["k", "l", "m", "n", "r", "s", "t", "x", "z"]


def non_word(rng, like):
    """A pronounceable non-word of about the length of `like`, in its
    letter case."""
    w = rng.choice(STARTS) + rng.choice(VOWELS)
    for _ in range(max(0, min(2, round(len(like) / 3) - 1))):
        w += rng.choice(MIDDLES) + rng.choice(VOWELS)
    if len(w) < 5 or rng.random() < 0.5:
        w += rng.choice(CODAS)
    if like.isupper() and len(like) > 1:
        return w.upper()
    return w.capitalize() if like[0].isupper() else w


def packages():
    """{fixture: the name of its package}: a path that starts with it is
    the program's own."""
    out = {}
    with open(os.path.join(HERE, "fixtures", "port-full", "fixture.json"), encoding="utf-8") as h:
        commit = json.load(h)["commit"]
    for fx, f in (("stk", os.path.join(HERE, "fixtures", "stk", "rust", "Cargo.toml")),
                  ("port-full", os.path.join(pair.commit_tree(commit, ["compiler"]), "compiler", "Cargo.toml"))):
        with open(f, encoding="utf-8") as h:
            out[fx] = re.search(r'^name = "([^"]+)"', h.read(), re.M).group(1)
    return out


def library_names(srcs, pkgs):
    """{word: class} of the names the fixtures take from outside, and
    {word: reason} of those left as they are. A word is the library's when,
    in one fixture, it stands where only an outside name stands (before
    `!`, inside an attribute, in a path, after `.`) or is capitalised, and
    that fixture declares no item of that name. It is then renamed
    everywhere, also where another fixture's own item has the name (a
    token has no type)."""
    words, kept = {}, {}
    for fx in sorted({name.split("/")[0] for name in srcs}):
        items, places = set(), {}
        for name, text in srcs.items():
            if name.startswith(fx + "/"):
                survey(text, items, places)
        for w, where in places.items():
            if w in items or w in KEYWORDS or w in PRIMITIVES or w in ("_", "main", pkgs.get(fx)):
                continue
            if not (where & {"macro", "attribute", "head", "path", "member"} or w[0].isupper()):
                continue  # a local binding
            cls = ("macro" if "macro" in where else
                   "attribute" if "code" not in where else "type" if w[0].isupper() else
                   "module" if "head" in where else "function")
            if words.get(w, cls) != cls:
                cls = min(cls, words[w], key=["macro", "type", "module", "function", "attribute"].index)
            words[w] = cls
    return words, kept


def make_table(srcs=None, pkgs=None):
    srcs = sources() if srcs is None else srcs
    words, kept = library_names(srcs, packages() if pkgs is None else pkgs)
    used = {x for text in srcs.values() for k, x in lex(text) if k == "ident"}
    for text in srcs.values():
        # The kind of a macro's parameter: `$name:kind`.
        for m in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*\s*:\s*([a-z]+)", text):
            if m.group(1) in FRAGMENTS:
                words.setdefault(m.group(1), "fragment")
    words.update({w: "keyword" for w in KEYWORDS})
    words.update({w: "primitive" for w in PRIMITIVES})
    # The non-words: none is a word of the fixtures, of the language, or
    # another non-word (letter case apart).
    taken = {x.lower() for text in srcs.values() for x in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)}
    taken |= {w.lower() for w in words}
    for w in used:
        if w.endswith("__") and w.rstrip("_") in words:
            raise SystemExit(f"the fixtures have the identifier {w}: the escape of {w.rstrip('_')}")
    rng = random.Random(SEED)
    out = {}
    for w in sorted(words):
        while True:
            s = non_word(rng, w)
            if s.lower() not in taken:
                break
        taken.add(s.lower())
        out[w] = {"to": s, "class": words[w]}
    while True:
        ext = "." + non_word(rng, "rs")[:3]
        if ext[1:] not in taken:
            break
    return {"about": "The renaming of the unlearned control arm (ADR-0154 decision 2): Rust word -> surface word, "
                     "with the class of the word. Generated by `unlearned.py make` from the seed and the fixtures; "
                     "do not edit.",
            "seed": SEED, "extension": ext, "words": out, "kept": kept}


# ---------- the prompt ----------

def prompt_text(table):
    """What the agent is told: the tools, and the language as a reference
    would give it: every keyword and primitive type with its meaning, the
    library's names by kind. It is not told that the language is another
    one renamed."""
    by = {}
    for w, e in table.doc["words"].items():
        by.setdefault(e["class"], []).append((e["to"], w))
    ext = table.ext
    lines = [
        "You are working on a program written in a language you have not seen (source files end in",
        f"`{ext}`). You can only reach the code through the tools below; there is no shell and you cannot",
        "run the program itself.",
        "",
        "## Tools",
        "- `list_dir`, `read_file` (a file or a line range; lines are numbered), `grep`",
        "  (Python `re` syntax, optional context lines; one path, several, or the whole",
        "  project).",
        f"- `write_file` (a whole `{ext}` file under `src/` or `tests/`), `edit_file`",
        "  (replace one exact occurrence of a text).",
        f"- `build`, `test` (you may add tests under `tests/` or in modules marked",
        f"  `#[{table.fwd.get('cfg', 'cfg')}({table.fwd.get('test', 'test')})]`).",
        "- `answer` (questions only): the full paths (`module::name`, the module is the",
        "  file under `src/`) of the definitions asked for.",
        "",
        "## How to work",
        "Read only what you need. You have at most 60 tool calls. For a question, call",
        "`answer` once with every definition asked for and nothing else. For a change,",
        "change only what the task needs, keep the program building and stop calling",
        "tools when you are done. The change is judged afterwards on inputs you do not",
        "see: the program's output bytes, the build and its tests, and whether code",
        "outside the task changed.",
        "",
        "## The language",
        "Statically typed, compiled, with ownership and borrowing checked by the compiler:",
        "a value has one owner, `&` borrows it for reading and `&` followed by the",
        f"keyword `{table.fwd['mut']}` for changing. Blocks are `{{ }}`, a path is `a::b`, a type",
        "follows its name after `:`, a function's result type follows `->`, a block's last",
        "expression without `;` is its value, `'a` names a lifetime, `#[..]` is an",
        "attribute of the next item, a name followed by `!` is a macro call, and `?`",
        "after an expression returns its error to the caller.",
        "",
        "Keywords:",
        "",
    ]
    for s, w in sorted(by["keyword"]):
        if KEYWORDS[w] != "reserved":
            lines.append(f"- `{s}`: {KEYWORDS[w]}")
    reserved = ", ".join(f"`{s}`" for s, w in sorted(by["keyword"]) if KEYWORDS[w] == "reserved")
    lines += ["", f"Reserved, without a use: {reserved}.", "", "Primitive types (also the suffix of a number, as in "
              f"`1{table.fwd['u32']}`):", ""]
    lines += [f"- `{s}`: {PRIMITIVES[w]}" for s, w in sorted(by["primitive"])]
    titles = [("type", "Types, interfaces, variants and constants of the standard library"),
              ("module", "Its modules"), ("function", "Its functions, methods and fields"), ("macro", "Its macros"),
              ("attribute", "Words of attributes"), ("fragment", "Kinds of a macro's parameters")]
    lines += ["", "The names below are the standard library's and the language's own, by kind. The project",
              "does not define them; what each does is to be read from how the code uses it.", ""]
    for cls, title in titles:
        if by.get(cls):
            lines.append(f"{title}: " + ", ".join(f"`{s}`" for s, _ in sorted(by[cls])) + ".")
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------- the arm's copy of the code ----------

def base_of(root):
    """The Rust crate behind the surface at `root` (`WORK/code`): beside it,
    where the agent's tools do not reach."""
    return os.path.join(os.path.dirname(os.path.realpath(root)), "base", "crate")


def source_files(crate, ext):
    out = []
    for top in ("src", "tests"):
        for d, dirs, files in os.walk(os.path.join(crate, top)):
            dirs.sort()
            out += [os.path.relpath(os.path.join(d, f), crate) for f in sorted(files) if f.endswith(ext)]
    return out


def to_surface(base, root, table=None):
    """The surface of the Rust crate `base`, written to `root`: every `.rs`
    file under `src/` and `tests/` renamed, and nothing else (the manifest
    and the build script are the build's, not the language's)."""
    table = table or Table()
    for rel in source_files(base, ".rs"):
        with open(os.path.join(base, rel), encoding="utf-8") as h:
            text = h.read()
        dest = os.path.join(root, table.path(rel))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as h:
            h.write(table.to_surface(text))
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    return root


def sync(root, table=None):
    """The crate behind the surface, brought to what the surface says: each
    surface file mapped back (written only when it changed, so cargo builds
    what changed), a Rust file whose surface file went removed. Returns
    the crate."""
    table = table or Table()
    base = base_of(root)
    want = {}
    for rel in source_files(root, table.ext):
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as h:
            want[table.path(rel, forward=False)] = table.to_rust(h.read())
    for rel in source_files(base, ".rs"):
        if rel not in want:
            os.remove(os.path.join(base, rel))
    for rel, text in want.items():
        p = os.path.join(base, rel)
        old = None
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="replace") as h:
                old = h.read()
        if old != text:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as h:
                h.write(text)
    return base


def tool_list(table):
    """The Rust arm's tools under the arm's names: the same seven, with
    `build` and `test` for the two that name the build tool."""
    out = []
    for t in pair.RUST_TOOLS:
        t = json.loads(json.dumps(t).replace(".rs", table.ext).replace("crate", "project"))
        if t["name"] == "cargo_build":
            t.update(name="build", description="Build the program and its tests. Returns the exit status and the "
                                               "compiler's messages.")
        elif t["name"] == "cargo_test":
            t.update(name="test", description="Build and run the tests, optionally only those whose name contains "
                                              "FILTER. Returns the exit status and the output.")
        out.append(t)
    return out


class Tools(pair.RustTools):
    """The Rust arm's tools on the surface. Reading, searching and writing
    work on the surface files as they are; `build` and `test` map the
    surface back, run cargo on the crate behind it and map what it says
    forward."""

    def __init__(self, root, target_dir):
        super().__init__(root, target_dir)
        self.table = Table()
        self.tools = tool_list(self.table)
        self.ext = self.table.ext
        self.unmapped = {}

    def call(self, name, args):
        if name in ("cargo_build", "cargo_test", "rename"):
            return f"unknown tool {name}", True
        return super().call(name, args)

    def _path(self, p, write=False):
        full = super()._path(p)
        rel = os.path.relpath(full, self.root).split(os.sep)
        if write and not (rel[0] in ("src", "tests") and full.endswith(self.ext)):
            raise ValueError(f"only {self.ext} files under src/ or tests/ may be written")
        return full

    def facts(self):
        return {"unmapped": self.unmapped}

    def _run(self, args):
        base = sync(self.root, self.table)
        code, out = pair.cargo(base, self.target_dir, args + ["--message-format=json"])
        text = render(out, self.table, base)
        for w, k in self.table.leaks(text).items():
            self.unmapped[w] = self.unmapped.get(w, 0) + k
        if len(text) > pair.OUTPUT_LIMIT:
            text = text[:pair.OUTPUT_LIMIT] + f"\n... ({len(text) - pair.OUTPUT_LIMIT} more characters)"
        return f"exit status: {code}\n{text}", code != 0

    def t_build(self):
        return self._run(["build", "--all-targets"])

    def t_test(self, filter=None):  # noqa: A002 (the tool's argument name)
        return self._run(["test"] + ([filter] if isinstance(filter, str) and filter else []))


CARGO_LINE = re.compile(r"\s*(warning: `[^`]*` \(.*\) generated|Compiling|Finished|Running|Doc-tests|Blocking|Fresh|Dirty|Checking|warning: unused manifest|"
                        r"error: could not compile|error: test failed|error: \d+ targets? failed|note: run with|"
                        r"Caused by:|process didn't exit successfully|warning: build failed)")


def render(out, table, base):
    """What cargo printed (`--message-format=json`: the compiler's
    diagnostics as JSON lines, the test runner's lines as text, cargo's own
    lines), as the agent reads it: each diagnostic written anew from its
    parts (its sentence, the place, the surface line, the labels, the
    notes), the test runner's lines mapped, cargo's own dropped."""
    lines, seen = [], set()
    for ln in out.split("\n"):
        if ln.startswith('{"reason"'):
            try:
                msg = json.loads(ln)
            except ValueError:
                continue
            d = msg.get("message")
            if msg.get("reason") != "compiler-message" or not d or d.get("level") not in ("error", "warning"):
                continue
            text = diagnostic(d, table)
            if text not in seen:  # the same message of two targets (the program and its tests)
                seen.add(text)
                lines.append(text)
        elif ln.strip() and not CARGO_LINE.match(ln) and not re.search(r"rustc|cargo|RUST_|rust-lang|\.cargo", ln):
            m = re.fullmatch(r"test (\S+)( - should panic)? \.\.\. (\w+)", ln)
            if m:
                lines.append(f"test {table.to_surface(m.group(1))}{m.group(2) or ''} ... {m.group(3)}")
            elif re.match(r"---- (\S+) stdout ----$", ln):
                lines.append(f"---- {table.to_surface(ln.split()[1])} stdout ----")
            elif re.match(r"    [\w:]+$", ln) or re.match(r"(test result|running \d+ tests?|failures:)", ln):
                lines.append(ln if ln.startswith(("test result", "running", "failures")) else "    " + table.to_surface(ln.strip()))
            else:
                lines.append(table.message(ln))
    return "\n".join(lines) + ("\n" if lines else "")


def diagnostic(d, table):
    head = re.sub(r"rustc|cargo", "the compiler", d["message"])
    out = [f"{d['level']}: {table.message(head)}"]
    for sp in d.get("spans", []):
        if not sp.get("is_primary") and not sp.get("label"):
            continue
        if os.path.isabs(sp["file_name"]) or not sp["file_name"].startswith(("src/", "tests/")):
            continue  # a place in the library's own sources
        src = sp["text"][0]["text"] if sp.get("text") else ""
        col = len(table.to_surface(src[:max(0, sp["column_start"] - 1)])) + 1
        out.append(f"  --> {table.path(sp['file_name'])}:{sp['line_start']}:{col}")
        if src:
            out.append(f"   | {table.to_surface(src).rstrip()}")
        if sp.get("label"):
            out.append(f"   = {table.message(sp['label'])}")
    for c in d.get("children", []):
        if re.search(r"rustc|cargo|rust-lang|https?://|#\[warn|#\[deny|`-[A-Z-]", c["message"]):
            continue
        text = f"   = {c['level']}: {table.message(c['message'])}"
        fix = [sp["suggested_replacement"] for sp in c.get("spans", []) if sp.get("suggested_replacement")]
        if fix:
            text += ": " + ", ".join(f"`{table.to_surface(x)}`" for x in fix)
        out.append(text)
    return "\n".join(out)


# ---------- the task set ----------

def map_calls(calls, table):
    """Scripted calls of the Rust arm as the arm makes them: paths, texts
    and answers in the surface, `build` and `test` for the cargo tools."""
    def words(s):
        return re.sub(r"[A-Za-z_][A-Za-z0-9_]*", lambda m: table.word(m.group(0), True), s)

    out = []
    for name, args in calls:
        a = dict(args)
        if "path" in a:
            a["path"] = [table.path(p) for p in a["path"]] if isinstance(a["path"], list) else table.path(a["path"])
        for k in ("content", "old", "new"):
            if k in a:
                a[k] = table.to_surface(a[k])
        if "pattern" in a:
            a["pattern"] = words(a["pattern"])
        if "filter" in a:
            a["filter"] = words(a["filter"])
        if name == "answer":
            a["defs"] = [table.to_surface(x) for x in a["defs"]]
        out.append([{"cargo_build": "build", "cargo_test": "test"}.get(name, name), a])
    return out


def map_prompt(text, table):
    parts = text.split("`")
    return "`".join(table.to_surface(p) if k % 2 else p for k, p in enumerate(parts))


def with_arm(task, table):
    """The task with the arm's part: its statement, reference and weak
    solutions and, for a question, the answer, all from the Rust arm's by
    the table. Nothing is written by hand."""
    t = json.loads(json.dumps(task))
    # A statement that names definitions in backticks is mapped. One that
    # states behaviour for hidden cases (a replay, a history, a new
    # command) quotes inputs of the program, not code: the same text in
    # every arm.
    mapped = "cases" not in t and "steps" not in t

    def prompts(p):
        p = p if isinstance(p, dict) else {"bmb": p, "rust": p}
        return {**p, "unlearned": map_prompt(p["rust"], table) if mapped else p["rust"]}

    def solutions(s):
        if "steps" in t:
            return {**s, "unlearned": [map_calls(c, table) for c in s["rust"]]}
        return {**s, "unlearned": map_calls(s["rust"], table)}

    if "steps" in t:
        for st in t["steps"]:
            st["prompt"] = prompts(st["prompt"])
            st["oracle"] = {**st["oracle"], "unlearned": map_calls(st["oracle"]["rust"], table)}
    else:
        t["prompt"] = prompts(t["prompt"])
        t["oracle"] = solutions(t["oracle"])
    t["weak"] = [solutions(w) for w in t["weak"]]
    if "truth" in t:
        truth = t["truth"] if isinstance(t["truth"], dict) else {"bmb": t["truth"], "rust": t["truth"]}
        t["truth"] = {**truth, "unlearned": [table.to_surface(x) for x in truth["rust"]]}
    return t


def picked():
    """[(directory, file)] of the set: the tasks of `stk`, and of each
    family of `gate-d` the first of a seeded shuffle."""
    out = [(STK, f) for f in sorted(os.listdir(STK)) if f.endswith(".json")]
    src = os.path.join(HERE, FROM)
    by = {}
    for f in sorted(os.listdir(src)):
        if f.endswith(".json"):
            with open(os.path.join(src, f), encoding="utf-8") as h:
                by.setdefault(json.load(h)["family"], []).append(f)
    for family, k in PER_FAMILY.items():
        pool = list(by[family])
        random.Random(f"{SEED}:{family}").shuffle(pool)
        out += [(src, f) for f in sorted(pool[:k])]
    return out


def make():
    """{path: text} of everything `make` writes."""
    doc = make_table()
    table = Table(doc)
    out = {TABLE: json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n", PROMPT: prompt_text(table)}
    for d, f in picked():
        with open(os.path.join(d, f), encoding="utf-8") as h:
            task = json.load(h)
        out[os.path.join(DIR, "tasks", f)] = json.dumps(with_arm(task, table), indent=1, ensure_ascii=False) + "\n"
    return out


def manifest(files):
    lines = []
    for p in sorted(files, key=lambda p: (not p.startswith(DIR), p)) + [
            os.path.join(HERE, "fixtures", "port-full", "fixture.json"), os.path.join(HERE, "prompt-bmb.md"),
            os.path.join(HERE, "prompt-rust.md")]:
        data = files[p].encode() if p in files else open(p, "rb").read()
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {os.path.relpath(p, DIR)}\n")
    return "".join(lines)


def roundtrip(table=None):
    """Every Rust file of the fixtures, as committed and in each
    documentation condition, maps to the surface and back to its own bytes;
    the surface has no word of the table in its code. Returns the problems
    and the numbers."""
    table = table or Table()
    problems, files, size, surface_size = [], 0, 0, 0
    for name, text in sources().items():
        for cond, t in (("all", text), ("summary", pair.strip_comments(text, True)), ("none", pair.strip_comments(text))):
            s = table.to_surface(t)
            if table.to_rust(s) != t:
                problems.append(f"{name} (docs {cond}): does not map back to its bytes")
            left = sorted({x for k, x in lex(s) if k == "ident" and x in table.fwd})
            if left:
                problems.append(f"{name} (docs {cond}): the surface has {left[:5]}")
            if s.count("\n") != t.count("\n"):
                problems.append(f"{name} (docs {cond}): the surface has other lines")
            if cond == "none":
                size, surface_size = size + len(t.encode()), surface_size + len(s.encode())
        files += 1
    return problems, {"files": files, "bytes": size, "surface_bytes": surface_size}


def leaks_report(table=None):
    """{where: {word: count}} of the table's words (plain English apart)
    that the surface of the fixtures still shows: in strings and in the
    comments of each documentation condition."""
    table = table or Table()
    out = {"strings": {}, "comments (docs all)": {}, "comments (docs summary)": {}}
    for text in sources().values():
        for cond, t in (("all", text), ("summary", pair.strip_comments(text, True))):
            for k, x in lex(table.to_surface(t)):
                where = "strings" if k == "str" and cond == "all" else f"comments (docs {cond})" if k == "comment" else None
                if where:
                    for w, n in table.leaks(x).items():
                        out[where][w] = out[where].get(w, 0) + n
    return out


def main():
    cmd = sys.argv[1:]
    if cmd in (["make"], ["make", "--check"]):
        files = make()
        files[os.path.join(DIR, "MANIFEST")] = manifest(files)
        if cmd == ["make"]:
            shutil.rmtree(os.path.join(DIR, "tasks"), ignore_errors=True)
            for p, text in files.items():
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as h:
                    h.write(text)
            print(f"wrote the table ({len(json.loads(files[TABLE])['words'])} words), the prompt, "
                  f"{len(files) - 3} tasks and the MANIFEST")
            return 0
        bad = [os.path.relpath(p, HERE) for p, text in files.items()
               if not os.path.exists(p) or open(p, encoding="utf-8").read() != text]
        have = {os.path.join(DIR, "tasks", f) for f in os.listdir(os.path.join(DIR, "tasks"))}
        bad += [os.path.relpath(p, HERE) for p in sorted(have - set(files))]
        for b in bad:
            print(f"{b}: differs from what `make` writes", file=sys.stderr)
        if not bad:
            print(f"ok: the table, the prompt, {len(files) - 3} tasks and the MANIFEST are what `make` writes")
        return 1 if bad else 0
    if cmd == ["roundtrip"]:
        problems, n = roundtrip()
        for p in problems:
            print(p, file=sys.stderr)
        if not problems:
            print(f"ok: {n['files']} files in three documentation conditions map back to their bytes; without comments "
                  f"{n['bytes']} bytes are {n['surface_bytes']} in the surface")
        return 1 if problems else 0
    if cmd == ["leaks"]:
        for where, words in leaks_report().items():
            top = sorted(words.items(), key=lambda x: (-x[1], x[0]))
            print(f"{where}: {sum(words.values())} occurrences of {len(words)} words: "
                  + ", ".join(f"{w} {n}" for w, n in top[:15]))
        return 0
    if len(cmd) == 2 and cmd[0] == "show":
        with open(cmd[1], encoding="utf-8") as h:
            sys.stdout.write(Table().to_surface(h.read()))
        return 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
