# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Parser: single-pipe grammar and variable/tilde expansion."""

from __future__ import annotations

import pytest

from borescope.shell.parser import ParseError, expand, parse_and_expand, parse_pipeline


def test_blank_line():
    assert parse_pipeline('   ') == []


def test_single_command():
    assert parse_pipeline('ls -l /var/log') == [['ls', '-l', '/var/log']]


def test_quoted_argument_kept_together():
    assert parse_pipeline("grep 'hello world' f") == [['grep', 'hello world', 'f']]


def test_single_pipe():
    assert parse_pipeline('cat f | grep x') == [['cat', 'f'], ['grep', 'x']]


def test_quoted_pipe_is_not_a_split():
    assert parse_pipeline("echo 'a | b'") == [['echo', 'a | b']]


@pytest.mark.parametrize('op', [';', '&&', '||', '>', '>>', '<', '&'])
def test_unsupported_operators_rejected(op):
    with pytest.raises(ParseError):
        parse_pipeline(f'echo a {op} echo b')


def test_two_pipes_rejected():
    with pytest.raises(ParseError):
        parse_pipeline('a | b | c')


def test_empty_pipe_stage_rejected():
    with pytest.raises(ParseError):
        parse_pipeline('cat f |')


def test_expand_tilde():
    assert expand('~', {'HOME': '/root'}) == '/root'
    assert expand('~/logs', {'HOME': '/root'}) == '/root/logs'


def test_expand_var():
    env = {'HOME': '/root', 'APP': 'myapp'}
    assert expand('$HOME/$APP', env) == '/root/myapp'
    assert expand('${APP}.log', env) == 'myapp.log'


def test_expand_unknown_var_is_empty():
    assert expand('$NOPE/x', {}) == '/x'


def test_quoted_operator_is_literal():
    # A quoted ';' must be an argument, not rejected as sequencing.
    assert parse_pipeline("echo ';'") == [['echo', ';']]
    assert parse_pipeline('echo ">"') == [['echo', '>']]


_ENV = {'HOME': '/root', 'APP': 'myapp'}


def test_single_quotes_suppress_expansion():
    assert parse_and_expand("echo '$APP'", _ENV) == [['echo', '$APP']]
    assert parse_and_expand("echo '~'", _ENV) == [['echo', '~']]


def test_double_quotes_expand_vars_not_tilde():
    assert parse_and_expand('echo "$APP"', _ENV) == [['echo', 'myapp']]
    # ``~`` is literal inside double quotes.
    assert parse_and_expand('echo "~"', _ENV) == [['echo', '~']]


def test_unquoted_expands_var_and_tilde():
    assert parse_and_expand('cat $APP', _ENV) == [['cat', 'myapp']]
    assert parse_and_expand('cd ~/logs', _ENV) == [['cd', '/root/logs']]


def test_tilde_only_expands_at_word_start():
    assert parse_and_expand('echo a~b', _ENV) == [['echo', 'a~b']]


def test_mixed_quoting_within_a_word():
    # ``literal'$APP'"$APP"`` → literal + literal $APP + expanded myapp.
    assert parse_and_expand('echo x\'$APP\'"$APP"', _ENV) == [['echo', 'x$APPmyapp']]


def test_parse_and_expand_pipe():
    assert parse_and_expand('cat $APP | grep x', _ENV) == [['cat', 'myapp'], ['grep', 'x']]


def test_unbalanced_quote_raises():
    with pytest.raises(ParseError):
        parse_pipeline("echo 'unterminated")
