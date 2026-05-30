# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Filesystem commands implemented over the Pebble files API.

These exist as built-ins (rather than ``exec``) because they need either
shell-side state (paths relative to ``cwd``) or the Pebble files API
(``pull``/``push``/``list_files``/``make_dir``/``remove_path``) to work against a
rock with no shell or coreutils.
"""

from __future__ import annotations

import fnmatch
import posixpath
import re
import sys
import time
from typing import TYPE_CHECKING, Any

from .. import pathutils
from ..sanitise import safe_name
from ._args import parse_args
from .base import Command, Result

if TYPE_CHECKING:
    from ...transport import Transport
    from ..context import ShellContext


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _read_bytes(transport: Transport, path: str) -> bytes:
    with transport.pull(path, encoding=None) as handle:
        data = handle.read()
    return data if isinstance(data, bytes) else data.encode('utf-8')


def _read_text(transport: Transport, path: str) -> str:
    data = _read_bytes(transport, path)
    return data.decode('utf-8', errors='replace')


def _is_dir(info: Any) -> bool:
    return getattr(getattr(info, 'type', None), 'name', '') == 'DIRECTORY'


def _int(value: str | None, default: int) -> int:
    """Parse a line count, returning *default* when unset; raise on a bad value."""
    return default if value is None else int(value)  # ValueError propagates to caller


def _mode_str(perm: int | None) -> str:
    if perm is None:
        return '---------'
    out = ''
    for shift in (6, 3, 0):
        bits = (perm >> shift) & 7
        out += 'r' if bits & 4 else '-'
        out += 'w' if bits & 2 else '-'
        out += 'x' if bits & 1 else '-'
    return out


def _type_char(info: Any) -> str:
    name = getattr(getattr(info, 'type', None), 'name', '')
    return {'DIRECTORY': 'd', 'SYMLINK': 'l'}.get(name, '-')


def _long_format(info: Any) -> str:
    size = getattr(info, 'size', None) or 0
    mtime = getattr(info, 'last_modified', None)
    when = mtime.strftime('%Y-%m-%d %H:%M') if mtime else ''
    perms = _mode_str(getattr(info, 'permissions', None))
    return f'{_type_char(info)}{perms} {str(size).rjust(8)} {when:>16} {safe_name(info.name)}'


def _resolve(ctx: ShellContext, path: str) -> str:
    return pathutils.resolve(ctx.cwd, path, home=ctx.home)


def _input_text(ctx: ShellContext, paths: list[str], stdin: str | None) -> str:
    if paths:
        return _read_text(ctx.transport, _resolve(ctx, paths[0]))
    return stdin or ''


def _dest_path(ctx: ShellContext, dst: str, src: str) -> str:
    """If *dst* is an existing directory, place *src*'s basename inside it."""
    try:
        infos = ctx.transport.list_files(dst, itself=True)
    except Exception:
        return dst
    if infos and _is_dir(infos[0]):
        return posixpath.join(dst, posixpath.basename(src))
    return dst


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
class Ls(Command):
    name = 'ls'
    summary = 'List directory contents'
    usage = 'ls [-l] [-a] [path...]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        flags, _, paths = parse_args(args)
        long, show_all = 'l' in flags, 'a' in flags
        paths = paths or [ctx.cwd]
        blocks: list[str] = []
        errors: list[str] = []
        for path in paths:
            try:
                infos = ctx.transport.list_files(_resolve(ctx, path))
            except Exception as exc:
                errors.append(f'ls: {path}: {exc}')
                continue
            entries = sorted(infos, key=lambda i: i.name)
            if not show_all:
                entries = [i for i in entries if not i.name.startswith('.')]
            rendered = '\n'.join(_long_format(i) if long else safe_name(i.name) for i in entries)
            blocks.append(f'{path}:\n{rendered}' if len(paths) > 1 else rendered)
        return Result(
            output='\n\n'.join(b for b in blocks if b),
            error='\n'.join(errors),
            code=1 if errors else 0,
        )


class Cat(Command):
    name = 'cat'
    summary = 'Concatenate and print files'
    usage = 'cat [file...]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        _, _, paths = parse_args(args)
        if not paths:
            return Result.ok(stdin or '')
        chunks: list[str] = []
        errors: list[str] = []
        for path in paths:
            try:
                chunks.append(_read_text(ctx.transport, _resolve(ctx, path)))
            except Exception as exc:
                errors.append(f'cat: {path}: {exc}')
        return Result(output=''.join(chunks), error='\n'.join(errors), code=1 if errors else 0)


class Head(Command):
    name = 'head'
    summary = 'Print the first lines of input'
    usage = 'head [-n N] [file]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        _, values, paths = parse_args(args, valued=('n',))
        try:
            count = _int(values.get('n'), 10)
        except ValueError:
            return Result.fail(f'head: invalid line count: {values["n"]!r}')
        try:
            text = _input_text(ctx, paths, stdin)
        except Exception as exc:
            return Result.fail(f'head: {paths[0]}: {exc}')
        # keepends so original line terminators (and a trailing newline) survive.
        return Result.ok(''.join(text.splitlines(keepends=True)[:count]))


class Tail(Command):
    name = 'tail'
    summary = 'Print the last lines of input (-f to follow)'
    usage = 'tail [-n N] [-f] [file]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        flags, values, paths = parse_args(args, valued=('n',))
        try:
            count = _int(values.get('n'), 10)
        except ValueError:
            return Result.fail(f'tail: invalid line count: {values["n"]!r}')
        follow = 'f' in flags

        if not paths:
            if follow:
                return Result.fail('tail: -f requires a file')
            return Result.ok(''.join((stdin or '').splitlines(keepends=True)[-count:]))

        path = _resolve(ctx, paths[0])
        if follow:
            return self._follow(ctx, path, paths[0], count)
        try:
            text = _read_text(ctx.transport, path)
        except Exception as exc:
            return Result.fail(f'tail: {paths[0]}: {exc}')
        # keepends so original line terminators (and a trailing newline) survive.
        return Result.ok(''.join(text.splitlines(keepends=True)[-count:]))

    @staticmethod
    def _delta(seen: int, data: bytes) -> tuple[str, int]:
        """Return (new text to emit, updated byte offset) for a follow poll.

        Pebble can only ever hand back the *whole* file, so following means
        re-reading and diffing by byte offset. A file shorter than what we've
        already emitted was truncated or rotated, so reset and re-emit from the
        start rather than waiting for it to grow past the old length.
        """
        if len(data) < seen:  # truncated or rotated under us
            seen = 0
        if len(data) > seen:
            return data[seen:].decode('utf-8', errors='replace'), len(data)
        return '', seen

    @classmethod
    def _follow(cls, ctx: ShellContext, path: str, display: str, count: int) -> Result:
        try:
            data = _read_bytes(ctx.transport, path)
        except Exception as exc:
            return Result.fail(f'tail: {display}: {exc}')
        initial = '\n'.join(data.decode('utf-8', errors='replace').splitlines()[-count:])
        if initial:
            sys.stdout.write(initial + '\n')
            sys.stdout.flush()
        seen = len(data)
        try:
            while True:
                time.sleep(1.0)
                try:
                    data = _read_bytes(ctx.transport, path)
                except Exception:  # noqa: S112 - transient read failures are expected while following
                    continue
                chunk, seen = cls._delta(seen, data)
                if chunk:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
        except KeyboardInterrupt:
            sys.stdout.write('\n')
        return Result()


class Find(Command):
    name = 'find'
    summary = 'Walk the tree, filtering by name/type'
    usage = 'find [path] [-name PATTERN] [-type f|d] [-maxdepth N]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        # find uses single-dash long options (-name, -type), so it parses its own
        # args rather than going through the short-flag splitter.
        start_arg: str | None = None
        name_pat: str | None = None
        type_filter: str | None = None
        max_depth: int | None = None
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ('-name', '-iname'):
                i += 1
                name_pat = args[i] if i < len(args) else None
            elif arg == '-type':
                i += 1
                type_filter = args[i] if i < len(args) else None
            elif arg == '-maxdepth':
                i += 1
                try:
                    max_depth = int(args[i]) if i < len(args) else None
                except ValueError:
                    return Result.fail(f'find: invalid -maxdepth: {args[i]!r}')
            elif not arg.startswith('-') and start_arg is None:
                start_arg = arg
            i += 1
        start = _resolve(ctx, start_arg) if start_arg else ctx.cwd
        results: list[str] = []
        errors: list[str] = []

        # Iterative walk (each level is a juju round-trip, and a deep tree would
        # otherwise blow the Python recursion limit). Entries directly under the
        # start are depth 1; -maxdepth bounds both listing and descent.
        stack: list[tuple[str, int]] = [(start, 1)]
        while stack:
            path, depth = stack.pop()
            try:
                infos = ctx.transport.list_files(path)
            except Exception as exc:
                errors.append(f'find: {path}: {exc}')
                continue
            subdirs: list[tuple[str, int]] = []
            for info in sorted(infos, key=lambda i: i.name):
                full = posixpath.join(path, info.name)
                is_dir = _is_dir(info)
                within = max_depth is None or depth <= max_depth
                if within and self._matches(info.name, is_dir, name_pat, type_filter):
                    # Display the path defanged; walk the raw path.
                    results.append(safe_name(full))
                if is_dir and (max_depth is None or depth < max_depth):
                    subdirs.append((full, depth + 1))
            # Push reversed so siblings pop back in sorted (depth-first) order.
            stack.extend(reversed(subdirs))

        return Result(
            output='\n'.join(results),
            error='\n'.join(errors),
            code=1 if errors and not results else 0,
        )

    @staticmethod
    def _matches(name: str, is_dir: bool, name_pat: str | None, type_filter: str | None) -> bool:
        if name_pat is not None and not fnmatch.fnmatch(name, name_pat):
            return False
        if type_filter == 'd' and not is_dir:
            return False
        return not (type_filter == 'f' and is_dir)


class Stat(Command):
    name = 'stat'
    summary = 'Show file metadata'
    usage = 'stat <path...>'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        _, _, paths = parse_args(args)
        if not paths:
            return Result.fail('stat: usage: stat <path...>')
        blocks: list[str] = []
        errors: list[str] = []
        for path in paths:
            resolved = _resolve(ctx, path)
            try:
                info = ctx.transport.list_files(resolved, itself=True)[0]
            except Exception as exc:
                errors.append(f'stat: {path}: {exc}')
                continue
            blocks.append(self._format(info, resolved))
        return Result(output='\n'.join(blocks), error='\n'.join(errors), code=1 if errors else 0)

    @staticmethod
    def _format(info: Any, path: str) -> str:
        perms = getattr(info, 'permissions', None)
        mode = f'{perms:o}' if perms is not None else '?'
        size = getattr(info, 'size', None)
        owner = f'{getattr(info, "user", "?")}:{getattr(info, "group", "?")}'
        mtime = getattr(info, 'last_modified', None)
        return (
            f'  File: {path}\n'
            f'  Type: {_type_char(info)}  Mode: {mode}  Owner: {owner}\n'
            f'  Size: {size if size is not None else "?"}  '
            f'Modified: {mtime.isoformat() if mtime else "?"}'
        )


class Grep(Command):
    name = 'grep'
    summary = 'Search input for a pattern'
    usage = 'grep [-i] [-v] [-n] [-c] PATTERN [file...]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        flags, _, positionals = parse_args(args)
        if not positionals:
            return Result.fail('grep: usage: grep [-i] [-v] [-n] [-c] PATTERN [file...]')
        pattern, files = positionals[0], positionals[1:]
        try:
            regex = re.compile(pattern, re.IGNORECASE if 'i' in flags else 0)
        except re.error as exc:
            return Result.fail(f'grep: invalid pattern: {exc}')

        invert, show_num, count_only = 'v' in flags, 'n' in flags, 'c' in flags
        sources: list[tuple[str | None, str]] = []
        errors: list[str] = []
        if files:
            for path in files:
                try:
                    sources.append((path, _read_text(ctx.transport, _resolve(ctx, path))))
                except Exception as exc:
                    errors.append(f'grep: {path}: {exc}')
        else:
            sources.append((None, stdin or ''))

        multi = len(files) > 1
        out: list[str] = []
        matched = False
        for label, text in sources:
            count = 0
            for num, line in enumerate(text.splitlines(), 1):
                hit = bool(regex.search(line)) != invert
                if not hit:
                    continue
                matched = True
                count += 1
                if not count_only:
                    prefix = (f'{label}:' if multi else '') + (f'{num}:' if show_num else '')
                    out.append(prefix + line)
            if count_only:
                out.append((f'{label}:' if multi else '') + str(count))
        return Result(
            output='\n'.join(out),
            error='\n'.join(errors),
            code=0 if matched else 1,
        )


class Cp(Command):
    name = 'cp'
    summary = 'Copy a file'
    usage = 'cp <src> <dst>'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        _, _, paths = parse_args(args)
        if len(paths) != 2:
            return Result.fail('cp: usage: cp <src> <dst>')
        src, dst = _resolve(ctx, paths[0]), _resolve(ctx, paths[1])
        try:
            data = _read_bytes(ctx.transport, src)
        except Exception as exc:
            return Result.fail(f'cp: {paths[0]}: {exc}')
        try:
            ctx.transport.push(_dest_path(ctx, dst, src), data)
        except Exception as exc:
            return Result.fail(f'cp: {paths[1]}: {exc}')
        return Result()


class Mv(Command):
    name = 'mv'
    summary = 'Move or rename a file'
    usage = 'mv <src> <dst>'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        _, _, paths = parse_args(args)
        if len(paths) != 2:
            return Result.fail('mv: usage: mv <src> <dst>')
        src, dst = _resolve(ctx, paths[0]), _resolve(ctx, paths[1])
        try:
            data = _read_bytes(ctx.transport, src)
            ctx.transport.push(_dest_path(ctx, dst, src), data)
            ctx.transport.remove_path(src)
        except Exception as exc:
            return Result.fail(f'mv: {exc}')
        return Result()


class Rm(Command):
    name = 'rm'
    summary = 'Remove files or directories'
    usage = 'rm [-r] [-f] <path...>'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        flags, _, paths = parse_args(args)
        if not paths:
            return Result.fail('rm: usage: rm [-r] [-f] <path...>')
        recursive = 'r' in flags or 'R' in flags
        force = 'f' in flags
        errors: list[str] = []
        for path in paths:
            try:
                ctx.transport.remove_path(_resolve(ctx, path), recursive=recursive)
            except Exception as exc:
                if not force:
                    errors.append(f'rm: {path}: {exc}')
        return Result(error='\n'.join(errors), code=1 if errors else 0)


class Mkdir(Command):
    name = 'mkdir'
    summary = 'Create directories'
    usage = 'mkdir [-p] <path...>'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        flags, _, paths = parse_args(args)
        if not paths:
            return Result.fail('mkdir: usage: mkdir [-p] <path...>')
        parents = 'p' in flags
        errors: list[str] = []
        for path in paths:
            try:
                ctx.transport.make_dir(_resolve(ctx, path), make_parents=parents)
            except Exception as exc:
                errors.append(f'mkdir: {path}: {exc}')
        return Result(error='\n'.join(errors), code=1 if errors else 0)


class Touch(Command):
    name = 'touch'
    summary = 'Create an empty file if it does not exist'
    usage = 'touch <path...>'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        _, _, paths = parse_args(args)
        if not paths:
            return Result.fail('touch: usage: touch <path...>')
        errors: list[str] = []
        for path in paths:
            resolved = _resolve(ctx, path)
            try:
                ctx.transport.list_files(resolved, itself=True)
                continue  # already exists; Pebble can't bump mtime, so leave it
            except Exception:  # noqa: S110 - path absence is the expected case for touch
                pass
            try:
                ctx.transport.push(resolved, '')
            except Exception as exc:
                errors.append(f'touch: {path}: {exc}')
        return Result(error='\n'.join(errors), code=1 if errors else 0)
