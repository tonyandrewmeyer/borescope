"""Parser: single-pipe grammar and variable/tilde expansion."""

from __future__ import annotations

import pytest

from borescope.shell.parser import ParseError, expand, parse_pipeline


def test_blank_line():
    assert parse_pipeline("   ") == []


def test_single_command():
    assert parse_pipeline("ls -l /var/log") == [["ls", "-l", "/var/log"]]


def test_quoted_argument_kept_together():
    assert parse_pipeline("grep 'hello world' f") == [["grep", "hello world", "f"]]


def test_single_pipe():
    assert parse_pipeline("cat f | grep x") == [["cat", "f"], ["grep", "x"]]


def test_quoted_pipe_is_not_a_split():
    assert parse_pipeline("echo 'a | b'") == [["echo", "a | b"]]


@pytest.mark.parametrize("op", [";", "&&", "||", ">", ">>", "<", "&"])
def test_unsupported_operators_rejected(op):
    with pytest.raises(ParseError):
        parse_pipeline(f"echo a {op} echo b")


def test_two_pipes_rejected():
    with pytest.raises(ParseError):
        parse_pipeline("a | b | c")


def test_empty_pipe_stage_rejected():
    with pytest.raises(ParseError):
        parse_pipeline("cat f |")


def test_expand_tilde():
    assert expand("~", {"HOME": "/root"}) == "/root"
    assert expand("~/logs", {"HOME": "/root"}) == "/root/logs"


def test_expand_var():
    env = {"HOME": "/root", "APP": "myapp"}
    assert expand("$HOME/$APP", env) == "/root/myapp"
    assert expand("${APP}.log", env) == "myapp.log"


def test_expand_unknown_var_is_empty():
    assert expand("$NOPE/x", {}) == "/x"
