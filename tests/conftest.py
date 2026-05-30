# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Shared fixtures: an in-memory fake transport and a shell context."""

from __future__ import annotations

import datetime
import io
import posixpath
from types import SimpleNamespace
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
        if self.command and self.command[0] == 'echo':
            return ' '.join(self.command[1:]) + '\n', ''
        if self.command and self.command[0] == 'cat':
            return self.stdin or '', ''
        return '', ''


class FakeTransport:
    """An in-memory filesystem implementing the Transport surface fs commands use."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.dirs: set[str] = {'/'}
        self.links: dict[str, str] = {}

    # -- test helpers ------------------------------------------------------
    def add_file(self, path: str, content: bytes | str = b'') -> None:
        data = content if isinstance(content, bytes) else content.encode('utf-8')
        self.files[path] = data
        parent = posixpath.dirname(path)
        while parent and parent != '/':
            self.dirs.add(parent)
            parent = posixpath.dirname(parent)
        self.dirs.add('/')

    def add_dir(self, path: str) -> None:
        self.dirs.add(path)
        parent = posixpath.dirname(path)
        while parent and parent != '/':
            self.dirs.add(parent)
            parent = posixpath.dirname(parent)

    def add_symlink(self, path: str, target: str) -> None:
        self.links[path] = target
        parent = posixpath.dirname(path)
        while parent and parent != '/':
            self.dirs.add(parent)
            parent = posixpath.dirname(parent)

    # -- internal ----------------------------------------------------------
    def _exists(self, path: str) -> bool:
        return path in self.files or path in self.dirs or path in self.links

    def _info(self, path: str) -> pebble.FileInfo:
        is_dir = path in self.dirs
        is_link = path in self.links
        if is_link:
            ftype = pebble.FileType.SYMLINK
        elif is_dir:
            ftype = pebble.FileType.DIRECTORY
        else:
            ftype = pebble.FileType.FILE
        return pebble.FileInfo(
            path=path,
            name=posixpath.basename(path) or '/',
            type=ftype,
            size=None if is_dir or is_link else len(self.files[path]),
            permissions=0o755 if is_dir else 0o644,
            last_modified=datetime.datetime(2026, 1, 1, 12, 0, 0),
            user_id=0,
            user='root',
            group_id=0,
            group='root',
        )

    # -- Transport surface -------------------------------------------------
    def list_files(self, path, *, pattern=None, itself=False):
        if itself:
            if not self._exists(path):
                raise pebble.PathError('not-found', f'{path}: no such file or directory')
            return [self._info(path)]
        if path in self.files:
            return [self._info(path)]
        if path not in self.dirs:
            raise pebble.PathError('not-found', f'{path}: no such file or directory')
        return [
            self._info(entry)
            for entry in [*self.files, *self.dirs]
            if entry != path and posixpath.dirname(entry) == path
        ]

    def pull(self, path, *, encoding='utf-8'):
        if path not in self.files:
            raise pebble.PathError('not-found', f'{path}: no such file or directory')
        data = self.files[path]
        return io.BytesIO(data) if encoding is None else io.StringIO(data.decode(encoding))

    def push(self, path, source, *, encoding='utf-8', make_dirs=False, **kwargs):
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
            raise pebble.PathError('generic', f'mkdir {path}: parent does not exist')
        self.add_dir(path)

    def remove_path(self, path, *, recursive=False):
        if path in self.files:
            del self.files[path]
            return
        if path in self.dirs:
            kids = [
                e
                for e in [*self.files, *self.dirs]
                if e != path and e.startswith(path.rstrip('/') + '/')
            ]
            if kids and not recursive:
                raise pebble.PathError('generic', f'rmdir {path}: directory not empty')
            for kid in kids:
                self.files.pop(kid, None)
                self.dirs.discard(kid)
            self.dirs.discard(path)
            return
        raise pebble.PathError('not-found', f'{path}: no such file or directory')

    def exec(self, command, *, working_dir=None, stdin=None, **kwargs):
        return FakeProc(command, stdin)


class _Plan:
    """Minimal stand-in for ops.pebble.Plan (only the bits the shell uses)."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def to_yaml(self) -> str:
        import yaml

        return yaml.safe_dump(self._data)

    def to_dict(self) -> dict:
        return self._data


class FakePebble:
    """In-memory Pebble surface for the service/plan/check/notice/change commands.

    Read methods return lightweight ``SimpleNamespace`` objects shaped like the
    ops.pebble types (only the attributes the commands touch); action methods
    record their calls so tests can assert on them. ``CheckStatus`` uses the real
    enum because ``health`` compares against it by identity.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []
        self._services = [
            SimpleNamespace(name='web', startup=_ns('enabled'), current=_ns('active')),
            SimpleNamespace(name='worker', startup=_ns('disabled'), current=_ns('inactive')),
        ]
        self._checks = [
            SimpleNamespace(
                name='ready',
                level=_ns('ready'),
                status=pebble.CheckStatus.UP,
                failures=0,
                threshold=3,
            ),
        ]

    # -- system ------------------------------------------------------------
    def get_system_info(self):
        return SimpleNamespace(version='1.99')

    # -- services ----------------------------------------------------------
    def get_services(self, names=None):
        if not names:
            return list(self._services)
        return [s for s in self._services if s.name in names]

    def _action(self, verb, *args):
        self.calls.append((verb, args))
        return 'change-1'

    def start_services(self, names, **kw):
        return self._action('start', tuple(names))

    def stop_services(self, names, **kw):
        return self._action('stop', tuple(names))

    def restart_services(self, names, **kw):
        return self._action('restart', tuple(names))

    def replan_services(self, **kw):
        return self._action('replan')

    # -- plan --------------------------------------------------------------
    def get_plan(self):
        return _Plan({'services': {'web': {'command': '/web', 'override': 'replace'}}})

    # -- checks ------------------------------------------------------------
    def get_checks(self, level=None, names=None):
        if not names:
            return list(self._checks)
        return [c for c in self._checks if c.name in names]

    def set_check_status(self, status) -> None:
        """Test helper: flip the single check's status."""
        self._checks[0].status = status

    # -- notices -----------------------------------------------------------
    def get_notices(self, **kw):
        return [
            SimpleNamespace(
                id='1',
                type=_ns('custom'),
                key='example.com/thing',
                occurrences=3,
                last_repeated=datetime.datetime(2026, 1, 2, 3, 4, 5),
            ),
        ]

    def get_notice(self, notice_id):
        return SimpleNamespace(
            id=notice_id,
            type=_ns('custom'),
            key='example.com/thing',
            occurrences=3,
            first_occurred=datetime.datetime(2026, 1, 1),
            last_occurred=datetime.datetime(2026, 1, 2),
            last_data={'k': 'v'},
        )

    def notify(self, type, key, *, data=None):
        self.calls.append(('notify', (key, data)))
        return '7'

    # -- changes -----------------------------------------------------------
    def get_changes(self, select=None, service=None):
        task = SimpleNamespace(status=_ns('Done'), summary='Do the thing')
        return [
            SimpleNamespace(
                id='1', status=_ns('Done'), ready=True, summary='Start web', tasks=[task]
            ),
        ]

    def get_change(self, change_id):
        task = SimpleNamespace(status=_ns('Done'), summary='Do the thing')
        return SimpleNamespace(id=str(change_id), summary='Start web', tasks=[task])


def _ns(value: str) -> SimpleNamespace:
    """An enum-ish object exposing ``.value`` (what ``_enum_value`` reads)."""
    return SimpleNamespace(value=value)


@pytest.fixture
def pebble_transport() -> FakePebble:
    return FakePebble()


@pytest.fixture
def pebble_ctx(pebble_transport: FakePebble, target: Target) -> ShellContext:
    return ShellContext(transport=cast('Transport', pebble_transport), target=target)


@pytest.fixture
def transport() -> FakeTransport:
    fake = FakeTransport()
    fake.add_file('/etc/hostname', 'borescope\n')
    fake.add_file(
        '/etc/passwd',
        'root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1::/usr/sbin:/usr/sbin/nologin\n',
    )
    fake.add_dir('/var/log/app')
    fake.add_file('/var/log/app/error.log', 'line1\nline2\nERROR boom\nline4\n')
    return fake


@pytest.fixture
def target() -> Target:
    return Target(
        unit='app/0',
        app='app',
        container='workload',
        model='testmodel',
        controller='ctrl',
    )


@pytest.fixture
def ctx(transport: FakeTransport, target: Target) -> ShellContext:
    return ShellContext(transport=cast('Transport', transport), target=target)
