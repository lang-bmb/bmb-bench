#!/usr/bin/env python3
"""A rename through the language server, for the Rust arm of the port twin.

rust-analyzer runs for the length of a session (`Server`): it is started
when the session's tools are made, loads the crate while the agent works,
and a `rename` waits until it has. Nothing of it is kept between sessions
(rust-analyzer has no index on disk, and none is made before the session).

The server gets the crate as the session has it, with its own target
directory (the build script of a crate runs there once, as the server asks
cargo to; `cargo check` on save is off: the agent's `cargo_build` is the
arm's compiler). A file the session's tools write is given to the server
as an open document (`changed`); it watches nothing itself.

    ra.py version              the rust-analyzer the harness would use
    ra.py time CRATE FILE LINE NAME NEW
                               start-up and one rename on a crate, timed
                               (the edit is counted, not applied)

Standard library only.
"""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time

READY_TIMEOUT = 600   # seconds for the crate to load
REQUEST_TIMEOUT = 300  # seconds for one answer


class Refused(Exception):
    """The server (or the harness, before it asks) does not rename this."""


def version():
    """The version line of the rust-analyzer the toolchain gives (`rustup
    component add rust-analyzer`), or None when there is none."""
    try:
        r = subprocess.run(["rust-analyzer", "--version"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def uri(path):
    from urllib.parse import quote
    return "file://" + quote(os.path.abspath(path))


def path_of(u):
    from urllib.parse import unquote, urlparse
    return unquote(urlparse(u).path)


def utf16_col(line, col):
    """The UTF-16 offset of character `col` of `line` (LSP positions)."""
    return len(line[:col].encode("utf-16-le")) // 2


def from_utf16(line, units):
    """The character index of UTF-16 offset `units` in `line`."""
    return len(line.encode("utf-16-le")[:units * 2].decode("utf-16-le", errors="ignore"))


def apply_edits(text, edits):
    """`text` with the LSP text edits applied (ranges are of the old text;
    they do not overlap)."""
    lines = text.split("\n")
    starts, at = [], 0
    for ln in lines:
        starts.append(at)
        at += len(ln) + 1

    def offset(pos):
        if pos["line"] >= len(lines):
            return len(text)
        return starts[pos["line"]] + from_utf16(lines[pos["line"]], pos["character"])

    spans = sorted(((offset(e["range"]["start"]), offset(e["range"]["end"]), e["newText"]) for e in edits), reverse=True)
    for a, b, new in spans:
        text = text[:a] + new + text[b:]
    return text


class Server:
    """rust-analyzer on the crate at `root`, for one session."""

    def __init__(self, root, target_dir):
        self.root = os.path.realpath(root)
        self.t0 = time.perf_counter()
        self.ready_s = None
        env = {**os.environ, "CARGO_TARGET_DIR": target_dir, "CARGO_NET_OFFLINE": "true", "CARGO_TERM_COLOR": "never"}
        self.p = subprocess.Popen(["rust-analyzer"], cwd=self.root, env=env, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.next = 1
        self.answers = {}
        self.open = {}
        self.lock = threading.Lock()
        self.ids = threading.Lock()
        self.ready = threading.Event()
        self.dead = threading.Event()
        threading.Thread(target=self._read, daemon=True).start()
        self.options = {
            "checkOnSave": False,
            "check": {"workspace": False},
            "cargo": {"buildScripts": {"enable": True}, "targetDir": target_dir, "allTargets": True},
            "procMacro": {"enable": False},
            "files": {"watcher": "client"},
            "numThreads": 2,
            "cachePriming": {"enable": True, "numThreads": 2},
            "diagnostics": {"enable": False},
        }
        self._send({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
            "processId": os.getpid(), "rootUri": uri(self.root),
            "workspaceFolders": [{"uri": uri(self.root), "name": "crate"}],
            "capabilities": {
                "workspace": {"configuration": True, "workspaceEdit": {"documentChanges": True}},
                "textDocument": {"rename": {"prepareSupport": True},
                                 "synchronization": {"dynamicRegistration": False}},
                "window": {"workDoneProgress": True},
                "experimental": {"serverStatusNotification": True},
            },
            "initializationOptions": self.options,
        }})

    # -- the wire --

    def _send(self, msg):
        data = json.dumps(msg).encode()
        with self.lock:
            self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(data) + data)
            self.p.stdin.flush()

    def _read(self):
        out = self.p.stdout
        try:
            while True:
                size = None
                while True:
                    ln = out.readline()
                    if not ln:
                        raise EOFError
                    ln = ln.strip()
                    if not ln:
                        break
                    if ln.lower().startswith(b"content-length:"):
                        size = int(ln.split(b":")[1])
                msg = json.loads(out.read(size))
                if "method" in msg and "id" in msg:  # a request of the server
                    self._serve(msg)
                elif "method" in msg:
                    self._notified(msg)
                elif msg.get("id") == 0:
                    self._send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
                elif msg.get("id") in self.answers:
                    self.answers[msg["id"]].put(msg)
        except (EOFError, OSError, ValueError):
            pass
        self.dead.set()
        self.ready.set()

    def _serve(self, msg):
        result = None
        if msg["method"] == "workspace/configuration":
            result = [self.options if it.get("section") == "rust-analyzer" else None for it in msg["params"]["items"]]
        self._send({"jsonrpc": "2.0", "id": msg["id"], "result": result})

    def _notified(self, msg):
        if msg["method"] == "experimental/serverStatus":
            p = msg["params"]
            if p.get("quiescent"):
                if self.ready_s is None:
                    self.ready_s = round(time.perf_counter() - self.t0, 3)
                self.ready.set()
            else:
                self.ready.clear()

    def _request(self, method, params):
        with self.ids:
            rid = self.next
            self.next += 1
            self.answers[rid] = queue.Queue()
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        try:
            return self.answers[rid].get(timeout=REQUEST_TIMEOUT)
        except queue.Empty:
            raise Refused(f"the language server did not answer within {REQUEST_TIMEOUT} s") from None
        finally:
            del self.answers[rid]

    # -- what the harness asks --

    def wait_ready(self):
        if not self.ready.wait(READY_TIMEOUT) or self.dead.is_set():
            raise Refused("the language server is not running" if self.dead.is_set()
                          else f"the language server did not load the crate within {READY_TIMEOUT} s")

    def changed(self, path):
        """A file of the crate was written (or made) by the session's tools:
        the server gets its text as an open document, so the next request
        sees it (a change it is only told to look for on disk may be read
        after the request)."""
        if self.dead.is_set():
            return
        with open(path, encoding="utf-8") as h:
            text = h.read()
        u = uri(path)
        if u not in self.open:
            self.open[u] = 1
            self._send({"jsonrpc": "2.0", "method": "textDocument/didOpen",
                        "params": {"textDocument": {"uri": u, "languageId": "rust", "version": 1, "text": text}}})
        else:
            self.open[u] += 1
            self._send({"jsonrpc": "2.0", "method": "textDocument/didChange",
                        "params": {"textDocument": {"uri": u, "version": self.open[u]},
                                   "contentChanges": [{"text": text}]}})

    def rename(self, path, line, col, new):
        """The workspace edit of renaming the symbol at `path` (absolute),
        0-based `line` and character `col`, as {absolute path: [text edit]};
        `Refused` with the server's words when it does not."""
        self.wait_ready()
        with open(path, encoding="utf-8") as h:
            lines = h.read().split("\n")
        pos = {"textDocument": {"uri": uri(path)}, "position": {"line": line, "character": utf16_col(lines[line], col)}}
        r = self._request("textDocument/prepareRename", pos)
        if "error" in r or r.get("result") is None:
            raise Refused(r.get("error", {}).get("message", "nothing to rename here"))
        r = self._request("textDocument/rename", {**pos, "newName": new})
        if "error" in r or r.get("result") is None:
            raise Refused(r.get("error", {}).get("message", "nothing to rename here"))
        edit, out = r["result"], {}
        for u, es in (edit.get("changes") or {}).items():
            out.setdefault(path_of(u), []).extend(es)
        for dc in edit.get("documentChanges") or []:
            if "textDocument" not in dc:
                raise Refused(f"the rename would {dc.get('kind', 'change')} a file; only text edits are applied")
            out.setdefault(path_of(dc["textDocument"]["uri"]), []).extend(dc["edits"])
        return out

    def close(self):
        try:
            if not self.dead.is_set():
                self.answers[-1] = queue.Queue()
                self._send({"jsonrpc": "2.0", "id": -1, "method": "shutdown", "params": None})
                try:
                    self.answers[-1].get(timeout=5)
                except queue.Empty:
                    pass
                self._send({"jsonrpc": "2.0", "method": "exit", "params": None})
        except OSError:
            pass
        try:
            self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
        for pipe in (self.p.stdin, self.p.stdout):
            try:
                pipe.close()
            except OSError:
                pass


def column(line_text, name):
    """The character index of the first whole-word `name` in a line, or None."""
    m = re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])", line_text)
    return m.start() if m else None


def main():
    if sys.argv[1:] == ["version"]:
        v = version()
        print(v or "no rust-analyzer: rustup component add rust-analyzer")
        return 0 if v else 1
    if len(sys.argv) == 7 and sys.argv[1] == "time":
        crate, f, line, name, new = sys.argv[2:]
        import tempfile
        with tempfile.TemporaryDirectory(prefix="ra-target-", dir=os.environ.get("TMPDIR")) as tgt:
            s = Server(crate, tgt)
            try:
                s.wait_ready()
                p = os.path.join(s.root, f)
                with open(p, encoding="utf-8") as h:
                    col = column(h.read().split("\n")[int(line) - 1], name)
                t0 = time.perf_counter()
                edits = s.rename(p, int(line) - 1, col, new)
                took = time.perf_counter() - t0
            finally:
                s.close()
        print(json.dumps({"rust_analyzer": version(), "ready_s": s.ready_s, "rename_s": round(took, 3),
                          "files": {os.path.relpath(k, s.root): len(v) for k, v in sorted(edits.items())}}))
        return 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
