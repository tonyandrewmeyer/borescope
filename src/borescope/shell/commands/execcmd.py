# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""The ``exec`` escape hatch — run any binary that's already in the container."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Command, Result

if TYPE_CHECKING:
    from ..context import ShellContext


class Exec(Command):
    name = 'exec'
    summary = 'Run a program inside the container (escape hatch)'
    usage = 'exec <command> [args...]'

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        if not args:
            return Result.fail('exec: usage: exec <command> [args...]')
        from ops import pebble

        try:
            process = ctx.transport.exec(args, working_dir=ctx.cwd, stdin=stdin)
            out, err = process.wait_output()
        except pebble.ExecError as exc:
            return Result(
                output=exc.stdout or '',
                error=exc.stderr or '',
                code=exc.exit_code or 1,
            )
        except Exception as exc:
            return Result.fail(f'exec: {exc}')
        return Result(output=out or '', error=err or '', code=0)
