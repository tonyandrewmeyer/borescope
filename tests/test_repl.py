# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""REPL execution: pipes, errors, exit, unsupported syntax."""

from __future__ import annotations

from typing import cast

import pytest

from borescope.shell.commands.base import Command, ExitShell
from borescope.shell.repl import Shell


def test_single_pipe_filters(ctx):
    result = Shell(ctx).run_line('cat /etc/passwd | grep root')
    assert 'root' in result.output
    assert 'daemon' not in result.output


def test_pipe_into_grep_count(ctx):
    result = Shell(ctx).run_line('cat /var/log/app/error.log | grep -c line')
    assert result.output == '3'


def test_command_not_found(ctx):
    result = Shell(ctx).run_line('frobnicate x')
    assert result.code == 127
    assert 'exec frobnicate' in result.error


def test_exit_raises_exitshell(ctx):
    with pytest.raises(ExitShell):
        Shell(ctx).run_line('exit 3')


def test_unsupported_syntax_reported(ctx):
    result = Shell(ctx).run_line('echo a > b')
    assert result.code == 1
    assert 'not supported' in result.error


def test_execute_and_emit_returns_exit_code(ctx):
    assert Shell(ctx).execute_and_emit('exit 5') == 5


def test_blank_line_is_noop(ctx):
    result = Shell(ctx).run_line('   ')
    assert result.code == 0
    assert result.output == ''


def test_logs_follow_rejected_in_pipe(ctx):
    result = Shell(ctx).run_line('logs --follow myapp | grep ERROR')
    assert result.code != 0
    assert "borescope: 'logs' cannot be used in a pipe." in result.error


def test_logs_follow_short_flag_rejected_in_pipe(ctx):
    result = Shell(ctx).run_line('logs -f myapp | grep ERROR')
    assert result.code != 0
    assert "borescope: 'logs' cannot be used in a pipe." in result.error


def test_logs_without_follow_not_rejected_in_pipe(ctx):
    """logs without --follow is pipeable; any failure here is not a pipe-rejection."""
    result = Shell(ctx).run_line('logs myapp | grep ERROR')
    assert 'cannot be used in a pipe' not in result.error


def test_broken_pipe_propagates_instead_of_reporting(ctx):
    """A BrokenPipeError from a command must escape to cli.main, which turns it
    into a quiet SIGPIPE-style exit — not become a '<name>: Broken pipe' Result."""
    shell = Shell(ctx)

    class Boom:
        name = 'boom'
        summary = 'raise BrokenPipeError'

        def would_stream(self, args):
            return False

        def run(self, ctx, args, stdin=None):
            raise BrokenPipeError

    # A plain class + cast rather than a Command subclass: subclassing would
    # leak 'boom' into the auto-discovery registry for every later test.
    shell.registry['boom'] = cast('Command', Boom())
    with pytest.raises(BrokenPipeError):
        shell.run_line('boom')
