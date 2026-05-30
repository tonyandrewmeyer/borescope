# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Shell-state and trivial commands: cd, pwd, echo, env, exit, clear, help."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import pathutils
from .base import Command, ExitShell, Result

if TYPE_CHECKING:
    from ..context import ShellContext


class Cd(Command):
    name = 'cd'
    summary = 'Change the current directory'
    usage = 'cd [dir]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        target = args[0] if args else '~'
        path = pathutils.resolve(ctx.cwd, target, home=ctx.home)
        try:
            infos = ctx.transport.list_files(path, itself=True)
        except Exception as exc:
            return Result.fail(f'cd: {target}: {exc}')
        ftype = getattr(infos[0].type, 'name', '') if infos else ''
        # A symlink may point at a directory, and Pebble's metadata can't tell us
        # the target's type, so follow optimistically; only a definitively
        # non-directory entry (a regular file, device, …) is rejected outright.
        if ftype not in ('DIRECTORY', 'SYMLINK', ''):
            return Result.fail(f'cd: not a directory: {target}')
        ctx.chdir(path)
        return Result()


class Pwd(Command):
    name = 'pwd'
    summary = 'Print the current directory'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        return Result.ok(ctx.cwd)


class Echo(Command):
    name = 'echo'
    summary = 'Write arguments to output'
    usage = 'echo [args...]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        return Result.ok(' '.join(args))


class Env(Command):
    name = 'env'
    summary = "Show the shell's tracked environment"

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        lines = [f'{key}={value}' for key, value in sorted(ctx.env.items())]
        return Result.ok('\n'.join(lines))


class Exit(Command):
    name = 'exit'
    aliases = ('quit',)
    summary = 'Leave borescope'
    usage = 'exit [code]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        code = 0
        if args:
            try:
                code = int(args[0])
            except ValueError:
                code = 1
        raise ExitShell(code)


class Clear(Command):
    name = 'clear'
    summary = 'Clear the screen'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        return Result.ok('\033[H\033[2J')


class Help(Command):
    name = 'help'
    aliases = ('?',)
    summary = 'List available commands'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        from .base import build_registry

        seen: dict[str, Command] = {
            name: cmd
            for name, cmd in build_registry().items()
            if cmd.name == name  # skip aliases
        }
        width = max((len(n) for n in seen), default=0)
        lines = [f'  {name.ljust(width)}  {cmd.summary}' for name, cmd in sorted(seen.items())]
        header = "Built-in commands (anything else: 'exec <cmd> ...' runs it in the container):"
        return Result.ok(header + '\n' + '\n'.join(lines))
