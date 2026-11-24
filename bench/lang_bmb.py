"""The product checkout: where the compiler's sources, builds and history are.

The harnesses live in this repository and the compiler in lang-bmb
(https://github.com/lang-bmb/lang-bmb). A harness finds the compiler binary
through `$BMB`. What else it needs from the product (its sources, its git
history, a build of it, the caches under its `target/`) it takes from the
checkout `$LANG_BMB` names, through this module. Standard library only.
"""
import os
import subprocess


def root():
    """The lang-bmb checkout, or exit saying how to name it."""
    d = os.environ.get("LANG_BMB")
    if not d:
        raise SystemExit("LANG_BMB is not set: it names a checkout of https://github.com/lang-bmb/lang-bmb "
                         "(this step reads the product's sources, history or build)")
    d = os.path.abspath(d)
    if not os.path.isdir(os.path.join(d, "compiler")):
        raise SystemExit(f"LANG_BMB={d}: not a lang-bmb checkout (no compiler/)")
    return d


def path(*parts):
    """A path under the lang-bmb checkout."""
    return os.path.join(root(), *parts)


def locate(rel, here):
    """A repository-relative path or pattern: `bench/..` is in this
    repository (`here`), everything else in the lang-bmb checkout."""
    return os.path.join(here if rel.split("/")[0] == "bench" else root(), rel)


def repository_of(commit, here):
    """The repository that has `commit`: this one (`here`), else the lang-bmb
    checkout. A task or a run from before the harnesses moved here names a
    lang-bmb commit, and that history has `bench/` too."""
    r = subprocess.run(["git", "cat-file", "-e", commit + "^{commit}"], cwd=here, capture_output=True)
    return here if r.returncode == 0 else root()


def commit():
    """HEAD of the lang-bmb checkout, with `+dirty` when its tracked files
    differ from it; None when LANG_BMB is not set."""
    if not os.environ.get("LANG_BMB"):
        return None
    d = root()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=d,
                           capture_output=True, text=True).stdout.strip()
    return head + ("+dirty" if dirty else "")


def stamp():
    """The row field that names the product: `lang_bmb_commit`. A row's
    `commit` is this repository's (the harness and the frozen sets). The
    field is left out when LANG_BMB is not set."""
    c = commit()
    return {"lang_bmb_commit": c} if c else {}
