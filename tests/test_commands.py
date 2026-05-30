"""Built-in command behaviour against the in-memory fake transport."""

from __future__ import annotations

import pytest

from borescope.shell.commands.base import build_registry


@pytest.fixture
def registry():
    return build_registry()


def run(registry, ctx, name, *args, stdin=None):
    return registry[name].run(ctx, list(args), stdin)


# -- listing / reading -------------------------------------------------------
def test_ls(registry, ctx):
    result = run(registry, ctx, "ls", "/etc")
    assert set(result.output.split("\n")) == {"hostname", "passwd"}
    assert result.code == 0


def test_ls_long_format(registry, ctx):
    result = run(registry, ctx, "ls", "-l", "/etc")
    assert "hostname" in result.output
    assert result.output.startswith("-")  # file type char


def test_ls_missing_path_errors(registry, ctx):
    result = run(registry, ctx, "ls", "/nope")
    assert result.code == 1
    assert "ls:" in result.error


def test_cat(registry, ctx):
    assert run(registry, ctx, "cat", "/etc/hostname").output == "borescope\n"


def test_cat_stdin_passthrough(registry, ctx):
    assert run(registry, ctx, "cat", stdin="piped").output == "piped"


def test_head(registry, ctx):
    out = run(registry, ctx, "head", "-n", "2", "/var/log/app/error.log").output
    assert out == "line1\nline2"


def test_tail(registry, ctx):
    out = run(registry, ctx, "tail", "-n", "2", "/var/log/app/error.log").output
    assert out == "ERROR boom\nline4"


def test_grep_file(registry, ctx):
    result = run(registry, ctx, "grep", "ERROR", "/var/log/app/error.log")
    assert result.output == "ERROR boom"
    assert result.code == 0


def test_grep_no_match_exit_1(registry, ctx):
    result = run(registry, ctx, "grep", "zzz", "/var/log/app/error.log")
    assert result.output == ""
    assert result.code == 1


def test_grep_stdin_with_line_numbers(registry, ctx):
    result = run(registry, ctx, "grep", "-n", "b", stdin="a\nb\nbb\n")
    assert result.output == "2:b\n3:bb"


def test_find_by_name(registry, ctx):
    result = run(registry, ctx, "find", "/var", "-name", "*.log")
    assert result.output == "/var/log/app/error.log"


def test_find_by_type_dir(registry, ctx):
    result = run(registry, ctx, "find", "/var", "-type", "d")
    assert "/var/log" in result.output
    assert "/var/log/app" in result.output


def test_stat(registry, ctx):
    result = run(registry, ctx, "stat", "/etc/hostname")
    assert "File: /etc/hostname" in result.output


# -- write operations --------------------------------------------------------
def test_mkdir_touch_cp_mv_rm(registry, ctx, transport):
    assert run(registry, ctx, "mkdir", "-p", "/work/sub").code == 0
    assert "/work/sub" in transport.dirs

    assert run(registry, ctx, "touch", "/work/a.txt").code == 0
    assert "/work/a.txt" in transport.files

    assert run(registry, ctx, "cp", "/etc/hostname", "/work/h.txt").code == 0
    assert transport.files["/work/h.txt"] == b"borescope\n"

    assert run(registry, ctx, "mv", "/work/h.txt", "/work/sub/h2.txt").code == 0
    assert "/work/h.txt" not in transport.files
    assert transport.files["/work/sub/h2.txt"] == b"borescope\n"

    assert run(registry, ctx, "rm", "-r", "/work").code == 0
    assert "/work" not in transport.dirs


def test_rm_missing_without_force_errors(registry, ctx):
    result = run(registry, ctx, "rm", "/nope")
    assert result.code == 1


def test_rm_missing_with_force_ok(registry, ctx):
    result = run(registry, ctx, "rm", "-f", "/nope")
    assert result.code == 0


# -- shell state -------------------------------------------------------------
def test_cd_changes_cwd(registry, ctx):
    run(registry, ctx, "cd", "/var/log/app")
    assert ctx.cwd == "/var/log/app"
    assert run(registry, ctx, "pwd").output == "/var/log/app"


def test_cd_into_file_errors(registry, ctx):
    result = run(registry, ctx, "cd", "/etc/hostname")
    assert result.code == 1
    assert ctx.cwd == "/"


def test_cd_relative(registry, ctx):
    run(registry, ctx, "cd", "/var")
    run(registry, ctx, "cd", "log/app")
    assert ctx.cwd == "/var/log/app"


def test_echo(registry, ctx):
    assert run(registry, ctx, "echo", "hello", "world").output == "hello world"


def test_exec_echo(registry, ctx):
    assert run(registry, ctx, "exec", "echo", "hi").output == "hi\n"


def test_service_action_past_tense_strings():
    # Naive "verb + 'ed'" produced "Stoped" (one p); each subclass now declares
    # its past-tense form explicitly. Lock that in.
    from borescope.shell.commands.pebble import Restart, Start, Stop

    assert Start.past == "Started"
    assert Stop.past == "Stopped"
    assert Restart.past == "Restarted"
