"""REPL execution: pipes, errors, exit, unsupported syntax."""

from __future__ import annotations

import pytest

from cascade.shell.commands.base import ExitShell
from cascade.shell.repl import Shell


def test_single_pipe_filters(ctx):
    result = Shell(ctx).run_line("cat /etc/passwd | grep root")
    assert "root" in result.output
    assert "daemon" not in result.output


def test_pipe_into_grep_count(ctx):
    result = Shell(ctx).run_line("cat /var/log/app/error.log | grep -c line")
    assert result.output == "3"


def test_command_not_found(ctx):
    result = Shell(ctx).run_line("frobnicate x")
    assert result.code == 127
    assert "exec frobnicate" in result.error


def test_exit_raises_exitshell(ctx):
    with pytest.raises(ExitShell):
        Shell(ctx).run_line("exit 3")


def test_unsupported_syntax_reported(ctx):
    result = Shell(ctx).run_line("echo a > b")
    assert result.code == 1
    assert "not supported" in result.error


def test_execute_and_emit_returns_exit_code(ctx):
    assert Shell(ctx).execute_and_emit("exit 5") == 5


def test_blank_line_is_noop(ctx):
    result = Shell(ctx).run_line("   ")
    assert result.code == 0
    assert result.output == ""
