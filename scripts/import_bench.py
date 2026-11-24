#!/usr/bin/env python3
"""Imports `bench/` from a commit of lang-bmb, and proves the import.

  import_bench.py LANG_BMB COMMIT           write bench/ from the commit
  import_bench.py --check LANG_BMB COMMIT   fail unless bench/ is that import

LANG_BMB is a checkout of https://github.com/lang-bmb/lang-bmb that has the
commit. The tree is read with `git archive COMMIT bench`, so only tracked
files come over.

One transformation is applied, so that the host name of the model gateway the
measurements ran through is not in this repository:

- result rows (`*.jsonl`) and session records (`*.json.gz`, after
  decompression): every occurrence of the host name becomes `<gateway>`.
  Nothing else in a row changes. A session record that held the name is
  compressed again the way the harness writes it (bench/m1/sessionlog.py:
  gzip, level 9, time 0, no file name); the others keep their bytes.
- `bench/README.md` and `bench/m1/model_api.py`: the gateway is read from the
  environment (`BMB_GATEWAY`) instead of being written in the text. The exact
  replacements are in EDITS below.

The host name is not written in this file either: it is recognised by the
SHA-256 of its text, among the host names the source has in front of
`/openai/v1` and `/anthropic/v1`. The import stops when a frozen file (one a
MANIFEST lists) would change, when a file of another kind holds the name, or
when the name is still somewhere afterwards.

`bench/SOURCE` records the commit. Files changed or added in this repository
after the import are listed there (`changed:`, `added:`), and `--check`
verifies the list is exact: every other tracked file under `bench/` equals the
transformed source byte for byte, a listed file really differs, and no listed
file is frozen. Without `--check`, listed files are left as they are.

Standard library only. Deterministic: the same commit gives the same bytes.
"""
import gzip
import hashlib
import io
import os
import re
import subprocess
import sys
import tarfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = "bench/SOURCE"
REPOSITORY = "https://github.com/lang-bmb/lang-bmb"
HOST_SHA256 = "6b6573740b4d01a3e1f0775fe605571864e8c99858289be1a53339eaa9cd91a4"
PLACEHOLDER = b"<gateway>"

# (path, old text, new text): each old text occurs exactly once. `{host}` is
# the gateway's host name.
EDITS = [
    ("bench/m1/model_api.py",
     "Base URLs default to the environment's gateway and can be overridden:\n"
     "BMB_OPENAI_BASE_URL, BMB_ANTHROPIC_BASE_URL. Keys are optional (the gateway's\n"
     "credentials are supplied by the environment): OPENAI_API_KEY, ANTHROPIC_API_KEY.\n",
     "Base URLs come from the environment: BMB_GATEWAY is the URL of a gateway that\n"
     "serves both APIs (under `/openai/v1` and `/anthropic/v1`), and\n"
     "BMB_OPENAI_BASE_URL, BMB_ANTHROPIC_BASE_URL give either base URL whole. No\n"
     "host is written here; in published result rows the measuring gateway's host\n"
     "reads `<gateway>`. Keys are optional (the gateway's credentials are supplied\n"
     "by the environment): OPENAI_API_KEY, ANTHROPIC_API_KEY.\n"),
    ("bench/m1/model_api.py",
     'GATEWAY = "https://{host}"\n'
     'OPENAI_BASE = os.environ.get("BMB_OPENAI_BASE_URL", GATEWAY + "/openai/v1")\n'
     'ANTHROPIC_BASE = os.environ.get("BMB_ANTHROPIC_BASE_URL", GATEWAY + "/anthropic/v1")\n',
     'GATEWAY = os.environ.get("BMB_GATEWAY", "").rstrip("/")\n'
     'OPENAI_BASE = os.environ.get("BMB_OPENAI_BASE_URL") or (GATEWAY and GATEWAY + "/openai/v1")\n'
     'ANTHROPIC_BASE = os.environ.get("BMB_ANTHROPIC_BASE_URL") or (GATEWAY and GATEWAY + "/anthropic/v1")\n'),
    ("bench/m1/model_api.py",
     "    data = json.dumps(body, default=vars).encode()\n",
     '    if not url.startswith(("http://", "https://")):\n'
     '        raise SystemExit("model_api: no model endpoint: set BMB_GATEWAY (the gateway\'s URL), "\n'
     '                         "or BMB_OPENAI_BASE_URL / BMB_ANTHROPIC_BASE_URL")\n'
     "    data = json.dumps(body, default=vars).encode()\n"),
    ("bench/README.md",
     "주소 기본값은 이 환경의 게이트웨이 `https://{host}`(`/openai/v1`, `/anthropic/v1`)다. "
     "`BMB_OPENAI_BASE_URL`·`BMB_ANTHROPIC_BASE_URL`로 바꾼다.",
     "주소는 환경 변수로 준다: `BMB_GATEWAY`(두 API를 `/openai/v1`, `/anthropic/v1` 아래에서 내는 게이트웨이의 주소)나 "
     "`BMB_OPENAI_BASE_URL`·`BMB_ANTHROPIC_BASE_URL`(주소 전체). 저장소에는 게이트웨이의 호스트 이름이 없고, "
     "결과 행과 세션 기록에서는 `<gateway>`로 적혀 있다."),
]


def gz(data):
    """gzip as bench/m1/sessionlog.py writes it: level 9, time 0, no name."""
    c = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    body = c.compress(data) + c.flush()
    tail = (zlib.crc32(data) & 0xFFFFFFFF).to_bytes(4, "little") + (len(data) & 0xFFFFFFFF).to_bytes(4, "little")
    return b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff" + body + tail


def archive(lang_bmb, commit):
    """{path: (bytes, executable)} of bench/ at the commit, and the full commit id."""
    full = subprocess.run(["git", "-C", lang_bmb, "rev-parse", "--verify", commit + "^{commit}"],
                          capture_output=True, text=True, check=True).stdout.strip()
    tar = subprocess.run(["git", "-C", lang_bmb, "archive", "--format=tar", full, "bench"],
                         capture_output=True, check=True).stdout
    files = {}
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        for m in t:
            if m.isdir() or m.name == "pax_global_header":
                continue
            if not m.isfile():
                sys.exit(f"import: {m.name}: not a regular file")
            files[m.name] = (t.extractfile(m).read(), bool(m.mode & 0o100))
    return files, full


def frozen_paths(files):
    """Every path a MANIFEST lists (`<sha256>  <path relative to its directory>`)."""
    out = set()
    for path, (data, _) in files.items():
        if os.path.basename(path) != "MANIFEST":
            continue
        for line in data.decode().splitlines():
            if line.strip():
                out.add(os.path.normpath(os.path.join(os.path.dirname(path), line.split(None, 1)[1])))
    return out


def find_host(files):
    """The gateway's host name, found in the source by its digest."""
    seen = set()
    for data, _ in files.values():
        seen.update(re.findall(rb"https?://([A-Za-z0-9.-]+)/(?:openai|anthropic)/v1", data))
        seen.update(re.findall(rb'GATEWAY = "https?://([A-Za-z0-9.-]+)"', data))
    for h in sorted(seen):
        if hashlib.sha256(h).hexdigest() == HOST_SHA256:
            return h
    sys.exit("import: the gateway's host name is not in the source (HOST_SHA256)")


def transform(files):
    """The tree this repository holds, and the counts of what changed."""
    host = find_host(files)
    frozen = frozen_paths(files)
    out, counts = {}, {"jsonl": 0, "jsonl lines": 0, "gz": 0, "other": 0}
    edits = {}
    for path, old, new in EDITS:
        edits.setdefault(path, []).append((old.replace("{host}", host.decode()), new))
    for path, (data, exe) in sorted(files.items()):
        new = data
        if path in edits:
            text = data.decode()
            for old, repl in edits[path]:
                if text.count(old) != 1:
                    sys.exit(f"import: {path}: expected exactly one occurrence of {old[:50]!r}")
                text = text.replace(old, repl)
            new = text.encode()
            counts["other"] += 1
        elif path.endswith(".jsonl"):
            if host in data:
                new = data.replace(host, PLACEHOLDER)
                counts["jsonl"] += 1
                counts["jsonl lines"] += sum(1 for l in data.split(b"\n") if host in l)
        elif path.endswith(".gz"):
            plain = gzip.decompress(data)
            if host in plain:
                new = gz(plain.replace(host, PLACEHOLDER))
                counts["gz"] += 1
        elif host in data:
            sys.exit(f"import: {path}: holds the gateway's host name and no rule covers it")
        if new != data and path in frozen:
            sys.exit(f"import: {path}: frozen (listed in a MANIFEST) and holds the gateway's host name")
        out[path] = (new, exe)
    # Nothing of the name is left, in any letter case, compressed or not.
    part = host.split(b".")[-2].lower()
    for path, (data, _) in out.items():
        plain = gzip.decompress(data) if path.endswith(".gz") else data
        if part in plain.lower():
            sys.exit(f"import: {path}: still holds the gateway's host name")
    return out, counts, frozen


def read_source():
    """(commit, changed paths, added paths) from bench/SOURCE, or (None, set(), set())."""
    commit, changed, added = None, set(), set()
    try:
        lines = open(os.path.join(ROOT, SOURCE)).read().splitlines()
    except OSError:
        return commit, changed, added
    for line in lines:
        key, _, value = line.partition(":")
        value = value.strip()
        if key == "commit":
            commit = value
        elif key == "changed":
            changed.add(value)
        elif key == "added":
            added.add(value)
    return commit, changed, added


def source_text(full, changed, added):
    lines = [f"repository: {REPOSITORY}", f"commit: {full}", "path: bench",
             "transformation: scripts/import_bench.py", ""]
    lines.append("# Files under bench/ that differ from the transformed source, changed or")
    lines.append("# added in this repository. `scripts/import_bench.py --check` keeps this exact.")
    lines += [f"changed: {p}" for p in sorted(changed)]
    lines += [f"added: {p}" for p in sorted(added)]
    return "\n".join(lines) + "\n"


def tracked():
    """{path: executable} of the tracked files under bench/."""
    r = subprocess.run(["git", "-C", ROOT, "ls-files", "-s", "-z", "--", "bench"],
                       capture_output=True, check=True).stdout.decode()
    out = {}
    for entry in r.split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            out[path] = meta.split()[0] == "100755"
    return out


def write(tree, full, changed, added):
    for path in sorted(set(tracked()) - set(tree) - added - {SOURCE}):
        os.unlink(os.path.join(ROOT, path))
    for path, (data, exe) in tree.items():
        if path in changed:
            continue
        dest = os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        os.chmod(dest, 0o755 if exe else 0o644)
    with open(os.path.join(ROOT, SOURCE), "w") as f:
        f.write(source_text(full, changed, added))


def check(tree, full, frozen, changed, added):
    bad = []
    recorded = read_source()[0]
    if recorded != full:
        bad.append(f"{SOURCE}: records commit {recorded}, checked against {full}")
    have = tracked()
    recompressed = 0
    for path in sorted(set(tree) | set(have)):
        if path == SOURCE:
            continue
        if path in added:
            if path in tree or path not in have:
                bad.append(f"{path}: listed as added, but " + ("it is in the source" if path in tree else "it is not tracked"))
            continue
        if path not in have:
            bad.append(f"{path}: in the source, not tracked here")
            continue
        if path not in tree:
            bad.append(f"{path}: tracked here, not in the source and not listed as added")
            continue
        data, exe = tree[path]
        mine = open(os.path.join(ROOT, path), "rb").read()
        same = mine == data
        if not same and path.endswith(".gz") and path not in changed:
            # Another zlib may compress to other bytes: the record itself decides.
            same = gzip.decompress(mine) == gzip.decompress(data)
            recompressed += same
        if path in changed:
            if path in frozen:
                bad.append(f"{path}: listed as changed, and frozen by a MANIFEST")
            if same:
                bad.append(f"{path}: listed as changed, but equal to the source")
            continue
        if not same:
            bad.append(f"{path}: differs from the transformed source")
        elif have[path] != exe:
            bad.append(f"{path}: executable bit differs from the source")
    for path in sorted((changed | added) - set(have)):
        if path not in tree:
            bad.append(f"{path}: listed in {SOURCE}, not tracked")
    for line in bad:
        print("import: " + line, file=sys.stderr)
    if bad:
        return 1
    note = f", {recompressed} compared after decompression" if recompressed else ""
    print(f"import ok: bench/ is {full[:12]} transformed: {len(tree) - len(changed)} files equal, "
          f"{len(changed)} changed here, {len(added)} added here{note}")
    return 0


def main():
    args = sys.argv[1:]
    checking = args[:1] == ["--check"]
    if checking:
        args = args[1:]
    if len(args) != 2:
        sys.exit(__doc__)
    files, full = archive(*args)
    tree, counts, frozen = transform(files)
    _, changed, added = read_source()
    if checking:
        return check(tree, full, frozen, changed, added)
    write(tree, full, changed, added)
    print(f"imported {len(tree)} files from {full}: rewrote {counts['jsonl']} .jsonl "
          f"({counts['jsonl lines']} lines), {counts['gz']} .json.gz, {counts['other']} other; "
          f"{len(frozen)} frozen paths untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
