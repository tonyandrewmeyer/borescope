"""Shared fixtures: an in-memory fake transport and a shell context."""

from __future__ import annotations

import datetime
import io
import posixpath
from typing import cast

import pytest
from ops import pebble

from borescope.discovery import Target
from borescope.shell.context import ShellContext
from borescope.transport import Transport


class FakeProc:
    """Stand-in for ops.pebble.ExecProcess covering the bits borescope uses."""

    def __init__(self, command: list[str], stdin: str | None):
        self.command = command
        self.stdin = stdin

    def wait_output(self) -> tuple[str, str]:
        if self.command and self.command[0] == "echo":
            return " ".join(self.command[1:]) + "\n", ""
        if self.command and self.command[0] == "cat":
            return self.stdin or "", ""
        return "", ""


class FakeTransport:
    """An in-memory filesystem implementing the Transport surface fs commands use."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.dirs: set[str] = {"/"}

    # -- test helpers ------------------------------------------------------
    def add_file(self, path: str, content: bytes | str = b"") -> None:
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        self.files[path] = data
        parent = posixpath.dirname(path)
        while parent and parent != "/":
            self.dirs.add(parent)
            parent = posixpath.dirname(parent)
        self.dirs.add("/")

    def add_dir(self, path: str) -> None:
        self.dirs.add(path)
        parent = posixpath.dirname(path)
        while parent and parent != "/":
            self.dirs.add(parent)
            parent = posixpath.dirname(parent)

    # -- internal ----------------------------------------------------------
    def _exists(self, path: str) -> bool:
        return path in self.files or path in self.dirs

    def _info(self, path: str) -> pebble.FileInfo:
        is_dir = path in self.dirs
        return pebble.FileInfo(
            path=path,
            name=posixpath.basename(path) or "/",
            type=pebble.FileType.DIRECTORY if is_dir else pebble.FileType.FILE,
            size=None if is_dir else len(self.files[path]),
            permissions=0o755 if is_dir else 0o644,
            last_modified=datetime.datetime(2026, 1, 1, 12, 0, 0),
            user_id=0,
            user="root",
            group_id=0,
            group="root",
        )

    # -- Transport surface -------------------------------------------------
    def list_files(self, path, *, pattern=None, itself=False):
        if itself:
            if not self._exists(path):
                raise pebble.PathError(
                    "not-found", f"{path}: no such file or directory"
                )
            return [self._info(path)]
        if path in self.files:
            return [self._info(path)]
        if path not in self.dirs:
            raise pebble.PathError("not-found", f"{path}: no such file or directory")
        children = []
        for entry in [*self.files, *self.dirs]:
            if entry != path and posixpath.dirname(entry) == path:
                children.append(self._info(entry))
        return children

    def pull(self, path, *, encoding="utf-8"):
        if path not in self.files:
            raise pebble.PathError("not-found", f"{path}: no such file or directory")
        data = self.files[path]
        return (
            io.BytesIO(data) if encoding is None else io.StringIO(data.decode(encoding))
        )

    def push(self, path, source, *, encoding="utf-8", make_dirs=False, **kwargs):
        if isinstance(source, bytes):
            data = source
        elif isinstance(source, str):
            data = source.encode(encoding)
        else:
            raw = source.read()
            data = raw if isinstance(raw, bytes) else raw.encode(encoding)
        self.add_file(path, data)

    def make_dir(self, path, *, make_parents=False, **kwargs):
        if not make_parents and posixpath.dirname(path) not in self.dirs:
            raise pebble.PathError("generic", f"mkdir {path}: parent does not exist")
        self.add_dir(path)

    def remove_path(self, path, *, recursive=False):
        if path in self.files:
            del self.files[path]
            return
        if path in self.dirs:
            kids = [
                e
                for e in [*self.files, *self.dirs]
                if e != path and e.startswith(path.rstrip("/") + "/")
            ]
            if kids and not recursive:
                raise pebble.PathError("generic", f"rmdir {path}: directory not empty")
            for kid in kids:
                self.files.pop(kid, None)
                self.dirs.discard(kid)
            self.dirs.discard(path)
            return
        raise pebble.PathError("not-found", f"{path}: no such file or directory")

    def exec(self, command, *, working_dir=None, stdin=None, **kwargs):
        return FakeProc(command, stdin)


@pytest.fixture
def transport() -> FakeTransport:
    fake = FakeTransport()
    fake.add_file("/etc/hostname", "borescope\n")
    fake.add_file(
        "/etc/passwd",
        "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1::/usr/sbin:/usr/sbin/nologin\n",
    )
    fake.add_dir("/var/log/app")
    fake.add_file("/var/log/app/error.log", "line1\nline2\nERROR boom\nline4\n")
    return fake


@pytest.fixture
def target() -> Target:
    return Target(
        unit="app/0",
        app="app",
        container="workload",
        model="testmodel",
        controller="ctrl",
    )


@pytest.fixture
def ctx(transport: FakeTransport, target: Target) -> ShellContext:
    return ShellContext(transport=cast(Transport, transport), target=target)
